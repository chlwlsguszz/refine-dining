"""Render a self-contained, read-only Korean review of retrieved food matches."""

import argparse
import json
import os
import tempfile
from collections import Counter
from html import escape
from pathlib import Path


VERDICTS = {"직접 비교": "direct", "참고 비교": "reference", "보류": "hold"}
SOURCE_FIELDS = (
    ("출처", "srcNm"), ("출처 코드", "srcCd"),
    ("대표식품", "lv4Nm"), ("대표식품 코드", "lv4Cd"),
    ("중분류", "lv5Nm"), ("중분류 코드", "lv5Cd"),
    ("소분류", "lv6Nm"), ("소분류 코드", "lv6Cd"),
    ("세분류", "lv7Nm"), ("세분류 코드", "lv7Cd"),
    ("기준량", "basis"), ("원산지역", "region"), ("원산지", "country"),
    ("생산·채취·포획월", "month"), ("수입 여부", "imported"), ("자료 생성 방법", "production"),
    ("자료 기준일", "referenceDate"),
)


def required_text(record, key):
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a nonempty string")
    return value


def index_unique(records, key):
    if not isinstance(records, list):
        raise ValueError(f"Expected a list of records with key {key}")
    index = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError(f"Invalid record with key {key}")
        code = required_text(record, key)
        if code in index:
            raise ValueError(f"Duplicate {key}: {code}")
        index[code] = record
    return index


def join_records(evidence, result):
    if not isinstance(evidence, list) or not evidence or not isinstance(result, dict):
        raise ValueError("Evidence and results must contain at least one case")
    matches = index_unique(result.get("matches"), "targetCd")
    joined = []
    for item in evidence:
        target = item["target"]
        code = required_text(target, "foodCd")
        required_text(target, "foodNm")
        match = matches.pop(code, None)
        if match is None:
            raise ValueError(f"Missing result or duplicate target: {code}")
        candidates = index_unique(item["candidates"], "foodCd")
        if not candidates:
            raise ValueError(f"No retrieved candidates for {code}")
        for candidate in candidates.values():
            required_text(candidate, "foodNm")
        verdict = required_text(match, "verdict")
        if verdict not in VERDICTS:
            raise ValueError(f"Unknown verdict for {code}: {verdict}")
        selected_code = match["selectedCd"]
        if selected_code is None:
            if verdict != "보류" or match.get("candidateQuote"):
                raise ValueError(f"Missing selected candidate for {code}")
        elif selected_code not in candidates:
            raise ValueError(f"Selected candidate outside the retrieved pool for {code}")
        required_text(match, "reason")
        required_text(match, "alternatives")
        if required_text(match, "targetQuote") not in target["foodNm"]:
            raise ValueError(f"Unverified target quote for {code}")
        selected = candidates.get(selected_code)
        if selected and required_text(match, "candidateQuote") not in selected["foodNm"]:
            raise ValueError(f"Unverified candidate quote for {code}")
        joined.append((target, candidates, match, selected))
    if matches:
        raise ValueError(f"Unexpected result targets: {', '.join(matches)}")
    return joined


def highlight(name, quote):
    if not quote:
        return escape(name)
    before, _, after = name.partition(quote)
    return f"{escape(before)}<mark>{escape(quote)}</mark>{escape(after)}"


def metadata(record):
    fields = "".join(
        f"<div><dt>{label}</dt><dd>{escape(str(value))}</dd></div>"
        for label, key in SOURCE_FIELDS
        if (value := record.get(key)) is not None and str(value).strip()
    )
    return f'<details class="meta"><summary>출처·분류·관측 정보</summary><dl>{fields}</dl></details>'


def record_panel(label, record, quote):
    if record is None:
        return f'<section><h3>{label}</h3><p class="name">선택 보류</p></section>'
    return (
        f'<section><h3>{label}</h3><p class="name">{highlight(record["foodNm"], quote)}</p>'
        f'<code>{escape(record["foodCd"])}</code>{metadata(record)}</section>'
    )


