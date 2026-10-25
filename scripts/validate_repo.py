#!/usr/bin/env python3
"""Read-only validation of this collection; never execute archived skills."""
import hashlib
import json
from pathlib import Path
import re
import sys

try:
    import yaml
except ImportError:
    raise SystemExit("Install validation dependencies: python3 -m pip install -r requirements-dev.txt")

ROOT = Path(__file__).resolve().parents[1]
HEADER = re.compile(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", re.S)
NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


def validate(root=ROOT):
    failures = []

    def issue(path, message):
        failures.append({"file": str(path.relative_to(root)), "message": message})

    def read_json(path):
        try:
            return json.loads(path.read_text())
        except (OSError, ValueError) as error:
            issue(path, type(error).__name__)
            return {}

    required = ["README.md", "AGENTS.md", "CONTRIBUTING.md", "LICENSE", "LICENSES.md",
                "THIRD_PARTY_NOTICES.md", "catalog.json", "docs/index.md"]
    for name in required:
        if not (root / name).is_file():
            issue(root / name, "Missing collection document")

    catalog = read_json(root / "catalog.json")
    listed = {entry.get("path") + "/SKILL.md" for entry in catalog.get("entries", [])
              if entry.get("included") and isinstance(entry.get("path"), str)}
    candidates = sorted([*root.glob("skills/*/SKILL.md"), *root.glob("plugins/*/skills/*/SKILL.md")])
    candidate_names = {str(path.relative_to(root)) for path in candidates}
    unregistered = sorted(candidate_names - listed)
    skill_paths = [path for path in candidates if str(path.relative_to(root)) in listed]
    if listed - candidate_names:
        issue(root / "catalog.json", "Included Skill paths are missing from the working tree")
    seen = set()
    upstream_count = 0
    notices = (root / "THIRD_PARTY_NOTICES.md").read_text() if (root / "THIRD_PARTY_NOTICES.md").is_file() else ""
    for path in skill_paths:
        text = path.read_text()
        match = HEADER.match(text)
        try:
            fields = yaml.safe_load(match.group(1)) if match else None
            if not isinstance(fields, dict):
                raise ValueError("Missing YAML mapping")
        except (ValueError, yaml.YAMLError):
            issue(path, "Invalid Skill frontmatter")
            continue
        name = fields.get("name")
        if not isinstance(name, str) or len(name) > 64 or not NAME.fullmatch(name) or name != path.parent.name:
            issue(path, "Skill name must match directory and use kebab-case")
            continue
        if name in seen:
            issue(path, "Duplicate Skill name")
        seen.add(name)
        description = fields.get("description")
        if not isinstance(description, str) or not description.strip() or len(description) > 1024:
            issue(path, "Missing or overlong description")
        metadata = fields.get("metadata", {})
        if not isinstance(metadata, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in metadata.items()):
            issue(path, "Metadata must contain string keys and values")
            metadata = {}
        if path.parent.parent == root / "skills":
            provenance_path = path.parent / "PROVENANCE.json"
            provenance = read_json(provenance_path)
            if provenance.get("classification") == "public-upstream-local-derivative":
                upstream_count += 1
                license_path = path.parent / "LICENSE"
                if not license_path.is_file():
                    issue(license_path, "Missing original upstream license")
                elif hashlib.sha256(license_path.read_bytes()).hexdigest() != provenance.get("license_sha256"):
                    issue(license_path, "Upstream license differs from recorded verified text")
                if fields.get("license") != "MIT" or metadata.get("upstream-author") != "Matt Pocock":
                    issue(path, "Verified upstream attribution or license metadata missing")
                if metadata.get("upstream-reference") != provenance.get("reference_revision"):
                    issue(path, "Reference revision differs from provenance")
                if provenance.get("reference_is_original_install_revision") is not False:
                    issue(provenance_path, "Comparison revision must not imply known installation history")
                if "> 来源：" not in text or provenance.get("repository", "") not in text:
                    issue(path, "Missing visible source attribution")
                if f"skills/{name}/SKILL.md" not in notices:
                    issue(root / "THIRD_PARTY_NOTICES.md", "Upstream Skill missing from source index: " + name)

    yaml_paths = sorted(root.rglob("*.yaml"))
    for path in yaml_paths:
        try:
            value = yaml.safe_load(path.read_text())
            if not isinstance(value, dict):
                raise ValueError()
            policy = value.get("policy", {})
            if "allow_implicit_invocation" in policy and policy["allow_implicit_invocation"] is not None and type(policy["allow_implicit_invocation"]) is not bool:
                issue(path, "Invocation policy must be boolean or null")
        except (ValueError, TypeError, yaml.YAMLError):
            issue(path, "Invalid agent YAML")

    for lock in root.glob("plugins/*/upstream.lock.json"):
        data = read_json(lock)
        vendor = lock.parent / "vendor/xiaohongshu-mcp"
        for name, digest in data.get("source_sha256", {}).items():
            path = vendor / name
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                issue(path, "Locked upstream source changed or missing")

    maintained = [*root.glob("*.md"), *root.glob("docs/**/*.md"),
                  *root.glob("plugins/*/README.md"), *root.glob("plugins/*/docs/**/*.md"),
                  *root.glob("plugins/*/skills/*/SKILL.md")]
    for path in maintained:
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text()):
            target = target.split("#", 1)[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            resolved = (path.parent / target).resolve()
            if not resolved.is_relative_to(root.resolve()) or not resolved.exists():
                issue(path, "Broken or external local link: " + target)

    return {"ok": not failures, "skills": len(skill_paths), "agent_yaml": len(yaml_paths),
            "verified_upstream_skills": upstream_count,
            "unregistered_skills": unregistered, "failures": failures}


if __name__ == "__main__":
    result = validate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["ok"] else 1)
