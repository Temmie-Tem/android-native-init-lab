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
SCRIPT_DIR = SCRIPT.parent.resolve()


def load_module():
    if str(SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPT_DIR))
    spec = importlib.util.spec_from_file_location("s22plus_boot_only_f1_transport", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def make_ap(path: Path, members=("boot.img.lz4",)) -> tuple[int, str]:
    stream = io.BytesIO()
    with tarfile.open(
        fileobj=stream, mode="w", format=tarfile.USTAR_FORMAT
    ) as archive:
        for name in members:
            payload = b"payload-" + name.encode("ascii")
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            info.mode = 0o644
            info.uid = info.gid = info.mtime = 0
            info.uname = info.gname = ""
            archive.addfile(info, io.BytesIO(payload))
    prefix = stream.getvalue()
    payload = prefix + f"{hashlib.md5(prefix).hexdigest()}  AP.tar\n".encode()
    path.write_bytes(payload)
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
                member = self.module.boot_only_member_receipt(
                    pinned, label="candidate"
                )
                payload = b"payload-boot.img.lz4"
                self.assertEqual(
                    member,
                    {
                        "name": "boot.img.lz4",
                        "size": len(payload),
                        "sha256": hashlib.sha256(payload).hexdigest(),
                    },
                )

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

    def test_boot_only_ap_rejects_plain_tar_bad_md5_and_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            valid = root / "valid.tar.md5"
            make_ap(valid)

            cases = {}
            cases["plain_tar"] = valid.read_bytes()[:-41]
            bad_md5 = bytearray(valid.read_bytes())
            bad_md5[-41] = ord("0") if bad_md5[-41] != ord("0") else ord("1")
            cases["bad_md5"] = bytes(bad_md5)

            stream = io.BytesIO()
            with tarfile.open(
                fileobj=stream, mode="w", format=tarfile.USTAR_FORMAT
            ) as archive:
                payload = b"payload-boot.img.lz4"
                info = tarfile.TarInfo("boot.img.lz4")
                info.size = len(payload)
                info.mode = 0o600
                info.uid = info.gid = info.mtime = 0
                info.uname = info.gname = ""
                archive.addfile(info, io.BytesIO(payload))
            prefix = stream.getvalue()
            cases["noncanonical_metadata"] = (
                prefix
                + f"{hashlib.md5(prefix).hexdigest()}  AP.tar\n".encode()
            )

            for name, payload in cases.items():
                with self.subTest(name=name):
                    path = root / f"{name}.tar.md5"
                    path.write_bytes(payload)
                    with self.assertRaises(self.module.F1TransportError):
                        with self.module.pin_boot_only_ap(
                            path,
                            label="candidate",
                            expected_size=len(payload),
                            expected_sha256=hashlib.sha256(payload).hexdigest(),
                        ):
                            pass

            rollback = root / "noncanonical_metadata.tar.md5"
            rollback_payload = cases["noncanonical_metadata"]
            with self.module.pin_boot_only_ap(
                rollback,
                label="rollback",
                expected_size=len(rollback_payload),
                expected_sha256=hashlib.sha256(rollback_payload).hexdigest(),
                require_deterministic_metadata=False,
            ) as pinned:
                self.assertEqual(
                    self.module.boot_only_member_receipt(
                        pinned,
                        label="rollback",
                        require_deterministic_metadata=False,
                    )["name"],
                    "boot.img.lz4",
                )
            bad_md5_path = root / "bad_md5.tar.md5"
            with self.assertRaises(self.module.F1TransportError):
                with self.module.pin_boot_only_ap(
                    bad_md5_path,
                    label="rollback",
                    expected_size=len(cases["bad_md5"]),
                    expected_sha256=hashlib.sha256(cases["bad_md5"]).hexdigest(),
                    require_deterministic_metadata=False,
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

            prefixed = root / "prefixed.tar.md5"
            size, digest = make_ap(
                prefixed, ("a" * 101 + "/boot.img.lz4",)
            )
            for label, deterministic in (("candidate", True), ("rollback", False)):
                with self.subTest(label=label):
                    with self.assertRaises(self.module.F1TransportError):
                        with self.module.pin_boot_only_ap(
                            prefixed,
                            label=label,
                            expected_size=size,
                            expected_sha256=digest,
                            require_deterministic_metadata=deterministic,
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