def candidate_list(candidates, selected):
    rows = []
    for code, record in candidates.items():
        indicator = '<span class="selected">선택 후보</span>' if code == selected else ""
        rows.append(
            f'<li><div><b>{escape(record["foodNm"])}</b>{indicator}</div>'
            f'<code>{escape(code)}</code>{metadata(record)}</li>'
        )
    return (f'<details class="pool"><summary>검색된 생것 후보 전체 · {len(rows)}건</summary>'
            f'<ul>{"".join(rows)}</ul></details>')


def same_decision(match, other):
    return match["verdict"] == other["verdict"] and match["selectedCd"] == other["selectedCd"]


def local_panel(match, local_case):
    if local_case is None:
        return ""
    _, _, decision, selected = local_case
    agreement = "일치" if same_decision(match, decision) else "차이 있음"
    chosen = "선택 보류"
    if selected:
        chosen = f'{escape(selected["foodNm"])} · <code>{escape(selected["foodCd"])}</code>'
    return (
        f'<details class="pool"><summary>API 없는 로컬 판정 · {agreement}</summary>'
        f'<p><b>{escape(decision["verdict"])}</b> · {chosen}</p>'
        f'<h3>로컬 판정 근거</h3><p class="explanation">{escape(decision["reason"])}</p>'
        f'<h3>다른 후보와 비교</h3><p class="explanation">{escape(decision["alternatives"])}</p></details>'
    )


def case_panel(target, candidates, match, selected, opened, model, review_note, local_case):
    verdict = match["verdict"]
    chosen = escape(selected["foodNm"]) if selected else "선택 보류"
    source_terms = " ".join(
        record["foodCd"] + " " + record["foodNm"]
        for record in (target, *candidates.values())
    )
    selected_label = "검토 후보 원문" if verdict == "보류" else "선택한 생것 원문"
    review = ""
    if review_note:
        review = (f'<details class="meta"><summary>원문 대조 후 재검토</summary>'
                  f'<p class="explanation">{escape(review_note)}</p></details>')
    return f'''
<details class="case" data-verdict="{escape(verdict)}" data-search="{escape(source_terms)}" {opened}>
  <summary><span class="badge {VERDICTS[verdict]}">{escape(verdict)}</span>
    <span class="pair"><strong>{escape(target["foodNm"])}</strong><small>생것 후보 · {chosen}</small></span>
    <span class="chevron" aria-hidden="true"></span>
  </summary>
  <div class="body">
    <div class="records">{record_panel("대상 식품 원문", target, match["targetQuote"])}
      {record_panel(selected_label, selected, match.get("candidateQuote"))}</div>
    <h3>판정 이유</h3><p class="explanation">{escape(match["reason"])}</p>
    <h3>다른 후보와 비교</h3><p class="explanation">{escape(match["alternatives"])}</p>
    <p class="model">이 판정의 생성 모델 · {escape(model)}</p>{review}
    {local_panel(match, local_case)}
    {candidate_list(candidates, match["selectedCd"])}
  </div>
</details>'''


