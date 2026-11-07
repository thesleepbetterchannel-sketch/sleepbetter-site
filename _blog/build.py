#!/usr/bin/env python3
"""Builds the Sleep Better blog.

Each post is a Markdown file in _blog/posts/ with a short header:

    title: Why Rain Sounds Help You Fall Asleep
    slug: why-rain-sounds-help-you-sleep
    date: 2026-11-06
    category: Sound & sleep
    description: One or two sentences for Google and social previews.
    listen: 5, 1, 17          (episode numbers to feature, optional)
    ---
    Body in Markdown...

Run:  python3 _blog/build.py
It writes blog/index.html, blog/<slug>/index.html and refreshes sitemap.xml.
A post with "draft: yes" in its header is skipped.
"""
import html, json, math, re, sys
from datetime import date
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "_blog" / "posts"
OUT = ROOT / "blog"
SITE = "https://thesleepbetter.co"
CHANNEL = "https://www.youtube.com/@TheSleepBetterCo"
CATEGORY_ORDER = ["Sound & sleep", "Sleep habits", "Seasons & life stages"]

# Live episodes only. Add new ones here as they go public.
EPISODES = {
    1: ("Rain on a Glass Roof", "JfmyKeh_3CU"),
    2: ("City Rain & Thunder", "cUUz1kuTo6I"),
    3: ("Soft Rain in the Woods", "QQCUMxaNRGY"),
    4: ("Crackling Fireplace, Rain Outside", "hHzewkYTXpQ"),
    5: ("Heavy Rain on a Tin Roof", "N1MT-7IbiQs"),
    6: ("Snowy Night, Soft Winter Wind", "lLzRwSEd5tc"),
    7: ("Rain on a Tent in the Forest", "yEsUuqeMCqA"),
    8: ("Deep Brown Noise", "Ug7TDj_AYmk"),
    9: ("Rainy Beach at Night", "gSgYsSfxZx4"),
    10: ("Fan & Soft Rain, Cozy Bedroom", "v-u9Qk4h1Wk"),
    11: ("Thanksgiving Fireplace", "_VDRZ1qKPSc"),
    12: ("Christmas Fireplace", "FrptK-eP5dc"),
    13: ("Cozy Winter Blizzard", "7txNSKA6eqQ"),
    14: ("Cozy Fall Cabin", "b2lHocwMGic"),
    15: ("Quiet Christmas Eve Snowfall", "t7_Dvf9XWmA"),
    17: ("Rain on the Window", "LC2IYmP3BdE"),
    21: ("Soft Pink Noise", "rtTsqzz2Svk"),
    22: ("Soft Green Noise", "ZDFy3eKCL2Q"),
    23: ("Soft Grey Noise", "f2mzUeqOVqA"),
    24: ("Relaxing White Noise", "ofsNXre5Vq4"),
}

HEAD_TAGS = """<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=AW-18551058355"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'AW-18551058355');
</script>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="/img/slumber-avatar.jpg">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght,SOFT@0,9..144,500..800,100;1,9..144,500..700,100&family=Figtree:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/blog/blog.css">
<!-- Privacy-friendly analytics by Plausible -->
<script async src="https://plausible.io/js/pa-1U95-WWJvMxari_U4PVUm.js"></script>
<script>
  window.plausible=window.plausible||function(){(plausible.q=plausible.q||[]).push(arguments)},plausible.init=plausible.init||function(i){plausible.o=i||{}};
  plausible.init()
</script>"""

YT_ICON = '<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M23 7.2a3 3 0 0 0-2.1-2.1C19 4.6 12 4.6 12 4.6s-7 0-8.9.5A3 3 0 0 0 1 7.2 31 31 0 0 0 .5 12 31 31 0 0 0 1 16.8a3 3 0 0 0 2.1 2.1c1.9.5 8.9.5 8.9.5s7 0 8.9-.5a3 3 0 0 0 2.1-2.1 31 31 0 0 0 .5-4.8 31 31 0 0 0-.5-4.8ZM9.7 15.1V8.9l5.8 3.1-5.8 3.1Z" fill="currentColor"/></svg>'

