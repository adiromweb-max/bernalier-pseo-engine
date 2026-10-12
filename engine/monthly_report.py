"""
monthly_report.py — builds the monthly report from the weekly Search Console snapshots.

Outputs (in reports/):
  YYYY-MM-client.html    English, for Andrew. Leads with progress; "areas we're strengthening"
                         is framed gently with the way forward.
  YYYY-MM-internal.md    Hebrew, for Adi. Same numbers + the things that need action.
"""
import json, os, glob, datetime, html
import config

DATA = config.DATA_DIR
OUT = os.path.join(os.path.dirname(DATA), "reports")


def load(path, default=None):
    try:
        return json.load(open(path))
    except Exception:
        return default


def pct(a, b):
    if not b:
        return None
    return round((a - b) / b * 100)


def trend_word(delta):
    if delta is None:
        return "tracking has started"
    return f"up {delta}%" if delta > 0 else ("steady" if delta == 0 else f"{delta}% vs prior period")


def slug(u):
    return u.rstrip("/").split("/")[-1].replace("bernalier-puppy-price-", "").replace("-", " ").title()


def main():
    os.makedirs(OUT, exist_ok=True)
    snaps = sorted(glob.glob(os.path.join(DATA, "gsc", "snapshot-*.json")))
    snap = load(snaps[-1]) if snaps else None
    idx = load(os.path.join(DATA, "index_report.json"), {})
    ins = load(os.path.join(DATA, "gsc_insights.json"), {})
    state = load(config.STATE_FILE, {"completed": []})
    pm = load(config.PAGEMAP, {"pages": []})
    month = datetime.date.today().strftime("%Y-%m")
    mname = datetime.date.today().strftime("%B %Y")

    cur = (snap or {}).get("totals", {})
    prev = (snap or {}).get("prev_totals", {})
    d_impr = pct(cur.get("impressions", 0), prev.get("impressions", 0))
    d_clk = pct(cur.get("clicks", 0), prev.get("clicks", 0))
    published = idx.get("published", 0)
    indexed = idx.get("indexed", 0)
    built = len(state.get("completed", []))
    total = len(pm.get("pages", []))

    # pages gaining traction
    movers = []
    if snap:
        for u, p in snap["pages"].items():
            before = snap["prev_pages"].get(u, {}).get("impressions", 0)
            movers.append((p["impressions"] - before, u, p))
        movers.sort(reverse=True)
    top = [m for m in movers if m[0] > 0][:5]

    e = html.escape
    rows = ""
    if snap:
        rows = (f"<tr><td>Search impressions</td><td>{cur['impressions']:,}</td><td>{trend_word(d_impr)}</td></tr>"
                f"<tr><td>Clicks from Google</td><td>{cur['clicks']:,}</td><td>{trend_word(d_clk)}</td></tr>"
                f"<tr><td>Pages appearing in search</td><td>{cur['pages_with_impressions']}</td><td></td></tr>")
    rows += (f"<tr><td>Location guides live</td><td>{published}</td><td></td></tr>"
             f"<tr><td>Confirmed in Google's index</td><td>{indexed} of {published}</td><td></td></tr>")
    top_items = []
    for _, u, p in top:
        pos = ", average position " + str(p["position"]) if p["position"] else ""
        top_items.append("<li><b>" + e(slug(u)) + "</b> — " + format(p["impressions"], ",") + " impressions" + pos + "</li>")
    top_html = "".join(top_items)
    strengthen = ins.get("strengthen", [])[:5]
    str_html = "".join(f"<li>{e(slug(s['page']))} guide: next focus is “{e(s['queries'][0]['q'])}”</li>" for s in strengthen)
    exp = ins.get("expansion", {})
    added = exp.get("added", [])
    head = ("Search visibility for the new location guides is growing."
            if (d_impr or 0) > 0 else
            "The new location guides are being published steadily and Google is discovering them.")

    client = f"""<!doctype html><meta charset="utf-8"><title>BernalierPups.com — SEO Progress, {mname}</title>
<style>body{{font:16px/1.55 system-ui,sans-serif;max-width:720px;margin:32px auto;padding:0 16px;color:#1f2933}}
table{{border-collapse:collapse;width:100%}}td{{padding:8px 10px;border-bottom:1px solid #e3e7ea}}h2{{margin-top:28px}}</style>
<h1>BernalierPups.com — SEO Progress, {mname}</h1>
<p><b>{head}</b></p>
<table>{rows}</table>
{f'<h2>Guides gaining traction</h2><ul>{top_html}</ul>' if top_html else ''}
<h2>This month</h2>
<ul><li>{built} of {total} planned location guides are built; new ones are released gradually (a few each week) so growth looks natural to Google.</li>
{f'<li>{len(added)} new locations were added to the plan based on what people are actually searching for.</li>' if added else ''}
<li>Each guide links to the others in its state, strengthening the whole group together.</li></ul>
{f'<h2>Next focus areas</h2><ul>{str_html}</ul>' if str_html else ''}
<p style="color:#6b7780;font-size:14px">New pages typically take several weeks to build visibility; this report tracks that progress month by month.</p>"""
    open(os.path.join(OUT, f"{month}-client.html"), "w").write(client)

    # ── internal Hebrew notes ──
    L = [f"# דוח פנימי — BernalierPups — {mname}", ""]
    if snap:
        L += ["## מגמה", f"- חשיפות: {cur['impressions']:,} ({'+' if (d_impr or 0)>0 else ''}{d_impr}% מול התקופה הקודמת)" if d_impr is not None else f"- חשיפות: {cur['impressions']:,}",
              f"- קליקים: {cur['clicks']:,}" + (f" ({'+' if d_clk>0 else ''}{d_clk}%)" if d_clk is not None else ""),
              f"- עמודים עם חשיפות: {cur['pages_with_impressions']}", ""]
    else:
        L += ["## מגמה", "- עדיין אין נתוני Search Console (הלולאה תתחיל לצבור בהרצה הבאה).", ""]
    L += ["## מצב המערכת", f"- פורסמו: {published}", f"- באינדקס של גוגל: {indexed} מתוך {published}",
          f"- נבנו: {built} מתוך {total} במפה", ""]
    if added:
        L += ["## הורחב אוטומטית החודש", *[f"- {a}" for a in added], ""]
    flags = []
    for c in ins.get("cannibalization", [])[:5]:
        flags.append(f"קניבליזציה על השאילתה: {c['query']} ({len(c['pages'])} עמודים)")
    for l in ins.get("low_ctr", [])[:5]:
        flags.append(f"CTR נמוך ({l['ctr']*100:.1f}%) בעמוד: {slug(l['page'])} — לשקול שכתוב כותרת/תיאור")
    if flags:
        L += ["## דורש תשומת לב", *[f"- {f}" for f in flags], ""]
    if strengthen:
        L += ["## הזדמנויות חיזוק (שאילתות במקום 6-30)"]
        for s in strengthen:
            L.append(f"- {slug(s['page'])}: " + ", ".join(q['q'] for q in s['queries'][:3]))
        L.append("")
    open(os.path.join(OUT, f"{month}-internal.md"), "w").write("\n".join(L))
    print(f"[report] wrote reports/{month}-client.html and {month}-internal.md")


if __name__ == "__main__":
    main()
