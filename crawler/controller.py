
""" Controller that starts/stops workers and exposes stats """ 
import logging 
from db import init_db, add_url_if_new 
from utils import RobotsCache, DomainDelay 
from worker import CrawlerWorker

class CrawlerController: 
    def __init__(self, db_file='crawler.db', num_workers=6, max_depth=2, per_domain_delay=1.0): 
        self.db_file = db_file 
        self.num_workers = num_workers 
        self.max_depth = max_depth 
        self.db_conn = init_db(self.db_file) 
        self.robots = RobotsCache() 
        self.domain_delay = DomainDelay(delay=per_domain_delay) 
        self.workers = []

    def add_seed(self, url, depth=0):
        add_url_if_new(self.db_conn, url, depth)

    def start(self):
        for i in range(self.num_workers):
            w = CrawlerWorker(i+1, self.db_file, self.robots, self.domain_delay, max_depth=self.max_depth)
            w.start()
            self.workers.append(w)
        logging.info("Crawler started with %d workers", self.num_workers)

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
