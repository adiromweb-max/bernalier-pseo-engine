"""
assembler.py — Bernalier engine. Turns generated content (JSON) into the
final HTML body pushed into the bernalier_page CPT. The CPT inherits the
site's active theme header/footer/colors automatically, so this only
builds the inner content. Direct port of MGR's assembler.py.
"""
import json, html
import config

# Minimal scoped CSS — theme-neutral classes, relies on the theme for base colors.
SCOPED_CSS = """
<style>
.bnl-wrap{max-width:880px;margin:0 auto}
.bnl-takeaway{background:rgba(74,90,58,.1);border-left:4px solid #4a5a3a;border-radius:0 8px 8px 0;padding:14px 18px;margin:0 0 20px;font-size:1.02rem}
.bnl-price{background:rgba(74,90,58,.08);border:1px solid rgba(74,90,58,.3);border-radius:14px;padding:24px 28px;margin:22px 0;display:flex;flex-wrap:wrap;gap:18px;align-items:center;justify-content:space-between}
.bnl-price .big{font-size:2.2rem;font-weight:700;line-height:1}
.bnl-price .lbl{font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;opacity:.7;display:block;margin-top:6px}
.bnl-live{font-size:.7rem;font-weight:700;text-transform:uppercase;color:#5a8a4a}
.bnl-table{width:100%;border-collapse:collapse;margin:18px 0;border-radius:10px;overflow:hidden}
.bnl-table th{text-align:left;padding:12px 16px;font-size:.8rem;text-transform:uppercase;letter-spacing:.03em}
.bnl-table td{padding:11px 16px;border-bottom:1px solid rgba(0,0,0,.08)}
.bnl-faq details{border:1px solid rgba(0,0,0,.1);border-radius:10px;margin-bottom:10px;padding:0}
.bnl-faq summary{padding:15px 18px;cursor:pointer;font-weight:600}
.bnl-faq .a{padding:0 18px 15px}
.bnl-related{background:rgba(0,0,0,.03);border-radius:14px;padding:22px 26px;margin:28px 0}
.bnl-related ul{list-style:none;display:grid;grid-template-columns:1fr 1fr;gap:10px;padding:0}
.bnl-related a{display:block;padding:10px 14px;background:#fff;border:1px solid rgba(0,0,0,.1);border-radius:8px;text-decoration:none;font-weight:600}
.bnl-cta{text-align:center;border-radius:14px;padding:34px;margin:28px 0;background:rgba(74,59,71,.06)}
.bnl-btn{display:inline-block;background:#4a3b47;color:#fff;padding:14px 36px;border-radius:50px;text-decoration:none;font-weight:700;margin-top:8px}
@media(max-width:600px){.bnl-related ul{grid-template-columns:1fr}}
</style>
"""

def _esc(s): return html.escape(str(s))

# Whitelist of internal paths Claude is allowed to link to in body text.
# Pulled from data_layer.json existing_owner_pages (verified real URLs only).
# size/lifespan intentionally excluded — no pillar page exists yet for them.
_ALLOWED_LINK_PATHS = (
    "/", "/bernalier-pricing/", "/health-guarantee/",
    "/bernalier-temperament/", "/bernalier-mini-bernese-mountain-dog/",
    "/frequently-asked-questions/", "/parent-dogs/", "/about-bernaliers/",
    "/puppy-training/", "/delivery-pickup/", "/process/", "/apply/",
)

def _safe_links(text):
    """
    Escape the paragraph, then re-enable ONLY whitelisted internal <a> links.
    Prevents any unverified/external/broken links or injection from the model.
    """
    import re
    anchors = []
    def _stash(m):
        href, label = m.group(1), m.group(2)
        if href in _ALLOWED_LINK_PATHS:
            anchors.append((href, label))
            return f"\x00{len(anchors)-1}\x00"
        return label  # drop the link, keep the text
    tmp = re.sub(r'<a\s+href="([^"]+)"\s*>(.*?)</a>', _stash, text, flags=re.IGNORECASE)
    tmp = _esc(tmp)
    for i, (href, label) in enumerate(anchors):
        tmp = tmp.replace(f"\x00{i}\x00", f'<a href="{_esc(href)}">{_esc(label)}</a>')
    return tmp

