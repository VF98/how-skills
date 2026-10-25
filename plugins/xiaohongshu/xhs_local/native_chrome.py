"""Use approved Chrome Apple Events on an existing inactive official tab.

No profile access, debugging port, new window, extension, activation, attachment
upload or arbitrary script tool. A rejection stops this route; no fallback.
"""
import ctypes
import json
from pathlib import Path
import platform
import subprocess
import time
from urllib.parse import urlsplit

from .drafts import atomic_private_write
from .errors import XHSError
from . import research

ACCOUNT_JS = r"""(() => {
 const visible=e=>!!e&&e.getBoundingClientRect().width>0&&e.getBoundingClientRect().height>0;
 const area=document.querySelector('.main-container .user');
 const channel=document.querySelector('.main-container .user .link-wrapper .channel');
 let id=null;
 if(area)for(const a of area.querySelectorAll('a[href]')){
   const m=(a.getAttribute('href')||'').match(/\/user\/profile\/([a-f0-9]{24})/);if(m){id=m[1];break;}}
 return {own_channel_visible:visible(channel),public_account_id:id};
})()"""

FORM_JS = r"""(() => {
 const visible=e=>!!e&&e.getBoundingClientRect().width>0&&e.getBoundingClientRect().height>0;
 return {origin:location.origin,path:location.pathname,title:document.title,
   login_visible:location.pathname.includes('/login'),
   headings:[...document.querySelectorAll('h1,h2,[role="tab"]')].filter(visible).map(e=>e.innerText.trim()).filter(Boolean).slice(0,20),
   controls:[...document.querySelectorAll('button,[role="button"],a,.creator-tab,.tab-item')].slice(0,120).filter(visible)
      .map(e=>({text:(e.innerText||e.getAttribute('aria-label')||'').trim().slice(0,80),
        path:e.tagName==='A'&&e.origin===location.origin?new URL(e.href).pathname:null}))
      .filter(x=>x.text&&/草稿|暂存|保存|上传|图文|视频|长文|创作|笔记|发布|返回|取消|下一步/.test(x.text)).slice(0,50),
   inputs:[...document.querySelectorAll('input,textarea,[contenteditable="true"]')]
      .map(e=>({tag:e.tagName,type:e.getAttribute('type'),placeholder:e.getAttribute('placeholder'),
        accept:e.getAttribute('accept'),required:!!e.required,visible:visible(e),contenteditable:e.getAttribute('contenteditable')}))
      .filter(x=>x.type!=='password'&&x.type!=='tel'),
   attachment_required_text:/上传图片|拖拽图片|点击上传|上传图文|至少.*图片/.test(document.body?.innerText||''),
   existing_text_present:[...document.querySelectorAll('input[type="text"],textarea,[contenteditable="true"]')].some(e=>!!(e.value||e.innerText||'').trim()),
   body_excerpt:null};
})()"""

SEARCH_DOM_JS = r"""(() => {
 const visible=e=>!!e&&e.getBoundingClientRect().width>0&&e.getBoundingClientRect().height>0;
 const links=[...document.querySelectorAll('a[href]')].filter(a=>/^https:\/\/www\.xiaohongshu\.com\/(?:explore|search_result|discovery\/item)\/[0-9a-f]{24}/.test(a.href));
 const cards=[...document.querySelectorAll('section.note-item,.note-item')].filter(visible);
 return {title:document.title,url:location.href,initial_state_present:!!window.__INITIAL_STATE__,
   search_state_field_names:Object.keys(window.__INITIAL_STATE__?.search||{}).slice(0,20),
   visible_note_card_count:cards.length,
   sample_cards:cards.slice(0,3).map(e=>({title:e.querySelector('.title')?.innerText||null,
      author:e.querySelector('.author .name,.author-wrapper .name')?.innerText||null,
      links:[...e.querySelectorAll('a[href]')].filter(a=>/^https:\/\/www\.xiaohongshu\.com\/(?:explore|search_result|discovery\/item)\/[0-9a-f]{24}/.test(a.href)).slice(0,2).map(a=>a.href)})),
   sample_note_links:[...new Set(links.map(a=>a.href))].slice(0,3),
   login_prompt_visible:[...document.querySelectorAll('.login-container,.login-modal')].some(visible)};
})()"""

