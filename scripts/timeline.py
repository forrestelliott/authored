#!/usr/bin/env python3
"""Build one chronology of the writing process from an evidence folder.

Reads, without modifying anything:
  - filesystem times (from snapshot.py's manifest.json when present)
  - Word/PowerPoint/Excel metadata: created, modified, editing minutes, revision
    count, Word editing-session IDs (rsids), tracked-change and comment dates
  - OpenDocument metadata: created, modified, editing duration and cycles
  - PDF creation and modification dates
  - photo capture dates (if Pillow is installed)
  - git commits (with --git)

Usage:
    python3 timeline.py <evidence-folder> [--git <repo>] [--out timeline.md] [--json timeline.json]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "ep": "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties",
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "meta": "urn:oasis:names:tc:opendocument:xmlns:meta:1.0",
}
W = "{%s}" % NS["w"]
OOXML = {".docx", ".docm", ".dotx", ".pptx", ".xlsx"}
ODF = {".odt", ".ods", ".odp"}
IMAGES = {".jpg", ".jpeg", ".heic", ".png", ".tif", ".tiff"}


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    v = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(v)
    except ValueError:
        try:
            dt = datetime.fromisoformat(v.split(".")[0])
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc) if value.strip().endswith("Z") else dt.astimezone()
    return dt.astimezone()


def fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M")


def iso_duration_minutes(value: str | None) -> int | None:
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:([\d.]+)S)?", (value or "").strip())
    if not m:
        return None
    d, h, mi, s = (float(x) if x else 0 for x in m.groups())
    return int(d * 1440 + h * 60 + mi + s / 60)


class Timeline:
    def __init__(self) -> None:
        self.events: list[dict] = []
        self.documents: list[dict] = []

    def add(self, when: datetime | None, source: str, kind: str, detail: str = "") -> None:
        if when:
            self.events.append({"when": when, "source": source, "kind": kind, "detail": detail})


def read_xml(z: zipfile.ZipFile, name: str) -> ET.Element | None:
    try:
        return ET.fromstring(z.read(name))
    except (KeyError, ET.ParseError):
        return None


def text(root: ET.Element | None, path: str) -> str | None:
    if root is None:
        return None
    el = root.find(path, NS)
    return el.text if el is not None and el.text else None


def ooxml(path: Path, label: str, tl: Timeline) -> dict:
    info: dict = {"file": label, "type": "Office document"}
    try:
        z = zipfile.ZipFile(path)
    except zipfile.BadZipFile:
        info["warning"] = "not a valid Office file"
        return info
    with z:
        core = read_xml(z, "docProps/core.xml")
        app = read_xml(z, "docProps/app.xml")
        created = parse_dt(text(core, "dcterms:created"))
        modified = parse_dt(text(core, "dcterms:modified"))
        info.update({
            "author": text(core, "dc:creator"),
            "last_modified_by": text(core, "cp:lastModifiedBy"),
            "created": created,
            "modified": modified,
            "revision": text(core, "cp:revision"),
            "editing_minutes": text(app, "ep:TotalTime"),
            "application": text(app, "ep:Application"),
            "words": text(app, "ep:Words"),
        })
        tl.add(created, label, "document created (internal metadata)")
        tl.add(modified, label, "document last saved (internal metadata)")

        settings = read_xml(z, "word/settings.xml")
        if settings is not None:
            rsids = settings.findall(".//w:rsids/w:rsid", NS)
            if rsids:
                info["editing_sessions"] = len(rsids)

        doc = read_xml(z, "word/document.xml")
        if doc is not None:
            changes: Counter = Counter()
            first_seen: dict = {}
            for tag, kind in ((W + "ins", "insertion"), (W + "del", "deletion")):
                for el in doc.iter(tag):
                    dt = parse_dt(el.get(W + "date"))
                    if dt:
                        key = (dt.date(), el.get(W + "author") or "unknown", kind)
                        changes[key] += 1
                        first_seen[key] = min(dt, first_seen.get(key, dt))
            for key, n in sorted(changes.items()):
                _, author, kind = key
                tl.add(first_seen[key], label, f"tracked changes: {n} {kind}{'s' if n > 1 else ''} that day", f"by {author}")
            if changes:
                info["tracked_changes"] = sum(changes.values())

        comments = read_xml(z, "word/comments.xml")
        if comments is not None:
            for c in comments.iter(W + "comment"):
                snippet = "".join(t.text or "" for t in c.iter(W + "t"))[:80]
                tl.add(parse_dt(c.get(W + "date")), label, "comment", f"{c.get(W + 'author') or 'unknown'}: {snippet}")
    return info


def odf(path: Path, label: str, tl: Timeline) -> dict:
    info: dict = {"file": label, "type": "OpenDocument"}
    try:
        with zipfile.ZipFile(path) as z:
            meta = read_xml(z, "meta.xml")
    except zipfile.BadZipFile:
        info["warning"] = "not a valid OpenDocument file"
        return info
    m = meta.find("office:meta", NS) if meta is not None else None
    created = parse_dt(text(m, "meta:creation-date"))
    modified = parse_dt(text(m, "dc:date"))
    info.update({
        "author": text(m, "meta:initial-creator"),
        "last_modified_by": text(m, "dc:creator"),
        "created": created,
        "modified": modified,
        "editing_minutes": iso_duration_minutes(text(m, "meta:editing-duration")),
        "editing_sessions": text(m, "meta:editing-cycles"),
    })
    tl.add(created, label, "document created (internal metadata)")
    tl.add(modified, label, "document last saved (internal metadata)")
    return info


def pdf(path: Path, label: str, tl: Timeline) -> dict:
    info: dict = {"file": label, "type": "PDF"}
    data = path.read_bytes()
    for key, kind in ((b"CreationDate", "created"), (b"ModDate", "modified")):
        m = re.search(rb"/" + key + rb"\s*\(D:(\d{4})(\d{2})?(\d{2})?(\d{2})?(\d{2})?(\d{2})?([Z+\-])?(\d{2})?'?(\d{2})?", data)
        if not m:
            continue
        y, mo, d, h, mi, s, sign, oh, om = (x.decode() if x else None for x in m.groups())
        stamp = f"{y}-{mo or '01'}-{d or '01'}T{h or '00'}:{mi or '00'}:{s or '00'}"
        if sign in ("+", "-") and oh:
            stamp += f"{sign}{oh}:{om or '00'}"
        elif sign == "Z":
            stamp += "Z"
        dt = parse_dt(stamp)
        info[kind] = dt
        tl.add(dt, label, f"PDF {kind} (internal metadata)")
    producer = re.search(rb"/Producer\s*\(([^)]{1,120})\)", data)
    if producer:
        info["application"] = producer.group(1).decode("latin-1", "replace")
    return info


def image(path: Path, label: str, tl: Timeline) -> dict | None:
    try:
        from PIL import Image  # optional
    except ImportError:
        return None
    try:
        exif = Image.open(path).getexif()
        raw = exif.get_ifd(0x8769).get(36867) or exif.get(306)  # DateTimeOriginal, then DateTime
    except Exception:
        return None
    if not raw:
        return None
    try:
        dt = datetime.strptime(str(raw), "%Y:%m:%d %H:%M:%S").astimezone()
    except ValueError:
        return None
    tl.add(dt, label, "photo taken (camera metadata)")
    return {"file": label, "type": "Photo", "created": dt}


def git_events(repo: Path, tl: Timeline) -> None:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "log", "--reverse", "--format=%x1e%aI%x1f%h%x1f%s", "--numstat"],
            capture_output=True, text=True, check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"git history unavailable: {e}", file=sys.stderr)
        return
    for block in out.split("\x1e")[1:]:
        head, *stats = block.strip("\n").split("\n")
        when, sha, subject = head.split("\x1f")
        added = removed = 0
        for line in stats:
            parts = line.split("\t")
            if len(parts) == 3 and parts[0].isdigit():
                added += int(parts[0])
                removed += int(parts[1])
        tl.add(parse_dt(when), f"git {repo.name}", f"commit {sha}: {subject}", f"+{added} / -{removed} lines")


def build(folder: str | Path, git: str | None = None) -> tuple[Timeline, dict | None, Path]:
    """Analyze an evidence folder. Returns the timeline, the snapshot manifest (if any) and the files' base folder."""
    root = Path(folder).expanduser().resolve()
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else None
    base = root / "originals" if manifest else root
    fs_times = {Path(r["archive_path"]).relative_to("originals").as_posix(): r for r in manifest["files"]} if manifest else {}

    tl = Timeline()
    for path in sorted(p for p in base.rglob("*") if p.is_file() and not p.name.startswith(".")):
        label = path.relative_to(base).as_posix()
        if label in {"manifest.json", "MANIFEST.md"} or label.startswith(("timeline.", "drafts.", "report.")):
            continue
        rec = fs_times.get(label)
        if rec:
            modified, created = parse_dt(rec.get("modified")), parse_dt(rec.get("created"))
        else:
            st = path.stat()
            modified = datetime.fromtimestamp(st.st_mtime).astimezone()
            bt = getattr(st, "st_birthtime", None)
            created = datetime.fromtimestamp(bt).astimezone() if bt else None
        if created and modified and abs((modified - created).total_seconds()) < 60:
            tl.add(modified, label, "file created and last modified (filesystem)")
        else:
            tl.add(created, label, "file created (filesystem)")
            tl.add(modified, label, "file last modified (filesystem)")

        ext = path.suffix.lower()
        info = None
        if ext in OOXML:
            info = ooxml(path, label, tl)
        elif ext in ODF:
            info = odf(path, label, tl)
        elif ext == ".pdf":
            info = pdf(path, label, tl)
        elif ext in IMAGES:
            info = image(path, label, tl)
        if info:
            tl.documents.append(info)

    if git:
        git_events(Path(git).expanduser().resolve(), tl)
    tl.events.sort(key=lambda e: e["when"])
    return tl, manifest, base


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", help="evidence folder (snapshot.py output, or any folder)")
    ap.add_argument("--git", help="git repository whose history is part of the evidence")
    ap.add_argument("--out", help="write Markdown here (default: print)")
    ap.add_argument("--json", help="also write machine-readable JSON here")
    args = ap.parse_args()

    tl, manifest, _ = build(args.folder, args.git)
    md = render(tl, manifest)
    if args.out:
        Path(args.out).write_text(md)
        print(f"Wrote {args.out} ({len(tl.events)} events)")
    else:
        print(md)
    if args.json:
        Path(args.json).write_text(json.dumps({"events": tl.events, "documents": tl.documents}, indent=2, default=str))


