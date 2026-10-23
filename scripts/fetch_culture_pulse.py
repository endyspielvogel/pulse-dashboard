#!/usr/bin/env python3
"""Best-effort daily social/culture discovery. No API keys or fake trend rankings."""
import datetime, email.utils, html, json, os, random, re, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from pathlib import Path
TODAY=datetime.datetime.now(datetime.timezone.utc).date().isoformat()
UA={'User-Agent':'PULSE dashboard public culture discovery/1.0 (contact: github.com/endyspielvogel/pulse-dashboard)'}
def get(url):
 req=urllib.request.Request(url,headers=UA)
 with urllib.request.urlopen(req,timeout=16) as r:return r.read()
def rss(query,platform):
 url='https://news.google.com/rss/search?q='+urllib.parse.quote(query)+'&hl=en-US&gl=US&ceid=US:en'
 try:root=ET.fromstring(get(url))
 except Exception as e:print('RSS unavailable',platform,str(e));return []
 out=[]
 for item in root.findall('.//item')[:18]:
  title=html.unescape(item.findtext('title','')).strip();link=item.findtext('link','').strip()
  if not title or not link:continue
  out.append({'platform':platform,'title':title,'url':link,'image':'','link_type':'coverage','note':'Aktueller Trendbericht – Link führt zur Berichterstattung, nicht zwingend zum Originalclip'})
 return out
def reddit(sub,kind):
 try:
  data=json.loads(get('https://www.reddit.com/r/'+sub+'/hot.json?limit=60&raw_json=1'))
 except Exception as e:print('Reddit unavailable',sub,str(e));return []
 out=[]
 for child in data.get('data',{}).get('children',[]):
  p=child.get('data',{});title=p.get('title','');url=p.get('url_overridden_by_dest') or p.get('url') or ''
  if p.get('over_18') or p.get('stickied') or p.get('is_self') or not title:continue
  image=''
  try:image=html.unescape(p['preview']['images'][0]['source']['url'])
  except (KeyError,IndexError,TypeError):pass
  if not image and re.search(r'\.(?:jpg|jpeg|png|gif)(?:\?|$)',url,re.I):image=url
  if not image:continue
  permalink='https://www.reddit.com'+p.get('permalink','')
  out.append({'platform':'REDDIT / '+sub.upper(),'title':title,'url':permalink,'image':image,'link_type':'original','note':'Community-Beitrag · keine garantierte weltweite Viral-Rangliste'})
 return out
# Headlines from recent reporting are discovery leads, not verified original social clips.
social=[]
for platform,q in [('TIKTOK','TikTok viral video trend when:7d'),('INSTAGRAM REELS','Instagram Reels viral video trend when:7d'),('YOUTUBE SHORTS','YouTube Shorts viral video trend when:7d')]:
 choices=rss(q,platform)
 if choices:social.append(choices[int(TODAY[-2:])%min(len(choices),6)])
# Reddit hot is time-sensitive but not a claim of cross-platform popularity.
memes=reddit('memes','meme')+reddit('gifs','gif')+reddit('dankmemes','meme')
random.Random(TODAY).shuffle(memes)
culture=memes[:3]
# Preserve only honest, source-labelled records; UI falls back to source discovery links.
out={'fetched_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'date':TODAY,'social':social,'culture':culture}
Path('data').mkdir(exist_ok=True)
Path('data/culture_pulse.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('social',len(social),'culture',len(culture))
