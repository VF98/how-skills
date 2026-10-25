import copy
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from xhs_local.drafts import DraftStore
from xhs_local.errors import XHSError
from xhs_local.platform import PlatformDrafts, native_call


class OfficialEditor:
    def __init__(self):
        self.tabs={'1':{'mode':'landing'}}
        self.cards={}
        self.actions=[]
        self.uploads=0

    def __call__(self,action,binding,**p):
        self.actions.append(action)
        t=self.tabs[binding['tab_id']]
        if action=='inspect':
            return {'ready':'complete','controls':[{'text':'草稿箱'}],
                    'categories':['图文笔记(1)'] if t['mode']=='list' else [],
                    'cards':[{'id':i,'title':v['title']} for i,v in self.cards.items()] if t['mode']=='list' else [],
                    'editor_present':t['mode']=='editor','upload_gate':t['mode']=='landing',
                    'title':t.get('title'),'content':t.get('content'),'image_elements':t.get('images',0),'decoded_image_count':t.get('images',0)}
        if action=='new_check_tab':
            tid=str(len(self.tabs)+1);self.tabs[tid]={'mode':'landing'}
            return {'window_id':'10','tab_id':tid}
        if action=='reset_check_tab':
            t.clear();t['mode']='landing';return {'reset':True}
        if action=='retire_editor':
            t.clear();t['mode']='landing';return {'retired':True}
        if action=='drafts':
            t['mode']='list';return {'opened':True}
        if action=='category':return {'clicked':'图文笔记(1)'}
        if action=='upload':
            self.uploads+=1;t.update(mode='editor',title='',content='',images=len(p['assets']));return {'selected_images':len(p['assets'])}
        if action=='set_text':
            t.update(title=p['title'],content=p['content']);return {'text_entered':True}
        if action=='save':
            tid=t.setdefault('native_id','owned-id' if not self.cards else 'owned-id-'+str(len(self.cards)+1));self.cards[tid]=copy.deepcopy(t);return {'method':'official_auto_save'}
        if action=='reopen':
            value=self.cards[p['native_id']];t.clear();t.update(copy.deepcopy(value));return {'native_draft_id':p['native_id']}
        raise AssertionError(action)


class PlatformTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.browser=OfficialEditor();self.platform=PlatformDrafts(self.root,self.browser)
        self.platform.bind('10','1')
        self.image=self.root/'image.png';self.image.write_bytes(b'\x89PNG\r\n\x1a\n'+b'fixture')
        with DraftStore(self.root/'manuscripts') as s:
            self.local=s.create({'title':'标题','content':'第一行\n\n第二行','tags':['AI'],'images':[str(self.image)]})
        self.sleep=patch('xhs_local.platform.time.sleep');self.sleep.start()

    def tearDown(self):
        self.sleep.stop();self.tmp.cleanup()

    def test_create_edit_and_reopen_keep_one_native_id_and_one_upload(self):
        mid=self.local['manuscript_id'];first=self.platform.sync(mid,1)
        with DraftStore(self.root/'manuscripts') as s:s.update(mid,1,{'title':'新标题'})
        second=self.platform.sync(mid,2)
        self.assertEqual(sum(t['mode']=='editor' for t in self.browser.tabs.values()),1)
        third=self.platform.reopen(mid)
        self.assertEqual([r['native_draft_id'] for r in (first,second,third)],['owned-id']*3)
        self.assertEqual(self.browser.uploads,1)
        self.assertEqual(len(self.browser.cards),1)
        self.assertEqual(third['observation']['content'],'第一行\n\n第二行\n\n#AI')
        self.assertEqual(sum(t['mode']=='editor' for t in self.browser.tabs.values()),1)

    def test_unknown_upload_outcome_is_not_retried(self):
        original=self.platform.runner
        def timeout(action,*a,**kw):
            if action=='upload':raise XHSError('platform_outcome_unknown','timeout')
            return original(action,*a,**kw)
        self.platform.runner=timeout
        with self.assertRaises(XHSError):self.platform.sync(self.local['manuscript_id'],1)
        count=len(self.browser.actions)
        with self.assertRaises(XHSError):self.platform.sync(self.local['manuscript_id'],1)
        self.assertEqual(len(self.browser.actions),count)
        with self.assertRaises(XHSError):self.platform.reconcile(self.local['manuscript_id'],1)
        self.assertEqual(self.browser.uploads,0)

    def test_reconcile_finishes_exact_pending_content_without_reupload(self):
        original=self.platform._finish
        self.platform._finish=lambda *a,**kw:(_ for _ in ()).throw(XHSError('interrupted','stopped'))
        with self.assertRaises(XHSError):self.platform.sync(self.local['manuscript_id'],1)
        self.platform._finish=original
        result=self.platform.reconcile(self.local['manuscript_id'],1)
        self.assertTrue(result['platform_saved']);self.assertEqual(self.browser.uploads,1)

    def test_manual_edit_is_preserved_before_any_navigation(self):
        mid=self.local['manuscript_id'];r=self.platform.sync(mid,1)
        self.browser.tabs[r['binding']['tab_id']]['content']='手工修改'
        with DraftStore(self.root/'manuscripts') as s:s.update(mid,1,{'title':'新标题'})
        count=len(self.browser.actions)
        with self.assertRaises(XHSError):self.platform.sync(mid,2)
        self.assertNotIn('reset_check_tab',self.browser.actions[count:])
        self.assertEqual(self.browser.tabs[r['binding']['tab_id']]['content'],'手工修改')

    def test_stale_revision_and_changed_asset_stop_before_browser(self):
        count=len(self.browser.actions)
        with self.assertRaises(XHSError):self.platform.sync(self.local['manuscript_id'],2)
        with DraftStore(self.root/'manuscripts') as s:
            (s.assets/self.local['payload']['images'][0]['sha256']).write_bytes(b'changed')
        with self.assertRaises(XHSError):self.platform.sync(self.local['manuscript_id'],1)
        self.assertEqual(len(self.browser.actions),count)

    def test_native_bridge_keeps_large_media_off_process_arguments(self):
        result={'data':{'selected_images':1},'foreground_unchanged':True,'active_tabs_unchanged':True}
        with patch('xhs_local.platform.existing_permission'),patch('xhs_local.platform.subprocess.run',return_value=subprocess.CompletedProcess([],0,json.dumps(result),'')) as run:
            native_call('upload',{'window_id':'10','tab_id':'1'},assets=[{'base64':'A'*300000}])
            args,kw=run.call_args
            self.assertEqual(args[0],['/usr/bin/osascript','-l','JavaScript','-'])
            self.assertIn('A'*300000,kw['input'])

    def test_publication_and_arbitrary_script_actions_are_rejected(self):
        with patch('xhs_local.platform.existing_permission') as permission:
            for action in ('publish','schedule','evaluate','delete','private_publish'):
                with self.assertRaises(XHSError):native_call(action,{})
            permission.assert_not_called()

    def test_next_article_gets_separate_editor_and_preserves_previous_draft(self):
        first=self.platform.sync(self.local['manuscript_id'],1)
        original=copy.deepcopy(self.browser.cards[first['native_draft_id']])
        with DraftStore(self.root/'manuscripts') as s:
            second=s.create({'title':'另一篇','content':'新内容','images':[str(self.image)]})
        r=self.platform.sync(second['manuscript_id'],1)
        self.assertNotEqual(r['native_draft_id'],first['native_draft_id'])
        self.assertEqual(self.browser.cards[first['native_draft_id']],original)
        self.assertEqual(self.browser.uploads,2)

    def test_reopen_waits_for_saved_id_while_list_temporarily_reports_zero(self):
        mid=self.local['manuscript_id'];first=self.platform.sync(mid,1)
        original=self.platform.runner;remaining=[0]
        def delayed(action,binding,**p):
            result=original(action,binding,**p)
            if action=='category':remaining[0]=3
            if action=='inspect' and result.get('categories') and remaining[0]:
                remaining[0]-=1;result={**result,'categories':['图文笔记(0)'],'cards':[]}
            return result
        self.platform.runner=delayed
        second=self.platform.reopen(mid)
        self.assertEqual(second['native_draft_id'],first['native_draft_id'])
        self.assertEqual(self.browser.uploads,1)

    def test_source_editor_is_kept_until_independent_list_confirms_save(self):
        original=self.platform.runner;delay=[0];saving=[False]
        def delayed(action,binding,**p):
            result=original(action,binding,**p)
            if action=='save':saving[0]=True
            if action=='category' and saving[0]:delay[0]=3
            if action=='inspect' and result.get('categories') and delay[0]:
                self.assertTrue(any(t['mode']=='editor' for t in self.browser.tabs.values()))
                delay[0]-=1;result={**result,'cards':[]}
            return result
        self.platform.runner=delayed
        r=self.platform.sync(self.local['manuscript_id'],1)
        self.assertTrue(r['platform_saved'])
        self.assertEqual(sum(t['mode']=='editor' for t in self.browser.tabs.values()),1)

    @unittest.skipUnless(shutil.which('node'),'Node unavailable')
    def test_editor_readback_uses_authored_paragraphs_instead_of_visual_spacing(self):
        source=Path(__file__).parents[1]/'xhs_local/platform_page.js'
        fixture=r'''
global.Node={TEXT_NODE:3,ELEMENT_NODE:1};
const t=s=>({nodeType:3,textContent:s});
const p=(...children)=>({nodeType:1,tagName:'P',childNodes:children});
const br={nodeType:1,tagName:'BR',classList:{contains:()=>true}};
const title={placeholder:'标题',value:'标题',getBoundingClientRect:()=>({width:20,height:10})};
const editor={innerText:'a\n\n\n\n\nb',children:[p(t('a')),p(br),p(t('b'))],getBoundingClientRect:()=>({width:20,height:10})};
global.getComputedStyle=()=>({display:'block',visibility:'visible',opacity:'1'});
global.location={origin:'https://creator.xiaohongshu.com',pathname:'/publish/publish',href:'https://creator.xiaohongshu.com/publish/publish'};
global.document={title:'创作平台',body:{innerText:''},readyState:'complete',querySelector:()=>null,querySelectorAll:q=>q==='input,textarea'?[title]:q==='[contenteditable=true]'?[editor]:[]};
process.stdout.write(JSON.stringify(platformPage({action:'inspect'}).content));
'''
        r=subprocess.run([shutil.which('node'),'-e',source.read_text()+fixture],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(json.loads(r.stdout),'a\n\nb')

    @unittest.skipUnless(shutil.which('node'),'Node unavailable')
    def test_image_mode_ignores_rendered_duplicate_far_outside_viewport(self):
        source=Path(__file__).parents[1]/'xhs_local/platform_page.js'
        fixture=r'''
const clicked=[];
const tab=x=>({innerText:'上传图文',parentElement:null,getBoundingClientRect:()=>({x,y:81,width:96,height:40}),click:()=>clicked.push(x)});
const tabs=[tab(-9758),tab(369)];
global.innerWidth=1440;global.innerHeight=1100;
global.getComputedStyle=()=>({display:'flex',visibility:'visible',opacity:'1'});
global.location={origin:'https://creator.xiaohongshu.com',pathname:'/publish/publish'};
global.document={title:'创作平台',body:{innerText:'上传视频'},querySelectorAll:q=>q==='.creator-tab'?tabs:[]};
platformPage({action:'image_mode'});process.stdout.write(JSON.stringify(clicked));
'''
        r=subprocess.run([shutil.which('node'),'-e',source.read_text()+fixture],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads(r.stdout),[369])


if __name__=='__main__':unittest.main()
