#!/usr/bin/env python3
"""Show how a piece of writing changed from draft to draft.

For each pair of consecutive drafts, reports words added and removed, how much of
the earlier draft survived, and the largest single block of new text. Large
insertions are flagged so the writer can explain them (and find the notes or
section file they came from) before a reviewer asks.

Reads .txt, .md, .docx, .odt, .html and .rtf directly; .pdf through `pdftotext`
if it is installed. Source files are only read.

Usage:
    python3 draft_diff.py <draft1> <draft2> [...] [--sources notes.txt ...] [--sort name|mtime]
                          [--out drafts.md] [--html drafts.html]

--sources lists other evidence (notes, outlines, section files). Each large new
passage is checked against them, so text moved in from notes can be traced.
"""

from __future__ import annotations

import argparse
import difflib
import html
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
TEXT_NS = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"
FLAG_MIN_WORDS = 150      # an insertion at least this long ...
FLAG_SHARE = 0.25         # ... that is also this share of the new draft gets flagged
TRACE_MIN_WORDS = 40      # passages at least this long are traced against --sources
TRACE_MATCH = 0.35        # share of a passage's wording found in a source to call it a match


def docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    paras = []
    for p in root.iter(W + "p"):
        parts = []
        for el in p.iter():
            if el.tag == W + "t" and el.text:
                parts.append(el.text)
            elif el.tag in (W + "tab", W + "br"):
                parts.append(" ")
        paras.append("".join(parts))
    return "\n".join(paras)   # w:delText (tracked deletions) is intentionally excluded


def odt_text(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("content.xml"))
    return "\n".join("".join(p.itertext()) for p in root.iter() if p.tag in (TEXT_NS + "p", TEXT_NS + "h"))


def rtf_text(raw: str) -> str:
    raw = re.sub(r"\\par[d]?", "\n", raw)
    raw = re.sub(r"\{\\\*[^{}]*\}", "", raw)
    raw = re.sub(r"\\'[0-9a-f]{2}", "", raw)
    raw = re.sub(r"\\[a-zA-Z]+-?\d* ?", "", raw)
    return raw.replace("{", "").replace("}", "")


def extract(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in (".docx", ".docm"):
        return docx_text(path)
    if ext == ".odt":
        return odt_text(path)
    if ext == ".pdf":
        if not shutil.which("pdftotext"):
            sys.exit(f"{path.name}: install poppler (pdftotext) to read PDFs, or export the draft as .docx or .txt.")
        return subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True, check=True).stdout
    raw = path.read_text(errors="replace")
    if ext in (".html", ".htm"):
        raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
        return html.unescape(re.sub(r"<[^>]+>", " ", raw))
    if ext == ".rtf":
        return rtf_text(raw)
    return raw


def words(text: str) -> list[str]:
    return re.findall(r"\S+", text)


def compare(prev: list[str], cur: list[str]) -> dict:
    sm = difflib.SequenceMatcher(None, prev, cur, autojunk=False)
    kept = sum(b.size for b in sm.get_matching_blocks())
    added = removed = 0
    inserts = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op in ("insert", "replace"):
            added += j2 - j1
            inserts.append((j2 - j1, j1, j2))
        if op in ("delete", "replace"):
            removed += i2 - i1
    inserts.sort(reverse=True)
    return {
        "kept": kept,
        "added": added,
        "removed": removed,
        "retained_pct": round(100 * kept / len(prev)) if prev else 0,
        "top_inserts": [(n, " ".join(cur[j1:j2])) for n, j1, j2 in inserts[:3]],
    }


def shingle_coverage(passage: list[str], source: list[str], n: int = 5) -> float:
    """Share of the passage's words covered by n-word phrases that also occur in the source.

    Order-independent, so it still finds notes that were rearranged or woven into prose.
    """
    norm = lambda toks: [re.sub(r"\W+", "", t.lower()) for t in toks]
    p, s = norm(passage), norm(source)
    grams = {tuple(s[i:i + n]) for i in range(len(s) - n + 1)}
    covered = [False] * len(p)
    for i in range(len(p) - n + 1):
        if tuple(p[i:i + n]) in grams:
            covered[i:i + n] = [True] * n
    return sum(covered) / len(p) if p else 0.0


