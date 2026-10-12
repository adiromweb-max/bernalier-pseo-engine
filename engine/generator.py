"""
generator.py — Claude-powered unique content per page, Bernalier engine.
Direct port of the MGR engine's generator.py — same GEO/AEO structure,
same prompt-caching + retry + red-line-guard pattern — swapped to the
Bernalier breed and its own real facts (see data/data_layer.json).
"""
import json, time, requests
import config

SYSTEM_PROMPT = """You are an expert dog-breed content writer optimizing for BOTH Google and AI answer engines (ChatGPT, Perplexity, Gemini, Google AI Overviews) for a US Mini Bernese Mountain Dog / Bernalier breeder (Crockett Pups, Greenville SC).

This is a competitive US market. Content must be citation-worthy by AI engines and rank in Google. Follow GEO (Generative Engine Optimization) best practices:

CONTENT STRUCTURE (critical for AI citation):
- Lead every section with a DIRECT ANSWER in the first 40-60 words. State the answer, then elaborate.
- Keep paragraphs SHORT: 2-3 sentences max. Long blocks don't get cited by AI.
- High fact density: include a concrete number, stat, or specific detail every 150-200 words.
- Write to answer "fan-out" sub-questions an AI would break a query into (e.g. for price: "how much", "what affects cost", "is it worth it", "payment options").
- Use natural question phrasing in headings that match how people actually ask.

ANSWER ENGINE OPTIMIZATION (AEO / "People Also Ask"):
- Each FAQ question must be phrased the way a real person types it into Google ("How much is a Bernalier?", "Are mini Bernese good with kids?") — these are what win "People Also Ask" placements.
- Each FAQ answer must be SELF-CONTAINED and lead with the answer in the first sentence (under 50 words), so Google can lift it directly into a PAA box or AI Overview.
- Cover a range of question types: what/how/why/when/cost/comparison — Google rewards pages that answer the full cluster of related questions.
- The key_takeaway and each FAQ answer should make sense even if quoted alone, with no surrounding context needed.

ABSOLUTE RULES — violating any is a failure:
1. A "Bernalier" = "Mini Bernese Mountain Dog" = "Mini Berner" = Bernese Mountain Dog x Cavalier King Charles Spaniel. It is NOT related to any Poodle-mix breed.
2. The words "Poodle", "Doodle", and "Bernedoodle" are STRICTLY FORBIDDEN anywhere in your output — not even to say "this is not a Bernedoodle", not in comparisons, not in passing. Simply never write those words. State only what the breed IS (Bernese x Cavalier). Any appearance causes automatic rejection.
3. Use only the facts provided in the DATA block. Never invent prices, sizes, or guarantees. Accurate facts are what make content citation-worthy.
3a. HEALTH GUARANTEE: There are TWO tiers. The 1-year tier IS automatic and can be stated as included ("backed by an automatic 1-year health guarantee"). The 12-year tier is CONDITIONAL on the owner maintaining pet insurance for 6 months and using a recommended food — always describe it as "available" or "conditional," never as automatically included. Never blur the two tiers into one unconditional guarantee.
4. Warm, family-first, trustworthy tone (E-E-A-T). Show expertise and care. Never clinical or salesy.
5. Genuinely useful, specific content — no filler, no repetition across sections.
6. Output ONLY valid JSON in the exact schema requested. No markdown, no preamble.
"""

