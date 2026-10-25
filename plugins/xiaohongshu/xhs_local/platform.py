"""Image drafts in the user's existing Chrome, using only the official editor."""
import base64
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

from .drafts import DraftStore, atomic_private_write, image_type, private_dir
from .errors import XHSError
from .native_chrome import existing_permission

PAGE = Path(__file__).with_name('platform_page.js').read_text()
LANDING = 'https://creator.xiaohongshu.com/publish/publish?source=official'
ACTIONS = {'inspect', 'image_mode', 'upload', 'set_text', 'drafts', 'category', 'reopen', 'save', 'preview'}
BRIDGE = r'''
ObjC.import('AppKit');
function run(){
 const p=PAYLOAD,c=Application('com.google.Chrome');
 if(!c.running())throw Error('existing_chrome_required');
 const front=()=>ObjC.unwrap($.NSWorkspace.sharedWorkspace.frontmostApplication.bundleIdentifier);
 const before={front:front(),windows:c.windows().map(w=>({id:String(w.id()),active:w.activeTabIndex()}))};
 const w=c.windows().find(w=>String(w.id())===p.binding.window_id);
 if(!w)throw Error('bound_window_missing');
 let t=w.tabs().find(t=>String(t.id())===p.binding.tab_id);
 if(!t||!/^https:\/\/creator\.xiaohongshu\.com\/publish\/publish(?:[?#]|$)/.test(t.url()||''))throw Error('bound_official_editor_missing');
 let data;
 if(p.action==='new_check_tab'){
   const active=w.activeTabIndex(),newTab=c.Tab({url:p.landing});w.tabs.push(newTab);w.activeTabIndex=active;
   const tabs=w.tabs();t=tabs[tabs.length-1];data={window_id:String(w.id()),tab_id:String(t.id())};
 }else if(p.action==='reset_check_tab'){
   if(!p.binding.check_tab)throw Error('owned_check_tab_required');
   t.url=p.landing;data={reset:true};
 }else{
    data=JSON.parse(t.execute({javascript:'JSON.stringify((()=>{try{return ('+PAGE.toString()+')('+JSON.stringify(p.action==='retire_editor'?Object.assign({},p,{action:'inspect'}):p)+')}catch(e){return {stopped:true,error:String(e.message||e)}}})())'}));
    if(p.action==='retire_editor'){
      if(!data||data.stopped||!data.editor_present||data.title!==p.title||data.content!==p.content||data.image_elements!==p.image_count)throw Error('owned_unchanged_editor_required');
      t.url=p.landing;data={retired:true,tab_id:String(t.id())};
    }
 }
 const after={front:front(),windows:c.windows().map(w=>({id:String(w.id()),active:w.activeTabIndex()}))};
 return JSON.stringify({data,foreground_unchanged:before.front===after.front,active_tabs_unchanged:before.windows.every(x=>after.windows.some(y=>x.id===y.id&&x.active===y.active))});
}
'''


def now():
    return datetime.now(timezone.utc).isoformat()


def native_call(action, binding, **payload):
    if action not in ACTIONS | {'new_check_tab', 'reset_check_tab', 'retire_editor'}:
        raise XHSError('platform_action_not_allowed', '只提供固定图文草稿动作')
    existing_permission()
    p = dict(payload, action=action, binding=binding, landing=LANDING)
    # stdin avoids OS argument length limits and keeps media out of process arguments.
    source = 'const PAYLOAD=' + json.dumps(p, ensure_ascii=False) + ';\n' + PAGE + '\nconst PAGE=platformPage;\n' + BRIDGE
    try:
        r = subprocess.run(['/usr/bin/osascript', '-l', 'JavaScript', '-'], input=source,
                           capture_output=True, text=True, timeout=8)
    except subprocess.TimeoutExpired:
        raise XHSError('platform_outcome_unknown', '原生接口超时；先只读核对，禁止重复上传') from None
    if r.returncode:
        raise XHSError('platform_bridge_stopped', r.stderr.strip()[:250])
    try:
        result = json.loads(r.stdout)
        data = result['data']
    except (ValueError, KeyError):
        raise XHSError('platform_outcome_unknown', '页面未返回有效结果，先只读核对') from None
    if not result['foreground_unchanged'] or not result['active_tabs_unchanged']:
        raise XHSError('platform_activity_changed', '活动上下文改变，已停止')
    if not isinstance(data, dict) or data.get('stopped'):
        raise XHSError('platform_ui_stopped', str(data)[:250])
    return data


