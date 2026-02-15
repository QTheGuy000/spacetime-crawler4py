import re
from urllib.parse import urlparse, urljoin, urldefrag
from bs4 import BeautifulSoup
import nltk
nltk.download('stopwords')
from nltk.corpus import stopwords
from collections import Counter
unique_pages = set()

REJECTED_LOGS = "rejected_urls.log"

from word_stats import update_from_html
def scraper(url, resp):
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content

    #Stores all hyperlinks extracted from the page
    out_links = []

    #Step 1: validate response
    #if resp is missing or has no raw_response, there is no page to parse
    if resp is None or resp.raw_response is None:
        return out_links

    #Allow 200-399 so redirects don't stop the crawl
    if resp.status < 200 or resp.status >= 400:
        return out_links

    #save raw response URL
    raw = resp.raw_response

    #Step 2: check if content exists
    content = raw.content
    if not content:
        return out_links

    #Treat extremely tiny bodies as "no data"
    if len(content) < 100:
        return out_links

    #Step 3: check if content type is HTML
    ctype = (raw.headers.get("Content-Type") or "").lower()
    if "text/html" not in ctype:
        return out_links

    #Step 4: parse HTML and extract links
    soup = BeautifulSoup(content, "lxml")

    #Use final downloaded URL as base (handles redirects)
    base = raw.url or url

    # Update word stats only for pages we consider valid for this crawl
    if is_valid(base):
        update_from_html(base, content)

    #update word stats
    update_from_html(base, content)

    #Avoid duplicates on the same page
    seen_on_page = set()

    #Loop through all anchor tags with href
    for a in soup.find_all("a", href = True):
        #Get the href and clean
        href = (a.get("href") or "").strip()
        if not href:
            continue

        #Convert relative URLs into absolute URLs
        abs_url = urljoin(base, href)

        #Remove fragments (#...) so they dont count as different pages
        abs_url, _ = urldefrag(abs_url)

        #Lowercase hostname only (keep the path)
        p = urlparse(abs_url)
        if p.netloc:
            abs_url = p._replace(netloc=p.netloc.lower()).geturl()

        #Only add the URL once per page
        if abs_url not in seen_on_page:
            seen_on_page.add(abs_url)
            out_links.append(abs_url)
    #return the list
    return out_links