def build_user_prompt(page, data, pricing, sibling_links=None):
    import datetime
    current_year = datetime.date.today().year
    breed = data["breed"]
    owners = data.get("existing_owner_pages", {})

    # Tier 1: homepage + evergreen pillar pages that actually exist on the site.
    # size/lifespan are intentionally left out until those pillar pages are built —
    # see data_layer.json existing_owner_pages._note.
    linkable = [(u, k) for u, k in [
        ("/", "Bernalier"),
        (owners.get("pricing"), "Bernalier pricing"),
        (owners.get("health"), "health guarantee"),
        (owners.get("temperament"), "Bernalier temperament"),
        (owners.get("core"), "Bernalier breed guide"),
        (owners.get("faq"), "frequently asked questions"),
    ] if u]
    link_list = "\n".join(f"- {url} (anchor idea: \"{kw}\")" for url, kw in linkable)

    sibling_block = ""
    if sibling_links:
        sib = "\n".join(f"- {url} (anchor idea: \"{anchor}\")" for url, anchor in sibling_links)
        sibling_block = f"""

RELATED PAGES IN THIS CLUSTER — link to 2-3 of these too, where they fit naturally. These connect pages in the same region/topic and are important for site structure:
{sib}"""

    hg = data["health_guarantee"]
    dep = data["pricing"]
    breeder = data["breeder"]
    # pricing dict here is the DYNAMIC live/fallback range from pricing.py
    # (bi_color_min/max, tri_color_min/max, average, live). Static facts that
    # never change (deposit, healthcare fee, tax) are written in literally,
    # same pattern the MGR engine's generator.py uses.
    return f"""DATA:
Breed names: {breed['primary_name']} (aka {', '.join(breed['synonyms'])})
Composition: {breed['composition']['primary']['cross']}
Size: {breed['size']['weight_lbs']['typical']} lbs typical (range {breed['size']['weight_lbs']['min']}-{breed['size']['weight_lbs']['max']}), {breed['size']['height_in']['min']}-{breed['size']['height_in']['max']} in tall, full grown around {breed['size']['full_grown_months']['max']} months
Lifespan: {breed['lifespan_years']['min']}-{breed['lifespan_years']['max']} years
Colors: {', '.join(breed['coat']['colors'])}
Temperament: {', '.join(breed['temperament'])}
Price: bi-color ${pricing['bi_color_min']}-{pricing['bi_color_max']}, tri-color ${pricing['tri_color_min']}-{pricing['tri_color_max']}{f", average about ${pricing['average']}" if pricing.get('average') else ""}. Plus a $200 pre-adoption healthcare fee (not taxed). $300 deposit: {dep["deposit_terms"]} 6% sales tax applies ONLY to puppies picked up/delivered in South Carolina.
Breeder: {breeder['brand']} ({breeder['network']} network), {breeder['location']['city']}, {breeder['location']['state']}, {breeder['phone']}, genetic testing, microchipped, family-raised.
Health guarantee: {hg['automatic_tier']['years']}-year tier is AUTOMATIC ({hg['automatic_tier']['coverage']}). {hg['extended_tier']['years']}-year tier is CONDITIONAL on: {'; '.join(hg['extended_tier']['conditional_on'])}. Never state the {hg['extended_tier']['years']}-year tier as automatic. The 1-year tier is automatic with every puppy but is still governed by the terms on the /health-guarantee/ page (for example the buyer must have a licensed vet well-check within 7 days of taking ownership) — NEVER write "no conditions attached", "unconditional" or "no strings" about any part of the guarantee.

INTERNAL LINKS — weave 2-3 of these naturally INTO your section paragraphs as contextual links (NOT a list). Use the keyword-rich anchor inside a relevant sentence. Format as HTML: <a href="URL">anchor text</a>. Only link where it genuinely fits the topic. Do NOT link to the current page's own topic. Always include the homepage link ("Bernalier") once where natural.
Available pages to link:
{link_list}{sibling_block}

PAGE TO WRITE:
Intent: {page['intent']}
{f"Location focus: {page['location']}" if page.get('location') else "Scope: national (no specific location)"}
Target keywords: {', '.join(page['keywords'][:6])}

CURRENT YEAR: {current_year}. If you reference a year anywhere (title, meta, or body), it MUST be {current_year} — never an earlier year. Prefer to avoid putting a year in the title unless it genuinely helps; if you do, use {current_year}.

Write JSON with this exact schema:
{{
  "title": "SEO title under 60 chars, include main keyword{' and location' if page.get('location') else ''}",
  "meta_description": "compelling meta under 155 chars",
  "h1": "page headline",
  "key_takeaway": "ONE direct, citation-ready sentence (under 30 words) that answers the page's core question with a specific fact/number. This is what AI engines will quote.",
  "intro": "2-3 short sentences. First sentence = direct answer. Specific to this intent{'/location' if page.get('location') else ''}",
  "quick_facts": [
    {{"label": "short label", "value": "specific value/number"}}
  ],
  "sections": [
    {{"h2": "question-style heading", "body": "Lead with direct answer in first 40-60 words, then elaborate. Short paragraphs (2-3 sentences). Weave in 2-3 contextual internal links as HTML <a> tags where relevant. Separate paragraphs with a blank line."}}
  ],
  "faqs": [
    {{"q": "natural question exactly as a person would Google it", "a": "self-contained answer, direct answer first sentence, using only DATA facts, under 50 words"}}
  ]
}}
Include 3-4 quick_facts, 2-4 sections, and 5-7 FAQs covering different question types (cost, size, temperament, comparison, process). More well-formed Q&A = more "People Also Ask" placements and AI citations. Make it the most useful, most quotable page on this topic in the niche."""

