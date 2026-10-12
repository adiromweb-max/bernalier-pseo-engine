"""
pricing.py — Dynamic price resolution for the Bernalier engine.

Unlike MGR (which scrapes a stable /mini-golden-retriever-puppies/ listing
page for CURRENT LITTER prices, since MGR sells specific in-stock puppies
at specific prices), Bernalier's pricing model is base ranges by coat color
published on the evergreen /bernalier-pricing/ page — it does not rotate
monthly the way the "for sale" litter-announcement pages do. So this
scrapes THAT stable page instead, and falls back to the hardcoded numbers
in config.PRICING_FALLBACK if the page text ever changes shape.
"""
import re, requests
import config

def get_live_pricing():
    """
    Return {'bi_color_min','bi_color_max','tri_color_min','tri_color_max',
    'average','live': bool}.
    """
    try:
        r = requests.get(config.PRICING_SOURCE_URL, timeout=20,
                         headers={"User-Agent": "Bernalier-Engine/1.0"})
        r.raise_for_status()
        text = r.text

        # Page text looks like: "average price ... is about $3200 ."
        #   "Bi-color Bernalier $2500 – 3500"   "Tri-color Bernalier $2800 – 4000"
        avg_m   = re.search(r'about\s*\$(\d{3,5})', text)
        bi_m    = re.search(r'Bi-?color[^$]*\$(\d{3,5})\s*[–-]\s*(\d{3,5})', text, re.IGNORECASE)
        tri_m   = re.search(r'Tri-?color[^$]*\$(\d{3,5})\s*[–-]\s*(\d{3,5})', text, re.IGNORECASE)

        if bi_m and tri_m:
            return {
                "bi_color_min": int(bi_m.group(1)), "bi_color_max": int(bi_m.group(2)),
                "tri_color_min": int(tri_m.group(1)), "tri_color_max": int(tri_m.group(2)),
                "average": int(avg_m.group(1)) if avg_m else None,
                "live": True,
            }
    except Exception as e:
        print(f"[pricing] live fetch failed ({e}); using fallback")

    fb = config.PRICING_FALLBACK
    return {
        "bi_color_min": fb["bi_color_min"], "bi_color_max": fb["bi_color_max"],
        "tri_color_min": fb["tri_color_min"], "tri_color_max": fb["tri_color_max"],
        "average": fb["average"], "live": False,
    }

def price_range_str(p):
    return f"${p['bi_color_min']:,}–${p['tri_color_max']:,} (avg ${p['average']:,})" if p.get("average") \
        else f"${p['bi_color_min']:,}–${p['tri_color_max']:,}"

if __name__ == "__main__":
    import json
    print(json.dumps(get_live_pricing(), indent=2))