def is_valid(url):
    # Decide whether to crawl this url or not.
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)
        path = (parsed.path or "").lower()
        #only allow http/https
        if parsed.scheme not in set(["http", "https"]):
            reject_and_log(url, "not http https")
            return False

        #only allow the required domains
        netloc = parsed.netloc.lower()
        allowed = ["ics.uci.edu", "cs.uci.edu", "informatics.uci.edu", "stat.uci.edu"]
        if not any(netloc == d or netloc.endswith("." + d) for d in allowed):
            reject_and_log(url, "not in allowed domain")
            return False

        #Avoid pages that have a bunch of dates at the end
        if re.search(r"/\d{4}-\d{2}-\d{2}", path):
            reject_and_log(url, "date sequence")
            return False
        
        #Avoid lengthy urls
        segments_num = [s for s in parsed.path.split("/") if s]
        if len(segments_num) > 8:
            reject_and_log(url, "too deep path")
            return False
        
        #avoid extremely long URLS
        if len(url) > 300:
            reject_and_log(url, "len > 300")
            return False
    
        #avoid session ids
        lower_url = url.lower()
        if "jsessionid" in lower_url or "sessionid" in lower_url:
            reject_and_log(url, "jsessionid sessionid lower url")
            return False
    
        #avoid directory listing sort traps
        if "c=" in parsed.query.lower() and "o=" in parsed.query.lower():
            reject_and_log(url, "c= o=")
            return False

        q = (parsed.query or "").lower()

        #WordPress calendar + login traps
        if "isg.ics.uci.edu" in netloc:
            #block login/admin 
            if path.startswith("/wp-login.php") or path.startswith("/wp-admin"):
                reject_and_log(url, "login or admin")
                return False

            #block calendar params
            bad_params = [
                "outlook-ical", "ical",          # export
                "eventdisplay",                  # past/list views
                "tribe-bar-date", "tribebar-date",# date pagination
                "paged", "page", "offset"        # generic paging
            ]
            if any(bp in q for bp in bad_params):
                reject_and_log(url, "bad params")
                return False

            #block endless calendar pages but keep event pages
            if path.startswith("/events/tag/") or path.startswith("/events/category/"):
                reject_and_log(url, "events tag or category")
                return False
            if path.startswith("/events/list") or path.startswith("/events/month"):
                reject_and_log(url, "events list or month")
                return False
            #some pages are /events/tag/<tag>/<yyyy-mm>
            if re.search(r"^/events/tag/[^/]+/\d{4}-\d{2}/?$", path):
                reject_and_log(url, "events tag something else")
                return False

        #Gitlab traps
        if "gitlab.ics.uci.edu" in netloc:

            # reject any query string
            if parsed.query:
                reject_and_log(url, "parsed query")
                return False

            #block common infinite navigation sections
            bad_gitlab = ["/-/commit/", "/-/commits/", "/-/tree/", "/-/tags", "/-/compare",
                "/-/merge_requests", "/-/issues", "/-/pipelines", "/-/jobs",
                "/-/branches", "/-/project_members", "/-/activity", "/-/blob/"
            ]
            if any(b in path for b in bad_gitlab):
                reject_and_log(url, "bad gitlab")
                return False

            #block long hash tokens
            if re.search(r"/[0-9a-f]{32,}(/|$)", path):
                reject_and_log(url, "re search")
                return False

        #DokuWiki / wiki traps
        trap_params = [
            "do=", "idx=", "tab_files", "tab_details", "image=", "media=",
            "sectok=", "ns=", "rev=", "diff="
        ]
        if any(tp in q for tp in trap_params):
            reject_and_log(url, "trap_params")
            return False

        #calendar / paging / sort traps (endless page=1,2,3…)
        if re.search(r"(?:^|[&;])(page|p|start|offset)=\d{3,}(?:$|[&;])", q):
            reject_and_log(url, "page start offset")
            return False

        #repeated query keys (e.g., tab_details repeated, etc.)
        if parsed.query:
            keys = [kv.split("=", 1)[0].lower() for kv in re.split(r"[&;]", parsed.query) if kv.strip()]
            if len(keys) != len(set(keys)):
                reject_and_log(url, "repeated query keys")
                return False
        
        #avoid too many query parameters
        if parsed.query:
            parts = re.split(r"[&;]", parsed.query)
            if len([p for p in parts if p.strip()]) > 8:
                reject_and_log(url, "too many query parameters")
                return False
    
        #avoid repeated path segments
        segments = [s for s in parsed.path.lower().split("/") if s]
        count = {}
        for s in segments:
            count[s] = count.get(s, 0) + 1
            if count[s] >= 4:
                reject_and_log(url, "repeating path segments")
                return False

        # Block pagination, sorting, and filtering traps
        # These generate infinite URL variations with little/no new content
        q = parsed.query.lower()
        if any(k in q for k in ["page=", "offset=", "start=", "sort=", "filter=", "replytocom="]):
            reject_and_log(url, "pagination, sorting, filtering")
            return False

        # Block internal search result pages
        # Search pages endlessly generate new URLs with low information value
        path = parsed.path.lower()
        if "/search" in path:
            reject_and_log(url, "low information value")
            return False

        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz"
            + r"|txt|c|h|cpp|cc|py|java)$", 
            parsed.path.lower())
    
    except TypeError:
        print ("TypeError for ", parsed)
        raise
    

def reject_and_log(url, exp):
    with open(REJECTED_LOGS, "a", encoding="utf-8") as f:
        f.write(f"{url}\t{exp}\n")