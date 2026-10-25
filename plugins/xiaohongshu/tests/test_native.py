import json
from pathlib import Path
import tempfile
import subprocess
import shutil
import unittest
from unittest.mock import patch

from xhs_local.app import App
from xhs_local.errors import XHSError
from xhs_local.native_chrome import NativeChromeBrowser, bind_existing, validate_native_url, native_call, JXA, READERS
from xhs_local.research import SNAPSHOT_JS, normalize_detail, normalize_search

BINDING = {"window_id": "1", "anchor_tab_id": "2", "work_tab_id": "3", "creator_tab_id": "4",
           "public_account_id": "1234567890abcdef12345678", "route": "existing_chrome_apple_events"}
HOME = "https://www.xiaohongshu.com/explore"
SEARCH = "https://www.xiaohongshu.com/search_result?keyword=fixture"


class FakeChrome:
    def __init__(self):
        self.calls = []
        self.risk = False
        self.denied = False
        self.active = False

    def __call__(self, action, binding, **kwargs):
        self.calls.append((action, kwargs))
        if self.active:
            raise XHSError("native_work_tab_active", "active work tab")
        if action in {"bind", "lease"}:
            return {"ok": True, **BINDING, "original_work_url": HOME, "foreground_and_activity_unchanged": True}
        if action == "meta":
            return {"ok": True, "title": "安全限制" if self.risk else "fixture", "loading": False, "url": SEARCH}
        if action == "read":
            if self.denied:
                raise XHSError("native_page_read_rejected", "denied")
            return {"ok": True, "data": {"url": SEARCH, "feeds": [], "emptyState": True}}
        return {"ok": True, "foreground_and_activity_unchanged": True}


