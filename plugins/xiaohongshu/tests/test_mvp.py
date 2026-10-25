import base64
import io
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from xhs_local.app import App, TOOLS
from xhs_local.browser import Browser, CHROME, WebSocket, request_allowed
from xhs_local.cli import mcp
from xhs_local.drafts import DraftStore, platform_draft_status
from xhs_local.errors import XHSError
from xhs_local.research import normalize_detail, normalize_search, SNAPSHOT_JS, CREATOR_INSPECT_JS, validate_note_url

ROOT = Path(__file__).resolve().parents[1]
ID = "1234567890abcdef12345678"
URL = f"https://www.xiaohongshu.com/explore/{ID}?xsec_token=fixture-public-signature&xsec_source=pc_search&source=fixture"


def fixture_snapshot():
    return {"loggedIn": True, "loginPrompt": False, "links": [URL],
            "feeds": [{"id": ID, "modelType": "note", "xsecToken": "fixture-public-signature",
                       "noteCard": {"displayTitle": "离线测试笔记", "type": "normal", "user": {"nickname": "测试作者"}}},
                      {"id": "bad", "modelType": "live_v2"}],
            "notes": {ID: {"noteId": ID, "title": "离线测试笔记", "desc": "这是离线正文。不是网站检索结果。",
                           "user": {"nickname": "测试作者"}}}}


class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.app = App(Path(self.tmp.name) / "data")

    def assert_code(self, code, fn):
        with self.assertRaises(XHSError) as caught:
            fn()
        self.assertEqual(caught.exception.code, code)

    def test_no_account_no_browser_or_credentials_created(self):
        with patch("xhs_local.app.NativeChromeBrowser") as browser:
            self.assert_code("native_binding_required", lambda: self.app.run_tool("xhs_search", {"keyword": "测试"}))
            browser.assert_not_called()
        self.assertFalse(self.app.data_dir.exists())

    def test_write_tools_not_registered_and_cannot_be_called(self):
        names = {x["name"] for x in TOOLS}
        forbidden = {"publish_content", "publish_with_video", "save_draft", "cloud_draft", "post_comment_to_feed",
                     "like_feed", "favorite_feed", "schedule_publish", "get_login_qrcode", "delete_cookies", "evaluate"}
        self.assertFalse(names & forbidden)
        with patch("xhs_local.app.NativeChromeBrowser") as browser:
            for name in forbidden:
                self.assert_code("tool_not_allowed", lambda n=name: self.app.run_tool(n, {}))
            browser.assert_not_called()
        self.assertFalse(self.app.data_dir.exists())

    def test_publish_private_scheduled_comments_upload_all_network_blocked(self):
        urls = ["https://creator.xiaohongshu.com/web_api/sns/v2/note",
                "https://edith.xiaohongshu.com/api/sns/web/v1/note/post",
                "https://edith.xiaohongshu.com/api/sns/web/v1/comment/post",
                "https://edith.xiaohongshu.com/api/sns/web/v1/note/like",
                "https://creator.xiaohongshu.com/api/draft/save",
                "https://upload.xhscdn.com/media", "http://127.0.0.1:9999/publish"]
        for url in urls:
            for method in ["POST", "PUT", "DELETE", "PATCH"]:
                self.assertFalse(request_allowed(method, url), (method, url))
        self.assertTrue(request_allowed("POST", "https://edith.xiaohongshu.com/api/sns/web/v1/search/notes"))
        self.assertFalse(request_allowed("POST", "https://evil.test/api/sns/web/v1/search/notes"))
        self.assertFalse(request_allowed("POST", "http://edith.xiaohongshu.com/api/sns/web/v1/search/notes"))
        self.assertFalse(request_allowed("POST", "https://edith.xiaohongshu.com/api/sns/web/v1/search/notes/../publish"))

    def test_native_draft_status_does_not_reuse_historical_account_proof(self):
        value = self.app.run_tool("xhs_platform_draft_status", {})
        self.assertFalse(value["platform_saved"])
        self.assertTrue(value["native_draft_save_implemented"])
        self.assertTrue(value["native_draft_update_implemented"])
        self.assertEqual(value["capability"], "implemented_unverified")
        self.assertTrue(value["diagnostic_test_driver_implemented"])
        self.assertFalse(value["live_verified"])
        self.assertNotIn("recorded_verification", value)
        self.assertFalse(value["current_session_rechecked"])
        self.assertEqual(value["storage_scope"], "browser_profile_local")
        self.assertFalse(self.app.data_dir.exists())

    def test_invalid_arguments_are_rejected_before_launch(self):
        with patch("xhs_local.app.NativeChromeBrowser") as browser:
            self.assert_code("invalid_arguments", lambda: self.app.run_tool("xhs_search", {"keyword": "x", "publish": True}))
            self.assert_code("invalid_limit", lambda: self.app.run_tool("xhs_search", {"keyword": "x", "limit": True}))
            self.assert_code("invalid_note_url", lambda: self.app.run_tool("xhs_read_note", {"url": "http://127.0.0.1"}))
            browser.assert_not_called()

    def test_account_instructions_never_launch_gui(self):
        with patch("subprocess.Popen") as popen:
            result = self.app.account_instructions()
            self.assertFalse(result["gui_launched"])
            self.assertFalse(result["requires_user_confirmation"])
            self.assertTrue(result["existing_session_only"])
            self.assertFalse(result["permissions_changed_by_plugin"])
            popen.assert_not_called()
        self.assertFalse(self.app.data_dir.exists())

    def test_personal_chrome_profile_cannot_be_selected(self):
        for path in [Path.home(), Path("/"), Path.home()/"Library/Application Support/Google/Chrome"]:
            self.assert_code("unsafe_storage", lambda p=path: App(p))

    def test_mcp_protocol_and_unknown_tool_refusal(self):
        messages = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26"}},
                    {"jsonrpc": "2.0", "method": "notifications/initialized"},
                    {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                    {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "publish_content", "arguments": {}}}]
        output = io.StringIO()
        mcp(self.app, io.StringIO("\n".join(map(json.dumps, messages))), output)
        result = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["result"]["protocolVersion"], "2025-03-26")
        self.assertEqual(len(result[1]["result"]["tools"]), 16)
        self.assertTrue(result[2]["result"]["isError"])

    def test_broken_mcp_request_does_not_stop_following_request(self):
        output = io.StringIO()
        mcp(self.app, io.StringIO('{broken}\n{"jsonrpc":"2.0","id":4,"method":"ping"}\n'), output)
        result = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertIn("error", result[0])
        self.assertEqual(result[1]["result"], {})


