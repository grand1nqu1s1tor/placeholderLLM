import asyncio
import os
import random
from dotenv import load_dotenv
from pymongo import MongoClient
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from twikit import Client

# Load environment variables
load_dotenv()

# Twitter API Credentials
USERNAME = os.getenv("TWITTER_USERNAME")
EMAIL = os.getenv("TWITTER_EMAIL")
PASSWORD = os.getenv("TWITTER_PASSWORD")

# MongoDB Connection
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017/twitter_etl")
client_mongo = MongoClient(MONGO_URI)
db = client_mongo["twitter_etl"]
collection = db["tweets_ai"]

if "tweets_ai" not in db.list_collection_names():
    db.create_collection("tweets_ai")
    print("Created collection: tweets_ai")

client = Client("en-US")

if not USERNAME or not EMAIL or not PASSWORD:
    raise ValueError("Twitter credentials not set! Check your .env file.")


# Retry with exponential backoff if API fails
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
)
async def fetch_ai_tweets():
    """Fetches tweets related to AI using a fixed query."""
    ai_queries = ["Crypto", "GPT", "LLM", "AI"]

    all_tweets = []
    for query in ai_queries:
        print(f"\n🔍 Searching tweets for AI topic: {query}")
        tweets = await client.search_tweet(query, "Top", 20)
        all_tweets.extend(tweets)

    return all_tweets


async def fetch_full_ai_tweets():
    while True:
        try:
            # Log in to Twikit
            await client.login(
                auth_info_1=USERNAME,
                auth_info_2=EMAIL,
                password=PASSWORD,
                cookies_file="cookies.json",
            )
            print("✅ Logged in successfully for AI tweets!")

            # Fetch AI tweets
            tweets = await fetch_ai_tweets()
            tweet_ids = [tweet.id for tweet in tweets]

            print(f"🔹 Found {len(tweet_ids)} AI-related tweet IDs")

            if not tweet_ids:
                print("⚠ No AI-related tweets found. Retrying in 2 hours...")
                await asyncio.sleep(7200)
                continue

            # Fetch full tweet details
            full_tweets = await client.get_tweets_by_ids(tweet_ids)

            # Store in MongoDB (Only High-Engagement)
            for tweet in full_tweets:
                try:
                    tweet_data = {
                        "topic": "AI",
                        "tweet_id": tweet._data["rest_id"],
                        "text": tweet._data["legacy"]["full_text"],
                        "user": {
                            "user_id": tweet._data["core"]["user_results"]["result"][
                                "rest_id"
                            ],
                            "handle": tweet._data["core"]["user_results"]["result"][
                                "legacy"
                            ]["screen_name"],
                        },
                        "created_at": tweet._data["legacy"]["created_at"],
                        "engagement": {
                            "likes": tweet._data["legacy"]["favorite_count"],
                            "retweets": tweet._data["legacy"]["retweet_count"],
                        },
                        "mentions": [
                            mention["screen_name"]
                            for mention in tweet._data["legacy"]["entities"][
                                "user_mentions"
                            ]
                        ],
                        "hashtags": [
                            hashtag["text"]
                            for hashtag in tweet._data["legacy"]["entities"]["hashtags"]
                        ],
                        "urls": [
                            url["expanded_url"]
                            for url in tweet._data["legacy"]["entities"]["urls"]
                        ],
                    }

                    #  **Filter Out Low-Engagement Tweets**
                    if (
                        tweet_data["engagement"]["likes"] >= 1000
                        or tweet_data["engagement"]["retweets"] >= 100
                    ):
                        # Overwrite tweet in MongoDB (or insert if not exists)
                        collection.replace_one(
                            {"tweet_id": tweet_data["tweet_id"]},
                            tweet_data,
                            upsert=True,
                        )
                        print(f" Overwritten AI Tweet: {tweet_data['tweet_id']}")
                    else:
                        print(
                            f"⚠ Skipping low engagement tweet: {tweet_data['tweet_id']} from topic '{tweet_data['topic']}'"
                        )

                    # ✅ **Prevent API rate limiting**
                    await asyncio.sleep(random.uniform(1, 3))

                except Exception as e:
                    print(f" Error processing AI tweet: {e}")

            print("\n⏳ Sleeping for 2 hours before fetching AI tweets again...")
            await asyncio.sleep(7200)  # Sleep for 2 hours before refetching

        except Exception as e:
            print(f" Fatal Error: {e}")
            print("Retrying in 2 hours...")
            await asyncio.sleep(7200)  # Wait before retrying


# Run the async function
asyncio.run(fetch_full_ai_tweets())
