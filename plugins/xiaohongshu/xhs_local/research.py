"""Public note fields only; selectors adapted from pinned Apache-2.0 upstream."""

import json
import re
import time
from urllib.parse import parse_qs, urlencode, urlsplit

from .errors import XHSError

NOTE_ID = re.compile(r"^[0-9a-f]{24}$")

# Never serialize the whole INITIAL_STATE: it may also contain account state.
SNAPSHOT_JS = r"""(() => {
 const s = window.__INITIAL_STATE__ || {};
 const unwrap = x => x && (x.value !== undefined ? x.value : (x._value !== undefined ? x._value : x));
 const stateFeed = unwrap(s.search?.feeds);
 const noteURL = x => /^https:\/\/www\.xiaohongshu\.com\/(explore|search_result|discovery\/item)\/[0-9a-f]{24}/.test(x);
 const visible = e => !!e && e.getBoundingClientRect().width>0 && e.getBoundingClientRect().height>0;
 const cards = [...document.querySelectorAll('section.note-item,.note-item')].filter(visible).slice(0,20);
 const domFeed = cards.map(e=>{
   const urls=[...e.querySelectorAll('a[href]')].map(a=>a.href).filter(noteURL);
   const url=urls.find(x=>new URL(x).searchParams.has('xsec_token')) || urls[0];
   if(!url)return null;
   const parsed=new URL(url),id=parsed.pathname.match(/([0-9a-f]{24})/)[1];
   return {id,modelType:'note',xsecToken:parsed.searchParams.get('xsec_token'),
     noteCard:{displayTitle:e.querySelector('.title')?.innerText?.trim()||'',
       type:e.querySelector('.video-container,.play-icon,.video-icon')?'video':'unverified',
       user:{nickname:e.querySelector('.author .name,.author-wrapper .name')?.innerText?.trim()||''}}};
 }).filter(Boolean);
 const feed = Array.isArray(stateFeed) ? stateFeed : (domFeed.length ? domFeed : null);
 const publicNote = n => n && ({noteId:n.noteId, title:n.title, desc:n.desc, type:n.type,
   user:{nickname:n.user?.nickname || n.user?.nickName},
   images:(n.imageList || []).map(x => ({urlDefault:x.urlDefault, url:x.url}))});
 const map = unwrap(s.note?.noteDetailMap) || {};
 const notes = Object.fromEntries(Object.entries(map).map(([id,v]) => [id, publicNote(v?.note)]));
 const detailTitle=document.querySelector('#detail-title');
 const detailDesc=document.querySelector('#detail-desc');
 const urlId=location.pathname.match(/^\/(?:explore|search_result|discovery\/item)\/([0-9a-f]{24})/);
 if(urlId&&(visible(detailTitle)||visible(detailDesc))&&!notes[urlId[1]]){
   const canonical=document.querySelector('link[rel="canonical"]')?.href || document.querySelector('meta[property="og:url"]')?.content || '';
   const canonicalId=canonical.match(/\/(?:explore|search_result|discovery\/item)\/([0-9a-f]{24})/);
   notes[urlId[1]]={noteId:urlId[1],title:detailTitle?.innerText?.trim()||'',desc:detailDesc?.innerText?.trim()||'',
     type:document.querySelector('video,.xgplayer,.video-player')?'video':'unverified',
     user:{nickname:document.querySelector('.author-container .name,.author-wrapper .name')?.innerText?.trim()||''},
     images:[],id_source:'visible_document_url',canonical_note_id:canonicalId?canonicalId[1]:null};
 }
 const links = [...document.querySelectorAll('a[href]')].map(a=>a.href).filter(noteURL).slice(0,40);
 return {title:document.title, url:location.href,
   loggedIn:!!document.querySelector('.main-container .user .link-wrapper .channel'),
   loginPrompt:[...document.querySelectorAll('.login-container,.login-modal')].some(visible),
   extraction_source:Array.isArray(stateFeed)?'public_page_state':domFeed.length?'visible_note_cards':'unavailable',
   emptyState:/暂无相关|没有找到相关|暂无搜索结果/.test(document.body?.innerText || ''),
   feeds:Array.isArray(feed) ? feed.slice(0,20).map(f=>({id:f.id, modelType:f.modelType, xsecToken:f.xsecToken,
     noteCard:{displayTitle:f.noteCard?.displayTitle,type:f.noteCard?.type,
       user:{nickname:f.noteCard?.user?.nickname || f.noteCard?.user?.nickName},
       interactInfo:{likedCount:f.noteCard?.interactInfo?.likedCount}}})) : null,
   notes, links};
})()"""