STYLE = """
*{box-sizing:border-box} :root{color-scheme:light;--ink:#172d29;--sub:#445d55;--edge:#cfdcd5;
--page:#f6f8f5;--paper:#fff;--accent:#225c49}
body{margin:0;background:var(--page);color:var(--ink);font:16px/1.55 "Malgun Gothic","Apple SD Gothic Neo",sans-serif}
main{max-width:1050px;margin:auto;padding:42px 30px 72px}
h1{margin:0;font-size:clamp(26px,4vw,38px);letter-spacing:-.045em;line-height:1.25}
.lead{color:var(--sub);max-width:850px;margin:8px 0}
.model{font-size:.84rem;color:var(--sub);overflow-wrap:anywhere}
.controls{display:flex;flex-wrap:wrap;align-items:end;gap:14px 30px;padding:20px 0 13px}
.filters{min-width:0;margin:0;padding:0;border:0;display:flex;flex-wrap:wrap;gap:5px}
legend,.search>span{display:block;color:var(--sub);font-size:.83rem;font-weight:700;margin-bottom:4px}
button,input{font:inherit}button{padding:6px 10px;border:1px solid var(--edge);color:var(--ink);
background:var(--paper);border-radius:5px;cursor:pointer;font-size:.9rem}
button[aria-pressed=true]{border-color:var(--accent);background:var(--accent);color:white}
input{padding:6px 10px;border:1px solid var(--edge);border-radius:5px;width:min(100%,290px)}
input:focus-visible,summary:focus-visible,button:focus-visible{outline:3px solid #22735a;outline-offset:2px}
.status{margin:5px 0 10px;font-size:.88rem;color:var(--sub)}.case{background:var(--paper);border-top:1px solid var(--edge)}
.case:last-of-type{border-bottom:1px solid var(--edge)}summary{cursor:pointer}
.case>summary{display:grid;grid-template-columns:80px 1fr 12px;gap:12px;align-items:center;padding:14px}
.case>summary::-webkit-details-marker{display:none}.case>summary:hover{background:#eff5ef}
.chevron{width:8px;height:8px;border-right:2px solid var(--sub);border-bottom:2px solid var(--sub);transform:rotate(45deg)}
.case[open]>summary .chevron{transform:rotate(225deg)}.pair>*{display:block;overflow-wrap:anywhere}
.pair small,code{color:var(--sub);font-size:.82rem}.pair strong{font-size:1rem}
.badge,.selected{border-radius:3px;text-align:center;font-size:.78rem;font-weight:700;padding:3px 6px}
.direct{background:#dceee1;color:#244e34}.reference{background:#e5edf4;color:#294a63}.hold{background:#f7ebd7;color:#6b4a19}
.body{padding:0 18px 20px}.records{display:grid;grid-template-columns:1fr 1fr;border:1px solid var(--edge);border-radius:6px}
.records section{min-width:0;padding:14px}.records section+section{border-left:1px solid var(--edge)}
h3{margin:14px 0 3px;font-size:.86rem;color:var(--sub)}.records h3{margin:0 0 5px}
.name{font-weight:700;margin:0 0 3px;overflow-wrap:anywhere}mark{background:#ffefb5;color:inherit}
code{overflow-wrap:anywhere}.explanation{margin:0;white-space:pre-line;overflow-wrap:anywhere}
.meta{margin-top:6px;font-size:.86rem}.meta summary,.pool summary{color:var(--accent);font-weight:600}
dl{margin:6px 0 0}dl div{display:grid;grid-template-columns:7em 1fr;gap:8px}dt{color:var(--sub)}dd{margin:0;overflow-wrap:anywhere}
.pool{border-top:1px solid var(--edge);margin:14px 0 0;padding-top:10px}.pool ul{list-style:none;margin:0;padding:0}
.pool li{padding:9px 0;border-bottom:1px solid var(--edge);overflow-wrap:anywhere}.selected{margin-left:8px;background:#e6efe9;color:var(--accent)}
[hidden]{display:none!important}
@media(max-width:650px){main{padding:22px 12px 40px}.records{grid-template-columns:1fr}.records section+section{
border-left:0;border-top:1px solid var(--edge)}.case>summary{grid-template-columns:66px 1fr 8px;gap:8px;padding:10px}.body{padding:0 10px 15px}}
"""


SCRIPT = r"""
const buttons = [...document.querySelectorAll('.filters button')];
const cases = [...document.querySelectorAll('.case')];
const search = document.getElementById('search');
let verdict = '전체';
function update() {
  const tokens = search.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
  let count = 0;
  for (const item of cases) {
    const text = item.dataset.search.toLowerCase();
    item.hidden = !((verdict === '전체' || item.dataset.verdict === verdict) && tokens.every(t => text.includes(t)));
    if (!item.hidden) count++;
  }
  document.getElementById('status').textContent = count + '건 표시 · 전체 ' + cases.length + '건';
  for (const button of buttons) button.setAttribute('aria-pressed', String(button.dataset.verdict === verdict));
}
for (const button of buttons) button.addEventListener('click', () => { verdict = button.dataset.verdict; update(); });
search.addEventListener('input', update);
"""


