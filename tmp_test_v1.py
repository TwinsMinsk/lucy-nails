from firecrawl import FirecrawlApp
import os
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), 'backend', '.env')
load_dotenv(dotenv_path)

app = FirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY"))

try:
    print("Checking app.v1.crawl_url with minimal params...")
    # пробуем вызвать без scrape_options для теста
    result = app.v1.crawl_url(
        url="https://example.com",
        limit=1
    )
    print(f"Result type: {type(result)}")
    print(f"Result: {result}")
except Exception as e:
    import traceback
    print(f"Error in app.v1.crawl_url: {e}")
    traceback.print_exc()
