import copy,hashlib,json,pathlib,subprocess,tempfile,unittest
from types import SimpleNamespace
from unittest.mock import patch
from xhs_local.errors import XHSError
from xhs_local.native_media_test import call,APPROVED_RUN,APPROVED_HASHES,JOURNAL,JS

class SyntheticMediaScopeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = pathlib.Path(temporary.name)
        self.data = b"synthetic image fixture; never sent to a real browser"
        assets = self.root / "test-assets"
        assets.mkdir()
        self.image = assets / (APPROVED_RUN + "-image.png")
        self.image.write_bytes(self.data)
        self.digest = hashlib.sha256(self.data).hexdigest()
        for target, value in [("ROOT", self.root), ("APPROVED_HASHES", {"image": self.digest})]:
            mocked = patch("xhs_local.native_media_test." + target, value)
            mocked.start()
            self.addCleanup(mocked.stop)

    def fixture(self):
        return {"run_id": APPROVED_RUN, "items": {"image": {
            "asset": {"path": str(self.image), "name": self.image.name,
                      "sha256": self.digest, "mime": "image/png"},
            "tab_id": "123", "title": "合成测试", "body": "离线夹具",
            "native_draft_id": None, "uploaded": False, "imported_to_editor": False}}}

    def test_media_transport_never_activates_an_app_or_switches_tabs(self):
        self.assertNotIn('.activate(',JS)
        self.assertNotIn('activeTabIndex=',JS)

    def test_known_native_draft_prevents_reimport_even_without_event_history(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'journal.json';j=self.fixture();j['items']['image']['native_draft_id']='existing-test';p.write_text(json.dumps(j))
            with patch('xhs_local.native_media_test.JOURNAL',p),patch('xhs_local.native_media_test.existing_permission') as permission:
                with self.assertRaises(XHSError):call('image','upload')
                permission.assert_not_called()

    def test_publication_upload_alternatives_and_arbitrary_scripts_are_not_actions(self):
        for action in ['publish','private_publish','schedule','delete','evaluate','fetch','file_picker']:
            with self.assertRaises(XHSError):call('image',action)

    def test_wrong_run_or_hash_stops_before_browser_access(self):
        for field in ['run_id','sha256']:
            with tempfile.TemporaryDirectory() as d:
                p=pathlib.Path(d)/'journal.json';j=self.fixture()
                if field=='run_id':j['run_id']='other-task'
                else:j['items']['image']['asset']['sha256']='0'*64
                p.write_text(json.dumps(j))
                with patch('xhs_local.native_media_test.JOURNAL',p),patch('xhs_local.native_media_test.existing_permission') as permission:
                    with self.assertRaises(XHSError):call('image','upload')
                    permission.assert_not_called()

    def test_unapproved_path_stops_without_reading_that_file(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'journal.json';j=self.fixture();j['items']['image']['asset']['path']='/tmp/not-an-approved-user-file.png';p.write_text(json.dumps(j))
            with patch('xhs_local.native_media_test.JOURNAL',p),patch('xhs_local.native_media_test.existing_permission') as permission:
                with self.assertRaises(XHSError):call('image','upload')
                permission.assert_not_called()

    def test_a_second_upload_attempt_is_refused_before_execution(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'journal.json';j=self.fixture();j['events']=[{'kind':'image','action':'upload','status':'outcome_unknown'}];p.write_text(json.dumps(j))
            with patch('xhs_local.native_media_test.JOURNAL',p),patch('xhs_local.native_media_test.existing_permission') as permission:
                with self.assertRaises(XHSError):call('image','upload')
                permission.assert_not_called()

    def test_mock_transport_receives_only_the_pinned_synthetic_file(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'journal.json';p.write_text(json.dumps(self.fixture()))
            result={'data':{'file_selected':True},'foreground_unchanged':True,'active_tab_unchanged':True}
            with patch('xhs_local.native_media_test.JOURNAL',p),patch('xhs_local.native_media_test.existing_permission'),patch('xhs_local.native_media_test.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout=json.dumps(result))) as run:
                call('image','upload')
            payload=json.loads(run.call_args.args[0][-1]);self.assertEqual(payload['file_name'],APPROVED_RUN+'-image.png');self.assertEqual(payload['file_bytes'],len(self.data));self.assertEqual(payload['mime'],'image/png')
            stored=json.loads(p.read_text());self.assertNotIn('base64',json.dumps(stored))
