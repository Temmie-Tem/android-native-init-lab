import hashlib
import importlib.util
import io
import os
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/s22plus_boot_only_f1_transport.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("s22plus_boot_only_f1_transport", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def make_ap(path: Path, members=("boot.img.lz4",)) -> tuple[int, str]:
    with tarfile.open(path, "w") as archive:
        for name in members:
            payload = b"payload-" + name.encode("ascii")
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
    payload = path.read_bytes()
    return len(payload), hashlib.sha256(payload).hexdigest()


class S22PlusBootOnlyF1TransportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_boot_only_ap_requires_real_tar_md5_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "AP.tar.md5"
            size, digest = make_ap(path)
            with self.module.pin_boot_only_ap(
                path,
                label="candidate",
                expected_size=size,
                expected_sha256=digest,
            ) as pinned:
                self.assertEqual(pinned.path, path.absolute())
                self.assertFalse(str(pinned.path).startswith("/proc/"))

    def test_boot_only_ap_rejects_wrong_suffix_and_extra_member(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            wrong = root / "AP.bin"
            size, digest = make_ap(wrong)
            with self.assertRaises(self.module.F1TransportError):
                with self.module.pin_boot_only_ap(
                    wrong,
                    label="candidate",
                    expected_size=size,
                    expected_sha256=digest,
                ):
                    pass
            extra = root / "AP.tar.md5"
            size, digest = make_ap(extra, ("boot.img.lz4", "recovery.img.lz4"))
            with self.assertRaises(self.module.F1TransportError):
                with self.module.pin_boot_only_ap(
                    extra,
                    label="candidate",
                    expected_size=size,
                    expected_sha256=digest,
                ):
                    pass

    def test_pin_rejects_symlink_and_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "odin4"
            target.write_bytes(b"odin")
            link = root / "link"
            link.symlink_to(target)
            digest = hashlib.sha256(b"odin").hexdigest()
            with self.assertRaises(self.module.F1TransportError):
                with self.module.pin_regular_file(
                    link,
                    label="Odin4",
                    expected_size=4,
                    expected_sha256=digest,
                ):
                    pass
            with self.assertRaises(self.module.F1TransportError):
                with self.module.pin_regular_file(
                    target,
                    label="Odin4",
                    expected_size=4,
                    expected_sha256="0" * 64,
                ):
                    pass

    def test_pin_detects_path_replacement(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "input"
            path.write_bytes(b"original")
            digest = hashlib.sha256(b"original").hexdigest()
            with self.assertRaises(self.module.F1TransportError):
                with self.module.pin_regular_file(
                    path,
                    label="input",
                    expected_size=8,
                    expected_sha256=digest,
                ):
                    replacement = root / "replacement"
                    replacement.write_bytes(b"replaced")
                    os.replace(replacement, path)

    def test_command_keeps_tar_md5_and_rejects_proc_fd(self):
        module = self.module
        command = module.build_odin_boot_only_command(
            Path("/usr/bin/odin4"),
            Path("/tmp/AP.tar.md5"),
            "/dev/bus/usb/001/002",
        )
        self.assertEqual(command[3], "/tmp/AP.tar.md5")
        with self.assertRaises(module.F1TransportError):
            module.build_odin_boot_only_command(
                Path("/proc/self/fd/5"),
                Path("/tmp/AP.tar.md5"),
                "/dev/bus/usb/001/002",
            )

    def test_execute_uses_regular_path_and_returns_bounded_receipt(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            odin = root / "odin4"
            odin.write_bytes(b"odin")
            odin.chmod(0o700)
            ap = root / "AP.tar.md5"
            ap_size, ap_digest = make_ap(ap)
            seen = {}

            def fake_run(command, **kwargs):
                seen["command"] = command
                self.assertNotIn("pass_fds", kwargs)
                return mock.Mock(returncode=0, stdout=b"ok", stderr=b"")

            with mock.patch.object(module.subprocess, "run", side_effect=fake_run):
                receipt, stdout, stderr = module.execute_odin_boot_only(
                    odin,
                    ap,
                    "/dev/bus/usb/001/002",
                    odin_size=4,
                    odin_sha256=hashlib.sha256(b"odin").hexdigest(),
                    ap_size=ap_size,
                    ap_sha256=ap_digest,
                    label="candidate",
                )
            self.assertEqual(seen["command"][0], str(odin.absolute()))
            self.assertEqual(seen["command"][3], str(ap.absolute()))
            self.assertNotIn("/proc/", " ".join(seen["command"]))
            self.assertTrue(receipt["regular_path_inputs"])
            self.assertEqual((stdout, stderr), (b"ok", b""))


if __name__ == "__main__":
    unittest.main()
