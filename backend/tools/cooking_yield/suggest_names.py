"""Local E5 retrieval of measured yield records; numeric calculations remain in Java."""

import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
from collections import OrderedDict
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend/tools/rag_match"))
from embed_food_names import Encoder, MODEL_FILE, TOKENIZER_FILE, file_digest, prefixed_name
from dev_candidate_search import MODEL_SHA, TOKENIZER_SHA, REVISION

SPECIES = (
    re.compile(r"닭|치킨|chicken", re.I),
    re.compile(r"소고기|쇠고기|한우|비프|beef", re.I),
    re.compile(r"돼지|돈육|포크|pork", re.I),
)
PARTS = tuple(re.compile(words, re.I) for words in (
    r"넓적다리|넙적다리|허벅지|윗다리|thigh",
    r"아랫다리|북채|드럼스틱|drumstick",
    r"가슴|브레스트|breast",
    r"날개|윙|wing",
    r"패티|버거|patty|patties|burger",
    r"다짐육|분쇄육|다진|민스|mince|ground",
    r"등심|로인|loin",
))
# Exact table names may include these conditions, but an embedding must not infer them.
SPECIAL_PREP = re.compile(r"제거|없는|벗[긴겨기]|껍질|뼈|순살|닭다리살|정육|염지|양념|튀김|대체육|소시지|햄|%|skin|bone|ground replacement", re.I)

SEARCH_SPECIES = {
    "chicken": r"닭|치킨|chicken", "beef": r"소고기|쇠고기|한우|비프|티본|\bbeef\b|t-bone",
    "pork": r"돼지|돈육|포크|\bpork\b", "turkey": r"칠면조|터키|\bturkey\b",
    "veal": r"송아지|\bveal\b", "lamb": r"양고기|램|\blamb\b",
    "emu": r"에뮤|\bemu\b", "ostrich": r"타조|\bostrich\b", "bison": r"들소|바이슨|\bbison\b",
    "deer": r"사슴|\bdeer\b", "elk": r"엘크|\belk\b",
}
# The corpus contains only meat/poultry. Known out-of-corpus foods must not be
# turned into meat estimates merely because E5 assigns them a relative rank.
OUTSIDE_CORPUS = re.compile(
    r"감자|고구마|옥수수|두부|콩|쌀|밥|보리|밀가루|버섯|브로콜리|당근|양파|배추|상추|사과|바나나|김치|짜장면|"
    r"연어|고등어|참치|생선|새우|오징어|조개|전복|문어|계란|달걀|우유|치즈|두유|"
    r"\b(potato|corn|tofu|rice|bean|mushroom|broccoli|carrot|onion|apple|banana|salmon|fish|shrimp|squid|egg|milk|cheese)\b", re.I)

SEARCH_CUTS = {
    "thigh": r"넓적다리|넙적다리|허벅지|윗다리|\bthigh\b",
    "drumstick": r"아랫다리|북채|드럼스틱|\bdrumstick\b", "breast": r"가슴|브레스트|\bbreast\b",
    "wing": r"날개|\bwing\b", "tenderloin": r"안심|tenderloin", "loin": r"등심|\bloin\b",
    "ribeye": r"꽃등심|립아이|rib.?eye", "ribs": r"갈비|ribs", "brisket": r"양지|브리스킷|brisket",
    "shoulder": r"어깨|앞다리|shoulder|chuck", "round": r"우둔|홍두깨|뒷다리|\bround\b",
    "ground": r"다짐|다진|분쇄|패티|버거|ground|patty|burger|mince", "liver": r"간$|\bliver\b",
    "heart": r"심장|heart", "gizzard": r"모래주머니|근위|닭똥집|gizzard", "neck": r"목살|\bneck\b",
    "ham": r"햄|\bham\b", "bacon": r"베이컨|bacon", "sausage": r"소시지|소세지|sausage",
}


def query_cuts(name):
    cuts = {cut for cut, pattern in SEARCH_CUTS.items() if re.search(pattern, name, re.I)}
    if re.search(r"닭\s*다리|chicken\s+leg", name, re.I) and not cuts:
        cuts.update({"thigh", "drumstick"})
    return cuts


def query_methods(method):
    for pattern, methods in (
        (r"오븐|로스트|로스팅|roast|bake", {"roast"}),
        (r"그릴|직화|브로일|grill|broil", {"grill"}),
        (r"삶|데치|simmer|boil|poach|stew", {"simmer"}),
        (r"조림|조린|brais", {"braise"}),
        (r"볶|saute|stir", {"saute", "pan_fry"}),
        (r"팬|pan|griddle", {"dry_pan", "pan_fry"}),
        (r"튀|deep.?fr", {"deep_fry"}),
        (r"전자|microwave", {"microwave"}),
        (r"구이|구운", {"roast", "grill", "dry_pan", "pan_fry"}),
    ):
        if re.search(pattern, method, re.I):
            return methods
    return set()


