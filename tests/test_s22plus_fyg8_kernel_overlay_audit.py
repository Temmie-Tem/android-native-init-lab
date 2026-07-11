import importlib.util
import io
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/revalidation/s22plus_fyg8_kernel_overlay_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("s22plus_fyg8_kernel_overlay_audit_tested", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def make_tar(path: Path, members: list[tuple[str, bytes | None, int]]) -> None:
    with tarfile.open(path, "w:gz") as archive:
        for name, data, mode in members:
            info = tarfile.TarInfo(name)
            info.mode = mode
            if data is None:
                info.type = tarfile.DIRTYPE
                info.size = 0
                archive.addfile(info)
            else:
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))


class S22PlusFyg8KernelOverlayAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_overlay_classifies_added_identical_and_changed(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base = tmp_path / "base.tar.gz"
            delta = tmp_path / "delta.tar.gz"
            make_tar(base, [("same", b"a", 0o644), ("changed", b"old", 0o644)])
            make_tar(
                delta,
                [
                    ("Kernel/", None, 0o755),
                    ("Kernel/same", b"a", 0o644),
                    ("Kernel/changed", b"new", 0o644),
                    ("Kernel/added", b"x", 0o755),
                ],
            )
            base_members = self.module.inspect_archive(base, delta=False)
            delta_members = self.module.inspect_archive(delta, delta=True)
            classes = {}
            for name, item in delta_members.items():
                previous = base_members.get(name)
                if previous is None:
                    classes[name] = "added"
                elif self.module.equivalent(previous, item):
                    classes[name] = "replaced_identical"
                else:
                    classes[name] = "replaced_changed"
            self.assertEqual(
                classes,
                {"same": "replaced_identical", "changed": "replaced_changed", "added": "added"},
            )

    def test_rejects_path_traversal_and_wrong_delta_prefix(self):
        with self.assertRaises(self.module.AuditError):
            self.module.safe_path("../escape", delta=False)
        with self.assertRaises(self.module.AuditError):
            self.module.safe_path("kernel_platform/file", delta=True)

    def test_absolute_symlink_is_recorded_but_absolute_hardlink_is_rejected(self):
        self.assertEqual(
            self.module.safe_link_target(
                "tool/lib.so", "/lib/lib.so.1", delta=False, kind="symlink"
            ),
            "/lib/lib.so.1",
        )
        with self.assertRaises(self.module.AuditError):
            self.module.safe_link_target(
                "tool/lib.so", "/tmp/file", delta=False, kind="hardlink"
            )

    def test_delta_symlink_target_is_not_rewritten(self):
        self.assertEqual(
            self.module.safe_link_target(
                "path/link", "Kernel/path/target", delta=True, kind="symlink"
            ),
            "Kernel/path/target",
        )

    def test_manifest_render_is_order_independent(self):
        rows = [{"path": "b", "size": 2}, {"path": "a", "size": 1}]
        first = self.module.render_jsonl(sorted(rows, key=lambda row: row["path"]))
        second = self.module.render_jsonl(sorted(reversed(rows), key=lambda row: row["path"]))
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
