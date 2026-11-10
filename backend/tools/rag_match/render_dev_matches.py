"""Render a read-only, offline review of local raw-food retrieval proposals."""

import argparse
from collections import Counter
from html import escape
import json
import math
from pathlib import Path
from urllib.parse import urlsplit

from render_review import STYLE, VERDICTS, metadata, record_panel, required_text


ASSESSMENTS = {"direct": "직접 비교 근거", "reference": "참고 비교 근거",
               "conflict": "조건 충돌", "insufficient": "근거 부족"}

EXTRA_STYLE = """
.filters{display:flex;flex-wrap:wrap;gap:10px 20px;margin-top:20px}
.filters label{display:grid;gap:3px;max-width:100%;color:var(--sub);font-size:.85rem;font-weight:700}
.filters input,.filters select{max-width:100%;padding:6px 9px;background:white;color:var(--ink);
border:1px solid #a0b2a7;border-radius:5px;font:inherit}
.filters select:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
.case .records{margin-top:6px}.pool ol{list-style:none;padding:0;margin:4px 0}
.pool .candidate{padding:10px 0}.candidate p{margin:4px 0 0}
.metric{color:var(--sub);font-size:.82rem;font-variant-numeric:tabular-nums}
.source-line{margin:7px 0;color:var(--sub);font-size:.87rem;overflow-wrap:anywhere}
@media(max-width:600px){.filters label,.filters input,.filters select{width:100%}}
"""

SCRIPT = """
const cases = [...document.querySelectorAll('details.case')];
const query = document.querySelector('#query');
const verdict = document.querySelector('#verdict');
const family = document.querySelector('#family');
const normalize = text => text.normalize('NFKC').toLowerCase().replace(/[_\\s]+/g, '');
const names = cases.map(item => normalize(item.dataset.search));
function filterCases() {
  const terms = query.value.trim().split(/\\s+/).filter(Boolean).map(normalize);
  let shown = 0;
  cases.forEach((item, i) => {
    const visible = (!verdict.value || item.dataset.verdict === verdict.value)
      && (!family.value || item.dataset.family === family.value)
      && terms.every(term => names[i].includes(term));
    item.hidden = !visible;
    if (visible) shown++;
  });
  document.querySelector('#status').textContent = shown + '건 표시 · 전체 ' + cases.length + '건';
}
query.addEventListener('input', filterCases);
verdict.addEventListener('change', filterCases);
family.addEventListener('change', filterCases);
"""


def render_candidate(candidate, selected):
    record = candidate["record"]
    code = required_text(record, "foodCd")
    name = required_text(record, "foodNm")
    rank, score = candidate["rank"], candidate["score"]
    if type(rank) is not int or rank < 1 or type(score) not in (float, int) or not math.isfinite(score):
        raise ValueError(f"Invalid vector rank or score for {code}")
    marker = '<span class="selected">비교 후보로 제안</span>' if code == selected else ""
    value = required_text(candidate, "assessment")
    assessment = escape(ASSESSMENTS.get(value, value))
    explanation = escape(required_text(candidate, "reason"))
    return (f'<li class="candidate"><div class="metric">검색 {rank}위 · 코사인 유사도 {score:.4f}</div>'
            f'<strong>{escape(name)}</strong> {marker} <code>{escape(code)}</code>'
            f'<p><b>{assessment}</b> · {explanation}</p>{metadata(record)}</li>')


def evidence_panel(source):
    if source is None:
        return ""
    url = required_text(source, "url")
    link = urlsplit(url)
    if (link.scheme != "https" or not link.hostname or link.username or link.password
            or "\\" in url or any(c.isspace() for c in url)):
        raise ValueError("An HTTPS evidence source URL is required.")
    title = escape(required_text(source, "title"))
    summary = escape(required_text(source, "summary"))
    return (f'<section class="evidence-source"><h3>추가로 확인한 출처</h3>'
            f'<p class="explanation">{summary}</p><a href="{escape(url, quote=True)}" '
            f'target="_blank" rel="noopener noreferrer">{title}</a></section>')