def trace(passage: list[str], sources: dict[str, list[str]]) -> tuple[str, float] | None:
    """Return the source sharing the most wording with this passage, if it shares enough."""
    best = None
    for name, toks in sources.items():
        found = shingle_coverage(passage, toks)
        if found >= TRACE_MATCH and (best is None or found > best[1]):
            best = (name, found)
    return best


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("drafts", nargs="+", help="draft files, earliest first (or use --sort)")
    ap.add_argument("--sources", nargs="*", default=[], help="notes, outlines or section files to trace new passages to")
    ap.add_argument("--sort", choices=["given", "name", "mtime"], default="given")
    ap.add_argument("--out", help="write Markdown here (default: print)")
    ap.add_argument("--html", help="also write a side-by-side HTML diff of each step here")
    args = ap.parse_args()

    paths = [Path(p).expanduser() for p in args.drafts]
    for p in paths:
        if not p.is_file():
            sys.exit(f"Not found: {p}")
    if len(paths) < 2:
        sys.exit("Give at least two drafts.")
    if args.sort == "name":
        paths.sort(key=lambda p: p.name)
    elif args.sort == "mtime":
        paths.sort(key=lambda p: p.stat().st_mtime)

    texts = [extract(p) for p in paths]
    toks = [words(t) for t in texts]
    sources = {Path(s).name: words(extract(Path(s).expanduser())) for s in args.sources}

    lines = ["# How the drafts changed", "",
             "| # | Draft | Modified | Words | Added | Removed | Kept from previous |",
             "|---|-------|----------|-------|-------|---------|--------------------|"]
    steps = []
    for i, (p, t) in enumerate(zip(paths, toks)):
        mod = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        if i == 0:
            lines.append(f"| 1 | {p.name} | {mod} | {len(t):,} | | | |")
            continue
        c = compare(toks[i - 1], t)
        steps.append((paths[i - 1], p, c, len(t)))
        lines.append(f"| {i + 1} | {p.name} | {mod} | {len(t):,} | {c['added']:,} | {c['removed']:,} | {c['retained_pct']}% |")

    lines += ["", "Modified times are the files' current filesystem times. Use the snapshot manifest for the originals' times.", ""]

    flagged, traced = [], []
    for prev_p, cur_p, c, total in steps:
        lines += [f"## {prev_p.name} → {cur_p.name}", ""]
        lines.append(f"{c['added']:,} words added, {c['removed']:,} removed, {c['retained_pct']}% of the previous draft kept.")
        lines.append("")
        if c["top_inserts"]:
            lines.append("Largest new passages:")
            lines.append("")
            for n, passage in c["top_inserts"]:
                preview = " ".join(passage.split()[:30]) + (" …" if n > 30 else "")
                mark = ""
                origin = trace(passage.split(), sources) if sources and n >= TRACE_MIN_WORDS else None
                if origin:
                    mark = f" ({round(origin[1] * 100)}% of its wording also appears in **{origin[0]}**)"
                    traced.append((cur_p.name, n, origin[0], round(origin[1] * 100)))
                elif n >= FLAG_MIN_WORDS and total and n / total >= FLAG_SHARE:
                    mark = " **(large single insertion: note where this text came from)**"
                    flagged.append((cur_p.name, n))
                lines.append(f"- {n:,} words{mark}: \"{preview}\"")
            lines.append("")

    lines += ["## Summary", ""]
    if len(toks) >= 2:
        lines.append(f"The text went from {len(toks[0]):,} words in {paths[0].name} to {len(toks[-1]):,} words in "
                     f"{paths[-1].name} across {len(paths)} drafts.")
    if traced:
        lines.append("")
        lines.append("Shared wording with other evidence: " + "; ".join(
            f"a {n:,}-word passage in {name} shares {share}% of its wording with {src}"
            for name, n, src, share in traced) + ". "
            "Overlap is measured using matching five-word phrases, ignoring case and punctuation. "
            "It suggests a connection, not proof of origin. Include those files as exhibits and ask the writer to explain the relationship.")
    if flagged:
        lines.append("")
        lines.append("Large single insertions appear in: " + ", ".join(f"{name} ({n:,} words)" for name, n in flagged) + ". "
                     "Reviewers look for these first. They usually have an ordinary source, such as text moved from a "
                     "notes file, an outline or a separately drafted section. Find that source and add it to the evidence.")
    elif not traced:
        lines.append("")
        lines.append("No single insertion made up a large share of any draft, which is consistent with gradual writing.")

    md = "\n".join(lines) + "\n"
    if args.out:
        Path(args.out).write_text(md)
        print(f"Wrote {args.out}")
    else:
        print(md)

    if args.html:
        hd = difflib.HtmlDiff(wrapcolumn=80)
        body = []
        for i in range(1, len(texts)):
            body.append(f"<h2>{html.escape(paths[i - 1].name)} → {html.escape(paths[i].name)}</h2>")
            body.append(hd.make_table(texts[i - 1].splitlines(), texts[i].splitlines(),
                                      paths[i - 1].name, paths[i].name, context=True, numlines=2))
        Path(args.html).write_text(
            "<!doctype html><meta charset='utf-8'><title>Draft changes</title>"
            "<style>body{font-family:system-ui,sans-serif;margin:24px}table.diff{font-family:ui-monospace,monospace;"
            "font-size:12px;border-collapse:collapse}.diff_add{background:#dfd}.diff_chg{background:#ffc}"
            ".diff_sub{background:#fdd}td{vertical-align:top;padding:1px 4px}</style>" + "".join(body))
        print(f"Wrote {args.html}")


if __name__ == "__main__":
    main()
