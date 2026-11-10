"""Opt-in Spring HTTP + real MySQL integration test on a fresh disposable database.

Set RUN_NUTRITION_HTTP_IT=1 after building the Spring bootJar. Requires Java 17,
Docker and the mysql:8.0 image. RAG_IT_PORT defaults to 18084, JAR path may be
overridden with RAG_IT_JAR. No user database or real food approvals are accessed.
"""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import tempfile
import time
import unittest
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

from week1_snapshot import canonical


ROOT = Path(__file__).resolve().parents[3]
BUILD = ROOT / "backend/build"
PORT = int(os.environ.get("RAG_IT_PORT", "18084"))
JAVA = Path(os.environ["JAVA_HOME"]) / "bin/java" if os.environ.get("JAVA_HOME") else "java"
JAR = Path(os.environ.get("RAG_IT_JAR", BUILD / "libs/backend-0.0.1-SNAPSHOT.jar")).resolve()
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def docker(*args):
    result = subprocess.run(["docker", *args], capture_output=True, text=True, check=True,
                            creationflags=NO_WINDOW, timeout=90)
    return result.stdout.strip()


@contextmanager
def database():
    name = "refine-nutrition-it-" + secrets.token_hex(6)
    password = secrets.token_urlsafe(24)
    docker("run", "--detach", "--rm", "--name", name, "-p", "127.0.0.1::3306",
           "-e", "MYSQL_ROOT_PASSWORD=" + password, "-e", "MYSQL_DATABASE=rag_it", "mysql:8.0",
           "--character-set-server=utf8mb4", "--collation-server=utf8mb4_unicode_ci")
    try:
        port = docker("port", name, "3306/tcp").split(":")[-1]
        for _ in range(90):
            try:
                # TCP readiness excludes the socket-only bootstrap daemon.
                docker("exec", "-e", "MYSQL_PWD=" + password, name, "mysql", "--protocol=tcp", "-h127.0.0.1",
                       "-uroot", "rag_it", "-e", "select 1")
                break
            except subprocess.CalledProcessError:
                time.sleep(1)
        else:
            raise TimeoutError("Disposable MySQL did not become ready.")
        yield name, port, password
    finally:
        docker("stop", name)


def write_fixture(directory, revision, duplicate=False):
    rows = []
    for code, name, raw in (("T", "시험콩_찐것", False), ("R", "시험콩_생것", True),
                            ("H", "시험콩_추출액", False)):
        rows.append({"original": {"food_cd": code, "food_nm": name, "food_lv7cd": "01" if raw else "03",
                                  "enerc": revision, "water": 0, "ca": 0, "fibtg": 0},
                     "cells": {"water": {"status": "observed", "sourceText": "0"},
                               "ca": {"status": "missing", "sourceText": None},
                               "fibtg": {"status": "unverified", "sourceText": None},
                               "enerc": {"status": "observed", "sourceText": str(revision)}}})
    snapshot = "sha256:" + hashlib.sha256(canonical([revision, "fixture"])).hexdigest()
    if duplicate:
        rows.append(rows[-1])
    upstream = hashlib.sha256(canonical(rows)).hexdigest()
    version = "sha256:" + hashlib.sha256(canonical([snapshot, upstream, rows])).hexdigest()
    catalog = {"version": version, "snapshotId": snapshot, "upstreamSha256": upstream, "rowCount": len(rows),
               "sourceUrl": "https://example.org/fixture", "rows": rows}
    proposals = {"snapshotId": snapshot, "policyVersion": "fixture-v1", "results": []}
    for row in (rows[0], rows[2]):
        code = row["original"]["food_cd"]
        proposals["results"].append({"targetCd": code, "targetQuote": row["original"]["food_nm"],
                                     "selectedCd": "R" if code == "T" else None,
                                     "verdict": "참고 비교" if code == "T" else "보류", "reason": "합성 검수 표본",
                                     "candidates": [{"record": {"foodCd": "R", "foodNm": rows[1]["original"]["food_nm"]}}],
                                     "evidenceSource": None})
    for name, payload in (("catalog", catalog), ("proposals", proposals)):
        (directory / (name + ".json")).write_bytes(canonical(payload))
    return version


def http(path, key=None, body=None):
    headers = {"Content-Type": "application/json"}
    if key:
        headers["X-Admin-Key"] = key
    req = Request(f"http://127.0.0.1:{PORT}{path}", headers=headers, data=canonical(body) if body else None)
    client = build_opener(ProxyHandler({}))
    try:
        with client.open(req, timeout=4) as response:
            return response.status, json.load(response)
    except HTTPError as exc:
        return exc.code, json.load(exc)


