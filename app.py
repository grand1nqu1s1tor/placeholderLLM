import os
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from qdrant_client import QdrantClient
from sentence_transformers import CrossEncoder, SentenceTransformer

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Connect to Qdrant
qdrant = QdrantClient(host="qdrant", port=6333)

# Load models
model = SentenceTransformer("BAAI/bge-small-en")
reranker = CrossEncoder("BAAI/bge-reranker-base", device="cpu")

# Hugging Face API Key
HUGGINGFACE_API_KEY = os.getenv("HF_APP_TOKEN")
HEADERS = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}

# Define request model
class QueryRequest(BaseModel):
    query: str
    top_k: int = 10  # Default to 10 results


@app.get("/trending_summary")
def summarize_trends(limit: int = 10):
    """
    Summarize trending topics into meaningful insights.
    By default, retrieves up to 10 topics from the 'trending_topics' collection.
    """

    # Scroll Qdrant to fetch the trending topics
    try:
        trending_results = qdrant.scroll(collection_name="trending_topics", limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to scroll Qdrant: {e}")

    top_trends = [res.payload["topic"] for res in trending_results]

    summaries = []
    for trend in top_trends:
        # Encode trend into embedding and search for related tweets
        try:
            trend_embedding = model.encode(trend, convert_to_numpy=True).tolist()
            related_tweets = qdrant.search(
                collection_name="tweet_embeddings",
                query_vector=trend_embedding,
                limit=5
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to query Qdrant: {e}")

        # Safely get tweet texts
        tweet_texts = " ".join(
            [tweet.payload.get("text", "") for tweet in related_tweets]
        )

        # Summarization prompt
        prompt = f"Summarize these tweets about '{trend}': {tweet_texts}"

        # Call Hugging Face T5 API
        try:
            response = requests.post(
                "https://api-inference.huggingface.co/models/t5-small",
                headers=HEADERS,
                json={"inputs": prompt},
            )
            response.raise_for_status()  # Raise if non-2xx response
            summary = response.json()
        except requests.RequestException as e:
            raise HTTPException(
                status_code=500, detail=f"Hugging Face summarization API error: {e}"
            )

        summaries.append({"trend": trend, "summary": summary})

    return {"trending_summaries": summaries}


@app.post("/search")
def search_tweets(request: QueryRequest):
    """
    Retrieve and rerank tweets using `bge-reranker-base` locally.
    """

    # Encode query
    try:
        query_embedding = model.encode(request.query, convert_to_numpy=True).tolist()
        # Flatten if nested
        if isinstance(query_embedding[0], list):
            query_embedding = query_embedding[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to encode query: {e}")

    # Search in Qdrant
    try:
        search_results = qdrant.search(
            collection_name="tweet_embeddings",
            query_vector=query_embedding,
            limit=request.top_k,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Qdrant search error: {e}")

    # Safely extract tweet texts
    tweet_texts = [res.payload.get("text", "") for res in search_results]

    # Prepare input for reranker
    reranking_input = [(request.query, text) for text in tweet_texts]

    # Local reranking
    try:
        scores = reranker.predict(reranking_input, batch_size=len(reranking_input))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reranker inference error: {e}")

    # Sort by score descending
    reranked_results = sorted(
        (
            {"tweet": txt, "score": float(score)}
            for txt, score in zip(tweet_texts, scores)
        ),
        key=lambda x: x["score"],
        reverse=True,
    )

    return {"query": request.query, "reranked_results": reranked_results}
