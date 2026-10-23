#!/usr/bin/env python3
"""Download Google Trending Now RSS for AT and US into a static JSON file."""
import datetime as dt
import json
import pathlib
import urllib.request
import xml.etree.ElementTree as ET

OUT = pathlib.Path(__file__).resolve().parents[1] / 'data' / 'trends.json'
NAMESPACE = '{https://trends.google.com/trending/rss}'
now = dt.datetime.now(dt.timezone.utc).isoformat()
existing = {}
if OUT.exists():
    try:
        existing = json.loads(OUT.read_text(encoding='utf-8'))
    except (ValueError, OSError):
        pass
countries = dict(existing.get('countries', {}))
successes = 0
for geo in ('AT', 'US'):
    try:
        url = 'https://trends.google.com/trending/rss?geo=' + geo
        request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; PULSE-Dashboard/1.0)', 'Accept': 'application/rss+xml, application/xml, text/xml'})
        with urllib.request.urlopen(request, timeout=25) as response:
            xml = response.read()
        root = ET.fromstring(xml)
        items = []
        for item in root.findall('./channel/item'):
            title = (item.findtext('title') or '').strip()
            volume = (item.findtext(NAMESPACE + 'approx_traffic') or '').strip()
            if title:
                items.append({'title': title, 'volume': volume})
            if len(items) == 10:
                break
        if not items:
            raise ValueError('Empty RSS feed')
        countries[geo] = items
        successes += 1
        print(f'{geo}: {len(items)} trends')
    except Exception as exc:
        print(f'{geo}: fetch failed: {exc}; retaining last successful data')
if successes == 0:
    raise SystemExit('No fresh RSS data; previous file retained')
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({'fetched_at': now, 'countries': countries}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