READERS = {"account": ACCOUNT_JS, "snapshot": research.SNAPSHOT_JS, "search_dom": SEARCH_DOM_JS,
           "creator": research.CREATOR_INSPECT_JS, "creator_form": FORM_JS}

JXA = r"""
ObjC.import('AppKit');
function run(argv){
 const p=JSON.parse(argv[0]);
 const apps=$.NSWorkspace.sharedWorkspace.runningApplications;let running=false;
 for(let i=0;i<apps.count;i++)if(ObjC.unwrap(apps.objectAtIndex(i).bundleIdentifier)==='com.google.Chrome')running=true;
 if(!running)return JSON.stringify({ok:false,error:'native_chrome_not_running'});
 const c=Application('com.google.Chrome');
 function fingerprint(){return JSON.stringify({front:ObjC.unwrap($.NSWorkspace.sharedWorkspace.frontmostApplication.bundleIdentifier),
   windows:c.windows().map(w=>({id:String(w.id()),active:w.activeTabIndex()}))});}
 const before=fingerprint();
 function find(id){for(const w of c.windows())for(const t of w.tabs())if(String(t.id())===String(id))return {w,t};
   throw Error('native_tab_missing');}
 function home(u){return /^https:\/\/www\.xiaohongshu\.com\/(?:explore\/?|\/?)(?:[?#]|$)/.test(u||'');}
 function idle(u){return home(u)||/^https:\/\/creator\.xiaohongshu\.com\/(?:new\/(?:home|encyclopedia)\/?)?(?:[?#]|$)/.test(u||'');}
 function inactive(x){if(String(x.w.tabs()[x.w.activeTabIndex()-1].id())===String(x.t.id()))throw Error('native_work_tab_active');}
 function read(x,reader){
   const u=x.t.url()||'';
   if(!/^https:\/\/(www|creator)\.xiaohongshu\.com\//.test(u))throw Error('native_unexpected_origin');
   if(!(reader in READERS))throw Error('native_reader_not_allowed');
   const risk=JSON.parse(x.t.execute({javascript:"JSON.stringify((()=>{const t=(document.body?.textContent||'').slice(0,5000);return {blocked:document.title==='安全限制'||t.includes('IP存在风险')||t.includes('操作过于频繁'),code:t.includes('300012')?'300012':null}})())"}));
   if(risk.blocked)throw Error('site_access_blocked'+(risk.code?':'+risk.code:''));
   return JSON.parse(x.t.execute({javascript:'JSON.stringify('+READERS[reader]+')'}));
 }
 let out;
 try{
   const anchor=find(p.binding.anchor_tab_id);const work=find(p.binding.work_tab_id);
   if(String(anchor.w.id())!==String(work.w.id()))throw Error('native_profile_window_mismatch');
   if(p.binding.window_id&&String(anchor.w.id())!==String(p.binding.window_id))throw Error('native_window_changed');
   if(String(anchor.t.id())===String(work.t.id()))throw Error('native_work_tab_is_anchor');
   if(p.action==='bind'||p.action==='lease'){
     if(!home(anchor.t.url())||!idle(work.t.url()))throw Error('native_idle_home_required');
     inactive(work);
     const account=read(anchor,'account');
     if(!account.own_channel_visible||!account.public_account_id)throw Error('native_account_unverified');
     if(p.binding.public_account_id&&p.binding.public_account_id!==account.public_account_id)throw Error('native_account_changed');
     if(p.action==='bind'&&p.binding.creator_tab_id){const creator=find(p.binding.creator_tab_id);
       if(String(creator.w.id())!==String(anchor.w.id())||!/^https:\/\/creator\.xiaohongshu\.com\//.test(creator.t.url()||''))throw Error('native_creator_tab_mismatch');}
     out={ok:true,window_id:String(anchor.w.id()),anchor_tab_id:String(anchor.t.id()),work_tab_id:String(work.t.id()),
       creator_tab_id:p.binding.creator_tab_id||null,public_account_id:account.public_account_id,original_work_url:work.t.url()};
   }else if(p.action==='navigate'){
     inactive(work);
     if(!/^https:\/\/(www|creator)\.xiaohongshu\.com\//.test(p.url||''))throw Error('native_url_not_allowed');
     work.t.url=p.url;
     out={ok:true,url:work.t.url(),loading:work.t.loading()};
   }else if(p.action==='meta'){
     inactive(work);out={ok:true,url:work.t.url(),title:work.t.title(),loading:work.t.loading()};
   }else if(p.action==='read'){
     const x=p.target==='creator'?find(p.binding.creator_tab_id):work;
     if(p.target!=='creator')inactive(work);
     if(p.target==='creator'&&String(x.w.id())!==String(anchor.w.id()))throw Error('native_creator_tab_mismatch');
     out={ok:true,data:read(x,p.reader)};
   }else if(p.action==='restore'){
     inactive(work);
     if(work.t.url()!==p.expected_url)throw Error('native_work_tab_changed_by_user');
     if(!idle(p.original_url))throw Error('native_restore_url_not_allowed');
     work.t.url=p.original_url;out={ok:true,restored:true};
   }else throw Error('native_action_not_allowed');
 }catch(e){out={ok:false,error:String(e.message||e),error_number:e.errorNumber||e.number||null};}
 out.foreground_and_activity_unchanged=before===fingerprint();
 if(!out.foreground_and_activity_unchanged){out.ok=false;out.error='native_activity_changed';}
 return JSON.stringify(out);
}
"""


