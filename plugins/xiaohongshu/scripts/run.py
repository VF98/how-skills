#!/usr/bin/env python3
"""Portable local entrypoint; private state is kept outside the source tree."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from xhs_local.app import App
from xhs_local.cli import main
from xhs_local.drafts import atomic_private_write
from xhs_local.errors import XHSError


def run():
    if "--help" in sys.argv or "-h" in sys.argv:
        return main()
    selected = None
    for i, value in enumerate(sys.argv[1:], 1):
        if value == "--data-dir" and i + 1 < len(sys.argv):
            selected = sys.argv[i + 1]
        elif value.startswith("--data-dir="):
            selected = value.split("=", 1)[1]
    os.environ.setdefault("XHS_LOCAL_DATA", str(Path.home() / ".local/share/personal-skills/xiaohongshu"))
    app = App(selected)
    backend = app.data_dir / "browser-backend.json"
    if backend.exists():
        if app.browser_backend() != "isolated_headless":
            raise XHSError("backend_conflict", "此入口使用独立后台环境；请选择新的独立数据目录")
    else:
        atomic_private_write(backend, b'{"mode":"isolated_headless","desktop_fallback":false}')
    return main()


if __name__ == "__main__":
    try:
        run()
    except XHSError as error:
        print(json.dumps(error.as_dict(), ensure_ascii=False))
        raise SystemExit(1)
