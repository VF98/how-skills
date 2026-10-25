#!/usr/bin/env python3
"""Inspect exact Git-index blobs without printing possible secret values."""
from pathlib import Path, PurePosixPath
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_NAMES = {
    "auth.json", "credentials.json", "cookies.json", ".env", ".netrc",
    "account-consent.json", "native-binding.json", "browser-backend.json",
}
FORBIDDEN_DIRS = {
    ".git", "__pycache__", ".venv", "node_modules", "evidence", "content",
    "isolated-runtime", "profile", "profiles", ".xhs-local-data",
}
PATTERNS = {
    "private-key": re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----"),
    "access-token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,}|glpat-[A-Za-z0-9_-]{16,}|sk-(?:proj-)?[A-Za-z0-9_-]{24,})\b"),
    "mac-user-path": re.compile(re.escape("/" + "Users" + "/") + r"(?!user(?:/|\b)|example(?:/|\b)|[<{$])[^/\s\"']+"),
    "linux-user-path": re.compile(re.escape("/" + "home" + "/") + r"(?!user(?:/|\b)|example(?:/|\b)|[<{$])[^/\s\"']+"),
    "private-network": re.compile(r"\b(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})\b"),
}


def index_blobs(root=ROOT):
    result = subprocess.run(["git", "ls-files", "--stage", "-z"], cwd=root,
                            check=True, capture_output=True).stdout
    entries = []
    for record in result.split(b"\0"):
        if not record:
            continue
        meta, name = record.split(b"\t", 1)
        mode, oid, stage = meta.decode().split()
        if mode not in {"100644", "100755"} or stage != "0":
            raise ValueError("Only regular, conflict-free staged files can be exported")
        entries.append({"name": name.decode(), "mode": mode, "oid": oid})
    if not entries:
        raise ValueError("No staged files; review and stage the intended export first")
    output = subprocess.run(["git", "cat-file", "--batch"], cwd=root, check=True,
                            input=("\n".join(e["oid"] for e in entries) + "\n").encode(),
                            capture_output=True).stdout
    position = 0
    for entry in entries:
        end = output.index(b"\n", position)
        oid, kind, size = output[position:end].decode().split()
        if oid != entry["oid"] or kind != "blob":
            raise ValueError("Unexpected Git object")
        position = end + 1
        entry["data"] = output[position:position + int(size)]
        position += int(size) + 1
    return entries


def inspect(entries):
    findings = []
    for entry in entries:
        name = entry["name"]
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts:
            findings.append({"file": name, "rule": "unsafe-path"})
        if (path.name in FORBIDDEN_NAMES or set(path.parts) & FORBIDDEN_DIRS
                or path.suffix.lower() in {".pyc", ".pyo", ".sqlite", ".sqlite3", ".db", ".zip", ".png", ".jpg", ".jpeg", ".mp4", ".pem", ".key"}
                or (path.name.startswith(".env.") and path.name != ".env.example")):
            findings.append({"file": name, "rule": "runtime-or-private-artifact"})
        try:
            source = entry["data"].decode("utf-8")
        except UnicodeDecodeError:
            findings.append({"file": name, "rule": "unreviewed-binary"})
            continue
        for rule, pattern in PATTERNS.items():
            if pattern.search(source):
                findings.append({"file": name, "rule": rule})
        if path.suffix == ".json":
            try:
                json.loads(source)
            except ValueError:
                findings.append({"file": name, "rule": "invalid-json"})
    return findings


def checked_index():
    entries = index_blobs()
    findings = inspect(entries)
    catalog_blob = next((entry["data"] for entry in entries if entry["name"] == "catalog.json"), None)
    if catalog_blob is None:
        findings.append({"file": "catalog.json", "rule": "missing-skill-catalog"})
    else:
        try:
            catalog = json.loads(catalog_blob)
            registered = {item["path"] + "/SKILL.md" for item in catalog.get("entries", [])
                          if item.get("included") and isinstance(item.get("path"), str)}
            exported = {entry["name"] for entry in entries
                        if re.fullmatch(r"(?:skills/[^/]+|plugins/[^/]+/skills/[^/]+)/SKILL\.md", entry["name"])}
            for name in sorted(registered ^ exported):
                findings.append({"file": name, "rule": "skill-catalog-export-mismatch"})
        except (ValueError, TypeError):
            findings.append({"file": "catalog.json", "rule": "invalid-skill-catalog"})
    if findings:
        print(json.dumps({"ok": False, "findings": findings}, ensure_ascii=False, indent=2))
        raise SystemExit(1)
    return entries


if __name__ == "__main__":
    try:
        entries = checked_index()
        print(json.dumps({"ok": True, "staged_files": len(entries),
                          "scope": "staged source blobs; static patterns plus manual review"}))
    except (ValueError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