def render(tl: Timeline, manifest: dict | None) -> str:
    lines = ["# Writing timeline", ""]
    if manifest:
        lines += [f"Built from the evidence snapshot taken {manifest['snapshot_taken']}.", ""]
    if tl.events:
        days = {e["when"].date() for e in tl.events}
        lines += [
            f"Activity spans {fmt(tl.events[0]['when'])} to {fmt(tl.events[-1]['when'])}, "
            f"with recorded events on {len(days)} separate day{'s' if len(days) != 1 else ''}.",
            "",
        ]

    if tl.documents:
        lines += ["## Document metadata", "",
                  "| File | Created | Last saved | Editing time | Sessions | Revision | Tracked changes | Application |",
                  "|------|---------|------------|--------------|----------|----------|-----------------|-------------|"]
        for d in tl.documents:
            mins = d.get("editing_minutes")
            try:
                mins_s = f"{int(mins):,} min" if mins not in (None, "") else ""
            except ValueError:
                mins_s = str(mins)
            lines.append("| {} | {} | {} | {} | {} | {} | {} | {} |".format(
                d["file"],
                fmt(d["created"]) if d.get("created") else "",
                fmt(d["modified"]) if d.get("modified") else "",
                mins_s,
                d.get("editing_sessions") or "",
                d.get("revision") or "",
                d.get("tracked_changes") or "",
                (d.get("application") or "").replace("|", "/"),
            ))
        lines += [
            "",
            "Editing time and revision count are recorded by the application that saved the file. "
            "Sessions are Word's editing-session IDs (rsids) or OpenDocument editing cycles. Files exported "
            "from Google Docs or converted between formats usually lack these, so a blank cell is not a red flag.",
            "",
        ]

    lines += ["## Chronology", "", "| When | Source | Event | Detail |", "|------|--------|-------|--------|"]
    for e in tl.events:
        lines.append(f"| {fmt(e['when'])} | {e['source']} | {e['kind']} | {e['detail'].replace('|', '/')} |")
    lines += [
        "",
        "## Reading this timeline",
        "",
        "Timestamps come from file systems and from metadata written by applications. Copying, syncing, "
        "downloading or converting a file can change them, so they support the writer's account rather than "
        "prove it on their own. Version history captured from the writing tool itself, dated drafts, notes "
        "and third-party records carry more weight.",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
