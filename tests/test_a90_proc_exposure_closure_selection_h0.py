"""Public-only pinning for the A90 /proc closure-selection H0 document."""

from __future__ import annotations

from pathlib import Path
import unittest


REPO = Path(__file__).resolve().parents[1]
DOC = REPO / (
    "docs/plans/"
    "A90_PROC_EXPOSURE_CLOSURE_SELECTION_H0_2026-08-15.md"
)
HANDOFF = REPO / "workspace/public/src/native-init/a90_server_distro.c"


class A90ProcExposureClosureSelectionTests(unittest.TestCase):
    def test_selected_closure_and_h0_proof_boundary_are_pinned(self) -> None:
        document = DOC.read_text(encoding="utf-8")
        document_flat = " ".join(document.split())
        source = HANDOFF.read_text(encoding="utf-8")

        for phrase in (
            "`DEBIAN_OWNS_WIFI_ZERO_NATIVE_SIDECARS`",
            "`NESTED_PID_NAMESPACE_ISOLATION`",
            "The explicit selection is `NESTED_PID_NAMESPACE_ISOLATION`",
            "fresh PID namespace",
            "distinct superblock and",
            "`nosuid,nodev,noexec,hidepid=2`",
            "`/proc/<native-pid>/{root,fd,ns}` is not nameable",
            "produces `ENOENT` for `/proc/<native-pid>` itself",
            "no host-proc bind, native proc FD, pidfd, nsfs FD",
            "written before `execve()` is called",
            "H16 did not prove Debian PID 1 or Dropbear",
            "does not claim that H16 failed to reach userspace",
            "Native PID 1 keeps ownership of `wlan0`",
            "one bound veth peer",
            "`block ingress -> record cause -> reap -> cleanup`",
            "negative corpus",
            "`NO_PROOF_OBSERVER`",
            "device-attributable contradiction is `REFUTED`",
            "Candidate identity: **unallocated**",
            "D0: **unallocated**",
            "F1: **unallocated**",
            "D1: **unallocated**",
            "No ordinal, version, build string, manifest",
        ):
            self.assertIn(phrase, document_flat)

        self.assertLess(
            document.index("The explicit selection is `NESTED_PID_NAMESPACE_ISOLATION`"),
            document.index("## Allocation state"),
        )
        marker = source.index('a90_benchmark_mark("switch_root_exec")')
        exec_call = source.index("execve(A90_D3_BUSYBOX", marker)
        self.assertLess(marker, exec_call)


if __name__ == "__main__":
    unittest.main()