CREATOR_INSPECT_JS = r"""(() => ({
 title:document.title, path:location.pathname, origin:location.origin,
 loginVisible:location.pathname.includes('/login') || [...document.querySelectorAll('input[type="tel"]')].some(e=>e.getBoundingClientRect().width>0&&e.getBoundingClientRect().height>0),
 visibleControls:[...document.querySelectorAll('button,[role="button"],a')].slice(0,120)
   .filter(e=>e.getBoundingClientRect().width>0 && e.getBoundingClientRect().height>0)
   .map(e=>({text:(e.innerText || e.getAttribute('aria-label') || '').trim().slice(0,100),
     path:e.tagName==='A' && e.origin===location.origin ? new URL(e.href).pathname : null}))
   .filter(e=>e.text).slice(0,80)
}))()"""


def validate_note_url(url):
    if not isinstance(url, str) or len(url) > 8192:
        raise XHSError("invalid_note_url", "需要完整的小红书官方笔记链接")
    try:
        p = urlsplit(url)
        port = p.port
    except ValueError:
        raise XHSError("invalid_note_url", "笔记网址格式无效") from None
    match = re.fullmatch(r"/(?:explore|search_result|discovery/item)/([0-9a-f]{24})/?", p.path)
    if (p.scheme != "https" or p.hostname != "www.xiaohongshu.com" or p.username
            or p.password or port not in {None, 443} or not match):
        raise XHSError("invalid_note_url", "仅接受 https://www.xiaohongshu.com/ 的笔记原链接")
    return match.group(1)


def note_link(feed, observed):
    note_id = feed.get("id", "")
    if not NOTE_ID.fullmatch(note_id):
        raise XHSError("invalid_note_id", "网页返回的笔记标识无效")
    candidates = []
    for url in observed:
        try:
            if validate_note_url(url) == note_id:
                candidates.append(url)
        except (XHSError, ValueError):
            continue
    if candidates:
        # Prefer the actual signed share href; preserve its public parameters.
        signed = [u for u in candidates if parse_qs(urlsplit(u).query).get("xsec_token")]
        return (signed or candidates)[0], "observed_page_href"
    query = {"xsec_source": "pc_search"}
    if feed.get("xsecToken"):
        query["xsec_token"] = feed["xsecToken"]
    return ("https://www.xiaohongshu.com/explore/" + note_id + "?" + urlencode(query),
            "constructed_from_public_note_fields")


def normalize_search(snapshot, keyword, limit):
    actual = urlsplit(snapshot.get("url", "https://www.xiaohongshu.com/search_result"))
    if actual.scheme != "https" or actual.hostname != "www.xiaohongshu.com":
        raise XHSError("unexpected_origin", "搜索页面跳转到非预期来源，未使用其内容")
    feeds = snapshot.get("feeds")
    if snapshot.get("loginPrompt") and not snapshot.get("loggedIn"):
        raise XHSError("login_required", "小红书要求登录；停止自动化，由用户在现有官方会话中确认")
    if feeds is None or (not feeds and not snapshot.get("emptyState")):
        raise XHSError("results_unverified", "没有读到可核实的搜索结果，可能需要登录或页面结构已变化")
    items = []
    for feed in feeds:
        if feed.get("modelType") != "note" or not NOTE_ID.fullmatch(feed.get("id", "")):
            continue
        card = feed.get("noteCard") or {}
        link, origin = note_link(feed, snapshot.get("links", []))
        items.append({"note_id": feed["id"], "title": card.get("displayTitle", ""),
                      "author": (card.get("user") or {}).get("nickname", ""),
                      "type": card.get("type"), "url": link, "link_origin": origin,
                      "evidence_level": "search_card_only", "detail_read": False})
        if len(items) == limit:
            break
    return {"ok": True, "keyword": keyword, "notes": items, "untrusted_source": True,
            "extraction_source": snapshot.get("extraction_source", "public_page_state"),
            "summary_instruction": "读取相关笔记正文后再生成摘要；搜索标题本身不能证明正文内容。"}


