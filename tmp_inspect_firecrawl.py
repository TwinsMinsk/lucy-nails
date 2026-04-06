import firecrawl
print(f"Firecrawl version: {firecrawl.__version__ if hasattr(firecrawl, '__version__') else 'unknown'}")
print(f"Dir(firecrawl): {dir(firecrawl)}")

try:
    from firecrawl import FirecrawlApp
    print(f"Dir(FirecrawlApp): {dir(FirecrawlApp)}")
    app = FirecrawlApp(api_key="test")
    print(f"Methods of FirecrawlApp instance: {[m for m in dir(app) if not m.startswith('_')]}")
except Exception as e:
    print(f"Error importing FirecrawlApp: {e}")

try:
    from firecrawl import Firecrawl
    print(f"Dir(Firecrawl): {dir(Firecrawl)}")
    f = Firecrawl(api_key="test")
    print(f"Methods of Firecrawl instance: {[m for m in dir(f) if not m.startswith('_')]}")
except Exception as e:
    print(f"Error importing Firecrawl: {e}")
