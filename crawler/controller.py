""" Controller that starts/stops workers and exposes stats """ 

import logging
from urllib.parse import urlparse

from db import init_db, add_url_if_new
from utils import RobotsCache, DomainDelay
from worker import CrawlerWorker

class CrawlerController:
    def __init__(self, db_file='crawler.db', num_workers=6, max_depth=2, per_domain_delay=1.0, same_domain=True):
        self.db_file = db_file
        self.num_workers = num_workers
        self.max_depth = max_depth
        self.db_conn = init_db(self.db_file)
        self.robots = RobotsCache()
        self.domain_delay = DomainDelay(delay=per_domain_delay)
        self.workers = []

        # same-domain configuration
        self.same_domain = same_domain
        # set of allowed hostnames (netloc without port)
        self.allowed_domains = set()

    def add_seed(self, url, depth=0):
        # register allowed domain for same-domain mode
        if self.same_domain:
            parsed = urlparse(url)
            if parsed.hostname:
                self.allowed_domains.add(parsed.hostname.lower())
        add_url_if_new(self.db_conn, url, depth)

    def start(self):
        for i in range(self.num_workers):
            w = CrawlerWorker(
                i+1,
                self.db_file,
                self.robots,
                self.domain_delay,
                max_depth=self.max_depth,
                same_domain=self.same_domain,
                allowed_domains=self.allowed_domains
            )
            w.start()
            self.workers.append(w)
        logging.info("Crawler started with %d workers (same_domain=%s)", self.num_workers, self.same_domain)

    def stop(self):
        logging.info("Stopping crawler...")
        for w in self.workers:
            w.stop()
        for w in self.workers:
            w.join(timeout=2)
        try:
            self.db_conn.close()
        except:
            pass
        logging.info("Stopped.")

    def stats(self):
        cur = self.db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM frontier WHERE status='pending'")
        pending = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM frontier WHERE status='in_progress'")
        in_progress = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM frontier WHERE status='done'")
        done = cur.fetchone()[0]
        return {"pending": pending, "in_progress": in_progress, "done": done}
