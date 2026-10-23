#!/usr/bin/env python3
"""PULSE V6.9: public original posts only; no API keys or invented viral rankings.

Sources can rate-limit GitHub Actions. Empty lists are intentional when no
verifiable original post with a usable thumbnail can be retrieved.
"""
import datetime
import html
import json
import random
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

NOW = datetime.datetime.now(datetime.timezone.utc)
TODAY = NOW.date().isoformat()
UA = {"User-Agent": "Mozilla/5.0 (compatible; PULSECulture/1.1; public trend discovery)"}
VIDEO_DOMAINS = {"www.tiktok.com", "tiktok.com", "vm.tiktok.com", "vt.tiktok.com",
                 "www.instagram.com", "instagram.com", "www.youtube.com", "youtube.com", "youtu.be"}


def fetch(url, timeout=12):
    request = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def log_error(source, error):
    print(f"{source}: {type(error).__name__}: {error}")


def clean(value):
    return html.unescape(str(value or "")).strip()


def valid_url(value):
    try:
        parsed = urllib.parse.urlsplit(value)
        return parsed.scheme == "https" and bool(parsed.netloc)
    except ValueError:
        return False


def original_platform(url):
    try:
        parsed = urllib.parse.urlsplit(url)
        host = parsed.hostname or ""
        path = parsed.path.lower()
    except ValueError:
        return None
    if host not in VIDEO_DOMAINS:
        return None
    if "tiktok.com" in host and "/video/" in path:
        return "TIKTOK"
    if "instagram.com" in host and "/reel/" in path:
        return "INSTAGRAM REELS"
    if host in ("www.youtube.com", "youtube.com") and "/shorts/" in path:
        return "YOUTUBE SHORTS"
    return None


def reddit_json(subreddit, sort="hot"):
    urls = [
        f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit=80&raw_json=1",
        f"https://old.reddit.com/r/{subreddit}/{sort}.json?limit=80&raw_json=1",
    ]
    for url in urls:
        try:
            data = json.loads(fetch(url))
            return [c.get("data", {}) for c in data.get("data", {}).get("children", [])]
        except (ValueError, KeyError, urllib.error.URLError, TimeoutError) as exc:
            log_error(url, exc)
    return []


def reddit_rss(subreddit):
    """Public RSS alternative when Reddit JSON is blocked."""
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for host in ("www.reddit.com", "old.reddit.com"):
        url = f"https://{host}/r/{subreddit}/hot/.rss?limit=60"
        try:
            root = ET.fromstring(fetch(url))
            result = []
            for entry in root.findall("a:entry", ns):
                title = clean(entry.findtext("a:title", "", ns))
                link = next((e.get("href", "") for e in entry.findall("a:link", ns)
                             if e.get("rel", "alternate") == "alternate"), "")
                body = entry.findtext("a:content", "", ns)
                imgs = re.findall(r'<img[^>]+src=["\']([^"\']+)', html.unescape(body), re.I)
                image = clean(imgs[0]) if imgs else ""
                if image.startswith("//"):
                    image = "https:" + image
                if title and valid_url(link) and valid_url(image):
                    result.append({"platform": "REDDIT / " + subreddit.upper(), "title": title,
                                   "url": link, "image": image, "link_type": "original",
                                   "note": "Öffentlicher Reddit-Beitrag · keine verifizierte Viral-Rangliste"})
            if result:
                return result
        except (ET.ParseError, urllib.error.URLError, TimeoutError) as exc:
            log_error(url, exc)
    return []


