#!/usr/bin/env python3
"""Turn an evidence folder into a printable writing-process report (HTML, prints to PDF).

The report is for the reviewer. It shows the recorded timeline,
how the drafts grew, which days had activity, where new passages came from, and
a hashed list of the exhibits.

Usage:
    python3 report.py <evidence-folder> [--drafts d1.docx d2.docx ...] [--sources notes.txt ...]
                      [--title "Essay title"] [--writer "Name"] [--summary summary.txt]
                      [--git <repo>] [--out report.html]

Drafts and sources are paths inside the evidence folder (or absolute paths). If you
omit them, Word/OpenDocument files are treated as drafts (ordered by their saved
date) and .txt/.md files as notes. --summary is a short plain-text statement in the
writer's own words; blank lines separate paragraphs.
"""

from __future__ import annotations

import argparse
import html
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import draft_diff  # noqa: E402
import timeline    # noqa: E402

REPO_URL = "https://github.com/forrestelliott/authored"
DRAFT_EXT = {".docx", ".docm", ".odt"}
NOTE_EXT = {".txt", ".md", ".rtf"}
e = html.escape


def resolve(paths: list[str] | None, base: Path) -> list[Path]:
    out = []
    for p in paths or []:
        cand = Path(p).expanduser()
        if not cand.is_absolute():
            hits = [base / p] + sorted(base.rglob(Path(p).name))
            cand = next((h for h in hits if h.is_file()), base / p)
        if not cand.is_file():
            sys.exit(f"Not found in evidence folder: {p}")
        out.append(cand)
    return out


def preview(passage: str, limit: int = 26) -> str:
    """First words of a passage, starting at a sentence boundary when the diff began mid-sentence."""
    ws = passage.split()
    if ws and not ws[0][0].isupper():
        for i, w in enumerate(ws[:15]):
            if w.endswith((".", "?", "!")) and i + 1 < len(ws):
                ws = ws[i + 1:]
                break
        else:
            ws = ["…"] + ws
    return " ".join(ws[:limit]) + (" …" if len(ws) > limit else "")


def stamp(dt: datetime, year: bool = False) -> str:
    """'Sun Sep 20, 21:18' or 'Sep 20, 2026 21:18' (portable: no %-d)."""
    return f"{dt:%b} {dt.day}, {dt:%Y %H:%M}" if year else f"{dt:%a %b} {dt.day}, {dt:%H:%M}"


