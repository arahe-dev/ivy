import unittest

from llama_moe_autotune.ranking import best_result, safest_result


class RankingTests(unittest.TestCase):
    def test_best_result_prefers_success_speed(self):
        results = [
            {"outcome": "timeout", "decode_tps": 100, "candidate": {"context": 512, "ngl": 0, "batch": 32}},
            {"outcome": "success", "decode_tps": 5, "wall_seconds": 30, "metrics": {}, "candidate": {"context": 512, "ngl": 0, "batch": 32}},
            {"outcome": "success", "decode_tps": 10, "wall_seconds": 20, "metrics": {}, "candidate": {"context": 2048, "ngl": 16, "batch": 128}},
        ]

        self.assertEqual(best_result(results)["decode_tps"], 10)

    def test_safest_result_uses_successes_only(self):
        results = [
            {"outcome": "crash", "decode_tps": 100, "candidate": {"context": 512, "ngl": 0, "batch": 32}},
            {"outcome": "success", "decode_tps": 2, "candidate": {"context": 512, "ngl": 0, "batch": 32}},
        ]

        self.assertEqual(safest_result(results)["outcome"], "success")


if __name__ == "__main__":
    unittest.main()
