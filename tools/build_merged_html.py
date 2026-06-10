#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合并「优先翻译推荐单」与「今译核实_最终复核」两张表，生成一个自包含、可筛选/排序的 HTML。

join 键：藏 + 书名 + 题材 + 朝代
- 推荐单为基表（叙事类书的 优先级/知名度/理由）
- 左连接今译核实（今译状态/source_url/复核说明）
- 推荐单中未出现在核实表的书 → 今译状态记为「未核实」（初判未命中今译）
- 仅出现在核实表、不在推荐单的书（极少）也并入，优先级等留空
"""
import csv, json, os

ROOT = os.path.join(os.path.dirname(__file__), "..", "翻译价值分档")
REC = os.path.join(ROOT, "guwen_优先翻译推荐单.csv")
YI  = os.path.join(ROOT, "guwen_今译核实_最终复核.csv")
OUT = os.path.join(ROOT, "guwen_推荐与今译_合并.html")


def load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def key(r):
    return (r["藏"], r["书名"], r["题材"], r["朝代"])


def main():
    rec = load(REC)
    yi = load(YI)
    yi_by_key = {key(r): r for r in yi}

    merged = []
    seen_yi = set()
    for r in rec:
        k = key(r)
        y = yi_by_key.get(k)
        if y:
            seen_yi.add(k)
        merged.append({
            "藏": r["藏"], "书名": r["书名"], "题材": r["题材"],
            "朝代": r["朝代"], "页数": int(r["页数"] or 0),
            "推荐优先级": r["推荐优先级"], "知名度": r["知名度"], "理由": r["理由"],
            "今译状态": y["今译状态"] if y else "未核实",
            "source_url": y.get("source_url", "") if y else "",
            "复核说明": y.get("复核说明", "") if y else "",
        })
    # 仅在核实表、不在推荐单中的书
    for r in yi:
        if key(r) in seen_yi:
            continue
        merged.append({
            "藏": r["藏"], "书名": r["书名"], "题材": r["题材"],
            "朝代": r["朝代"], "页数": int(r["页数"] or 0),
            "推荐优先级": "", "知名度": "", "理由": "",
            "今译状态": r["今译状态"], "source_url": r.get("source_url", ""),
            "复核说明": r.get("复核说明", ""),
        })

    # 排序：优先级(高>中>低>空) → 知名度(高>中>低) → 今译状态(无在前=待翻译缺口) → 页数
    prio_rank = {"高": 0, "中": 1, "低": 2, "": 3}
    fame_rank = {"高": 0, "中": 1, "低": 2, "": 3}
    yi_rank = {"无": 0, "未核实": 1, "不确定": 2, "初判有_复核驳回": 3,
               "很可能有_反爬待核": 4, "确认有今译": 5,
               "浅近文言_基本可读_待定": 6, "本身白话_无需今译": 7}
    merged.sort(key=lambda r: (
        prio_rank.get(r["推荐优先级"], 3),
        fame_rank.get(r["知名度"], 3),
        yi_rank.get(r["今译状态"], 9),
        -r["页数"],
    ))

    html = TEMPLATE.replace("__DATA__", json.dumps(merged, ensure_ascii=False))
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(html)
    # 统计
    gap = sum(1 for r in merged if r["推荐优先级"] == "高" and r["今译状态"] in ("无", "未核实"))
    print(f"合并 {len(merged)} 条 -> {OUT}")
    print(f"高优先且无今译（翻译缺口）：{gap} 部")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>古籍优先翻译推荐 × 今译核实 合并表</title>
<style>
  :root{
    --bg:#f6f4ef; --panel:#fffdf8; --ink:#2a2722; --muted:#8a857c;
    --line:#e4ddd0; --accent:#b5563b; --accent2:#3b6b5e;
  }
  *{box-sizing:border-box}
  body{margin:0;font-family:-apple-system,"PingFang SC","Microsoft YaHei",Segoe UI,sans-serif;
    background:var(--bg);color:var(--ink);font-size:14px;line-height:1.5}
  header{padding:18px 22px 12px;border-bottom:1px solid var(--line);background:var(--panel);
    position:sticky;top:0;z-index:20}
  h1{margin:0 0 4px;font-size:18px;font-weight:700}
  .sub{color:var(--muted);font-size:12.5px}
  .stats{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
  .pill{background:#fff;border:1px solid var(--line);border-radius:20px;padding:3px 11px;font-size:12px}
  .pill b{color:var(--accent)}
  .controls{display:flex;flex-wrap:wrap;gap:8px;align-items:center;padding:10px 22px;
    background:var(--panel);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:19}
  input[type=search],select{font:inherit;padding:6px 9px;border:1px solid var(--line);
    border-radius:7px;background:#fff;color:var(--ink)}
  input[type=search]{min-width:220px}
  .controls label{font-size:12px;color:var(--muted)}
  button.reset{background:var(--accent);color:#fff;border:none;border-radius:7px;
    padding:6px 12px;cursor:pointer;font:inherit}
  .wrap{padding:0 0 60px}
  table{border-collapse:collapse;width:100%;background:var(--panel)}
  th,td{padding:7px 10px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
  th{position:sticky;top:0;background:#efe9dd;cursor:pointer;white-space:nowrap;font-size:12.5px;
    user-select:none;z-index:5}
  th.sorted-asc::after{content:" ▲";color:var(--accent)}
  th.sorted-desc::after{content:" ▼";color:var(--accent)}
  tbody tr:hover{background:#fbf7ee}
  td.title{font-weight:600;white-space:nowrap}
  td.reason,td.note{max-width:280px;color:#5c574e;font-size:13px}
  a{color:var(--accent2);text-decoration:none}
  a:hover{text-decoration:underline}
  .tag{display:inline-block;padding:1px 8px;border-radius:11px;font-size:11.5px;white-space:nowrap}
  .p-高{background:#f4d9d0;color:#9c3a22}.p-中{background:#f1e7cf;color:#8a6d24}
  .p-低{background:#e7e3da;color:#6d685e}
  .y-无{background:#d9ecd9;color:#2c6b3c}.y-未核实{background:#eee9dd;color:#7a7568}
  .y-确认有今译{background:#f3d6d0;color:#9c3a22}
  .y-很可能有_反爬待核{background:#f1e3cf;color:#8a6324}
  .y-初判有_复核驳回{background:#e2ecf3;color:#356074}
  .y-不确定{background:#ece2f0;color:#6a4d7a}
  .y-本身白话_无需今译{background:#cfe8e4;color:#1f6b5e}
  .y-浅近文言_基本可读_待定{background:#e3ecd5;color:#5a6b30}
  .gap{box-shadow:inset 3px 0 0 var(--accent)}
  .empty{padding:40px;text-align:center;color:var(--muted)}
  .legend{font-size:11.5px;color:var(--muted);padding:6px 22px}
</style>
</head>
<body>
<header>
  <h1>古籍优先翻译推荐 × 今译核实 合并表</h1>
  <div class="sub">「优先翻译推荐单」（优先级/知名度/理由）左连接「今译核实_最终复核」（是否已有现代白话译本）。左侧红条 = <b>高优先且尚无今译</b>，即最值得翻译的空白。</div>
  <div class="stats" id="stats"></div>
</header>
<div class="controls">
  <input type="search" id="q" placeholder="搜索 书名 / 理由 / 复核说明…">
  <label>藏 <select id="f-藏"></select></label>
  <label>题材 <select id="f-题材"></select></label>
  <label>朝代 <select id="f-朝代"></select></label>
  <label>优先级 <select id="f-推荐优先级"></select></label>
  <label>知名度 <select id="f-知名度"></select></label>
  <label>今译状态 <select id="f-今译状态"></select></label>
  <button class="reset" id="reset">重置</button>
  <span id="count" class="sub"></span>
</div>
<div class="legend">今译状态：<b>无</b>=搜不到白话今译 · <b>未核实</b>=初判未命中(多半也无) · <b>确认有今译</b>=已验证有译本 · <b>很可能有_反爬待核</b> · <b>初判有_复核驳回</b> · <b>不确定</b> · <b>本身白话_无需今译</b>=原著即白话、现代人可读 · <b>浅近文言_基本可读_待定</b>=半文半白略费力</div>
<div class="wrap">
  <table id="tbl">
    <thead><tr>
      <th data-k="藏">藏</th>
      <th data-k="书名">书名</th>
      <th data-k="题材">题材</th>
      <th data-k="朝代">朝代</th>
      <th data-k="页数" data-num="1">页数</th>
      <th data-k="推荐优先级">优先级</th>
      <th data-k="知名度">知名度</th>
      <th data-k="今译状态">今译状态</th>
      <th data-k="理由">理由</th>
      <th data-k="复核说明">今译说明 / 链接</th>
    </tr></thead>
    <tbody id="tb"></tbody>
  </table>
  <div class="empty" id="empty" style="display:none">无匹配结果</div>
</div>
<script>
const DATA = __DATA__;
const cols = ["藏","题材","朝代","推荐优先级","知名度","今译状态"];
const order = {推荐优先级:["高","中","低",""], 知名度:["高","中","低",""],
  今译状态:["无","未核实","不确定","初判有_复核驳回","很可能有_反爬待核","确认有今译","浅近文言_基本可读_待定","本身白话_无需今译"]};
function uniq(k){
  const s=[...new Set(DATA.map(r=>r[k]))];
  if(order[k]) s.sort((a,b)=>order[k].indexOf(a)-order[k].indexOf(b));
  else s.sort((a,b)=>(''+a).localeCompare(b,'zh'));
  return s;
}
cols.forEach(k=>{
  const sel=document.getElementById('f-'+k);
  sel.innerHTML='<option value="">全部</option>'+uniq(k).map(v=>`<option>${v||'—'}</option>`).join('');
});
let sortK=null,sortDir=1;
function esc(s){return (s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function render(){
  const q=document.getElementById('q').value.trim().toLowerCase();
  const filt={}; cols.forEach(k=>filt[k]=document.getElementById('f-'+k).value);
  let rows=DATA.filter(r=>{
    for(const k of cols){ if(filt[k] && (r[k]||'—')!==filt[k]) return false; }
    if(q){const hay=(r.书名+' '+r.理由+' '+r.复核说明).toLowerCase(); if(!hay.includes(q))return false;}
    return true;
  });
  if(sortK){
    const num=sortK==='页数';
    rows=rows.slice().sort((a,a2)=>{
      let x=a[sortK],y=a2[sortK];
      if(order[sortK]){x=order[sortK].indexOf(x);y=order[sortK].indexOf(y);}
      else if(num){x=+x;y=+y;}
      else {x=''+x;y=''+y;return sortDir*x.localeCompare(y,'zh');}
      return sortDir*(x-y);
    });
  }
  const tb=document.getElementById('tb');
  tb.innerHTML=rows.map(r=>{
    const gap=(r.推荐优先级==='高' && (r.今译状态==='无'||r.今译状态==='未核实'))?' gap':'';
    const link=r.source_url?` <a href="${esc(r.source_url)}" target="_blank" rel="noopener">链接↗</a>`:'';
    const note=esc(r.复核说明)+link;
    return `<tr class="${gap}">
      <td>${esc(r.藏)}</td>
      <td class="title">${esc(r.书名)}</td>
      <td>${esc(r.题材)}</td>
      <td>${esc(r.朝代)}</td>
      <td>${r.页数}</td>
      <td>${r.推荐优先级?`<span class="tag p-${r.推荐优先级}">${r.推荐优先级}</span>`:'—'}</td>
      <td>${r.知名度||'—'}</td>
      <td><span class="tag y-${r.今译状态}">${r.今译状态}</span></td>
      <td class="reason">${esc(r.理由)}</td>
      <td class="note">${note||'—'}</td>
    </tr>`;
  }).join('');
  document.getElementById('empty').style.display=rows.length?'none':'block';
  document.getElementById('count').textContent=`显示 ${rows.length} / ${DATA.length} 部`;
}
function stats(){
  const n=DATA.length;
  const gap=DATA.filter(r=>r.推荐优先级==='高'&&(r.今译状态==='无'||r.今译状态==='未核实')).length;
  const hi=DATA.filter(r=>r.推荐优先级==='高').length;
  const has=DATA.filter(r=>r.今译状态==='确认有今译').length;
  document.getElementById('stats').innerHTML=
    `<span class="pill">合并 <b>${n}</b> 部</span>`+
    `<span class="pill">高优先 <b>${hi}</b></span>`+
    `<span class="pill">高优先·待翻译缺口 <b>${gap}</b></span>`+
    `<span class="pill">已确认有今译 <b>${has}</b></span>`;
}
document.querySelectorAll('#tbl th').forEach(th=>{
  th.addEventListener('click',()=>{
    const k=th.dataset.k;
    if(sortK===k) sortDir*=-1; else {sortK=k;sortDir=1;}
    document.querySelectorAll('#tbl th').forEach(t=>t.classList.remove('sorted-asc','sorted-desc'));
    th.classList.add(sortDir>0?'sorted-asc':'sorted-desc');
    render();
  });
});
document.getElementById('q').addEventListener('input',render);
cols.forEach(k=>document.getElementById('f-'+k).addEventListener('change',render));
document.getElementById('reset').addEventListener('click',()=>{
  document.getElementById('q').value='';
  cols.forEach(k=>document.getElementById('f-'+k).value='');
  sortK=null;document.querySelectorAll('#tbl th').forEach(t=>t.classList.remove('sorted-asc','sorted-desc'));
  render();
});
stats();render();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