def render(evidence, result, baseline=None):
    cases = join_records(evidence, result)
    local_cases = {}
    comparison_summary = ""
    if baseline is not None:
        local_cases = {case[0]["foodCd"]: case for case in join_records(evidence, baseline)}
        agreement = sum(same_decision(match, local_cases[target["foodCd"]][2])
                        for target, _, match, _ in cases)
        comparison_summary = (
            f'<p class="lead"><strong>로컬 판정과 일치 · {agreement}/{len(cases)}건</strong></p>'
            '<p class="model">같은 원본에 대한 두 결과를 대조해 판정 유형과 선택한 생것 코드가 모두 같은 건을 셌습니다. '
            '이 수치는 두 방식의 일치도를 나타냅니다. 정확도를 평가하려면 독립적으로 검수한 정답이 필요합니다. '
            '로컬 판정과 이 화면 열람은 외부 API 호출 비용이 없습니다.</p>'
        )
    base_model = required_text(result, "model")
    codes = {target["foodCd"] for target, _, _, _ in cases}
    models = result.get("modelsByTarget", {})
    notes = result.get("appliedReviewNotes", {})
    for label, mapping in (("modelsByTarget", models), ("appliedReviewNotes", notes)):
        if not isinstance(mapping, dict) or not set(mapping).issubset(codes):
            raise ValueError(f"Invalid target mapping in {label}")
        for code in mapping:
            required_text(mapping, code)
    model_counts = Counter(models.get(code, base_model) for code in codes)
    model_summary = " · ".join(f"{escape(name)} {n}건" for name, n in sorted(model_counts.items()))
    counts = Counter(match["verdict"] for _, _, match, _ in cases)
    filters = "".join(
        f'<button type="button" data-verdict="{label}" aria-pressed="{str(label == "전체").lower()}">{label} {amount}</button>'
        for label, amount in [("전체", len(cases)), *((label, counts[label]) for label in VERDICTS)]
    )
    panels = "".join(
        case_panel(*case, "open" if index == 0 else "",
                   models.get(case[0]["foodCd"], base_model), notes.get(case[0]["foodCd"]),
                   local_cases.get(case[0]["foodCd"]))
        for index, case in enumerate(cases)
    )
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>조리식품과 생것 매칭 검토</title>
<style>{STYLE}</style></head><body><main><header><h1>조리식품과 생것 매칭 검토</h1>
<p class="lead">직접 비교는 관측 조건이 일치하는 후보, 참고 비교는 차이를 명시한 후보입니다. 보류는 현재 근거로 비교를 승인하기 어려운 건입니다.</p>
<p class="model">판정 생성 · {model_summary}　/　원문 출처 · 로컬 원본 식품 기록　/　표시된 판정은 검토 제안입니다.</p>{comparison_summary}</header>
<div class="controls"><fieldset class="filters"><legend>판정별로 보기</legend>{filters}</fieldset>
<label class="search"><span>식품명·식품코드 검색</span><input id="search" type="search" autocomplete="off"></label></div>
<p class="status" id="status" role="status">{len(cases)}건 표시 · 전체 {len(cases)}건</p>
{panels}</main><script>{SCRIPT}</script></body></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("evidence", "matches", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--baseline", type=Path, help="Compare a second, locally generated set of decisions.")
    args = parser.parse_args()
    if any(path and args.output.resolve() == path.resolve() for path in (args.evidence, args.matches, args.baseline)):
        parser.error("Output must be different from input files")
    evidence = json.loads(args.evidence.read_text(encoding="utf-8-sig"))
    result = json.loads(args.matches.read_text(encoding="utf-8-sig"))
    baseline = json.loads(args.baseline.read_text(encoding="utf-8-sig")) if args.baseline else None
    document = render(evidence, result, baseline)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=args.output.parent, suffix=".tmp", delete=False) as tmp:
        temporary = Path(tmp.name)
    try:
        temporary.write_text(document, encoding="utf-8")
        os.replace(temporary, args.output)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"{len(evidence)} cases -> {args.output}")


if __name__ == "__main__":
    main()
