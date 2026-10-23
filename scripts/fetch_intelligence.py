#!/usr/bin/env python3
"""Collect publicly available Google News RSS headlines for PULSE V5."""
import datetime as dt
import json
import pathlib
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'intelligence.json'
now = dt.datetime.now(dt.timezone.utc).isoformat()
try:
    previous = json.loads(OUT.read_text(encoding='utf-8'))
except (OSError, ValueError):
    previous = {}

queries = {
    'brands': {
        'McDonald’s': '"McDonald’s" OR "McDonalds"',
        'Burger King': '"Burger King"',
        'Omnicom': '"Omnicom" advertising',
        'Mercedes-Benz': '"Mercedes-Benz"',
        'Nvidia': '"Nvidia"',
    },
    'topics': {
        'Wirtschaft': 'Wirtschaft Börse Unternehmen',
        'Werbung & Marketing': 'Werbung Marketing Agenturen',
        'Technologie & KI': 'Künstliche Intelligenz Technologie',
        'Meine Aktien': 'Omnicom OR McDonald’s OR Nvidia OR Mercedes-Benz OR "British American Tobacco"',
    },
}
result = {'fetched_at': now, 'brands': {}, 'topics': {}}
count = 0
for category, entries in queries.items():
    for key, query in entries.items():
        try:
            params = urllib.parse.urlencode({'q': query + ' when:2d', 'hl': 'de', 'gl': 'AT', 'ceid': 'AT:de'})
            url = 'https://news.google.com/rss/search?' + params
            request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 PULSE Dashboard', 'Accept': 'application/rss+xml,application/xml'})
            with urllib.request.urlopen(request, timeout=20) as response:
                xml = response.read()
            root = ET.fromstring(xml)
            items = []
            for node in root.findall('./channel/item')[:8]:
                title = (node.findtext('title') or '').strip()
                link = (node.findtext('link') or '').strip()
                published = (node.findtext('pubDate') or '').strip()
                if title and link and link.startswith('https://'):
                    items.append({'title': title, 'url': link, 'published': published})
            if not items:
                raise ValueError('no headlines')
            result[category][key] = items
            count += 1
            print(category, key, len(items))
        except Exception as exc:
            print('Fetch failed:', category, key, exc)
            result[category][key] = previous.get(category, {}).get(key, [])
if not count and not any(result[c][k] for c in result if c in ('brands', 'topics') for k in result[c]):
    raise SystemExit('No news data available; retaining previous JSON')
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
