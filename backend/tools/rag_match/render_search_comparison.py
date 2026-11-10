"""Render the name-only retrieval comparison as a self-contained Korean HTML file."""

import argparse
from html import escape
import json
from pathlib import Path


METHODS = (("lexical", "키워드"), ("dense", "벡터"), ("hybrid", "혼합"))
STATUS = {"conflict": "부위 충돌", "same_part": "같은 부위", "review": "판단 보류"}


def table(headers, rows):
    head = "".join(f'<th scope="col">{escape(h)}</th>' for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    return f'<div class="scroll"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def rank_text(result):
    low, high = result["rankBest"], result["rankWorst"]
    if high is None:
        return "미검색"
    return f"{low}위" if low == high else f"{low}–{high}위 (동점)"


def food(name, code):
    return f'<span>{escape(name)}</span><small>{escape(code)}</small>'


def top_foods(result):
    tops = result["firstPlaceCandidates"]
    return "<br>".join(food(c["foodNm"], c["foodCd"]) for c in tops) or "미검색"


def change_tags(methods):
    changes = []
    for k in (1, 5):
        before = methods["lexical"]["rankWorst"]
        after = methods["dense"]["rankWorst"]
        before_hit = before is not None and before <= k
        after_hit = after is not None and after <= k
        if before_hit != after_hit:
            changes.append(("gain" if after_hit else "loss") + str(k))
    return changes


def reference_html(row):
    methods = row["methods"]
    ranks = "".join(f"<span>{label} {escape(rank_text(methods[key]))}</span>" for key, label in METHODS)
    method_rows = [[label, escape(rank_text(methods[key])), top_foods(methods[key])] for key, label in METHODS]
    terms = " ".join([row["targetName"], row["rawName"], row["targetCd"], row["rawCd"]])
    return (
        f'<details class="case" data-search="{escape(terms, quote=True)}" '
        f'data-changes="{" ".join(change_tags(methods))}">'
        f'<summary><strong>{escape(row["targetName"])}</strong><span class="ranks">{ranks}</span></summary>'
        '<div class="case-body"><div class="pair">'
        f'<div><b>검색한 식품</b>{food(row["targetName"], row["targetCd"])}</div>'
        f'<div><b>찾아야 할 생것</b>{food(row["rawName"], row["rawCd"])}</div></div>'
        + table(["검색 방식", "기준 생것 순위", "실제 1위 생것 원문"], method_rows)
        + f'<p class="caption">{escape(row["source"])} · {escape(row["basis"])}</p></div></details>'
    )


def guard_html(checks):
    cases = checks["cases"]
    metrics = checks["guardMetrics"]
    rows = []
    for row in cases:
        ranks = [escape(rank_text(row["methods"][key])) for key, _ in METHODS]
        rows.append([food(row["targetName"], row["targetCd"]), food(row["rawName"], row["rawCd"]),
                     *ranks, STATUS[row["guardStatus"]] + "<small>" + escape(row["sourceRationale"]) + "</small>"])
    by_method = checks["conflictPairsInTopKBeforeGuard"]
    counts = " · ".join(f'{label} {by_method[key]["5"]}쌍' for key, label in METHODS)
    return (
        '<section><h2>부위가 다른 후보는 몇 위에 나왔나?</h2>'
        f'<p>먼저 부위 충돌 {metrics["conflictPairs"]}쌍에서 후보가 상위 5개에 든 횟수를 셌습니다. {counts}.</p>'
        f'<p>별도의 부위 검사는 충돌 {metrics["detectedConflicts"]}/{metrics["conflictPairs"]}쌍을 표시했습니다. '
        f'같은 부위 대조 {metrics["controlPairs"]}쌍 중 잘못 표시한 사례는 {metrics["falseFlags"]}쌍이며, '
        f'불명확한 {metrics["uncertainPairs"]}쌍 중 {metrics["uncertainDeferred"]}쌍을 보류했습니다.</p>'
        f'<details class="guard"><summary>부위 검사 {len(cases)}쌍의 원문과 검사 전 검색 순위</summary>'
        + table(["가공식품", "확인한 생것", "키워드", "벡터", "혼합", "부위 검사 결과"], rows)
        + "</details></section>"
    )


STYLE = """
:root{color-scheme:light;--ink:#172f2b;--sub:#4e645d;--edge:#cad6ce;--accent:#19624a}
*{box-sizing:border-box}body{margin:0;color:var(--ink);background:#f7f9f6;font:16px/1.55 "Malgun Gothic","Apple SD Gothic Neo",sans-serif}
main{max-width:1060px;margin:auto;padding:34px 24px 64px}header,section{margin:0 0 30px}
h1,h2,p{margin:0 0 9px}h1{font-size:clamp(27px,4vw,38px);letter-spacing:-.055em}h2{font-size:21px;letter-spacing:-.03em}
small,.caption{display:block;color:var(--sub);font-size:.83rem;overflow-wrap:anywhere}.caption{margin-top:6px}
strong{font-weight:700}.scroll{overflow-x:auto;background:#fff}table{border-collapse:collapse;width:100%;font-size:.9rem}
th,td{border-bottom:1px solid var(--edge);padding:8px;text-align:left;vertical-align:top;overflow-wrap:anywhere}
th{background:#e8efea;color:#354f43;white-space:nowrap}td small{font-size:.75rem}
.score{max-width:620px;margin-top:12px}.score td:not(:first-child){font-variant-numeric:tabular-nums}
.tools,.pager{display:flex;align-items:end;gap:8px 14px;flex-wrap:wrap}.tools label{display:grid;gap:3px;font-size:.86rem;color:var(--sub)}
input,select,button{font:inherit;color:var(--ink);padding:6px 9px;border:1px solid #96a79d;border-radius:4px;background:white;max-width:100%}
button,summary,select{cursor:pointer}button:disabled{opacity:.45}button:focus-visible,summary:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
.pager{align-items:center;margin:10px 0}.pager output{min-width:12rem;font-size:.87rem;color:var(--sub)}
.case{background:#fff;border-bottom:1px solid var(--edge)}.case summary,.guard summary{padding:11px;overflow-wrap:anywhere}
.case summary::marker,.guard summary::marker{color:var(--accent)}.ranks{display:inline-flex;gap:12px;flex-wrap:wrap;margin-left:14px;color:var(--sub);font-size:.82rem}
.case-body{padding:0 12px 12px}.pair{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,210px),1fr));gap:8px;margin:6px 0 12px}.pair b{display:block;color:var(--sub);font-size:.82rem}
.guard{border-block:1px solid var(--edge)}.guard .scroll{max-height:65vh}.guard table{min-width:680px}
details[hidden]{display:none}footer{font-size:.83rem;color:var(--sub);overflow-wrap:anywhere}
@media(max-width:560px){main{padding:21px 10px 40px}.ranks{display:flex;margin:4px 0 0}.tools label{width:100%}.tools select,.tools input{width:100%}}
"""

SCRIPT = r"""
const cases = [...document.querySelectorAll('.case')];
const search = document.getElementById('query'), change = document.getElementById('change');
const previous = document.getElementById('previous'), next = document.getElementById('next');
let page=0;
function norm(v){return v.normalize('NFKC').toLowerCase().replace(/[_\s]+/g,'');}
function update(){
 const q=norm(search.value), filtered=cases.filter(el=>norm(el.dataset.search).includes(q)
   && (change.value==='all'||el.dataset.changes.split(' ').includes(change.value)));
 const count=filtered.length;
 page=Math.max(0,Math.min(page,Math.ceil(count/20)-1));
 const visible=new Set(filtered.slice(page*20,page*20+20));
 for(const el of cases){el.hidden=!visible.has(el);if(el.hidden)el.open=false;}
 previous.disabled=page===0;next.disabled=(page+1)*20>=count;
 document.getElementById('status').textContent=count?count+'건 중 '+(page*20+1)+'–'+Math.min(count,(page+1)*20)+'번째':'일치하는 식품 0건';
}
for(const el of [search,change])el.addEventListener('input',()=>{page=0;update()});
previous.onclick=()=>{page--;update()};next.onclick=()=>{page++;update()};update();
"""


def render(report):
    summary = report["summary"]
    results = report["referenceResults"]
    size = summary["evaluatedPairs"]
    if not size or len(results) != size or len({row["targetCd"] for row in results}) != size:
        raise ValueError("The comparison must contain one result per evaluated food.")
    scores = []
    for key, label in METHODS:
        hits = summary["methods"][key]["hitsAt"]
        scores.append([label, *(f'{hits[k]["guaranteed"]}건 ({100*hits[k]["guaranteed"]/size:.1f}%)' for k in ("1", "5"))])
    deltas = summary["changesAgainstLexical"]["dense"]
    buttons = ['<option value="all">전체 결과</option>']
    for k in (1, 5):
        for tag, kind, label in (("gain", "recovered", "되찾음"), ("loss", "lost", "놓침")):
            count = len(deltas[str(k)][kind])
            buttons.append(f'<option value="{tag}{k}">상위 {k}위 {label} · {count}건</option>')
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>키워드·벡터로 생것 찾기</title><style>{STYLE}</style></head><body><main>
<header><h1>키워드·벡터로 생것 찾기</h1><p>가공식품 {size}개에서 분류코드를 가리고 식품명만으로 생것 {summary["rawSearchPool"]:,}개를 검색했습니다.</p>
<div class="score">{table(["검색 방식", "기준 생것이 단독 1위", "기준 생것이 상위 5위"], scores)}</div>
<p class="caption">동점이면 가장 뒤의 가능한 순위로 집계했습니다. 기준 식품명과 표기가 명확히 대응하는 쌍의 실험이며, 원재료가 불분명한 109건의 결과는 아직 측정하지 않았습니다.</p></header>
<section><h2>식품별 순위와 실제 1위</h2><div class="tools"><label>식품명 또는 코드<input id="query" type="search"></label>
<label>키워드 대비 벡터 검색 변화<select id="change">{"".join(buttons)}</select></label></div>
<div class="pager"><output id="status" aria-live="polite"></output><button id="previous">이전</button><button id="next">다음</button></div>
{"".join(reference_html(row) for row in results)}</section>{guard_html(report["partChecks"])}
<footer>모델 · {escape(report["model"])} · {escape(report["revision"])}<br>원본 스냅샷 · {escape(report["snapshotId"])}</footer>
</main><script>{SCRIPT}</script></body></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        parser.error("Input and output must differ.")
    report = json.loads(args.input.read_text(encoding="utf-8"))
    page = render(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(page, encoding="utf-8")
    print(f'{len(report["referenceResults"])} references -> {args.output}')


if __name__ == "__main__":
    main()