HEADER = """<header class="bar">
  <a class="brand" href="/"><img src="/img/slumber-avatar.jpg" alt="" width="44" height="44">The Sleep Better Company</a>
  <nav aria-label="Site"><a href="/#episodes">Episodes</a><a href="/blog/">Sleep notes</a><a class="pill" href="{ch}">Subscribe on YouTube</a></nav>
</header>""".format(ch=CHANNEL)

FOOTER = """<div class="band">
  <div><h2>Sleep sounds for tonight</h2><p>Ten-hour rain, fire, waves and soft noise from The Sleep Better Company. No music, no talking, no ads in the middle of the night.</p></div>
  <a class="btn" href="{ch}">{yt}Subscribe on YouTube</a>
</div>
<footer><div class="row">
  <div class="tagline">Rain<i>·</i>Fire<i>·</i>Waves<i>·</i>Rest</div>
  <div><a href="/">Home</a> · <a href="/blog/">Sleep notes</a> · © {yr} The Sleep Better Company</div>
</div></footer>""".format(ch=CHANNEL, yt=YT_ICON, yr=date.today().year)

DISCLAIMER = ('<aside class="note"><b>A note from us:</b> this article is general information, not medical advice. '
              'If sleep problems are affecting your days, please talk with a doctor.</aside>')


def esc(s):
    return html.escape(s, quote=True)