def validate_native_url(url):
    try:
        p = urlsplit(url)
        if p.scheme != "https" or p.username or p.password or p.port not in {None, 443}:
            raise ValueError()
        if p.hostname == "www.xiaohongshu.com":
            if p.path.rstrip("/") in {"", "/explore", "/search_result"}:
                return
            research.validate_note_url(url)
            return
        allowed_creator = {"/", "/new/encyclopedia", "/new/home", "/publish/publish", "/new/publish",
                           "/new/note-manager", "/new/note-management", "/new/notes", "/creator/notes",
                           "/new/draft", "/new/drafts"}
        if p.hostname == "creator.xiaohongshu.com" and p.path in allowed_creator:
            return
    except (ValueError, XHSError):
        pass
    raise XHSError("native_url_not_allowed", "只允许官方搜索、笔记读取和已审查的创作界面路径")


def existing_permission():
    if platform.system() != "Darwin":
        raise XHSError("native_mac_required", "此路线需要这台 Mac 的现有 Chrome")
    class Desc(ctypes.Structure):
        _fields_ = [("type", ctypes.c_uint32), ("data", ctypes.c_void_p)]
    lib = ctypes.CDLL("/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices")
    lib.AECreateDesc.argtypes = [ctypes.c_uint32, ctypes.c_void_p, ctypes.c_long, ctypes.POINTER(Desc)]
    lib.AECreateDesc.restype = ctypes.c_int32
    lib.AEDeterminePermissionToAutomateTarget.argtypes = [ctypes.POINTER(Desc), ctypes.c_uint32, ctypes.c_uint32, ctypes.c_bool]
    lib.AEDeterminePermissionToAutomateTarget.restype = ctypes.c_int32
    lib.AEDisposeDesc.argtypes = [ctypes.POINTER(Desc)]
    cc = lambda x: int.from_bytes(x.encode(), "big")
    desc = Desc()
    target = b"com.google.Chrome"
    if lib.AECreateDesc(cc("bund"), ctypes.c_char_p(target), len(target), ctypes.byref(desc)) != 0:
        raise XHSError("native_permission_unknown", "无法读取现有 Chrome 权限状态")
    try:
        status = lib.AEDeterminePermissionToAutomateTarget(ctypes.byref(desc), cc("CrSu"), cc("ExJa"), False)
    finally:
        lib.AEDisposeDesc(ctypes.byref(desc))
    if status != 0:
        raise XHSError("native_permission_unavailable", "现有 Chrome 授权不可用；不会申请新权限或切换到其他路线")


