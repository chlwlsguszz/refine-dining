"""Retrieve scoped official passages and verify extractive local-model proposals."""

from collections import Counter
import re

from assess_development import documented_reference
from dev_match_policy import decide
from match import VERDICTS


POLICY = "grounded-rag-v1"
PROMPT = """당신은 한국 식품성분표 검수 보조자다. 아래 JSON의 데이터만 읽고 가공식품의 비교용 생것을 제안한다.
이름·표본·단위에서 개인적인 상식을 추가하거나 품종·부위를 추측하지 않는다. 비교 근거가 모자라거나 후보가 여럿이면 보류한다.
공식 문단에서 use가 ingredient_reference이면 명시된 원료로 참고 비교만 제안할 수 있다. process_context는 가공 설명만 가능하다.
targetQuote와 candidateQuote는 해당 식품명을 전체 복사한다. 선택 시 차이는 입력 원문에 있는 관측 필드로 대조한다.
문단을 인용하면 ID와 quote 전체를 함께 복사한다. 원문 행만으로 판단했으면 문단 ID와 quote를 null로 둔다.
보류하면 selectedCd와 candidateQuote는 null이다. 비교가 가능해도 사람의 결정은 별도로 이루어진다."""

ROW_FIELDS = ("foodCd", "foodNm", "lv4Nm", "lv5Nm", "lv6Nm", "lv7Nm", "basis",
              "srcNm", "country", "imported", "region", "month")
DIFFERENCES = {"foodNm": "원문 식품명", "basis": "영양 기준량", "srcNm": "자료 출처",
               "country": "원산지", "region": "지역", "month": "관측월", "lv5Nm": "세부 품목",
               "lv6Nm": "소분류"}


def validate_passages(passages):
    ids = set()
    for passage in passages:
        if (not all(isinstance(passage.get(k), str) and passage[k].strip()
                    for k in ("id", "quote", "title", "summary", "url", "version", "publisher", "locator",
                              "checkedOn", "limitations"))
                or passage["id"] in ids or not passage["url"].startswith("https://")
                or passage["use"] not in {"ingredient_reference", "process_context"}):
            raise ValueError("Incomplete or duplicate official passage.")
        ids.add(passage["id"])
        scope = passage["scope"]
        if (not all(isinstance(scope.get(k), list) and all(isinstance(v, str) and v for v in scope[k])
                    for k in ("families", "states", "processed"))
                or not any(scope.values())):
            raise ValueError("A passage requires a bounded food scope.")
        if passage["use"] == "ingredient_reference" and not passage.get("rawIngredient"):
            raise ValueError("Ingredient definitions require a named raw ingredient.")


def retrieve_passages(target, passages, limit=3):
    """Apply applicability filters first. Rank by name overlap and scope specificity."""
    query = set(re.findall(r"[\w가-힣]+", target["foodNm"].replace("_", " ")))
    ranked = []
    for passage in passages:
        scope = passage["scope"]
        fields = (("families", "lv4Nm"), ("processed", "lv5Nm"), ("states", "lv7Nm"))
        if any(scope[k] and target.get(field) not in scope[k] for k, field in fields):
            continue
        body = passage["summary"] + " " + passage["quote"] + " " + passage["title"]
        overlap = sum(token in body for token in query)
        score = 2 * sum(bool(scope[k]) for k, _ in fields) + overlap
        ranked.append((score, passage["id"], passage))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [p for _, _, p in ranked[:limit]]


def compare_records(target, candidates, passages, boundary):
    baseline = decide(target, candidates, boundary_ties=boundary)
    selected = {k: baseline[k] for k in ("selectedCd", "candidateQuote", "verdict", "reason")}
    selected["evidenceSource"] = None
    if boundary or baseline["selectedCd"]:
        return baseline, selected
    suitable = []
    for passage in passages:
        if passage["use"] != "ingredient_reference":
            continue
        source = {"family": target["lv4Nm"], "processed": target["lv5Nm"], "state": target["lv7Nm"],
                  "rawIngredient": passage["rawIngredient"], "summary": passage["summary"]}
        found = documented_reference(target, candidates, [source])
        if found:
            raw, _, reason = found
            item = next(a for a in baseline["assessments"] if a["foodCd"] == raw["foodCd"])
            if item["flag"] != "conflict":
                suitable.append((raw, passage, reason))
    if suitable and len({raw["foodCd"] for raw, _, _ in suitable}) == 1:
        raw, passage, reason = suitable[0]
        selected.update(selectedCd=raw["foodCd"], candidateQuote=raw["foodNm"], verdict="참고 비교",
                        reason=reason, evidenceSource=passage)
    return baseline, selected


