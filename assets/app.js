'use strict';
const DATA=JSON.parse(document.getElementById('site-data').textContent);
const C=DATA.config;
const E=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const root=()=>C.site_url?C.site_url.replace(/\/$/,'')+'/':new URL('./',location.href).href;
const safe=s=>{try{const u=new URL(s);return ['https:','http:'].includes(u.protocol)&&!u.username&&!u.password?u.href:''}catch{return ''}};
const day=d=>new Date(d+'T12:00:00+09:00').toLocaleDateString('ko-KR',{month:'long',day:'numeric',weekday:'short'});
const fullDay=d=>d.replaceAll('-','.');
const mark='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="3"/><path d="M7 7h10M7 11h10M7 15h4M7 18h10M14 15h3"/></svg>';
const picture='<svg viewBox="0 0 48 40" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true"><rect x="5" y="4" width="38" height="32" rx="4"/><circle cx="16" cy="14" r="3"/><path d="m6 30 11-10 8 7 7-12 10 16"/></svg>';
function toast(s){const t=document.getElementById('toast');t.textContent=s;t.classList.remove('hidden');clearTimeout(window.toastTimer);window.toastTimer=setTimeout(()=>t.classList.add('hidden'),4000)}
async function copy(s){try{await navigator.clipboard.writeText(s);toast('복사했습니다. 카카오톡에 붙여넣어 주세요.')}catch{const t=document.createElement('textarea');t.value=s;document.body.append(t);t.select();const ok=document.execCommand('copy');t.remove();if(ok)toast('복사했습니다. 카카오톡에 붙여넣어 주세요.');else window.prompt('아래 내용을 복사해 주세요.',s)}}
function shareText(){return `[${C.title}]\n새로 모은 기사를 보내드립니다. 아래 링크에서 확인해 주세요.\n\n${root()}`}
async function share(){if(DATA.demo){document.getElementById('share-demo').showModal();return}if(navigator.share){try{await navigator.share({title:C.title,text:'새로 모은 기사를 확인해 주세요.',url:root()});return}catch(e){if(e.name==='AbortError')return}}await copy(shareText())}
function header(editor=false){return `<header><div class="wrap top"><a href="${E(root())}" class="brand" id="home"><span class="mark">${mark}</span>${E(C.title)}</a><nav><button class="quiet" id="${editor?'view':'edit'}">${editor?'← 뉴스 보기':'기사 올리기 ＋'}</button></nav></div></header>`}
function photo(a){return `<div class="photo"><div class="photo-empty">${picture}<span>${DATA.demo?'기사 대표사진 자리':'대표사진 없음'}</span></div>${safe(a.image)?`<img src="${E(safe(a.image))}" alt="${E(a.title)} 대표사진" loading="lazy" referrerpolicy="no-referrer">`:''}</div>`}
function card(a){return `<article class="news-card"><a class="photo-link" href="${E(safe(a.url))}" target="_blank" rel="noopener noreferrer" aria-label="${E(a.title)} 원문 읽기">${photo(a)}</a><div class="news-content"><div class="source">${E(a.source||'원문 기사')}</div><h3><a href="${E(safe(a.url))}" target="_blank" rel="noopener noreferrer">${E(a.title)}</a></h3>${a.summary?`<p class="summary">${E(a.summary)}</p>${a.summary_kind?`<span class="summary-kind">${E(a.summary_kind==='본문 자동 발췌'?'기사 본문에서 자동 발췌':'언론사에서 제공한 기사 소개')}</span>`:''}`:'<p class="summary muted">요약이 아직 없습니다. 기사 원문에서 확인해 주세요.</p>'}<a class="read" href="${E(safe(a.url))}" target="_blank" rel="noopener noreferrer">기사 읽기 <span aria-hidden="true">↗</span></a></div></article>`}
function bindPhotos(){document.querySelectorAll('.photo img').forEach(img=>{img.addEventListener('error',()=>img.remove());if(img.complete&&img.naturalWidth===0)img.remove()})}
function render(){document.getElementById('app').innerHTML=header()+`<main class="wrap" id="main"><div class="intro"><div><div class="eyebrow">NEWS COLLECTION</div><h1>오늘의 시내버스 주요 뉴스</h1><p>전하고 싶은 소식을 한곳에 모았습니다.</p></div><div class="share-actions"><button class="share" id="share">카카오톡으로 공유 ↗</button><button id="copy">링크 복사</button></div></div>${DATA.demo?'<div class="demo">화면 미리보기 · 보내주신 인포크 페이지의 지난 기사로 구성했습니다. 날짜는 기존 공유일 기준입니다.</div>':''}<div class="news-tools"><span class="archive-note">최신 날짜부터 · 지난 기사도 이곳에서</span><label class="search"><span class="sr-only">지난 기사 검색</span><input type="search" id="search" placeholder="지난 기사 검색"></label></div><div id="news"></div><footer>기사 제목이나 사진을 누르면 원문으로 이동합니다.<br>공유하는 사이트 주소는 항상 같습니다.<span class="credit">공유사진: <a href="https://commons.wikimedia.org/wiki/File:Hyundai_Elec_City_Fuel_Cell_Busan_bus_copy.jpg" target="_blank" rel="noopener noreferrer">Nord794ub · Wikimedia Commons</a> / <a href="https://creativecommons.org/licenses/by-sa/4.0/" target="_blank" rel="noopener noreferrer">CC BY-SA 4.0</a></span></footer></main><dialog id="share-demo" aria-labelledby="share-demo-title"><div class="dialog-top"><strong id="share-demo-title">카카오톡 공유 화면 예시</strong><button id="close-share" aria-label="미리보기 닫기">×</button></div><p class="dialog-note">실제 카카오톡 화면은 게시 후 확인할 수 있습니다.</p><div class="kakao-card"><img src="${E(C.share_image_inline||new URL(C.share_image||'assets/busan-city-bus.jpg',root()).href)}" alt="부산 시내버스 공유 대표사진"><div><strong>${E(C.title)}</strong><p>${E(C.subtitle)}</p><small>게시 후 고정 사이트 주소 표시</small></div></div></dialog>`;
 const draw=q=>{const groups=DATA.briefs.map(g=>({...g,articles:g.articles.filter(a=>!q||[a.title,a.summary,a.source].join(' ').toLowerCase().includes(q.toLowerCase()))})).filter(g=>g.articles.length);document.getElementById('news').innerHTML=groups.map((g,i)=>`<section class="daily"><div class="day"><h2>${E(day(g.date))}<span>${g.date.slice(0,4)}</span></h2><span class="count">기사 ${g.articles.length}개</span>${i===0&&!q?'<span class="latest">최근 등록</span>':''}</div><div class="news-grid">${g.articles.map(card).join('')}</div></section>`).join('')||`<div class="empty">${DATA.briefs.length?'검색된 기사가 없습니다.':'아직 등록된 기사가 없습니다.'}</div>`;bindPhotos()};draw('');document.getElementById('close-share').onclick=()=>document.getElementById('share-demo').close();document.getElementById('search').oninput=e=>draw(e.target.value.trim());document.getElementById('share').onclick=share;document.getElementById('copy').onclick=()=>DATA.demo?toast('실제 게시 후 고정 사이트 주소를 복사할 수 있습니다.'):copy(root());document.getElementById('edit').onclick=editor;document.getElementById('home').onclick=e=>{e.preventDefault();render()}}
