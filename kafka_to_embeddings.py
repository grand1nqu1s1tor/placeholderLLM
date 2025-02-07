import json
from kafka import KafkaConsumer
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

# Kafka Config
KAFKA_BROKER = "kafka:9092"
KAFKA_TOPIC = "tweets_cdc"

# Load the embedding model
model = SentenceTransformer("BAAI/bge-small-en")

# FAISS Vector Store Setup
d = 384  # Dimension of embeddings
index = faiss.IndexFlatL2(d)  # L2 similarity index

print("✅ Listening for tweets from Kafka...")

consumer = KafkaConsumer(
    KAFKA_TOPIC,
    bootstrap_servers=KAFKA_BROKER,
    auto_offset_reset="earliest",
    enable_auto_commit=True,
    value_deserializer=lambda x: json.loads(x.decode("utf-8")),
)

tweet_data = []  # Store tweet metadata

for message in consumer:
    tweet = message.value
    print(f"📢 New Tweet Detected: {tweet['text']}")

    # Extract only text & hashtags
    embedding_text = (
        tweet["text"] + " " + " ".join(tweet["hashtags"]) + " " + tweet["user_handle"]
    )

    # Generate embedding
    embedding = model.encode(embedding_text, convert_to_numpy=True)
    print(f"✅ Embedding Generated: {embedding}")

    # Add embedding to FAISS
    index.add(np.array([embedding]))

    # Store metadata
    tweet_data.append(
        {
            "tweet_id": tweet["tweet_id"],
            "text": tweet["text"],
            "hashtags": tweet["hashtags"],
        }
    )

    print(f"📢 Processed Tweet: {tweet['text']} (Embedding Generated)")
