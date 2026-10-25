"""Narrow, explicitly authorized native longform test; no publication or file actions.

The nine existing MCP tools remain read-only/local. This diagnostic accepts only
its journal's marked test text and uses the official UI to save. It never writes
browser storage directly and never exposes arbitrary JavaScript or selectors.
"""
import datetime
import json
import subprocess
from pathlib import Path
from .errors import XHSError
from .native_chrome import existing_permission

ACTIONS = frozenset({'inspect', 'longform', 'new', 'set_a', 'set_b', 'save_a', 'save_b', 'drafts', 'longform_drafts', 'inspect_test_card', 'reopen_test', 'reload_saved_list'})

JS = r'''ObjC.import('AppKit');
function run(argv){
 const p=JSON.parse(argv[0]), c=Application('com.google.Chrome');
 const front=()=>ObjC.unwrap($.NSWorkspace.sharedWorkspace.frontmostApplication.bundleIdentifier);
 let x=null;for(const w of c.windows())for(const t of w.tabs())if(String(t.id())===p.tab)x={w,t};
 if(!x)throw Error('test_tab_missing');
 if(!/^https:\/\/creator\.xiaohongshu\.com\/publish\/publish(?:[?#]|$)/.test(x.t.url()||''))throw Error('official_editor_not_open');
 const before={front:front(),active:x.w.activeTabIndex()};
 const script='JSON.stringify((()=>{try{return ('+PAGE.toString()+')('+JSON.stringify(p)+')}catch(e){return {stopped:true,error:String(e.message||e)}}})())';
 const data=JSON.parse(x.t.execute({javascript:script}));
 if(p.action==='reload_saved_list'&&data?.safe_to_reload)x.t.reload();
 const after={front:front(),active:x.w.activeTabIndex()};
 return JSON.stringify({data,before,after,foreground_unchanged:before.front===after.front,active_tab_unchanged:before.active===after.active,url:x.t.url()});
}
function PAGE(p){
 const shown=e=>{if(!e)return false;const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>0&&r.height>0&&r.x+r.width>0&&r.y+r.height>0&&r.x<innerWidth&&r.y<innerHeight&&s.visibility==='visible'&&Number(s.opacity)>0.1;};
 const hit=e=>{const r=e.getBoundingClientRect();const h=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);return h&&e.contains(h)?h:null;};
 const text=e=>(e.innerText||'').trim();
 const pageText=(document.body?.innerText||'').slice(0,5000);
 if(document.title==='安全限制'||/IP存在风险|操作过于频繁|请完成安全验证|访问异常/.test(pageText))throw Error('site_access_blocked');
 if(location.pathname.includes('/login'))throw Error('official_login_required');
 const titles=[...document.querySelectorAll('textarea[placeholder="输入标题"]')].filter(shown);
 const editors=[...document.querySelectorAll('[contenteditable="true"]')].filter(shown);
 const title=titles.length===1?titles[0].value:null;
 const rawBody=editors.length===1?editors[0].innerText:null;
 const blocks=editors.length===1?[...editors[0].children]:[];
 // Observed native longform DOM uses one P per logical test line. Keep raw
 // innerText separately: it inserts a blank line between those paragraphs.
 const body=blocks.length&&blocks.every(e=>e.tagName==='P')?blocks.map(e=>e.innerText).join('\n'):rawBody;
 function fields(){if(titles.length!==1||editors.length!==1)throw Error('expected_unique_longform_fields');if(document.querySelectorAll('input[type="file"]').length)throw Error('unexpected_attachment_input');}
 function same(version){fields();if(title!==p.title||body!==p[version])throw Error('test_content_mismatch');}
 function clickUnique(selector,label){const matches=[...document.querySelectorAll(selector)].filter(shown).filter(e=>text(e)===label&&hit(e));if(matches.length!==1)throw Error('expected_unique_control:'+label+':'+matches.length);if(matches[0].disabled)throw Error('control_disabled');hit(matches[0]).click();return {clicked:label};}
 function empty(){if([...document.querySelectorAll('textarea,input[type="text"],[contenteditable="true"]')].some(e=>(e.value||e.innerText||'').trim()))throw Error('existing_text_not_empty');}
 const snapshot=()=>({path:location.pathname,query:location.search,editor_present:titles.length===1&&editors.length===1,title:title===p.title?title:null,body:title===p.title?body:null,raw_body:title===p.title?rawBody:null,body_blocks:title===p.title?blocks.map(e=>({tag:e.tagName,text:e.innerText})):null,other_text_present:!!((title?.trim()&&title!==p.title)||(body?.trim()&&title!==p.title)),file_inputs:document.querySelectorAll('input[type="file"]').length,fields:[...document.querySelectorAll('textarea,[contenteditable="true"]')].filter(shown).map(e=>({tag:e.tagName,placeholder:e.getAttribute('placeholder'),class:e.className})),draft_labels:[...document.querySelectorAll('.header-draft')].filter(shown).map(text),controls:[...document.querySelectorAll('button,[role="button"]')].filter(shown).map(e=>({text:text(e).slice(0,80),class:e.className,disabled:!!e.disabled})).filter(e=>e.text).slice(0,30),draft_ui:[...document.querySelectorAll('span,p,div')].filter(shown).filter(e=>!e.children.length).map(text).filter(t=>t.length<200&&/草稿|本地|浏览器|自动保存|暂存|还没有|暂无/.test(t)).slice(0,25)});
 if(p.action==='inspect')return snapshot();
 if(p.action==='reload_saved_list'){if(titles.length||editors.length)throw Error('save_and_leave_before_reload');if(!p.native_id)throw Error('native_id_required_before_reload');return {safe_to_reload:true,scope:'only_this_task_tab'};}
 if(p.action==='longform'){empty();return clickUnique('div.creator-tab','写长文');}
 if(p.action==='new'){empty();return clickUnique('button.new-btn','新的创作');}
 if(p.action==='set_a'||p.action==='set_b'){
  fields();if(p.action==='set_a'){empty();}else same('A');
  const value=p.action==='set_a'?p.A:p.B;
  editors[0].focus();const selection=getSelection(),range=document.createRange();range.selectNodeContents(editors[0]);selection.removeAllRanges();selection.addRange(range);
  const inserted=document.execCommand('insertText',false,value);if(!inserted)throw Error('native_editor_insert_failed');
  const setter=Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set;setter.call(titles[0],p.title);titles[0].dispatchEvent(new Event('input',{bubbles:true}));
  return {text_inserted:true,revision:p.action==='set_a'?'A':'B',editor_insert_reported:inserted};
 }
 if(p.action==='save_a'||p.action==='save_b'){same(p.action==='save_a'?'A':'B');return clickUnique('button','暂存离开');}
 if(p.action==='drafts'){if(titles.length||editors.length)throw Error('leave_editor_before_draft_list');const nodes=[...document.querySelectorAll('.header-draft')].filter(shown).filter(e=>hit(e));if(nodes.length!==1)throw Error('expected_one_draft_entry');const label=text(nodes[0]);hit(nodes[0]).click();return {draft_entry_clicked:true,label};}
 if(p.action==='longform_drafts'){if(!p.native_id)throw Error('known_test_id_required');return clickUnique('.d-drawer .draft-tabs .tab-item','长文笔记(1)');}
 if(p.action==='inspect_test_card'||p.action==='reopen_test'){
  if(titles.length||editors.length)throw Error('draft_list_required');
  // Only this exact marked test title may be selected; never inspect other drafts.
  const titleMatches=[...document.querySelectorAll('.draft-title-text')].filter(shown).filter(e=>text(e)===p.title).filter(e=>hit(e));
  const matches=titleMatches;
  if(matches.length!==1){
   const candidates=[...document.querySelectorAll('div,span,p,h1,h2,h3,a')].filter(shown).filter(e=>text(e)===p.title).map(e=>{const r=e.getBoundingClientRect();return {tag:e.tagName,class:e.className,child_count:e.children.length,rect:{x:r.x,y:r.y,width:r.width,height:r.height},hit:!!hit(e),parent:e.parentElement.className};});
   if(p.action==='inspect_test_card')return {matching_test_titles:matches.length,candidates};
   throw Error('expected_one_matching_test_draft:'+matches.length);
  }
  const e=matches[0];const ancestors=[];let a=e;
  const card=e.closest('.draft-item');if(!card)throw Error('test_draft_card_missing');
  const nativeId=card.getAttribute('data-draft-id');if(!nativeId)throw Error('native_draft_id_missing');
  if(p.native_id&&p.native_id!==nativeId)throw Error('native_draft_id_changed');
  for(let i=0;i<5&&a;i++,a=a.parentElement)ancestors.push({tag:a.tagName,class:a.className,render_key:a.__vnode?.key??a.__vueParentComponent?.vnode?.key??null,attributes:[...a.attributes].filter(v=>/^(?:data-(?:id|draft-id|note-id|key)|href|id)$/.test(v.name)).map(v=>({name:v.name,value:v.value})),text:text(a).length<400?text(a):null});
  if(p.action==='inspect_test_card')return {matching_test_titles:matches.length,native_draft_id:nativeId,ancestors,snapshot:snapshot()};
  const edit=[...card.querySelectorAll('button,[role="button"],div,span')].filter(shown).filter(e=>text(e)==='编辑').filter(e=>![...e.children].some(child=>text(child)==='编辑')).filter(e=>hit(e));
  if(edit.length!==1)throw Error('expected_one_test_edit_control:'+edit.length);
  hit(edit[0]).click();return {reopen_clicked:true,control:'编辑',matching_test_titles:1,native_draft_id:nativeId};
 }
 throw Error('native_test_action_not_allowed');
}
'''


