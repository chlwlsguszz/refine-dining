"""Score predeclared external cooking experiments through the running weight API."""

import argparse
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path
import sys
from urllib.request import ProxyHandler, Request, build_opener


ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "datasets/cooking-yield/evaluation"
METHODS = {
    "broil": "브로일",
    "griddle": "팬구이",
    "grill": "그릴구이",
    "microwave": "전자레인지 조리",
    "reheat": "브로일 후 냉동 및 전자레인지 재가열",
}


def read_json(raw):
    return json.loads(raw, parse_float=Decimal)


def call(api, url, payload=None):
    body = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
    req = Request(url, data=body, headers={"Content-Type": "application/json; charset=utf-8"})
    with api.open(req, timeout=10) as response:
        return read_json(response.read())


def mean_error(errors):
    if not errors:
        return None
    return float((sum(errors) / len(errors)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def evaluate(url):
    corpus = (DATA / "external-observations.json").read_bytes()
    api = build_opener(ProxyHandler({}))
    endpoint = url.rstrip("/") + "/api/weight/predict"
    results = []
    for group in read_json(corpus)["cohorts"]:
        rows, method_errors, baseline_errors = [], [], []
        for case in group["cases"]:
            query = {"foodName": "소고기 패티", "cookingMethod": METHODS[case["method"]],
                     "baseWeight": float(group["baseWeight"])}
            initial = call(api, endpoint, query)
            if initial.get("predictedWeight") is not None or initial["status"] not in {"NEED_CONDITIONS", "NO_MATCH"}:
                raise ValueError(f"An unconfirmed request received an estimate: {case['id']}")
            result = {"id": case["id"], "query": query, "observed": float(case["observed"]),
                      "initialStatus": initial["status"], "confirmedEvidenceId": None,
                      "predicted": None, "absoluteError": None}
            candidates = {row["id"] for row in initial["candidates"]}
            condition = case["condition"]
            if condition is None or condition not in candidates:
                result["outcome"] = initial["status"] if condition is None else "REFERENCE_UNAVAILABLE"
            else:
                selected = call(api, endpoint, {**query, "evidenceId": condition})
                if selected["status"] != "ESTIMATED" or selected["evidence"]["id"] != condition:
                    raise ValueError(f"Confirmed weight did not use the selected row: {case['id']}")
                predicted = Decimal(selected["predictedWeight"])
                observed = Decimal(case["observed"])
                error = abs(predicted - observed)
                result.update(outcome="ESTIMATED", confirmedEvidenceId=condition,
                              predicted=float(predicted), absoluteError=float(error),
                              referencePercent=float(selected["yieldPercent"]),
                              referenceVersion=selected["evidence"]["version"],
                              referenceRow=selected["evidence"]["sourceRow"])
                method_errors.append(error)
                fixed = (Decimal(group["baseWeight"]) * Decimal("0.70")).quantize(
                    Decimal("0.1"), rounding=ROUND_HALF_UP)
                baseline_errors.append(abs(fixed - observed))
            rows.append(result)
        results.append({"id": group["id"], "measure": group["measure"], "groups": len(rows),
                        "estimatedGroups": len(method_errors), "notEstimatedGroups": len(rows) - len(method_errors),
                        "meanAbsoluteError": mean_error(method_errors),
                        "fixed70PercentMaeOnIdenticalGroups": mean_error(baseline_errors),
                        "rows": rows})
    return {"observationsSha256": hashlib.sha256(corpus).hexdigest(), "engine": "POST /api/weight/predict",
            "comparisonLevel": "External, broad cooking-method groups; individual errors unavailable.",
            "allGroups": sum(g["groups"] for g in results),
            "estimatedGroupsAfterEvidenceSelection": sum(g["estimatedGroups"] for g in results),
            "cohorts": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:18082")
    parser.add_argument("--output", type=Path, default=DATA / "external-results.json")
    args = parser.parse_args()
    if args.output.resolve() == (DATA / "external-observations.json").resolve():
        parser.error("Choose a different path for results.")
    result = evaluate(args.base_url)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    for group in result["cohorts"]:
        print(f"{group['id']}: {group['estimatedGroups']}/{group['groups']}, "
              f"MAE ({group['measure']}) = {group['meanAbsoluteError']}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError) as exc:
        sys.exit(f"Could not evaluate the weight API: {exc}")