def short_day(d: date | datetime) -> str:
    return f"{d.strftime('%b')} {d.day}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder")
    ap.add_argument("--drafts", nargs="*")
    ap.add_argument("--sources", nargs="*")
    ap.add_argument("--title", default="")
    ap.add_argument("--writer", default="")
    ap.add_argument("--summary", help="text file (or literal text) with the writer's short statement")
    ap.add_argument("--git")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    tl, manifest, base = timeline.build(args.folder, args.git)
    docs = {d["file"]: d for d in tl.documents}
    label_of = lambda p: p.relative_to(base).as_posix() if base in p.parents else p.name

    def saved(p: Path) -> datetime:
        d = docs.get(label_of(p), {})
        if d.get("modified"):
            return d["modified"]
        rec = next((r for r in (manifest or {}).get("files", []) if r["archive_path"].endswith(label_of(p))), None)
        if rec and rec.get("modified"):
            return timeline.parse_dt(rec["modified"])
        return datetime.fromtimestamp(p.stat().st_mtime).astimezone()

    files = sorted(p for p in base.rglob("*") if p.is_file() and not p.name.startswith("."))
    drafts = resolve(args.drafts, base) if args.drafts else sorted((p for p in files if p.suffix.lower() in DRAFT_EXT), key=saved)
    sources = resolve(args.sources, base) if args.sources is not None else [p for p in files if p.suffix.lower() in NOTE_EXT]
    sources = [p for p in sources if p not in drafts]
    if not drafts:
        sys.exit("No drafts found. Pass --drafts.")

    # ---- analysis -------------------------------------------------------
    src_words = {p.name: draft_diff.words(draft_diff.extract(p)) for p in sources}
    toks = [draft_diff.words(draft_diff.extract(p)) for p in drafts]
    if not any(toks):
        sys.exit("No readable words found in the selected drafts. Choose a non-empty draft or export it as text.")
    rows = []
    for i, (p, t) in enumerate(zip(drafts, toks)):
        meta = docs.get(label_of(p), {})
        row = {"name": p.name, "when": saved(p), "words": len(t), "minutes": meta.get("editing_minutes"),
               "sessions": meta.get("editing_sessions"), "kept": len(t), "new": 0, "traced": 0, "passages": []}
        if i:
            c = draft_diff.compare(toks[i - 1], t)
            row.update(kept=len(t) - c["added"], new=c["added"], removed=c["removed"], retained=c["retained_pct"])
            for n, passage in c["top_inserts"]:
                if n < 40:
                    continue
                origin = draft_diff.trace(passage.split(), src_words) if src_words else None
                if origin:
                    row["traced"] += round(n * origin[1])
                row["passages"].append({"words": n, "preview": preview(passage),
                                        "source": origin[0] if origin else None,
                                        "share": round(origin[1] * 100) if origin else None,
                                        "large": n >= draft_diff.FLAG_MIN_WORDS and n / max(len(t), 1) >= draft_diff.FLAG_SHARE})
        rows.append(row)

    # A document's own metadata outranks its filesystem dates, which change when files are copied.
    has_meta = {d["file"] for d in tl.documents if d.get("modified")}
    events = [ev for ev in tl.events if not ("filesystem" in ev["kind"] and ev["source"] in has_meta)]
    first, last = events[0]["when"].date(), events[-1]["when"].date()
    active = {}
    for ev in events:
        active.setdefault(ev["when"].date(), []).append(ev)
    span_days = (last - first).days + 1

    def num(v):
        try:
            return int(v)
        except (TypeError, ValueError):
            return None
    minutes = max((num(d.get("editing_minutes")) or 0 for d in tl.documents), default=0)
    sessions = max((num(d.get("editing_sessions")) or 0 for d in tl.documents), default=0)

    stats = [(f"{span_days}", "days in the recorded timeline"),
             (f"{len(active)}", "dates with recorded activity"),
             (f"{len(drafts)}", "saved drafts"),
             (f"{rows[-1]['words']:,}", "words in the final draft")]
    editor_stats = []
    if minutes:
        h, m = divmod(minutes, 60)
        editor_stats.append((f"{h}h {m:02d}m" if h else f"{m}m") + " editing time recorded by the editor")
    if sessions:
        editor_stats.append(f"{sessions} recorded editing-session markers")

    # ---- growth chart (SVG) --------------------------------------------
    W, H, L, R, T, B = 760, 250, 56, 24, 26, 46
    t0 = datetime.combine(first, datetime.min.time()).astimezone()
    t1 = datetime.combine(last + timedelta(days=1), datetime.min.time()).astimezone()
    span = (t1 - t0).total_seconds() or 1
    ymax = max(r["words"] for r in rows) * 1.18
    x = lambda dt: L + (W - L - R) * (dt - t0).total_seconds() / span
    y = lambda v: T + (H - T - B) * (1 - v / ymax)
    svg = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Word count of each draft over time">']
    step = max(1, round(ymax / 4 / 100) * 100)
    for v in range(0, int(ymax), step):
        svg.append(f'<line x1="{L}" x2="{W - R}" y1="{y(v):.1f}" y2="{y(v):.1f}" class="grid"/>'
                   f'<text x="{L - 8}" y="{y(v) + 4:.1f}" class="axis" text-anchor="end">{v:,}</text>')
    d0 = first
    tick_every = 1 if span_days <= 16 else 2 if span_days <= 32 else 7
    while d0 <= last:
        if (d0 - first).days % tick_every == 0:
            dx = x(datetime.combine(d0, datetime.min.time()).astimezone() + timedelta(hours=12))
            svg.append(f'<text x="{dx:.1f}" y="{H - B + 18}" class="axis" text-anchor="middle">{d0.day}</text>')
        d0 += timedelta(days=1)
    svg.append(f'<text x="{L}" y="{H - 6}" class="axis">{e(first.strftime("%B %Y"))}</text>')
    pts = [(x(r["when"]), y(r["words"])) for r in rows]
    area = f'M{pts[0][0]:.1f},{y(0):.1f} ' + " ".join(f"L{a:.1f},{b:.1f}" for a, b in pts) + f' L{pts[-1][0]:.1f},{y(0):.1f} Z'
    svg.append(f'<path d="{area}" class="area"/>')
    svg.append('<polyline points="' + " ".join(f"{a:.1f},{b:.1f}" for a, b in pts) + '" class="line"/>')
    for (a, b), r in zip(pts, rows):
        svg.append(f'<circle cx="{a:.1f}" cy="{b:.1f}" r="5" class="dot"/>'
                   f'<text x="{a:.1f}" y="{b - 12:.1f}" class="lbl" text-anchor="middle">{r["words"]:,}</text>')
    for p in sources:
        sx = x(saved(p))
        svg.append(f'<path d="M{sx:.1f},{y(0) - 7:.1f} l6,7 -6,7 -6,-7 Z" class="note"><title>{e(p.name)}</title></path>'
                   f'<text x="{sx + 9:.1f}" y="{y(0) - 4:.1f}" class="nlbl">{e(p.stem.replace("_", " "))}</text>')
    svg.append("</svg>")

    # ---- calendar -------------------------------------------------------
    start = first - timedelta(days=first.weekday())
    end = last + timedelta(days=6 - last.weekday())
    draft_days = {r["when"].date() for r in rows}
    note_days = {saved(p).date() for p in sources}
    cal = ['<div class="cal">'] + [f'<div class="dow">{d}</div>' for d in "MTWTFSS"]
    d0 = start
    while d0 <= end:
        n = len(active.get(d0, []))
        cls = "day" + (" on" if n else "") + (" out" if d0 < first or d0 > last else "")
        mark = '<span class="m d"></span>' if d0 in draft_days else '<span class="m n"></span>' if d0 in note_days else ""
        tip = "; ".join(sorted({ev["source"].split("/")[-1] for ev in active.get(d0, [])}))
        cal.append(f'<div class="{cls}" title="{e(short_day(d0))}{": " + e(tip) if tip else ""}"><span>{d0.day}</span>{mark}</div>')
        d0 += timedelta(days=1)
    cal.append("</div>")

    # ---- draft bars -----------------------------------------------------
    wmax = max(r["words"] for r in rows)
    bars = []
    for i, r in enumerate(rows):
        pct = lambda v: 100 * v / wmax
        other_new = r["new"] - r["traced"]
        seg = (f'<span class="k" style="width:{pct(r["kept"]):.2f}%"></span>'
               f'<span class="t" style="width:{pct(r["traced"]):.2f}%"></span>'
               f'<span class="w" style="width:{pct(other_new):.2f}%"></span>') if i else f'<span class="w" style="width:{pct(r["words"]):.2f}%"></span>'
        meta = [f'{r["words"]:,} words']
        if i:
            meta.append(f'+{r["new"]:,} / −{r["removed"]:,}')
            meta.append(f'{r["retained"]}% of previous kept')
        if r["minutes"]:
            meta.append(f'{int(r["minutes"]):,} min editing')
        passages = ""
        for ps in r["passages"]:
            tag = (f'<span class="tag src">overlap with {e(ps["source"])} · {ps["share"]}% shared wording</span>' if ps["source"]
                   else '<span class="tag one">new since the previous draft</span>' if ps["large"] else "")
            passages += f'<li><b>{ps["words"]:,} new words</b> {tag}<q>{e(ps["preview"])}</q></li>'
        bars.append(
            f'<article class="draft"><div class="dh"><span class="dn">{i + 1:02d}</span><span class="nm">{e(r["name"])}</span>'
            f'<span class="dt">{e(stamp(r["when"]))}</span></div>'
            f'<div class="bar">{seg}</div><div class="meta">{" · ".join(meta)}</div>'
            + (f'<ul class="ps">{passages}</ul>' if passages else "") + "</article>")

    # ---- exhibits -------------------------------------------------------
    exhibit_rows = ""
    if manifest:
        for n, rec in enumerate(manifest["files"], 1):
            nm = Path(rec["archive_path"]).name
            mod = timeline.parse_dt(rec.get("modified"))
            exhibit_rows += (f'<tr><td>{n:02d}</td><th scope="row">{e(nm)}</th><td>{e(stamp(mod, year=True)) if mod else ""}</td>'
                             f'<td>{rec["size_bytes"]:,} B</td><td class="h">{e(rec["sha256"])}</td></tr>')

    summary_html = ""
    if args.summary:
        sp = Path(args.summary).expanduser()
        text = sp.read_text() if sp.is_file() else args.summary
        summary_html = "".join(f"<p>{e(par.strip())}</p>" for par in text.split("\n\n") if par.strip())

    title = args.title or rows[-1]["name"]
    taken_dt = datetime.fromisoformat(manifest["snapshot_taken"]) if manifest else datetime.now()
    taken = f"{short_day(taken_dt)}, {taken_dt.year}"
    body = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Writing process: {e(title)}</title>
