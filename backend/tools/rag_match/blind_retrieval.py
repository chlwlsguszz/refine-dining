"""BM25 over food names only. Positions in the returned scores follow the input order."""

from collections import Counter, defaultdict
import math
import re
import unicodedata


WORD = re.compile(r"[^\W_]+", re.UNICODE)
HANGUL_RUN = re.compile(r"[가-힣]{2,}")
K1 = 1.2
B = 0.75


def _terms(name):
    if not isinstance(name, str):
        raise TypeError("Name retrieval accepts text only.")
    for word in WORD.findall(unicodedata.normalize("NFKC", name).casefold()):
        yield word
        for run in HANGUL_RUN.findall(word):
            # Separate term namespace so a substring and an exact word stay distinguishable.
            for i in range(len(run) - 1):
                yield "#" + run[i:i + 2]


class NameSearch:
    """Index the full candidate list without identifiers, labels, or classification fields."""

    def __init__(self, names: list[str]):
        self.size = len(names)
        frequencies = [Counter(_terms(name)) for name in names]
        lengths = [sum(terms.values()) for terms in frequencies]
        average_length = sum(lengths) / self.size if self.size else 0
        document_frequency = Counter(term for terms in frequencies for term in terms)
        self.postings = defaultdict(list)
        for position, counts in enumerate(frequencies):
            if not counts:
                continue
            length_factor = K1 * (1 - B + B * lengths[position] / average_length)
            for term, count in counts.items():
                df = document_frequency[term]
                idf = math.log1p((self.size - df + 0.5) / (df + 0.5))
                weight = idf * count * (K1 + 1) / (count + length_factor)
                self.postings[term].append((position, weight))

    def scores(self, query_name: str) -> list[float]:
        """Score every candidate; no overlap yields zero and ties are not resolved."""
        scores = [0.0] * self.size
        for term in sorted(set(_terms(query_name))):
            for position, weight in self.postings.get(term, ()):
                scores[position] += weight
        return scores
