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
collection = db["tweets_trending"]

if "tweets" not in db.list_collection_names():
    db.create_collection("tweets")
    print("Created collection: tweets")


# Initialize Twikit Client
client = Client("en-US")

if not USERNAME or not EMAIL or not PASSWORD:
    raise ValueError("Twitter credentials not set! Check your .env file.")


# Retry with exponential backoff if API fails
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
)
async def fetch_trending_topics():
    """Fetches the top 10 trending topics on Twitter."""
    return await client.get_trends(category="for-you", count=10)


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
)
async def fetch_tweets_by_topic(topic):
    """Fetches up to 50 tweets for a given trending topic."""
    return await client.search_tweet(topic, "Top", 5)


async def fetch_full_tweets():
    while True:
        try:
            # Log in to Twikit
            await client.login(
                auth_info_1=USERNAME,
                auth_info_2=EMAIL,
                password=PASSWORD,
                cookies_file="cookies.json",
            )
            print("✅ Logged in successfully!")

            # Step 1: Fetch Trending Topics
            trending_topics = await fetch_trending_topics()
            topic_names = [trend.name for trend in trending_topics]

            print(f"🔹 Top 10 Trending Topics: {topic_names}")

            if not topic_names:
                print(
                    "⚠ No trending topics found. Sleeping for 2 hours before retrying..."
                )
                await asyncio.sleep(7200)  # Sleep for 2 hours
                continue

            # Step 2: Loop through each topic and fetch tweets
            for topic in topic_names:
                print(f"\n🔍 Searching tweets for topic: {topic}")

                tweets = await fetch_tweets_by_topic(topic)
                tweet_ids = [tweet.id for tweet in tweets[:5]]

                print(f"🔹 Found {len(tweet_ids)} tweet IDs for '{topic}'")

                if not tweet_ids:
                    print(f"⚠ No tweets found for '{topic}'. Skipping...")
                    continue

                # Step 3: Fetch Full Tweet Details
                full_tweets = await client.get_tweets_by_ids(tweet_ids)

                # Step 4: Store Full Tweets in MongoDB (Only High-Engagement)
                for tweet in full_tweets:
                    try:
                        tweet_data = {
                            "topic": topic,
                            "tweet_id": tweet._data["rest_id"],
                            "text": tweet._data["legacy"]["full_text"],
                            "user": {
                                "user_id": tweet._data["core"]["user_results"][
                                    "result"
                                ]["rest_id"],
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
                                for hashtag in tweet._data["legacy"]["entities"][
                                    "hashtags"
                                ]
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
                            print(
                                f" Overwritten Tweet: {tweet_data['tweet_id']} from topic '{topic}'"
                            )

                        else:
                            print(
                                f"⚠ Skipping low engagement tweet: {tweet_data['tweet_id']} from topic '{topic}'"
                            )

                        # ✅ **Prevent API rate limiting**
                        await asyncio.sleep(random.uniform(1, 3))

                    except Exception as e:
                        print(f" Error processing tweet: {e}")

            print("\n⏳ Sleeping for 2 hours before fetching new trends...")
            await asyncio.sleep(7200)  # Sleep for 2 hours

        except Exception as e:
            print(f" Fatal Error: {e}")
            print("Retrying in 2 hours...")
            await asyncio.sleep(7200)


# Run the async function
asyncio.run(fetch_full_tweets())
