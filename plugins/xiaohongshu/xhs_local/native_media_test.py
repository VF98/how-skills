"""One-time, hash-pinned synthetic media draft diagnostic; never publishes."""
import base64,datetime,hashlib,json,pathlib,subprocess
from .errors import XHSError
from .native_chrome import existing_permission
ROOT=pathlib.Path(__file__).resolve().parents[1]
JOURNAL=ROOT/'evidence/native-media-workflow.json'
APPROVED_RUN='synthetic-media-fixture'
APPROVED_HASHES={'image':'45a72bdf1b04aab093b4e39dae922a17056675a6c1113557ba8e035d4983616a','video':'d7d6a51a8523025ef3e8b2b89c251793a4347aebf9c188beb621dac1c6f24bbc'}
ACTIONS={'state','upload','set_text','save','preview','drafts','category','card','reopen','dismiss_image_hint','inspect_actions','preview_snapshot','prepare_video_preview','pause_video_preview'}
JS=r'''ObjC.import('AppKit');
function run(argv){const p=JSON.parse(argv[0]),c=Application('com.google.Chrome');let x=null;for(const w of c.windows())for(const t of w.tabs())if(String(t.id())===p.tab)x={w,t};if(!x)throw Error('media_tab_missing');if(!/^https:\/\/creator\.xiaohongshu\.com\/publish\/publish(?:[?#]|$)/.test(x.t.url()||''))throw Error('official_editor_required');const front=()=>ObjC.unwrap($.NSWorkspace.sharedWorkspace.frontmostApplication.bundleIdentifier);const before={front:front(),active:x.w.activeTabIndex()};const script='JSON.stringify((()=>{try{return ('+PAGE.toString()+')('+JSON.stringify(p)+')}catch(e){return {stopped:true,error:String(e.message||e)}}})())';const data=JSON.parse(x.t.execute({javascript:script}));return JSON.stringify({data,before,after:{front:front(),active:x.w.activeTabIndex()},foreground_unchanged:before.front===front(),active_tab_unchanged:before.active===x.w.activeTabIndex(),url:x.t.url()});}
function PAGE(p){
 const rendered=e=>{if(!e)return false;const r=e.getBoundingClientRect();if(!r.width||!r.height)return false;for(let a=e;a;a=a.parentElement){const s=getComputedStyle(a);if(s.visibility==='hidden'||s.display==='none'||Number(s.opacity)<0.1)return false;}return true;};
 const shown=e=>{if(!rendered(e))return false;const r=e.getBoundingClientRect();return r.x+r.width>0&&r.y+r.height>0&&r.x<innerWidth&&r.y<innerHeight;};
 const txt=e=>(e.innerText||'').trim();const hit=e=>{const r=e.getBoundingClientRect(),h=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);return h&&e.contains(h)?h:null;};
 const body=(document.body?.innerText||'').slice(0,6000);if(document.title==='安全限制'||/IP存在风险|操作过于频繁|请完成安全验证|访问异常/.test(body))throw Error('site_access_blocked');if(location.pathname.includes('/login'))throw Error('official_login_required');
 const titles=[...document.querySelectorAll('input[type=text],input:not([type]),textarea')].filter(rendered).filter(e=>/标题/.test(e.getAttribute('placeholder')||''));const editors=[...document.querySelectorAll('[contenteditable=true]')].filter(rendered);const title=titles.length===1?titles[0].value:null;const content=editors.length===1?txt(editors[0]):null;
 function control(labels,scope=document){let m=[...scope.querySelectorAll('button,[role=button]')].filter(rendered).filter(e=>labels.includes(txt(e)));if(!m.length)m=[...scope.querySelectorAll('div,span')].filter(rendered).filter(e=>labels.includes(txt(e))&&!e.children.length);if(m.length!==1)throw Error('unique_safe_control_required:'+labels.join('|')+':'+m.length);if(m[0].disabled)throw Error('control_disabled');m[0].scrollIntoView({block:'center'});const target=hit(m[0]);if(!target)throw Error('control_obscured');target.click();return {clicked:txt(m[0])};}
 const fileInputs=[...document.querySelectorAll('input[type=file]')];
 const state=()=>({path:location.pathname,query:location.search,editor_present:titles.length===1&&editors.length===1,title:titles.length===1&&(title===p.title||title===p.file_name||title===p.file_stem)?title:null,content:title===p.title?content:null,other_text_present:!!(title&&![p.title,p.file_name,p.file_stem].includes(title))||!!(content&&content!==p.content),fields:[...document.querySelectorAll('input,textarea,[contenteditable=true]')].filter(e=>e.type!=='password'&&e.type!=='tel').map(e=>({tag:e.tagName,type:e.type||null,placeholder:e.getAttribute('placeholder'),class:e.className,visible:shown(e),accept:e.accept||null})),controls:[...document.querySelectorAll('button,[role=button],.header-draft')].filter(shown).map(e=>({text:txt(e).slice(0,80),disabled:!!e.disabled,class:e.className})).filter(e=>e.text).slice(0,40),ui:[...new Set([...document.querySelectorAll('span,p,div')].filter(shown).filter(e=>!e.children.length).map(txt).filter(t=>t&&t.length<160&&/上传|处理中|转码|完成|成功|失败|草稿|暂存|预览|封面|视频|图片|图文|本地|浏览器/.test(t)))].slice(0,45),images:[...document.querySelectorAll('img')].filter(e=>e.naturalWidth>=300&&shown(e)).map(e=>({width:e.naturalWidth,height:e.naturalHeight,source_type:e.currentSrc.startsWith('blob:')?'blob':e.currentSrc.startsWith('data:')?'data':'remote',origin:(()=>{try{return new URL(e.currentSrc).origin}catch{return null}})()})).slice(0,10),videos:[...document.querySelectorAll('video')].map(e=>({duration:Number.isFinite(e.duration)?e.duration:null,width:e.videoWidth,height:e.videoHeight,ready_state:e.readyState,network_state:e.networkState,error_code:e.error?.code??null,error_message:e.error?.message??null,preload:e.preload,current_time:e.currentTime,paused:e.paused,visible:shown(e),source_type:e.currentSrc.startsWith('blob:')?'blob':e.currentSrc?'remote':'empty'})),preview_regions:[...document.querySelectorAll('[class*=preview]')].filter(shown).map(e=>({tag:e.tagName,class:e.className})).slice(0,20)});
 if(p.action==='state')return state();
 if(p.action==='pause_video_preview'){if(p.kind!=='video'||title!==p.title||content!==p.content)throw Error('owned_video_preview_required');const v=[...document.querySelectorAll('.publish-page-preview video')];for(const e of v)e.pause();return {test_preview_paused:true};}
 if(p.action==='prepare_video_preview'){if(p.kind!=='video'||title!==p.title||content!==p.content)throw Error('owned_video_preview_required');const v=[...document.querySelectorAll('.publish-page-preview video')].filter(shown);if(v.length!==1)throw Error('unique_visible_video_preview_required');v[0].preload='auto';v[0].muted=true;v[0].load();const play=v[0].play();if(play&&play.catch)play.catch(()=>{});return {preview_play_requested:true,muted:true,can_play_mp4:v[0].canPlayType('video/mp4')};}
 if(p.action==='inspect_actions')return {labels:[...document.querySelectorAll('button,[role=button],a,div,span')].filter(rendered).filter(e=>!e.children.length).filter(e=>/草稿|暂存|保存|预览|发布/.test(txt(e))&&txt(e).length<80).map(e=>({tag:e.tagName,text:txt(e),class:e.className,visible:shown(e)})).slice(0,30)};
 if(p.action==='preview_snapshot'){if(title!==p.title||content!==p.content)throw Error('test_text_mismatch_before_preview_read');const region=document.querySelector('.publish-page-preview');if(!region)throw Error('preview_region_missing');return {native_preview_present:rendered(region),title_matches:txt(region).includes(p.title),body_matches:txt(region).includes(p.content),preview_images:[...region.querySelectorAll('img')].map(e=>({width:e.naturalWidth,height:e.naturalHeight,rendered:rendered(e),complete:e.complete})),preview_videos:[...region.querySelectorAll('video')].map(e=>({duration:e.duration,width:e.videoWidth,height:e.videoHeight,ready_state:e.readyState})),current_editor_matches:true};}
 if(p.action==='dismiss_image_hint'){if(p.kind!=='image'||!body.includes('图片可以编辑啦'))throw Error('expected_image_feature_hint');return control(['我知道了']);}
 if(p.action==='upload'){
  if(titles.length||editors.length)throw Error('blank_upload_landing_required');if(fileInputs.length!==1||fileInputs[0].files.length)throw Error('one_empty_file_input_required');const ext=p.kind==='image'?'.png':'.mp4';if(!fileInputs[0].accept.includes(ext))throw Error('wrong_media_mode');if(!p.file_name.startsWith(p.run_id)||p.file_bytes>100000)throw Error('test_asset_bounds_required');
  const bytes=Uint8Array.from(atob(p.base64),c=>c.charCodeAt(0));if(bytes.length!==p.file_bytes)throw Error('test_asset_length_mismatch');const f=new File([bytes],p.file_name,{type:p.mime});const dt=new DataTransfer();dt.items.add(f);fileInputs[0].files=dt.files;fileInputs[0].dispatchEvent(new Event('change',{bubbles:true}));return {file_selected:true,name:p.file_name,bytes:f.size,type:f.type};
 }
 if(p.action==='set_text'){
  if(titles.length!==1||editors.length!==1)throw Error('unique_media_fields_required');if(title&&![p.title,p.file_name,p.file_stem].includes(title))throw Error('existing_title_stop');if(content&&content!==p.content)throw Error('existing_body_stop');
  const proto=titles[0].tagName==='INPUT'?HTMLInputElement.prototype:HTMLTextAreaElement.prototype;Object.getOwnPropertyDescriptor(proto,'value').set.call(titles[0],p.title);titles[0].dispatchEvent(new Event('input',{bubbles:true}));
  if(content!==p.content){editors[0].focus();const r=document.createRange();r.selectNodeContents(editors[0]);const s=getSelection();s.removeAllRanges();s.addRange(r);if(!document.execCommand('insertText',false,p.content))throw Error('media_text_insert_failed');}return {test_text_entered:true};
 }
 if(p.action==='save'){if(title!==p.title||content!==p.content)throw Error('test_text_mismatch_before_save');return control(['暂存离开','保存草稿','存草稿','暂存草稿']);}
 if(p.action==='preview'){if(title!==p.title||content!==p.content)throw Error('test_text_mismatch_before_preview');return control(['预览','预览笔记']);}
 if(p.action==='drafts'){if(titles.length||editors.length)throw Error('leave_editor_first');return control([...document.querySelectorAll('.header-draft')].map(txt));}
 if(p.action==='category'){const label=p.kind==='image'?'图文笔记':'视频笔记';const m=[...document.querySelectorAll('.d-drawer .draft-tabs .tab-item')].filter(rendered).filter(e=>txt(e).startsWith(label+'('));if(m.length!==1)throw Error('unique_category_required');m[0].click();return {clicked:txt(m[0]),route:'background_dom_no_focus_change'};}
 if(p.action==='card'||p.action==='reopen'){
  if(titles.length||editors.length)throw Error('list_required');const m=[...document.querySelectorAll('.draft-title-text')].filter(rendered).filter(e=>txt(e)===p.title);if(m.length!==1)return {matching_test_cards:m.length};const card=m[0].closest('.draft-item');const id=card?.getAttribute('data-draft-id');if(!id)throw Error('native_draft_id_missing');if(p.native_id&&p.native_id!==id)throw Error('test_id_changed');if(p.action==='reopen'){const edit=[...card.querySelectorAll('button,div,span')].filter(rendered).filter(e=>txt(e)==='编辑'&&!e.children.length);if(edit.length!==1)throw Error('unique_owned_edit_control_required');edit[0].click();return {native_draft_id:id,clicked:'编辑',route:'background_dom_no_focus_change'};}return {native_draft_id:id,title:txt(m[0]),matching_test_cards:1,card_text:txt(card).slice(0,300),draft_labels:[...document.querySelectorAll('.header-draft')].map(txt)};
 }
 throw Error('media_action_not_allowed');
}
'''

