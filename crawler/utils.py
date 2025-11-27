""" Utility functions: normalize_url, RobotsCache, DomainDelay """ 
from urllib.parse import urljoin, urlparse, urldefrag 
import urllib.robotparser 
import threading 
import time

def normalize_url(base_url, link): 
    if not link: 
        return None 
    joined = urljoin(base_url, link) 
    no_frag, _ = urldefrag(joined) 
    parsed = urlparse(no_frag) 
    if parsed.scheme not in ("http", "https"): 
        return None 
    netloc = parsed.hostname 
    if parsed.port: 
        if (parsed.scheme == "http" and parsed.port != 80) or (parsed.scheme == "https" and parsed.port != 443): 
            netloc = f"{parsed.hostname}:{parsed.port}" 
    normalized = parsed._replace(netloc=netloc).geturl() 
    return normalized

class RobotsCache: 
    def __init__(self): 
        self.cache = {} 
        self.lock = threading.Lock()

    def can_fetch(self, user_agent, url):
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.hostname}"
        with self.lock:
            rp = self.cache.get(base)
            if not rp:
                rp = urllib.robotparser.RobotFileParser()
                try:
                    rp.set_url(urljoin(base, "/robots.txt"))
                    rp.read()
                except Exception:
                    rp = None
                self.cache[base] = rp
            if rp is None:
                return True
            return rp.can_fetch(user_agent, url)

class DomainDelay: 
    def __init__(self, delay=1.0): 
        self.delay = delay 
        self.last_access = {} 
        self.lock = threading.Lock()

    def wait(self, url):
        parsed = urlparse(url)
        domain = parsed.netloc
        with self.lock:
            last = self.last_access.get(domain)
            now = time.time()
            if last:
                elapsed = now - last
                if elapsed < self.delay:
                    time.sleep(self.delay - elapsed)
            self.last_access[domain] = time.time()
