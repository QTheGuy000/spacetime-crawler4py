from threading import Thread
from threading import Thread, Lock
from inspect import getsource
from utils.download import download
from utils import get_logger
import scraper
import time

TOTAL_CRAWLED = 0
TOTAL_CRAWLED_LOCK = Lock()
CRAWLED_MAX = 20

class Worker(Thread):
    def __init__(self, worker_id, config, frontier):
        self.logger = get_logger(f"Worker-{worker_id}", "Worker")
        self.config = config
        self.frontier = frontier
        # basic check for requests in scraper
        assert {getsource(scraper).find(req) for req in {"from requests import", "import requests"}} == {-1}, "Do not use requests in scraper.py"
        assert {getsource(scraper).find(req) for req in {"from urllib.request import", "import urllib.request"}} == {-1}, "Do not use urllib.request in scraper.py"
        super().__init__(daemon=True)
        
    def run(self):
        global TOTAL_CRAWLED
        while True:
            with TOTAL_CRAWLED_LOCK:
                if TOTAL_CRAWLED >= CRAWLED_MAX:
                    self.logger.info(f"Reached {CRAWLED_MAX} total pages. Stopping Crawler.")
                    break
            tbd_url = self.frontier.get_tbd_url()
            if not tbd_url:
                self.logger.info("Frontier is empty. Stopping Crawler.")
                break
            resp = download(tbd_url, self.config, self.logger)
            self.logger.info(
                f"Downloaded {tbd_url}, status <{resp.status}>, "
                f"using cache {self.config.cache_server}.")
            scraped_urls = scraper.scraper(tbd_url, resp)
            for scraped_url in scraped_urls:
                self.frontier.add_url(scraped_url)
            self.frontier.mark_url_complete(tbd_url)
            with TOTAL_CRAWLED_LOCK:
                TOTAL_CRAWLED += 1
                self.logger.info(f"Progress: {TOTAL_CRAWLED}/{CRAWLED_MAX} pages crawled.")
            time.sleep(self.config.time_delay)
