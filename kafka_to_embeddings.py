import json
import numpy as np
import os
from kafka import KafkaConsumer
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams
from sentence_transformers import SentenceTransformer
import uuid

# Kafka Configuration
KAFKA_BROKER = "kafka:9092"
KAFKA_TOPIC = "tweets_cdc"

# Qdrant Configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))  # Ensure integer type
COLLECTION_NAME = "tweet_embeddings"

# Initialize Qdrant Client
qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, prefer_grpc=False)

# Ensure Qdrant Collection Exists
def setup_qdrant():
    collections = qdrant.get_collections().collections
    collection_names = [c.name for c in collections]

    if COLLECTION_NAME not in collection_names:
        # Create the collection with on-disk indexing enabled
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=384, distance=Distance.EUCLID, on_disk=True),
        )
        print(f"✅ Created Qdrant Collection: {COLLECTION_NAME}")
    else:
        print(f"✅ Qdrant Collection '{COLLECTION_NAME}' Already Exists")

    # 🔹 Force Qdrant to index vectors immediately
    qdrant.update_collection(
        collection_name=COLLECTION_NAME,
        optimizer_config={"indexing_threshold": 1},  # Ensures immediate indexing
    )
    print(f"⚡ Updated Qdrant Indexing Threshold to 1 for {COLLECTION_NAME}")

setup_qdrant()



# Load the embedding model
model = SentenceTransformer("BAAI/bge-small-en")

print("✅ Listening for tweets from Kafka...")

consumer = KafkaConsumer(
    KAFKA_TOPIC,
    bootstrap_servers=KAFKA_BROKER,
    auto_offset_reset="earliest",
    enable_auto_commit=True,
    value_deserializer=lambda x: json.loads(x.decode("utf-8")),
)

for message in consumer:
    tweet = message.value
    print(f"📢 New Tweet Detected: {tweet}")

    # Ensure the tweet contains required fields
    if not all(k in tweet for k in ("text", "hashtags", "user_handle", "tweet_id")):
        print(f"❌ Skipping malformed tweet: {tweet}")
        continue

    # Extract text + hashtags + user handle for generating the EMBEDDING VECTOR
    embedding_text = f"{tweet['text']} {' '.join(tweet['hashtags'])} {tweet['user_handle']}"

    # Generate embedding
    embedding = model.encode(embedding_text, convert_to_numpy=True).astype(np.float32).tolist()

    print(f"✅ Embedding Generated: {embedding[:5]}... (Truncated)")

    # Generate a unique ID based on tweet_id
    point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, str(tweet["tweet_id"])))

    print(f"🚀 Sending to Qdrant: ID={point_id}")
    print(f"➡️ Vector: {embedding[:5]}... (Truncated)")
    print(f"➡️ Metadata: {tweet}")

    # Store in Qdrant
    qdrant.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(
                id=point_id,  # ✅ Convert tweet_id to a UUID string
                vector=embedding,  # ✅ Convert NumPy array to a list
                payload={  # Store metadata
                    "tweet_id": str(tweet["tweet_id"]),  # ✅ Ensure tweet_id is a string
                    "text": tweet["text"],
                    "hashtags": tweet["hashtags"],
                    "user_handle": tweet["user_handle"],
                    "created_at": tweet.get("created_at", "unknown"),
                },
            )
        ],
    )

    print(f"✅ Stored in Qdrant: {tweet['tweet_id']}")

print("🚀 Qdrant Vector Storage Running!")