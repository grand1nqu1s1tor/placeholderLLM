import json
import numpy as np
import os
import uuid
from kafka import KafkaConsumer
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams
from sentence_transformers import SentenceTransformer

# Kafka Configuration
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
KAFKA_TOPICS = [os.getenv("TRENDING_TOPIC", "tweets_trending"), os.getenv("AI_TOPIC", "tweets_ai")]

# Qdrant Configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
COLLECTION_NAME = "tweet_embeddings"

# Initialize Qdrant Client
qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, prefer_grpc=False)


# Ensure Qdrant Collection Exists
def setup_qdrant():
    collections = qdrant.get_collections().collections
    collection_names = [c.name for c in collections]

    if COLLECTION_NAME not in collection_names:
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE, on_disk=True),
        )
        print(f"Created Qdrant Collection: {COLLECTION_NAME}")
    else:
        print(f"Qdrant Collection '{COLLECTION_NAME}' Already Exists")

    qdrant.update_collection(
        collection_name=COLLECTION_NAME,
        optimizer_config={"indexing_threshold": 5},
    )
    print(f"Updated Qdrant Indexing Threshold to 1 for {COLLECTION_NAME}")


setup_qdrant()

# Load the embedding model
model = SentenceTransformer("BAAI/bge-small-en")

print("Listening for tweets from Kafka...")

# Initialize Kafka Consumer to listen to both topics
consumer = KafkaConsumer(
    *KAFKA_TOPICS,
    bootstrap_servers=KAFKA_BROKER,
    auto_offset_reset="earliest",
    enable_auto_commit=True,
    value_deserializer=lambda x: json.loads(x.decode("utf-8")) if x else None,
)

for message in consumer:
    if message.value is None:  # ✅ Skip None messages
        print("⚠ Received an empty Kafka message. Skipping...")
        continue

    tweet = message.value
    topic = message.topic  # ✅ Extract topic name

    print(f"New Tweet Detected from {topic}: {tweet}")

    # Ensure the tweet contains required fields
    if not all(k in tweet for k in ("text", "hashtags", "user_handle", "tweet_id")):
        print(f"Skipping malformed tweet: {tweet}")
        continue

    # Extract text + hashtags + user handle for generating the embedding vector
    embedding_text = f"{tweet['text']} {' '.join(tweet['hashtags'])} {tweet['user_handle']}"

    # Generate embedding
    embedding = model.encode(embedding_text, convert_to_numpy=True).astype(np.float32).tolist()

    print(f"Embedding Generated: {embedding[:5]}... (Truncated)")

    # Generate a unique ID based on tweet_id
    point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, str(tweet["tweet_id"])))

    print(f"Sending to Qdrant: ID={point_id}")
    print(f"Vector: {embedding[:5]}... (Truncated)")
    print(f"Metadata: {tweet}")

    # Store in Qdrant
    qdrant.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "tweet_id": str(tweet["tweet_id"]),
                    "text": tweet["text"],
                    "hashtags": tweet["hashtags"],
                    "user_handle": tweet["user_handle"],
                    "created_at": tweet.get("created_at", "unknown"),
                    "category": "trending" if topic == os.getenv("TRENDING_TOPIC", "tweets_trending") else "ai",
                },
            )
        ],
    )

    print(f"Stored in Qdrant: {tweet['tweet_id']} under category {topic}")

print("Qdrant Vector Storage Running!")
