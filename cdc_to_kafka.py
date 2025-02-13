import json
import os
import time
import threading
from datetime import datetime
from dotenv import load_dotenv
from kafka import KafkaProducer
from pymongo import MongoClient

# Load environment variables
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017/twitter_etl")
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
KAFKA_TRENDING_TOPIC = os.getenv("TRENDING_TOPIC", "tweets_trending")
KAFKA_AI_TOPIC = os.getenv("AI_TOPIC", "tweets_ai")

print("Connecting to MongoDB...")
client = MongoClient(MONGO_URI)
db = client["twitter_etl"]

# Collections to Watch
trending_collection = db["tweets_trending"]
ai_collection = db["tweets_ai"]
print("Connected to MongoDB.")

# Kafka Producer Setup
print("Connecting to Kafka...")
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
)
print("Connected to Kafka.")

print("CDC Started: Listening for new tweets in MongoDB...")


def watch_collection(collection, kafka_topic):
    """Watches a MongoDB collection and sends new tweets to Kafka."""
    while True:
        try:
            with collection.watch() as stream:
                for change in stream:
                    print(f"MongoDB Change Detected in {collection.name}: {change}")

                    if change["operationType"] == "insert":
                        tweet_data = change["fullDocument"]

                        tweet_message = {
                            "tweet_id": tweet_data.get("tweet_id", "unknown"),
                            "text": tweet_data.get("text", ""),
                            "user_handle": tweet_data.get("user", {}).get("handle", "unknown"),
                            "hashtags": tweet_data.get("hashtags", []),
                            "created_at": tweet_data.get("created_at", datetime.utcnow().isoformat()),
                        }

                        print(f"New Tweet Detected in {collection.name}: {tweet_message}")

                        # Send to Kafka with Exception Handling
                        try:
                            producer.send(kafka_topic, tweet_message)
                            print(f"✅ Tweet sent to Kafka Topic: {kafka_topic}")
                        except Exception as kafka_error:
                            print(f"❌ Kafka Error: {kafka_error}")

        except Exception as e:
            print(f"⚠️ CDC Service Error on {collection.name}: {e}")
            print("🔄 Restarting CDC Watcher...")
            time.sleep(5)  # Small delay before retrying


# Start watching both collections in separate threads
threading.Thread(target=watch_collection, args=(trending_collection, KAFKA_TRENDING_TOPIC), daemon=True).start()
threading.Thread(target=watch_collection, args=(ai_collection, KAFKA_AI_TOPIC), daemon=True).start()

# Keep script running with a better approach
stop_event = threading.Event()
stop_event.wait()