def small_record(row):
    return {key: row.get(key) for key in ROW_FIELDS}


def model_input(target, candidates, passages):
    return {"target": small_record(target), "candidates": [small_record(c) for c in candidates],
            "passages": [{k: p[k] for k in ("id", "quote", "summary", "limitations", "use")} for p in passages]}


def response_schema(target, candidates, passages):
    def choices(values, nullable=False):
        values = list(dict.fromkeys(values))
        if nullable:
            values.append(None)
        return {"enum": values}
    props = {"verdict": choices(VERDICTS), "selectedCd": choices((c["foodCd"] for c in candidates), True),
             "targetQuote": choices([target["foodNm"]]),
             "candidateQuote": choices((c["foodNm"] for c in candidates), True),
             "citationId": choices((p["id"] for p in passages), True),
             "citationQuote": choices((p["quote"] for p in passages), True),
             "differenceField": choices(list(DIFFERENCES))}
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


def validate_generation(response, target, candidates, passages, allowed):
    """Verify citations and admissibility, independently of constrained decoder support."""
    schema = response_schema(target, candidates, passages)
    if not isinstance(response, dict) or set(response) != set(schema["required"]):
        raise ValueError("invalid_response_fields")
    for key, prop in schema["properties"].items():
        if response[key] not in prop["enum"]:
            raise ValueError("ungrounded_" + key)
    cited = next((p for p in passages if p["id"] == response["citationId"]), None)
    if response["citationQuote"] != (cited["quote"] if cited else None):
        raise ValueError("mismatched_citation")
    candidate = next((r for r in candidates if r["foodCd"] == response["selectedCd"]), None)
    if response["candidateQuote"] != (candidate["foodNm"] if candidate else None):
        raise ValueError("mismatched_candidate_quote")
    if (response["verdict"] == "보류") != (candidate is None):
        raise ValueError("invalid_selection")
    if candidate:
        if response["selectedCd"] != allowed["selectedCd"] or response["verdict"] != allowed["verdict"]:
            raise ValueError("unsupported_identity_or_observation")
        if allowed["evidenceSource"]:
            if not cited or cited["id"] != allowed["evidenceSource"]["id"]:
                raise ValueError("missing_ingredient_citation")
        elif cited:
            raise ValueError("citation_does_not_support_selected_pair")
        field = response["differenceField"]
        if target.get(field) == candidate.get(field):
            raise ValueError("difference_not_observed")
        return {"field": field, "label": DIFFERENCES[field],
                "target": target.get(field), "candidate": candidate.get(field)}
    return None


def explain_generation(response, target, candidates, passages, difference):
    """Display only server-extracted observations, including on an abstention."""
    field = response["differenceField"]
    if difference:
        explanation = (f"{response['verdict']} 제안. {difference['label']} 표기는 대상 "
                       f"‘{difference['target']}’, 선택한 생것 ‘{difference['candidate']}’입니다.")
    else:
        examples = list(dict.fromkeys(str(c.get(field) or "미기재") for c in candidates))[:2]
        observed = " / ".join(examples) if examples else "후보 없음"
        explanation = (f"모델이 선택을 보류했습니다. {DIFFERENCES[field]} 표기는 대상 "
                       f"‘{target.get(field) or '미기재'}’, 조회 후보 예시는 ‘{observed}’입니다.")
    cited = next((p for p in passages if p["id"] == response["citationId"]), None)
    if cited:
        explanation += f" {cited['title']} {cited['locator']}의 원문은 ‘{cited['quote']}’입니다."
    return explanation


def summarize(rows):
    stages = {}
    for stage in ("sourceRecords", "withPassages"):
        stages[stage] = dict(Counter(r[stage]["verdict"] for r in rows))
    stages["localGeneration"] = dict(Counter(r["generation"]["status"] for r in rows))
    stages["validatedModelVerdicts"] = dict(Counter(r["generation"]["response"]["verdict"] for r in rows
                                                  if r["generation"]["status"] == "validated"))
    stages["publishedProposals"] = dict(Counter(r["verdict"] for r in rows))
    return stages
