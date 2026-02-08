import re
from urllib.parse import urlparse, urljoin, urldefrag
from bs4 import BeautifulSoup

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
    
    #Only process successful HTTP responses (code 200)
    if resp.status != 200:
        return out_links
    
    #save raw response URL
    raw = resp.raw_response
    
    #Step 2: check if content exists
    content = raw.content
    if not content:
        return out_links
    
    #Step 3: check if content type is HTML
    ctype = (raw.headers.get("Content-Type") or "").lower()
    if "text/html" not in ctype:
        return out_links
    
    #Step 4: parse HTML and extract links
    soup = BeautifulSoup(content, "lxml")
    
    #Use final downloaded URL as base
    base = raw.url or url
    
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
        if parsed.scheme not in set(["http", "https"]):
            return False
        netloc = parsed.netloc.lower()
        allowed_domains = ["ics.uci.edu", "cs.uci.edu", "informatics.uci.edu", "stat.uci.edu"]
        for domain in allowed_domains:
            if netloc.endswith(domain):
                break
        else:
            return False

        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

    except TypeError:
        print ("TypeError for ", parsed)
        raise
