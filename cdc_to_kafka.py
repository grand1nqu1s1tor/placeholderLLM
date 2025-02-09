import json
import os
from dotenv import load_dotenv
from kafka import KafkaProducer
from pymongo import MongoClient
from datetime import datetime

# Load environment variables
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017/twitter_etl")
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "tweets_cdc")

# Connect to MongoDB
print("🔹 Connecting to MongoDB...")
client = MongoClient(MONGO_URI)
db = client["twitter_etl"]
collection = db["tweets"]
print("✅ Connected to MongoDB.")

# Kafka Producer Setup
print("🔹 Connecting to Kafka...")
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
)
print("✅ Connected to Kafka.")

print("✅ CDC Started: Listening for new tweets in MongoDB...")

try:
    # Watch for new tweets
    with collection.watch() as stream:
        for change in stream:
            print(
                f"🔄 MongoDB Change Detected: {change}"
            )  #  Debugging log (print every change)

            if change["operationType"] == "insert":
                tweet_data = change["fullDocument"]

                # Extract only relevant fields
                tweet_message = {
                    "tweet_id": tweet_data.get("tweet_id", "unknown"),
                    "text": tweet_data.get("text", ""),
                    "user_handle": tweet_data.get("user", {}).get("handle", "unknown"),
                    "hashtags": tweet_data.get("hashtags", []),
                    "created_at": tweet_data.get("created_at", change.get("wallTime", datetime.utcnow()).isoformat()),
                    #  Fallback to wallTime

                }

                print(
                    f"📢 New Tweet Detected: {tweet_message}"
                )  # ✅ Log every tweet detected

                # Send to Kafka
                producer.send(KAFKA_TOPIC, tweet_message)
                print("✅ Tweet sent to Kafka!")  # ✅ Log successful Kafka push

except Exception as e:
    print(f"❌ CDC Service Error: {e}")  # ✅ Log errors