@contextmanager
def spring(directory, db_port, password, key):
    env = {**os.environ, "DB_HOST": "127.0.0.1", "DB_PORT": db_port, "DB_NAME": "rag_it",
           "DB_USERNAME": "root", "DB_PASSWORD": password, "ADMIN_API_KEY": key,
           "PUBLIC_DATA_API_KEY": "", "GEMINI_API_KEY": "", "SERVER_PORT": str(PORT), "SERVER_ADDRESS": "127.0.0.1",
           "RAG_CATALOG": str(directory / "catalog.json"), "RAG_PROPOSALS": str(directory / "proposals.json")}
    log = directory / "spring.log"
    with log.open("wb") as output:
        proc = subprocess.Popen([str(JAVA), "-jar", str(directory / "application.jar")], cwd=directory, env=env, stdout=output,
                                stderr=subprocess.STDOUT, creationflags=NO_WINDOW)
        try:
            for _ in range(100):
                if proc.poll() is not None:
                    tail = log.read_text(encoding="utf-8", errors="replace")[-3500:]
                    raise RuntimeError("Spring fixture startup failed: " + tail)
                try:
                    if http("/api/nutrition/foods/T")[0] == 200:
                        break
                except (URLError, TimeoutError, ConnectionError):
                    pass
                time.sleep(0.4)
            else:
                raise TimeoutError("Spring fixture did not become ready.")
            yield
        finally:
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=20)


@unittest.skipUnless(os.environ.get("RUN_NUTRITION_HTTP_IT") == "1", "Opt in to start disposable MySQL and Spring")
class NutritionHttpIT(unittest.TestCase):
    def test_review_lifecycle_with_release_changes(self):
        self.assertTrue(JAR.is_file(), "Build the Spring bootJar first.")
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", PORT))
        key = secrets.token_urlsafe(20)
        admin = "/api/admin/nutrition/proposals"
        approve = {"decision": "APPROVED", "reviewer": "fixture", "note": "fixture source inspected"}
        hold = {"decision": "HELD", "reviewer": "fixture", "note": "fixture evidence insufficient"}
        BUILD.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=BUILD) as tmp, database() as (container, port, password):
            directory = Path(tmp)
            # Preserve this test run's binary even if a concurrent workspace build replaces bootJar.
            shutil.copyfile(JAR, directory / "application.jar")
            a = write_fixture(directory, 101)
            with spring(directory, port, password, key):
                self.assertEqual(403, http(admin)[0])
                self.assertEqual(403, http(admin, "incorrect")[0])
                proposals = {p["targetCd"]: p for p in http(admin, key)[1]}
                self.assertEqual({"PENDING"}, {p["reviewStatus"] for p in proposals.values()})
                t = admin + "/" + proposals["T"]["reviewId"]
                h = admin + "/" + proposals["H"]["reviewId"]
                self.assertEqual(403, http(t, body=approve)[0])
                cells = http("/api/nutrition/foods/T?version=" + a)[1]["cells"]
                self.assertEqual((0, "observed"), (cells["water"]["value"], cells["water"]["status"]))
                self.assertEqual((None, "missing"), (cells["ca"]["value"], cells["ca"]["status"]))
                self.assertEqual((None, "unverified"), (cells["fibtg"]["value"], cells["fibtg"]["status"]))
                self.assertEqual(400, http(h, key, approve)[0])
                self.assertEqual(400, http(t, key, dict(approve, note=" "))[0])
                with ThreadPoolExecutor(2) as pool:
                    replies = list(pool.map(lambda _: http(t, key, approve), range(2)))
                self.assertEqual([200, 200], [s for s, _ in replies])
                self.assertEqual(replies[0][1]["decidedAt"], replies[1][1]["decidedAt"])
                self.assertEqual(400, http(t, key, hold)[0])
                self.assertEqual("HELD", http(h, key, hold)[1]["reviewStatus"])
            b = write_fixture(directory, 102)
            with spring(directory, port, password, key):
                self.assertNotEqual(a, b)
                self.assertEqual(404, http("/api/nutrition/foods/T?version=" + a)[0])
                self.assertEqual(404, http(t, key, approve)[0])
                self.assertTrue(all(p["reviewStatus"] == "PENDING" for p in http(admin, key)[1]))
            # Inject a duplicate-row failure after the batch has begun. Inspect real transaction rollback.
            broken = write_fixture(directory, 103, duplicate=True)
            with self.assertRaisesRegex(RuntimeError, "Spring fixture startup failed"), spring(directory, port, password, key):
                self.fail("An invalid catalog was accepted.")
            count = docker("exec", "-e", "MYSQL_PWD=" + password, container, "mysql", "-N", "-uroot", "rag_it",
                           "-e", "select count(*) from rag_food where catalog_id='" + broken + "'")
            self.assertEqual("0", count)
            self.assertEqual(a, write_fixture(directory, 101))
            with spring(directory, port, password, ""):
                self.assertEqual(403, http(admin, key)[0])
                self.assertEqual(200, http("/api/nutrition/foods/T?version=" + a)[0])
            with spring(directory, port, password, key):
                restored = {p["targetCd"]: p["reviewStatus"] for p in http(admin, key)[1]}
                self.assertEqual({"T": "APPROVED", "H": "HELD"}, restored)


if __name__ == "__main__":
    unittest.main()
