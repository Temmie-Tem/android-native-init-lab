from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p322_runtime_repair.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "s22plus_fyg8_p322_runtime_repair", SCRIPT
    )
    if spec is None or spec.loader is None:
        raise AssertionError("unable to load P322 runtime repair")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fixture(module) -> bytes:
    """A compact generated-P319-shaped source fixture with a fenced tail."""
    return b"".join(
        (
            module.P319_STOCK_RUNTIME_MARKER,
            b"\n/* preserved diagnostic/provider closure: "
            b"p316_ p317_ P316_ P317_ diagnostic DIAG provider PROVIDER */\n",
            b"static int s22plus_max77705_p319_stock_encode(\n"
            b"    const void *witness) { return witness != 0; }\n\n",
            module.P319_BYPASS_PREIMAGE,
            module.P319_STOCK_PUBLISHER_DEFINITION,
            b"    p319_stock_bypass_to_pair();\n"
            b"}\n",
        )
    )


def _helper_source(module, runtime: bytes) -> bytes:
    """Extract the transformed helper with a small brace-balanced scan."""
    marker = b"static void p319_stock_bypass_to_pair(void)"
    start = runtime.index(marker)
    brace = runtime.index(b"{", start)
    depth = 0
    for index in range(brace, len(runtime)):
        token = runtime[index : index + 1]
        if token == b"{":
            depth += 1
        elif token == b"}":
            depth -= 1
            if depth == 0:
                return runtime[start : index + 1]
    raise AssertionError("unterminated P322 helper")


def _compile_checkpoint_harness(module, helper: bytes) -> Path:
    source = br"""
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>

#define P313_DETAIL_CHECKPOINT_POSITION_CONTRADICTION 0x6720L

struct checkpoint_state {
    uint8_t terminal;
    uint8_t generation;
};

static struct checkpoint_state g_checkpoint;
static unsigned int progress_count;
static uint8_t progress_generation[32];

static __attribute__((noreturn)) void p290_fail_next(long detail) {
    if (detail != P313_DETAIL_CHECKPOINT_POSITION_CONTRADICTION)
        exit(76);
    exit(77);
}

static void p290_progress_position(uint8_t generation, unsigned int detail) {
    if (detail != 0U || generation != g_checkpoint.generation
        || progress_count >= 32U)
        exit(78);
    progress_generation[progress_count++] = generation;
    ++g_checkpoint.generation;
}
""" + helper + br"""

int main(int argc, char **argv) {
    if (argc != 2) return 10;
    int mode = atoi(argv[1]);
    g_checkpoint.terminal = 0U;
    g_checkpoint.generation = 92U;
    progress_count = 0U;
    if (mode == 0) {
        p319_stock_bypass_to_pair();
        if (g_checkpoint.generation != 105U || progress_count != 13U)
            return 11;
        for (unsigned int i = 0U; i < 13U; ++i)
            if (progress_generation[i] != (uint8_t)(92U + i)) return 12;
        return 0;
    }
    if (mode == 1) g_checkpoint.generation = 106U;
    else if (mode == 2) g_checkpoint.terminal = 1U;
    else return 13;
    p319_stock_bypass_to_pair();
    return 14;
}
"""
    directory = Path(tempfile.mkdtemp(prefix="p322-runtime-repair-c-"))
    source_path = directory / "fixture.c"
    binary_path = directory / "fixture"
    source_path.write_bytes(source)
    result = subprocess.run(
        ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", source_path,
         "-o", binary_path],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    return binary_path


class P322RuntimeRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()
        cls.before = _fixture(cls.module)
        cls.after = cls.module.transform_runtime_include(cls.before)

    def test_exact_one_anchor_transform(self) -> None:
        module = self.module
        self.assertEqual(self.before.count(module.P319_BYPASS_PREIMAGE), 1)
        self.assertEqual(self.after.count(module.P322_BYPASS_POSTIMAGE), 1)
        self.assertEqual(self.after.count(module.P319_BYPASS_PREIMAGE), 0)
        self.assertEqual(
            self.after,
            self.before.replace(
                module.P319_BYPASS_PREIMAGE, module.P322_BYPASS_POSTIMAGE, 1
            ),
        )
        receipt = module.validate_repair(self.before, self.after)
        self.assertTrue(receipt["changed_only_in_anchor"])
        self.assertEqual(receipt["changed_anchor"], "p319_stock_bypass_to_pair")

    def test_second_anchor_and_already_repaired_inputs_are_rejected(self) -> None:
        module = self.module
        with self.assertRaises(module.RuntimeRepairError):
            module.transform_runtime_include(
                self.before + module.P319_BYPASS_PREIMAGE
            )
        with self.assertRaises(module.RuntimeRepairError):
            module.validate_p319_preimage(self.after)

    def test_old_bug_is_rejected_after_transform(self) -> None:
        module = self.module
        with self.assertRaises(module.RuntimeRepairError):
            module.validate_transformed_runtime(self.before)
        helper = _helper_source(module, self.after)
        self.assertNotIn(b"g_checkpoint.generation != 105U", helper)
        self.assertIn(b"g_checkpoint.generation > 105U", helper)
        self.assertIn(
            b"p290_progress_position((uint8_t)g_checkpoint.generation, 0U);",
            helper,
        )

    def test_bounded_92_to_105_progression_semantics(self) -> None:
        binary = _compile_checkpoint_harness(
            self.module, _helper_source(self.module, self.after)
        )
        result = subprocess.run([binary, "0"], capture_output=True, check=False)
        self.assertEqual(result.returncode, 0)

    def test_generation_overrun_and_terminal_fail_closed(self) -> None:
        binary = _compile_checkpoint_harness(
            self.module, _helper_source(self.module, self.after)
        )
        for mode in ("1", "2"):
            with self.subTest(mode=mode):
                result = subprocess.run(
                    [binary, mode], capture_output=True, check=False
                )
                self.assertEqual(result.returncode, 77)

    def test_diagnostic_provider_closure_is_not_widened(self) -> None:
        module = self.module
        for marker in module.P322_DIAGNOSTIC_PROVIDER_MARKERS:
            with self.subTest(marker=marker):
                self.assertEqual(self.before.count(marker), self.after.count(marker))
        # The byte-level validator also rejects an otherwise postimage-shaped
        # source whose preserved diagnostic/provider tail was changed.
        mutated = self.after.replace(b"provider", b"providerX", 1)
        with self.assertRaises(module.RuntimeRepairError):
            module.validate_repair(self.before, mutated)

    def test_artifact_transform_changes_only_named_runtime_member(self) -> None:
        module = self.module
        source = {"unrelated": b"stable", module.P322_RUNTIME_KEY: self.before}
        result = module.transform_artifacts(source)
        self.assertEqual(result["unrelated"], source["unrelated"])
        self.assertEqual(result[module.P322_RUNTIME_KEY], self.after)


if __name__ == "__main__":
    unittest.main()
