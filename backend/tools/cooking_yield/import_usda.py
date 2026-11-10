"""Build the measured cooking-yield catalog from the pinned USDA workbook (Python 3, stdlib)."""

import argparse
import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WORKBOOK = ROOT / "datasets/cooking-yield/USDA_CookingYields_MeatPoultry02.xlsx"
OUTPUT = ROOT / "backend/src/main/resources/cooking-yields.json"
BASE = "https://www.ars.usda.gov/ARSUserFiles/80400535/Data/retn/USDA_CookingYields_MeatPoultry02"
SHA256 = "13bd2cec633841867bf8532ed57114c81f3791b9bcd35a396dec6a1b960773ff"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def workbook_rows(path):
    if hashlib.sha256(path.read_bytes()).hexdigest() != SHA256:
        raise ValueError("Workbook checksum changed. Review the release and mappings before importing.")
    with zipfile.ZipFile(path) as archive:
        strings = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        shared = ["".join(t.text or "" for t in item.iter(NS + "t")) for item in strings]
        sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    for row in sheet.iter(NS + "row"):
        data = {}
        for cell in row.findall(NS + "c"):
            value = cell.findtext(NS + "v")
            if value is not None:
                col = re.match(r"[A-Z]+", cell.attrib["r"])[0]
                data[col] = shared[int(value)].strip() if cell.get("t") == "s" else value
        yield int(row.attrib["r"]), data


def number(raw):
    if raw is None or raw == "n/a":
        return None
    value = float(raw)
    if not math.isfinite(value):
        raise ValueError(f"Invalid source number: {raw}")
    return int(value) if value.is_integer() else value


# These are search terms. Acceptance requires the user to confirm the listed conditions.
# A Korean raw-food code narrows candidates; a code alone never establishes equivalence.
METHODS = {
    "roast": ("오븐구이", ["오븐구이", "구운것(오븐)", "오븐에 구운것", "로스트", "로스팅", "구운것"]),
    "simmer": ("약한 불로 삶기", ["삶은것", "삶기", "약불 삶기", "시머링"]),
    "braise": ("소량의 물로 뚜껑 덮어 익히기", ["조림", "조린것", "브레이징"]),
    "grill": ("그릴·브로일 구이", ["그릴구이", "직화구이", "브로일", "구운것"]),
    "dry_pan": ("기름 없는 팬구이", ["팬구이", "구운것(팬)", "팬에 구운것", "기름 없는 팬구이", "구운것"]),
    "saute": ("팬에 볶기", ["볶은것", "볶기", "팬볶음"]),
    "pan_fry": ("팬에 지지기", ["팬에 지지기", "팬구이", "구운것(팬)", "팬에 구운것", "구운것"]),
}
CHICKEN = {
    "breast": ("닭 가슴", ["닭가슴", "닭고기 가슴", "닭가슴 껍질 포함"], []),
    "drum": ("닭 아랫다리", ["닭 아랫다리", "닭 북채", "닭고기 아랫다리", "닭고기_아랫다리_생것"], ["R209-008006301-0000"]),
    "thigh": ("닭 넓적다리", ["닭 넓적다리", "닭고기 넓적다리", "닭고기_넓적다리_생것"], ["R209-008000701-0000"]),
    "wing": ("닭 날개", ["닭 날개", "닭고기 날개", "닭고기_날개_생것"], ["R209-008000601-0000"]),
}
POULTRY_ROWS = {
    5060: ("breast", "roast"), 5061: ("breast", "simmer"),
    5069: ("drum", "roast"), 5676: ("drum", "braise"),
    5094: ("thigh", "roast"), 5095: ("thigh", "simmer"), 5677: ("thigh", "braise"),
    5103: ("wing", "roast"), 5104: ("wing", "simmer"),
}
# USDA's thresholds are different for beef and pork.
BEEF_FAT = ("지방 12% 미만", "지방 12~22%", "지방 22% 초과")
PORK_FAT = ("지방 10% 미만", "지방 10~27%", "지방 27% 초과")
PORK_LOIN_ALIASES = ["돼지 등심", "돼지고기 등심", "돼지고기_등심_생것", "포크찹"]
PORK_LOIN_CODE = ["R209-014008301-0000"]


