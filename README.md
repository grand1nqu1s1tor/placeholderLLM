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

---

## **📌 Getting Started**
### **1️⃣ Clone the Repository**
```bash
git clone https://github.com/your-username/PlaceholderLLM.git
cd PlaceholderLLM
