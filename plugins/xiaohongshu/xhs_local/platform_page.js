// Fixed official-editor operations. No network API, storage writes, or publish action.
function platformPage(p) {
  if (location.origin !== 'https://creator.xiaohongshu.com') throw Error('official_creator_required');
  const visible = e => {
    if (!e) return false;
    const r = e.getBoundingClientRect();
    if (!r.width || !r.height) return false;
    for (let n=e;n;n=n.parentElement) {
      const s=getComputedStyle(n);
      if (s.display==='none'||s.visibility==='hidden'||Number(s.opacity)<0.1) return false;
    }
    return true;
  };
  const text=e=>(e.innerText||'').trim();
  const body=document.body?.innerText||'';
  if (document.title==='安全限制'||/IP存在风险|操作过于频繁|请完成安全验证|访问异常/.test(body)) throw Error('site_access_blocked');
  if (location.pathname.includes('/login')||[...document.querySelectorAll('input[type=tel]')].some(visible)) throw Error('official_login_required');
  const titles=[...document.querySelectorAll('input,textarea')].filter(visible).filter(e=>/标题/.test(e.placeholder||''));
  const editors=[...document.querySelectorAll('[contenteditable=true]')].filter(visible);
  const title=titles.length===1?titles[0].value:null;
  // innerText on the whole ProseMirror node inserts CSS paragraph spacing as
  // extra newlines. Read its actual block structure to retain authored breaks.
  const inlineText=n=>n.nodeType===Node.TEXT_NODE?n.textContent:n.nodeType!==Node.ELEMENT_NODE?'':n.tagName==='BR'?(n.classList.contains('ProseMirror-trailingBreak')?'':'\n'):[...n.childNodes].map(inlineText).join('');
  const content=editors.length===1?(editors[0].children.length?[...editors[0].children].map(inlineText).join('\n'):editors[0].textContent).trim():null;
  const images=[...document.querySelectorAll('.img-list img,.image-list img,.upload-image img')];
  function click(e) {
    if (!e||!visible(e)||e.disabled) throw Error('safe_control_unavailable');
    e.click();
    return {clicked:text(e).slice(0,100)};
  }
  function control(labels, scope=document) {
    let found=[...scope.querySelectorAll('button,[role=button]')].filter(visible).filter(e=>labels.includes(text(e)));
    if (!found.length) found=[...scope.querySelectorAll('div,span')].filter(visible).filter(e=>!e.children.length&&labels.includes(text(e)));
    if (found.length!==1) throw Error('unique_control_required:'+labels.join('|')+':'+found.length);
    return click(found[0]);
  }
  const cards=()=>[...document.querySelectorAll('.draft-item')].filter(visible).map(e=>({
    id:e.getAttribute('data-draft-id'),title:e.querySelector('.draft-title-text')?.innerText.trim(),
    text:text(e).slice(0,200)
  }));
  const state=()=>({
    url:location.href,page_title:document.title,ready:document.readyState,
    editor_present:titles.length===1&&editors.length===1,title,content,
    upload_gate:body.includes('上传图片，或写文字生成图片'),
    selected_files:[...document.querySelectorAll('input[type=file]')].map(e=>e.files.length),
    categories:[...document.querySelectorAll('.draft-tabs .tab-item')].filter(visible).map(text),
    cards:cards(),
    image_elements:images.length,
    decoded_image_count:images.filter(e=>e.complete&&e.naturalWidth>0&&e.naturalHeight>0).length,
    images:[...document.querySelectorAll('img')].filter(e=>e.naturalWidth>=300).map(e=>({
      width:e.naturalWidth,height:e.naturalHeight,complete:e.complete,class:e.className,
      parent_class:e.parentElement?.className
    })),
    controls:[...document.querySelectorAll('button,[role=button],.header-draft')].filter(visible).map(e=>({text:text(e),disabled:!!e.disabled,class:e.className})).filter(e=>e.text).slice(0,50),
    hints:[...document.querySelectorAll('span,div,p')].filter(visible).filter(e=>!e.children.length&&/保存|草稿|上传|处理中|失败|图片可以|我知道|张图片/.test(text(e))).map(text).filter(t=>t.length<150).slice(0,50),
    preview: (()=>{const e=document.querySelector('.publish-page-preview');return e?{visible:visible(e),text:text(e),images:[...e.querySelectorAll('img')].map(i=>({width:i.naturalWidth,height:i.naturalHeight,complete:i.complete}))}:null;})()
  });
  if (p.action==='inspect') return state();
  if (p.action==='image_mode') {
    if (titles.length||editors.length) throw Error('blank_landing_required');
    const m=[...document.querySelectorAll('.creator-tab')].filter(visible).filter(e=>{
      const r=e.getBoundingClientRect();
      return r.x+r.width>0&&r.y+r.height>0&&r.x<innerWidth&&r.y<innerHeight&&text(e)==='上传图文';
    });
    if (m.length!==1) throw Error('unique_image_mode_required');
    return click(m[0]);
  }
  if (p.action==='upload') {
    if (!body.includes('上传图片，或写文字生成图片')||titles.length||editors.length) throw Error('empty_image_upload_gate_required');
    const inputs=[...document.querySelectorAll('input[type=file]')];
    if (inputs.length!==1||inputs[0].files.length||!inputs[0].accept.includes('.png')) throw Error('one_empty_image_input_required');
    const dt=new DataTransfer();
    for(const a of p.assets){
      const bytes=Uint8Array.from(atob(a.base64),c=>c.charCodeAt(0));
      if(bytes.length!==a.bytes)throw Error('asset_length_mismatch');
      dt.items.add(new File([bytes],a.name,{type:a.mime}));
    }
    inputs[0].files=dt.files;
    inputs[0].dispatchEvent(new Event('change',{bubbles:true}));
    return {selected_images:dt.files.length,names:p.assets.map(a=>a.name)};
  }
  if (p.action==='set_text') {
    if(titles.length!==1||editors.length!==1)throw Error('unique_editor_fields_required');
    if (p.previous) {
      if(title!==p.previous.title||content!==p.previous.content)throw Error('platform_revision_conflict');
    } else if(content||title&&![p.title,...p.asset_names.map(n=>n.replace(/\.[^.]+$/,'')),...p.asset_names].includes(title)) throw Error('existing_editor_content');
    Object.getOwnPropertyDescriptor(titles[0].tagName==='INPUT'?HTMLInputElement.prototype:HTMLTextAreaElement.prototype,'value').set.call(titles[0],p.title);
    titles[0].dispatchEvent(new Event('input',{bubbles:true}));
    titles[0].dispatchEvent(new Event('change',{bubbles:true}));
    if(content!==p.content){
      editors[0].focus();
      const r=document.createRange();r.selectNodeContents(editors[0]);
      const s=getSelection();s.removeAllRanges();s.addRange(r);
      if(!document.execCommand('insertText',false,p.content))throw Error('editor_insert_failed');
      editors[0].dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText',data:p.content}));
      editors[0].blur();
    }
    titles[0].blur();
    return {text_entered:true};
  }
  if(p.action==='drafts'){
    if(titles.length||editors.length)throw Error('landing_required');
    if([...document.querySelectorAll('.draft-tabs .tab-item')].some(visible))return {already_open:true};
    const m=[...document.querySelectorAll('.header-draft .draft-title-box')].filter(visible);
    if(m.length!==1)throw Error('unique_draft_control_required');return click(m[0]);
  }
  if(p.action==='category'){
    const m=[...document.querySelectorAll('.d-drawer .draft-tabs .tab-item')].filter(visible).filter(e=>text(e).startsWith('图文笔记('));
    if(m.length!==1)throw Error('unique_image_category_required');return click(m[0]);
  }
  if(p.action==='reopen'){
    if(titles.length||editors.length)throw Error('draft_list_required');
    const m=[...document.querySelectorAll('.draft-item')].filter(visible).filter(e=>e.getAttribute('data-draft-id')===p.native_id);
    if(m.length!==1||m[0].querySelector('.draft-title-text')?.innerText.trim()!==p.title)throw Error('owned_draft_id_and_title_required');
    return {...control(['编辑'],m[0]),native_draft_id:p.native_id};
  }
  if(p.action==='save'||p.action==='preview'){
    if(title!==p.title||content!==p.content)throw Error('text_mismatch_before_'+p.action);
    if(p.action==='preview')return control(['预览','预览笔记']);
    const labels=['暂存离开','保存草稿','存草稿','暂存草稿'];
    if(![...document.querySelectorAll('button,[role=button]')].filter(visible).some(e=>labels.includes(text(e))))return {method:'official_auto_save',explicit_button:false};
    return control(labels);
  }
  throw Error('platform_action_not_allowed');
}
