import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from xhs_local.app import App
from xhs_local.drafts import atomic_private_write
from xhs_local.errors import XHSError
from xhs_local.isolated import IsolatedRuntime, isolated_request_allowed


class IsolationSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.app=App(self.root)
        atomic_private_write(self.root/'browser-backend.json',b'{"mode":"isolated_headless","desktop_fallback":false}')

    def tearDown(self):self.temp.cleanup()

    def test_daily_browser_entries_stop_before_apple_events(self):
        with patch('xhs_local.app.NativeChromeBrowser') as native,patch('xhs_local.app.bind_existing') as bind:
            for f in [lambda:self.app.browser(),lambda:self.app.bind_native('1','2'),
                      lambda:self.app.run_tool('xhs_creator_inspect',{}),
                      lambda:self.app.run_tool('xhs_search',{'keyword':'AI'})]:
                with self.assertRaises(XHSError) as error:f()
                self.assertEqual(error.exception.code,'desktop_browser_disabled')
            native.assert_not_called();bind.assert_not_called()

    def test_platform_tab_binding_cannot_select_daily_chrome(self):
        with patch('xhs_local.isolated.IsolatedRuntime.ensure') as start:
            with self.assertRaises(XHSError):self.app.run_tool('xhs_platform_draft_bind',{'window_id':'1','tab_id':'2'})
            start.assert_not_called()

    def test_only_dedicated_headless_process_is_started_without_gui_launcher(self):
        runtime=IsolatedRuntime(self.root)
        def start(args,**kw):
            self.assertIn('--headless=new',args);self.assertIn('--no-startup-window',args)
            self.assertIn('--user-data-dir='+str(runtime.profile),args)
            self.assertNotIn('--no-sandbox',args);self.assertNotIn('open',args)
            (runtime.profile/'DevToolsActivePort').write_text('12345\n/devtools/browser/owned\n')
            return SimpleNamespace(pid=12345,poll=lambda:None)
        with patch('xhs_local.isolated.subprocess.Popen',side_effect=start) as process:
            state=runtime.ensure()
            self.assertTrue(state['headless']);process.assert_called_once()
            self.assertTrue(process.call_args.kwargs['start_new_session'])

    def test_wrong_process_or_recorded_site_restriction_never_falls_back(self):
        runtime=IsolatedRuntime(self.root)
        for value in [{'pid':12345},{'site_restriction':{'code':'300012'}}]:
            runtime._write(value)
            with patch('xhs_local.isolated.subprocess.run',return_value=subprocess.CompletedProcess([],0,'unrelated process','')),patch('xhs_local.isolated.subprocess.Popen') as start:
                with self.assertRaises(XHSError):runtime.ensure()
                start.assert_not_called()

    def test_publish_and_social_writes_are_blocked_while_login_and_image_uploads_work(self):
        for method in ('POST','PUT','PATCH','DELETE'):
            for url in ('https://creator.xiaohongshu.com/web_api/sns/v2/note','https://edith.xiaohongshu.com/api/sns/web/v1/note/post','https://creator.xiaohongshu.com/api/publish','https://edith.xiaohongshu.com/api/sns/web/v1/comment/post','https://edith.xiaohongshu.com/api/sns/web/v1/note/like'):
                self.assertFalse(isolated_request_allowed(method,url),(method,url))
        self.assertTrue(isolated_request_allowed('POST','https://creator.xiaohongshu.com/api/login/qrcode'))
        self.assertTrue(isolated_request_allowed('PUT','https://ros-upload.xhscdn.com/object/image'))
        self.assertFalse(isolated_request_allowed('POST','https://unrelated.test/upload'))
        self.assertFalse(isolated_request_allowed('POST','https://creator.xiaohongshu.com/api/note/publish_image'))
        self.assertTrue(isolated_request_allowed('POST','https://creator.xiaohongshu.com/api/media/v1/upload/permit'))

    def test_invalid_login_capture_flag_stops_before_browser_start(self):
        with patch('xhs_local.isolated.IsolatedRuntime.ensure') as start:
            with self.assertRaises(XHSError):self.app.run_tool('xhs_isolated_status',{'capture_login':'true'})
            start.assert_not_called()

    def test_virtual_focus_is_scoped_to_registered_headless_targets(self):
        runtime=IsolatedRuntime(self.root);runtime.profile.mkdir()
        (runtime.profile/'DevToolsActivePort').write_text('12345\n/devtools/browser/owned\n')
        state={'generation':'owned','targets':['registered'],'headless':True}
        with patch.object(runtime,'ensure',return_value=state),patch('xhs_local.isolated.WebSocket'),patch('xhs_local.isolated.Browser') as browser:
            browser.return_value.call.return_value={'sessionId':'session'}
            with self.assertRaises(XHSError):
                with runtime.connection({'window_id':'daily','tab_id':'unregistered'}):pass
            browser.return_value.call.assert_not_called()
            with runtime.connection({'window_id':'owned','tab_id':'registered'}):pass
            calls=browser.return_value.call.call_args_list
            self.assertEqual(calls[0].args,('Target.activateTarget',{'targetId':'registered'}))
            self.assertEqual(calls[1].args,('Target.attachToTarget',{'targetId':'registered','flatten':True}))


if __name__=='__main__':unittest.main()
