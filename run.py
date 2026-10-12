"""
run.py — Bernalier Engine orchestrator. Direct port of the MGR engine's
run.py. Runs the full pipeline: load page map -> for each page, resolve
pricing, generate content (Claude), assemble HTML, push to WordPress.
Phased in batches. Tracks state so reruns don't duplicate.

USAGE:
    export ANTHROPIC_API_KEY=sk-ant-...
    export BERNALIER_WP_USER=your_wp_user
    export BERNALIER_WP_APP_PASS="xxxx xxxx xxxx xxxx"
    python run.py --batch all --limit 3          # dry run (writes HTML to output/ only)
    python run.py --batch all --live --limit 3   # generate and push live (as drafts — see config.PUBLISH_STATUS)

NOTE ON --batch: MGR's "quickwins" filter targets EXISTING national pages
that already rank 4-20 in Google and gives them a location variant to push
further. Bernalier's location pages are 100% NEW (see
cannibalization_warning in data_layer.json — none of this site's 49 pages
target any state/city), so there's no ranking history to filter by yet.
Until Adi pulls real keyword-volume data into data/pages.json, "quickwins"
will match nothing — use --batch all.
"""
import json, os, time, argparse, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "engine"))

import config
import pricing as pricing_mod
import generator
import assembler
import wp_push

def load_json(p):
    with open(p) as f: return json.load(f)

def load_state():
    if os.path.exists(config.STATE_FILE):
        return load_json(config.STATE_FILE)
    return {"completed": [], "owned_keywords": {}}

def save_state(state):
    with open(config.STATE_FILE, "w") as f:
        json.dump(state, f, indent=1)

def build_sibling_map(all_pages):
    """
    For each page, find related pages in the same silo (same US state) so
    each page can link to its neighbors — builds hierarchy/siloing.
    Returns {slug: [(url, anchor), ...]}.
    """
    US_STATES = ["Texas","California","Florida","New York","North Carolina","Georgia",
                 "South Carolina","Ohio","Pennsylvania","Virginia","Tennessee","Illinois",
                 "Michigan","Colorado","Arizona","Washington","Massachusetts","New Jersey",
                 "Alabama","Indiana","Kentucky","Missouri","Wisconsin","Minnesota","Maryland"]
    by_state = {}
    for p in all_pages:
        loc = p.get("location", "")
        state = next((s for s in US_STATES if s in loc), None)
        if state:
            by_state.setdefault(state, []).append(p)

    sibling_map = {}
    for p in all_pages:
        loc = p.get("location", "")
        state = next((s for s in US_STATES if s in loc), None)
        if not state:
            continue
        slug = wp_push.make_slug(p)
        sibs = []
        for other in by_state[state]:
            if other is p:
                continue
            o_slug = wp_push.make_slug(other)
            o_loc = other.get("location", "")
            anchor = f"Bernalier puppies in {o_loc}" if o_loc else "Bernalier puppies"
            sibs.append((f"/guide/{o_slug}/", anchor))
        if sibs:
            sibling_map[slug] = sibs[:4]
    return sibling_map

def parse_pagemap():
    """Turn the flat pagemap list into structured page dicts."""
    pm = load_json(config.PAGEMAP)
    pages = []
    for entry in pm["pages"]:
        intent, _, loc = entry.partition(" | ")
        loc = "" if "(national)" in loc else loc.strip()
        pages.append({"intent": intent.strip(), "location": loc, "keywords": [intent.strip()]})
    return pages