def native_call(action, binding, **kwargs):
    existing_permission()
    payload = {"action": action, "binding": binding, **kwargs}
    code = "const READERS=" + json.dumps(READERS, ensure_ascii=False) + ";\n" + JXA
    try:
        completed = subprocess.run(["/usr/bin/osascript", "-l", "JavaScript", "-e", code,
                                    json.dumps(payload, ensure_ascii=False)], capture_output=True, text=True, timeout=8 if action == "read" else 20)
    except subprocess.TimeoutExpired:
        raise XHSError("native_timeout", "Chrome 原生接口读取超时；未重试、切换路线或操作前台") from None
    if completed.returncode != 0:
        raise XHSError("native_bridge_failed", "Chrome 原生接口失败；未尝试其他连接路线")
    try:
        value = json.loads(completed.stdout)
    except ValueError:
        raise XHSError("native_bridge_failed", "Chrome 原生接口返回无效数据") from None
    if not value.get("ok"):
        if value.get("error_number") == 12:
            raise XHSError("native_page_read_rejected", "Chrome 拒绝页面读取；停止操作，不切换权限或路线")
        error = value.get("error", "native_bridge_failed")
        if error.startswith("site_access_blocked"):
            raise XHSError("site_access_blocked", "官网返回风控或限制；已停止，不恢复导航或切换路线")
        raise XHSError(error if error.startswith("native_") else "native_operation_stopped",
                       "现有非活动标签不满足安全操作条件；已停止")
    return value


def bind_existing(path, anchor_tab_id, work_tab_id, creator_tab_id=None, runner=native_call):
    binding = {"anchor_tab_id": str(anchor_tab_id), "work_tab_id": str(work_tab_id),
               "creator_tab_id": str(creator_tab_id) if creator_tab_id else None}
    checked = runner("bind", binding)
    saved = {k: checked[k] for k in ["window_id", "anchor_tab_id", "work_tab_id", "creator_tab_id", "public_account_id"]}
    saved["route"] = "existing_chrome_apple_events"
    atomic_private_write(path, json.dumps(saved, ensure_ascii=False, indent=2).encode())
    return {"ok": True, "binding": saved, "credentials_copied": False, "new_permissions_created": False,
            "foreground_and_activity_unchanged": checked["foreground_and_activity_unchanged"]}


class NativeChromeBrowser:
    def __init__(self, binding, runner=native_call):
        self.binding, self.runner = binding, runner
        self.original_url = None
        self.current_url = None
        self.blocked = False
        self.actions = []

    def _call(self, action, **kwargs):
        try:
            value = self.runner(action, self.binding, **kwargs)
        except BaseException:
            self.blocked = True
            raise
        self.actions.append(action)
        return value

    def __enter__(self):
        value = self._call("lease")
        self.original_url = value["original_work_url"]
        return self

    def navigate(self, url):
        validate_native_url(url)
        self._call("navigate", url=url)
        self.current_url = url
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            meta = self._call("meta")
            if meta.get("title") == "安全限制":
                self.blocked = True
                raise XHSError("site_access_blocked", "官网出现安全限制；停止此路线")
            if not meta.get("loading"):
                self.current_url = meta["url"]
                return
            time.sleep(0.5)
        self.blocked = True
        raise XHSError("native_page_timeout", "页面未能及时加载；不重试或恢复导航")

    def evaluate(self, expression):
        names = {research.SNAPSHOT_JS: "snapshot", research.CREATOR_INSPECT_JS: "creator", FORM_JS: "creator_form"}
        if expression not in names:
            raise XHSError("native_reader_not_allowed", "此适配层只支持固定的公开页面读取器")
        data = self._call("read", reader=names[expression])["data"]
        if expression == research.SNAPSHOT_JS and isinstance(data, dict) and data.get("url"):
            self.current_url = data["url"]
        return data

    def inspect_existing_creator(self):
        if not self.binding.get("creator_tab_id"):
            raise XHSError("native_creator_tab_missing", "请先提供同一窗口中已打开的官方创作平台标签")
        return self._call("read", reader="creator", target="creator")["data"]

    def evidence(self):
        return {"route": "existing_chrome_apple_events", "new_debug_port": False, "profile_copied": False,
                "foreground_and_activity_unchanged": True, "actions": self.actions,
                "work_tab_restored": "restore" in self.actions}

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None and not self.blocked and self.current_url is not None:
            self._call("restore", original_url=self.original_url, expected_url=self.current_url)
