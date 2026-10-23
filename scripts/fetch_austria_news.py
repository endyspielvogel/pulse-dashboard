#!/usr/bin/env python3
"""Collect one recent Austrian headline per publisher using public Google News RSS search."""
import datetime as dt
import email.utils
import json
import pathlib
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

SOURCES = [('ORF.at','orf.at'), ('Die Presse','diepresse.com'), ('DER STANDARD','derstandard.at'), ('HORIZONT','horizont.at'), ('medianet','medianet.at')]
HEADERS={'User-Agent':'Mozilla/5.0 (compatible; PULSE-News/1.0)'}

def fetch(source,domain):
    query=urllib.parse.quote('site:'+domain)
    url=f'https://news.google.com/rss/search?q={query}&hl=de&gl=AT&ceid=AT:de'
    request=urllib.request.Request(url,headers=HEADERS)
    with urllib.request.urlopen(request,timeout=22) as resp:
        root=ET.fromstring(resp.read())
    for item in root.findall('./channel/item'):
        title=(item.findtext('title') or '').strip()
        link=(item.findtext('link') or '').strip()
        published=(item.findtext('pubDate') or '').strip()
        if not title or not link:continue
        date=None
        try:date=email.utils.parsedate_to_datetime(published).astimezone(dt.timezone.utc).isoformat()
        except (TypeError,ValueError):pass
        return {'source':source,'title':title,'url':link,'published_at':date}
    return None

def main():
    path=pathlib.Path('data/austria_news.json')
    previous=[]
    if path.exists():
        try:previous=json.loads(path.read_text(encoding='utf-8')).get('articles',[])
        except (OSError,ValueError):pass
    articles=[]
    for source,domain in SOURCES:
        try:
            item=fetch(source,domain)
            if item:articles.append(item)
            else:print(f'No items: {source}')
        except Exception as exc:print(f'Fetch failed for {source}: {exc}')
        if not any(a['source']==source for a in articles):
            articles.extend(a for a in previous if a.get('source')==source) 
    if not articles:raise RuntimeError('No articles and no fallback data')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps({'fetched_at':dt.datetime.now(dt.timezone.utc).isoformat(),'articles':articles},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Saved {len(articles)} articles')
if __name__=='__main__':main()