def validate(journal, action):
    if action not in ACTIONS:
        raise XHSError('native_test_action_not_allowed', '只允许固定测试草稿操作')
    planned=journal['planned_test']
    if not planned['title'].startswith('功能验证草稿，请勿发布 ') or journal['run_id'] not in planned['A'] or journal['run_id'] not in planned['B']:
        raise XHSError('native_test_marker_required','只允许已标记的非敏感功能测试文字')
    if planned['A']==planned['B']:
        raise XHSError('native_test_revisions_required','测试必须有两个不同版本')
    if action in {'new','set_a'} and planned.get('native_draft_id'):
        raise XHSError('native_test_already_created','已有测试草稿ID；使用原条目，不再新建或重写A')
    if action in {'set_b','reopen_test','longform_drafts','reload_saved_list'} and not planned.get('native_draft_id'):
        raise XHSError('native_test_id_required','先从测试卡片核对原生ID')
    events=journal.get('native_events',[])
    if events and events[-1].get('status')=='outcome_unknown' and action not in {'inspect','inspect_test_card'}:
        raise XHSError('native_test_read_before_retry','上次结果不明，必须先只读确认')


def call(journal_path, action, timeout=8):
    path=Path(journal_path)
    journal=json.loads(path.read_text())
    validate(journal,action)
    existing_permission()
    payload={'action':action,'tab':journal['work_tab_id'],'native_id':journal['planned_test'].get('native_draft_id'),**{k:journal['planned_test'][k] for k in ['title','A','B']}}
    started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    event={'action':action,'started_at_utc':started,'status':'requested'}
    journal.setdefault('native_events',[]).append(event)
    path.write_text(json.dumps(journal,ensure_ascii=False,indent=2)+'\n')
    path.chmod(0o600)
    try:
        result=subprocess.run(['/usr/bin/osascript','-l','JavaScript','-e',JS,json.dumps(payload,ensure_ascii=False)],capture_output=True,text=True,timeout=timeout)
        if result.returncode:
            raise XHSError('native_test_stopped',result.stderr.strip()[:300])
        data=json.loads(result.stdout)
        event.update(status='completed',result=data)
        if not isinstance(data.get('data'),dict):
            raise XHSError('native_result_missing','页面未返回操作数据；先只读确认状态，不重复写入')
        if data['data'].get('stopped'):
            raise XHSError('native_test_stopped',data['data'].get('error','页面保护已停止操作'))
        if action=='inspect_test_card' and data['data'].get('native_draft_id'):
            journal['planned_test']['native_draft_id']=data['data']['native_draft_id']
        if not data.get('foreground_unchanged') or not data.get('active_tab_unchanged'):
            raise XHSError('native_activity_changed','活动上下文发生变化，停止后续操作')
    except subprocess.TimeoutExpired:
        event.update(status='outcome_unknown',error='native_timeout')
        raise XHSError('native_timeout','原生调用超时；先只读检查，不重复写入') from None
    except Exception as exc:
        event.update(status='stopped',error=str(exc))
        raise
    finally:
        event['finished_at_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        path.write_text(json.dumps(journal,ensure_ascii=False,indent=2)+'\n')
    return data
