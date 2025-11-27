""" Main entrypoint. Usage: python main.py <seed_url> [num_workers] [max_depth] """ 
import time 
import logging 
import sys 
from controller import CrawlerController

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def main(): 
    num_workers = int(sys.argv[2]) if len(sys.argv) > 2 else 6 
    max_depth = int(sys.argv[3]) if len(sys.argv) > 3 else 2 
    seed = sys.argv[1] if len(sys.argv) > 1 else "https://example.com/"

    controller = CrawlerController(num_workers=num_workers, max_depth=max_depth)

    # seed DB if empty
    cur = controller.db_conn.cursor()
    cur.execute("SELECT COUNT(*) FROM frontier")
    if cur.fetchone()[0] == 0:
        controller.add_seed(seed)
        logging.info("Added seed: %s", seed)

    try:
        controller.start()
        while True:
            time.sleep(5)
            s = controller.stats()
            logging.info("Stats: pending=%d in_progress=%d done=%d", s["pending"], s["in_progress"], s["done"]) 
    except KeyboardInterrupt:
        logging.info("Caught KeyboardInterrupt, shutting down...")
        controller.stop()

if __name__ == '__main__': 
    main()