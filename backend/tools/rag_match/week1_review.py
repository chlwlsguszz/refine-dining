"""Render an offline, unlabelled human-review packet. No model or DB access."""

import json


FIELDS = (
    "foodCd", "foodNm", "srcCd", "srcNm", "lv4Cd", "lv4Nm", "lv5Cd", "lv5Nm",
    "lv6Cd", "lv6Nm", "lv7Cd", "lv7Nm", "basis", "region", "country", "month",
    "imported", "production", "referenceDate",
)


def _text(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Review packet has a missing identifier or food name.")
    return value


def _record(value):
    _text(value["foodCd"])
    _text(value["foodNm"])
    record = {key: value.get(key) for key in FIELDS}
    if "rawFields" in value:
        if not isinstance(value["rawFields"], dict):
            raise ValueError(f"Invalid rawFields for {value['foodCd']}")
        record["rawFields"] = value["rawFields"]
    return record


def render_review_page(packet):
    """Build a portable HTML file, embedding only raw fields relevant to review."""
    catalog = [_record(row) for row in packet["catalog"]]
    codes = {row["foodCd"] for row in catalog}
    if not catalog or len(codes) != len(catalog):
        raise ValueError("Raw catalogue must be nonempty with unique food codes.")
    cases = []
    seen = set()
    for case in packet["cases"]:
        target = _record(case["target"])
        code = target["foodCd"]
        ids = case["candidateCds"]
        if (code in seen or code in codes or not isinstance(ids, list)
                or not set(ids).issubset(codes) or len(ids) != len(set(ids))):
            raise ValueError(f"Invalid review target or initial candidates: {code}")
        seen.add(code)
        cases.append({"target": target, "candidateCds": ids, "family": case["family"], "stratum": case["stratum"]})
    if not cases:
        raise ValueError("Empty review packet.")
    data = {"snapshotId": _text(packet["snapshotId"]), "packetId": _text(packet["packetId"]),
            "cases": cases, "catalog": catalog}
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    # Even a literal closing script tag in a source record stays inside the JSON.
    return PAGE.replace("__REVIEW_PACKET__", payload.replace("<", "\\u003c"))


PAGE = r'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>식품 원문 검수 · Refine Dining</title>
<style>
:root{color-scheme:light;--paper:#fbfcfa;--ink:#20302b;--soft:#51645c;--line:#cdd8d0;--green:#16563d}
*{box-sizing:border-box} body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.6 "Malgun Gothic","Apple SD Gothic Neo",sans-serif}
main{max-width:1220px;margin:0 auto;padding:32px 24px 60px}h1,h2,h3,p{margin:0 0 .4em}
h1{font-size:clamp(25px,4vw,37px);letter-spacing:-.04em}h2{font-size:19px}h3{font-size:15px}
header,.nav,.columns{margin-bottom:20px}.caption,small,code{color:var(--soft)}code{font-size:.88em;overflow-wrap:anywhere}
.tools,.controls,.pager{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
button,select,input,textarea{color:var(--ink);background:white;border:1px solid #a1b1a6;border-radius:4px;font:inherit;padding:5px 9px}
button{cursor:pointer}button.primary{background:var(--green);color:white;border-color:var(--green)}button:disabled{opacity:.45;cursor:default}
button:focus-visible,summary:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible{outline:3px solid #38836c;outline-offset:2px}
.nav{border-block:1px solid var(--line);padding:12px 0}.nav select{max-width:100%;min-width:min(30em,100%)}
.columns{display:grid;grid-template-columns:minmax(0,.83fr) minmax(0,1.38fr);gap:22px;align-items:start}
.left{position:sticky;top:12px;background:#eef4ef;padding:16px;border-radius:5px;max-height:calc(100vh - 24px);overflow:auto}
.right{min-width:0}details>summary{cursor:pointer;color:var(--green);font-weight:600}
.candidate{padding:10px 0;border-bottom:1px solid var(--line);overflow-wrap:anywhere}
.candidate-head{display:flex;gap:8px;align-items:start;justify-content:space-between}.candidate-head>div{min-width:0}
.candidate-head select{font-size:.88rem;flex-shrink:0}.source-name{overflow-wrap:anywhere;font-weight:700;font-size:1.02rem;margin:0}
.meta{font-size:.86rem;margin-top:4px}.meta dl{margin:4px 0}.meta dl>div{display:grid;grid-template-columns:5.5em 1fr;gap:8px}
.meta dt{color:var(--soft);overflow-wrap:anywhere}.meta dd{margin:0;overflow-wrap:anywhere}
#annotation{border-top:1px solid var(--line);padding-top:14px;margin-top:14px}.field{display:block;margin:9px 0}
.field>span{display:block;font-weight:700}textarea{width:100%;min-height:75px;resize:vertical}
.full{margin-top:18px;border:1px solid var(--line);border-radius:4px;padding:10px}.full input{width:100%}
#saveState,#notice{font-size:.88rem;overflow-wrap:anywhere}#notice{color:#743e13;min-height:1.4em}
.guide{margin:9px 0}.guide p{margin:5px 0;color:var(--soft)}[hidden]{display:none!important}
@media(max-width:780px){main{padding:18px 12px 40px}.columns{grid-template-columns:1fr}.left{position:static;max-height:none}.nav .controls{align-items:stretch}}
</style></head><body><main>
<header><h1>식품 원문 검수</h1>
<p class="caption">가공식품에 대응하는 생것을 찾고 판단 근거를 기록하세요. 타당한 생것은 여러 개 선택할 수 있습니다.</p>
<div class="tools"><button type="button" id="export">검수 JSON 내보내기</button>
<button type="button" id="import">검수 JSON 불러오기</button><input id="file" type="file" accept="application/json,.json" hidden>
<span id="saveState" aria-live="polite"></span></div>
<details class="guide"><summary>판정 기준과 저장 방법</summary>
<p>직접 비교는 품목·부위·기준량과 관측 조건까지 대응하는 경우입니다. 참고 비교는 같은 재료를 비교할 근거가 있고 산지·품종·월 등 차이를 명시할 수 있는 경우입니다.</p>
<p>원본을 확인한 뒤 적절한 생것이 없으면 ‘비교 불가’, 추가 자료나 판단이 필요하면 ‘판단 보류’를 고르세요. 전체 생것에서 후보를 직접 찾아 추가할 수도 있습니다.</p>
<p>브라우저는 작성 내용을 이 기기에 임시 저장합니다. 검수한 항목은 ‘이 건 확정’을 누르세요. 작업을 마칠 때 JSON을 내보내면 내용과 확정 여부를 보관하거나 다른 기기에서 이어볼 수 있습니다.</p>
<p id="snapshot"></p></details></header>
<nav class="nav" aria-label="검수 대상"><label for="cases"><b>검수할 식품</b></label>
<div class="controls"><select id="cases"></select><button type="button" id="prev">이전</button>
<button type="button" id="next">다음</button><span id="progress"></span></div></nav>
<div class="columns"><section class="left"><h2>대상 식품 원문</h2><div id="target"></div>
<div id="annotation"><h2>내 판정</h2><label class="field"><span>판정 상태</span><select id="status">
<option value="unreviewed">미검수</option><option value="matched">비교 후보 선택</option>
<option value="no_match">비교 불가</option><option value="deferred">판단 보류</option>
</select></label>
<label class="field"><span>판단 근거</span><textarea id="reason" placeholder="선택한 후보별로 일치하는 점과 차이를 적거나, 선택하기 어려운 이유를 적으세요."></textarea></label>
<div class="tools"><button type="button" id="confirm" class="primary">이 건 확정</button><span id="rowState"></span></div>
<p id="notice" aria-live="polite"></p></div></section>
<section class="right"><h2 id="poolTitle">생것 후보 원문</h2><p class="caption">제시된 후보를 검토하고 적절한 항목의 판정을 선택하세요.</p>
<div id="pool"></div><details class="full" id="all"><summary id="allTitle">전체 생것에서 추가 검색</summary>
<label class="field"><span>이름·식품코드·분류·지역 검색</span><input type="search" id="query" autocomplete="off"></label>
<p class="caption" id="hits" aria-live="polite"></p><div id="results"></div>
<div class="pager" id="pager"><button type="button" id="pagePrev">이전 결과</button><button type="button" id="pageNext">다음 결과</button></div>
</details></section></div></main>
<script type="application/json" id="source">__REVIEW_PACKET__</script>
<script>
"use strict";
const packet=JSON.parse(document.getElementById("source").textContent);
const catalog=new Map(packet.catalog.map(r=>[r.foodCd,r]));
const ids=packet.cases.map(c=>c.target.foodCd);
const storageKey="refine-dining.week1.review.v1."+packet.snapshotId+"."+packet.packetId;
const statuses={unreviewed:"미검수",matched:"비교 후보 선택",no_match:"비교 불가",deferred:"판단 보류"};
const fields=[["출처","srcNm"],["대표식품","lv4Nm"],["중분류","lv5Nm"],["소분류·부위","lv6Nm"],["상태","lv7Nm"],
 ["기준량","basis"],["원산지","country"],["원산지역","region"],["생산·채취·포획월","month"],
 ["수입 여부","imported"],["자료 생성 방법","production"],["자료 기준일","referenceDate"]];
const byId=id=>document.getElementById(id);
const make=(tag,text)=>{const el=document.createElement(tag);if(text!==undefined)el.textContent=text;return el};
const blank=targetCd=>({targetCd,status:"unreviewed",selections:[],reason:"",confirmed:false});
let reviews=ids.map(blank), at=0, page=0, lastStored=null;
const pageSize=20;
const normal=value=>String(value??"").normalize("NFKC").toLocaleLowerCase().replaceAll("_"," ");
const names=new Map([...catalog.values()].map(r=>[r.foodCd,normal([r.foodCd,r.foodNm,r.lv4Nm,r.lv5Nm,r.lv6Nm,r.country,r.region].join(" "))]));
function signature(){
 return {schemaVersion:1,snapshotId:packet.snapshotId,packetId:packet.packetId,reviews};
}
function stateLabel(row){
 if(row.confirmed)return statuses[row.status]+" · 확정";
 return row.status==="unreviewed"&&!row.reason.trim()?"미검수":"작성 중";
}
function incomplete(row){
 if(row.status==="unreviewed")return "판정 상태를 골라 주세요.";
 if(row.status==="matched"&&!row.selections.length)return "비교 가능한 생것과 직접·참고 판정을 선택하세요.";
 if(row.status!=="matched"&&row.selections.length)return "현재 상태에 선택한 후보가 남아 있습니다.";
 return row.reason.trim()?"":"판단 근거를 입력하세요.";
}
function validateFile(data){
 if(data?.schemaVersion!==1||data.snapshotId!==packet.snapshotId||data.packetId!==packet.packetId)throw Error("다른 스냅샷 또는 검수 묶음입니다.");
 if(!Array.isArray(data.reviews)||data.reviews.length!==ids.length)throw Error("검수 대상 수가 맞지 않습니다.");
 const found=new Map();
 for(const item of data.reviews){
  if(!item||!ids.includes(item.targetCd)||found.has(item.targetCd)||typeof item.status!=="string"||!Object.hasOwn(statuses,item.status)
    ||typeof item.confirmed!=="boolean"||typeof item.reason!=="string"||!Array.isArray(item.selections))throw Error("대상 코드 또는 판정 필드가 올바르지 않습니다.");
  const seen=new Set(), choices=[];
  for(const choice of item.selections){
   if(!choice||!catalog.has(choice.foodCd)||seen.has(choice.foodCd)||!["직접 비교","참고 비교"].includes(choice.verdict))throw Error("존재하지 않거나 중복된 생것 후보 또는 판정입니다.");
   seen.add(choice.foodCd);choices.push({foodCd:choice.foodCd,verdict:choice.verdict});
  }
  const row={targetCd:item.targetCd,status:item.status,selections:choices,reason:item.reason,confirmed:item.confirmed};
  if((row.status!=="matched"&&choices.length)||(row.confirmed&&incomplete(row)))throw Error("확정 여부와 판정 내용이 맞지 않습니다.");
  found.set(row.targetCd,row);
 }
 return ids.map(code=>found.get(code));
}
function persist(){
 try{
  const current=localStorage.getItem(storageKey);
  if(current!==lastStored){byId("saveState").textContent="다른 창의 저장본이 있습니다. 현재 작업은 JSON으로 내보내세요.";return}
  const text=JSON.stringify(signature());localStorage.setItem(storageKey,text);lastStored=text;
  byId("saveState").textContent="이 브라우저에 저장됨";
 }catch{byId("saveState").textContent="브라우저 저장을 사용할 수 없습니다. JSON으로 내보내세요."}
}
function refreshNav(){
 const options=reviews.map((row,i)=>new Option((i+1)+". "+packet.cases[i].target.foodNm+" · "+stateLabel(row),String(i)));
 byId("cases").replaceChildren(...options);byId("cases").value=String(at);
 byId("prev").disabled=at===0;byId("next").disabled=at===ids.length-1;
 byId("progress").textContent="확정 "+reviews.filter(r=>r.confirmed).length+" / "+ids.length+"건";
 byId("rowState").textContent=stateLabel(reviews[at]);byId("confirm").disabled=reviews[at].confirmed;
}
function sourceMeta(record,opened){
 const details=make("details");details.className="meta";details.open=opened;
 details.append(make("summary","분류·출처·관측 조건"));
 const dl=make("dl");for(const [label,key] of fields){const pair=make("div"),raw=record[key];
   pair.append(make("dt",label),make("dd",raw===null||raw===undefined||String(raw).trim()===""?"미기재":String(raw)));dl.append(pair)}
 details.append(dl);
 const wrapper=make("div");wrapper.append(details);
 if(record.rawFields){
  const raw=make("details"),all=make("dl");raw.className="meta";raw.append(make("summary","DB 원본 행 전체"));
  const note=make("p","동기화 시 숫자 파싱을 거친 DB 저장값입니다. 공백·미측정이 0으로 적재됐을 수 있습니다.");note.className="caption";
  for(const [key,value] of Object.entries(record.rawFields)){
   const pair=make("div");
   pair.append(make("dt",key),make("dd",value===null?"NULL":value===""?"빈 문자열":String(value)));
   all.append(pair);
  }
  raw.append(note,all);wrapper.append(raw);
 }
 return wrapper;
}
function candidate(record){
 const box=make("article");box.className="candidate";const head=make("div");head.className="candidate-head";
 const identification=make("div"),name=make("p",record.foodNm);name.className="source-name";
 identification.append(name,make("code",record.foodCd),make("small"," · "+(record.basis||"기준량 미기재")));
 const select=make("select");select.setAttribute("aria-label",record.foodNm+" ("+record.foodCd+") 판정");
 select.dataset.candidate=record.foodCd;
 for(const [label,value] of [["선택 안 함",""],["직접 비교","직접 비교"],["참고 비교","참고 비교"]])select.add(new Option(label,value));
 select.value=reviews[at].selections.find(v=>v.foodCd===record.foodCd)?.verdict??"";
 select.addEventListener("change",()=>choose(record.foodCd,select.value));
 head.append(identification,select);box.append(head,sourceMeta(record,false));return box;
}
function showPool(){
 const initial=packet.cases[at].candidateCds, codes=[...new Set([...initial,...reviews[at].selections.map(s=>s.foodCd)])];
 byId("poolTitle").textContent="생것 후보 원문 · "+codes.length+"건";
 byId("pool").replaceChildren(...codes.map(code=>candidate(catalog.get(code))));
 if(!codes.length)byId("pool").append(make("p","전체 생것 검색에서 후보를 확인하세요."));
}
function showSearch(){
 const words=normal(byId("query").value).trim().split(/\s+/).filter(Boolean);
 const hits=words.length?[...names].filter(([,text])=>words.every(w=>text.includes(w))).map(([code])=>code):[];
 page=Math.min(page,Math.max(0,Math.ceil(hits.length/pageSize)-1));
 byId("results").replaceChildren(...hits.slice(page*pageSize,(page+1)*pageSize).map(code=>candidate(catalog.get(code))));
 byId("hits").textContent=words.length?(hits.length+"건"+(hits.length?" · "+(page*pageSize+1)+"–"+Math.min((page+1)*pageSize,hits.length)+"번째":"")):"전체 원본에서 찾을 검색어를 입력하세요.";
 byId("pager").hidden=hits.length<=pageSize;byId("pagePrev").disabled=page===0;byId("pageNext").disabled=(page+1)*pageSize>=hits.length;
}
function choose(code,value){
 const row=reviews[at], wasIncluded=packet.cases[at].candidateCds.includes(code)||row.selections.some(s=>s.foodCd===code);
 row.selections=row.selections.filter(s=>s.foodCd!==code);
 if(value){row.selections.push({foodCd:code,verdict:value});row.status="matched"}
 row.confirmed=false;byId("status").value=row.status;byId("notice").textContent="";
 if(!wasIncluded||(!value&&!packet.cases[at].candidateCds.includes(code)))showPool();
 for(const select of document.querySelectorAll("[data-candidate]"))if(select.dataset.candidate===code)select.value=value;
 persist();refreshNav();
}
function showCase(){
 const item=packet.cases[at], row=reviews[at], target=item.target;
 const heading=make("p",target.foodNm);heading.className="source-name";
 const group=make("p",(target.lv4Nm||item.family)+" · "+item.stratum);group.className="caption";
 byId("target").replaceChildren(heading,make("code",target.foodCd),group,sourceMeta(target,true));
 byId("status").value=row.status;byId("reason").value=row.reason;byId("notice").textContent="";
 byId("all").open=false;byId("query").value="";page=0;showPool();showSearch();refreshNav();
}
function move(i){at=Math.max(0,Math.min(i,ids.length-1));showCase()}
byId("cases").onchange=e=>move(Number(e.target.value));byId("prev").onclick=()=>move(at-1);byId("next").onclick=()=>move(at+1);
byId("query").oninput=()=>{page=0;showSearch()};byId("pagePrev").onclick=()=>{page--;showSearch()};byId("pageNext").onclick=()=>{page++;showSearch()};
byId("status").onchange=e=>{
 const row=reviews[at],value=e.target.value;
 if(value!=="matched"&&row.selections.length&&!window.confirm("선택한 후보를 해제하고 판정 상태를 바꿀까요?")){e.target.value=row.status;return}
 if(value!=="matched")row.selections=[];
 row.status=value;row.confirmed=false;byId("notice").textContent="";showPool();showSearch();persist();refreshNav();
};
byId("reason").oninput=e=>{reviews[at].reason=e.target.value;reviews[at].confirmed=false;byId("notice").textContent="";persist();refreshNav()};
byId("confirm").onclick=()=>{const issue=incomplete(reviews[at]);byId("notice").textContent=issue;if(issue)return;reviews[at].confirmed=true;persist();refreshNav()};
byId("export").onclick=()=>{
 const blob=new Blob([JSON.stringify(signature(),null,2)+"\n"],{type:"application/json;charset=utf-8"});
 const url=URL.createObjectURL(blob),a=make("a");a.href=url;a.download="food-review-"+packet.packetId.replace(/[^a-z0-9_-]/gi,"").slice(0,24)+".json";
 document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),2000);
};
byId("import").onclick=()=>byId("file").click();
byId("file").onchange=async e=>{
 const file=e.target.files[0];if(!file)return;
 try{
  const incoming=validateFile(JSON.parse((await file.text()).replace(/^\uFEFF/,"")));
  if(reviews.some(r=>r.confirmed||r.status!=="unreviewed"||r.reason)&&!window.confirm("현재 작업을 불러온 JSON의 검수 내용으로 교체할까요?"))return;
  reviews=incoming;persist();showCase();byId("notice").textContent="검수 내용을 불러왔습니다.";
 }catch(err){byId("notice").textContent="불러오기 실패 · "+err.message}
 finally{e.target.value=""}
};
try{lastStored=localStorage.getItem(storageKey);if(lastStored){reviews=validateFile(JSON.parse(lastStored));byId("saveState").textContent="저장된 검수 내용 복원됨"}}
catch{byId("saveState").textContent="저장본을 읽지 못했습니다. 필요한 경우 검수 JSON을 불러오세요."}
byId("snapshot").textContent="스냅샷 "+packet.snapshotId+" · 검수 묶음 "+packet.packetId;
byId("allTitle").textContent="전체 생것 "+catalog.size.toLocaleString("ko-KR")+"건에서 추가 검색";
showCase();
</script></body></html>'''