class ResearchTests(unittest.TestCase):
    def test_original_href_preserves_public_share_parameters(self):
        result = normalize_search(fixture_snapshot(), "测试", 10)
        self.assertEqual(len(result["notes"]), 1)
        self.assertEqual(result["notes"][0]["url"], URL)
        self.assertEqual(result["notes"][0]["link_origin"], "observed_page_href")
        self.assertFalse(result["notes"][0]["detail_read"])

    def test_link_fallback_is_labelled_instead_of_called_observed(self):
        snap = fixture_snapshot()
        snap["links"] = []
        note = normalize_search(snap, "测试", 1)["notes"][0]
        self.assertEqual(note["link_origin"], "constructed_from_public_note_fields")
        self.assertIn("fixture-public-signature", note["url"])

    def test_note_identity_must_match_link(self):
        result = normalize_detail(fixture_snapshot(), URL)
        self.assertTrue(result["link_identity_verified"])
        snap = fixture_snapshot()
        snap["notes"][ID]["noteId"] = "different"
        with self.assertRaises(XHSError):
            normalize_detail(snap, URL)

    def test_conflicting_canonical_note_identity_rejected(self):
        snap = fixture_snapshot()
        snap["notes"][ID]["canonical_note_id"] = "abcdef1234567890abcdef12"
        with self.assertRaises(XHSError):
            normalize_detail(snap, URL)

    def test_login_wall_and_unverified_empty_results_do_not_become_success(self):
        for snap in [{"loginPrompt": True, "loggedIn": False}, {"feeds": []}, {}]:
            with self.assertRaises(XHSError):
                normalize_search(snap, "测试", 3)
        self.assertEqual(normalize_search({"feeds": [], "emptyState": True}, "测试", 3)["notes"], [])

    def test_url_validation_prevents_external_requests_and_credentials(self):
        for url in ["https://evil.test/explore/"+ID, "https://www.xiaohongshu.com.evil.test/explore/"+ID,
                    "https://user:secret@www.xiaohongshu.com/explore/"+ID,
                    "https://www.xiaohongshu.com:wrong/explore/"+ID, "file:///tmp/secret"]:
            with self.assertRaises(XHSError):
                validate_note_url(url)


class ManuscriptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "manuscripts"

    def test_a_b_reopen_after_new_process_same_id_and_old_revision_retained(self):
        with DraftStore(self.root) as store:
            a = store.create({"title": "测试 A", "content": "正文 A", "tags": ["测试"]})
            b = store.update(a["manuscript_id"], 1, {"title": "测试 B", "content": "正文 B"})
            self.assertEqual(a["manuscript_id"], b["manuscript_id"])
            self.assertEqual(b["revision"], 2)
            self.assertNotEqual(a["sha256"], b["sha256"])
            self.assertFalse(b["platform_saved"])
            self.assertEqual(store.get(a["manuscript_id"], 1)["payload"]["title"], "测试 A")
        script = "from xhs_local.drafts import DraftStore; import json,sys; s=DraftStore(sys.argv[1]); print(json.dumps(s.get(sys.argv[2]),ensure_ascii=False))"
        reopened = json.loads(subprocess.check_output([sys.executable, "-c", script, str(self.root), a["manuscript_id"]], cwd=ROOT))
        self.assertEqual(reopened["payload"]["title"], "测试 B")
        self.assertEqual(reopened["sha256"], b["sha256"])
        self.assertEqual(reopened["storage_scope"], "local_manuscript_only")

    def test_stale_update_is_refused_and_no_duplicate_manuscript_created(self):
        with DraftStore(self.root) as store:
            a = store.create({"title": "A", "content": "A"})
            store.update(a["manuscript_id"], 1, {"title": "B"})
            with self.assertRaises(XHSError) as caught:
                store.update(a["manuscript_id"], 1, {"title": "C"})
            self.assertEqual(caught.exception.code, "revision_conflict")
            self.assertEqual(store.db.execute("SELECT COUNT(*) FROM manuscripts").fetchone()[0], 1)
            self.assertEqual(store.get(a["manuscript_id"])["payload"]["title"], "B")

    def test_idempotent_update_does_not_increment_version(self):
        with DraftStore(self.root) as store:
            a = store.create({"title": "A", "content": "A"})
            b = store.update(a["manuscript_id"], 1, {"title": "A"})
            self.assertEqual(a["revision"], b["revision"])

    def test_preview_is_escaped_inert_and_matches_persisted_revision(self):
        with DraftStore(self.root) as store:
            a = store.create({"title": "<script>attack</script>", "content": '<img src=x onerror="attack()">', "tags": ["<tag>"]})
            preview = store.preview(a["manuscript_id"])
            text = Path(preview["preview_path"]).read_text()
            self.assertIn("未写入小红书草稿", text)
            self.assertIn("&lt;script&gt;", text)
            self.assertNotIn("<script>", text)
            self.assertIn(a["sha256"], text)
            self.assertFalse(preview["platform_editor_preview"])
            self.assertIn("Content-Security-Policy", text)

    def test_image_order_survives_source_removal_and_update(self):
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRz8AAAAASUVORK5CYII=")
        image = Path(self.tmp.name) / "sample.png"
        image.write_bytes(png)
        with DraftStore(self.root) as store:
            a = store.create({"title": "A", "content": "A", "images": [str(image), str(image)]})
            image.unlink()
            b = store.update(a["manuscript_id"], 1, {"content": "B"})
            self.assertEqual(a["payload"]["images"], b["payload"]["images"])
            preview = store.preview(a["manuscript_id"])
            self.assertEqual(Path(preview["preview_path"]).read_text().count("data:image/png;base64,"), 2)

    def test_unknown_fields_and_remote_images_rejected(self):
        with DraftStore(self.root) as store:
            for value in [{"title": "A", "content": "A", "visibility": "仅自己可见"},
                          {"title": "A", "content": "A", "images": ["https://evil.test/x.png"]}]:
                with self.assertRaises(XHSError):
                    store.create(value)

    def test_store_permissions_are_private(self):
        with DraftStore(self.root) as store:
            store.create({"title": "A", "content": "A"})
        self.assertEqual(self.root.stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.root/"manuscripts.sqlite3").stat().st_mode & 0o777, 0o600)


