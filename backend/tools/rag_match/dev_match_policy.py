"""Propose comparisons only when retrieved names and recorded observation fields support one."""

from benchmark_cases import SIMPLE_STATES
from benchmark_parts import check_parts
from match import direct_comparison_supported, known


def name_evidence(record):
    """Keep identity tokens on their original side of the processing state."""
    tokens = tuple(t.strip() for t in record["foodNm"].split("_"))
    state = record.get("lv7Nm")
    if not known(state) or tokens.count(state) != 1 or tokens[0] == state:
        return None
    position = tokens.index(state)
    identity = tokens[:position]
    normalized = list(identity)
    # Only remove an explicit powder suffix when the record independently says it was milled.
    if record.get("lv7Cd") == "06" and len(identity) > 1 and identity[-1].endswith("가루"):
        base = identity[-1][:-2]
        if base:
            normalized[-1] = base
    return identity, tuple(normalized), tokens[position + 1:]


def describe(record, flag, reason, pending=False):
    return {"foodCd": record["foodCd"], "foodNm": record["foodNm"],
            "flag": flag, "reason": reason, "pendingIdentityMatch": pending}


def field_value(record, key):
    value = record.get(key)
    return value if known(value) else "미기재"


def informative_detail(token, target):
    if token.startswith(("수입", "국내산", "국산", "원양산")) or token.endswith("산"):
        return False
    return known(token) and token not in {target.get("country"), target.get("region"), "대표", "평균"}


def assess(target, candidate):
    target_name, candidate_name = target["foodNm"], candidate["foodNm"]
    if candidate.get("lv7Cd") != "01" or candidate.get("lv7Nm") != "생것":
        return describe(candidate, "insufficient", "세분류에 생것 관측임을 표시한 기록이 필요합니다.")
    if target_name.split("_")[0] != candidate_name.split("_")[0]:
        return describe(candidate, "insufficient", f"원문의 품목 표기 ‘{target_name.split('_')[0]}’와 "
                        f"‘{candidate_name.split('_')[0]}’를 같은 품목으로 볼 별칭 근거가 없습니다.")
    part, part_reason = check_parts(target_name, candidate_name)
    if part == "conflict":
        return describe(candidate, "conflict", part_reason)

    for key, label in (("basis", "영양 기준량"), ("country", "원산지"), ("imported", "수입 여부")):
        left, right = field_value(target, key), field_value(candidate, key)
        if "미기재" not in (left, right) and left != right:
            return describe(candidate, "conflict", f"{label} 표기가 대상 ‘{left}’, 생것 ‘{right}’로 다릅니다.")

    original, raw = name_evidence(target), name_evidence(candidate)
    if not original or not raw:
        return describe(candidate, "insufficient", "원문에서 세분류명과 일치하는 조리 상태를 독립적으로 분리할 수 없습니다.")
    left, right = original[1], raw[1]
    if left != right:
        return describe(candidate, "insufficient", f"가공 표기를 제외한 원문은 대상 ‘{'_'.join(original[0])}’, "
                        f"생것 ‘{'_'.join(raw[0])}’입니다. 품종·부위·원료 범위가 대응하는지 확인이 필요합니다.")
    if target.get("lv7Cd") not in SIMPLE_STATES or SIMPLE_STATES[target["lv7Cd"]] != target.get("lv7Nm"):
        return describe(candidate, "insufficient", f"‘{target.get('lv7Nm')}’의 직전 원료 상태 또는 첨가물은 "
                        "이름만으로 확정하기 어려워 비교를 보류합니다.")
    if any(not known(record.get(key)) for record in (target, candidate)
           for key in ("basis", "srcCd", "lv4Cd", "lv6Cd")):
        return describe(candidate, "insufficient", "기준량·출처·분류 중 미기재 정보가 있습니다.", True)
    if target.get("imported") not in {"Y", "N"} or candidate.get("imported") not in {"Y", "N"}:
        return describe(candidate, "insufficient", "두 기록의 수입 여부를 확인할 수 없습니다.", True)
    left_country, right_country = field_value(target, "country"), field_value(candidate, "country")
    if left_country != right_country or (target["imported"] == "Y" and left_country == "미기재"):
        return describe(candidate, "insufficient", f"원산지가 대상 ‘{left_country}’, 생것 ‘{right_country}’로 "
                        "두 기록의 원산지 대응을 확인하기 어렵습니다.", True)
    for key, label in (("region", "원산지역"), ("month", "관측월")):
        if known(target.get(key)) and target[key] != candidate.get(key):
            return describe(candidate, "insufficient", f"{label}이 대상 ‘{target[key]}’, "
                            f"생것 ‘{field_value(candidate, key)}’입니다.", True)
    if not all(known(token) for token in left) or not any(informative_detail(t, target) for t in left[1:]):
        return describe(candidate, "insufficient", f"원문에서 공통으로 확인한 표기는 ‘{'_'.join(left)}’입니다. "
                        "비교할 품종·부위·세부 원료를 특정할 근거가 부족합니다.")
    # A broad family heading plus a generic tissue token still does not name a species.
    if left[0].endswith("류") and (not known(target.get("lv5Nm")) or target["lv5Nm"] not in left[1:]
                                  or target["lv5Nm"] != candidate.get("lv5Nm")):
        return describe(candidate, "insufficient", f"‘{left[0]}’ 아래 같은 세부 품목이라는 원문·분류 근거가 부족합니다.")
    for key, label in (("lv5Nm", "중분류"), ("lv6Nm", "소분류")):
        a, b = target.get(key), candidate.get(key)
        if known(a) and known(b) and a != b:
            if key == "lv5Nm" and target["lv7Cd"] == "06" and a == b + "가루":
                continue
            return describe(candidate, "insufficient", f"식품명에 공통 표기가 있지만 {label} 실명이 "
                            f"‘{a}’와 ‘{b}’로 달라 같은 세부 품목·부위를 확인하기 어렵습니다.")
    if left_country != "미기재" and direct_comparison_supported(target, candidate):
        return describe(candidate, "direct", f"원문에서 품목·부위 ‘{'_'.join(left)}’와 관측 표기가 일치하고 "
                        f"출처·소분류·원산지 {left_country}·기준량 {target['basis']}이 같습니다.")
    # Different nonempty sampling scopes must be explicit before a comparison can be described.
    if original[2] != raw[2] and not (original[2] == ("대표", "평균") and len(raw[2]) == 2):
        return describe(candidate, "insufficient", "가공 상태 뒤의 관측 범위가 다르며 대응을 확인할 근거가 부족합니다.", True)
    limits = []
    if original[0] != raw[0]:
        limits.append(f"대상에는 ‘{original[0][-1]}’, 생것에는 ‘{raw[0][-1]}’로 기재")
    for key, label in (("srcNm", "출처"), ("lv5Nm", "중분류"), ("lv6Nm", "소분류")):
        if target.get(key) != candidate.get(key):
            limits.append(f"{label} 대상 ‘{field_value(target, key)}’ / 생것 ‘{field_value(candidate, key)}’")
    if original[2] != raw[2]:
        limits.append(f"관측 표기 대상 ‘{'_'.join(original[2])}’ / 생것 ‘{'_'.join(raw[2])}’")
    if left_country == "미기재":
        limits.append("양쪽 원산지명이 미기재여서 같은 산지인지 확인할 수 없음")
    for key, label in (("region", "생것 원산지역"), ("month", "생것 관측월")):
        if target.get(key) != candidate.get(key) and known(candidate.get(key)):
            limits.append(f"{label} ‘{candidate[key]}’")
    if not limits:
        limits.append("세부 관측 조건이 같은 실제 표본인지 추가 확인 필요")
    return describe(candidate, "reference", f"원문에서 가공 전 품목·세부 표기 ‘{'_'.join(left)}’와 "
                    f"기준량 {target['basis']}을 확인했습니다. 검토할 차이는 다음과 같습니다. {', '.join(limits)}.")


