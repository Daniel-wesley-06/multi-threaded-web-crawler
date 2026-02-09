# 🕷️ Multi-Threaded Web Crawler (Python)

A fully functional multi-threaded web crawler with:
- Persistent crawling state (resume support)
- SQLite-based frontier & visited tables
- Robots.txt compliance
- Per-domain politeness delay
- Thread-safe URL claiming
- Configurable thread count and crawl depth

## 🚀 Features

- Multi-threaded crawling
- Automatic resume even after crash
- HTML parsing with BeautifulSoup
- URL normalization
- Retries + failure handling
- Clean modular architecture
- CLI usage

## 📦 Installation

```bash
pip install -r requirements.txt
```

## ▶️ Usage

```bash
python -m crawler.main https://example.com 6 2
```

### Args:

- Seed URL
- Number of worker threads
- Max depth

## 🧱 Project Structure

```
crawler/
  main.py
  controller.py
  worker.py
  db.py
  utils.py
```

## 🧠 Resume Support

The crawler stores:
- Frontier (pending, in-progress, done, failed)
- Visited pages

Simply restart the program; it continues crawling from where it left off.

### Persisted pages and deduplication

Fetched HTML pages are saved under `data/pages/` with filenames equal to their SHA-256 content hash (e.g. `data/pages/<hash>.html`).  
The crawler stores page metadata in the `pages` table (url, content_path, content_hash, title, meta_description, fetched_at, status_code).  
If two URLs produce identical content bytes the crawler detects the duplicate via content hash and does **not** store the payload twice — it links the new URL to the existing content file to save space.
