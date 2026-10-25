"""Dedicated persistent headless Chrome. Never attaches to the daily browser."""
import base64
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import time
from urllib.parse import urlsplit
import uuid

from .browser import Browser, CHROME, WebSocket, request_allowed
from .drafts import atomic_private_write, private_dir
from .errors import XHSError
from .platform import ACTIONS, LANDING, PAGE, PlatformDrafts, now

LOGIN = 'https://creator.xiaohongshu.com/'


def isolated_request_allowed(method, url):
    p=urlsplit(url)
    # Independent of the tool action: publication/social writes remain blocked.
    if method.upper() not in {'GET','HEAD','OPTIONS'}:
        if re.search(r'/(?:publish|post_note|comment|like|follow|favorite|note/post)(?:/|$)',p.path,re.I):
            return False
    if request_allowed(method,url):
        return True
    if method.upper() not in {'POST','PUT'} or p.scheme!='https':
        return False
    host=p.hostname or ''
    official=host=='xiaohongshu.com' or host.endswith('.xiaohongshu.com')
    if method.upper()=='POST' and official and re.search(r'(?:login|qrcode|qr_code|captcha|racing_get|access_check|getconfig|/config$|/scripting$|/sbtsource$|/api/p/pj$)',p.path,re.I):
        return True
    # Uploads are restricted to official image endpoints/CDNs, not note publish.
    if official and re.search(r'/(?:upload(?:/|$)|image/(?:upload|upload_token|preupload)(?:/|$)|material/(?:upload|upload_token|preupload)(?:/|$))',p.path,re.I):
        return True
    return host=='xhscdn.com' or host.endswith('.xhscdn.com')


