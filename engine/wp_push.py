"""
wp_push.py — Bernalier engine. Pushes assembled pages into WordPress via
REST API (bernalier_page CPT — see bernalier-cpt-plugin.php), and resolves
internal links from the keyword_map (anti-cannibalization).
Direct port of the MGR engine's wp_push.py.
"""
import json, requests, re
from requests.auth import HTTPBasicAuth
import config

# ── Internal link resolution (silo + anti-cannibalization) ──────────
def load_keyword_map():
    with open(config.KEYWORD_MAP) as f:
        return json.load(f)

def resolve_internal_links(page, data, kw_map, completed_pages=None, max_links=8):
    """
    True hierarchical silo:
    - Link UP to the most relevant pillar (verified real URL).
    - Link to SIBLING pages the engine already created in the same cluster.
    - Link to a few evergreen pillars.
    All URLs verified real or engine-created; never broken.
    NOTE: size/lifespan pillars don't exist yet on this site (see
    data_layer.json existing_owner_pages._note) — they're skipped here via
    the `if url` guards rather than linking to null.
    """
    owners = data["existing_owner_pages"]
    intent = page["intent"]
    links = []

    pillar_map = [
        ("price", "Bernalier Pricing", owners.get("pricing")),
        ("cost",  "Bernalier Pricing", owners.get("pricing")),
        ("size",  "Bernalier Breed Guide", owners.get("core")),   # falls back to core guide until a size pillar exists
        ("grown", "Bernalier Breed Guide", owners.get("core")),
        ("weight","Bernalier Breed Guide", owners.get("core")),
        ("temperament", "Bernalier Temperament", owners.get("temperament")),
        ("lifespan", "Bernalier Breed Guide", owners.get("core")), # falls back to core guide until a lifespan pillar exists
        ("health", "Health Guarantee", owners.get("health")),
        ("mix",   "Bernalier Breed Guide", owners.get("core")),
        ("core",  "Bernalier Breed Guide", owners.get("core")),
    ]
    cluster_key = None
    for key, label, url in pillar_map:
        if key in intent and url and (label, url) not in links:
            links.append((label, url))
            cluster_key = key
            break

    # SIBLING links — other engine-created pages in the same cluster (the silo)
    if completed_pages and cluster_key:
        siblings = []
        for sib_intent, sib_slug in completed_pages.items():
            if sib_intent == intent:
                continue
            if cluster_key in sib_intent:
                label = sib_intent.split(":")[-1].strip().title()
                siblings.append((label, "/guide/" + sib_slug + "/"))  # matches bernalier-cpt-plugin.php rewrite slug
        for s in siblings[:3]:
            if s not in links:
                links.append(s)

    # Evergreen links — homepage first (protects head term), then safe pillars.
    # Deliberately EXCLUDES what_is/breed-guide intent and any for-sale/adoption
    # intent from being an engine target at all (see cannibalization_warning in
    # data_layer.json) — those stay Andrew's manual pages / the existing pillars.
    evergreen = [
        ("Bernalier", "/"),
        ("Bernalier Pricing", owners.get("pricing")),
        ("Health Guarantee", owners.get("health")),
        ("Bernalier Temperament", owners.get("temperament")),
        ("Bernalier Breed Guide", owners.get("core")),
    ]
    for label, url in evergreen:
        if url and (label, url) not in links:
            links.append((label, url))
        if len(links) >= max_links:
            break

    return links[:max_links]

# ── WordPress REST push ─────────────────────────────────────────────
def push_page(content, html_body, schema, page, slug, allow_update=False):
    """
    Create a bernalier_page post via REST. Returns the post URL.
    SAFETY: by default, if a page with this slug already exists, we SKIP it
    (never overwrite an indexed/ranking page). Only updates if allow_update=True.
    """
    auth = HTTPBasicAuth(config.WP_USER, config.WP_APP_PASS)
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    existing = requests.get(f"{config.WP_CPT_REST}?slug={slug}&status=any",
                            auth=auth, headers={"Accept": "application/json"}, timeout=30).json()
    if existing:
        if not allow_update:
            raise SkipExisting(f"page already exists (id {existing[0]['id']}), skipping to protect it")
        pid = existing[0]["id"]

    payload = {
        "title":   content["title"],
        "slug":    slug,
        "content": html_body,
        "status":  config.PUBLISH_STATUS,
        "excerpt": content.get("meta_description", ""),
        "meta": {
            "bernalier_seo_title": content["title"],
            "bernalier_meta_desc": content.get("meta_description", ""),
            "bernalier_schema":    schema,
            "bernalier_intent":    page["intent"],
            "bernalier_location":  page.get("location", ""),
        },
    }

    if existing and allow_update:
        r = requests.post(f"{config.WP_CPT_REST}/{pid}", json=payload, auth=auth, headers=headers, timeout=60)
    else:
        r = requests.post(config.WP_CPT_REST, json=payload, auth=auth, headers=headers, timeout=60)
    r.raise_for_status()
    result = r.json()
    link = result.get("link", "")
    if not link:
        print(f"    [debug] no link in response. status={r.status_code}, keys={list(result.keys())[:8]}, id={result.get('id')}", flush=True)
    return link

class SkipExisting(Exception):
    """Raised when a page already exists and must not be overwritten."""
    pass

def bulk_existing_slugs(slugs):
    """Fast check: which of these slugs already exist on the site?"""
    auth = HTTPBasicAuth(config.WP_USER, config.WP_APP_PASS)
    headers = {"Accept": "application/json"}
    existing = set()
    CHUNK = 30
    for i in range(0, len(slugs), CHUNK):
        chunk = slugs[i:i+CHUNK]
        try:
            params = "&".join(f"slug[]={s}" for s in chunk) + "&per_page=100&status=any&_fields=slug"
            r = requests.get(f"{config.WP_CPT_REST}?{params}", auth=auth, headers=headers, timeout=30)
            if r.ok:
                for item in r.json():
                    if item.get("slug"):
                        existing.add(item["slug"])
        except Exception as e:
            print(f"  (bulk check warning: {e})", flush=True)
    return existing

def make_slug(page):
    intent = page["intent"]
    category, _, detail = intent.partition(":")
    detail = detail.strip() or category.strip()
    base = detail.lower().replace(" ", "-").replace("/", "-")
    base = "".join(c for c in base if c.isalnum() or c == "-")

    generic = {"general", "guide", "overview", "info"}
    if base in generic or detail.lower() in generic:
        cat = "".join(c for c in category.strip().lower().replace(" ", "-") if c.isalnum() or c == "-")
        base = f"{cat}-{base}"

    base = re.sub(r"-+", "-", base).strip("-")
    if page.get("location"):
        loc = page["location"].lower().replace(", ", "-").replace(" ", "-")
        loc = "".join(c for c in loc if c.isalnum() or c == "-")
        return f"bernalier-{base}-{loc}"
    return f"bernalier-{base}"
