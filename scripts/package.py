#!/usr/bin/env python3
"""Export reviewed Git-index content; no Git metadata or working-tree caches."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from check_export import ROOT, checked_index


def archive(destination, entries, prefix, strip=""):
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for entry in sorted(entries, key=lambda e: e["name"]):
            name = prefix + "/" + entry["name"][len(strip):]
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            mode = 0o755 if entry["mode"] == "100755" else 0o644
            info.external_attr = (0o100000 | mode) << 16
            output.writestr(info, entry["data"])
    with zipfile.ZipFile(destination) as output:
        if output.testzip() is not None:
            raise ValueError("Archive integrity failed")
    return {"file": destination.name, "files": len(entries),
            "bytes": destination.stat().st_size,
            "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path,
                        default=ROOT.parent / "personal-skills-exports")
    args = parser.parse_args()
    folder = args.output_dir.expanduser().resolve()
    if folder == ROOT or folder.is_relative_to(ROOT):
        parser.error("Choose an output directory outside the source repository")
    entries = checked_index()
    folder.mkdir(parents=True, exist_ok=True)
    plugin_prefix = "plugins/xiaohongshu/"
    plugin = [e for e in entries if e["name"].startswith(plugin_prefix)]
    if not any(e["name"] == plugin_prefix + "plugin.json" for e in plugin):
        raise ValueError("Missing Xiaohongshu plugin manifest")
    result = [archive(folder / "personal-skills.zip", entries, "personal-skills"),
              archive(folder / "xiaohongshu-plugin.zip", plugin, "xiaohongshu", plugin_prefix)]
    (folder / "SHA256SUMS").write_text("".join(f'{a["sha256"]}  {a["file"]}\n' for a in result))
    (folder / "manifest.json").write_text(json.dumps({"source": "reviewed Git index", "archives": result}, indent=2) + "\n")
    print(json.dumps({"output": str(folder), "archives": result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
