#!/usr/bin/env python3
"""Preserve writing-process evidence before anything else touches it.

Copies files into a read-only archive, and records each original's path, size,
SHA-256 hash and filesystem timestamps in a manifest. Source files are only read,
never modified.

Usage:
    python3 snapshot.py <file-or-folder> [...] --out <evidence-folder>

Writes:
    <out>/originals/...   read-only copies (timestamps preserved where the OS allows)
    <out>/manifest.json   machine-readable record
    <out>/MANIFEST.md     human-readable record for the evidence packet
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

SKIP_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def iso(ts: float | None) -> str | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone().isoformat(timespec="seconds")


def collect(inputs: list[str]) -> list[tuple[Path, Path]]:
    """Return (absolute source path, archive-relative path) pairs."""
    pairs = []
    for raw in inputs:
        src = Path(raw).expanduser().resolve()
        if not src.exists():
            sys.exit(f"Not found: {raw}")
        if src.is_file():
            pairs.append((src, Path(src.name)))
            continue
        for p in sorted(src.rglob("*")):
            if p.is_file() and p.name not in SKIP_NAMES and not any(part.startswith(".") for part in p.relative_to(src).parts):
                pairs.append((p, Path(src.name) / p.relative_to(src)))
    return pairs


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+", help="files or folders to preserve")
    ap.add_argument("--out", required=True, help="evidence folder to create")
    args = ap.parse_args()

    out = Path(args.out).expanduser().resolve()
    for raw in args.inputs:
        src = Path(raw).expanduser().resolve()
        if out == src or (src.is_dir() and src in out.parents):
            sys.exit("--out must not be inside a folder being preserved or replace an input file.")
    archive = out / "originals"
    if archive.exists() and any(archive.iterdir()):
        sys.exit(f"{archive} already has files. Choose a new --out folder so earlier snapshots stay untouched.")

    pairs = collect(args.inputs)
    if not pairs:
        sys.exit("No files found to preserve.")
    for src, _ in pairs:
        if out == src or out in src.parents:
            sys.exit("Input files must not be inside --out. Choose a separate evidence folder.")

    # Validate all destination names before writing any copies. Case folding also
    # prevents collisions when an archive is created on a case-insensitive disk.
    destinations = {}
    for src, rel in pairs:
        key = rel.as_posix().casefold()
        if key in destinations:
            sys.exit(f"Archive path collision: {src} and {destinations[key]} both map to {rel}. "
                     "Preserve a common parent folder or use separate snapshots.")
        destinations[key] = src
    for _, rel in pairs:
        if any(parent.as_posix().casefold() in destinations for parent in rel.parents):
            sys.exit(f"Archive path collision: a file would also be a parent folder of {rel}. "
                     "Preserve a common parent folder or use separate snapshots.")

    archive.mkdir(parents=True, exist_ok=True)
    taken = datetime.now(timezone.utc).astimezone()
    records = []
    for src, rel in pairs:
        st = src.stat()
        dest = archive / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        dest.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        digest = sha256(src)
        if sha256(dest) != digest:
            sys.exit(f"Copy verification failed for {src}")
        records.append({
            "archive_path": str(Path("originals") / rel),
            "original_path": str(src),
            "size_bytes": st.st_size,
            "sha256": digest,
            "modified": iso(st.st_mtime),
            "created": iso(getattr(st, "st_birthtime", None)),
            "metadata_changed": iso(st.st_ctime),
        })

    manifest = {
        "snapshot_taken": taken.isoformat(timespec="seconds"),
        "host_os": f"{platform.system()} {platform.release()}",
        "note": "Timestamps are those of the original files when the snapshot was taken. "
                "Copying, syncing or converting files can change filesystem timestamps, so treat them "
                "as consistent with an account of the work, not as proof on their own.",
        "files": records,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))

    lines = [
        "# Evidence manifest",
        "",
        f"Snapshot taken: {manifest['snapshot_taken']}  ",
        f"Files: {len(records)}",
        "",
        manifest["note"],
        "",
        "| # | File | Modified | Created | Size | SHA-256 |",
        "|---|------|----------|---------|------|---------|",
    ]
    for i, r in enumerate(records, 1):
        lines.append(
            f"| {i} | {r['archive_path'].removeprefix('originals/')} | {r['modified'] or ''} | "
            f"{r['created'] or 'n/a'} | {r['size_bytes']:,} B | `{r['sha256'][:16]}…` |"
        )
    lines += ["", "Full hashes are in manifest.json."]
    (out / "MANIFEST.md").write_text("\n".join(lines) + "\n")

    print(f"Preserved {len(records)} files in {archive}")
    print(f"Manifest: {out / 'MANIFEST.md'}")


if __name__ == "__main__":
    main()
