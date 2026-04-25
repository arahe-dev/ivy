import pathlib
import unittest

from llama_moe_autotune.candidates import generate_candidates, build_candidate_command


class CandidateTests(unittest.TestCase):
    def test_survival_smoke_is_first(self):
        flags = {
            "supported": {
                "--mmap": True,
                "--cpu-moe": True,
                "-ctk": True,
                "-ctv": True,
                "-ub": True,
                "-ngl": True,
                "--reasoning-budget": True,
                "--single-turn": True,
                "--no-display-prompt": True,
            }
        }
        model_info = {"summary": {"block_count": 62}}

        candidates = generate_candidates(
            flags, model_info, max_candidates=5, disable_reasoning=False
        )

        self.assertEqual(candidates[0].name, "survival_smoke")
        self.assertEqual(candidates[0].context, 512)
        self.assertEqual(candidates[0].batch, 32)
        self.assertEqual(candidates[0].ubatch, 16)
        self.assertEqual(candidates[0].ngl, 0)
        self.assertEqual(candidates[0].kv, "q4_0")
        self.assertIs(candidates[0].cpu_moe, True)
        self.assertEqual(candidates[0].n_predict, 16)

    def test_candidate_count_is_bounded(self):
        flags = {"supported": {}}
        candidates = generate_candidates(
            flags, {"summary": {}}, max_candidates=3, disable_reasoning=False
        )

        self.assertEqual(len(candidates), 3)
        self.assertEqual([candidate.index for candidate in candidates], [0, 1, 2])

    def test_reasoning_budget_injected_when_disabled(self):
        flags = {
            "supported": {
                "--mmap": True,
                "--reasoning-budget": True,
                "--single-turn": True,
                "--no-display-prompt": True,
            }
        }
        model_info = {"summary": {}}
        candidates = generate_candidates(
            flags, model_info, max_candidates=1, disable_reasoning=True
        )

        cmd = build_candidate_command(
            candidates[0],
            pathlib.Path("/fake/llama-cli"),
            pathlib.Path("/fake/model.gguf"),
            "test",
            flags,
            disable_reasoning=True,
        )

        self.assertIn("--reasoning-budget", cmd)
        self.assertIn("0", cmd)
        self.assertIn("--single-turn", cmd)
        self.assertIn("--no-display-prompt", cmd)

    def test_reasoning_budget_not_injected_when_enabled(self):
        flags = {
            "supported": {
                "--mmap": True,
                "--reasoning-budget": True,
                "--single-turn": True,
                "--no-display-prompt": True,
            }
        }
        model_info = {"summary": {}}
        candidates = generate_candidates(
            flags, model_info, max_candidates=1, disable_reasoning=False
        )

        cmd = build_candidate_command(
            candidates[0],
            pathlib.Path("/fake/llama-cli"),
            pathlib.Path("/fake/model.gguf"),
            "test",
            flags,
            disable_reasoning=False,
        )

        self.assertNotIn("--reasoning-budget", cmd)

    def test_post_reasoning_tune_experiment(self):
        flags = {
            "supported": {
                "--mmap": True,
                "--cpu-moe": True,
                "-ctk": True,
                "-ctv": True,
                "-ngl": True,
                "--reasoning-budget": True,
                "--single-turn": True,
                "--no-display-prompt": True,
            },
            "n_gpu_layers_values": {"auto": True},
        }
        model_info = {"summary": {"block_count": 62}}
        candidates = generate_candidates(
            flags,
            model_info,
            max_candidates=24,
            disable_reasoning=True,
            experiment="post_reasoning_tune",
        )

        self.assertTrue(len(candidates) > 0)
        self.assertTrue(len(candidates) <= 24)


if __name__ == "__main__":
    unittest.main()