class WebSocketTests(unittest.TestCase):
    def test_fragmented_message_with_ping_is_reassembled(self):
        reader, writer = socket.socketpair()
        self.addCleanup(reader.close)
        self.addCleanup(writer.close)
        client = WebSocket.__new__(WebSocket)
        client.sock, client.buffer = reader, bytearray()
        writer.sendall(b'\x01\x05{"ok"' + b'\x89\x01x' + b'\x80\x06:true}')
        self.assertEqual(client.receive(), {"ok": True})
        self.assertEqual(writer.recv(2)[0], 0x8a)


@unittest.skipUnless(os.environ.get("XHS_RUN_CHROME_TESTS") == "1" and CHROME.is_file(), "opt-in real headless Chrome offline test")
class ChromeOfflineTests(unittest.TestCase):
    def test_real_headless_reading_blocks_publication_and_keeps_focus(self):
        requests = []
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                data = b"<!doctype html><html><title>Offline fixture</title><body>Offline fixture</body></html>"
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(data)
            def do_POST(self):
                requests.append(self.path)
                self.send_response(200)
                self.end_headers()
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        front = ["/usr/bin/osascript", "-l", "JavaScript", "-e",
                 "ObjC.import('AppKit'); ObjC.unwrap($.NSWorkspace.sharedWorkspace.frontmostApplication.bundleIdentifier)"]
        before = subprocess.check_output(front).strip()
        self.assertTrue(before)
        with Browser() as browser:
            browser.navigate(f"http://127.0.0.1:{server.server_port}/fixture")
            snap = fixture_snapshot()
            initial = {"search": {"feeds": {"_value": snap["feeds"]}},
                       "note": {"noteDetailMap": {ID: {"note": snap["notes"][ID]}}},
                       "private_account_fixture": {"cookie": "MUST_NOT_BE_EXTRACTED"}}
            browser.evaluate("window.__INITIAL_STATE__=" + json.dumps(initial))
            public = browser.evaluate(SNAPSHOT_JS)
            self.assertNotIn("MUST_NOT_BE_EXTRACTED", json.dumps(public))
            # Identity/source validation itself is exercised with the actual
            # offline origin explicitly replaced by our synthetic official URL.
            # This is fixture data, never a claim of a real website check.
            public["url"] = "https://www.xiaohongshu.com/search_result?keyword=fixture"
            self.assertEqual(normalize_search(public, "离线", 10)["notes"][0]["note_id"], ID)
            public["url"] = URL
            self.assertEqual(normalize_detail(public, URL)["content"], snap["notes"][ID]["desc"])
            browser.evaluate("document.body.innerHTML += '<input type=password value=DO_NOT_READ><button>草稿箱</button>'")
            controls = browser.evaluate(CREATOR_INSPECT_JS)
            self.assertNotIn("DO_NOT_READ", json.dumps(controls))
            self.assertIn("草稿箱", json.dumps(controls, ensure_ascii=False))
            # The final publication route is blocked at the browser network layer,
            # even if an unexpected page script attempts a direct POST.
            outcome = browser.evaluate("fetch('/api/sns/web/v1/note/post',{method:'POST',body:'private-or-public'}).then(()=>false).catch(()=>true)")
            self.assertTrue(outcome)
            self.assertEqual(browser.blocked_requests, 1)
        after = subprocess.check_output(front).strip()
        self.assertEqual(before, after, "headless offline test must preserve foreground app")
        self.assertEqual(requests, [])


if __name__ == "__main__":
    unittest.main()
