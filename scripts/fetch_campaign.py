#!/usr/bin/env python3
"""Campaign UK article discovery via Google News RSS (no paid API)."""
import datetime as dt
import email.utils
import html
import json
import pathlib
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data' / 'campaign.json'
QUERIES = [
    'site:campaignlive.co.uk "ad of the day"',
    'site:campaignlive.co.uk "the work"',
    'site:campaignlive.co.uk',
]

def clean(value):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]*>', ' ', value or ''))).strip()

def retrieve(query):
    url = 'https://news.google.com/rss/search?' + urllib.parse.urlencode({
        'q': query, 'hl': 'en-GB', 'gl': 'GB', 'ceid': 'GB:en'
    })
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (PULSE dashboard)'})
    with urllib.request.urlopen(req, timeout=22) as response:
        xml = response.read()
    root = ET.fromstring(xml)
    articles = []
    for item in root.findall('./channel/item'):
        source = item.find('source')
        publisher = (source.text or '') if source is not None else ''
        source_url = (source.attrib.get('url', '') if source is not None else '')
        if 'campaign' not in publisher.lower() and 'campaignlive.co.uk' not in source_url.lower():
            continue
        title = clean(item.findtext('title'))
        title = re.sub(r'\s+[-–]\s+Campaign(?: UK)?$', '', title, flags=re.I)
        link = (item.findtext('link') or '').strip()
        date_raw = item.findtext('pubDate') or ''
        try:
            date = email.utils.parsedate_to_datetime(date_raw)
            date_iso = date.isoformat()
            date_label = date.strftime('%d.%m.%Y')
        except (TypeError, ValueError):
            date_iso = ''
            date_label = date_raw
        if title and link:
            articles.append({'title': title, 'url': link, 'published': date_label,
                             'published_iso': date_iso, 'description': '', 'source': 'Campaign UK'})
    return articles

def main():
    seen = set()
    articles = []
    for query in QUERIES:
        try:
            found = retrieve(query)
            print(f'{query}: {len(found)} articles')
        except Exception as exc:
            print(f'Warning: {query}: {exc}')
            continue
        for article in found:
            key = article['title'].casefold()
            if key not in seen:
                seen.add(key)
                articles.append(article)
    if not articles:
        if OUTPUT.exists():
            print('No new items: retaining previous campaign.json')
            return
        raise RuntimeError('No Campaign UK articles found in Google News RSS')
    articles.sort(key=lambda a: a['published_iso'], reverse=True)
    payload = {'fetched_at': dt.datetime.now(dt.timezone.utc).isoformat(),
               'source': 'Google News RSS, Campaign UK', 'articles': articles[:12]}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Saved {len(payload["articles"])} articles to {OUTPUT}')

if __name__ == '__main__':
    main()
