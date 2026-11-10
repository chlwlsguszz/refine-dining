"""Freeze the cross-subcategory discovery cohort and produce a blind development review packet."""

from collections import Counter, defaultdict
import hashlib
import json
import unicodedata


DEFAULT_SEED = 20261110
PROTOCOL = "week1-family-split-v2"
PRIOR_STATE = {"83": "02", "84": "02", "85": "04", "86": "04", "88": "08"}
STRATA = {"same_lv5": "동일 출처·중분류의 다른 소분류",
          "lv4_only": "동일 출처·대표식품의 다른 중분류"}
FIELDS = {
    "foodCd": "food_cd", "foodNm": "food_nm", "srcCd": "src_cd", "srcNm": "src_nm",
    "lv4Cd": "food_lv4cd", "lv4Nm": "food_lv4nm", "lv5Cd": "food_lv5cd",
    "lv5Nm": "food_lv5nm", "lv6Cd": "food_lv6cd", "lv6Nm": "food_lv6nm",
    "lv7Cd": "food_lv7cd", "lv7Nm": "food_lv7nm", "basis": "nut_con_srtr_qua",
    "region": "food_coo_rgn_nm", "country": "coo_nm", "month": "prd_coll_cap_mon",
    "imported": "impt_yn", "production": "data_prod_nm", "referenceDate": "crtr_ymd",
}


def digest(value):
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def display_record(row):
    return {**{label: row.get(column) for label, column in FIELDS.items()}, "rawFields": row}


def eligible(row):
    name, subcategory = row["food_nm"], row["food_lv6cd"]
    return (name is not None and subcategory is not None and subcategory.strip()
            and (row["src_cd"] != "2" or ("대표" in name and "평균" in name)))


def source_group(row):
    return row["src_cd"], row["food_lv4cd"]


def discover(rows):
    codes = [row["food_cd"] for row in rows]
    if any(not isinstance(code, str) or not code.strip() for code in codes) or len(codes) != len(set(codes)):
        raise ValueError("Raw snapshot contains missing or duplicate food codes.")
    raw_foods = sorted((r for r in rows if r["food_lv7cd"] == "01"), key=lambda r: r["food_cd"])
    all_raw_subcategories = {r["food_lv6cd"] for r in raw_foods}
    pools = defaultdict(list)
    for raw in raw_foods:
        key = source_group(raw)
        if None not in key:
            pools[key].append(raw)
    preceding = Counter((r["src_cd"], r["food_lv6cd"], r["nut_con_srtr_qua"], r["food_lv7cd"])
                        for r in rows if r["food_lv7cd"] in PRIOR_STATE.values())

    targets = []
    for row in sorted(rows, key=lambda item: item["food_cd"]):
        # Even a raw parent discarded by the seafood name filter removes a group
        # from this cohort. It belongs to the earlier same-subcategory experiment.
        if not eligible(row) or row["food_lv6cd"] in all_raw_subcategories:
            continue
        candidates = pools.get(source_group(row))
        if not candidates:
            continue
        prev_code = PRIOR_STATE.get(row["food_lv7cd"])
        if prev_code and row["nut_con_srtr_qua"] is not None:
            key = row["src_cd"], row["food_lv6cd"], row["nut_con_srtr_qua"], prev_code
            if preceding[key] == 1:
                continue
        middle = row["food_lv5cd"]
        same_middle = sum(c["food_lv5cd"] == middle for c in candidates) if middle is not None else 0
        stratum = "same_lv5" if same_middle else "lv4_only"
        targets.append((row, candidates, stratum, same_middle))
    return raw_foods, targets


def family_codes(rows):
    """Group on official Lv4 code across sources; also unite identical official names."""
    parents = {row["food_lv4cd"]: row["food_lv4cd"] for row in rows}
    names = {}

    def root(code):
        while parents[code] != code:
            parents[code] = parents[parents[code]]
            code = parents[code]
        return code

    for row in rows:
        code = row["food_lv4cd"]
        name = "".join(unicodedata.normalize("NFKC", row.get("food_lv4nm") or "").casefold().split())
        if name and name not in {"-", "미상", "해당없음"}:
            a, b = root(code), root(names.setdefault(name, code))
            parents[max(a, b)] = min(a, b)
    return {code: root(code) for code in parents}