def render_case(row, first):
    target = row["target"]
    code, name = required_text(target, "foodCd"), required_text(target, "foodNm")
    verdict, selected = required_text(row, "verdict"), row["selectedCd"]
    if verdict not in VERDICTS or (selected is None) != (verdict == "보류"):
        raise ValueError(f"Inconsistent selected candidate and verdict: {code}")
    if row["split"] not in {"dev_review", "dev_remaining"}:
        raise ValueError(f"Expected a development target: {code}")
    family = required_text(row, "family")
    candidates = row["candidates"]
    if not isinstance(candidates, list) or not candidates:
        raise ValueError(f"Missing retrieved candidates: {code}")
    records = {required_text(c["record"], "foodCd"): c["record"] for c in candidates}
    if (len(records) != len(candidates) or code in records
            or any(r.get("lv7Cd") != "01" for r in records.values())
            or (selected is not None and selected not in records)):
        raise ValueError(f"Invalid retrieved or selected raw food: {code}")
    chosen = records.get(selected)
    chosen_name = escape(chosen["foodNm"]) if chosen else "선택 보류"
    search_text = " ".join(f"{r['foodCd']} {r['foodNm']}" for r in (target, *records.values()))
    candidate_items = "".join(render_candidate(c, selected) for c in candidates)
    ties = row.get("boundaryTies", 0)
    tie_note = (f'<p class="metric">표시 범위 밖에도 마지막 후보와 검색 점수가 동률인 '
                f'생것이 {ties}건 있습니다.</p>') if type(ties) is int and ties > 0 else ""
    reason = escape(required_text(row, "reason"))
    return f'''<details class="case" data-family="{escape(family)}" data-verdict="{escape(verdict)}"
 data-search="{escape(search_text)}" {"open" if first else ""}>
<summary><span class="badge {VERDICTS[verdict]}">{escape(verdict)}</span>
<span class="pair"><strong>{escape(name)}</strong><small>{escape(family)} · {chosen_name}</small></span>
<span class="chevron" aria-hidden="true"></span></summary>
<div class="body"><div class="records">{record_panel("대상 식품 원문", target, None)}
{record_panel("제안한 생것 원문", chosen, None)}</div>
<h3>판정 이유</h3><p class="explanation">{reason}</p>
{evidence_panel(row.get("evidenceSource"))}
<details class="pool"><summary>검색한 생것 {len(candidates)}건의 원문과 판단 근거</summary>
{tie_note}<ol>{candidate_items}</ol></details></div></details>'''


def render(report):
    rows = report["results"]
    if not rows or len({row["target"]["foodCd"] for row in rows}) != len(rows):
        raise ValueError("Expected unique development target rows.")
    panels = "".join(render_case(row, number == 0) for number, row in enumerate(rows))
    counts = Counter(row["verdict"] for row in rows)
    family_counts = Counter(row["family"] for row in rows)
    verdict_options = "".join(f'<option value="{label}">{label} · {counts[label]}건</option>' for label in VERDICTS)
    family_options = "".join(f'<option value="{escape(label)}">{escape(label)} · {count}건</option>'
                             for label, count in sorted(family_counts.items()))
    source_summary = " · ".join(f"{label} {counts[label]}건" for label in VERDICTS)
    initial = report.get("summary", {}).get("nameOnlyVerdicts")
    initial_line = ""
    if initial is not None:
        if (not isinstance(initial, dict) or not set(initial) <= set(VERDICTS)
                or any(type(n) is not int or n < 0 for n in initial.values()) or sum(initial.values()) != len(rows)):
            raise ValueError("Name-only counts must describe the same development targets.")
        initial_summary = " · ".join(f"{label} {initial.get(label, 0)}건" for label in VERDICTS)
        initial_line = f'<p class="source-line">DB 원문만 대조한 초기 제안 · {initial_summary}</p>'
    model = escape(required_text(report, "model"))
    snapshot = escape(required_text(report, "snapshotId"))
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>가공식품의 생것 후보</title>
<style>{STYLE}{EXTRA_STYLE}</style></head><body><main><header>
<h1>가공식품의 생것 후보</h1>
<p class="lead">개발용 {len(rows)}건의 최종 제안 · {source_summary}</p>{initial_line}
<p>로컬 임베딩으로 식품명이 가까운 생것을 찾고, 원문과 관측 정보를 대조하는 규칙으로 비교 후보를 제안했습니다.
직접 비교는 재료와 관측 조건이 맞는 경우, 참고 비교는 명시할 차이가 남은 경우입니다. 보류는 비교할 생것 하나를 고를 근거가 부족한 경우입니다.</p>
<p class="source-line">제안의 정확도는 별도 검수가 필요합니다. 검색 모델 · {model}</p></header>
<div class="filters"><label>식품명·코드 검색<input id="query" type="search" autocomplete="off"></label>
<label>판정<select id="verdict"><option value="">전체 판정</option>{verdict_options}</select></label>
<label>식품군<select id="family"><option value="">전체 식품군</option>{family_options}</select></label></div>
<p class="status" id="status" role="status">{len(rows)}건 표시 · 전체 {len(rows)}건</p>{panels}
<footer class="source-line">원본 스냅샷 · {snapshot}</footer></main><script>{SCRIPT}</script></body></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        parser.error("Input and output must differ.")
    report = json.loads(args.input.read_text(encoding="utf-8-sig"))
    html = render(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")
    print(f"{len(report['results'])} development targets -> {args.output}")


if __name__ == "__main__":
    main()
