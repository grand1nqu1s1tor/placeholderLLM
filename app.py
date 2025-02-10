import os
import requests
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from qdrant_client import QdrantClient
from sentence_transformers import CrossEncoder
from sentence_transformers import SentenceTransformer

load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Connect to Qdrant
qdrant = QdrantClient(host="qdrant", port=6333)

# Load Sentence Transformer model
model = SentenceTransformer("BAAI/bge-small-en")
reranker = CrossEncoder("BAAI/bge-reranker-base", device="cpu")

# Hugging Face API Key (replace with your actual key)
HUGGINGFACE_API_KEY = os.getenv("HF_APP_TOKEN")
HEADERS = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}

# Define request model for search
class QueryRequest(BaseModel):
    query: str
    top_k: int = 10  # Default to 10 results


# 📌 1️⃣ API to Get Top 10 Trending Topics
@app.get("/trending_summary")
def summarize_trends():
    """Summarize the trending topics into meaningful insights"""

    # ✅ Fix: Use scroll instead of search (search requires a query vector)
    trending_results = qdrant.scroll(
        collection_name="trending_topics",
        limit=5
    )
    top_trends = [result.payload["topic"] for result in trending_results]

    summaries = []
    for trend in top_trends:
        trend_embedding = model.encode(trend, convert_to_numpy=True).tolist()
        related_tweets = qdrant.search(
            collection_name="tweet_embeddings",
            query_vector=trend_embedding,
            limit=5
        )

        # ✅ Fix: Handle missing 'text' field safely
        tweet_texts = " ".join([result.payload.get("text", "") for result in related_tweets])

        # ✅ Context-aware prompt for summarization
        prompt = f"Summarize these tweets about '{trend}': {tweet_texts}"

        # ✅ Call Hugging Face API for summarization
        response = requests.post(
            "https://api-inference.huggingface.co/models/t5-small",
            headers=HEADERS,
            json={"inputs": prompt}
        )

        summary = response.json()
        summaries.append({"trend": trend, "summary": summary})

    return {"trending_summaries": summaries}

@app.post("/search")
def search_tweets(request: QueryRequest):
    """Retrieve and rerank tweets using `bge-reranker-base` locally."""

    # Ensure query embedding is a flat list
    query_embedding = model.encode(request.query, convert_to_numpy=True).tolist()

    # Check if it's nested and flatten it
    if isinstance(query_embedding[0], list):
        query_embedding = query_embedding[0]  # Convert [[...]] → [...]

    # Retrieve similar tweets from Qdrant
    search_results = qdrant.search(
        collection_name="tweet_embeddings",
        query_vector=query_embedding,  # Now it's a flat list
        limit=request.top_k
    )

    # Handle missing 'text' field safely
    tweet_texts = [result.payload.get("text", "") for result in search_results]

    # Format input for reranking (query-text pairs)
    reranking_input = [(request.query, tweet) for tweet in tweet_texts]

    # Get reranking scores from `bge-reranker-base`
    scores = reranker.predict(reranking_input, batch_size=len(reranking_input))

    # Sort results based on scores and convert numpy.float32 to float
    reranked_results = sorted(
        [{"tweet": tweet, "score": float(score)} for tweet, score in zip(tweet_texts, scores)],
        key=lambda x: x["score"],
        reverse=True  # Higher score = more relevant
    )

    return {"query": request.query, "reranked_results": reranked_results}