def held_out_families(entries, review_size, seed):
    """Hold out 30% of entire families, balancing query strata before source coverage."""
    totals = Counter(row["stratumId"] for row in entries)
    sources = Counter(row["srcCd"] for row in entries)
    by_family = defaultdict(list)
    for row in entries:
        by_family[row["familyCode"]].append(row)
    count = max(1, round(len(by_family) * 0.30))
    best = None
    result = None
    for attempt in range(512):
        ordered = sorted(by_family, key=lambda code: digest([seed, "test", attempt, code]))
        selection = ordered[:count]
        held = [row for family in selection for row in by_family[family]]
        strata = Counter(row["stratumId"] for row in held)
        if len(entries) - len(held) < review_size or any(strata[s] == n for s, n in totals.items()):
            continue
        source = Counter(row["srcCd"] for row in held)
        score = (sum((strata[s] / n - 0.30) ** 2 for s, n in totals.items()),
                 sum((source[s] / n - 0.30) ** 2 for s, n in sources.items()))
        if best is None or score < best:
            best, result = score, set(selection)
    if not result:
        raise ValueError("Insufficient separate families for both review and evaluation.")
    return result


def choose_review(entries, development, size, seed):
    """Proportional stratum quotas, then spread cases over families and sources."""
    totals = Counter(row["stratumId"] for row in entries)
    available = Counter(row["stratumId"] for row in development)
    quotas = Counter()
    for _ in range(size):
        possible = [s for s in totals if quotas[s] < available[s]]
        if not possible:
            raise ValueError("Insufficient development targets for the requested review size.")
        selected = max(possible, key=lambda s: (size * totals[s] / len(entries) - quotas[s], s))
        quotas[selected] += 1

    source_totals = Counter(row["srcCd"] for row in entries)
    chosen = set()
    used_families, used_sources, used_strata = Counter(), Counter(), Counter()
    for step in range(1, size + 1):
        active = [s for s in quotas if used_strata[s] < quotas[s]]
        stratum = max(active, key=lambda s: (step * quotas[s] / size - used_strata[s], s))
        options = (row for row in development if row["targetCd"] not in chosen and row["stratumId"] == stratum)
        row = min(options, key=lambda item: (
            used_families[item["familyCode"]],
            used_sources[item["srcCd"]] - step * source_totals[item["srcCd"]] / len(entries),
            digest([seed, "dev", item["targetCd"]]),
        ))
        chosen.add(row["targetCd"])
        used_families[row["familyCode"]] += 1
        used_sources[row["srcCd"]] += 1
        used_strata[stratum] += 1
    return chosen


def build_packet(rows, snapshot_id, seed=DEFAULT_SEED, review_size=20):
    if not snapshot_id or review_size < 1:
        raise ValueError("A snapshot ID and positive review size are required.")
    raw_foods, targets = discover(rows)
    families = family_codes([row for row, _, _, _ in targets])
    family_names = defaultdict(set)
    for row, _, _, _ in targets:
        if row.get("food_lv4nm"):
            family_names[families[row["food_lv4cd"]]].add(row["food_lv4nm"])
    entries = []
    by_code = {}
    for row, candidates, stratum, same_middle in targets:
        family = families[row["food_lv4cd"]]
        entry = {label: row.get(FIELDS[label]) for label in
                 ("srcCd", "srcNm", "lv4Cd", "lv4Nm", "lv5Cd", "lv5Nm",
                  "lv6Cd", "lv6Nm", "lv7Cd", "lv7Nm", "basis")}
        entry.update(targetCd=row["food_cd"], targetNm=row["food_nm"], familyCode=family,
                     family=(" / ".join(sorted(family_names[family])) or family) + f" [{family}]",
                     stratumId=stratum, stratum=STRATA[stratum], candidateCount=len(candidates),
                     sameLv5CandidateCount=same_middle)
        entries.append(entry)
        by_code[entry["targetCd"]] = (row, candidates)
    held_out = held_out_families(entries, review_size, seed)
    development = [e for e in entries if e["familyCode"] not in held_out]
    review = choose_review(entries, development, review_size, seed)
    cases = []
    for entry in entries:
        code = entry["targetCd"]
        if code in review:
            entry["split"] = "dev_review"
            row, candidates = by_code[code]
            # Randomized deterministic presentation; no prior matcher evidence or ranking.
            ordered = sorted((c["food_cd"] for c in candidates), key=lambda c: digest([seed, code, c]))
            cases.append({"target": display_record(row), "candidateCds": ordered,
                          "stratum": entry["stratum"], "family": entry["family"]})
        else:
            entry["split"] = "test" if entry["familyCode"] in held_out else "dev_remaining"
    manifest = {"protocol": PROTOCOL, "snapshotId": snapshot_id, "seed": seed, "totalTargets": len(entries),
                "splitCounts": dict(Counter(e["split"] for e in entries)),
                "stratumCounts": dict(Counter(e["stratumId"] for e in entries)), "rows": entries}
    packet = {"protocol": PROTOCOL, "snapshotId": snapshot_id, "seed": seed,
              "cases": cases, "catalog": [display_record(row) for row in raw_foods]}
    packet["packetId"] = digest(packet)
    return manifest, packet