class IsolatedRuntime:
    def __init__(self,data_dir):
        self.root=private_dir(Path(data_dir)/'isolated-runtime')
        self.profile=self.root/'profile'
        self.metadata=self.root/'runtime.json'

    def _read(self):
        if not self.metadata.exists():return {}
        if self.metadata.is_symlink() or self.metadata.stat().st_mode&0o077:
            raise XHSError('unsafe_isolated_runtime','隔离运行状态必须为普通私有文件')
        return json.loads(self.metadata.read_text())

    def _write(self,value):
        atomic_private_write(self.metadata,(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode())

    def ensure(self):
        lockpath=self.root/'startup.lock'
        with lockpath.open('a') as lock:
            os.chmod(lockpath,0o600)
            fcntl.flock(lock,fcntl.LOCK_EX)
            state=self._read()
            if state.get('site_restriction'):
                raise XHSError('isolated_site_restricted','隔离浏览器已记录站点限制；已停止，不更改网络或回退日常浏览器')
            pid=state.get('pid')
            if pid:
                r=subprocess.run(['/bin/ps','-p',str(pid),'-o','command='],capture_output=True,text=True)
                cmd=r.stdout.strip()
                if cmd:
                    if '--headless=new' not in cmd or '--user-data-dir='+str(self.profile) not in cmd or str(CHROME) not in cmd:
                        raise XHSError('isolated_process_mismatch','运行进程不匹配专用无界面目录，拒绝连接')
                    return state
            if not CHROME.is_file():raise XHSError('chrome_missing','缺少已安装的 Chrome')
            private_dir(self.profile)
            (self.profile/'DevToolsActivePort').unlink(missing_ok=True)
            args=[str(CHROME),'--headless=new','--no-startup-window',
                  '--remote-debugging-address=127.0.0.1','--remote-debugging-port=0',
                  '--user-data-dir='+str(self.profile),'--no-first-run','--no-default-browser-check',
                  '--disable-sync','--disable-component-update','--disable-background-networking',
                  '--window-size=1440,1100','about:blank']
            process=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL,start_new_session=True)
            active=self.profile/'DevToolsActivePort';deadline=time.monotonic()+20
            while not active.exists():
                if process.poll() is not None or time.monotonic()>deadline:
                    if process.poll() is None:process.terminate()
                    raise XHSError('isolated_start_failed','无界面浏览器未启动；不会打开桌面窗口')
                time.sleep(.1)
            state={'pid':process.pid,'generation':uuid.uuid4().hex,'headless':True,
                   'profile':str(self.profile),'targets':[],'started_at':now()}
            self._write(state)
            return state

    @contextmanager
    def connection(self,binding=None):
        state=self.ensure();lines=(self.profile/'DevToolsActivePort').read_text().splitlines()
        denied=[]
        def policy(method,url):
            allowed=isolated_request_allowed(method,url)
            if not allowed:
                u=urlsplit(url);denied.append({'method':method,'host':u.hostname,'path':u.path})
            return allowed
        browser=Browser(request_policy=policy)
        browser.ws=WebSocket(int(lines[0]),lines[1]);browser.session=None
        try:
            if binding:
                if binding.get('window_id')!=state['generation'] or binding.get('tab_id') not in state['targets']:
                    raise XHSError('isolated_binding_stale','隔离标签已失效；仅允许本工具创建的无界面页面')
                # Focus only inside the verified headless process. This keeps its
                # autosave timers/animations running; it never activates a Mac app.
                browser.call('Target.activateTarget',{'targetId':binding['tab_id']})
                browser.session=browser.call('Target.attachToTarget',{'targetId':binding['tab_id'],'flatten':True})['sessionId']
                browser.call('Page.enable')
                browser.call('Runtime.enable')
                browser.call('Fetch.enable',{'patterns':[{'urlPattern':'*','requestStage':'Request'}]})
                browser.call('Page.setDownloadBehavior',{'behavior':'deny'})
            yield browser,state
        finally:
            # Close just the protocol socket. Dedicated Chrome keeps its own session/profile.
            browser.ws.close()
            if denied:
                path=self.root/'blocked-paths.json'
                previous=json.loads(path.read_text()) if path.exists() else []
                values={json.dumps(v,sort_keys=True):v for v in previous+denied}
                atomic_private_write(path,(json.dumps(list(values.values())[-60:],ensure_ascii=False,indent=2)+'\n').encode())

    def new_page(self,url=LANDING):
        if url not in {LANDING,LOGIN}:raise XHSError('isolated_url_not_allowed','仅打开官方创作入口')
        with self.connection() as (browser,state):
            tid=browser.call('Target.createTarget',{'url':'about:blank','background':True})['targetId']
            state['targets'].append(tid);self._write(state)
            binding={'window_id':state['generation'],'tab_id':tid,'route':'isolated_headless','check_tab':True}
        with self.connection(binding) as (browser,_):
            browser.navigate(url)
        return binding

    def _risk(self,browser):
        risk=browser.evaluate("(()=>{const t=document.body?.innerText||'';return {blocked:document.title==='安全限制'||/IP存在风险|操作过于频繁|请完成安全验证|访问异常/.test(t),code:t.includes('300012')?'300012':null}})()")
        if risk and risk.get('blocked'):
            state=self._read();state['site_restriction']={'observed_at':now(),**risk};self._write(state)
            raise XHSError('isolated_site_restricted','官方返回验证或站点限制；已停止，无网络/指纹变更或日常浏览器回退')

    def call(self,action,binding,**p):
        if action not in ACTIONS|{'new_check_tab','reset_check_tab','retire_editor'}:
            raise XHSError('platform_action_not_allowed','仅允许固定草稿动作')
        if action=='new_check_tab':return self.new_page()
        with self.connection(binding) as (browser,_):
            self._risk(browser)
            url=browser.evaluate('location.href')
            if not re.match(r'^https://creator\.xiaohongshu\.com/publish/publish(?:[?#]|$)',url or ''):
                raise XHSError('isolated_login_required','隔离浏览器需要先完成官方创作平台登录')
            if action=='reset_check_tab':
                if not binding.get('check_tab'):raise XHSError('owned_check_tab_required','仅重置本工具创建的核对页')
                browser.navigate(LANDING);return {'reset':True}
            data=browser.evaluate('(()=>{'+PAGE+';try{return platformPage('+json.dumps(dict(p,action='inspect' if action=='retire_editor' else action),ensure_ascii=False)+');}catch(e){return {stopped:true,error:String(e.message||e)};}})()')
            if not isinstance(data,dict) or data.get('stopped'):
                raise XHSError('isolated_page_result_invalid','隔离页面停止：'+str(data)[:250])
            if action=='retire_editor':
                if not data.get('editor_present') or any(data.get(k)!=p[k] for k in ('title','content')) or data.get('image_elements')!=p['image_count']:
                    raise XHSError('owned_unchanged_editor_required','旧编辑页不匹配，保留并停止')
                browser.navigate(LANDING);return {'retired':True,'tab_id':binding['tab_id']}
            return data

    def status(self,binding,capture=False):
        with self.connection(binding) as (browser,state):
            self._risk(browser)
            data=browser.evaluate(r'''(()=>{
              const visible=e=>!!e&&e.getBoundingClientRect().width>0&&e.getBoundingClientRect().height>0;
              const qr=[...document.querySelectorAll('canvas,img,[class*=qrcode],[class*=qr-code]')].filter(visible).map(e=>({e,r:e.getBoundingClientRect()})).filter(x=>x.r.width>=100&&x.r.width<=500&&x.r.height>=100&&x.r.height<=600);
              return {url:location.href,title:document.title,ready:document.readyState,text:(document.body?.innerText||'').slice(0,2200),
                qr_candidates:qr.map(x=>({tag:x.e.tagName,class:x.e.className||'',x:x.r.x,y:x.r.y,width:x.r.width,height:x.r.height})),
                fields:[...document.querySelectorAll('input')].filter(visible).map(e=>({type:e.type,placeholder:e.placeholder})),
                logged_in:!location.pathname.includes('/login')&&!/登录小红书|扫码登录|手机号登录/.test(document.body?.innerText||'')};
            })()''')
            result={'ok':True,'headless':True,'desktop_browser_used':False,'profile_isolated':True,
                    'binding':binding,'observation':data,'blocked_requests':browser.blocked_requests}
            if capture and not data['logged_in']:
                options={'format':'png','captureBeyondViewport':False}
                qr=next((q for q in data['qr_candidates'] if q['tag']=='IMG'),None)
                if qr:
                    options['clip']={'x':max(0,qr['x']-20),'y':max(0,qr['y']-20),'width':qr['width']+40,'height':qr['height']+40,'scale':2}
                image=browser.call('Page.captureScreenshot',options)
                path=self.root/('official-login-qr-'+str(time.time_ns())+'.png' if qr else 'official-login.png');atomic_private_write(path,base64.b64decode(image['data']))
                result['image_path']=str(path)
            return result


