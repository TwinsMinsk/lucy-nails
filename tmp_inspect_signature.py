from firecrawl import FirecrawlApp
import inspect

app = FirecrawlApp(api_key="test")
print(f"Signature of app.crawl: {inspect.signature(app.crawl)}")
try:
    print(f"Signature of app.v1.crawl_url: {inspect.signature(app.v1.crawl_url) if hasattr(app, 'v1') and hasattr(app.v1, 'crawl_url') else 'N/A'}")
except Exception as e:
    print(f"Error checking app.v1.crawl_url: {e}")
