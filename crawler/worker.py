# worker.py
import threading
import logging
import requests
from bs4 import BeautifulSoup
from db import claim_next_url, add_url_if_new, mark_done, mark_failed, get_page_by_hash, save_page_metadata
from utils import normalize_url, compute_hash, extract_title_meta
import time
from urllib.parse import urlparse
import os

USER_AGENT = "UniversityCrawler/1.0 (+https://example.edu/)"
REQUEST_TIMEOUT = 10
MAX_RETRIES = 2

# Ensure data directory exists
DATA_DIR = os.path.join("data", "pages")
os.makedirs(DATA_DIR, exist_ok=True)

class CrawlerWorker(threading.Thread):
    def __init__(self, id, db_file, robots, domain_delay, max_depth=2, same_domain=True, allowed_domains=None):
        super().__init__(daemon=True)
        self.id = id
        # each worker keeps its own DB connection
        import sqlite3
        self.db_conn = sqlite3.connect(db_file, check_same_thread=False)
        self.robots = robots
        self.domain_delay = domain_delay
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.running = True
        self.max_depth = max_depth

        # same-domain enforcement
        self.same_domain = same_domain
        # allowed_domains is a set of hostnames (lowercased)
        self.allowed_domains = set(d.lower() for d in (allowed_domains or set()))

    def _is_allowed_domain(self, url):
        if not self.same_domain:
            return True
        parsed = urlparse(url)
        hostname = parsed.hostname.lower() if parsed.hostname else None
        return hostname in self.allowed_domains

    def _store_or_link_page(self, url, content_bytes, status_code):
        """
        Compute hash, check for existing content; if new, write the file and store metadata.
        Returns the content_path used for this URL.
        """
        content_hash = compute_hash(content_bytes)
        # check if content hash already exists
        existing = get_page_by_hash(self.db_conn, content_hash)
        if existing:
            content_path = existing["content_path"]
            # create / update metadata entry for this URL that points to existing content_path
            title, meta_desc = extract_title_meta(content_bytes.decode('utf-8', errors='ignore'))
            save_page_metadata(self.db_conn, url, content_path, content_hash, title, meta_desc, status_code)
            return content_path, content_hash, False  # False indicates not newly written
        # otherwise write file
        filename = f"{content_hash}.html"
        content_path = os.path.join(DATA_DIR, filename)
        try:
            with open(content_path, "wb") as fh:
                fh.write(content_bytes)
        except Exception as e:
            logging.warning(f"Worker-{self.id} failed to write page file {content_path}: {e}")
            content_path = None
        title, meta_desc = extract_title_meta(content_bytes.decode('utf-8', errors='ignore'))
        save_page_metadata(self.db_conn, url, content_path, content_hash, title, meta_desc, status_code)
        return content_path, content_hash, True  # True indicates new file written

    def run(self):
        logging.info(f"Worker-{self.id} started")
        while self.running:
            job = claim_next_url(self.db_conn)
            if not job:
                time.sleep(0.5)
                continue

            url = job["url"]
            depth = job["depth"]
            logging.info(f"Worker-{self.id} claimed: {url} (depth {depth})")
            try:
                if not self.robots.can_fetch(USER_AGENT, url):
                    logging.info(f"Worker-{self.id} blocked by robots.txt: {url}")
                    mark_failed(self.db_conn, url)
                    continue

                self.domain_delay.wait(url)

                try:
                    resp = self.session.get(url, timeout=REQUEST_TIMEOUT)
                except Exception as e:
                    logging.warning(f"Worker-{self.id} error fetching {url}: {e}")
                    if job["retries"] >= MAX_RETRIES:
                        mark_failed(self.db_conn, url)
                    else:
                        cur = self.db_conn.cursor()
                        cur.execute("UPDATE frontier SET status='pending' WHERE url=?", (url,))
                        self.db_conn.commit()
                    continue

                status_code = resp.status_code
                # Save visited + frontier state
                mark_done(self.db_conn, url, status_code)
                logging.info(f"Worker-{self.id} fetched {url} [{status_code}]")

                content_type = resp.headers.get("Content-Type", "")
                if "text/html" in content_type:
                    # dedup + save page content & metadata
                    content_path, content_hash, was_new = self._store_or_link_page(url, resp.content, status_code)
                    logging.info(f"Worker-{self.id} saved page [{content_hash}] new={was_new} -> {content_path}")

                # parse links if HTML and depth < max_depth
                if "text/html" in content_type and depth < self.max_depth:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for a in soup.find_all("a", href=True):
                        new = normalize_url(url, a["href"])
                        if new:
                            # enforce same-domain if enabled
                            if self.same_domain and not self._is_allowed_domain(new):
                                logging.debug(f"Worker-{self.id} skipping out-of-domain URL: {new}")
                                continue
                            add_url_if_new(self.db_conn, new, depth + 1)

            except Exception as e:
                logging.exception(f"Worker-{self.id} unexpected error on {url}: {e}")
                mark_failed(self.db_conn, url)

    def stop(self):
        self.running = False
        try:
            self.session.close()
        except:
            pass
        try:
            self.db_conn.close()
        except:
            pass