class IsolatedPlatformDrafts(PlatformDrafts):
    autosave_settle_seconds = 10
    def __init__(self,data_dir):
        self.runtime=IsolatedRuntime(data_dir)
        super().__init__(data_dir,runner=self.runtime.call,registry_name='platform-isolated')

    def setup(self,capture=True):
        binding=self._read('binding.json')
        if not binding:
            binding=self.runtime.new_page(LOGIN);self._write('binding.json',binding)
        status=self.runtime.status(binding,capture=False)
        if status['observation']['logged_in'] and not re.match(r'^https://creator\.xiaohongshu\.com/publish/publish(?:[?#]|$)',status['observation']['url']):
            binding=self.runtime.new_page();self._write('binding.json',binding)
            status=self.runtime.status(binding,capture=False)
        if capture and '/login' in status['observation']['url'] and '二维码已过期' in status['observation']['text']:
            with self.runtime.connection(binding) as (browser,_):
                self.runtime._risk(browser)
                browser.evaluate("(()=>{if(location.origin!=='https://creator.xiaohongshu.com'||!location.pathname.includes('/login'))throw Error('official_login_required');const m=[...document.querySelectorAll('button,span,div,a')].filter(e=>!e.children.length&&['返回重新扫描','刷新'].includes(e.innerText.trim())&&e.getBoundingClientRect().width>0&&e.getBoundingClientRect().height>0);if(m.length!==1)throw Error('unique_login_refresh_required');m[0].click();return {login_qr_refreshed:true};})()")
            time.sleep(1)
            status=self.runtime.status(binding,capture=False)
        if capture and '/login' in status['observation']['url'] and '短信登录' in status['observation']['text']:
            with self.runtime.connection(binding) as (browser,_):
                self.runtime._risk(browser)
                browser.evaluate("(()=>{if(location.origin!=='https://creator.xiaohongshu.com'||!location.pathname.includes('/login')||!document.body.innerText.includes('短信登录'))throw Error('official_sms_login_required');const m=[...document.querySelectorAll('.sso-login-wrapper .css-jjnw1w img')].filter(e=>e.getBoundingClientRect().width>0);if(m.length!==1)throw Error('unique_login_mode_switch_required');m[0].click();return {qr_mode_requested:true};})()")
            time.sleep(1)
        return self.runtime.status(binding,capture=capture)

    def bind(self,window_id,tab_id):
        raise XHSError('desktop_binding_disabled','已选择独立无界面环境；日常 Chrome 标签绑定已禁用，请调用 isolated-status')

    def binding(self):
        binding=self._read('binding.json')
        if not binding:raise XHSError('isolated_setup_required','先调用 isolated-status 启动专用后台登录页')
        return binding

    @staticmethod
    def _result(j):
        return {**PlatformDrafts._result(j),'backend':'isolated_headless','desktop_browser_used':False}