def reddit_posts(subreddit):
    results = []
    for post in reddit_json(subreddit):
        if post.get("over_18") or post.get("stickied") or post.get("is_self") or post.get("removed_by_category"):
            continue
        title = clean(post.get("title"))
        permalink = post.get("permalink", "")
        url = "https://www.reddit.com" + permalink if permalink.startswith("/") else ""
        original = clean(post.get("url_overridden_by_dest") or post.get("url"))
        image = ""
        try:
            image = clean(post["preview"]["images"][0]["source"]["url"])
        except (KeyError, IndexError, TypeError):
            pass
        if not image and re.search(r"\.(?:jpg|jpeg|png|gif|webp)(?:\?|$)", original, re.I):
            image = original
        if not image and post.get("thumbnail", "").startswith("https://"):
            image = post["thumbnail"]
        if title and valid_url(url):
            results.append({"platform": "REDDIT / " + subreddit.upper(), "title": title,
                            "url": url, "image": image if valid_url(image) else "",
                            "external_url": original, "link_type": "original",
                            "note": "Öffentlicher Reddit-Beitrag · keine verifizierte Viral-Rangliste"})
    return results


def youtube_shorts():
    """Extract public Shorts results from YouTube search; never relabel regular videos."""
    found = []
    for query in ("viral shorts today", "trending shorts comedy"):
        url = "https://www.youtube.com/results?" + urllib.parse.urlencode({"search_query": query})
        try:
            page = fetch(url).decode("utf-8", "replace")
        except (urllib.error.URLError, TimeoutError) as exc:
            log_error("YouTube search", exc)
            continue
        # Shorts shelves expose a reelWatchEndpoint containing the actual video ID.
        for match in re.finditer(r'"reelWatchEndpoint"\s*:\s*\{\s*"videoId"\s*:\s*"([\w-]{11})"', page):
            video_id = match.group(1)
            # Only use titles present in the nearby shelf data; otherwise label neutrally.
            segment = page[max(0, match.start()-1800):match.start()+1800]
            titles = re.findall(r'"(?:simpleText|text)"\s*:\s*"([^"\\]{8,130})"', segment)
            title = clean(titles[-1]) if titles else "YouTube Short"
            found.append({"platform": "YOUTUBE SHORTS", "title": title,
                          "url": f"https://www.youtube.com/shorts/{video_id}",
                          "image": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                          "link_type": "original",
                          "note": "Öffentlich auffindbarer Short · Viralität nicht unabhängig bestätigt"})
    return found


def social_from_reddit():
    found = []
    for sub in ("TikTokCringe", "tiktok", "Instagramreels", "youtubehaiku", "shorts"):
        for post in reddit_posts(sub):
            platform = original_platform(post.get("external_url", ""))
            if platform and post.get("image"):
                found.append({"platform": platform, "title": post["title"],
                              "url": post["external_url"], "image": post["image"],
                              "link_type": "original",
                              "note": "Originalvideo, öffentlich auf Reddit geteilt · Viralität nicht unabhängig bestätigt"})
    return found


def unique(records, require_image=True):
    seen = set()
    output = []
    for record in records:
        url = record.get("url", "")
        if not valid_url(url) or (require_image and not valid_url(record.get("image", ""))):
            continue
        key = urllib.parse.urlsplit(url)._replace(query="", fragment="").geturl().rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        record.pop("external_url", None)
        output.append(record)
    return output


social_candidates = unique(youtube_shorts() + social_from_reddit())
random.Random(TODAY + "social").shuffle(social_candidates)
social = social_candidates[:3]

culture_candidates = []
for subreddit in ("memes", "gifs", "dankmemes", "wholesomememes", "funny"):
    posts = [p for p in reddit_posts(subreddit) if p.get("image")]
    culture_candidates.extend(posts if posts else reddit_rss(subreddit))
culture_candidates = unique(culture_candidates)
random.Random(TODAY + "culture").shuffle(culture_candidates)
culture = culture_candidates[:3]

result = {"fetched_at": NOW.isoformat(), "date": TODAY, "social": social, "culture": culture}
Path("data").mkdir(exist_ok=True)
Path("data/culture_pulse.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"PULSE V6.9: {len(social)} original social clips, {len(culture)} original culture posts")
if not social:
    print("NOTICE: No original social clips accessible. No news articles substituted.")
if not culture:
    print("NOTICE: Reddit blocked or no suitable images. No fake memes substituted.")
