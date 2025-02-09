# 📌 PlaceholderLLM

A lightweight, open-source project to experiment with **LLMs, data pipelines, and real-time processing**.

---

## **📌 Resources & Tools**

🔹 **LLM Learning Resources**

- [A curated list by a creator](https://areganti.notion.site/Applied-LLMs-Mastery-2024-562ddaa27791463e9a1286199325045c)
- [Referred this for structure](https://medium.com/decodingml/build-multi-index-advanced-rag-apps-bd33d2f0ec5c)
- [The best place where a lot of mumbo jumbo happens](https://www.aiagenttoolkit.xyz/#llms)

🔹 **Scrapers & AI Tools**

- [LinkedIn Scraper to be used ITF](https://github.com/tomquirk/linkedin-api)
- [Twikit - Free Twitter Scraper](https://twikit.readthedocs.io/en/latest/twikit.html)

---

## **📌 Data Pipeline Overview**

- **Tweets are fetched using Twikit** and stored in **MongoDB**.
- **Change Data Capture (CDC) with MongoDB Change Streams** detects new tweets in real time.
- **Kafka queues process tweet data asynchronously** for scalable downstream processing.

🔹 **Design Considerations**

- Each tweet document is approximately **1KB** in size.
- MongoDB **persists all data on disk** with optimized memory usage.
- Choosing my Embedding model is an important consideration : (https://openreview.net/pdf?id=zl3pfz4VCV)
- Finalizing BAAI/bge-small-en
- Had to use Replica Set setup for MongoDB since Watch Streams aren't supported on Standalone instance.
- Reduced Qdrant Indexing Threshold
- Lowered indexing_threshold to 1 to ensure immediate indexing of vectors instead of waiting for bulk inserts.
  Configured the collection (tweet_embeddings) with 384-dimensional vectors

---

Free Github Models : ( https://github.com/marketplace/models?WT.mc_id=academic-105485-koreyst)

### **1️⃣ Clone the Repository**

```bash
git clone https://github.com/your-username/PlaceholderLLM.git