"""Exercise the real Spring HTTP service in an isolated, ephemeral H2 database."""

import argparse
from decimal import Decimal, ROUND_HALF_UP
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "datasets/week1/2026-11-10"
OAT = "R101-001010101-0000"
RED = "R120-021030002-0000"
FRESH = "R120-021020001-0000"
EXTRACT = "R120-021030024-0000"


def run_cases(base, key, catalog):
    opener = build_opener(ProxyHandler({}))
    def http(path, body=None, admin=False):
        headers = {"Content-Type": "application/json; charset=UTF-8"}
        if admin:
            headers["X-Admin-Key"] = key
        data = None if body is None else json.dumps(body, ensure_ascii=False).encode()
        with opener.open(Request(base + path, data, headers), timeout=25) as response:
            return json.load(response)

    codes = {r["original"]["food_cd"]: r for r in catalog["rows"]}
    def equal(actual, expected):
        if actual != expected:
            raise AssertionError(f"{actual!r} != {expected!r}")

    measurements = []
    def ask(question, expected, food_cd=None):
        start = time.perf_counter()
        answer = http("/api/nutrition/answers", {"question":question,"foodCd":food_cd})
        elapsed = round((time.perf_counter()-start)*1000,2)
        equal(answer["status"], expected)
        cited = []
        for food in answer["foods"]:
            doc = http(food["href"])
            equal(doc["foodCd"], food["foodCd"])
            equal(doc["version"], catalog["version"])
            equal(doc["original"], codes[food["foodCd"]]["original"])
            equal(food["basis"], doc["original"]["nut_con_srtr_qua"])
            cited.append(doc["foodCd"])
        for line in answer["rows"]:
            scaled = []
            for i, field in enumerate(("target","candidate")):
                value = None
                if i < len(cited):
                    row = codes[cited[i]]
                    cell = row["cells"][line["key"]]
                    if cell["status"] == "observed":
                        basis = Decimal(row["original"]["nut_con_srtr_qua"].lower().removesuffix("ml").removesuffix("g"))
                        value = Decimal(cell["sourceText"]) * Decimal(str(answer["amount"])) / basis
                actual = line[field]
                expected_value = None if value is None else value.quantize(Decimal(".001"),rounding=ROUND_HALF_UP)
                equal(Decimal(str(actual)) if actual is not None else None, expected_value)
                scaled.append(value)
            diff = None if None in scaled else (scaled[0]-scaled[1]).quantize(Decimal(".001"),rounding=ROUND_HALF_UP)
            equal(None if line["delta"] is None else Decimal(str(line["delta"])), diff)
        measurements.append({"question":question,"status":expected,"sourceCodes":cited,"answerMs":elapsed,
                             "checkedCells":len(answer["rows"]),"values":answer["rows"],
                             "explanationSource":answer.get("explanationSource")})
        return answer

    offers = http("/api/admin/nutrition/proposals",admin=True)
    equal(len(offers),77)
    proposal = next(p for p in offers if p["targetCd"] == RED)
    equal(proposal["selectedCd"], FRESH)
    ask("귀리_겉귀리_도정_생것 150g 단백질","ANSWER")
    ask("인삼_홍삼_말린것 150g 단백질 비교","HELD")
    admin_note = {"decision":"APPROVED","reviewer":"격리 통합 테스트","note":"시연용 원료 정의와 양쪽 100g 기준 확인. 동일 시료 여부는 미확인."}
    http("/api/admin/nutrition/proposals/"+proposal["reviewId"],admin_note,True)
    compared = ask("인삼_홍삼_말린것 150g 단백질 비교","ANSWER")
    equal(compared["relation"]["evidenceSource"]["id"],"ginseng-red-art2-3")
    equal(compared["rows"][0]["delta"],13.35)
    ask("인삼_홍삼_말린것 150g 단백질 비교 이유","ANSWER")
    ask("인삼_홍삼_추출 100mL 단백질 비교","HELD")
    ask("인삼_홍삼_추출 100g 단백질","NEED_UNIT")
    ask("홍삼 100g 단백질","CHOOSE_FOOD")
    ask("홍삼 100g 단백질","ANSWER",RED)
    ask("수삼 150g을 조리한 뒤 총량","NEED_YIELD")
    ask("귀리 2컵 영양","NEED_UNIT")
    ask("존재하지않는식품xyz 100g 단백질","NO_MATCH")
    for state in ("missing","observed"):
        row = next(r for r in codes.values() if r["cells"]["sugar"]["status"]==state and r["original"]["sugar"]==0)
        single = ask("당류","ANSWER",row["original"]["food_cd"])
        equal(single["rows"][0]["target"],0 if state=="observed" else None)
    return {"snapshotId":catalog["snapshotId"],"catalogVersion":catalog["version"],"tests":measurements,
            "approvedOnlyInIsolatedTestDb":True,"cases":len(measurements),
            "checkedNutrientRows":sum(m["checkedCells"] for m in measurements)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--jar",type=Path,default=ROOT/"backend/build/libs/backend-0.0.1-SNAPSHOT.jar")
    p.add_argument("--catalog",type=Path,default=ROOT/"backend/build/rag/catalog.json")
    p.add_argument("--proposals",type=Path,default=DATA/"local-rag/development.json")
    p.add_argument("--output",type=Path)
    p.add_argument("--local-explainer",action="store_true",help="Also verify explanation routing to local Qwen on port 18081")
    a = p.parse_args()
    with socket.socket() as s:
        s.bind(("127.0.0.1",0))
        port = s.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    key = secrets.token_urlsafe(24)
    env = {**os.environ,"ADMIN_API_KEY":key,"RAG_CATALOG":str(a.catalog.resolve()),"RAG_PROPOSALS":str(a.proposals.resolve()),
           "RAG_PORT":str(port),"RAG_JDBC_URL":"jdbc:h2:mem:verify;MODE=MySQL;DATABASE_TO_LOWER=TRUE",
           "RAG_EXPLAINER":"http://127.0.0.1:18081" if a.local_explainer else ""}
    java = "java"
    if env.get("JAVA_HOME"):
        java = str(Path(env["JAVA_HOME"]) / "bin" / ("java.exe" if os.name == "nt" else "java"))
    with tempfile.TemporaryDirectory() as tmp, open(Path(tmp)/"app.log","wb+") as log:
        process = subprocess.Popen([java,"-jar",str(a.jar.resolve()),"--spring.profiles.active=rag-demo"],
                                   cwd=tmp,env=env,stdout=log,stderr=subprocess.STDOUT)
        try:
            for _ in range(100):
                if process.poll() is not None:
                    log.seek(0)
                    raise RuntimeError(log.read().decode(errors="replace")[-1800:])
                try:
                    with socket.create_connection(("127.0.0.1",port),timeout=1):
                        pass
                    request = Request(base + "/api/nutrition/foods/" + OAT)
                    with build_opener(ProxyHandler({})).open(request,timeout=2):
                        break
                except (OSError,HTTPError,URLError):
                    time.sleep(.5)
            else:
                raise RuntimeError("Spring demo did not become ready.")
            report = run_cases(base,key,json.loads(a.catalog.read_bytes()))
            route = next(t for t in report["tests"] if t["question"].endswith("이유"))["explanationSource"]
            if a.local_explainer and not str(route).startswith("local-model:"):
                raise RuntimeError("Local explanation did not return an authorized citation ID.")
            if a.output:
                a.output.parent.mkdir(parents=True,exist_ok=True)
                a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            print(f"{report['cases']} HTTP scenarios passed, {report['checkedNutrientRows']} nutrient rows checked; {route}")
        finally:
            process.terminate()
            try: process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

if __name__ == "__main__":
    main()
