"""Test payment link generation with demo_mode."""
import requests
import urllib.parse

r = requests.post(
    "http://localhost:8000/api/payments/link",
    json={"course_id": "default", "tariff": "self"},
)
print(f"Status: {r.status_code}")
data = r.json()
url = data.get("url", "")
print(f"URL: {url}")

# Parse and show params
parsed = urllib.parse.urlparse(url)
params = urllib.parse.parse_qs(parsed.query)
print("\nParsed params:")
for k, v in sorted(params.items()):
    print(f"  {k}: {v[0]}")
