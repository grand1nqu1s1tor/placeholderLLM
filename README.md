# 📌 PlaceholderLLM

A lightweight, open-source project to experiment with **LLMs, data pipelines, and real-time processing**.

---

## **📌 Resources & Tools**
🔹 **LLM Learning Resources**
- [Applied LLMs Mastery 2024](https://areganti.notion.site/Applied-LLMs-Mastery-2024-562ddaa27791463e9a1286199325045c)
- [Building Multi-Index Advanced RAG Apps](https://medium.com/decodingml/build-multi-index-advanced-rag-apps-bd33d2f0ec5c)
- [Everything AI Agent](https://www.aiagenttoolkit.xyz/#llms)

🔹 **Scrapers & AI Tools**
- [LinkedIn Scraper](https://github.com/tomquirk/linkedin-api)
- [Twikit - Free Twitter Scraper](https://twikit.readthedocs.io/en/latest/twikit.html)

---

## **📌 Data Pipeline Overview**
- **Tweets are fetched using Twikit** and stored in **MongoDB**.
- **Change Data Capture (CDC) with MongoDB Change Streams** detects new tweets in real time.
- **Kafka queues process tweet data asynchronously** for scalable downstream processing.

🔹 **Storage Considerations**
- Each tweet document is approximately **1KB** in size.
- MongoDB **persists all data on disk** with optimized memory usage.
- Choosing my Embedding model is an important consideration : (https://openreview.net/pdf?id=zl3pfz4VCV)
- Finalizing BAAI/bge-small-en
- Had to use Replica Set setup for MongoDB since Watch Streams aren't supported on Standalone instance.

---

## **📌 Getting Started**
### **1️⃣ Clone the Repository**
```bash
git clone https://github.com/your-username/PlaceholderLLM.git
cd PlaceholderLLM
![Screenshot 2025-02-06 at 12.22.16 PM.png](..%2F..%2F..%2F..%2Fvar%2Ffolders%2Fm4%2Fctrfwylx5_l_ytbflnt1j5dw0000gn%2FT%2FTemporaryItems%2FNSIRD_screencaptureui_lE3C9i%2FScreenshot%202025-02-06%20at%2012.22.16%E2%80%AFPM.png)