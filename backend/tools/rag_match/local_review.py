"""Compare the representative-average seafood cohort using only the retrieved records."""

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import re
import sys

from match import (direct_comparison_supported, evidence_index, known, observation_tokens,
                   read_json, save_report, validate_decisions)


METHOD = "로컬 관측 조건 매칭 · 외부 API 없음"
FIELDS = {"srcCd": "출처", "lv4Cd": "대표식품", "lv6Cd": "소분류", "basis": "기준량",
          "country": "원산지", "imported": "수입 여부"}


@dataclass
class Assessment:
    record: dict
    explanation: str
    priority: int = 0
    unresolved: bool = False


def scope_of(record):
    """Accept an explicit original suffix only when its metadata agrees."""
    tokens = observation_tokens(record)
    if not tokens or not tokens[0] or not all(known(value) for value in tokens[0]) or len(tokens[1]) != 2:
        return None
    site, period = tokens[1]
    if not known(site) or record["foodNm"].split("_").count(record["lv7Nm"]) != 1:
        return None
    if site == "수입" and record.get("imported") != "Y":
        return None
    if site in {"대표", "수입", "원양산"}:
        if known(record.get("region")) and record["region"] != site:
            return None
    elif site != record.get("region"):
        return None
    if period == "평균" and not known(record.get("month")):
        return site, period
    if re.fullmatch(r"(?:[1-9]|1[0-2])월", period) and record.get("month") == period[:-1].zfill(2):
        return site, period
    return None


def assess(target, candidate):
    for key, label in FIELDS.items():
        if not known(candidate.get(key)):
            return Assessment(candidate, f"{label} 정보가 부족함", unresolved=True)
        if candidate[key] != target[key]:
            return Assessment(candidate, f"{label} 값이 {candidate[key]}로 대상의 {target[key]}와 다름")
    tokens = observation_tokens(candidate)
    if not tokens or not tokens[0] or not all(known(x) for x in tokens[0]):
        return Assessment(candidate, "원문에서 품목·부위를 확인하기 어려움", unresolved=True)
    identity = observation_tokens(target)[0]
    if tokens[0] != identity:
        return Assessment(candidate, f"품목·부위 표기 {'_'.join(tokens[0])}가 대상의 {'_'.join(identity)}와 다름")
    scope = scope_of(candidate)
    if not scope:
        return Assessment(candidate, "관측 표기의 해석이나 지역·월 메타데이터 확인이 필요함", unresolved=True)
    site, period = scope
    if direct_comparison_supported(target, candidate):
        return Assessment(candidate, "대표_평균 표기와 원산지·기준량·관측 조건이 일치함", 4)
    if period == "평균" and site != "대표":
        return Assessment(candidate, f"{site}_평균으로 평균 표기는 같고 관측 범위가 다름", 3)
    if site == "대표" and period != "평균":
        return Assessment(candidate, f"대표_{period}으로 대표 표기는 같고 월이 한정됨", 2)
    if period != "평균":
        return Assessment(candidate, f"{site}_{period}에 한정된 관측임", 1)
    return Assessment(candidate, "관측 범위의 일치를 확인하기 어려움", unresolved=True)


def review(case):
    target = case["target"]
    in_scope = (target.get("srcCd") == "2" and target.get("imported") in {"Y", "N"}
                and known(target.get("lv7Cd")) and target["lv7Cd"] != "01"
                and all(known(target.get(key)) for key in FIELDS)
                and scope_of(target) == ("대표", "평균"))
    selected = None
    verdict = "보류"
    if in_scope:
        assessments = [assess(target, candidate) for candidate in case["candidates"]]
        highest = max(item.priority for item in assessments)
        leaders = [item for item in assessments if highest and item.priority == highest]
        if any(item.unresolved for item in assessments):
            reason = "후보 중 원문·메타데이터를 해석할 수 없는 기록이 있어 단일 최선 후보를 정하기 어렵습니다."
        elif not leaders:
            reason = f"대상의 원산지 {target['country']}, 수입 여부 {target['imported']}, 품목·부위와 기준량을 모두 충족하는 후보가 없습니다."
        elif len(leaders) > 1:
            places = ", ".join("_".join(scope_of(item.record)) for item in leaders)
            reason = f"원산지·품목·부위·기준량이 맞는 후보 중 {places}의 관측 우선순위가 같습니다. 한 건을 고를 추가 근거가 없습니다."
        else:
            winner = leaders[0]
            selected = winner.record
            verdict = "직접 비교" if highest == 4 else "참고 비교"
            comparison = {
                4: "대표·평균 표기와 지역·월 메타데이터가 모두 일치합니다.",
                3: "대상과 평균 표기가 같고 산지 범위가 달라 참고용으로 선택했습니다.",
                2: "대표 표기가 같고 특정 월에 한정된 관측이라 참고용으로 선택했습니다.",
                1: "품목·부위·원산지·기준량이 맞는 유일한 후보이며 지역과 월이 한정됩니다.",
            }
            reason = (f"‘{selected['foodNm']}’은 대상과 품목·부위, 원산지 {target['country']}, "
                      f"기준량 {target['basis']}이 일치합니다. {comparison[highest]}")
    else:
        assessments = [Assessment(c, "대상 관측 범위를 먼저 확인해야 함") for c in case["candidates"]]
        reason = "이 방식은 원산지·수입 여부·기준량이 확인되는 출처 2의 대표_평균 기록에 적용합니다. 대상 원문이나 필드를 검토해야 합니다."
    alternatives = " / ".join(
        f"‘{item.record['foodNm']}’ ({item.record['foodCd']}) — {item.explanation}"
        for item in assessments if item.record is not selected
    )
    return {"targetCd": target["foodCd"], "selectedCd": selected["foodCd"] if selected else None,
            "verdict": verdict, "reason": reason, "targetQuote": target["foodNm"],
            "candidateQuote": selected["foodNm"] if selected else None, "alternatives": alternatives}


def compare(index, local, previous):
    other = validate_decisions(index, previous["matches"])
    differences = [code for code, row in local.items()
                   if (row["verdict"], row["selectedCd"]) != (other[code]["verdict"], other[code]["selectedCd"])]
    print(f"Matched verdict and raw candidate: {len(local) - len(differences)}/{len(local)}")
    for code in differences:
        print(f"{code}: local {local[code]['verdict']} {local[code]['selectedCd']} | "
              f"compared {other[code]['verdict']} {other[code]['selectedCd']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--compare-matches", type=Path, help="Optional previously generated full decision set.")
    args = parser.parse_args()
    if any(p and p.resolve() == args.output.resolve() for p in (args.evidence, args.compare_matches)):
        parser.error("Output must differ from both input files.")
    index = evidence_index(read_json(args.evidence))
    decisions = validate_decisions(index, [review(case) for case in index.values()])
    if args.compare_matches:
        compare(index, decisions, read_json(args.compare_matches))
    save_report(args.output, {"model": METHOD, "matches": list(decisions.values())})
    print(f"Reviewed {len(decisions)} cases:", dict(Counter(r["verdict"] for r in decisions.values())))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError) as exc:
        sys.exit(f"Local matching failed: {exc}")
