"""Freeze the release recipe, evaluate its held-out split once, and verify the archived report."""

import argparse
from collections import Counter
import hashlib
from pathlib import Path
import sys
import time

import numpy as np

from assess_development import verify_record
from audit_evidence import clear_exclusion
from blind_retrieval import NameSearch
from grounded_rag import compare_records, retrieve_passages, validate_generation
from match import output_lock, read_json, save_report
from retrieval_policy import (DATA, METHODS, MODEL, OUTPUT, REVISION, ROOT, candidate_rows, catalog,
                              config, partition_rows, question_scores)
from run_local_rag import LocalLlama, digest, run
from week1_snapshot import validate_snapshot


TOOLS = Path(__file__).resolve().parent
SOURCES = (
    "retrieval_policy.py", "embed_food_names.py", "compare_dense.py", "dev_candidate_search.py",
    "blind_retrieval.py", "week1_cohort.py", "week1_snapshot.py", "assess_development.py",
    "dev_match_policy.py", "benchmark_parts.py", "benchmark_cases.py", "match.py",
    "grounded_rag.py", "run_local_rag.py", "audit_evidence.py", "release_evaluation.py",
)


def source_hash(path):
    # Git on Windows may materialize LF files as CRLF.
    return hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def passage_hash(cache):
    with np.load(cache, allow_pickle=False) as archive:
        checksum = hashlib.sha256()
        for field in ("raw_codes", "raw_vectors"):
            array = archive[field]
            checksum.update(str((field, array.shape, array.dtype.str)).encode())
            checksum.update(array.tobytes(order="C"))
        return checksum.hexdigest()


def constrain_paths(args):
    outputs = [args.output_dir / name for name in ("freeze.json", "report.json")]
    inputs = [args.snapshot, args.split, args.policy, args.passages, args.dev_rag, args.raw_vectors]
    if args.labels:
        inputs.append(args.labels)
    if {p.resolve() for p in outputs} & {p.resolve() for p in inputs}:
        raise ValueError("Use output paths distinct from the inputs.")
    summary = args.output_dir / "README.md"
    if summary.exists() and not (args.output_dir / "freeze.json").exists():
        raise ValueError("Use a separate evaluation directory; this directory contains another README.")


def release_recipe(args):
    policy, documents, dev = read_json(args.policy), read_json(args.passages), read_json(args.dev_rag)
    snapshot_id = policy["snapshotId"]
    if policy.get("method") not in METHODS or policy != config(snapshot_id, policy["method"]):
        raise ValueError("Invalid frozen retrieval policy")
    generation = dev["runConfig"]
    if (generation["snapshotId"] != snapshot_id or generation["passageHash"] != digest(documents)
            or generation["retrievalPolicy"] != policy["method"] or generation["retrievalEncoder"] != policy["model"]
            or generation["retrievalRevision"] != policy["revision"] or generation["retrievalProtocol"] != policy["protocol"]
            or not generation["model"].get("serverBuild")):
        raise ValueError("Development model, retrieval and passages must be verified before release")
    return {"protocol": "held-out-release-v1", "snapshotId": snapshot_id, "splitHash": digest(read_json(args.split)),
            "passageVectorHash": passage_hash(args.raw_vectors),
            "retrieval": policy, "generation": generation, "policyFiles": {f: source_hash(TOOLS / f) for f in SOURCES},
            "labelsHash": digest(read_json(args.labels)) if args.labels else None,
            "goldRule": "Only confirmed, blinded, independent source reviews with a reviewer and evidence. "
                        "A no-match requires exhaustive catalog review. Unreviewed targets are excluded."}


def checked_freeze(args):
    stored = read_json(args.output_dir / "freeze.json")
    recipe = release_recipe(args)
    if stored != {"fingerprint": digest(recipe), "recipe": recipe}:
        raise ValueError("Frozen release inputs changed. This release cannot be rescored with different settings.")
    return stored


def freeze(args):
    path = args.output_dir / "freeze.json"
    with output_lock(path):
        if path.exists():
            return checked_freeze(args)["fingerprint"]
        recipe = release_recipe(args)
        record = {"fingerprint": digest(recipe), "recipe": recipe}
        save_report(path, record)
        return record["fingerprint"]


