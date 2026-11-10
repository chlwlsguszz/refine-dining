"""Inspect explicit part conflicts in named pairs from the frozen development families.

Each reference below was read from the original food names. These purposefully
selected cases test the guard's behavior; they are not a random accuracy sample.
"""


# (target code, target original, candidate code, candidate original, part label, annotation)
PART_CASES = (
    ("R211-065034260-5311", "대구류_대구_간_조린것_수입_평균",
     "R211-065038701-5350", "대구류_대구_적색육_생것_수입_평균",
     "conflict", "같은 대구라도 간과 적색육은 서로 다른 부위다."),
    ("R106-113007647-0000", "순무_뿌리_데친것",
     "R106-113007801-0000", "순무_잎_생것",
     "conflict", "데친 원료는 순무 뿌리이고 후보는 잎이다."),
    ("R211-107034173-0000", "명태_내장_젓갈(창난젓)_대표_평균",
     "R211-107034001-1273", "명태_육_생것_강릉_평균",
     "conflict", "창난젓 행에는 내장이, 생것에는 육이 명시된다."),
    ("R211-107034037-0000", "명태_육_말린것(포)_대표_평균",
     "R211-107034301-5519", "명태_알_생것_수입_평균",
     "conflict", "포의 원료 부위는 명태 육이고 생것 후보는 명태 알이다."),
    ("R211-927034171-0000", "해삼_내장_젓갈_대표_평균",
     "R211-927034001-0000", "해삼_육_생것_대표_평균",
     "conflict", "같은 해삼 대표 평균에서도 내장과 육의 구분이 남는다."),
    ("R209-027011352-0000", "소고기_수입산(미국산)_설도_구운것(석쇠)",
     "R209-027018401-0000", "소고기_수입산(미국산)_목심(목심살)_생것",
     "conflict", "같은 미국산 소고기지만 설도와 목심의 부위명이 다르다."),
    ("R106-113007847-0000", "순무_잎_데친것",
     "R106-113007801-0000", "순무_잎_생것",
     "same_part", "데친 순무와 생순무에 모두 잎이 적혀 있다."),
    ("R209-027018446-0000", "소고기_수입산(미국산)_목심(목심살)_삶은것",
     "R209-027018401-0000", "소고기_수입산(미국산)_목심(목심살)_생것",
     "same_part", "두 기록의 목심(목심살) 표기가 같다."),
    ("R211-107034374-0000", "명태_알_젓갈(명란젓)_대표_평균",
     "R211-107034301-0000", "명태_알_생것_대표_평균",
     "same_part", "명란젓과 생것의 부위가 모두 명태 알이다."),
    ("R211-927034071-0000", "해삼_육_젓갈_대표_평균",
     "R211-927034001-0000", "해삼_육_생것_대표_평균",
     "same_part", "양쪽 원문이 모두 해삼 육을 지정한다."),
    ("R211-663094850-0896", "꼴뚜기류_창꼴뚜기_몸통_구운것_남해_평균",
     "R211-663094801-1201", "꼴뚜기류_창꼴뚜기_몸통_생것_부산_6월",
     "same_part", "창꼴뚜기 몸통이라는 표기가 일치한다. 산지·월은 별도 검토 항목이다."),
    ("R211-133013937-0000", "뱅어_전체_말린것(포)_대표_평균",
     "R211-133014001-0363", "뱅어_육_생것_군산_평균",
     "review", "전체와 육은 범위가 다르지만 서로 배타적인 부위라고 단정할 수 없다."),
    ("R106-077000023-0000", "미나리_농축",
     "R106-077037801-0000", "미나리_물미나리_잎_생것",
     "review", "농축 원문에 사용 부위가 없어 생것의 잎과 대응하는지 확인할 수 없다."),
)


FLESH = {"육", "적색육", "백색육"}
ORGANS = {"간", "내장", "알"}
PLANT_PARTS = {"잎", "뿌리", "줄기"}
BEEF_CUTS = {"설도", "목심", "갈비", "등심", "안심", "양지", "우둔", "앞다리", "사태", "채끝"}
PARTS = FLESH | ORGANS | PLANT_PARTS | BEEF_CUTS | {"몸통", "전체"}


def named_part(food_name):
    # Operate solely on original name tokens. Keep parenthetical specificity for display.
    parts = [token for token in food_name.split("_")[1:] if token.split("(", 1)[0] in PARTS]
    return parts[0] if len(parts) == 1 else None


def check_parts(target_name, candidate_name):
    left, right = named_part(target_name), named_part(candidate_name)
    if left is None or right is None:
        return "review", "한쪽의 부위가 기재되지 않았거나 한 부위로 해석하기 어렵습니다."
    if left == right:
        return "same_part", f"두 원문에 같은 부위 ‘{left}’가 적혀 있습니다."
    a, b = left.split("(", 1)[0], right.split("(", 1)[0]
    different = (
        (a in FLESH and b in ORGANS) or (a in ORGANS and b in FLESH)
        or (a != b and a in PLANT_PARTS and b in PLANT_PARTS)
        or (a != b and a in BEEF_CUTS and b in BEEF_CUTS)
    )
    if different:
        return "conflict", f"대상 ‘{left}’와 후보 ‘{right}’는 명시적으로 다른 부위입니다."
    return "review", f"‘{left}’와 ‘{right}’의 범위가 같은지 원문만으로 확정하기 어렵습니다."


def run_part_checks(rows):
    originals = {row["food_cd"]: row for row in rows}
    cases = []
    for target_cd, target_name, raw_cd, raw_name, expected, explanation in PART_CASES:
        target, raw = originals.get(target_cd), originals.get(raw_cd)
        if (not target or not raw or target["food_nm"] != target_name or raw["food_nm"] != raw_name
                or target["food_lv7cd"] == "01" or raw["food_lv7cd"] != "01"):
            raise ValueError(f"Frozen source reference is missing or has changed: {target_cd} / {raw_cd}")
        status, reason = check_parts(target["food_nm"], raw["food_nm"])
        cases.append({
            "targetCd": target_cd, "rawCd": raw_cd, "targetName": target_name, "rawName": raw_name,
            "expectedStatus": expected, "guardStatus": status,
            "expectedConflict": None if expected == "review" else expected == "conflict",
            "flagged": status == "conflict", "reason": reason, "sourceRationale": explanation,
        })
    negatives = [c for c in cases if c["expectedStatus"] == "conflict"]
    controls = [c for c in cases if c["expectedStatus"] == "same_part"]
    uncertain = [c for c in cases if c["expectedStatus"] == "review"]
    metrics = {
        "conflictPairs": len(negatives), "detectedConflicts": sum(c["flagged"] for c in negatives),
        "missedConflicts": sum(not c["flagged"] for c in negatives),
        "controlPairs": len(controls), "falseFlags": sum(c["flagged"] for c in controls),
        "samePartRecognized": sum(c["guardStatus"] == "same_part" for c in controls),
        "uncertainPairs": len(uncertain), "uncertainDeferred": sum(c["guardStatus"] == "review" for c in uncertain),
    }
    return {
        "scope": "동결 DB 원문의 명시적 부위만 점검한 개발 사례입니다. 같은 부위여도 품종·산지·기준량 등은 별도 확인해야 합니다.",
        "metrics": metrics, "cases": cases,
    }