function draftKey(){return 'simple-news-draft:'+encodeURIComponent(C.repository||new URL('./',location.href).pathname)}
function readDraft(){try{const saved=JSON.parse(localStorage.getItem(draftKey())||localStorage.getItem('simple-news-draft')||'null');return saved&&/^\d{4}-\d{2}-\d{2}$/.test(saved.date)&&Array.isArray(saved.articles)?saved:null}catch{return null}}
function editorData(){return {date:document.getElementById('date').value,articles:[...document.querySelectorAll('.edit-card')].map(el=>Object.fromEntries(['url','title','summary','image','source'].map(k=>[k,el.querySelector('.'+k).value.trim()])))}}
function saveDraft(){try{localStorage.setItem(draftKey(),JSON.stringify(editorData()));document.getElementById('draft-state').textContent='이 기기에 초안 저장됨'}catch{document.getElementById('draft-state').textContent='이 기기에서는 초안 저장이 지원되지 않습니다.'}}
function addArticle(a={}){
 const n=document.querySelectorAll('.edit-card').length;
 if(n===10){toast('한 번에 10개까지 올릴 수 있습니다.');return}
 const el=document.createElement('section');el.className='edit-card';
 el.innerHTML=`<div class="edit-top"><strong>기사 <span class="index"></span></strong><button type="button" class="remove quiet">삭제</button></div><label>기사 주소 *<input class="url" type="url" required placeholder="네이버 뉴스나 언론사 기사 주소를 붙여넣으세요" value="${E(a.url||'')}"></label><p class="field-hint">링크만 입력하면 등록 후 제목·사진·짧은 요약을 자동으로 가져옵니다.</p><p class="field-hint saved-link-hint" role="status"></p><details><summary>직접 수정하기 (선택)</summary><label>제목<input class="title" maxlength="250" value="${E(a.title||'')}" placeholder="기사 제목"></label><label>짧은 요약<textarea class="summary" maxlength="1500" placeholder="전달하고 싶은 핵심 내용을 2~3줄로 적어주세요.">${E(a.summary||'')}</textarea></label><label>대표사진 주소<input class="image" type="url" value="${E(a.image||'')}" placeholder="https://… (선택)"></label><label>언론사<input class="source" maxlength="100" value="${E(a.source||'')}" placeholder="언론사 이름 (선택)"></label></details>`;
 const urlField=el.querySelector('.url');let previousURL=urlField.value.trim();
 const clearDetails=()=>el.querySelectorAll('.title,.summary,.image,.source').forEach(field=>field.value='');
 const showExisting=()=>{const url=safe(urlField.value.trim());const found=url&&DATA.briefs.find(g=>g.articles.some(item=>safe(item.url)===url));el.querySelector('.saved-link-hint').textContent=found?`이미 ${found.date}에 등록된 기사입니다. 다른 기사를 올리려면 주소를 바꿔 주세요.`:''};
 el.querySelector('.remove').onclick=()=>{
  if(document.querySelectorAll('.edit-card').length===1){urlField.value='';previousURL='';clearDetails();showExisting();urlField.focus()}
  else el.remove();
  renumber();saveDraft();document.getElementById('preview-area').innerHTML='';
 };
 el.querySelectorAll('input,textarea').forEach(field=>field.oninput=()=>{saveDraft();document.getElementById('preview-area').innerHTML=''});
 urlField.oninput=()=>{
  const next=urlField.value.trim();
  if(next!==previousURL){clearDetails();previousURL=next}
  showExisting();saveDraft();document.getElementById('preview-area').innerHTML='';
 };
 document.getElementById('articles').append(el);showExisting();renumber();
}
function renumber(){const cards=[...document.querySelectorAll('.edit-card')];cards.forEach((el,i)=>{el.querySelector('.index').textContent=i+1;el.querySelector('.remove').textContent=cards.length===1?'비우기':'삭제'})}
function validate(){const form=document.getElementById('form');for(const d of form.querySelectorAll('details')){if([...d.querySelectorAll('input')].some(i=>!i.validity.valid))d.open=true}if(!form.reportValidity())return null;const data=editorData();if(data.articles.some(a=>!safe(a.url)||(a.image&&!safe(a.image)))){toast('기사와 사진 주소를 확인해 주세요.');return null}if(new Set(data.articles.map(a=>a.url)).size!==data.articles.length){toast('같은 기사 주소가 중복되었습니다.');return null}return data}
function editor(restored=null){
 const saved=readDraft();
 // A click event is never a draft. Previously saved input is restored only explicitly.
 const draft=restored&&typeof restored.date==='string'&&Array.isArray(restored.articles)?restored:null;
 const today=new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Seoul'}).format(new Date());
 document.getElementById('app').innerHTML=header(true)+`<main class="wrap editor" id="main"><div class="eyebrow">ADD NEWS</div><h1>전하고 싶은 기사 올리기</h1><p class="editor-intro">이번에 등록할 기사 주소만 넣어주세요. 이전에 게시한 기사는 그대로 보관됩니다.</p><div class="actions"><button type="button" id="new-entry">오늘 기사 새로 작성</button> <button type="button" id="restore-draft" ${saved?'':'disabled'}>${saved?`이전 초안 불러오기 (${E(saved.date)} · ${saved.articles.length}개)`:'저장된 초안 없음'}</button></div><form id="form"><label class="date-label">등록 날짜<input id="date" type="date" required value="${E(draft?.date||today)}"></label><div id="articles"></div><button id="add" type="button" class="add">＋ 기사 하나 더 추가</button><div class="editor-actions"><button id="preview" type="button">미리보기</button><button type="submit" class="primary">등록하기</button><span id="draft-state">새 입력칸입니다. 이전 초안은 자동으로 전송되지 않습니다.</span></div></form><p class="editor-help">등록 시 GitHub 로그인 화면에서 한 번 확인합니다. 반영까지 수 분 걸릴 수 있습니다.<br>요약은 기사 본문의 앞부분에서 핵심 문장을 발췌하고, 본문을 읽을 수 없으면 언론사의 기사 소개를 사용합니다. 차단된 기사는 자동 가져오기에 실패할 수 있습니다.</p><div id="status" role="status"></div><div id="preview-area"></div>${C.repository?`<a class="manage" href="https://github.com/${E(C.repository)}/issues" target="_blank" rel="noopener noreferrer">올린 기사 수정·삭제 ↗</a>`:'<p class="connection-note">현재는 미리보기입니다. GitHub 연결 후 실제 등록을 사용할 수 있습니다.</p>'}</main>`;
 document.getElementById('home').onclick=e=>{e.preventDefault();render()};document.getElementById('view').onclick=render;
 (draft?.articles?.length?draft.articles:[{}]).slice(0,10).forEach(addArticle);
 document.getElementById('new-entry').onclick=()=>{editor();toast('오늘 날짜의 빈 입력칸으로 시작합니다. 게시된 기사는 그대로입니다.')};
 document.getElementById('restore-draft').onclick=()=>{const current=readDraft();if(current){editor(current);toast('이전 초안을 불러왔습니다. 날짜와 모든 기사 주소를 확인해 주세요.')}};
 document.getElementById('add').onclick=()=>{addArticle();saveDraft()};document.getElementById('date').oninput=saveDraft;
 document.getElementById('preview').onclick=()=>{
  const data=validate();if(!data)return;
  document.getElementById('preview-area').innerHTML=`<h2>${E(data.date)} · 이번에 등록할 기사 ${data.articles.length}개</h2><p class="field-hint">여기에 나온 기사만 이번 등록에 포함됩니다.</p><div class="news-grid">`+data.articles.map(a=>card({...a,title:a.title||'발행할 때 기사 제목을 가져옵니다.',summary:a.summary||'등록 후 짧은 요약이 자동으로 채워집니다.'})).join('')+'</div>';
  bindPhotos();document.getElementById('preview-area').scrollIntoView({behavior:'smooth'});
 };
 document.getElementById('form').onsubmit=e=>{
  e.preventDefault();const data=validate();if(!data)return;saveDraft();
  if(!C.repository||DATA.demo){toast('GitHub 연결 전입니다. 입력한 내용은 초안으로 저장했습니다.');return}
  const body='```json\n'+JSON.stringify(data,null,2)+'\n```';
  const url=`https://github.com/${C.repository}/issues/new?title=${encodeURIComponent('[뉴스브리핑] '+data.date)}&body=${encodeURIComponent(body)}`;
  if(url.length>7600){copy(body);window.open(`https://github.com/${C.repository}/issues/new?title=${encodeURIComponent('[뉴스브리핑] '+data.date)}`,'_blank','noopener');document.getElementById('status').textContent='내용이 길어 복사했습니다. GitHub의 본문 칸에 붙여넣고 Create를 눌러주세요.'}
  else{window.open(url,'_blank','noopener');document.getElementById('status').textContent=`이번 등록은 ${data.date} 기사 ${data.articles.length}개입니다. `+'열린 GitHub 화면에서 Create를 누르면 등록됩니다. 새 기사는 ‘오늘 기사 새로 작성’으로 시작하세요.'}
 };
}
DATA.admin?editor():render();
