"""Transactional local manuscripts. These are NEVER platform-native drafts."""

import base64
from datetime import datetime, timezone
import hashlib
import html
import json
import mimetypes
import os
from pathlib import Path
import re
import sqlite3
import tempfile
import uuid

from .errors import XHSError

DRAFT_ID = re.compile(r"^[0-9a-f]{32}$")
MAX_IMAGE_BYTES = 20 * 1024 * 1024
SCOPE = "local_manuscript_only"


def private_dir(path):
    path = Path(path)
    if path.is_symlink():
        raise XHSError("unsafe_storage", "存储目录不能是符号链接")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path, 0o700)
    return path


def atomic_private_write(path, data):
    path = Path(path)
    private_dir(path.parent)
    fd, tmp = tempfile.mkstemp(prefix=".writing-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def payload_hash(payload):
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def image_type(data):
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data[:6] in {b"GIF87a", b"GIF89a"}:
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    raise XHSError("invalid_image", "预览仅接受 PNG、JPEG、GIF 或 WebP 图片")


class DraftStore:
    def __init__(self, root):
        self.root = private_dir(root)
        self.assets = private_dir(self.root / "assets")
        database = self.root / "manuscripts.sqlite3"
        if database.is_symlink():
            raise XHSError("unsafe_storage", "文稿数据库不能是符号链接")
        fd = os.open(database, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(fd)
        os.chmod(database, 0o600)
        self.db = sqlite3.connect(database, timeout=10, isolation_level=None)
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS manuscripts (
                id TEXT PRIMARY KEY, revision INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS revisions (
                id TEXT NOT NULL, revision INTEGER NOT NULL, payload TEXT NOT NULL,
                digest TEXT NOT NULL, created TEXT NOT NULL,
                PRIMARY KEY(id, revision), FOREIGN KEY(id) REFERENCES manuscripts(id));
        """)

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        self.close()

    def _validate(self, payload):
        if not isinstance(payload, dict) or set(payload) - {"title", "content", "tags", "images"}:
            raise XHSError("invalid_manuscript", "只接受 title、content、tags、images 字段")
        title, content = payload.get("title"), payload.get("content")
        if not isinstance(title, str) or not title.strip() or len(title) > 200:
            raise XHSError("invalid_title", "本地文稿标题需为 1 至 200 个字符")
        if not isinstance(content, str) or not content.strip() or len(content) > 100000:
            raise XHSError("invalid_content", "本地文稿正文需为 1 至 100000 个字符")
        tags = payload.get("tags", [])
        if not isinstance(tags, list) or len(tags) > 10 or any(
                not isinstance(t, str) or not t.strip() or len(t) > 60 for t in tags):
            raise XHSError("invalid_tags", "tags 需为最多 10 个非空字符串，每个不超过 60 字符")
        images = payload.get("images", [])
        if not isinstance(images, list) or len(images) > 18:
            raise XHSError("invalid_images", "images 需为最多 18 个本地图片路径")
        imported = []
        for value in images:
            if not isinstance(value, str):
                raise XHSError("invalid_image", "图片需为本地文件路径")
            path = Path(value).expanduser()
            if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_IMAGE_BYTES:
                raise XHSError("invalid_image", "图片需为不超过 20 MiB 的普通本地文件")
            data = path.read_bytes()
            media = image_type(data)
            digest = hashlib.sha256(data).hexdigest()
            asset = self.assets / digest
            if not asset.exists():
                atomic_private_write(asset, data)
            imported.append({"sha256": digest, "mime": media, "name": path.name})
        return {"title": title, "content": content, "tags": tags, "images": imported}

    @staticmethod
    def _id(value):
        if not isinstance(value, str) or not DRAFT_ID.fullmatch(value):
            raise XHSError("invalid_manuscript_id", "文稿 ID 格式无效")

    def create(self, payload):
        value = self._validate(payload)
        manuscript_id = uuid.uuid4().hex
        self.db.execute("BEGIN IMMEDIATE")
        try:
            self.db.execute("INSERT INTO manuscripts VALUES(?,1)", (manuscript_id,))
            self._insert(manuscript_id, 1, value)
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise
        return self.get(manuscript_id)

    def _insert(self, manuscript_id, revision, payload):
        self.db.execute("INSERT INTO revisions VALUES(?,?,?,?,?)", (
            manuscript_id, revision, json.dumps(payload, ensure_ascii=False), payload_hash(payload),
            datetime.now(timezone.utc).isoformat()))

    def get(self, manuscript_id, revision=None):
        self._id(manuscript_id)
        if revision is not None and (type(revision) is not int or revision < 1):
            raise XHSError("invalid_revision", "版本需为正整数")
        if revision is None:
            row = self.db.execute("SELECT r.revision,r.payload,r.digest,r.created FROM revisions r "
                                  "JOIN manuscripts m ON m.id=r.id AND m.revision=r.revision "
                                  "WHERE r.id=?", (manuscript_id,)).fetchone()
        else:
            row = self.db.execute("SELECT revision,payload,digest,created FROM revisions "
                                  "WHERE id=? AND revision=?", (manuscript_id, revision)).fetchone()
        if not row:
            raise XHSError("manuscript_missing", "未找到这个本地文稿或版本")
        return {"ok": True, "manuscript_id": manuscript_id, "revision": row[0],
                "payload": json.loads(row[1]), "sha256": row[2], "created_at": row[3],
                "storage_scope": SCOPE, "platform_saved": False, "platform_draft_id": None}

    def update(self, manuscript_id, expected_revision, patch):
        self._id(manuscript_id)
        if type(expected_revision) is not int or expected_revision < 1:
            raise XHSError("invalid_revision", "更新必须提供当前 expected_revision")
        if not isinstance(patch, dict) or not patch or set(patch) - {"title", "content", "tags", "images"}:
            raise XHSError("invalid_patch", "只接受 title、content、tags、images 的非空更新")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            current = self.get(manuscript_id)
            if current["revision"] != expected_revision:
                raise XHSError("revision_conflict", f"文稿已更新，当前版本是 {current['revision']}，请重新读取")
            old = current["payload"]
            merged = {**old, **patch}
            if "images" not in patch:
                merged["images"] = [str(self.assets / v["sha256"]) for v in old["images"]]
            value = self._validate(merged)
            if "images" not in patch:
                value["images"] = old["images"]
            if payload_hash(value) != current["sha256"]:
                next_revision = expected_revision + 1
                self._insert(manuscript_id, next_revision, value)
                self.db.execute("UPDATE manuscripts SET revision=? WHERE id=?", (next_revision, manuscript_id))
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise
        return self.get(manuscript_id)

    def preview(self, manuscript_id, revision=None):
        saved = self.get(manuscript_id, revision)
        p = saved["payload"]
        esc = html.escape
        images = []
        for item in p["images"]:
            data = (self.assets / item["sha256"]).read_bytes()
            if hashlib.sha256(data).hexdigest() != item["sha256"]:
                raise XHSError("asset_changed", "预览图片内容校验失败")
            encoded = base64.b64encode(data).decode()
            images.append(f'<img src="data:{item["mime"]};base64,{encoded}" alt="{esc(item["name"])}">')
        image_html = "".join(images) or '<div class="empty">尚未添加图片</div>'
        tags = " ".join("#" + esc(t) for t in p["tags"])
        warnings = []
        if len(p["title"]) > 20:
            warnings.append("标题超过 20 个字符，请在发布前核查平台限制。")
        if len(p["content"]) > 1000:
            warnings.append("正文超过 1000 个字符，请在发布前核查笔记类型和平台限制。")
        body = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>{esc(p['title'])} · 本地文稿预览</title>
<style>body{{margin:0;background:#f3f1ed;color:#242323;font:16px -apple-system,BlinkMacSystemFont,sans-serif}}
header{{padding:24px;max-width:1040px;margin:auto}}.badge{{display:inline-block;background:#fce4cf;padding:8px 14px;border-radius:30px}}
main{{max-width:1040px;margin:0 auto 50px;display:grid;grid-template-columns:1.1fr 1fr;background:white;border-radius:20px;overflow:hidden}}
.images{{background:#eceae6;padding:18px;display:flex;flex-direction:column;gap:14px}}img{{width:100%;border-radius:10px;object-fit:contain}}
article{{padding:32px}}h1{{font-size:24px;line-height:1.45}}.text{{white-space:pre-wrap;line-height:1.9;overflow-wrap:anywhere}}
.tags{{color:#496a89;margin-top:24px;line-height:1.7}}small{{color:#666;overflow-wrap:anywhere}}.empty{{padding:100px 20px;text-align:center;color:#777}}
.note{{color:#8b4a15;line-height:1.6}}@media(max-width:700px){{main{{margin:0 12px 24px;grid-template-columns:1fr}}article{{padding:24px}}}}</style>
<header><span class="badge">本地文稿预览 · 未写入小红书草稿</span><p>版本 {saved['revision']} · 最终由你自行发布</p>
<small>文稿 {manuscript_id}<br>内容 SHA-256 {saved['sha256']}</small></header>
<main><section class="images">{image_html}</section><article><h1>{esc(p['title'])}</h1>
<div class="text">{esc(p['content'])}</div><div class="tags">{tags}</div>
<p class="note">{'<br>'.join(map(esc,warnings))}</p></article></main></html>'''
        output = self.root / "previews" / manuscript_id / f"v{saved['revision']}.html"
        atomic_private_write(output, body.encode())
        return {**saved, "preview_path": str(output), "preview_source": SCOPE,
                "platform_editor_preview": False, "warnings": warnings}


def platform_draft_status():
    """Describe source capabilities without importing another account's proof."""
    return {"ok": True, "capability": "implemented_unverified", "platform_saved": False,
            "native_draft_save_implemented": True, "native_draft_reopen_implemented": True,
            "native_draft_update_implemented": True, "diagnostic_test_driver_implemented": True,
            "live_verified": False, "current_session_rechecked": False,
            "storage_scope": "browser_profile_local",
            "reason": "源码包含图文草稿保存和重开；此分发包不携带任何账号的历史验收证据。",
            "next_step": "在目标机器登录独立环境后，按同一原生ID验收保存、重开和修改。",
            "acceptance_required": ["保存后离开并重开核对全部字段和图片",
                                    "修改后重开同一ID且无重复草稿",
                                    "完整浏览器重启后的保留和恢复"],
            "cross_device_sync": "unverified; drafts may be confined to this browser profile"}
