import os
import sys

venv_site = os.path.join(os.path.dirname(__file__), '.venv', 'lib', 'python3.9', 'site-packages')
if os.path.exists(venv_site) and venv_site not in sys.path:
    sys.path.insert(0, venv_site)

from scraper.spiders.oliveyoung import OliveYoungSpider

spider = OliveYoungSpider()
prods = spider.discover_products(max_pages=1)
print(f"Total products fetched: {len(prods)}")
for p in prods[:5]:
    print("NAME:", p['name'])
    print("INCI STRING:", repr(p['inci_string']))
    print("-" * 40)
