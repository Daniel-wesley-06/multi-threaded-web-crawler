🕷️ Multi-Threaded Web Crawler (Python)

A fully functional multi-threaded web crawler with:
Persistent crawling state (resume support)
SQLite-based frontier & visited tables
Robots.txt compliance
Per-domain politeness delay
Thread-safe URL claiming
Configurable thread count and crawl depth

🚀 Features

Multi-threaded crawling
Automatic resume even after crash
HTML parsing with BeautifulSoup
URL normalization
Retries + failure handling
Clean modular architecture
CLI usage

📦 Installation

pip install -r requirements.txt

▶️ Usage
python -m crawler.main https://example.com 6 2

Args:

Seed URL
Number of worker threads
Max depth

🧱 Project Structure
crawler/
  main.py
  controller.py
  worker.py
  db.py
  utils.py

🧠 Resume Support

The crawler stores:
Frontier (pending, in-progress, done, failed)
Visited pages

Simply restart the program; it continues crawling from where it left off.