class PlatformDrafts:
    autosave_settle_seconds = 3
    def __init__(self, data_dir, runner=native_call, registry_name='platform'):
        self.data_dir = Path(data_dir)
        self.root = private_dir(self.data_dir / registry_name)
        self.runner = runner

    def _read(self, name, default=None):
        p = self.root / name
        if not p.exists():
            return default
        if p.is_symlink() or p.stat().st_mode & 0o077:
            raise XHSError('unsafe_platform_state', '平台绑定及状态文件需为普通私有文件')
        return json.loads(p.read_text())

    def _write(self, name, value):
        atomic_private_write(self.root / name, (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode())

    @contextmanager
    def _lock(self):
        with (self.root / 'operation.lock').open('a') as f:
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise XHSError('platform_busy', '另一项草稿操作正在进行') from None
            try:
                yield
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    def bind(self, window_id, tab_id):
        if not all(isinstance(v,str) and re.fullmatch(r'\d+',v) for v in (window_id,tab_id)):
            raise XHSError('invalid_tab', '需提供已核对的 Chrome 窗口和创作标签 ID')
        binding = {'window_id':window_id,'tab_id':tab_id,'route':'existing_chrome_apple_events'}
        state = self.runner('inspect', binding)
        with self._lock():
            self._write('binding.json', binding)
        return {'ok':True,'binding':binding,'observation':state}

    def binding(self):
        b = self._read('binding.json')
        if not b:
            raise XHSError('platform_binding_required', '先绑定已有官方创作页；无需消费者端研究登录')
        return b

    def inspect(self, manuscript_id=None):
        saved = None
        if manuscript_id:
            DraftStore._id(manuscript_id)
            saved = self._read(manuscript_id+'.json')
        return {'ok':True,'observation':self.runner('inspect', self.binding()),'draft':saved}

    def list(self):
        drafts=[]
        for path in sorted(self.root.glob('*.json')):
            if not re.fullmatch(r'[0-9a-f]{32}\.json',path.name):
                continue
            j=self._read(path.name)
            drafts.append({'manuscript_id':j['manuscript_id'],'title':j.get('last_text',{}).get('title'),
                           'native_draft_id':j.get('native_draft_id'),'revision':j.get('verified_revision'),
                           'pending':bool(j.get('pending')),'verified_at':j.get('verified_at'),
                           'image_count':j.get('image_count'),'storage_scope':'browser_profile_local'})
        return {'ok':True,'drafts':drafts,'source':'local_sync_registry','current_browser_rechecked':False}

    def _payload(self, manuscript_id, expected_revision):
        with DraftStore(self.data_dir / 'manuscripts') as store:
            local = store.get(manuscript_id)
            if type(expected_revision) is not int or local['revision'] != expected_revision:
                raise XHSError('revision_conflict', '请读取当前文稿后再同步')
            p = local['payload']
            content = p['content'].rstrip() + ('\n\n'+' '.join('#'+t.lstrip('#') for t in p['tags']) if p['tags'] else '')
            if len(p['title']) > 20 or len(content)>1000 or not 1<=len(p['images'])<=18:
                raise XHSError('platform_content_limit', '图文需标题≤20字、含标签正文≤1000字、1至18张图')
            assets=[]
            for a in p['images']:
                data = (store.assets / a['sha256']).read_bytes()
                if hashlib.sha256(data).hexdigest()!=a['sha256'] or image_type(data) not in {'image/png','image/jpeg','image/webp'}:
                    raise XHSError('asset_changed', '图片哈希或格式校验失败')
                assets.append(dict(a,bytes=len(data),base64=base64.b64encode(data).decode()))
        return local, {'title':p['title'],'content':content,'asset_names':[a['name'] for a in assets]}, assets

    def _event(self, j, action, binding, **payload):
        event={'action':action,'started_at':now(),'status':'requested'}
        j.setdefault('events',[]).append(event)
        self._write(j['manuscript_id']+'.json',j)
        try:
            result=self.runner(action,binding,**payload)
            event.update(status='completed',result=result)
            return result
        except Exception as e:
            event.update(status='stopped',error=str(e));raise
        finally:
            event['finished_at']=now()
            self._write(j['manuscript_id']+'.json',j)

    def _wait(self, j, binding, predicate, seconds=15):
        deadline=time.monotonic()+seconds
        while True:
            state=self._event(j,'inspect',binding)
            if predicate(state):
                return state
            if time.monotonic()>=deadline:
                raise XHSError('platform_not_ready', '官方编辑器尚未完成；保留页面，先检查状态再继续')
            time.sleep(1)

    def _list(self, j, check, reset=False, expected_id=None, expected_title=None):
        if reset:
            current=self._event(j,'inspect',check)
            if current.get('editor_present'):
                expected=j.get('last_text')
                # A just-written editor is handled by a fresh verification tab.
                if not expected or any(current.get(k)!=v for k,v in expected.items()):
                    raise XHSError('platform_revision_conflict', '编辑页出现未核对修改，停止导航以保留内容')
            self._event(j,'reset_check_tab',check)
        self._wait(j,check,lambda s:s.get('ready')=='complete' and bool(s.get('controls')))
        self._event(j,'drafts',check)
        self._wait(j,check,lambda s:bool(s.get('categories')))
        self._event(j,'category',check)
        # Counts initially render as zero while the browser-local database loads.
        # For known drafts wait for identity, never treat that placeholder as missing.
        if expected_id or expected_title:
            return self._wait(j,check,lambda s:any((not expected_id or c['id']==expected_id) and
                              (not expected_title or c['title']==expected_title) for c in s.get('cards',[])),seconds=20)
        previous=None;stable=0
        def settled(state):
            nonlocal previous,stable
            signature=json.dumps({'categories':state.get('categories'),'cards':state.get('cards')},sort_keys=True)
            stable=stable+1 if signature==previous else 0;previous=signature
            return stable>=4
        return self._wait(j,check,settled,seconds=20)

    def sync(self, manuscript_id, expected_revision):
        local,p,assets=self._payload(manuscript_id,expected_revision)
        with self._lock():
            binding=self.binding()
            j=self._read(manuscript_id+'.json',{'manuscript_id':manuscript_id,'events':[]})
            if j.get('pending'):
                raise XHSError('platform_reconcile_required', '上次写入未完成，先用 platform-inspect 核对；不会重复上传')
            native_id=j.get('native_draft_id')
            if native_id and j.get('asset_hashes') != [a['sha256'] for a in assets]:
                raise XHSError('image_replacement_not_supported', '当前同条修改支持标题正文标签；更换已有图片尚未实现')
            if native_id and j.get('verified_revision')==expected_revision:
                state=self._event(j,'inspect',j['check_binding'])
                if any(state.get(k)!=v for k,v in j['last_text'].items()) or state.get('decoded_image_count')!=j['image_count']:
                    raise XHSError('platform_revision_conflict', '平台当前状态与记录不同，请先核对')
                return self._result(j)
            check=j.get('check_binding')
            if not check:
                check={**self._event(j,'new_check_tab',binding),'check_tab':True}
                j['check_binding']=check
                self._write(manuscript_id+'.json',j)
            listed=self._list(j,check,reset=bool(j.get('native_draft_id')),expected_id=native_id)
            if native_id:
                matches=[a for a in listed['cards'] if a['id']==native_id and a['title']==j['last_text']['title']]
                if len(matches)!=1:
                    raise XHSError('owned_draft_missing', '未找到同一原生 ID 和旧标题，停止修改')
                self._event(j,'reopen',check,native_id=native_id,title=j['last_text']['title'])
                state=self._wait(j,check,lambda s:s.get('editor_present'))
                if any(state.get(k)!=v for k,v in j['last_text'].items()):
                    raise XHSError('platform_revision_conflict', '平台内容已由其他操作修改，请先核对')
                binding=check
            else:
                if any(c['title']==p['title'] for c in listed['cards']):
                    raise XHSError('same_title_exists', '已有同名草稿，停止新建以避免重复或覆盖')
                state=self._event(j,'inspect',binding)
                if state.get('editor_present'):
                    # Keep previous drafts intact when composing the next article.
                    binding=self._event(j,'new_check_tab',binding)
                    state=self._wait(j,binding,lambda s:s.get('ready')=='complete' and bool(s.get('controls')))
                if not state.get('upload_gate'):
                    self._event(j,'image_mode',binding)
                    self._wait(j,binding,lambda s:s.get('upload_gate'))
            j.update(pending=True,requested_revision=expected_revision,asset_hashes=[a['sha256'] for a in assets],edit_binding=binding)
            self._write(manuscript_id+'.json',j)
            if not native_id:
                self._event(j,'upload',binding,assets=assets)
                self._wait(j,binding,lambda s:s.get('editor_present') and s.get('decoded_image_count')==len(assets),seconds=25)
            self._event(j,'set_text',binding,**p,previous=j.get('last_text'))
            return self._finish(j,binding,check,local,p,len(assets))

    def _finish(self,j,binding,check,local,p,image_count):
        state=self._wait(j,binding,lambda s:all(s.get(k)==p[k] for k in ('title','content')) and s.get('decoded_image_count')==image_count)
        if state.get('image_elements')!=image_count:
            raise XHSError('platform_image_count_mismatch', '编辑器图片数量不符，停止保存')
        j['save_method']=self._event(j,'save',binding,**p)
        # Let the official editor debounce its autosave while this source page
        # is still the active page inside the isolated headless browser.
        time.sleep(self.autosave_settle_seconds)
        if binding==check:
            check={**self._event(j,'new_check_tab',binding),'check_tab':True}
            j['check_binding']=check
        # Keep the source intact until the independent draft list confirms its
        # save. The check page is only a list, so it cannot autosave stale text.
        listed=self._list(j,check,reset=True,expected_id=j.get('native_draft_id'),expected_title=p['title'])
        native_id=j.get('native_draft_id')
        matches=[a for a in listed['cards'] if a['title']==p['title'] and (not native_id or a['id']==native_id)]
        if len(matches)!=1:
            raise XHSError('draft_save_unverified', '草稿列表未唯一匹配，保留编辑页，不重复上传')
        j['native_draft_id']=matches[0]['id']
        if not j['native_draft_id']:
            raise XHSError('native_id_missing', '草稿卡片缺少原生 ID')
        # Once persisted, retire the source before opening another editor for
        # this same ID, preventing competing editor autosaves.
        self._event(j,'retire_editor',binding,**p,image_count=image_count)
        j.setdefault('retired_bindings',[]).append(binding)
        self._event(j,'reopen',check,native_id=j['native_draft_id'],title=p['title'])
        state=self._wait(j,check,lambda s:s.get('editor_present') and s.get('decoded_image_count')==image_count)
        if any(state.get(k)!=p[k] for k in ('title','content')) or state.get('image_elements')!=image_count:
            raise XHSError('draft_readback_mismatch', '重开后的文字或图片数量不符，保留状态待核对')
        j.update(pending=False,verified_revision=local['revision'],last_text={k:p[k] for k in ('title','content')},
                 verified_at=now(),image_count=image_count,local_sha256=local['sha256'])
        self._write(j['manuscript_id']+'.json',j)
        self._write('binding.json',check)
        return self._result(j)

    def reconcile(self,manuscript_id,expected_revision):
        local,p,assets=self._payload(manuscript_id,expected_revision)
        with self._lock():
            j=self._read(manuscript_id+'.json')
            if not j or not j.get('pending') or j.get('requested_revision')!=expected_revision or j.get('asset_hashes')!=[a['sha256'] for a in assets]:
                raise XHSError('pending_revision_required', '需要与上次未完成操作相同的文稿版本和图片')
            binding=j.get('edit_binding',self.binding())
            state=self._event(j,'inspect',binding)
            if any(state.get(k)!=p[k] for k in ('title','content')) or state.get('image_elements')!=len(assets):
                raise XHSError('pending_readback_mismatch', '当前编辑器未完全匹配，保持只读；不会重复上传或覆盖')
            return self._finish(j,binding,j['check_binding'],local,p,len(assets))

    def reopen(self, manuscript_id):
        DraftStore._id(manuscript_id)
        with self._lock():
            j=self._read(manuscript_id+'.json')
            if not j or not j.get('native_draft_id') or j.get('pending'):
                raise XHSError('verified_draft_required', '需要已验证保存的原生草稿')
            previous=self._event(j,'inspect',j['check_binding'])
            if previous.get('editor_present') and (any(previous.get(k)!=v for k,v in j['last_text'].items()) or previous.get('image_elements')!=j['image_count']):
                raise XHSError('platform_revision_conflict', '当前编辑页出现修改，先核对再重开')
            check={**self._event(j,'new_check_tab',self.binding()),'check_tab':True}
            listed=self._list(j,check,expected_id=j['native_draft_id'],expected_title=j['last_text']['title'])
            self._event(j,'reopen',check,native_id=j['native_draft_id'],title=j['last_text']['title'])
            state=self._wait(j,check,lambda s:s.get('editor_present') and s.get('decoded_image_count')==j['image_count'])
            if any(state.get(k)!=v for k,v in j['last_text'].items()) or state.get('image_elements')!=j['image_count']:
                raise XHSError('platform_revision_conflict', '重开内容与最后保存版本不同')
            old=j['check_binding']
            previous=self._event(j,'inspect',old)
            if previous.get('editor_present'):
                if any(previous.get(k)!=v for k,v in j['last_text'].items()) or previous.get('image_elements')!=j['image_count']:
                    raise XHSError('platform_revision_conflict', '旧编辑页出现手动修改，保留并停止')
                self._event(j,'retire_editor',old,**j['last_text'],image_count=j['image_count'])
                j.setdefault('retired_bindings',[]).append(old)
            j['check_binding']=check;j['verified_at']=now()
            self._write(manuscript_id+'.json',j);self._write('binding.json',check)
            return {**self._result(j),'observation':state}

    @staticmethod
    def _result(j):
        return {'ok':True,'manuscript_id':j['manuscript_id'],'revision':j['verified_revision'],
                'native_draft_id':j['native_draft_id'],'platform_saved':True,'reopened_verified':True,
                'storage_scope':'browser_profile_local','image_count':j['image_count'],
                'title':j['last_text']['title'],'verified_at':j['verified_at'],
                'published':False,'binding':j['check_binding']}