def korean_mappings():
    """Specify only audited source rows, separately from the workbook's numeric measurements."""
    mappings = {}
    for ndb, (part, method) in POULTRY_ROWS.items():
        label, aliases, codes = CHICKEN[part]
        basis = "껍질이 붙은 해당 생부위의 조리 직전 중량. 표에는 뼈 포함 여부가 명시되지 않았습니다."
        condition = "조리 전후 동일한 부위와 껍질 포함 상태로 계량합니다. 순살이나 가식부만의 중량은 별도 측정하세요."
        if ndb in {5676, 5677}:
            basis = "뼈와 껍질을 포함한 생부위 전체 중량. 조리 후에도 뼈를 발라내기 전에 계량했습니다."
            condition += " 연구에서는 물 100mL를 넣은 덮개 있는 팬에 익혀 5분 식힌 뒤 계량했습니다."
        elif method == "roast" and ndb != 5103:
            condition += " 원자료에는 오븐 온도와 시간이 없습니다."
        mappings[ndb] = (label + " (껍질 포함)", method, condition, basis, aliases, codes)

    # The published worksheet classifies grilled/broiled beef patties together, but
    # its study protocol describes oven broiling. Make that distinction visible.
    for ids, shape, method in [
        ((23564, 23574, 13496), "패티", "dry_pan"),
        ((23563, 23573, 13497), "패티", "grill"),
        ((23565, 23575, 13494), "부스러기", "saute"),
    ]:
        aliases = ["소고기 패티", "쇠고기 패티", "다진 소고기 패티", "소고기 햄버거 패티"] if shape == "패티" else ["다진 소고기", "소고기 다짐육", "소고기 분쇄육"]
        protocol = {
            "dry_pan": "기름 없이 전기 팬에서 약 11.75분, 중심 71°C까지 가열한 패티.",
            "grill": "자료의 조리법 범주는 브로일·그릴이고 연구의 패티는 예열한 오븐에서 브로일해 중심 71°C에 도달했습니다.",
            "saute": "팬에 잘게 풀어 볶은 뒤 체에 밭쳐 기름을 뺀 상태.",
        }[method]
        for ndb, fat in zip(ids, BEEF_FAT):
            mappings[ndb] = (
                f"다진 소고기 {shape} ({fat})", method, f"{fat}. {protocol}",
                "부재료를 섞지 않은 생 소고기 분쇄육 중량.", aliases, [],
            )

    for ids, shape, method in [
        ((10979, 10978, 10977), "패티", "dry_pan"),
        ((10976, 10975, 10974), "부스러기", "saute"),
    ]:
        aliases = ["돼지고기 패티", "다진 돼지고기 패티"] if shape == "패티" else ["다진 돼지고기", "돼지고기 다짐육", "돼지고기 분쇄육"]
        protocol = (
            "표에는 브로일·그릴로 분류되며 연구에서는 전기 팬에서 중심 74°C까지 구워 5분 뒤 계량했습니다."
            if shape == "패티" else "전기 팬에서 잘게 풀어 중심 74°C까지 볶고 체에 밭쳐 기름을 뺀 뒤 5분 뒤 계량했습니다."
        )
        for ndb, fat in zip(ids, PORK_FAT):
            mappings[ndb] = (
                f"다진 돼지고기 {shape} ({fat})", method, f"{fat}. {protocol}",
                "부재료를 섞지 않은 생 돼지고기 분쇄육 중량.", aliases, [],
            )

    for ndb, cut, method, bone in [
        (10037, "센터 로인", "braise", True), (10179, "센터 로인", "pan_fry", True),
        (10063, "톱 로인", "braise", False), (10186, "톱 로인", "pan_fry", False),
    ]:
        trim = "뼈 포함" if bone else "뼈 제거"
        label = f"돼지 등심 찹 ({cut}, {trim})"
        mappings[ndb] = (
            label, method, f"미국식 {cut} 찹 한 조각. {trim} 상태와 지방을 포함하는 조건을 확인하세요.",
            f"조리 전 찹 한 조각의 중량({trim}, 살·지방 포함).", PORK_LOIN_ALIASES, PORK_LOIN_CODE,
        )
    return mappings


def yield_statistics(row):
    mean = number(row["E"])
    lower, upper = number(row.get("H")), number(row.get("I"))
    count = number(row.get("F"))
    if mean is None or mean <= 0 or (lower is None) != (upper is None):
        raise ValueError(f"Invalid cooking yield statistics for NDB {row['B']}")
    if lower is not None and not (0 < lower <= mean <= upper):
        raise ValueError(f"Mean outside observed range for NDB {row['B']}")
    if count is not None and (not isinstance(count, int) or count < 1):
        raise ValueError(f"Invalid sample count for NDB {row['B']}")
    return dict(meanPercent=mean, minPercent=lower, maxPercent=upper, sampleCount=count)


def build_catalog(path):
    mappings = korean_mappings()
    records = []
    for row_number, row in workbook_rows(path):
        if row_number == 1:
            expected = {"B": "NDB", "C": "Yield Description", "E": "Cooking Yield %", "F": "n", "H": "Yield Minimum %", "I": "Yield Maximum %"}
            if any(row.get(col) != name for col, name in expected.items()):
                raise ValueError("Unexpected workbook schema")
            continue
        if not row.get("B", "").isdigit() or int(row["B"]) not in mappings:
            continue
        ndb = int(row["B"])
        food, method, conditions, basis, aliases, codes = mappings.pop(ndb)
        method_label, method_aliases = METHODS[method]
        records.append({
            "id": f"usda-r2-{ndb:05d}", "foodLabel": food, "methodLabel": method_label,
            "conditions": conditions, "rawBasis": basis,
            **yield_statistics(row),
            "sourceRow": f"Sheet1!A{row_number}:L{row_number}", "sourceNdb": f"{ndb:05d}",
            "sourceDescription": row["C"], "sourceMethod": row["D"], "sourceYear": int(row["L"]),
            "foodAliases": aliases, "methodAliases": method_aliases, "foodCodes": codes,
            "exactFoodAliases": [],
        })
    if mappings:
        raise ValueError(f"Missing mapped NDB entries: {sorted(mappings)}")
    return {
        "title": "USDA Table of Cooking Yields for Meat and Poultry",
        "version": "Release 2 (2014)", "sourceUrl": BASE + ".xlsx",
        "methodologyUrl": BASE + ".pdf", "sourceSha256": SHA256, "records": records,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", type=Path, default=WORKBOOK)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true", help="Compare to the packaged resource without writing it.")
    args = parser.parse_args()
    data = build_catalog(args.workbook)
    serialized = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if args.output.read_text(encoding="utf-8") != serialized:
            raise SystemExit("Packaged cooking-yields.json differs from the source workbook or mappings")
    else:
        args.output.write_text(serialized, encoding="utf-8", newline="\n")
    print(f"{len(data['records'])} measured USDA rows, source SHA256 {SHA256}")


if __name__ == "__main__":
    main()
