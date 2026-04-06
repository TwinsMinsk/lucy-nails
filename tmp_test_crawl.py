from firecrawl import FirecrawlApp
import os
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), 'backend', '.env')
load_dotenv(dotenv_path)

app = FirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY"))

try:
    print("Trying app.crawl...")
    result = app.crawl(
        "https://example.com", 
        limit=1, 
        scrape_options={'formats': ['markdown']}
    )
    print(f"Result type: {type(result)}")
    print(f"Result: {result}")
except Exception as e:
    print(f"Error in app.crawl: {e}")
