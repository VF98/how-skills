import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from xhs_local.errors import XHSError
from xhs_local.native_draft_test import ACTIONS,call,validate


def journal():
    return {'run_id':'test-marker','work_tab_id':'123','planned_test':{'title':'功能验证草稿，请勿发布 test-marker','A':'test-marker version A','B':'test-marker version B'}}

class NativeDraftTestGuards(unittest.TestCase):
    def test_only_explicit_diagnostic_actions_are_allowed(self):
        for action in ['publish','private_publish','schedule','upload','delete','evaluate','navigate','click']:
            with self.assertRaises(XHSError):validate(journal(),action)
        for action in ACTIONS:
            j=journal()
            if action in {'set_b','reopen_test','longform_drafts','reload_saved_list'}:
                j['planned_test']['native_draft_id']='00000000-0000-4000-8000-000000000001'
            validate(j,action)

    def test_unmarked_titles_and_text_are_rejected(self):
        for key in ['title','A','B']:
            j=journal();j['planned_test'][key]='ordinary user content'
            with self.assertRaises(XHSError):validate(j,'set_a')

    def test_identical_revisions_are_rejected(self):
        j=journal();j['planned_test']['B']=j['planned_test']['A']
        with self.assertRaises(XHSError):validate(j,'set_b')

    def test_timeout_records_uncertainty_without_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'journal.json';p.write_text(json.dumps(journal()))
            with patch('xhs_local.native_draft_test.existing_permission'),patch('xhs_local.native_draft_test.subprocess.run',side_effect=subprocess.TimeoutExpired('private',8)) as runner:
                with self.assertRaises(XHSError):call(p,'save_a')
            self.assertEqual(runner.call_count,1)
            saved=json.loads(p.read_text())
            self.assertEqual(saved['native_events'][-1]['status'],'outcome_unknown')
            self.assertNotIn('private',saved['native_events'][-1]['error'])

    def test_success_retains_actual_evidence_and_fixed_payload(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'journal.json';p.write_text(json.dumps(journal()))
            result={'foreground_unchanged':True,'active_tab_unchanged':True,'data':{'path':'/publish/publish'}}
            with patch('xhs_local.native_draft_test.existing_permission'),patch('xhs_local.native_draft_test.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout=json.dumps(result))) as runner:
                self.assertEqual(call(p,'inspect'),result)
            payload=json.loads(runner.call_args.args[0][-1])
            self.assertEqual(set(payload),{'action','tab','native_id','title','A','B'})
            self.assertEqual(json.loads(p.read_text())['native_events'][-1]['status'],'completed')

    def test_existing_native_id_prevents_a_second_creation(self):
        j=journal();j['planned_test']['native_draft_id']='already-created'
        for action in ['new','set_a']:
            with self.assertRaises(XHSError):validate(j,action)

    def test_uncertain_write_requires_a_read_before_any_mutation(self):
        j=journal();j['native_events']=[{'status':'outcome_unknown'}]
        with self.assertRaises(XHSError):validate(j,'save_a')
        validate(j,'inspect')


import shutil
from xhs_local.native_draft_test import JS

@unittest.skipUnless(shutil.which('node'),'existing Node required for native DOM guard fixtures')
class NativeDraftDOMGuards(unittest.TestCase):
    def page(self,action,editor=True,revision='A',duplicate_button=False,wrong_card=False):
        fixture=r'''
const fs=require('fs'),vm=require('vm');const p=JSON.parse(fs.readFileSync(0,'utf8'));const clicks=[];let cursor=0;const nodes=[];
function element(props={}){const x=cursor++*120;const e={innerText:'',children:[],tagName:'DIV',className:'fixture',attributes:[],getBoundingClientRect:()=>({x,y:0,width:100,height:30}),contains:o=>o===e,click:()=>clicks.push(e.innerText),getAttribute:()=>null,...props};nodes.push(e);return e;}
const title=element({tagName:'TEXTAREA',value:p.payload.title});
const body=p.payload[p.revision];const paras=body.split('\n').map(t=>element({tagName:'P',innerText:t}));
const rich=element({innerText:body.split('\n').join('\n\n'),children:paras});
const save=element({tagName:'BUTTON',innerText:'暂存离开',disabled:false});const buttons=[save];if(p.duplicate)buttons.push(element({tagName:'BUTTON',innerText:'暂存离开',disabled:false}));
const card={getAttribute:()=>p.wrongCard?'wrong-id':p.payload.native_id};const cardTitle=element({innerText:p.payload.title,closest:()=>card});
const document={title:'Official creator',body:{innerText:'Official creator'},elementFromPoint:x=>nodes.find(e=>{const r=e.getBoundingClientRect();return x>=r.x&&x<=r.x+r.width;}),querySelectorAll:s=>s==='textarea[placeholder="输入标题"]'?(p.editor?[title]:[]):s==='[contenteditable="true"]'?(p.editor?[rich]:[]):s==='textarea,[contenteditable="true"]'?(p.editor?[title,rich]:[]):s==='button'||s==='button,[role="button"]'?buttons:s==='.draft-title-text'?[cardTitle]:[]};
const context={document,location:{pathname:'/publish/publish',search:''},getComputedStyle:()=>({visibility:'visible',opacity:'1'}),innerWidth:10000,innerHeight:1000,payload:p.payload};
try{const result=vm.runInNewContext(p.source+';PAGE(payload)',context);process.stdout.write(JSON.stringify({result,clicks}));}catch(e){process.stdout.write(JSON.stringify({error:e.message,clicks}));}
'''
        payload={'action':action,'title':'功能验证草稿，请勿发布 fixture','A':'test-marker\nversion A','B':'test-marker\nversion B','native_id':'expected-id'}
        data={'source':JS[JS.index('function PAGE(p){'):],'payload':payload,'editor':editor,'revision':revision,'duplicate':duplicate_button,'wrongCard':wrong_card}
        result=subprocess.run([shutil.which('node'),'-e',fixture],input=json.dumps(data),capture_output=True,text=True,check=True,timeout=5)
        return json.loads(result.stdout)

    def test_save_requires_exact_expected_body_before_click(self):
        result=self.page('save_b',revision='A')
        self.assertEqual(result['error'],'test_content_mismatch')
        self.assertEqual(result['clicks'],[])

    def test_save_only_clicks_the_explicit_draft_control(self):
        result=self.page('save_b',revision='B')
        self.assertEqual(result['clicks'],['暂存离开'])
        self.assertEqual(result['result'],{'clicked':'暂存离开'})

    def test_duplicate_save_controls_stop_without_click(self):
        result=self.page('save_a',duplicate_button=True)
        self.assertIn('expected_unique_control',result['error'])
        self.assertEqual(result['clicks'],[])

    def test_paragraph_readback_preserves_raw_and_logical_text(self):
        result=self.page('inspect')['result']
        self.assertEqual(result['body'],'test-marker\nversion A')
        self.assertEqual(result['raw_body'],'test-marker\n\nversion A')

    def test_an_open_editor_cannot_be_reloaded_by_the_driver(self):
        self.assertEqual(self.page('reload_saved_list')['error'],'save_and_leave_before_reload')

    def test_a_changed_native_card_id_stops_reopen(self):
        result=self.page('reopen_test',editor=False,wrong_card=True)
        self.assertEqual(result['error'],'native_draft_id_changed')
        self.assertEqual(result['clicks'],[])