def assemble_html(content, page, data, pricing, internal_links):
    parts = [SCOPED_CSS, '<div class="bnl-wrap">']

    if content.get("key_takeaway"):
        parts.append(f'<div class="bnl-takeaway"><strong>Quick answer:</strong> {_esc(content["key_takeaway"])}</div>')

    parts.append(f"<p>{_esc(content['intro'])}</p>")

    if content.get("quick_facts"):
        parts.append('<table class="bnl-table"><tbody>')
        for f in content["quick_facts"]:
            parts.append(f'<tr><td>{_esc(f["label"])}</td><td>{_esc(f["value"])}</td></tr>')
        parts.append('</tbody></table>')

    # Price card (only for price/cost intents — never for sale/adoption, which
    # this engine never generates in the first place; see cannibalization_warning)
    if any(k in page["intent"] for k in ("price", "cost")):
        live = '<span class="bnl-live">● Live pricing from the current rate sheet</span>' if pricing.get("live") else ''
        avg_line = f"<p style=\"margin:6px 0 0\">Average price about ${pricing['average']:,}, plus a $200 pre-adoption healthcare fee.</p>" if pricing.get("average") else ""
        parts.append(f"""
<div class="bnl-price">
  <div><span class="big">${pricing['bi_color_min']:,}–${pricing['tri_color_max']:,}</span><span class="lbl">Bi-color to tri-color price range</span></div>
  <div>{live}{avg_line}</div>
</div>""")

    for s in content.get("sections", []):
        parts.append(f"<h2>{_esc(s['h2'])}</h2>")
        for para in s["body"].split("\n"):
            if para.strip():
                parts.append(f"<p>{_safe_links(para.strip())}</p>")

    if content.get("faqs"):
        parts.append('<h2>Frequently Asked Questions</h2><div class="bnl-faq">')
        for f in content["faqs"]:
            parts.append(f'<details><summary>{_esc(f["q"])}</summary><div class="a">{_esc(f["a"])}</div></details>')
        parts.append('</div>')

    if internal_links:
        parts.append('<div class="bnl-related"><h3>Related Pages</h3><ul>')
        for label, url in internal_links:
            parts.append(f'<li><a href="{_esc(url)}">{_esc(label)} →</a></li>')
        parts.append('</ul></div>')

    parts.append(f"""
<div class="bnl-cta">
  <h3>Ready to Find Your Bernalier?</h3>
  <p>Apply today to join the wait list and get matched with an available puppy.</p>
  <a href="/apply/" class="bnl-btn">Apply Today</a>
  <p style="margin-top:14px">Questions? Call <a href="tel:18647943134">(864) 794-3134</a></p>
</div>""")

    parts.append('</div>')
    return "\n".join(parts)

def build_faq_schema(content, page=None, data=None, pricing=None, url_path=None):
    """
    Build a full schema.org @graph: FAQPage + Article (speakable) +
    Product/Offer (price pages) + LocalBusiness + BreadcrumbList.
    """
    graph = []

    if content.get("faqs"):
        graph.append({
            "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": f["q"],
                 "acceptedAnswer": {"@type": "Answer", "text": f["a"]}}
                for f in content["faqs"]
            ],
        })

    article = {
        "@type": "Article",
        "headline": content.get("h1") or content.get("title", ""),
        "description": content.get("meta_description", ""),
        "speakable": {
            "@type": "SpeakableSpecification",
            "cssSelector": [".bnl-takeaway", ".bnl-faq"],
        },
        "datePublished": _today(),
        "dateModified": _today(),
    }
    if data:
        article["author"] = {"@type": "Organization", "name": data["breeder"]["brand"]}
        article["publisher"] = {"@type": "Organization", "name": data["breeder"]["network"]}
    graph.append(article)

    if pricing and page and any(k in page.get("intent", "") for k in ("price", "cost")):
        graph.append({
            "@type": "Product",
            "name": "Bernalier Puppy",
            "description": "Bernese Mountain Dog x Cavalier King Charles Spaniel puppy, family-raised with health guarantee.",
            "brand": {"@type": "Brand", "name": data["breeder"]["brand"] if data else "Bernalier Pups"},
            "offers": {
                "@type": "AggregateOffer",
                "priceCurrency": "USD",
                "lowPrice": pricing["bi_color_min"],
                "highPrice": pricing["tri_color_max"],
                "availability": "https://schema.org/InStock",
            },
        })

    if data:
        b = data["breeder"]
        graph.append({
            "@type": "LocalBusiness",
            "name": b["brand"],
            "telephone": b["phone"],
            "address": {
                "@type": "PostalAddress",
                "addressLocality": b["location"]["city"],
                "addressRegion": b["location"]["state_abbr"],
                "addressCountry": "US",
            },
        })

    if url_path and page:
        crumbs = _breadcrumbs(page, url_path)
        if crumbs:
            graph.append(crumbs)

    if not graph:
        return ""
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)

def _today():
    import datetime
    return datetime.date.today().isoformat()

def _breadcrumbs(page, url_path):
    base = "https://www.bernalierpups.com"
    items = [{"@type": "ListItem", "position": 1, "name": "Home", "item": base + "/"}]
    intent = page.get("intent", "")
    pillar = None
    if "price" in intent or "cost" in intent:
        pillar = ("Bernalier Pricing", "/bernalier-pricing/")
    elif "temperament" in intent:
        pillar = ("Bernalier Temperament", "/bernalier-temperament/")
    elif "health" in intent:
        pillar = ("Health Guarantee", "/health-guarantee/")
    if pillar:
        items.append({"@type": "ListItem", "position": 2, "name": pillar[0], "item": base + pillar[1]})
    items.append({"@type": "ListItem", "position": len(items) + 1,
                  "name": page.get("intent", "Guide"), "item": base + url_path})
    return {"@type": "BreadcrumbList", "itemListElement": items}