def reviewed_labels(document, snapshot_id, eligible, raw_codes):
    if document is None:
        return {}
    if document.get("snapshotId") != snapshot_id or document.get("partition") != "test":
        raise ValueError("Labels belong to another snapshot or partition")
    labels, seen = {}, set()
    for row in document["reviews"]:
        code = row["targetCd"]
        if code not in eligible or code in seen:
            raise ValueError("Duplicate or non-test target in label packet")
        seen.add(code)
        if row.get("confirmed") is not True or row["status"] in ("deferred", "unreviewed"):
            continue
        if (row.get("blinded") is not True or row.get("independent") is not True
                or not str(row.get("reviewer") or "").strip() or not str(row.get("reason") or "").strip()
                or not isinstance(row.get("evidence"), list) or not row["evidence"]
                or any(not isinstance(s, str) or not s.strip() for s in row["evidence"])):
            raise ValueError("Confirmed release labels require an independent reviewer and source citations")
        choices = row["selections"]
        codes = [choice["foodCd"] for choice in choices]
        if (row["status"] not in {"matched", "no_match"} or bool(codes) != (row["status"] == "matched")
                or len(codes) != len(set(codes)) or not set(codes) <= raw_codes
                or any(c.get("verdict") not in {"직접 비교", "참고 비교"} for c in choices)
                or (row["status"] == "no_match" and row.get("exhaustive") is not True)):
            raise ValueError("Invalid confirmed label or unsubstantiated whole-catalog no-match")
        labels[code] = row
    return labels


def score_rows(rows, gold):
    decisions = Counter(r["verdict"] for r in rows)
    ranks, selected_assessed, errors = [], 0, []
    for row in rows:
        code, selected = row["targetCd"], row["selectedCd"]
        label = gold.get(code)
        choices = {c["foodCd"]: c["verdict"] for c in label["selections"]} if label else {}
        if choices:
            rank = next((i for i, c in enumerate(row["candidates"], 1) if c["record"]["foodCd"] in choices), None)
            ranks.append({"targetCd": code, "firstCorrectRank": rank})
        if not selected:
            continue
        candidate = next(c["record"] for c in row["candidates"] if c["record"]["foodCd"] == selected)
        contradiction = clear_exclusion(row["target"], candidate)
        covered = label is not None and (selected in choices or label.get("exhaustive") is True)
        if covered or contradiction:
            selected_assessed += 1
        if contradiction:
            errors.append({"targetCd": code, "selectedCd": selected, "issue": "source_field_conflict",
                           "field": contradiction[0], "values": contradiction[1]})
        elif covered and choices.get(selected) != row["verdict"]:
            errors.append({"targetCd": code, "selectedCd": selected, "issue": "reviewed_code_or_tier_mismatch"})
    found = [r["firstCorrectRank"] for r in ranks if r["firstCorrectRank"] is not None]
    n, judged, positive = len(rows), len(gold), len(ranks)
    return {"queryCount": n, "proposedSelections": sum(count for key, count in decisions.items() if key != "보류"),
            "verdicts": {k: decisions[k] for k in ("직접 비교", "참고 비교", "보류")},
            "independentlyJudged": judged, "matchedGold": positive, "verifiedNoMatch": judged - positive,
            "unjudged": n - judged, "recallAt5": {"hits": len(found), "eligible": positive,
                "rate": len(found) / positive if positive else None},
            "firstCorrectRanks": ranks, "meanFirstCorrectRankAmongHits": sum(found) / len(found) if found else None,
            "mrrAt5": sum(1 / r for r in found) / positive if positive else None,
            "checkedSelections": selected_assessed, "verifiedWrongSelections": len(errors),
            "wrongSelectionRateAmongChecked": len(errors) / selected_assessed if selected_assessed else None,
            "wrongSelections": errors}


