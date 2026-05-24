# -*- coding: utf-8 -*-
"""
X いいね ギャラリービューア生成（v7）
================================================================
liked_tweets.db と media を読み合わせて gallery.html を作ります。

機能:
  - 表示: タイル / カード、サイズ 小中大特大（縦長サムネ）
  - 種別: 画像・動画 / 画像のみ / 動画のみ / テキストのみ
  - お気に入り(★): ギャラリー内でさらに★を付け、★だけ表示も可能
  - 検索 / 投稿者 / 並び替え / 年・月
  - 拡大表示で投稿者名クリック→ブラウザでその人を開く / 元ツイートも開ける
  - 複数枚は1サムネ＋枚数バッジ、拡大で左右めくり、動画はミュート再生
※ お気に入りはブラウザに保存されます（同じ gallery.html を使う限り保持）。
"""
import os
import json
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "liked_tweets.db")
OUT      = os.path.join(BASE_DIR, "gallery.html")


def main():
    if not os.path.exists(DB_PATH):
        print("liked_tweets.db が見つかりません。取り込みエンジンと同じフォルダに置いてください。")
        return
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    media_by_tweet = {}
    for m in con.execute("SELECT tweet_id, type, local_path FROM media"):
        media_by_tweet.setdefault(m["tweet_id"], []).append(
            {"type": m["type"], "path": "media/" + m["local_path"]})
    data = []
    for t in con.execute("SELECT * FROM tweets ORDER BY liked_rank ASC"):
        data.append({
            "id":   t["tweet_id"], "user": t["author_username"] or "",
            "name": t["author_name"] or "", "text": t["text"] or "",
            "date": (t["created_at"] or "")[:10], "rank": t["liked_rank"] or 0,
            "media": media_by_tweet.get(t["tweet_id"], []),
        })
    con.close()
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(TEMPLATE.replace("__DATA__", payload))
    print(f"作成しました: {OUT}")
    print(f"件数: {len(data)} 件")
    print("→ gallery.html をダブルクリックすると、ブラウザで開けます。")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>いいねギャラリー</title>
