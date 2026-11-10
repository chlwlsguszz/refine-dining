"""Optional loopback E5 lookup of cut names. No yields are returned by this service."""

import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
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


def handler(index):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path != "/suggest":
                self.send_error(404)
                return
            try:
                size = int(self.headers.get("Content-Length", 0))
                if not 1 <= size <= 16384:
                    raise ValueError
                body = json.loads(self.rfile.read(size))
                name, labels = body["name"], body["labels"]
                if not isinstance(name, str) or not 1 <= len(name) <= 250 or not isinstance(labels, list):
                    raise ValueError
                if not all(isinstance(label, str) for label in labels):
                    raise ValueError
                encoded = json.dumps(index.suggest(name, set(labels)), ensure_ascii=False).encode()
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
    index = CutNames(json.loads(args.table.read_bytes()), Encoder(graph, tokenizer, 4))
    with HTTPServer(("127.0.0.1", args.port), handler(index)) as server:
        print(f"Local E5 cut-name suggestions ready on 127.0.0.1:{args.port}", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