def call(kind,action):
    if kind not in {'image','video'} or action not in ACTIONS:raise XHSError('media_action_not_allowed','只允许这两份合成素材的固定草稿动作')
    j=json.loads(JOURNAL.read_text());item=j['items'][kind];a=item['asset']
    if j['run_id']!=APPROVED_RUN or a['sha256']!=APPROVED_HASHES[kind]:raise XHSError('media_scope_mismatch','此次授权只覆盖固定两份合成测试文件')
    if not item['tab_id']:raise XHSError('media_tab_missing','先绑定独立媒体测试页')
    payload={'action':action,'kind':kind,'tab':item['tab_id'],'run_id':j['run_id'],'title':item['title'],'content':item['body'],'native_id':item['native_draft_id'],'file_name':a['name'],'file_stem':pathlib.Path(a['name']).stem}
    if action=='upload':
        if item.get('native_draft_id') or item.get('imported_to_editor') or item.get('uploaded'):
            raise XHSError('media_already_imported','已有导入或原生草稿记录，禁止重新上传')
        if any(e['action']=='upload' and e['kind']==kind for e in j.get('events',[])):raise XHSError('media_upload_already_attempted','上传已尝试；必须只读核对，不重复上传')
        path=pathlib.Path(a['path']).resolve();expected=(ROOT/'test-assets'/a['name']).resolve()
        if path!=expected or hashlib.sha256(path.read_bytes()).hexdigest()!=APPROVED_HASHES[kind]:raise XHSError('media_asset_mismatch','文件范围或内容哈希不符')
        data=path.read_bytes();payload.update(base64=base64.b64encode(data).decode(),file_bytes=len(data),mime=a['mime'])
    existing_permission();event={'kind':kind,'action':action,'started_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'requested'};j.setdefault('events',[]).append(event);JOURNAL.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
    try:
        r=subprocess.run(['/usr/bin/osascript','-l','JavaScript','-e',JS,json.dumps(payload,ensure_ascii=False)],capture_output=True,text=True,timeout=8)
        if r.returncode:raise XHSError('media_native_stopped',r.stderr.strip()[:250])
        result=json.loads(r.stdout);event['result']=result
        if not isinstance(result.get('data'),dict) or result['data'].get('stopped'):raise XHSError('media_ui_stopped',str(result.get('data'))[:250])
        if not result['foreground_unchanged'] or not result['active_tab_unchanged']:raise XHSError('media_activity_changed','活动上下文改变，停止')
        event['status']='completed'
        if action=='card' and result['data'].get('native_draft_id'):item['native_draft_id']=result['data']['native_draft_id']
        return result
    except subprocess.TimeoutExpired:
        event.update(status='outcome_unknown',error='native_timeout');raise XHSError('native_timeout','先只读确认，不重复上传或写入') from None
    except Exception as e:event.update(status='stopped',error=str(e));raise
    finally:
        event['finished_at_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();JOURNAL.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
