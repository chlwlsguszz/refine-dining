from pathlib import Path
import tempfile
import unittest

try:
    import numpy as np
except ImportError:
    np = None

if np is not None:
    from embed_food_names import mean_pool, prefixed_name, valid_cache, write_vectors


@unittest.skipIf(np is None, "NumPy is required for the local embedding benchmark.")
class EmbeddingTests(unittest.TestCase):
    def test_food_names_only_with_distinct_e5_roles(self):
        self.assertEqual(prefixed_name("오미자_말린것", "query"), "query: 오미자 말린것")
        self.assertEqual(prefixed_name("오미자_생것", "passage"), "passage: 오미자 생것")
        with self.assertRaises(ValueError):
            prefixed_name({"foodCd": "classification"}, "query")

    def test_pooling_excludes_padding_then_normalizes(self):
        states = np.zeros((1, 3, 384), dtype=np.float32)
        states[0, 0, 0], states[0, 1, 1], states[0, 2, 2] = 3, 4, 1234
        vector = mean_pool(states, np.asarray([[1, 1, 0]]))
        np.testing.assert_allclose(vector[0, :3], [0.6, 0.8, 0], atol=1e-6)
        with self.assertRaises(ValueError):
            mean_pool(states, np.asarray([[0, 0, 0]]))

    def test_cache_rejects_stale_revision_wrong_order_and_bad_vectors(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "vectors.npz"
            cache.write_bytes(b"interrupted archive")
            self.assertFalse(valid_cache(cache, "v1", [], []))
            raw = np.asarray(["R1", "R2"])
            queries = np.asarray(["T1"])
            matrix = np.zeros((2, 384), dtype=np.float32)
            matrix[:, 0] = 1
            fields = dict(fingerprint="v1", raw_codes=raw, raw_vectors=matrix,
                          query_codes=queries, query_vectors=matrix[:1])
            write_vectors(cache, **fields)
            self.assertTrue(valid_cache(cache, "v1", raw, queries))
            self.assertFalse(valid_cache(cache, "v2", raw, queries))
            self.assertFalse(valid_cache(cache, "v1", raw[::-1], queries))
            matrix[0, 0] = np.nan
            write_vectors(cache, **fields)
            self.assertFalse(valid_cache(cache, "v1", raw, queries))


if __name__ == "__main__":
    unittest.main()
