"""Derive auditable, text-matched reference pairs from a frozen food snapshot.

These proxy labels identify a raw entry with the same recorded food identity.
They do not establish the same physical sample, a measured cooking yield or an
independently reviewed nutritional comparison. Only label construction uses
these metadata; retrieval must not receive them.
"""

from collections import Counter, defaultdict

from match import known


# Explicit elementary states in the source vocabulary. Prepared dishes,
# mixtures, added ingredients and operations requiring an intermediate state
# are outside this first benchmark.
SIMPLE_STATES = {
    "02": "말린것", "06": "분말화한것", "08": "얼린것", "34": "말린것(자연건조)",
    "46": "삶은것", "47": "데친것", "48": "끓인것", "49": "찐것", "50": "구운것",
    "51": "구운것(팬)", "52": "구운것(석쇠)", "53": "구운것(오븐)", "58": "볶은것",
    "64": "전자레인지로 가열한것",
}

REQUIRED_FIELDS = (
    "src_cd", "src_nm", "food_lv4cd", "food_lv4nm", "food_lv5cd", "food_lv6cd",
    "nut_con_srtr_qua", "impt_yn", "crtr_ymd",
)
OBSERVATION_FIELDS = ("coo_cd", "coo_nm", "food_coo_rgn_nm", "prd_coll_cap_mon")


def reference_key(row):
    """Keep identity and scope on their original sides of exactly one state token."""
    state = row["food_lv7nm"]
    if row["food_lv7cd"] == "01":
        if state != "생것":
            return None
    elif row["food_lv7cd"] not in SIMPLE_STATES or SIMPLE_STATES[row["food_lv7cd"]] != state:
        return None

    if not known(row["food_nm"]) or not all(known(row.get(key)) for key in REQUIRED_FIELDS):
        return None
    if row["impt_yn"] not in {"Y", "N"}:
        return None
    if row["impt_yn"] == "Y" and not all(known(row.get(key)) for key in ("coo_cd", "coo_nm")):
        return None
    tokens = tuple(part.strip() for part in row["food_nm"].split("_"))
    if tokens.count(state) != 1 or not all(known(token) for token in tokens):
        return None
    index = tokens.index(state)
    if not index:
        return None
    # Even missing optional values must agree as stored. Their joint absence
    # does not certify a common origin, region or collection month.
    return (tokens[:index], tokens[index + 1:],
            tuple(row[key] for key in REQUIRED_FIELDS),
            tuple(row.get(key) for key in OBSERVATION_FIELDS))


def build_reference_pairs(rows):
    """Return one reference for each target with exactly one matching raw observation."""
    candidates = defaultdict(list)
    raw_name_counts = Counter()
    targets = []
    for row in rows:
        key = reference_key(row)
        if row["food_lv7cd"] == "01":
            raw_name_counts[row["food_nm"]] += 1
            if key is not None:
                candidates[key].append(row)
        elif key is not None:
            targets.append((key, row))

    pairs = []
    for key, target in targets:
        matches = candidates.get(key, ())
        if len(matches) != 1:
            continue
        raw = matches[0]
        pairs.append({
            "targetCd": target["food_cd"], "rawCd": raw["food_cd"],
            "targetName": target["food_nm"], "rawName": raw["food_nm"],
            "familyCode": target["food_lv4cd"], "familyName": target["food_lv4nm"],
            "method": target["food_lv7nm"], "source": target["src_nm"],
            "sourceCode": target["src_cd"], "basis": target["nut_con_srtr_qua"],
            "originRecorded": known(target.get("coo_nm")), "rawNameMultiplicity": raw_name_counts[raw["food_nm"]],
            "reason": "원문에서 처리 상태만 바꾸면 품목과 관측 표기가 같고, "
                      "같은 출처·분류·기준량 및 저장된 원산지·수입·지역·월 조건에 생것이 한 건입니다.",
        })
    return sorted(pairs, key=lambda pair: pair["targetCd"])