def decide(target, candidates, boundary_ties=0):
    """Assess retrieval proposals, never emit a human-approved label."""
    if len({c["foodCd"] for c in candidates}) != len(candidates):
        raise ValueError("Duplicate retrieved food code.")
    assessments = [assess(target, c) for c in candidates]
    viable = [a for a in assessments if a["flag"] == "direct"]
    if not viable:
        viable = [a for a in assessments if a["flag"] == "reference"]
    selected = None
    if boundary_ties and viable:
        reason = "검색 범위 경계에 같은 점수의 미검토 기록이 남아 한 후보를 선정하지 않았습니다."
    elif len(viable) > 1:
        reason = f"상위 후보에서 원문 근거가 같은 수준인 생것 {len(viable)}건이 경합합니다. 순위로 동률을 해소하지 않았습니다."
    elif viable and any(a["pendingIdentityMatch"] for a in assessments):
        reason = "세부 식품명이 같은 다른 후보의 관측 정보가 불완전해 한 건을 선택하기 어렵습니다."
    elif viable:
        selected = viable[0]
        reason = selected["reason"]
    elif assessments:
        family = target["foodNm"].split("_")[0]
        example = next((a for a in assessments if a["foodNm"].split("_")[0] == family), assessments[0])
        reason = f"조회된 생것 {len(assessments)}건에서 비교 근거를 확인하지 못했습니다. 예: ‘{example['foodNm']}’. {example['reason']}"
    else:
        reason = "검토할 생것 후보가 없습니다."
    return {"targetCd": target["foodCd"], "targetQuote": target["foodNm"],
            "selectedCd": selected["foodCd"] if selected else None, "candidateQuote": selected["foodNm"] if selected else None,
            "verdict": {"direct": "직접 비교", "reference": "참고 비교"}[selected["flag"]] if selected else "보류",
            "reason": reason, "status": "unreviewed_proposal", "assessments": assessments}
