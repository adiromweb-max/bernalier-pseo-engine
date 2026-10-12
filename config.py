"""
Bernalier Engine — Configuration
Programmatic SEO engine for BernalierPups.com. Direct port of the MGR
engine's config.py (same shape/attribute names) so run.py/generator.py/
wp_push.py/assembler.py/pricing.py are straight ports.
"""
import os

# ── Claude API ────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")  # set in env, never hardcode
CLAUDE_MODEL      = "claude-sonnet-4-6"      # match whatever the MGR engine currently uses
CLAUDE_MAX_TOKENS = 4000

# ── WordPress REST API (client's site) ───────────────────────────────
WP_BASE_URL   = "https://www.bernalierpups.com"
WP_API        = f"{WP_BASE_URL}/wp-json/wp/v2"
WP_USER       = os.environ.get("BERNALIER_WP_USER", "")       # application-password user
WP_APP_PASS   = os.environ.get("BERNALIER_WP_APP_PASS", "")   # WP Application Password
WP_CPT_SLUG   = "bernalier_page"                               # custom post type (see bernalier-cpt-plugin.php)
WP_CPT_REST   = f"{WP_BASE_URL}/wp-json/wp/v2/{WP_CPT_SLUG}"

# ── Live pricing source (dynamic, with fallback) ─────────────────────
# NOTE: unlike MGR (which scrapes a stable /mini-golden-retriever-puppies/
# listing page for CURRENT LITTER prices), Bernalier has no such stable
# listing — its "for sale" pages rotate to a new URL almost every month
# (see cannibalization_warning in data_layer.json). So this instead
# scrapes the evergreen /bernalier-pricing/ pillar page, which states the
# base bi-color/tri-color ranges and doesn't rotate. Falls back to the
# same numbers hardcoded below if the page structure ever changes.
PRICING_SOURCE_URL = f"{WP_BASE_URL}/bernalier-pricing/"
PRICING_FALLBACK   = {
    "bi_color_min": 2500, "bi_color_max": 3500,
    "tri_color_min": 2800, "tri_color_max": 4000,
    "average": 3200,
}

# ── Generation controls ──────────────────────────────────────────────
BATCH_SIZE        = 10          # pages per run (phased rollout, avoid spam signals)
MAX_WORKERS        = 4
PUBLISH_STATUS    = os.environ.get("BERNALIER_PUBLISH_STATUS", "draft")     # 'draft' for review, 'publish' once Adi/Andrew approve the first batches
DRY_RUN           = True        # True = generate HTML locally only, don't push to WP. run.py --live flips this.
REQUEST_DELAY_SEC = 2           # politeness delay between API calls

# ── Paths ─────────────────────────────────────────────────────────────
BASE          = os.path.dirname(os.path.abspath(__file__))
DATA_DIR      = os.path.join(BASE, "data")
OUTPUT_DIR    = os.path.join(BASE, "output")
LOG_DIR       = os.path.join(BASE, "logs")
DATA_LAYER    = os.path.join(DATA_DIR, "data_layer.json")
PAGEMAP       = os.path.join(DATA_DIR, "final_pagemap.json")
KEYWORD_MAP   = os.path.join(DATA_DIR, "keyword_map.json")
STATE_FILE    = os.path.join(DATA_DIR, "generation_state.json")  # tracks what's built (anti-dup + anti-cannibal)