class YieldSearch:
    """Rank every source row by its bilingual identity and cooking method."""
    def __init__(self, document, encoder):
        self.encoder = encoder
        self.records = document["records"]
        texts = []
        for row in self.records:
            words = [row["foodLabel"], row["sourceDescription"], row["methodLabel"], row["sourceMethod"],
                     *row.get("foodAliases", []), *row.get("searchAliases", [])]
            texts.append(prefixed_name(". ".join(dict.fromkeys(words)), "passage"))
        self.vectors = encoder.encode(texts, 16)
        self.cache = OrderedDict()

    def search(self, food_name, cooking_method=""):
        name = food_name.strip()
        cache_key = (name, cooking_method.strip())
        if cache_key in self.cache:
            self.cache.move_to_end(cache_key)
            return self.cache[cache_key]
        tags = [key for key, pattern in SEARCH_SPECIES.items() if re.search(pattern, name, re.I)]
        # A mixed-food query may mention meat as well as an unsupported ingredient.
        # Return no whole-dish yield because the table has no such measurement.
        if OUTSIDE_CORPUS.search(name):
            return []
        eligible = [i for i, row in enumerate(self.records) if not tags or row["species"] in tags]
        if not eligible:
            return []
        query = prefixed_name(" ".join(filter(None, [name, cooking_method.strip()])), "query")
        scores = self.vectors @ self.encoder.encode([query], 1)[0]
        cuts, methods = query_cuts(name), query_methods(cooking_method)
        chop = bool(re.search(r"찹|\bchops?\b", name, re.I))
        def rank_score(i):
            row = self.records[i]
            cut_bonus = .04 if (cuts and row["cut"] in cuts) or (chop and "chop" in row["sourceDescription"].lower()) else 0
            method_bonus = .02 if methods and row["methodKey"] in methods else 0
            processing_penalty = .015 if "enhanced" in row.get("preparationTags", []) and not re.search(r"염지|용액|enhanced", name, re.I) else 0
            return float(scores[i]) + cut_bonus + method_bonus - processing_penalty
        ranked = sorted(eligible, key=lambda i: (-rank_score(i), self.records[i]["id"]))
        # A high raw similarity is required when neither animal nor cut is named.
        # This still permits unregistered expressions; regex is not an allowlist.
        minimum = .78 if tags or cuts or chop else .86
        result = [{"id": self.records[i]["id"], "score": round(float(scores[i]), 6)}
                  for i in ranked if float(scores[i]) >= minimum][:12]
        self.cache[cache_key] = result
        if len(self.cache) > 128:
            self.cache.popitem(last=False)
        return result


def species(name):
    tags = [i for i, pattern in enumerate(SPECIES) if pattern.search(name)]
    return tags[0] if len(tags) == 1 else None


class CutNames:
    def __init__(self, document, encoder):
        self.encoder = encoder
        aliases = {}
        for row in document["records"]:
            label = row["foodLabel"]
            aliases.setdefault(label, set()).update([label, *row["foodAliases"]])
        self.labels = sorted(aliases)
        texts = [prefixed_name(" ".join(sorted(aliases[label])), "passage") for label in self.labels]
        self.vectors = encoder.encode(texts, 16)

    def suggest(self, name, allowed):
        tag = species(name)
        if tag is None or SPECIAL_PREP.search(name):
            return []
        parts = [pattern for pattern in PARTS if pattern.search(name)]
        if not parts:
            return []
        eligible = [i for i, label in enumerate(self.labels)
                    if label in allowed and species(label) == tag and all(pattern.search(label) for pattern in parts)]
        if not eligible:
            return []
        query = self.encoder.encode([prefixed_name(name, "query")], 1)[0]
        scores = self.vectors @ query
        ranked = sorted(eligible, key=lambda i: (-scores[i], self.labels[i]))
        return [self.labels[i] for i in ranked if scores[i] >= .80][:3]


def handler(index, search_index=None):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path not in {"/suggest", "/search"}:
                self.send_error(404)
                return
            try:
                size = int(self.headers.get("Content-Length", 0))
                if not 1 <= size <= 16384:
                    raise ValueError
                body = json.loads(self.rfile.read(size))
                if self.path == "/search":
                    name, method = body["foodName"], body.get("cookingMethod", "") or ""
                    if (not isinstance(name, str) or not 1 <= len(name.strip()) <= 250
                            or not isinstance(method, str) or len(method) > 100 or search_index is None):
                        raise ValueError
                    result = {"engine": "E5", "matches": search_index.search(name, method)}
                else:
                    name, labels = body["name"], body["labels"]
                    if not isinstance(name, str) or not 1 <= len(name) <= 250 or not isinstance(labels, list):
                        raise ValueError
                    if len(labels) > 200 or not all(isinstance(label, str) and len(label) <= 300 for label in labels):
                        raise ValueError
                    result = index.suggest(name, set(labels))
                encoded = json.dumps(result, ensure_ascii=False).encode()
            except (KeyError, TypeError, ValueError):
                self.send_error(400)
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=18086)
    parser.add_argument("--model-dir", type=Path, default=ROOT / "backend/build/models/multilingual-e5-small" / REVISION)
    parser.add_argument("--table", type=Path, default=ROOT / "backend/src/main/resources/cooking-yields.json")
    args = parser.parse_args()
    graph, tokenizer = args.model_dir / MODEL_FILE, args.model_dir / TOKENIZER_FILE
    if file_digest(graph) != MODEL_SHA or file_digest(tokenizer) != TOKENIZER_SHA:
        raise ValueError("Unexpected E5 weights/tokenizer.")
    document = json.loads(args.table.read_bytes())
    encoder = Encoder(graph, tokenizer, 4)
    index, search_index = CutNames(document, encoder), YieldSearch(document, encoder)
    with HTTPServer(("127.0.0.1", args.port), handler(index, search_index)) as server:
        print(f"Local E5 yield search ready with {len(document['records'])} rows on 127.0.0.1:{args.port}", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
