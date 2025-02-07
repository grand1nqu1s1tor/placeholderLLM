import asyncio
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from twikit import Client

# Load environment variables from .env file
load_dotenv()

# Get Twitter credentials from environment variables
USERNAME = os.getenv("TWITTER_USERNAME")
EMAIL = os.getenv("TWITTER_EMAIL")
PASSWORD = os.getenv("TWITTER_PASSWORD")

# MongoDB Connection
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017/twitter_etl")
client_mongo = MongoClient(MONGO_URI)
db = client_mongo["twitter_etl"]
collection = db["tweets"]

if not USERNAME or not EMAIL or not PASSWORD:
    raise ValueError("❌ Twitter credentials not set! Check your .env file.")

# Initialize Twikit Client
client = Client("en-US")


async def fetch_full_tweets():
    # Log in to Twikit
    await client.login(
        auth_info_1=USERNAME,
        auth_info_2=EMAIL,
        password=PASSWORD,
        cookies_file="cookies.json",
    )
    print("✅ Logged in successfully!")

    # Step 1: Fetch Tweet IDs (Search for tweets)
    tweets = await client.search_tweet("LLM", "Top", 20)
    tweet_ids = [tweet.id for tweet in tweets[:10]]  # Get first 10 tweet IDs

    print(f"🔹 Found {len(tweet_ids)} tweet IDs: {tweet_ids}")

    if not tweet_ids:
        print("⚠ No tweets found. Exiting.")
        return

    # Step 2: Fetch Full Tweet Details
    full_tweets = await client.get_tweets_by_ids(tweet_ids)

    # Step 3: Print Full Tweets
    for tweet in full_tweets:
        tweet_data = {
            "tweet_id": tweet._data["rest_id"],
            "text": tweet._data["legacy"]["full_text"],
            "user": {
                "user_id": tweet._data["core"]["user_results"]["result"]["rest_id"],
                "handle": tweet._data["core"]["user_results"]["result"]["legacy"][
                    "screen_name"
                ],
            },
            "created_at": tweet._data["legacy"]["created_at"],
            "engagement": {
                "likes": tweet._data["legacy"]["favorite_count"],
                "retweets": tweet._data["legacy"]["retweet_count"],
            },
            "mentions": [
                mention["screen_name"]
                for mention in tweet._data["legacy"]["entities"]["user_mentions"]
            ],
            "hashtags": [
                hashtag["text"]
                for hashtag in tweet._data["legacy"]["entities"]["hashtags"]
            ],
            "urls": [
                url["expanded_url"] for url in tweet._data["legacy"]["entities"]["urls"]
            ],
        }
        # TODO Only edd to mongo if its engagement is significant
        collection.insert_one(tweet_data)
        print(f"\n✅ Tweet Data:\n{tweet_data}")


# Run the async function
asyncio.run(fetch_full_tweets())
