from collections import Counter, defaultdict
import threading
from threading import Lock
from bs4 import BeautifulSoup
from tokenizer import tokenize_text
from urllib.parse import urldefrag, urlparse


STOP_WORDS = {
    "a","an","and","are","as","at","be","by","for","from","has","he","in","is","it",
    "its","of","on","that","the","to","was","were","will","with","you","your","i",
    "we","they","them","this","these","those","or","not","but","about","into","than",
    "then","there","here","when","where","who","what","why","how","can","could",
    "should","would","do","does","did"
}

_counter = Counter()
_lock = Lock()
unique_pages = set()
subdomains_count = defaultdict(int)
subdomains_lock = threading.Lock()

longest_page_url = None
longest_page_word_count = 0


def update_from_html(url, html_bytes):
    global longest_page_url
    global longest_page_word_count
    global unique_pages

    if not html_bytes:
        return

    soup = BeautifulSoup(html_bytes, "lxml")

    # Remove scripts/styles
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)
    tokens = tokenize_text(text)
    url_defrag = urldefrag(url)[0]
    if url_defrag not in unique_pages:
        unique_pages.add(url_defrag)

        
        netloc = urlparse(url).netloc.lower()
        if netloc.endswith("uci.edu"):
            with subdomains_lock:
                subdomains_count[netloc] += 1

    # Filter stopwords
    filtered = [t for t in tokens if t not in STOP_WORDS and len(t) > 1]

    if not filtered:
        return

    with _lock:
        _counter.update(filtered)

        if len(filtered) > longest_page_word_count:
            longest_page_word_count = len(filtered)
            longest_page_url = url



def write_report():
    print("\n===== REPORT =====")
    print(f"Number of unique pages: {len(unique_pages)}")
    print(f"Longest page: {longest_page_url}")
    print(f"Word count: {longest_page_word_count}")

    print("\nTop 50 words:")
    for word, count in _counter.most_common(50):
        print(f"{word}\t{count}")

    print("\nSubdomains:")
    for sd in sorted(subdomains_count.keys()):
        print(f"{sd}, {subdomains_count[sd]}")