def markdown_report(report):
    metrics, generation = report["metrics"], report["localInference"]
    recall = metrics["recallAt5"]
    score = (f"{recall['hits']}/{recall['eligible']}건" if recall["eligible"] else "평가 가능한 정답 0건으로 산출 불가")
    errors = (f"{metrics['verifiedWrongSelections']}/{metrics['checkedSelections']}건" if metrics["checkedSelections"]
              else "정답 또는 명시적 충돌로 검증 가능한 선택 0건으로 산출 불가")
    lines = ["# 동결 식품 매칭 최종 평가", "",
             f"{report['familyCount']}개 식품군의 개발 미사용 {metrics['queryCount']}건을 "
             f"생것 {report['retrieval']['rawCount']:,}개에서 검색했습니다. 식품군 안에서 최대 3개를 먼저 고르고 "
             "전체 E5 검색에서 중복을 제외해 5개를 채웠습니다.", "",
             f"- 직접 비교 제안 {metrics['verdicts']['직접 비교']}건, 참고 비교 제안 {metrics['verdicts']['참고 비교']}건, "
             f"보류 {metrics['verdicts']['보류']}건입니다. 승인은 별도 검수 절차입니다.",
             f"- 독립 검수 {metrics['independentlyJudged']}건, 카탈로그 전체에서 적합 후보가 없다고 검증된 질의 "
             f"{metrics['verifiedNoMatch']}건, 적합 여부 미판정 {metrics['unjudged']}건입니다.",
             f"- 검증된 정답의 상위 5개 회수율은 {score}입니다. 검증한 선택 중 오연결 비율은 {errors}입니다.",
             f"- 로컬 생성 결과는 {', '.join(f'{k} {v}건' for k, v in generation['localGeneration'].items())}입니다. "
             f"외부 추론 호출은 {generation['externalRequests']}회입니다.",
             f"- 검색 순위 구성에 {report['retrieval']['rankingSeconds']:.3f}초가 걸렸습니다. "
             f"시작·모델 및 인덱스 로드·질의 임베딩·조회까지 {report['retrieval']['startupEncodingAndRetrievalSeconds']:.3f}초입니다.", ""]
    for key, title in (("modelAndCacheWrite", "로컬 모델 응답과 캐시 저장"), ("warmCacheRead", "같은 결과의 캐시 파일 읽기")):
        sample = generation[key]
        if sample["count"]:
            lines.append(f"{title} 중앙값은 {sample['medianMs']:,.2f}ms ({sample['count']}건)입니다.")
    lines += ["", "## 원문을 다시 확인할 사례", ""]
    examples = []
    # Describe one case per observed failure mode, with the actual candidate and source fields.
    for row in report["cases"]:
        if row["verdict"] != "보류" or not row["candidates"]:
            continue
        candidate = next((c for c in row["candidates"] if c["assessment"] == "conflict"), row["candidates"][0])
        target, raw = row["target"], candidate["record"]
        if target["basis"] != raw["basis"]:
            problem, followup = "기준량", "원천의 같은 기준량 자료 또는 공식 환산 근거를 확인합니다."
        elif target["lv4Cd"] != raw["lv4Cd"]:
            problem, followup = "품목", "생것 카탈로그의 해당 품목·별칭 및 검색 순위를 확인합니다."
        elif candidate["assessment"] == "conflict":
            problem, followup = "관측 조건", "충돌이 없는 다른 원문 관측을 확인합니다."
        else:
            problem, followup = "세부 원료", "가공 직전 원료·품종·부위를 특정할 공식 자료를 확인합니다."
        if problem in examples:
            continue
        examples.append(problem)
        lines += [f"**{problem}** · {target['foodNm']} (`{row['targetCd']}`) → "
                  f"{raw['foodNm']} (`{raw['foodCd']}`, {candidate['rank']}위). {candidate['reason']} {followup}", ""]
        if len(examples) == 4:
            break
    if not examples:
        lines += ["보류된 후보 사례가 없습니다.", ""]
    lines += ["[32건별 원문·후보 5개·판정·생성 응답](report.json) · [동결 설정](freeze.json) · "
              "[전체 식품 원본](../raw-snapshot.json) · [인용 문단](../evidence/passages.json)", "",
              f"동결 설정 해시 `{report['fingerprint']}`", ""]
    return "\n".join(lines)


def audit(report, frozen, args):
    content = {k: v for k, v in report.items() if k != "contentHash"}
    if (report["fingerprint"] != frozen["fingerprint"] or report["contentHash"] != digest(content)
            or report["runConfig"] != frozen["recipe"]["generation"]):
        raise ValueError("Archived output differs from frozen recipe or content hash")
    snapshot, split = read_json(args.snapshot), read_json(args.split)
    validate_snapshot(snapshot)
    if snapshot["snapshotId"] != frozen["recipe"]["snapshotId"]:
        raise ValueError("Wrong release snapshot")
    entries = partition_rows(snapshot, split, "test")
    expected = [e["targetCd"] for e, _ in entries]
    if expected != [row["targetCd"] for row in report["cases"]] or len(report["cases"]) != 32:
        raise ValueError("Release must cover all 32 held-out targets once")
    if report["familyCount"] != len({e["familyCode"] for e, _ in entries}) or report["familyCount"] != 14:
        raise ValueError("Release must cover all 14 held-out families")
    documents = read_json(args.passages)["passages"]
    originals = {r["food_cd"]: r for r in snapshot["rows"]}
    for row in report["cases"]:
        if row["target"]["foodCd"] != row["targetCd"]:
            raise ValueError("Archived target and source code differ")
        verify_record(row["target"], originals, False)
        candidates = [c["record"] for c in row["candidates"]]
        if len(candidates) > frozen["recipe"]["retrieval"]["k"] or len(set(c["foodCd"] for c in candidates)) != len(candidates):
            raise ValueError("Invalid release candidate list")
        for raw in candidates:
            verify_record(raw, originals, True)
        docs = retrieve_passages(row["target"], documents)
        _, checked = compare_records(row["target"], candidates, docs, len(row["boundaryTieCodes"]))
        if (row["passageIds"] != [d["id"] for d in docs]
                or any(row[key] != checked[key] for key in ("selectedCd", "verdict", "reason", "evidenceSource"))):
            raise ValueError(f"Archived decision cannot be traced to frozen records: {row['targetCd']}")
        generated = row["generation"]
        if generated["status"] == "validated":
            validate_generation(generated["response"], row["target"], candidates, docs, checked)
    raw_codes = {c for c, r in originals.items() if r["food_lv7cd"] == "01"}
    gold = reviewed_labels(read_json(args.labels) if args.labels else None, snapshot["snapshotId"], set(expected), raw_codes)
    if score_rows(report["cases"], gold) != report["metrics"]:
        raise ValueError("Archived metrics do not reproduce")
    return report["metrics"]


