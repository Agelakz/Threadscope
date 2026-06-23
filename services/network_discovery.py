"""
Network Discovery Tool for Threads

Captures all network traffic from Threads web app to discover endpoints.

DO NOT USE FOR:
- commenting, posting, liking
- follow/DM automation
- any content modification

ONLY USE FOR:
- endpoint discovery
- API analysis
- feed endpoint identification
"""

import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from urllib.parse import urlparse, parse_qs

from playwright.sync_api import sync_playwright, Page, Request, Response

logger = logging.getLogger(__name__)


@dataclass
class NetworkRequest:
    """Captured network request."""
    timestamp: str
    method: str
    url: str
    status: int
    resource_type: str
    content_type: str
    response_size: int
    headers: Dict[str, str] = field(default_factory=dict)
    graphql_data: Optional[Dict[str, Any]] = None
    matched_keywords: List[str] = field(default_factory=list)


@dataclass
class DiscoveryReport:
    """Discovery results summary."""
    total_requests: int = 0
    graphql_requests: int = 0
    api_requests: int = 0
    feed_candidates: int = 0
    search_candidates: int = 0
    profile_candidates: int = 0
    thread_candidates: int = 0
    interesting_requests: List[Dict[str, Any]] = field(default_factory=list)


class NetworkDiscovery:
    """
    Captures network traffic from Threads web app.
    
    Usage:
        discovery = NetworkDiscovery(session_cookies)
        discovery.capture(duration_seconds=30)
        discovery.save_results()
        report = discovery.generate_report()
    """
    
    THREADS_URL = "https://www.threads.com/"
    KEYWORDS = {
        "graphql": ["graphql", "query", "mutation"],
        "feed": ["feed", "timeline", "home", "barcelona"],
        "search": ["search", "q=", "query"],
        "profile": ["profile", "user", "username", "pk="],
        "thread": ["thread", "post", "item", "id="],
    }
    
    def __init__(self, cookies: Dict[str, str]):
        self.cookies = cookies
        self.requests: List[NetworkRequest] = []
        self.graphql_requests: List[NetworkRequest] = []
        self.graphql_dumps: List[Dict[str, Any]] = []
        self._page: Optional[Page] = None
        
    def _is_interesting_url(self, url: str) -> bool:
        """Check if URL contains interesting keywords and is not blacklisted."""
        url_lower = url.lower()
        
        # 1. Blacklist check (Garbage Filtering)
        blacklist = [
            "/ajax/bz",
            "/ajax/qm/",
            "/ajax/gen_204",
            "/ajax/bootloader-endpoint/",
            "logging",
            "telemetry",
            "tracking",
            "pixel"
        ]
        if any(b in url_lower for b in blacklist):
            return False
            
        # 2. Check keywords
        for category, keywords in self.KEYWORDS.items():
            if any(kw in url_lower for kw in keywords):
                return True
        return "api" in url_lower or "graphql" in url_lower
    
    def _extract_graphql_data(self, request: Request) -> Optional[Dict[str, Any]]:
        """Extract GraphQL query data from request."""
        try:
            post_data = request.post_data_buffer
            if post_data:
                data = json.loads(post_data)
                return {
                    "doc_id": data.get("doc_id"),
                    "variables": data.get("variables", {}),
                    "query": data.get("query", "")[:200] if data.get("query") else None,
                }
        except:
            pass
        
        parsed = urlparse(request.url)
        params = parse_qs(parsed.query)
        if "doc_id" in params:
            return {"doc_id": params["doc_id"][0]}
        
        return None
    
    def _categorize_request(self, url: str) -> List[str]:
        """Categorize request by keywords."""
        url_lower = url.lower()
        categories = []
        for category, keywords in self.KEYWORDS.items():
            if any(kw in url_lower for kw in keywords):
                categories.append(category)
        return categories
    
    def _get_resource_type(self, request: Request) -> str:
        """Determine resource type."""
        url = request.url.lower()
        if "graphql" in url:
            return "graphql"
        elif "api" in url:
            return "api"
        elif request.resource_type:
            return request.resource_type
        return "other"
    
    def _on_request(self, request: Request):
        """Handle captured request."""
        try:
            # 1. Ignore visual/media resources
            ignored_types = {"image", "media", "font", "stylesheet"}
            if request.resource_type in ignored_types:
                return

            timestamp = datetime.now().isoformat()
            url = request.url
            
            # 3. Dump XHR/Fetch
            if request.resource_type in {"xhr", "fetch"}:
                print(f"[DEBUG XHR/FETCH] {request.method} {url}")

            if not self._is_interesting_url(url):
                return
            
            graphql_data = self._extract_graphql_data(request) if request.method == "POST" else None
            matched_keywords = self._categorize_request(url)
            
            network_req = NetworkRequest(
                timestamp=timestamp,
                method=request.method,
                url=url,
                status=0,
                resource_type=self._get_resource_type(request),
                content_type="",
                response_size=0,
                headers=dict(request.headers),
                graphql_data=graphql_data,
                matched_keywords=matched_keywords
            )
            
            self.requests.append(network_req)
            
            if graphql_data or "graphql" in url.lower():
                self.graphql_requests.append(network_req)
                
        except Exception as e:
            logger.error(f"Request capture error: {e}")
    
    def _on_response(self, response: Response):
        """Handle captured response."""
        try:
            url = response.url
            for req in self.requests:
                if req.url == url:
                    req.status = response.status
                    req.response_size = response.body_size if hasattr(response, 'body_size') else 0
                    if response.headers:
                        ct = response.headers.get("content-type", "")
                        req.content_type = ct[:100] if ct else ""
                    break
                    
            # Extract GraphQL response payload
            if "/graphql/query" in url.lower():
                try:
                    req_post_data = response.request.post_data
                    payload = {}
                    if req_post_data:
                        try:
                            payload = json.loads(req_post_data)
                        except json.JSONDecodeError:
                            # Parse urlencoded payload
                            from urllib.parse import parse_qsl
                            payload = dict(parse_qsl(req_post_data))
                    doc_id = payload.get("doc_id")
                    friendly_name = payload.get("fb_api_req_friendly_name")
                    
                    try:
                        resp_json = response.json()
                    except Exception:
                        resp_json = {"error": "Failed to parse JSON or response not JSON"}
                        
                    self.graphql_dumps.append({
                        "url": url,
                        "doc_id": doc_id,
                        "friendly_name": friendly_name,
                        "request_payload": payload,
                        "response": resp_json
                    })
                except Exception as ex:
                    logger.warning(f"Failed to extract GraphQL payload/response: {ex}")
                    
        except Exception as e:
            logger.error(f"Response capture error: {e}")
    
    def capture(self, duration_seconds: int = 30) -> List[NetworkRequest]:
        """
        Capture network traffic for specified duration.
        
        Args:
            duration_seconds: How long to capture
            
        Returns:
            List of captured requests
        """
        logger.info("="*60)
        logger.info("NETWORK DISCOVERY - Starting Capture")
        logger.info("="*60)
        logger.info(f"Duration: {duration_seconds}s")
        logger.info(f"Cookies: {list(self.cookies.keys())}")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            self._page = context.new_page()
            
            # Inject cookies for all 3 Meta domains to survive cross-domain redirects
            playwright_cookies = []
            for name, value in self.cookies.items():
                playwright_cookies.append({"name": name, "value": value, "domain": ".instagram.com", "path": "/"})
                playwright_cookies.append({"name": name, "value": value, "domain": ".threads.net", "path": "/"})
                playwright_cookies.append({"name": name, "value": value, "domain": ".threads.com", "path": "/"})
            context.add_cookies(playwright_cookies)
            logger.info(f"Injected {len(self.cookies)} cookies x 3 domains = {len(playwright_cookies)} total cookie entries")
            
            self._page.on("request", self._on_request)
            self._page.on("response", self._on_response)
            
            logger.info("Navigating directly to https://www.threads.com/ (skip redirect)")
            self._page.goto(self.THREADS_URL, wait_until="networkidle", timeout=60000)
            
            logger.info("Waiting for feed elements to load...")
            try:
                # 3. Smart Waiting: Wait for article tags or pressable containers indicating a feed post
                self._page.wait_for_selector('article, [data-pressable-container="true"]', timeout=15000)
                logger.info("Feed elements detected!")
            except Exception as e:
                logger.warning("Could not find feed elements within timeout, proceeding anyway...")
                
            logger.info("Scrolling slowly to trigger pagination (GraphQL requests)...")
            for i in range(5):
                # Ensure we hit the bottom of the current loaded content to trigger lazy load
                self._page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                self._page.wait_for_timeout(2000)  # Wait 2 seconds for GraphQL to fire
            
            # Use remaining time if any
            elapsed_approx = 15000 + (5 * 2000)
            remaining_time = max(0, (duration_seconds * 1000) - elapsed_approx)
            if remaining_time > 0:
                logger.info(f"Continuing capture for remaining {remaining_time/1000}s...")
                self._page.wait_for_timeout(remaining_time)
            
            # Graceful Shutdown to prevent status 0
            logger.info("Waiting 3 seconds for pending GraphQL requests to complete...")
            self._page.wait_for_timeout(3000)
            
            browser.close()
        
        logger.info(f"Capture complete: {len(self.requests)} requests captured")
        return self.requests
    
    def save_results(self, 
                     network_file: str = "network_capture.json",
                     feed_file: str = "feed_candidates.json",
                     graphql_file: str = "graphql_candidates.json",
                     graphql_dump_file: str = "graphql_dump.json"):
        """Save capture results to JSON files."""
        
        logger.info(f"\n[SAVE] Saving to {network_file}")
        all_data = [asdict(r) for r in self.requests]
        with open(network_file, "w") as f:
            json.dump(all_data, f, indent=2)
        logger.info(f"[SAVE] Saved {len(all_data)} requests")
        
        logger.info(f"\n[SAVE] Saving to {feed_file}")
        feed_data = [asdict(r) for r in self.requests 
                     if any(kw in r.url.lower() for kw in ["feed", "timeline", "home", "barcelona", "api"])]
        with open(feed_file, "w") as f:
            json.dump(feed_data, f, indent=2)
        logger.info(f"[SAVE] Saved {len(feed_data)} feed candidates")
        
        logger.info(f"\n[SAVE] Saving to {graphql_file}")
        graphql_data = [asdict(r) for r in self.graphql_requests]
        with open(graphql_file, "w") as f:
            json.dump(graphql_data, f, indent=2)
        logger.info(f"[SAVE] Saved {len(graphql_data)} GraphQL requests")
        
        logger.info(f"\n[SAVE] Saving to {graphql_dump_file}")
        with open(graphql_dump_file, "w") as f:
            json.dump(self.graphql_dumps, f, indent=2)
        logger.info(f"[SAVE] Saved {len(self.graphql_dumps)} GraphQL dumps")
        
        return {
            "network_capture": network_file,
            "feed_candidates": feed_file,
            "graphql_candidates": graphql_file,
            "graphql_dump": graphql_dump_file
        }
    
    def generate_report(self, output_file: str = "NETWORK_DISCOVERY_REPORT.md") -> DiscoveryReport:
        """Generate discovery report."""
        
        feed_candidates = [r for r in self.requests 
                         if any(kw in r.url.lower() for kw in ["feed", "timeline", "home", "barcelona"])]
        search_candidates = [r for r in self.requests 
                            if any(kw in r.url.lower() for kw in ["search", "q=", "query"])]
        profile_candidates = [r for r in self.requests 
                             if any(kw in r.url.lower() for kw in ["profile", "user", "username", "pk="])]
        thread_candidates = [r for r in self.requests 
                            if any(kw in r.url.lower() for kw in ["thread", "post", "item", "id="])]
        api_requests = [r for r in self.requests if "api" in r.url.lower()]
        graphql_requests = self.graphql_requests
        
        def interest_score(r: NetworkRequest) -> float:
            score = 0
            url_lower = r.url.lower()
            
            # 2. Focus GraphQL / API
            if any(x in url_lower for x in ["/api/graphql", "/graphql/query", "/api/v1/"]):
                score += 20
            elif "graphql" in url_lower:
                score += 10
                
            if r.graphql_data:
                score += 5
            if any(kw in url_lower for kw in ["feed", "timeline", "home"]):
                score += 8
            if any(kw in url_lower for kw in ["search"]):
                score += 7
            if any(kw in url_lower for kw in ["profile"]):
                score += 6
            if r.status == 200:
                score += 3
            return score
        
        ranked = sorted(self.requests, key=interest_score, reverse=True)[:20]
        
        interesting = []
        for r in ranked:
            info = {
                "method": r.method,
                "url": r.url,
                "status": r.status,
                "type": r.resource_type,
                "matched_keywords": r.matched_keywords,
                "has_graphql_data": r.graphql_data is not None,
                "doc_id": r.graphql_data.get("doc_id") if r.graphql_data else None
            }
            interesting.append(info)
        
        report = DiscoveryReport(
            total_requests=len(self.requests),
            graphql_requests=len(graphql_requests),
            api_requests=len(api_requests),
            feed_candidates=len(feed_candidates),
            search_candidates=len(search_candidates),
            profile_candidates=len(profile_candidates),
            thread_candidates=len(thread_candidates),
            interesting_requests=interesting
        )
        
        logger.info(f"\n[REPORT] Generating {output_file}")
        
        md_content = f"""# Network Discovery Report

**Generated:** {datetime.now().isoformat()}

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| Total Requests Captured | {report.total_requests} |
| GraphQL Requests | {report.graphql_requests} |
| API Requests | {report.api_requests} |
| Feed Candidates | {report.feed_candidates} |
| Search Candidates | {report.search_candidates} |
| Profile Candidates | {report.profile_candidates} |
| Thread Candidates | {report.thread_candidates} |

---

## Top 20 Most Interesting Requests

| # | Method | URL | Status | Type | Keywords | Doc ID |
|---|--------|-----|--------|------|----------|--------|
"""
        
        for i, req in enumerate(interesting, 1):
            url_short = req["url"][:80] + "..." if len(req["url"]) > 80 else req["url"]
            keywords = ", ".join(req["matched_keywords"]) if req["matched_keywords"] else "-"
            doc_id = req.get("doc_id") or "-"
            md_content += f"| {i} | {req['method']} | {url_short} | {req['status']} | {req['type']} | {keywords} | {doc_id} |\n"
        
        md_content += f"""

---

## Feed Candidates (URLs)

"""
        for r in feed_candidates[:30]:
            md_content += f"- {r.method} {r.url}\n"
        
        md_content += f"""

---

## GraphQL Requests

"""
        for r in graphql_requests[:30]:
            doc_id = r.graphql_data.get("doc_id") if r.graphql_data else "?"
            md_content += f"- {r.method} doc_id={doc_id} → {r.url[:100]}\n"
        
        md_content += f"""

---

## Search Candidates

"""
        for r in search_candidates[:20]:
            md_content += f"- {r.method} {r.url[:150]}\n"
        
        md_content += f"""

---

## Next Steps

Based on this discovery:

1. **Home Feed**: Look for requests with `feed`, `timeline`, `barcelona` keywords
2. **Search**: Check requests with `search` or `query` params
3. **Profile**: Look for `pk=` or `user` in URLs
4. **Thread**: Check `thread`, `post`, `item` endpoints

Verify by testing these endpoints with curl_cffi session.
"""
        
        with open(output_file, "w") as f:
            f.write(md_content)
        
        logger.info(f"[REPORT] Saved to {output_file}")
        
        return report
    
    def print_summary(self, report: DiscoveryReport):
        """Print summary to console."""
        print("\n" + "="*60)
        print("NETWORK DISCOVERY SUMMARY")
        print("="*60)
        print(f"Total Requests:      {report.total_requests}")
        print(f"GraphQL Requests:     {report.graphql_requests}")
        print(f"API Requests:         {report.api_requests}")
        print(f"Feed Candidates:     {report.feed_candidates}")
        print(f"Search Candidates:   {report.search_candidates}")
        print(f"Profile Candidates:  {report.profile_candidates}")
        print(f"Thread Candidates:   {report.thread_candidates}")
        print("="*60)
        
        print("\n[TOP 5 MOST INTERESTING]")
        for i, req in enumerate(report.interesting_requests[:5], 1):
            print(f"\n{i}. {req['method']} {req['url'][:80]}...")
            print(f"   Status: {req['status']} | Type: {req['type']}")
            print(f"   Keywords: {', '.join(req['matched_keywords'])}")
            if req.get('doc_id'):
                print(f"   Doc ID: {req['doc_id']}")
        print("="*60)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    print("\n" + "="*60)
    print("NETWORK DISCOVERY TOOL")
    print("="*60)
    print("\nUsage:")
    print("  from services.network_discovery import NetworkDiscovery")
    print("  discovery = NetworkDiscovery(session_cookies)")
    print("  discovery.capture(duration_seconds=30)")
    print("  discovery.save_results()")
    print("  report = discovery.generate_report()")
    print("="*60)
