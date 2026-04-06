from firecrawl import FirecrawlApp
import inspect

app = FirecrawlApp(api_key="test")
print(f"Signature of app.crawl: {inspect.signature(app.crawl)}")