def is_quickwin(page, pages_data):
    """Quick win = intent cluster already ranking pos 4-20 with decent volume.
    See the module docstring — this won't match anything for Bernalier until
    real keyword data is added to data/pages.json."""
    sig = page["intent"]
    info = pages_data.get(sig)
    if not info: return False
    return 4 <= info.get("best_pos", 99) <= 20 and info.get("volume", 0) >= 300

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", default="all", choices=["quickwins", "all"])
    ap.add_argument("--live", action="store_true", help="push to WP (overrides DRY_RUN)")
    ap.add_argument("--limit", type=int, default=config.BATCH_SIZE)
    args = ap.parse_args()

    if args.live:
        config.DRY_RUN = False

    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    data       = load_json(config.DATA_LAYER)
    pages_data_path = os.path.join(config.DATA_DIR, "pages.json")
    pages_data = load_json(pages_data_path) if os.path.exists(pages_data_path) else {}
    kw_map     = wp_push.load_keyword_map()
    state      = load_state()
    completed_set = set(state.get("completed", []))

    pages = parse_pagemap()
    sibling_map = build_sibling_map(pages)
    if args.batch == "quickwins":
        pages = [p for p in pages if is_quickwin(p, pages_data)]

    for p in pages:
        info = pages_data.get(p["intent"])
        if info: p["keywords"] = info["keywords"][:6]

    pricing = pricing_mod.get_live_pricing()
    print(f"[pricing] bi-color ${pricing['bi_color_min']}-{pricing['bi_color_max']}, tri-color ${pricing['tri_color_min']}-{pricing['tri_color_max']} (live={pricing['live']})", flush=True)
    print(f"[batch] {args.batch}: {len(pages)} candidate pages | DRY_RUN={config.DRY_RUN}", flush=True)

    done = 0
    blocked = set(data.get("cannibalization_warning", {}).get("blocked_national_intents", []))
    blocked_cats = set(data.get("cannibalization_warning", {}).get("blocked_categories", []))
    blocked_dupes = set(data.get("cannibalization_warning", {}).get("blocked_duplicate_intents", []))

    import requests as _rq
    from requests.auth import HTTPBasicAuth as _Auth
    def _already_exists(slug):
        try:
            r = _rq.get(f"{config.WP_CPT_REST}?slug={slug}&status=any&_fields=id",
                        auth=_Auth(config.WP_USER, config.WP_APP_PASS),
                        headers={"Accept": "application/json"}, timeout=20)
            return bool(r.ok and r.json())
        except Exception:
            return False

    for page in pages:
        slug = wp_push.make_slug(page)
        if slug in state["completed"]:
            continue
        if page["intent"].strip() in blocked_dupes:
            print(f"  ⏭ skipped (duplicate intent): {page['intent']}", flush=True)
            continue
        if page["intent"].split(":")[0].strip() in blocked_cats:
            print(f"  ⏭ skipped (protects existing pillar/homepage): {page['intent']}", flush=True)
            continue
        if not page.get("location") and page["intent"] in blocked:
            print(f"  ⏭ skipped (would cannibalize existing page): {page['intent']}", flush=True)
            continue
        if done >= args.limit:
            print(f"[batch] reached limit {args.limit}; rerun to continue")
            break
        if slug in completed_set:
            continue
        if not config.DRY_RUN and _already_exists(slug):
            print(f"  ⏭ exists, skipping (no tokens used): {slug}", flush=True)
            state["completed"].append(slug)
            completed_set.add(slug)
            save_state(state)
            continue
        try:
            print(f"  → generating: {slug}", flush=True)
            t0 = time.time()
            content = generator.generate_page_content(page, data, pricing, sibling_links=sibling_map.get(slug))
            links   = wp_push.resolve_internal_links(page, data, kw_map, state.get("owned_keywords", {}))
            body    = assembler.assemble_html(content, page, data, pricing, links)
            schema  = assembler.build_faq_schema(content, page, data, pricing, "/guide/" + slug + "/")

            with open(os.path.join(config.OUTPUT_DIR, f"{slug}.html"), "w") as f:
                f.write(f"<!-- {content['title']} -->\n<!-- meta: {content.get('meta_description','')} -->\n{body}")

            if not config.DRY_RUN:
                try:
                    url = wp_push.push_page(content, body, schema, page, slug)
                    print(f"    pushed → {url}", flush=True)
                except wp_push.SkipExisting as se:
                    print(f"    ⏭ skipped (protected): {se}", flush=True)
                    state["completed"].append(slug)
                    save_state(state)
                    continue

            state["completed"].append(slug)
            state["owned_keywords"][page["intent"]] = slug
            save_state(state)
            done += 1
            print(f"    ✓ done in {time.time()-t0:.0f}s ({done}/{args.limit})", flush=True)
            time.sleep(config.REQUEST_DELAY_SEC)
        except Exception as e:
            print(f"    ⚠ failed {slug}: {e}", flush=True)

    print(f"[done] generated {done} pages this run. Total completed: {len(state['completed'])}")

if __name__ == "__main__":
    main()