def evaluate(args, frozen):
    path = args.output_dir / "report.json"
    if path.exists():
        return audit(read_json(path), frozen, args)
    client = LocalLlama(args.endpoint)
    # Verify weights/backend before any evaluation query is sent to the encoder.
    if client.verify() != frozen["recipe"]["generation"]["model"]:
        raise ValueError("Local runtime differs from frozen development model")
    started = time.perf_counter()
    snapshot, split, index, encoder, passages, meta, _ = catalog(args)
    entries = partition_rows(snapshot, split, "test")
    scores = question_scores(entries, encoder, meta, passages)
    lexical = NameSearch([r["food_nm"] for r in index.raw])
    ranking, rank_seconds = candidate_rows(index, entries, scores, frozen["recipe"]["retrieval"]["method"], snapshot, split, lexical)
    elapsed = time.perf_counter() - started
    identifiers = {r["target"]["foodCd"]: [c["record"]["foodCd"] for c in r["boundaryTies"]] for r in ranking["results"]}
    gold = reviewed_labels(read_json(args.labels) if args.labels else None, snapshot["snapshotId"],
                           {e["targetCd"] for e, _ in entries}, {r["food_cd"] for r in index.raw})
    outcome = run(ranking, read_json(args.passages), snapshot, client, args.cache_dir)
    rows = [{**row, "boundaryTieCodes": identifiers[row["targetCd"]]} for row in outcome["results"]]
    content = {"protocol": "held-out-release-v1", "snapshotId": snapshot["snapshotId"], "partition": "test",
               "fingerprint": frozen["fingerprint"], "familyCount": ranking["familyCount"], "runConfig": outcome["runConfig"],
               "retrieval": {"method": ranking["policy"], "encoder": MODEL, "revision": REVISION,
                             "rawCount": ranking["rawCount"], "startupEncodingAndRetrievalSeconds": elapsed,
                             "rankingSeconds": rank_seconds},
               "metrics": score_rows(rows, gold), "localInference": outcome["summary"], "cases": rows}
    report = {**content, "contentHash": digest(content)}
    metrics = audit(report, frozen, args)
    save_report(path, report)
    return metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("freeze", "evaluate", "verify"))
    parser.add_argument("--snapshot", type=Path, default=DATA / "raw-snapshot.json")
    parser.add_argument("--split", type=Path, default=DATA / "review/split-manifest.json")
    parser.add_argument("--policy", type=Path, default=OUTPUT / "policy.json")
    parser.add_argument("--passages", type=Path, default=DATA / "evidence/passages.json")
    parser.add_argument("--dev-rag", type=Path, required=True)
    parser.add_argument("--raw-vectors", type=Path, default=ROOT / "backend/build/e5-small-vectors.npz")
    parser.add_argument("--model-dir", type=Path, default=ROOT / "backend/build/models/multilingual-e5-small" / REVISION)
    parser.add_argument("--labels", type=Path, help="Independent, blinded release reviews supplied before freezing")
    parser.add_argument("--output-dir", type=Path, default=DATA / "release")
    parser.add_argument("--endpoint", default="http://127.0.0.1:18081")
    parser.add_argument("--cache-dir", type=Path, default=ROOT / "backend/build/local-rag-cache")
    args = parser.parse_args()
    constrain_paths(args)
    if args.action == "freeze":
        print(freeze(args))
        return
    frozen = checked_freeze(args)
    path = args.output_dir / "report.json"
    if args.action == "verify":
        report = read_json(path)
        metrics = audit(report, frozen, args)
        if (args.output_dir / "README.md").read_text(encoding="utf-8") != markdown_report(report):
            raise ValueError("Release summary differs from archived cases")
        print(metrics)
    else:
        with output_lock(path):
            metric = evaluate(args, frozen)
            (args.output_dir / "README.md").write_text(markdown_report(read_json(path)), encoding="utf-8", newline="\n")
            print(metric)


if __name__ == "__main__":
    try:
        main()
    except (KeyError, OSError, TypeError, ValueError) as exc:
        sys.exit(f"Release evaluation failed: {exc}")