<style>
  :root{--bg:#0c0c0f;--panel:#16161b;--card:#1b1b22;--line:#2a2a33;
    --ink:#ececf1;--sub:#8d8d9a;--accent:#e1b84b;--thumb:160px;--cardw:300px;}
  *{box-sizing:border-box;}
  body{margin:0;background:var(--bg);color:var(--ink);
    font-family:"Yu Gothic","Hiragino Kaku Gothic ProN","Noto Sans JP","Meiryo",sans-serif;}
  header{position:sticky;top:0;z-index:10;background:rgba(12,12,15,.93);
    backdrop-filter:blur(8px);border-bottom:1px solid var(--line);
    padding:11px 16px;display:flex;gap:9px;align-items:center;flex-wrap:wrap;}
  header h1{font-size:15px;margin:0 4px 0 0;letter-spacing:.06em;font-weight:700;}
  header h1 .dot{color:var(--accent);}
  input,select{background:var(--panel);color:var(--ink);border:1px solid var(--line);
    border-radius:9px;padding:7px 10px;font-size:13px;outline:none;}
  input:focus,select:focus{border-color:var(--accent);}
  #q{min-width:150px;flex:1;}
  .favtgl{background:var(--panel);color:var(--sub);border:1px solid var(--line);
    border-radius:9px;padding:7px 12px;font-size:13px;cursor:pointer;}
  .favtgl.on{background:var(--accent);color:#1a1400;font-weight:700;}
  .group{display:flex;border:1px solid var(--line);border-radius:9px;overflow:hidden;}
  .group button{background:var(--panel);color:var(--sub);border:0;padding:7px 11px;
    font-size:13px;cursor:pointer;border-left:1px solid var(--line);}
  .group button:first-child{border-left:0;}
  .group button.on{background:var(--accent);color:#1a1400;font-weight:700;}
  #count{color:var(--sub);font-size:13px;margin-left:auto;}

  main{padding:16px;}
  #tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(var(--thumb),1fr));gap:8px;}
  .tile{position:relative;aspect-ratio:3/4;overflow:hidden;border-radius:9px;
    background:#000;cursor:zoom-in;border:1px solid var(--line);}
  .tile img,.tile video{width:100%;height:100%;object-fit:cover;display:block;}
  .tile.ttile{background:var(--card);}
  .ttext{padding:10px;font-size:12px;line-height:1.55;height:100%;overflow:hidden;
    white-space:pre-wrap;word-break:break-word;color:var(--ink);}
  .cnt{position:absolute;right:6px;top:6px;color:#fff;font-size:12px;font-weight:700;
    background:rgba(0,0,0,.65);border-radius:7px;padding:2px 7px;line-height:1.3;}
  .play{position:absolute;left:6px;bottom:6px;color:#fff;font-size:12px;
    background:rgba(0,0,0,.55);border-radius:6px;padding:1px 6px;}
  .fav{position:absolute;left:6px;top:6px;z-index:3;color:rgba(255,255,255,.55);
    font-size:19px;cursor:pointer;line-height:1;text-shadow:0 0 3px #000;}
  .fav.on{color:var(--accent);}
  .tile .who{position:absolute;left:0;right:0;bottom:0;padding:6px 8px;font-size:11px;
    color:#fff;background:linear-gradient(transparent,rgba(0,0,0,.75));opacity:0;
    transition:.15s;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
  .tile:hover .who{opacity:1;}

  #grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(var(--cardw),1fr));gap:16px;align-items:start;}
  .card{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden;}
  .card .cimg{position:relative;aspect-ratio:3/4;overflow:hidden;cursor:zoom-in;background:#000;}
  .card .cimg img,.card .cimg video{width:100%;height:100%;object-fit:cover;display:block;}
  .card .ctext{position:relative;aspect-ratio:3/4;overflow:hidden;cursor:zoom-in;background:var(--card);
    padding:12px;font-size:13px;line-height:1.6;white-space:pre-wrap;word-break:break-word;
    border-bottom:1px solid var(--line);}
  .card .meta{padding:11px 13px 13px;}
  .card .user{font-size:13px;font-weight:700;}
  .card .user span{color:var(--sub);font-weight:400;margin-left:5px;}
  .card .text{font-size:13px;line-height:1.6;margin:7px 0 0;white-space:pre-wrap;word-break:break-word;
    display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;
    min-height:calc(1.6em * 3);}
  .card .date{font-size:11px;color:var(--sub);margin-top:8px;}
  .empty{color:var(--sub);text-align:center;padding:60px;}

  #lb{position:fixed;inset:0;background:rgba(0,0,0,.93);display:none;z-index:100;padding:24px;gap:18px;}
  #lb.show{display:flex;align-items:center;justify-content:center;}
  #lbMedia{flex:1;display:flex;align-items:center;justify-content:center;min-width:0;}
  #lbMedia img,#lbMedia video{max-width:100%;max-height:90vh;border-radius:8px;}
  .lbtext{max-width:620px;max-height:88vh;overflow:auto;background:var(--card);
    border:1px solid var(--line);border-radius:12px;padding:24px;font-size:15px;
    line-height:1.85;white-space:pre-wrap;word-break:break-word;color:var(--ink);}
  #lbInfo{width:300px;flex-shrink:0;align-self:stretch;overflow:auto;background:var(--card);
    border:1px solid var(--line);border-radius:12px;padding:16px;}
  #lbNav{font-size:12px;color:var(--accent);margin-bottom:8px;}
  #lbUser{font-weight:700;font-size:14px;}
  #lbUser a{color:var(--ink);text-decoration:none;}
  #lbUser a:hover{color:var(--accent);text-decoration:underline;}
  #lbText{font-size:13px;line-height:1.7;margin-top:10px;white-space:pre-wrap;word-break:break-word;}
  #lbDate{font-size:11px;color:var(--sub);margin-top:12px;}
  #lbLink{margin-top:12px;}
  #lbLink a{color:var(--accent);text-decoration:none;font-size:13px;}
  #lbLink a:hover{text-decoration:underline;}
  #lbClose{position:fixed;top:14px;right:18px;color:#fff;font-size:26px;cursor:pointer;z-index:101;}
  .lbArrow{position:fixed;top:50%;transform:translateY(-50%);color:#fff;font-size:44px;
    cursor:pointer;z-index:101;user-select:none;padding:0 14px;opacity:.7;}
  .lbArrow:hover{opacity:1;}
  #lbPrev{left:8px;} #lbNext{right:8px;}
  @media(max-width:700px){#lb{flex-direction:column;padding:14px;}#lbInfo{width:100%;}}
  .modal{position:fixed;inset:0;background:rgba(0,0,0,.72);display:none;
    align-items:center;justify-content:center;z-index:200;}
  .modal.show{display:flex;}
  .modalbox{background:var(--card);border:1px solid var(--line);border-radius:14px;
    padding:24px;width:430px;max-width:92vw;}
  .modalbox h3{margin:0 0 6px;font-size:16px;}
  .modalbox .hint{font-size:11px;color:var(--sub);margin-bottom:8px;}
  .modalbox label{display:block;font-size:12px;color:var(--sub);margin:10px 0 4px;}
  .modalbox input{width:100%;}
  .modalbtns{display:flex;gap:10px;margin-top:18px;justify-content:flex-end;}
  .modalbtns button{background:var(--accent);color:#1a1400;border:0;border-radius:9px;
    padding:8px 16px;font-size:14px;font-weight:700;cursor:pointer;}
  .modalbtns button.sub{background:var(--panel);color:var(--ink);border:1px solid var(--line);font-weight:400;}
  #progMsg{font-size:14px;text-align:center;line-height:1.6;}
  .selbox{position:absolute;right:6px;bottom:6px;z-index:4;width:26px;height:26px;
    border-radius:50%;background:rgba(0,0,0,.6);border:2px solid #fff;color:#fff;
    display:none;align-items:center;justify-content:center;font-size:15px;cursor:pointer;}
  body.selmode .selbox{display:flex;}
  body.selmode .tile,body.selmode .cimg,body.selmode .ctext{cursor:pointer;}
  .selbox.on{background:var(--accent);border-color:var(--accent);color:#1a1400;}
  .tile.selected,.card.selected{outline:3px solid var(--accent);outline-offset:-3px;border-radius:9px;}
  #delMsg{font-size:13px;line-height:1.7;margin-bottom:6px;}
</style>
</head>
<body>
<header>
  <h1><span class="dot">&#9733;</span> いいねギャラリー</h1>
  <input id="q" type="text" placeholder="本文・投稿者で検索...">
  <button id="favBtn" class="favtgl">&#9733; お気に入り</button>
  <button id="updBtn" class="favtgl" style="display:none">&#8635; いいね取得</button>
  <button id="cfgBtn" class="favtgl" style="display:none">&#9881;</button>
  <button id="selBtn" class="favtgl">&#9745; 選択</button>
  <button id="delBtn" class="favtgl" style="display:none;background:#e0533d;color:#fff;border-color:#e0533d">選択を解除</button>
  <select id="author"><option value="">すべての投稿者</option></select>
  <select id="kind">
    <option value="media">画像・動画</option><option value="photo">画像のみ</option>
    <option value="video">動画のみ</option><option value="text">テキストのみ</option>
  </select>
  <select id="sort">
    <option value="like_new">いいね順(新しい)</option><option value="like_old">いいね順(古い)</option>
    <option value="date_new">投稿日(新しい)</option><option value="date_old">投稿日(古い)</option>
    <option value="user">投稿者順</option>
  </select>
  <select id="year"><option value="">すべての年</option></select>
  <select id="month"><option value="">すべての月</option></select>
  <div class="group" id="modeG"><button data-mode="tile">タイル</button><button data-mode="card">カード</button></div>
  <div class="group" id="sizeG">
    <button data-size="110">小</button><button data-size="160">中</button>
    <button data-size="240">大</button><button data-size="360">特大</button></div>
  <span id="count"></span>
</header>
<main><div id="tiles"></div><div id="grid" style="display:none"></div></main>

<div id="lb">
  <span id="lbClose">&times;</span>
  <span id="lbPrev" class="lbArrow">&#8249;</span>
  <span id="lbNext" class="lbArrow">&#8250;</span>
  <div id="lbMedia"></div>
  <div id="lbInfo"><div id="lbNav"></div><div id="lbUser"></div><div id="lbText"></div><div id="lbDate"></div><div id="lbLink"></div></div>
</div>

<div id="cfgModal" class="modal">
  <div class="modalbox">
    <h3>APIキー設定</h3>
    <div class="hint">X開発者ポータルの4つの鍵を貼り付けて保存します（初回のみ）。</div>
    <label>API Key</label><input id="ck1" type="text" autocomplete="off">
    <label>API Key Secret</label><input id="ck2" type="text" autocomplete="off">
    <label>Access Token</label><input id="ck3" type="text" autocomplete="off">
    <label>Access Token Secret</label><input id="ck4" type="text" autocomplete="off">
    <div class="modalbtns"><button class="sub" onclick="closeCfg()">閉じる</button><button onclick="saveCfg()">保存</button></div>
  </div>
</div>
<div id="progModal" class="modal"><div class="modalbox"><div id="progMsg">取得中...</div></div></div>
<div id="delModal" class="modal"><div class="modalbox">
  <h3>いいねを解除</h3>
  <div id="delMsg"></div>
  <div class="modalbtns" style="flex-direction:column;align-items:stretch;gap:8px">
    <button onclick="doUnlike(false)">X本体だけ解除（手元のアーカイブは残す）</button>
    <button onclick="doUnlike(true)">手元のデータも一緒に削除する</button>
    <button class="sub" onclick="closeDel()">やめる</button>
  </div>
</div></div>

<script>
const DATA=__DATA__;
const SZ={'110':['110px','230px'],'160':['160px','300px'],'240':['240px','380px'],'360':['360px','480px']};
const tilesEl=document.getElementById('tiles'),gridEl=document.getElementById('grid');
const q=document.getElementById('q'),authorSel=document.getElementById('author'),kindSel=document.getElementById('kind');
const sortSel=document.getElementById('sort'),yearSel=document.getElementById('year'),monthSel=document.getElementById('month');
const favBtn=document.getElementById('favBtn'),countEl=document.getElementById('count'),lb=document.getElementById('lb');

let mode='tile',size='160',favOnly=false;
try{mode=localStorage.getItem('xlikeMode')||'tile';size=localStorage.getItem('xlikeSize')||'160';}catch(e){}
let FAV=new Set();
let selectMode=false;const SEL=new Set();
try{FAV=new Set(JSON.parse(localStorage.getItem('xlikeFav')||'[]'));}catch(e){}
function saveFav(){try{localStorage.setItem('xlikeFav',JSON.stringify([...FAV]));}catch(e){}}
function toggleFav(id,ev){ev.stopPropagation();if(FAV.has(id))FAV.delete(id);else FAV.add(id);saveFav();
  if(favOnly){render();}else if(ev&&ev.target){ev.target.classList.toggle('on',FAV.has(id));}}

function esc(s){return (s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}

[...new Set(DATA.map(t=>t.user).filter(Boolean))].sort().forEach(u=>{
  const o=document.createElement('option');o.value=u;o.textContent='@'+u;authorSel.appendChild(o);});
[...new Set(DATA.map(t=>t.date.slice(0,4)).filter(Boolean))].sort().reverse().forEach(y=>{
  const o=document.createElement('option');o.value=y;o.textContent=y+'年';yearSel.appendChild(o);});
for(let i=1;i<=12;i++){const mm=String(i).padStart(2,'0');
  const o=document.createElement('option');o.value=mm;o.textContent=i+'月';monthSel.appendChild(o);}

function filtered(){
  const kw=q.value.trim().toLowerCase(),au=authorSel.value,yr=yearSel.value,mo=monthSel.value,kind=kindSel.value;
  let list=DATA.filter(t=>{
    if(favOnly&&!FAV.has(t.id))return false;
    const hasVideo=t.media.some(m=>m.type!=='photo'),hasPhoto=t.media.some(m=>m.type==='photo');
    if(kind==='media'){if(!t.media.length)return false;}
    else if(kind==='photo'){if(!hasPhoto||hasVideo)return false;}
    else if(kind==='video'){if(!hasVideo)return false;}
    else if(kind==='text'){if(t.media.length)return false;}
    if(au&&t.user!==au)return false;
    if(yr&&t.date.slice(0,4)!==yr)return false;
    if(mo&&t.date.slice(5,7)!==mo)return false;
    if(kw&&!((t.text||'').toLowerCase().includes(kw)||(t.user||'').toLowerCase().includes(kw)||(t.name||'').toLowerCase().includes(kw)))return false;
    return true;
  });
  const s=sortSel.value;
  if(s==='like_new')list.sort((a,b)=>a.rank-b.rank);
  else if(s==='like_old')list.sort((a,b)=>b.rank-a.rank);
  else if(s==='date_new')list.sort((a,b)=>b.date.localeCompare(a.date));
  else if(s==='date_old')list.sort((a,b)=>a.date.localeCompare(b.date));
  else if(s==='user')list.sort((a,b)=>(a.user||'').localeCompare(b.user||''));
  return list;
}

let CUR=[],LBT=null,LBI=0,shown=0;
function openLb(i,startIdx){LBT=CUR[i];LBI=startIdx||0;showLb();lb.classList.add('show');}
function showLb(){
  const lbm=document.getElementById('lbMedia');
  if(!LBT.media.length){
    lbm.innerHTML=`<div class="lbtext">${esc(LBT.text)}</div>`;
    document.getElementById('lbNav').textContent='';
    document.getElementById('lbPrev').style.display='none';
    document.getElementById('lbNext').style.display='none';
  }else{
    const m=LBT.media[LBI];
    lbm.innerHTML = m.type==='photo'?`<img src="${m.path}">`:`<video src="${m.path}" controls autoplay muted></video>`;
    document.getElementById('lbNav').textContent = LBT.media.length>1 ? (LBI+1)+' / '+LBT.media.length : '';
    const multi=LBT.media.length>1;
    document.getElementById('lbPrev').style.display=multi?'block':'none';
    document.getElementById('lbNext').style.display=multi?'block':'none';
  }
  document.getElementById('lbUser').innerHTML = LBT.user
    ? `<a href="https://x.com/${LBT.user}" target="_blank" rel="noopener">${esc(LBT.name)}  @${esc(LBT.user)}</a>`
    : esc(LBT.name);
  document.getElementById('lbText').textContent=LBT.text||'';
  document.getElementById('lbDate').textContent=LBT.date||'';
  document.getElementById('lbLink').innerHTML = LBT.user
    ? `<a href="https://x.com/${LBT.user}/status/${LBT.id}" target="_blank" rel="noopener">元ツイートを開く &#8599;</a>` : '';
}
function lbPrev(e){e&&e.stopPropagation();if(!LBT.media.length)return;LBI=(LBI-1+LBT.media.length)%LBT.media.length;showLb();}
function lbNext(e){e&&e.stopPropagation();if(!LBT.media.length)return;LBI=(LBI+1)%LBT.media.length;showLb();}
function closeLb(){lb.classList.remove('show');document.getElementById('lbMedia').innerHTML='';}
document.getElementById('lbClose').onclick=closeLb;
document.getElementById('lbPrev').onclick=lbPrev;
document.getElementById('lbNext').onclick=lbNext;
lb.onclick=e=>{const tg=e.target;if(tg.tagName==='IMG'||tg.tagName==='VIDEO'||tg.tagName==='A'||tg.classList.contains('lbArrow'))return;closeLb();};

function thumbInner(m){
  return m.type==='photo'?`<img loading="lazy" src="${m.path}">`
    :`<video preload="metadata" muted src="${m.path}"></video><span class="play">&#9654;</span>`;
}
function favStar(t){return `<span class="fav ${FAV.has(t.id)?'on':''}" onclick="toggleFav('${t.id}',event)">&#9733;</span>`;}

const BATCH=80;
function selBox(t){return `<span class="selbox ${SEL.has(t.id)?'on':''}">&#10003;</span>`;}
function tileHTML(t,i){
  const m=t.media[0];const sel=SEL.has(t.id)?' selected':'';
  if(!m) return `<div class="tile ttile${sel}" onclick="tileClick(${i},0,event)"><div class="ttext">${esc(t.text)}</div>${favStar(t)}${selBox(t)}<div class="who">@${esc(t.user)}</div></div>`;
  const cnt=t.media.length>1?`<span class="cnt">${t.media.length}</span>`:'';
  return `<div class="tile${sel}" onclick="tileClick(${i},0,event)">${thumbInner(m)}${cnt}${favStar(t)}${selBox(t)}<div class="who">@${esc(t.user)}</div></div>`;
}
function cardHTML(t,i){
  const m=t.media[0];const sel=SEL.has(t.id)?' selected':'';
  const head = m
    ? `<div class="cimg" onclick="tileClick(${i},0,event)">${thumbInner(m)}${t.media.length>1?`<span class="cnt">${t.media.length}</span>`:''}${favStar(t)}${selBox(t)}</div>`
    : `<div class="ctext" onclick="tileClick(${i},0,event)">${esc(t.text)}${favStar(t)}${selBox(t)}</div>`;
  return `<div class="card${sel}">${head}<div class="meta"><div class="user">${esc(t.name)}<span>@${esc(t.user)}</span></div>
    <div class="text">${esc(t.text||'')}</div><div class="date">${t.date}</div></div></div>`;
}
function appendBatch(){
  const slice=CUR.slice(shown,shown+BATCH);
  if(!slice.length)return;
  const el=mode==='tile'?tilesEl:gridEl;
  let html='';
  for(let k=0;k<slice.length;k++){const i=shown+k;html+=mode==='tile'?tileHTML(slice[k],i):cardHTML(slice[k],i);}
  el.insertAdjacentHTML('beforeend',html);
  shown+=slice.length;
}
function render(){
  CUR=filtered();shown=0;
  tilesEl.innerHTML='';gridEl.innerHTML='';
  if(mode==='tile'){tilesEl.style.display='grid';gridEl.style.display='none';}
  else{tilesEl.style.display='none';gridEl.style.display='grid';}
  if(!CUR.length){
    (mode==='tile'?tilesEl:gridEl).innerHTML='<div class="empty">該当なし</div>';
  }else{
    appendBatch();
    // 画面が埋まらない場合は数バッチ先読み
    let guard=0;
    while(shown<CUR.length && document.body.offsetHeight<=window.innerHeight+200 && guard++<20){appendBatch();}
  }
  countEl.textContent=CUR.length+' 件';
}
window.addEventListener('scroll',()=>{
  if(shown<CUR.length && window.innerHeight+window.scrollY>=document.body.offsetHeight-900){appendBatch();}
});

function setMode(m){mode=m;try{localStorage.setItem('xlikeMode',m);}catch(e){}
  document.querySelectorAll('#modeG button').forEach(b=>b.classList.toggle('on',b.dataset.mode===m));render();}
function setSize(s){size=s;try{localStorage.setItem('xlikeSize',s);}catch(e){}
  document.documentElement.style.setProperty('--thumb',SZ[s][0]);
  document.documentElement.style.setProperty('--cardw',SZ[s][1]);
  document.querySelectorAll('#sizeG button').forEach(b=>b.classList.toggle('on',b.dataset.size===s));}

document.querySelectorAll('#modeG button').forEach(b=>b.onclick=()=>setMode(b.dataset.mode));
document.querySelectorAll('#sizeG button').forEach(b=>b.onclick=()=>setSize(b.dataset.size));
favBtn.onclick=()=>{favOnly=!favOnly;favBtn.classList.toggle('on',favOnly);render();};
q.addEventListener('input',render);
[authorSel,kindSel,sortSel,yearSel,monthSel].forEach(el=>el.addEventListener('change',render));
document.addEventListener('keydown',e=>{
  if(!lb.classList.contains('show'))return;
  if(e.key==='Escape')closeLb();
  else if(e.key==='ArrowLeft'&&LBT&&LBT.media.length>1)lbPrev();
  else if(e.key==='ArrowRight'&&LBT&&LBT.media.length>1)lbNext();
});

const cfgModal=document.getElementById('cfgModal'),progModal=document.getElementById('progModal'),progMsg=document.getElementById('progMsg');
function openCfg(){
  if(window.pywebview&&window.pywebview.api){
    window.pywebview.api.get_config().then(c=>{
      document.getElementById('ck1').value=c.api_key||'';
      document.getElementById('ck2').value=c.api_secret||'';
      document.getElementById('ck3').value=c.access_token||'';
      document.getElementById('ck4').value=c.access_token_secret||'';
    });
  }
  cfgModal.classList.add('show');
}
function closeCfg(){cfgModal.classList.remove('show');}
function saveCfg(){
  window.pywebview.api.save_config(
    document.getElementById('ck1').value.trim(),
    document.getElementById('ck2').value.trim(),
    document.getElementById('ck3').value.trim(),
    document.getElementById('ck4').value.trim()
  ).then(()=>{progMsg.textContent='APIキーを保存しました。';progModal.classList.add('show');
    closeCfg();setTimeout(()=>progModal.classList.remove('show'),1200);});
}
function fetchLikes(){
  progMsg.textContent='いいねを取得しています...\n（件数が多いと数分かかることがあります）';
  progModal.classList.add('show');
  window.pywebview.api.fetch_likes().then(res=>{
    progMsg.textContent='新規 '+res.new+' 件を取得しました。画面を更新します...';
    setTimeout(()=>location.reload(),1000);
  }).catch(e=>{progMsg.textContent='エラー: '+e;
    setTimeout(()=>progModal.classList.remove('show'),3000);});
}
window.addEventListener('pywebviewready',()=>{
  document.getElementById('updBtn').style.display='';
  document.getElementById('cfgBtn').style.display='';
});
document.getElementById('cfgBtn').onclick=openCfg;
document.getElementById('updBtn').onclick=fetchLikes;

const selBtn=document.getElementById('selBtn'),delBtn=document.getElementById('delBtn');
function updateDelBtn(){delBtn.textContent='選択を解除（'+SEL.size+'）';delBtn.style.display=selectMode?'':'none';}
function toggleSelectMode(){
  selectMode=!selectMode;
  document.body.classList.toggle('selmode',selectMode);
  selBtn.classList.toggle('on',selectMode);
  if(!selectMode){SEL.clear();
    document.querySelectorAll('.selbox.on').forEach(b=>b.classList.remove('on'));
    document.querySelectorAll('.selected').forEach(t=>t.classList.remove('selected'));}
  updateDelBtn();
}
function tileClick(i,startIdx,ev){
  if(selectMode){
    const id=CUR[i].id;
    if(SEL.has(id))SEL.delete(id);else SEL.add(id);
    const cont=ev.currentTarget;
    const box=cont.querySelector('.selbox');if(box)box.classList.toggle('on',SEL.has(id));
    const card=cont.closest('.card');
    if(card)card.classList.toggle('selected',SEL.has(id));
    else cont.classList.toggle('selected',SEL.has(id));
    updateDelBtn();
  }else{openLb(i,startIdx);}
}
selBtn.onclick=toggleSelectMode;
delBtn.onclick=()=>{
  if(!SEL.size){return;}
  if(!(window.pywebview&&window.pywebview.api)){alert('解除はアプリ（ウィンドウ）から実行してください。');return;}
  document.getElementById('delMsg').innerHTML='選択した <b>'+SEL.size+'件</b> のいいねをX本体から解除します。<br>手元に保存したデータ（画像など）はどうしますか?';
  document.getElementById('delModal').classList.add('show');
};
function closeDel(){document.getElementById('delModal').classList.remove('show');}
function doUnlike(deleteLocal){
  closeDel();
  if(!(window.pywebview&&window.pywebview.api))return;
  const ids=Array.from(SEL);
  progMsg.textContent='解除しています...（'+ids.length+'件）\nレート制限がある場合は時間がかかります';
  progModal.classList.add('show');
  window.pywebview.api.unlike_tweets(ids,deleteLocal).then(res=>{
    progMsg.textContent='解除完了: 成功 '+res.done+'件 / 失敗 '+res.failed+'件。画面を更新します...';
    setTimeout(()=>location.reload(),1300);
  }).catch(e=>{progMsg.textContent='エラー: '+e;setTimeout(()=>progModal.classList.remove('show'),3000);});
}

setSize(size);setMode(mode);
</script>
</body>
</html>"""


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[エラー] {type(e).__name__}: {e}")
    input("\n（このウィンドウを閉じるには Enter キーを押してください）")
