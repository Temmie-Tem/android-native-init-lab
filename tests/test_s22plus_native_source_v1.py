"""Direct source equivalence and real production C/consumer joins.

Historical generators are test oracles only. Hardware, USB and DRM operations
use the existing explicit host fixtures; these are not target boot proofs.
"""
from contextlib import contextmanager
import importlib
from pathlib import Path
import subprocess
import sys
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tests"),
               str(ROOT / "workspace/public/src/scripts/revalidation"),
               str(ROOT / "workspace/public/src/scripts/analysis")]

import s22plus_native_source_v1 as direct
import s22plus_native_refactor_h0_v1 as comparison
import s22plus_memory_manifest_v1 as memory
import test_s22plus_fyg8_p345_c_host_join as join
import test_s22plus_fyg8_p383_native_health_integration as health
import test_s22plus_fyg8_p381_hud_integration as hud


VERSIONS = {"p381": "v0.1.2-rc.4", "p382": "v0.1.2-rc.5", "p383": "v0.2.0-rc.1"}


def runtime_identity(runtime):
    namespace = Path(runtime.__file__).name.split("_")[2]
    return direct.Identity(namespace, runtime.P345_RUN_ID_HEX, VERSIONS[namespace])


@contextmanager
def production_join(*, profile=direct.CONSOLE_PROFILE):
    original = join.source

    def source(runtime=join.runtime):
        selected = runtime_identity(runtime)
        facade = types.SimpleNamespace(**vars(runtime))
        # The legacy fixture asks for a test-only readonly child. This adapter
        # deliberately emits the production helper, which has no such child.
        facade.build_helper = lambda _child=None: direct.helper_template(selected, profile=profile)
        text = original(facade)
        # The old test witness calls an otherwise retired native_exec helper.
        # Remove only that unused fixture function, never production C logic.
        return runtime._replace_function(text.encode(), b"static long p345_exec_command(", b"").decode()

    with mock.patch.object(join, "source", side_effect=source):
        yield


class SourceEquivalence(unittest.TestCase):
    def test_production_templates_and_materialized_keys_match_three_references(self):
        for namespace in VERSIONS:
            runtime = importlib.import_module(f"s22plus_fyg8_{namespace}_research_shell_runtime")
            selected = runtime_identity(runtime)
            self.assertEqual(direct.helper_template(selected), runtime.build_helper())
            self.assertNotEqual(direct.helper_template(selected),
                                runtime.build_helper(runtime.fixture_child_source()))
            for key in (bytes(range(32)), b"\xff" * 32):
                with self.subTest(namespace=namespace, key_shape=key[0]):
                    self.assertEqual(direct.materialize_helper(selected, key),
                                     runtime.materialize_helper(key))

    def test_renderer_census_and_actual_module_plan_match_reference(self):
        census = tuple(direct.MemoryModule(*row) for row in memory.manifest())
        self.assertEqual(direct.memory_census(census), memory.render())
        for namespace in VERSIONS:
            runtime = importlib.import_module(f"s22plus_fyg8_{namespace}_research_shell_runtime")
            renderer = importlib.import_module(f"s22plus_fyg8_{namespace}_display_renderer")
            self.assertEqual(direct.render_display(runtime_identity(runtime), census), renderer.render())
        plan = (comparison.REFERENCE / "inputs/s22plus_native_display_plan.h").read_bytes()
        self.assertEqual(direct.display_plan(comparison.display_rows(plan)), plan)

    def test_identity_injection_rejects_code_and_key_shape(self):
        for values in (("p383\n", "a" * 32, "v1.0.0"),
                       ("p383", "A" * 32, "v1.0.0"),
                       ("p383", "a" * 32, 'v1.0.0";')):
            with self.assertRaises(direct.SourceError):
                direct.Identity(*values)
        for key in (None, "k" * 32, b"k" * 31, b"k" * 33):
            with self.assertRaises(direct.SourceError):
                direct.materialize_helper(comparison.IDENTITY, key)

    def test_metadata_cannot_inject_source_or_silently_reorder_modules(self):
        bad = (
            [direct.MemoryModule('../bad.ko', 1, 0o400)],
            [direct.MemoryModule('bad.ko', True, 0o400)],
            [direct.MemoryModule('b.ko', 1, 0o400), direct.MemoryModule('a.ko', 1, 0o400)],
            [direct.MemoryModule('a.ko', 1, 0o400)] * 2,
        )
        for rows in bad:
            with self.assertRaises(direct.SourceError):
                direct.memory_census(rows)
        for rows in ([direct.DisplayModule('a.ko', 1, False)],
                     [direct.DisplayModule('a.ko', 1, True)] * 2):
            with self.assertRaises(direct.SourceError):
                direct.display_plan(rows)

    def test_direct_generator_has_no_candidate_import_dependency(self):
        script = """
import sys
sys.path.insert(0, 'workspace/public/src/scripts/revalidation')
import s22plus_native_source_v1 as source
source.helper_template(source.Identity('p383', 'c383f1e0a90b5e6d7c8a9b0c0d2e3f0b', 'v0.2.0-rc.1'))
assert not any(name.startswith('s22plus_fyg8_p') for name in sys.modules)
assert not any('namespace' in path.name for path in source.source_files())
"""
        result = subprocess.run([sys.executable, "-c", script], cwd=direct.ROOT,
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)


class ProductionNativeHealth(health.IntegrationTests):
    @classmethod
    def setUpClass(cls):
        with production_join():
            super().setUpClass()


class ProductionHud(hud.StatusIntegration):
    @classmethod
    def setUpClass(cls):
        census = tuple(direct.MemoryModule(*row) for row in memory.manifest())
        selected = runtime_identity(hud.runtime)
        with production_join(), mock.patch.object(
            hud.renderer_test.renderer, "render",
            side_effect=lambda: direct.render_display(selected, census),
        ):
            super().setUpClass()


if __name__ == "__main__":
    unittest.main()