def generate_page_content(page, data, pricing, _retry=True, sibling_links=None):
    """Call Claude API with prompt caching, return parsed content dict."""
    body = {
        "model": config.CLAUDE_MODEL,
        "max_tokens": config.CLAUDE_MAX_TOKENS,
        "system": [
            {"type": "text", "text": SYSTEM_PROMPT,
             "cache_control": {"type": "ephemeral"}}
        ],
        "messages": [{"role": "user", "content": build_user_prompt(page, data, pricing, sibling_links)}],
    }
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": config.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
            "anthropic-beta": "prompt-caching-2024-07-31",
        },
        json=body, timeout=60,
    )
    r.raise_for_status()
    resp = r.json()
    text = "".join(b["text"] for b in resp["content"] if b["type"] == "text")

    if resp.get("stop_reason") == "max_tokens" and _retry:
        body["max_tokens"] = config.CLAUDE_MAX_TOKENS
        body["messages"] = [{"role": "user",
            "content": build_user_prompt(page, data, pricing, sibling_links) +
            "\n\nIMPORTANT: keep it concise — 2 sections, 3 FAQs max, so the JSON fits in one response."}]
        r = requests.post("https://api.anthropic.com/v1/messages",
            headers={"x-api-key": config.ANTHROPIC_API_KEY,
                     "anthropic-version": "2023-06-01", "content-type": "application/json",
                     "anthropic-beta": "prompt-caching-2024-07-31"},
            json=body, timeout=60)
        r.raise_for_status()
        text = "".join(b["text"] for b in r.json()["content"] if b["type"] == "text")

    content = _extract_json(text)
    try:
        _validate_red_line(content)
    except ValueError:
        if _retry:
            warn = build_user_prompt(page, data, pricing, sibling_links) + (
                "\n\nCRITICAL: Your previous attempt mentioned 'poodle', 'doodle', or 'bernedoodle'. "
                "Rewrite with ZERO mention of those words anywhere — not even to say it's not one. "
                "State only what the breed IS (Bernese Mountain Dog x Cavalier King Charles Spaniel). Output ONLY the JSON.")
            r = requests.post("https://api.anthropic.com/v1/messages",
                headers={"x-api-key": config.ANTHROPIC_API_KEY,
                         "anthropic-version": "2023-06-01", "content-type": "application/json",
                         "anthropic-beta": "prompt-caching-2024-07-31"},
                json={"model": config.CLAUDE_MODEL, "max_tokens": config.CLAUDE_MAX_TOKENS,
                      "system": [{"type": "text", "text": SYSTEM_PROMPT,
                                  "cache_control": {"type": "ephemeral"}}],
                      "messages": [{"role": "user", "content": warn}]},
                timeout=60)
            r.raise_for_status()
            text = "".join(b["text"] for b in r.json()["content"] if b["type"] == "text")
            content = _extract_json(text)
        _validate_red_line(content)
    _fix_stale_year(content)
    _fix_health_guarantee(content)
    return content

def _fix_health_guarantee(content):
    """
    Safety net: rewrite any phrasing that presents the 12-YEAR tier as
    automatically 'included' / unconditional into accurate, conditional
    wording. The 1-year tier is left alone since it genuinely is automatic.
    Runs on every text field so it can't slip through regardless of the prompt.
    """
    import re
    def fix(text):
        if not isinstance(text, str):
            return text
        # "12-year health guarantee included" → conditional phrasing
        text = re.sub(
            r"12[\-\s]?year health guarantee\s+included",
            "12-year health guarantee (conditional on pet insurance + recommended food)",
            text, flags=re.IGNORECASE)
        # "includes ... a 12-year health guarantee" → "is backed by ..."
        text = re.sub(
            r"includes?\s+(a\s+)?12[\-\s]?year\s+health guarantee",
            r"is backed by a 12-year health guarantee (conditional on pet insurance + recommended food)",
            text, flags=re.IGNORECASE)
        return text

    def walk(obj):
        if isinstance(obj, str):
            return fix(obj)
        if isinstance(obj, list):
            return [walk(x) for x in obj]
        if isinstance(obj, dict):
            return {k: walk(v) for k, v in obj.items()}
        return obj

    for key in list(content.keys()):
        content[key] = walk(content[key])

def _fix_stale_year(content):
    """Safety net: replace any stale year (2020-2025) in title/meta with the current year."""
    import datetime, re
    cy = str(datetime.date.today().year)
    for field in ("title", "meta_description", "h1"):
        if content.get(field):
            content[field] = re.sub(r"\b20(2[0-5]|1\d)\b", cy, content[field])

def _extract_json(text):
    """Robustly extract a JSON object from model output."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1] if "```" in text[3:] else text
        text = text.removeprefix("json").strip().strip("`").strip()
    start = text.find("{")
    end   = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start:end+1]
    return json.loads(text)

def _validate_red_line(content):
    """Hard guard: reject any output that mentions poodle/doodle/bernedoodle."""
    blob = json.dumps(content).lower()
    for banned in ("poodle", "doodle", "bernedoodle"):
        if banned in blob:
            raise ValueError(f"RED LINE VIOLATION: output contained '{banned}' — page rejected")

if __name__ == "__main__":
    print("generator module — import and call generate_page_content()")