def parse(path):
    text = path.read_text(encoding="utf-8")
    head, body = text.split("\n---\n", 1)
    meta = {}
    for line in head.strip().splitlines():
        k, v = line.split(":", 1)
        meta[k.strip()] = v.strip()
    meta["body_md"] = body.strip()
    meta["listen"] = [int(x) for x in meta.get("listen", "").replace(" ", "").split(",") if x]
    for n in meta["listen"]:
        if n not in EPISODES:
            sys.exit(f"{path.name}: episode {n} is not in EPISODES (not live yet?)")
    words = len(re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", body).split())
    meta["minutes"] = max(2, math.ceil(words / 230))
    return meta


def listen_box(nums):
    if not nums:
        return ""
    items = []
    for n in nums:
        title, vid = EPISODES[n]
        items.append(f'<li><a href="https://www.youtube.com/watch?v={vid}">'
                     f'<img src="https://i.ytimg.com/vi/{vid}/mqdefault.jpg" alt="" width="320" height="180" loading="lazy">'
                     f'<span><small>Episode {n:02d} · 10 hours</small>{esc(title)}</span></a></li>')
    return ('<section class="listen"><h2>Listen tonight</h2><ul>' + "".join(items) + "</ul></section>")


def fmt_date(d):
    y, m, dd = map(int, d.split("-"))
    return date(y, m, dd).strftime("%B %-d, %Y")


def render_post(p, others):
    body = markdown.markdown(p["body_md"], extensions=["extra", "sane_lists"])
    body = re.sub(r'<a href="(https?://[^"]+)"', r'<a href="\1" rel="noopener"', body)
    related = [o for o in others if o["category"] == p["category"]][:3]
    if len(related) < 3:
        related += [o for o in others if o not in related][: 3 - len(related)]
    rel_html = "".join(
        f'<li><a href="/blog/{o["slug"]}/"><small>{esc(o["category"])}</small>{esc(o["title"])}</a></li>' for o in related)
    url = f"{SITE}/blog/{p['slug']}/"
    ld = {
        "@context": "https://schema.org", "@type": "BlogPosting",
        "headline": p["title"], "description": p["description"],
        "datePublished": p["date"], "dateModified": p.get("updated", p["date"]),
        "mainEntityOfPage": url, "image": f"{SITE}/img/hero.jpg",
        "author": {"@type": "Organization", "name": "The Sleep Better Company", "url": SITE},
        "publisher": {"@type": "Organization", "name": "The Sleep Better Company",
                      "logo": {"@type": "ImageObject", "url": f"{SITE}/img/slumber-avatar.jpg"}},
    }
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
{HEAD_TAGS}
<title>{esc(p['title'])} · The Sleep Better Company</title>
<meta name="description" content="{esc(p['description'])}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="article">
<meta property="og:title" content="{esc(p['title'])}">
<meta property="og:description" content="{esc(p['description'])}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}/img/hero.jpg">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{json.dumps(ld)}</script>
</head>
<body>
<div class="wrap">
{HEADER}
<main>
<article class="post">
  <p class="crumbs"><a href="/blog/">Sleep notes</a> <span aria-hidden="true">›</span> {esc(p['category'])}</p>
  <h1>{esc(p['title'])}</h1>
  <p class="dek">{esc(p['description'])}</p>
  <p class="meta"><time datetime="{p['date']}">{fmt_date(p['date'])}</time> · {p['minutes']} min read</p>
  <div class="prose">
{body}
  </div>
  {listen_box(p['listen'])}
  {DISCLAIMER}
</article>
<section class="related"><h2>Keep reading</h2><ul>{rel_html}</ul></section>
{FOOTER}
</main>
</div>
</body>
</html>
"""


def render_index(posts):
    groups = []
    for cat in CATEGORY_ORDER:
        items = [p for p in posts if p["category"] == cat]
        if not items:
            continue
        cards = "".join(
            f'<li><a href="/blog/{p["slug"]}/"><h3>{esc(p["title"])}</h3><p>{esc(p["description"])}</p>'
            f'<small>{p["minutes"]} min read</small></a></li>' for p in items)
        groups.append(f'<section class="cat"><h2>{esc(cat)}</h2><ul class="cards">{cards}</ul></section>')
    desc = ("Plain-spoken, well-sourced notes on sleep from The Sleep Better Company: sleep sounds, "
            "bedroom habits, and what the research actually says.")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
{HEAD_TAGS}
<title>Sleep notes · The Sleep Better Company</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{SITE}/blog/">
<meta property="og:title" content="Sleep notes from The Sleep Better Company">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{SITE}/blog/">
<meta property="og:image" content="{SITE}/img/hero.jpg">
</head>
<body>
<div class="wrap">
{HEADER}
<main>
<header class="intro">
  <p class="eyebrow">Sleep notes</p>
  <h1>Better nights, <em>backed by the research</em></h1>
  <p>Short, honest guides to sleeping well: what sleep sounds can and can't do, the habits that matter most, and when it's time to talk to a doctor. Every claim links to its source.</p>
</header>
{''.join(groups)}
{FOOTER}
</main>
</div>
</body>
</html>
"""


def write_sitemap(posts):
    today = date.today().isoformat()
    urls = [(f"{SITE}/", today, "weekly", "1.0"), (f"{SITE}/blog/", today, "weekly", "0.8")]
    urls += [(f"{SITE}/blog/{p['slug']}/", p.get("updated", p["date"]), "monthly", "0.7") for p in posts]
    rows = "".join(f"  <url>\n    <loc>{u}</loc>\n    <lastmod>{d}</lastmod>\n    <changefreq>{c}</changefreq>\n"
                   f"    <priority>{pr}</priority>\n  </url>\n" for u, d, c, pr in urls)
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + rows + "</urlset>\n")


def main():
    posts = [parse(f) for f in sorted(SRC.glob("*.md"))]
    posts = [p for p in posts if p.get("draft", "").lower() not in ("yes", "true")]
    posts.sort(key=lambda p: (CATEGORY_ORDER.index(p["category"]), p.get("order", "99").zfill(3)))
    slugs = set()
    for p in posts:
        assert p["slug"] not in slugs, p["slug"]
        slugs.add(p["slug"])
        others = [o for o in posts if o is not p]
        d = OUT / p["slug"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(render_post(p, others), encoding="utf-8")
    (OUT / "index.html").write_text(render_index(posts), encoding="utf-8")
    write_sitemap(posts)
    print(f"built {len(posts)} posts")


if __name__ == "__main__":
    main()