<style>
:root{{--ink:#202b2a;--mute:#596562;--rule:#dce1db;--paper:#fffefb;--kept:#c9cdc5;--new:#375e78;--src:#35765d;--soft:#f3f5ef}}
*{{box-sizing:border-box}}
body{{margin:0;background:#eaece6;color:var(--ink);font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;-webkit-font-smoothing:antialiased}}
a{{color:inherit}}
.page{{max-width:1000px;margin:40px auto;background:var(--paper);padding:42px 56px 30px;border-top:4px solid var(--src);box-shadow:0 8px 48px #26352c0b}}
.masthead{{display:flex;justify-content:space-between;align-items:baseline;border-bottom:1px solid var(--rule);padding-bottom:16px;margin-bottom:30px;gap:20px}}
.brand{{font:600 25px Georgia,serif;letter-spacing:-1px}}
.kicker,.eyebrow{{font-size:10px;font-weight:650;letter-spacing:.13em;text-transform:uppercase}}
.kicker{{color:var(--mute)}}
h1{{font:400 42px/1.12 Georgia,"Iowan Old Style",serif;letter-spacing:-1.25px;margin:0 0 22px;max-width:20ch;overflow-wrap:anywhere}}
.by{{display:flex;flex-wrap:wrap;gap:16px 36px;font-size:13px;padding-bottom:24px}}
.by div{{display:grid;gap:4px}}
.by .eyebrow{{color:var(--mute);font-size:9px}}
.summary{{border-left:2px solid var(--src);padding:4px 0 4px 20px;max-width:77ch;margin:0 0 28px}}
.summary .eyebrow{{color:var(--src);margin-bottom:8px}}
.summary p{{font-size:14px;line-height:1.65;margin:0 0 8px}}
.summary p:last-child{{margin:0}}
.stats{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));border-top:1px solid var(--rule);border-bottom:1px solid var(--rule);padding:18px 0;margin:0 0 30px}}
.stat{{padding:0 18px;border-left:1px solid var(--rule)}}
.stat:first-child{{padding-left:0;border:0}}
.stat b{{display:block;font:400 36px/1.1 Georgia,serif;font-variant-numeric:lining-nums tabular-nums;margin-bottom:7px}}
.stat span{{display:block;font-size:11px;line-height:1.45;color:var(--mute);max-width:16ch}}
.section-heading{{display:flex;align-items:baseline;gap:12px;margin:28px 0 18px;padding-top:18px;border-top:1px solid var(--rule)}}
.section-heading h2{{font:400 24px/1.2 Georgia,serif;letter-spacing:-.35px;margin:0}}
.section-heading .section-no{{font:11px ui-monospace,monospace;color:var(--src)}}
.timeline-heading{{border:0;padding:0;margin-top:0}}
.timeline-grid{{display:grid;grid-template-columns:minmax(0,2.2fr) minmax(0,1fr);gap:28px}}
.chart{{min-width:0}}
svg{{width:100%;height:auto;display:block;overflow:visible}}
.grid{{stroke:var(--rule)}} .axis{{font-size:11px;fill:var(--mute)}}
.area{{fill:var(--new);opacity:.07}} .line{{fill:none;stroke:var(--new);stroke-width:2.2}}
.dot{{fill:var(--paper);stroke:var(--new);stroke-width:2.4}} .lbl{{font-size:12px;font-weight:650;fill:var(--ink)}}
.note{{fill:var(--src)}} .nlbl{{font-size:10px;fill:var(--src)}}
.legend{{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:11px;color:var(--mute);margin-top:12px}}
.legend i{{display:inline-block;width:9px;height:9px;border-radius:1px;margin-right:5px;vertical-align:0}}
.activity{{padding:16px;background:var(--soft);border:1px solid var(--rule)}}
.activity h3{{font:600 11px/1.4 -apple-system,sans-serif;margin:0 0 10px}}
.cal{{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:3px}}
.dow{{font-size:9px;color:var(--mute);text-align:center}}
.day{{position:relative;aspect-ratio:1;border-radius:2px;font-size:10px;color:var(--mute);display:flex;align-items:center;justify-content:center}}
.day.on{{background:var(--new);color:#fff}} .day.out{{visibility:hidden}}
.m{{position:absolute;bottom:2px;width:3px;height:3px;border-radius:50%;background:#fff}}
.activity p{{font-size:10px;line-height:1.5;color:var(--mute);margin:10px 0 0}}
.editor-stats{{font-size:11px;color:var(--mute);margin:14px 0 0;padding-top:12px;border-top:1px solid var(--rule)}}
.editor-stats b{{font-weight:600;color:var(--ink)}}
.draft-legend{{margin:-4px 0 18px}}
.draft{{padding:18px 0;border-top:1px solid var(--rule);break-inside:avoid}}
.draft:first-child{{border-top:0;padding-top:0}}
.dh{{display:flex;gap:12px;align-items:baseline}}
.dn{{font:11px ui-monospace,monospace;color:var(--mute);flex:none}}
.nm{{font-size:13px;font-weight:650;overflow-wrap:anywhere;min-width:0}}
.dt{{margin-left:auto;color:var(--mute);font-size:11px;white-space:nowrap}}
.bar{{display:flex;height:8px;margin:12px 0 7px}}
.bar span{{display:block;height:100%}} .bar .k{{background:var(--kept)}} .bar .t{{background:var(--src)}} .bar .w{{background:var(--new)}}
.meta{{font-size:11px;color:var(--mute);line-height:1.55}}
.ps{{list-style:none;padding:0;margin:12px 0 0}}
.ps li{{font-size:11px;margin:10px 0 0;padding-left:12px;border-left:2px solid var(--rule)}}
.ps q{{display:block;margin-top:5px;color:var(--mute);font:italic 13px/1.5 Georgia,serif;quotes:"“" "”"}}
.tag{{display:inline;font-size:10px;padding:2px 5px;margin-left:6px;box-decoration-break:clone;-webkit-box-decoration-break:clone;overflow-wrap:anywhere}}
.tag.src{{background:#edf3ec;color:#285b43}} .tag.one{{background:#f5efdf;color:#71581f}}
.method-note{{margin:0;padding:12px 14px;background:var(--soft);border-left:2px solid var(--rule)}}
.table-wrap{{width:100%;overflow-x:auto}}
table{{width:100%;border-collapse:collapse;font-size:10px;text-align:left}}
caption{{text-align:left;font-size:11px;color:var(--mute);margin:0 0 12px}}
thead th{{font-size:9px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--mute);border-bottom:1px solid var(--ink);padding:0 12px 8px 0}}
tbody th,td{{font-weight:400;border-bottom:1px solid var(--rule);padding:10px 12px 10px 0;vertical-align:top}}
tbody th{{font-weight:600;overflow-wrap:anywhere;max-width:160px}}
td.h{{font:9px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--mute);word-break:break-all;width:31%;padding-right:0}}
.evidence-note{{font-size:11px;color:var(--mute);line-height:1.6;margin:18px 0 24px;max-width:90ch}}
.footer{{display:flex;justify-content:space-between;gap:20px;border-top:1px solid var(--rule);padding-top:14px;font-size:10px;color:var(--mute)}}
.footer a{{font-weight:650;text-decoration:none}}
@media screen and (max-width:720px){{
 .page{{padding:24px;margin:0;border-top-width:3px}} h1{{font-size:35px}} .masthead{{margin-bottom:24px}}
 .timeline-grid{{grid-template-columns:1fr}} .activity{{max-width:320px}} .stats{{gap:20px 0;grid-template-columns:repeat(2,minmax(0,1fr))}}
 .stat:nth-child(3){{padding-left:0;border:0}} .stat b{{font-size:32px}} .dh{{flex-wrap:wrap;gap:4px 8px}}
 .dt{{width:100%;margin:0 0 0 24px}} table{{min-width:570px}} .footer{{flex-wrap:wrap}}
}}
@media print{{
 body{{background:#fff;font-size:10pt}} .page{{max-width:none;margin:0;padding:0;box-shadow:none;border:0}}
 .masthead{{padding-bottom:10px;margin-bottom:20px}} h1{{font-size:32pt}} .summary p{{font-size:10pt}}
 .overview{{break-after:page}} .details .section-heading:first-child{{margin-top:0;border:0;padding-top:0}}
 .draft{{padding:8px 0}} .ps{{margin-top:7px}} .ps li{{margin-top:6px}} .ps q{{font-size:10pt;margin-top:3px}}
 .section-heading{{break-after:avoid;margin:14px 0 12px;padding-top:12px}}
 .draft-legend{{margin-bottom:12px}} .bar{{margin-top:8px}} .method-note{{padding:8px 10px}}
 tbody th,td{{padding-top:6px;padding-bottom:6px}} .evidence-note{{margin:12px 0;font-size:10px}}
 .table-wrap{{overflow:visible}} tr,.activity,.stats{{break-inside:avoid}} table{{min-width:0}}
 .footer{{margin-top:10px;padding-top:10px}} *{{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
}}
@page{{size:A4;margin:17mm}}
</style></head><body><main class="page">
<section class="overview" aria-label="Writing overview">
<header>
<div class="masthead"><span class="brand">Authored.</span><span class="kicker">Writing process report</span></div>
<h1>{e(title)}</h1>
<div class="by">
{f'<div><span class="eyebrow">Prepared for</span><span>{e(args.writer)}</span></div>' if args.writer else ''}
<div><span class="eyebrow">Recorded period</span><span>{e(short_day(first))} – {e(short_day(last))}, {last.year}</span></div>
{f'<div><span class="eyebrow">Evidence preserved</span><span>{e(taken)}</span></div>' if manifest else ''}
</div>
</header>
{f'<section class="summary" aria-label="Writer account"><div class="eyebrow">The writer’s account</div>{summary_html}</section>' if summary_html else ''}
<div class="stats">{"".join(f'<div class="stat"><b>{e(v)}</b><span>{e(k)}</span></div>' for v, k in stats)}</div>
<div class="section-heading timeline-heading"><span class="section-no">01</span><h2>The writing timeline</h2></div>
<div class="timeline-grid"><div class="chart">
{"".join(svg)}
<div class="legend"><span><i style="background:var(--new)"></i>Words in each saved draft</span>{'<span><i style="background:var(--src)"></i>Notes &amp; outlines</span>' if sources else ''}</div>
</div><aside class="activity"><h3>{e(first.strftime('%B %Y'))}{' – ' + e(last.strftime('%B %Y')) if (first.year, first.month) != (last.year, last.month) else ''}</h3>
{"".join(cal)}
<p><b>{len(active)} dates with recorded activity.</b> Highlighted dates come from document records and file timestamps.</p>
</aside></div>
{f'<p class="editor-stats"><b>Editor metadata</b> &nbsp; {e(" · ".join(editor_stats))}. These fields support the account; they do not verify time spent writing.</p>' if editor_stats else ''}
</section>
<section class="details" aria-label="Drafts and evidence">
<div class="section-heading"><span class="section-no">02</span><h2>How the drafts developed</h2></div>
<div class="legend draft-legend"><span><i style="background:var(--kept)"></i>Carried forward</span><span><i style="background:var(--src)"></i>Wording also in notes</span><span><i style="background:var(--new)"></i>Other new text</span></div>
<div class="drafts">{"".join(bars)}</div>
<p class="meta method-note">Green counts wording in the highlighted passages that matches five-word phrases in the notes, ignoring case and punctuation. A match suggests a connection, not proof of origin. Additions appeared between saved drafts; they do not establish a single paste or writing event.</p>
{f'<div class="section-heading"><span class="section-no">03</span><h2>The evidence file</h2></div><div class="table-wrap"><table><caption>{len(manifest["files"])} preserved files · Full SHA-256 fingerprints for verification</caption><thead><tr><th scope="col">No.</th><th scope="col">File</th><th scope="col">Last modified</th><th scope="col">Size</th><th scope="col">SHA-256</th></tr></thead><tbody>{exhibit_rows}</tbody></table></div>' if exhibit_rows else ''}
<p class="evidence-note"><b>Reading this evidence.</b> Dates and editing statistics are recorded by software and can change when files are copied, synced or converted. They support the writer’s account; drafts, notes and live version history remain the primary evidence. File fingerprints confirm file identity, not authorship.</p>
</section>
<footer class="footer"><span>Prepared with <a href="{REPO_URL}">Authored</a> · Writing, with a record.</span><span>{'Snapshot preserved ' + e(taken) if manifest else 'No snapshot manifest supplied'}</span></footer>
</main></body></html>
"""
    # Write into snapshot folders (ours); never add files to a writer's own folder by default.
    out = Path(args.out) if args.out else (Path(args.folder) / "report.html" if manifest else Path("report.html"))
    out.write_text(body)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
