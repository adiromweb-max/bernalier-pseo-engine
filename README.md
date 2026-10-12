# Bernalier Engine — Programmatic SEO for BernalierPups.com

A hybrid pSEO system, structured identically to the MGR engine
(`mgr-pseo-engine`). The engine runs on your infrastructure (generates
content via the Claude API), and pushes finished pages into the client's
WordPress via REST as a custom post type (`bernalier_page`). Pages inherit
the site's active theme.

## Key differences from the MGR engine

- **Breed**: Bernalier = Bernese Mountain Dog x Cavalier King Charles
  Spaniel (100% single cross, no F1/F1b split like MGR's Golden Cavalier /
  Golden Cocker). Red line: never mention Poodle/Doodle/**Bernedoodle**
  (the real Bernese x Poodle cross — easy to confuse with "Bernalier").
- **Pricing**: base ranges by coat color (bi-color $2,500–3,500, tri-color
  $2,800–4,000, avg ~$3,200), not per-litter live pricing. `pricing.py`
  scrapes the evergreen `/bernalier-pricing/` page instead of a rotating
  listing page (Bernalier has no stable "current puppies" URL — Andrew
  publishes a new for-sale page almost every month and never deletes the
  old ones).
- **Cannibalization**: verified against a full pull of the site's 49 pages
  + 7 posts (2026-09-24). Every existing "for sale"/"for adoption" page is
  NATIONAL — zero location targeting exists anywhere on the site today.
  That means the entire location fan-out this engine builds is genuinely
  new ground, unlike MGR where some states/cities already had content.
  It also means **no dedicated size or lifespan pillar page exists yet**
  (unlike MGR) — the engine links those clusters back to the breed guide
  until Adi/Andrew decide whether to build them.
- **URL structure**: `/guide/{slug}/`, matching the *live* MGR site (the
  checked-into-git `mgr-pseo-pages.php` actually shows a root rewrite slug,
  but the production plugin installed on minigoldenretrievers.com uses
  `/guide/`, confirmed by pulling live URLs via REST on 2026-09-24 — this
  repo's plugin matches the working production behavior, not the stale
  file in the MGR repo).

## Setup

1. Install `wordpress-plugin/bernalier-pseo-pages.php` as an mu-plugin (or
   activate as a regular plugin) on bernalierpups.com.
2. Create a WordPress Application Password for the engine's WP user.
3. Set secrets (locally via env vars, or as GitHub repo secrets for the
   Actions workflow): `ANTHROPIC_API_KEY`, `BERNALIER_WP_USER`,
   `BERNALIER_WP_APP_PASS`.
4. `pip install -r requirements.txt`
5. Dry run first: `python run.py --batch all --limit 3` (writes HTML to
   `output/` only, does not touch WordPress — check `config.DRY_RUN`).
6. Review the generated HTML. When happy, push a small live batch as
   drafts: `python run.py --batch all --live --limit 3` (config.PUBLISH_STATUS
   is `"draft"` by default — flip to `"publish"` once Adi/Andrew approve
   the first batches).

## ⚠️ Before running for real

- **Shared Anthropic key**: if this reuses the same `ANTHROPIC_API_KEY`
  secret as the MGR repo, remember the MGR scheduled run failed multiple
  times in the logs Adi shared with "Your credit balance is too low" — top
  up credits before the first Bernalier run too, or the same failure will
  repeat here.
- **`data/pages.json` is intentionally absent.** MGR's `--batch quickwins`
  filter depends on real keyword-volume/ranking data in this file (from an
  Ahrefs/GSC pull) to find intents already ranking 4–20. No such pull has
  been done for Bernalier yet, so `quickwins` will currently match zero
  pages — use `--batch all` (the default here) until that data exists.
- **`data/final_pagemap.json`** currently has 82 entries, all
  `price: puppy price | <state/city>`, covering the ~25 most populous
  states + their top 3–4 cities. This is a first draft mirroring the scale
  of MGR's pagemap — expand it (or add other intents) once the first batch
  proves out.
