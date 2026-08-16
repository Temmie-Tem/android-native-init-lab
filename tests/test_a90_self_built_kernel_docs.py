"""Pin the A90 self-built kernel report, especially its limits and its deviation.

The report records a build success. The two ways it could become harmful are
(1) drifting into a claim that the device boots, which no evidence supports,
and (2) letting the disabled RKP CFP mitigation quietly stop reading as a
security reduction. These tests hold both, and cross-check the artifact
digests and the boot header parity claim against the real staged files rather
than against the report's own prose.
"""

from __future__ import annotations

import hashlib
import struct
from pathlib import Path
import unittest


def flatten(text: str) -> str:
    """Collapse wrapping and blockquote markers, as the sibling docs tests do."""
    return " ".join(text.replace("> ", " ").split())


REPO = Path(__file__).resolve().parents[1]
REPORT = REPO / "docs/reports/A90_SELF_BUILT_KERNEL_H0_2026-08-16.md"
COMPOSITION = REPO / "docs/reports/A90_WLAN_KERNEL_SIDE_COMPOSITION_H0_2026-08-15.md"
CONFIRMATION = REPO / "docs/reports/A90_WLAN_KERNEL_SOURCE_CONFIRMATION_H0_2026-08-16.md"
BOOT_IMAGES = REPO / "workspace/private/inputs/boot_images"
BASE_IMAGE = BOOT_IMAGES / "boot_a90_base_selfbuilt_kernel_20260816.img"
DELETED = BOOT_IMAGES / "boot_a90_h24_selfbuilt_nocfp_20260816.img"
RESIDENT = REPO / (
    "workspace/private/outputs"
    "/a90-h24-minimal-debian-dev-ab-20260812-01/A/boot.img"
)
RESIDENT_B = REPO / (
    "workspace/private/outputs"
    "/a90-h24-minimal-debian-dev-ab-20260812-01/B/boot.img"
)
ROLLBACK = BOOT_IMAGES / "boot_linux_v2321_usb_clean_identity_rodata.img"
SOURCE_TARBALL = REPO / (
    "workspace/private/inputs/kernel_source"
    "/SM-A908N_KOR_12_Opensource_13272/Kernel.tar.gz"
)

BASE_SHA = "2d0be40158d56b6b053bc1aff6c6e149beb904da43a303b812e8ca6c4d583a9e"
BASE_SIZE = 66375680
RESIDENT_SHA = "d8c280e4acee5d17d13270fdf25535b4ce05304e786bc22efa84ab16f6b82782"
ROLLBACK_SHA = "ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb"
TARBALL_SHA = "403fdc49f086d238c01a796c390083c3c47c1754c218e228f29b55cc7c35d554"
IMAGE_SHA = "6cab67938d2d235ad5ad965abaefe7e3ebda6d13b57251705c91f5f333ab1b6d"


def boot_header(path: Path) -> dict[str, object]:
    """Parse the Android boot image header fields this report compares."""
    raw = path.read_bytes()[:1632]
    if raw[:8] != b"ANDROID!":
        raise ValueError(f"not an Android boot image: {path}")
    fields = struct.unpack("<10I", raw[8:48])
    return {
        "kernel_size": fields[0],
        "kernel_addr": fields[1],
        "ramdisk_size": fields[2],
        "ramdisk_addr": fields[3],
        "second_size": fields[4],
        "second_addr": fields[5],
        "tags_addr": fields[6],
        "page_size": fields[7],
        "header_version": fields[8],
        "os_version": fields[9],
        "name": raw[48:64],
        "cmdline": raw[64:576],
    }


class SelfBuiltKernelDocsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.raw = REPORT.read_text(encoding="utf-8")
        self.report = flatten(self.raw)

    def require_candidate(self) -> None:
        if not BASE_IMAGE.is_file():
            self.skipTest(f"private artifact not staged on this host: {BASE_IMAGE}")

    def test_the_build_versus_boot_limit_is_stated_before_anything_else(self) -> None:
        """The likeliest way this report becomes wrong is drifting into a boot claim."""
        head = flatten(self.raw[: self.raw.index("## Why this build was attempted")])
        self.assertIn("whether the device boots it is **unproved**", head)
        self.assertIn("No boot has been attempted", head)
        self.assertIn("requires a separately authorized F1", head)
        self.assertIn("Device or live effect: none", head)

    def test_the_report_never_claims_the_device_boots(self) -> None:
        self.assertIn("It does not prove the device boots", self.report)
        self.assertIn("A format-valid image can still boot-loop", self.report)
        self.assertIn("The first flash is an attended F1", self.report)
        self.assertIn("It is not authorized by this report", self.report)

    def test_the_cfp_removal_reads_as_a_security_reduction(self) -> None:
        """A hardening removal must not soften into a footnote."""
        self.assertIn(
            "**This lowers the device's security posture and should be recorded as such.**",
            self.raw,
        )
        self.assertIn("kernel exploit mitigation", self.report)
        self.assertIn("none of them is a claim that the loss is harmless", self.report)
        self.assertIn("removing it is a real reduction on this unit", self.report)
        self.assertIn("no such compensation is proved", self.report)

    def test_the_cfp_deviation_is_exactly_three_symbols(self) -> None:
        for symbol in (
            "CONFIG_RKP_CFP",
            "CONFIG_RKP_CFP_JOPP",
            "CONFIG_RKP_CFP_ROPP",
        ):
            self.assertIn(f"# {symbol} is not set", self.raw, symbol)
        self.assertIn("exactly three symbols", self.report)
        for retained in ("CONFIG_UH_RKP", "CONFIG_RKP_KDP", "rkp_init", "uh_call"):
            self.assertIn(retained, self.report, retained)

    def test_the_s22plus_precedent_is_not_misused(self) -> None:
        """S22+ did not disable CFP; that tree has no CFP. The report must say so."""
        self.assertIn("The S22+ precedent does **not** transfer", self.raw)
        self.assertIn("that target did not disable the feature", self.report.lower())
        self.assertIn("That is context, not equivalence", self.report)

    def test_the_option_c_compensation_is_offered_only_as_unproved(self) -> None:
        self.assertIn("this report does not make that argument", self.report.lower())

    def test_the_rebuild_does_not_contradict_the_wlan_finding(self) -> None:
        """The 2026-08-15 report said a rebuild removes no WLAN role; that stands."""
        self.assertTrue(COMPOSITION.is_file(), str(COMPOSITION))
        self.assertIn("removes **none** of the thirteen WLAN vendor roles", self.raw)
        self.assertIn("that conclusion is unchanged", self.report)
        self.assertIn("It does not retire any WLAN gate", self.report)
        self.assertIn("`H0D01` through `H0D10` are unchanged", self.report)

    def test_binderfs_is_named_as_still_disabled(self) -> None:
        self.assertIn("# CONFIG_ANDROID_BINDERFS is not set", self.raw)
        self.assertIn("It does not enable `CONFIG_ANDROID_BINDERFS`", self.report)
        self.assertIn("That symbol remains off", self.report)

    def test_the_four_blockers_are_each_recorded_with_a_mechanism(self) -> None:
        for token in (
            "m4 subprocess failed",
            "#!/usr/bin/env python2",
            "dangerous relocation: unsupported relocation",
            "R_AARCH64_ABS32 cannot be used against symbol",
            "KeyError: 'jopp_springboard_blr_x16'",
            "Unknown command line argument '-cfp-jopp'",
        ):
            self.assertIn(token, self.report, token)
        self.assertIn("no system package was installed", self.report)

    def test_the_silent_cc_option_drop_is_explained(self) -> None:
        """Why the build appeared to succeed before failing is the useful part."""
        self.assertIn("arrives through `cc-option`", self.report)
        self.assertIn("drops it **silently**", self.report)

    def test_the_device_tree_reuse_is_declared(self) -> None:
        self.assertIn("Device tree was reused, not rebuilt", self.raw)
        self.assertIn("997,113", self.report)
        self.assertIn("keeps the experiment to one variable", self.report)

    def test_the_size_delta_is_not_read_as_equivalence(self) -> None:
        self.assertIn("A one-page delta is **not** evidence of equivalence", self.raw)
        self.assertIn("an observation, not a similarity proof", self.report)
        self.assertIn("It does not prove functional equivalence to stock", self.report)

    def test_the_staged_source_digest_matches_the_report(self) -> None:
        if not SOURCE_TARBALL.is_file():
            self.skipTest(f"private artifact not staged on this host: {SOURCE_TARBALL}")
        digest = hashlib.sha256(SOURCE_TARBALL.read_bytes()).hexdigest()
        self.assertEqual(digest, TARBALL_SHA)
        self.assertIn(TARBALL_SHA, self.raw)

    def test_the_candidate_image_matches_its_recorded_digest(self) -> None:
        """The one test that catches the report describing a different artifact."""
        self.require_candidate()
        raw = BASE_IMAGE.read_bytes()
        self.assertEqual(len(raw), BASE_SIZE)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), BASE_SHA)
        self.assertIn(BASE_SHA, self.raw)
        self.assertIn(IMAGE_SHA, self.raw)

    def test_the_base_image_pairs_our_kernel_with_the_v3403_ramdisk(self) -> None:
        """The base image is a builder input, not a candidate.

        Its ramdisk is deliberately the v3403 base, not the resident's, because
        the flat builder overlays onto a base ramdisk and rejects a built one.
        """
        self.require_candidate()
        head = boot_header(BASE_IMAGE)
        self.assertEqual(head["kernel_size"], 49823517)
        self.assertEqual(head["ramdisk_size"], 16545280)
        self.assertIn(b"service_locator.enable=1", head["cmdline"])
        if RESIDENT.is_file():
            self.assertNotEqual(
                head["ramdisk_size"],
                boot_header(RESIDENT)["ramdisk_size"],
                "base image must not carry the resident ramdisk",
            )

    def test_the_candidate_kernel_is_arm64_with_the_stock_dtb_region(self) -> None:
        """The S22+ silent boot loop is why the format check is a test, not prose."""
        self.require_candidate()
        raw = BASE_IMAGE.read_bytes()
        page = boot_header(BASE_IMAGE)["page_size"]
        assert isinstance(page, int)
        blob = raw[page : page + 49823517]
        self.assertEqual(blob[:16], b"UNCOMPRESSED_IMG")
        size = struct.unpack("<I", blob[16:20])[0]
        self.assertEqual(size, 48826384)
        self.assertEqual(blob[20 + 56 : 20 + 60], b"ARMd", "ARM64 magic absent")
        self.assertEqual(hashlib.sha256(blob[20 : 20 + size]).hexdigest(), IMAGE_SHA)
        dtb = blob[20 + size :]
        self.assertEqual(len(dtb), 997113)
        self.assertEqual(dtb[:4].hex(), "d00dfeed")

    def test_the_resident_ab_build_is_deterministic_and_pinned(self) -> None:
        if not (RESIDENT.is_file() and RESIDENT_B.is_file()):
            self.skipTest(f"private artifact not staged on this host: {RESIDENT}")
        a = hashlib.sha256(RESIDENT.read_bytes()).hexdigest()
        b = hashlib.sha256(RESIDENT_B.read_bytes()).hexdigest()
        self.assertEqual(a, b, "resident A/B build is not reproducible")
        self.assertEqual(a, RESIDENT_SHA)
        self.assertIn(RESIDENT_SHA, self.raw)

    def test_the_bound_rollback_is_v2321_and_not_a_convenient_substitute(self) -> None:
        """The report previously named the wrong rollback; the contract names V2321."""
        self.assertIn("V2321 remains the exact bound rollback", self.report)
        self.assertIn("none of the `v33xx`/`v34xx` images", self.report)
        if not ROLLBACK.is_file():
            self.skipTest(f"private artifact not staged on this host: {ROLLBACK}")
        self.assertEqual(
            hashlib.sha256(ROLLBACK.read_bytes()).hexdigest(), ROLLBACK_SHA
        )
        self.assertIn(ROLLBACK_SHA, self.raw)

    def test_the_report_denies_f1_readiness_with_named_preconditions(self) -> None:
        """Asked whether this can be flashed now, the report must answer no."""
        self.assertIn("This is not an F1-ready candidate", self.report)
        for token in (
            "No successor candidate is authorized",
            "No fresh connected D0",
            "No candidate qualification",
            "Attended-only",
            "It is a build product, not a qualified candidate",
        ):
            self.assertIn(token, self.report, token)
        goal = (REPO / "GOAL_A90.md").read_text(encoding="utf-8")
        self.assertIn(
            "No successor candidate, approval, transfer, reboot, or D1 effect",
            flatten(goal),
        )

    def test_the_superseded_image_is_declared_and_absent(self) -> None:
        """A report must not cite an artifact that no longer exists."""
        self.assertIn("was superseded and deleted", self.raw)
        self.assertIn("contract-invalid as a candidate", self.report)
        self.assertIn("could be mistaken for a candidate", self.report)
        self.assertNotIn(
            "boot_a90_h24_selfbuilt_nocfp_20260816.img",
            self.raw,
            "the report must not cite the deleted artifact",
        )
        self.assertFalse(DELETED.exists(), "the superseded image must not be staged")

    def test_the_locator_cross_reference_still_exists(self) -> None:
        self.assertTrue(CONFIRMATION.is_file(), str(CONFIRMATION))
        self.assertIn("service_locator.enable=1", self.report)
        self.assertIn("service_locator.enable=1", CONFIRMATION.read_text(encoding="utf-8"))

    def test_no_authority_is_created_and_the_boundary_is_stated(self) -> None:
        self.assertIn("no human-verification bypass occurred", self.report)
        self.assertIn("excluded from commit by", self.report)
        self.assertIn("authority is granted or implied", self.report)
        self.assertNotIn("192.168.", self.raw, "build host IP must not be recorded")


if __name__ == "__main__":
    unittest.main()