class NativeChromeTests(unittest.TestCase):
    def test_success_restores_only_its_inactive_work_tab(self):
        runner = FakeChrome()
        with NativeChromeBrowser(BINDING, runner) as browser:
            browser.navigate(SEARCH)
            self.assertTrue(browser.evaluate(SNAPSHOT_JS)["emptyState"])
        self.assertEqual([a for a, _ in runner.calls], ["lease", "navigate", "meta", "read", "restore"])
        self.assertEqual(runner.calls[-1][1], {"original_url": HOME, "expected_url": SEARCH})
        self.assertTrue(browser.evidence()["work_tab_restored"])

    def test_risk_stops_without_restore_navigation_or_fallback(self):
        runner = FakeChrome(); runner.risk = True
        with self.assertRaises(XHSError) as caught:
            with NativeChromeBrowser(BINDING, runner) as browser:
                browser.navigate(SEARCH)
        self.assertEqual(caught.exception.code, "site_access_blocked")
        self.assertEqual([a for a, _ in runner.calls], ["lease", "navigate", "meta"])

    def test_page_rejection_stops_without_restore_or_new_permissions(self):
        runner = FakeChrome(); runner.denied = True
        with self.assertRaises(XHSError):
            with NativeChromeBrowser(BINDING, runner) as browser:
                browser.navigate(SEARCH)
                browser.evaluate(SNAPSHOT_JS)
        self.assertNotIn("restore", [a for a, _ in runner.calls])

    def test_active_tab_is_never_navigated(self):
        runner = FakeChrome(); runner.active = True
        with self.assertRaises(XHSError):
            with NativeChromeBrowser(BINDING, runner):
                pass
        self.assertEqual([a for a, _ in runner.calls], ["lease"])

    def test_arbitrary_scripts_are_not_a_reader(self):
        runner = FakeChrome()
        with self.assertRaises(XHSError):
            with NativeChromeBrowser(BINDING, runner) as browser:
                browser.evaluate("document.cookie")
        self.assertNotIn("read", [a for a, _ in runner.calls])

    def test_navigation_allowlist_rejects_messages_uploads_api_and_external(self):
        for url in ["https://www.xiaohongshu.com/message", "https://creator.xiaohongshu.com/api/publish",
                    "https://creator.xiaohongshu.com/web_api/sns/v2/note", "https://evil.test/",
                    "file:///tmp/private", "https://user:secret@www.xiaohongshu.com/explore"]:
            with self.assertRaises(XHSError):
                validate_native_url(url)
        validate_native_url(SEARCH)
        validate_native_url("https://creator.xiaohongshu.com/publish/publish?source=official")

    def test_binding_saves_references_without_auth_material(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "native-binding.json"
            result = bind_existing(path, "2", "3", "4", FakeChrome())
            saved = json.loads(path.read_text())
            self.assertEqual(set(saved), set(BINDING))
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertFalse(result["credentials_copied"])
            self.assertFalse(result["new_permissions_created"])

    def test_missing_binding_cannot_fall_back_to_legacy_headless(self):
        with tempfile.TemporaryDirectory() as folder:
            app = App(Path(folder)/"data")
            with patch("xhs_local.app.NativeChromeBrowser") as native:
                with self.assertRaises(XHSError) as caught:
                    app.run_tool("xhs_search", {"keyword": "fixture"})
                self.assertEqual(caught.exception.code, "native_binding_required")
                native.assert_not_called()
            with self.assertRaises(XHSError) as caught:
                app.confirm_account(True)
            self.assertEqual(caught.exception.code, "legacy_browser_paused")

    def test_native_control_code_has_no_activation_click_upload_or_debug_connection(self):
        for marker in [".activate(", ".click(", "fetch(", "WebSocket(", "document.cookie", "setFileInputFiles"]:
            self.assertNotIn(marker, JXA)
        self.assertEqual(set(READERS), {"account", "snapshot", "search_dom", "creator", "creator_form"})

    def test_timeout_does_not_expose_command_or_retry(self):
        with patch("xhs_local.native_chrome.existing_permission"), patch("xhs_local.native_chrome.subprocess.run", side_effect=subprocess.TimeoutExpired("private-command-value",20)) as run:
            with self.assertRaises(XHSError) as caught:
                native_call("read",BINDING,reader="creator")
            self.assertEqual(caught.exception.code,"native_timeout")
            self.assertNotIn("private-command-value",str(caught.exception))
            self.assertEqual(run.call_count,1)


@unittest.skipUnless(shutil.which('node'), 'existing Node required for DOM regression fixture')
class ObservedDOMRegressionTests(unittest.TestCase):
    def snapshot(self, detail=False):
        fixture = r"""
const fs=require('fs'),vm=require('vm');
const p=JSON.parse(fs.readFileSync(0,'utf8'));
const id='1234567890abcdef12345678';
const href='https://www.xiaohongshu.com/search_result/'+id+'?xsec_token=fixture-public&xsec_source=pc_search';
const visible={getBoundingClientRect:()=>({width:20,height:20})};
const title={...visible,innerText:'Robot DOM fixture'};
const desc={...visible,innerText:'Public description fixture'};
const author={...visible,innerText:'Fixture author'};
const anchors=[{href:'https://www.xiaohongshu.com/explore/'+id},{href}];
const card={...visible,querySelector:s=>s==='.title'?title:s.includes('.name')?author:null,querySelectorAll:()=>anchors};
const document={title:'Fixture',body:{innerText:'Fixture'},
 querySelector:s=>s==='#detail-title'&&p.detail?title:s==='#detail-desc'&&p.detail?desc:s==='link[rel="canonical"]'&&p.detail?{href}:s.includes('.author-container')&&p.detail?author:s.includes('.main-container')?visible:null,
 querySelectorAll:s=>s==='section.note-item,.note-item'?(p.detail?[]:[card]):s==='a[href]'?anchors:[]};
const location={href:p.detail?href:'https://www.xiaohongshu.com/search_result?keyword=fixture',pathname:p.detail?'/search_result/'+id:'/search_result'};
const result=vm.runInNewContext(p.script,{document,location,window:{},URL},{timeout:1000});
process.stdout.write(JSON.stringify(result));
"""
        p=subprocess.run([shutil.which('node'),'-e',fixture],input=json.dumps({'script':SNAPSHOT_JS,'detail':detail}),capture_output=True,text=True,check=True,timeout=5)
        return json.loads(p.stdout)

    def test_search_without_initial_state_uses_visible_cards_and_signed_original(self):
        result=normalize_search(self.snapshot(),'fixture',3)
        self.assertEqual(result['extraction_source'],'visible_note_cards')
        self.assertEqual(result['notes'][0]['title'],'Robot DOM fixture')
        self.assertIn('/search_result/',result['notes'][0]['url'])
        self.assertIn('fixture-public',result['notes'][0]['url'])
        self.assertEqual(result['notes'][0]['link_origin'],'observed_page_href')

    def test_detail_without_initial_state_verifies_canonical_and_public_body(self):
        data=self.snapshot(True)
        result=normalize_detail(data,data['url'])
        self.assertEqual(result['content'],'Public description fixture')
        self.assertTrue(result['link_identity_verified'])
        self.assertEqual(result['extraction_source'],'visible_note_detail')


if __name__ == "__main__":
    unittest.main()