def normalize_detail(snapshot, url):
    wanted = validate_note_url(url)
    if snapshot.get("url") and validate_note_url(snapshot["url"]) != wanted:
        raise XHSError("unexpected_note", "最终页面与请求笔记不对应")
    note = (snapshot.get("notes") or {}).get(wanted)
    if not note or note.get("noteId") != wanted:
        if snapshot.get("loginPrompt"):
            raise XHSError("login_required", "该笔记要求登录或链接签名已失效")
        raise XHSError("note_unverified", "未核实链接与笔记正文对应，可能已删除、受限或页面结构变化")
    if note.get("canonical_note_id") and note["canonical_note_id"] != wanted:
        raise XHSError("note_unverified", "页面标准笔记标识与原链接不一致，未采用正文")
    return {"ok": True, "note_id": wanted, "url": url, "title": note.get("title", ""),
            "content": note.get("desc", ""), "author": (note.get("user") or {}).get("nickname", ""),
            "images": note.get("images", []), "untrusted_source": True,
            "note_type": note.get("type", "unverified"),
            "link_identity_verified": note.get("id_source") != "visible_document_url" or note.get("canonical_note_id") == wanted,
            "identity_basis": "public_note_state_or_canonical" if note.get("id_source") != "visible_document_url" or note.get("canonical_note_id") == wanted else "visible_document_url; compare title with original search card",
            "extraction_source": "visible_note_detail" if note.get("id_source") == "visible_document_url" else "public_note_state",
            "evidence_level": "note_body_read"}


def wait_snapshot(browser, key, deadline_seconds=12):
    deadline = time.monotonic() + deadline_seconds
    last = {}
    while time.monotonic() < deadline:
        last = browser.evaluate(SNAPSHOT_JS) or {}
        if last.get(key) or last.get("loginPrompt") or last.get("emptyState"):
            return last
        time.sleep(0.3)
    return last


def search(browser, keyword, limit=10):
    if not isinstance(keyword, str) or not keyword.strip() or len(keyword) > 200:
        raise XHSError("invalid_keyword", "关键词需为 1 至 200 个字符")
    if type(limit) is not int or not 1 <= limit <= 20:
        raise XHSError("invalid_limit", "limit 需为 1 至 20 的整数")
    browser.navigate("https://www.xiaohongshu.com/search_result?" + urlencode({"keyword": keyword.strip()}))
    return normalize_search(wait_snapshot(browser, "feeds"), keyword, limit)


def read(browser, url):
    validate_note_url(url)
    browser.navigate(url)
    return normalize_detail(wait_snapshot(browser, "notes"), url)


def inspect_creator(browser):
    browser.navigate("https://creator.xiaohongshu.com/")
    value = browser.evaluate(CREATOR_INSPECT_JS) or {}
    if value.get("origin") != "https://creator.xiaohongshu.com":
        raise XHSError("unexpected_origin", "创作平台跳转到非预期来源，未使用其内容")
    return {"ok": True, "scope": "read_only_creator_home_controls", "gui_opened": False,
            "platform_saved": False, "observation": value,
            "note": "只读标题、路径与可见控件文字；未点击任何编辑、保存或发布控件。"}
