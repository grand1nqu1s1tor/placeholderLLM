import os
import json
from pymongo import MongoClient
from kafka import KafkaProducer
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB Connection
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017/twitter_etl")
client = MongoClient(MONGO_URI)
db = client["twitter_etl"]
collection = db["tweets"]

# Kafka Producer Setup
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "tweets_cdc")

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

print("✅ CDC Started: Listening for new tweets in MongoDB...")

# Watch for new tweets in MongoDB
with collection.watch() as stream:
    for change in stream:
        if change["operationType"] == "insert":
            tweet_data = change["fullDocument"]

            # Extract only relevant fields before sending to Kafka
            tweet_message = {
                "tweet_id": tweet_data["tweet_id"],
                "text": tweet_data["text"],
                "user_handle": tweet_data["user"]["handle"],
                "created_at": tweet_data["created_at"],
                "likes": tweet_data["engagement"]["likes"],
                "retweets": tweet_data["engagement"]["retweets"],
            }

            print(f"📢 New Tweet Detected: {tweet_message['text']}")

            # Send to Kafka
            producer.send(KAFKA_TOPIC, tweet_message)
            print("✅ Tweet sent to Kafka!")
