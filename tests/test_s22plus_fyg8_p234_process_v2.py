import copy
import hashlib
import importlib.util
import json
import struct
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import s22plus_boot_verify as boot_verify_fixture  # noqa: E402


def lz4_store(payload):
    descriptor = bytes((0x68, 0x70)) + len(payload).to_bytes(8, "little")
    return (
        b"\x04\x22\x4d\x18"
        + descriptor
        + bytes(((boot_verify_fixture.xxh32(descriptor) >> 8) & 0xFF,))
        + (0x80000000 | len(payload)).to_bytes(4, "little")
        + payload
        + b"\x00\x00\x00\x00"
    )


def newc(entries):
    output = bytearray()
    for index, item in enumerate([*entries, ("TRAILER!!!", 0, b"")], 1):
        if len(item) == 3:
            name, mode, payload = item
            uid = gid = 0
            nlink = 1
        elif len(item) == 6:
            name, mode, payload, uid, gid, nlink = item
        else:
            raise ValueError("newc fixture entry shape is invalid")
        encoded = name.encode("ascii") + b"\0"
        fields = (
            index,
            mode,
            uid,
            gid,
            nlink,
            0,
            len(payload),
            0,
            0,
            0,
            0,
            len(encoded),
            0,
        )
        output += b"070701" + b"".join(
            f"{value:08x}".encode("ascii") for value in fields
        )
        output += encoded
        output += bytes((-len(output)) % 4)
        output += payload
        output += bytes((-len(output)) % 4)
    return bytes(output)


def boot_v4(kernel, ramdisk):
    kernel_start = 4096
    ramdisk_start = (kernel_start + len(kernel) + 4095) // 4096 * 4096
    total = (ramdisk_start + len(ramdisk) + 4095) // 4096 * 4096
    output = bytearray(total)
    output[:8] = b"ANDROID!"
    struct.pack_into("<4I", output, 8, len(kernel), len(ramdisk), 0, 1584)
    struct.pack_into("<I", output, 40, 4)
    struct.pack_into("<I", output, 1580, 0)
    output[kernel_start : kernel_start + len(kernel)] = kernel
    output[ramdisk_start : ramdisk_start + len(ramdisk)] = ramdisk
    return bytes(output)


def static_aarch64_elf(entrypoint, suffix=b""):
    base = 0x400000
    entry_offset = entrypoint - base
    if entry_offset < 120:
        raise ValueError("fixture entrypoint overlaps the ELF headers")
    data = bytearray(max(0x1200, entry_offset + 4))
    data.extend(suffix)
    ident = b"\x7fELF\x02\x01\x01" + bytes(9)
    struct.pack_into(
        "<16sHHIQQQIHHHHHH",
        data,
        0,
        ident,
        2,
        183,
        1,
        entrypoint,
        64,
        0,
        0,
        64,
        56,
        1,
        0,
        0,
        0,
    )
    struct.pack_into(
        "<IIQQQQQQ",
        data,
        64,
        1,
        5,
        0,
        base,
        base,
        len(data),
        len(data),
        0x1000,
    )
    struct.pack_into("<I", data, entry_offset, 0xD503201F)
    return bytes(data)


def load_module(name):
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"{name}_tested", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class P234ProcessV2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if str(SCRIPTS) not in sys.path:
            sys.path.insert(0, str(SCRIPTS))
        cls.module = load_module("prepare_s22plus_fyg8_p234_process_v2")
        cls.evidence = cls.module.evidence
        cls.core = load_module("device_action_f1_v2")

    @staticmethod
    def identity(seed, size=123):
        return {"size": size, "sha256": hashlib.sha256(seed).hexdigest()}

    def repin_candidate_static(self, payloads, acceptance, mutate):
        candidate = json.loads(payloads["candidate_static"])
        mutate(candidate)
        payloads["candidate_static"] = (
            json.dumps(candidate, indent=2, sort_keys=True).encode("ascii") + b"\n"
        )
        candidate_receipt = self.module.receipt(payloads["candidate_static"])

        run_manifest = json.loads(payloads["run_manifest"])
        run_manifest["candidate_static"] = candidate_receipt
        payloads["run_manifest"] = self.module.canonical(run_manifest)

        process_static = json.loads(payloads["static_check"])
        process_static["run_binding"] = {
            "canonical_manifest_size": len(payloads["run_manifest"]),
            "canonical_manifest_sha256": hashlib.sha256(
                payloads["run_manifest"]
            ).hexdigest(),
            "verified": True,
        }
        process_static["candidate"]["artifacts"]["candidate_static"] = (
            candidate_receipt
        )
        payloads["static_check"] = self.module.canonical(process_static)

        receipts = {
            name: self.module.receipt(payload) for name, payload in payloads.items()
        }
        acceptance["contract"] = {
            name: {"path": f"contracts/{name}.json", **value}
            for name, value in receipts.items()
        }
        return receipts

    def generic_rootfs(self, init, child, init_elf, child_elf):
        return {
            "entry_count": self.module.e2_closure.EXPECTED_GENERIC_ENTRY_COUNT,
            "no_duplicate_or_alias": True,
            "init": {
                **init,
                "uid": 0,
                "gid": 0,
                "mode": 0o750,
                "nlink": 1,
                "elf": init_elf,
                "run_id_count": 1,
                "required_strings_complete": True,
                "forbidden_authority_absent": True,
            },
            "child": {
                **child,
                "uid": 0,
                "gid": 0,
                "mode": 0o750,
                "nlink": 1,
                "elf": child_elf,
                "token_count": 1,
            },
            "rdinit_override_absent": True,
            "verified": True,
        }

    def fixture(self, profile="E1A"):
        model = self.evidence.e1_latest_stage.model
        profile_number = model.PROFILE_NUMBERS[profile]
        terminal = model.PROFILE_TERMINALS[profile]
        reachable_slot_variants = sum(
            1 if stage == terminal else 1 + 4095
            for stage in model.PROFILE_STAGE_SEQUENCES[profile]
        )
        intent = self.module.static_checker.contract.intent
        _source_data, source_rows = intent.source_receipts(ROOT, profile)
        preimage = intent.identity_preimage(
            bytes.fromhex("1234567890abcdef1234567890abcdef"),
            source_rows,
            profile,
        )
        preimage_sha256 = hashlib.sha256(intent.canonical(preimage)).hexdigest()
        run_id = intent.derive_run_id(preimage).hex()
        ap = self.identity(b"ap", 456)
        identities = {
            "artifact_result": self.identity(b"artifact-result"),
            "boot_img": self.identity(b"boot"),
            "boot_img_lz4": self.identity(b"lz4"),
            "ap_tar_md5": ap,
        }
        userspace = {
            "result": self.identity(b"userspace-result"),
            "init": self.identity(b"init"),
            "child": self.identity(b"child"),
            "two_build_byte_identical": True,
            "verified": True,
        }
        static_result = {
            "schema": self.module.static_checker.SCHEMA,
            "target": self.module.TARGET,
            "verdict": self.module.static_checker.VERDICT,
            "candidate_contract": {
                "schema": self.evidence.E1_LATEST_STAGE_CANDIDATE_CONTRACT_SCHEMA,
                "target": self.module.TARGET,
                "verdict": self.evidence.E1_LATEST_STAGE_CANDIDATE_CONTRACT_VERDICT,
                "profile": profile,
                "profile_number": profile_number,
                "run_id": run_id,
                "unsat_record_hex": self.evidence.e1_latest_stage.model.unsat_record(
                    profile, bytes.fromhex(run_id)
                ).hex(),
                "unsat_tag_hex": self.evidence.e1_latest_stage.model.unsat_record(
                    profile, bytes.fromhex(run_id)
                )[len(self.evidence.e1_latest_stage.model.UNSAT_FAMILY) :].hex(),
                "decoder_id": self.evidence.E1_LATEST_STAGE_DECODER,
                "decoder_policy_id": self.evidence.e1_latest_stage.POLICY_ID,
                "identity_preimage": preimage,
                "identity_preimage_sha256": preimage_sha256,
                "intent": self.identity(b"candidate-intent"),
                "patch": {
                    **self.identity(b"candidate-patch"),
                    "targets": sorted(self.evidence.E1_LATEST_STAGE_BASE_FILES),
                    "base_files": self.evidence.E1_LATEST_STAGE_BASE_FILES,
                    "patched_files": {
                        name: hashlib.sha256(name.encode("ascii")).hexdigest()
                        for name in self.evidence.E1_LATEST_STAGE_BASE_FILES
                    },
                    "config_lines": [
                        "CONFIG_S22PLUS_FYG8_E1_LATEST_STAGE=y",
                        f"CONFIG_S22PLUS_FYG8_E1_PROFILE={profile_number}",
                        f'CONFIG_S22PLUS_FYG8_E1_RUN_ID_HEX="{run_id}"',
                        "CONFIG_S22PLUS_FYG8_E1_UNSAT_TAG_HEX=\""
                        + self.evidence.e1_latest_stage.model.unsat_record(
                            profile, bytes.fromhex(run_id)
                        )[len(self.evidence.e1_latest_stage.model.UNSAT_FAMILY) :].hex()
                        + "\"",
                    ],
                    "clean_apply": True,
                    "verified": True,
                },
                "base_files": self.evidence.E1_LATEST_STAGE_BASE_FILES,
                "patched_files": {
                    name: hashlib.sha256(name.encode("ascii")).hexdigest()
                    for name in self.evidence.E1_LATEST_STAGE_BASE_FILES
                },
                "config_lines": [
                    "CONFIG_S22PLUS_FYG8_E1_LATEST_STAGE=y",
                    f"CONFIG_S22PLUS_FYG8_E1_PROFILE={profile_number}",
                    f'CONFIG_S22PLUS_FYG8_E1_RUN_ID_HEX="{run_id}"',
                    "CONFIG_S22PLUS_FYG8_E1_UNSAT_TAG_HEX=\""
                    + self.evidence.e1_latest_stage.model.unsat_record(
                        profile, bytes.fromhex(run_id)
                    )[len(self.evidence.e1_latest_stage.model.UNSAT_FAMILY) :].hex()
                    + "\"",
                ],
                "reachable_record_contract": {
                    "reachable_slot_variants": reachable_slot_variants,
                    "profiles": [profile],
                    "checked_run_ids": {profile: run_id},
                    "adjacent_slot_combinations_verified": True,
                    "zero_crc_count": 0,
                    "family_collision_count": 0,
                    "decoder_policy_id": self.evidence.e1_latest_stage.POLICY_ID,
                    "verified": True,
                },
                "verified": True,
                "safety": {
                    "host_only": True,
                    "device_contact": False,
                    "device_write": False,
                    "odin_invoked": False,
                    "live_authorized": False,
                },
            },
            "build_repro": {
                "result": self.identity(b"build-repro-result"),
                "image": self.identity(b"Image"),
                "fresh_reverification": True,
                "two_clean_builds_byte_identical": True,
                "linked_audit_verified": True,
            },
            "candidate": {
                "artifacts": identities,
                "candidate_b_artifacts": copy.deepcopy(identities),
                "base_boot": self.identity(b"base-boot"),
                "ap": {
                    "tar_md5": "a" * 32,
                    "member": {
                        "name": "boot.img.lz4",
                        "size": identities["boot_img_lz4"]["size"],
                        "mode": 0o644,
                        "uid": 0,
                        "gid": 0,
                        "mtime": 0,
                        "uname": "",
                        "gname": "",
                    },
                },
                "fixed_interval": {
                    "kernel_start": self.evidence.E1_LATEST_STAGE_KERNEL_INTERVAL[0],
                    "kernel_end_exclusive": self.evidence.E1_LATEST_STAGE_KERNEL_INTERVAL[1],
                    "header_preserved": True,
                    "ramdisk_preserved": True,
                    "outside_interval_changed_byte_count": 0,
                    "verified": True,
                },
                "userspace": userspace,
                "verified": True,
                "boot_only_ap": True,
                "independent_reconstruction": True,
                "independent_lz4_roundtrip": True,
                "independent_magiskboot_unpack": True,
                "writer_exclusion_verified": True,
                "two_package_builds_byte_identical": True,
                "manifest_absent": True,
            },
            "tools": {
                "lz4": self.identity(b"lz4"),
                "magiskboot": self.identity(b"magiskboot"),
                "qemu_aarch64": self.identity(b"qemu-aarch64"),
            },
            "limits": [
                "host-only artifact qualification grants no D0, D1, F1, or live authority",
                "candidate execution and retained observation remain unproved",
            ],
            "safety": {
                "host_only": True,
                "device_contact": False,
                "device_write": False,
                "odin_invoked": False,
                "flash": False,
                "partition_write": False,
                "manifest_created": False,
                "live_authorized": False,
            },
        }
        if profile == "E1B":
            static_result["candidate"].update(
                {
                    "module_closure": {
                        "files": copy.deepcopy(self.evidence.E1B_MODULE_FILES),
                        "runtime_names": copy.deepcopy(
                            self.evidence.E1B_MODULE_RUNTIME_NAMES
                        ),
                        "count": 5,
                        "modules": copy.deepcopy(self.evidence.E1B_MODULE_SPECS),
                        "order_model": self.evidence.E1B_MODULE_ORDER_MODEL,
                        "stock_recovery_positions": copy.deepcopy(
                            self.evidence.E1B_STOCK_RECOVERY_POSITIONS
                        ),
                        "vendor_metadata_hashes": copy.deepcopy(
                            self.evidence.E1B_VENDOR_METADATA_HASHES
                        ),
                    },
                    "effective_rootfs": {
                        "composition_order": copy.deepcopy(
                            self.evidence.E1B_COMPOSITION_ORDER
                        ),
                        "entry_count": self.evidence.E1B_EFFECTIVE_ENTRY_COUNT,
                        "init": {
                            **userspace["init"],
                            "elf": {
                                "verified": True,
                                "machine": "AArch64",
                                "entrypoint": self.evidence.E1B_ELF_ENTRYPOINTS[
                                    "init"
                                ],
                                "interpreter": False,
                                "dynamic": False,
                                "executable_stack": False,
                                "entrypoint_mapped": True,
                            },
                            "run_id_count": 1,
                        },
                        "child": {
                            **userspace["child"],
                            "elf": {
                                "verified": True,
                                "machine": "AArch64",
                                "entrypoint": self.evidence.E1B_ELF_ENTRYPOINTS[
                                    "child"
                                ],
                                "interpreter": False,
                                "dynamic": False,
                                "executable_stack": False,
                                "entrypoint_mapped": True,
                            },
                        },
                        "modules": copy.deepcopy(
                            self.evidence.E1B_EFFECTIVE_MODULE_ROWS
                        ),
                        "module_count": 5,
                        "no_duplicate_override_or_alias": True,
                        "rdinit_override_absent": True,
                        "verified": True,
                    },
                    "stock_vendor_boot": copy.deepcopy(
                        self.evidence.E1B_STOCK_VENDOR_BOOT
                    ),
                }
            )
        elif profile == "E2":
            required = (
                self.module.e2_closure.DEFAULT_VENDOR_RAMDISK,
                self.module.e2_closure.DEFAULT_LZ4,
            )
            if not all((ROOT / path).exists() for path in required):
                self.skipTest("exact FYG8 private inputs are unavailable")
            closure = self.module.e2_closure.derive_module_closure(
                ROOT,
                ROOT / self.module.e2_closure.DEFAULT_VENDOR_RAMDISK,
                ROOT / self.module.e2_closure.DEFAULT_LZ4,
            )
            init_elf = {
                "verified": True,
                "machine": "AArch64",
                "entrypoint": self.module.e2_closure.EXPECTED_ELF_ENTRYPOINTS["init"],
                "interpreter": False,
                "dynamic": False,
                "executable_stack": False,
                "entrypoint_mapped": True,
            }
            child_elf = {
                **init_elf,
                "entrypoint": self.module.e2_closure.EXPECTED_ELF_ENTRYPOINTS["child"],
            }
            static_result["candidate"].update(
                {
                    "module_closure": closure,
                    "effective_rootfs": {
                        "composition_order": ["generic", "vendor[0]/"],
                        "entry_count": 474,
                        "generic_rootfs": self.generic_rootfs(
                            userspace["init"],
                            userspace["child"],
                            init_elf,
                            child_elf,
                        ),
                        "no_duplicate_override_or_alias": True,
                        "init": {
                            **userspace["init"],
                            "elf": init_elf,
                            "run_id_count": 1,
                        },
                        "child": {
                            **userspace["child"],
                            "elf": child_elf,
                        },
                        "modules": [
                            {
                                "file": row["file"],
                                "runtime": row["runtime_name"],
                                "layer": "vendor[0]/",
                            }
                            for row in closure["modules"]
                        ],
                        "module_count": 59,
                        "module_closure_sha256": (
                            self.module.e2_closure.closure_sha256(closure)
                        ),
                        "rdinit_override_absent": True,
                        "verified": True,
                    },
                    "stock_vendor_boot": copy.deepcopy(
                        self.evidence.E1B_STOCK_VENDOR_BOOT
                    ),
                }
            )
        if profile == "E2":
            ap = {
                **ap,
                "member": {"name": "boot.img.lz4", **identities["boot_img_lz4"]},
            }
        candidate_static_payload = (
            json.dumps(static_result, indent=2, sort_keys=True).encode("ascii") + b"\n"
        )
        candidate_static = self.module.receipt(candidate_static_payload)
        run_payload, process_static = self.module.derive(
            static_result, candidate_static, ap
        )
        payloads = {
            "candidate_static": candidate_static_payload,
            "run_manifest": run_payload,
            "static_check": process_static,
        }
        receipts = {
            name: self.module.receipt(payload) for name, payload in payloads.items()
        }
        acceptance = {
            "kind": self.evidence.E1_LATEST_STAGE_KIND,
            "source": self.evidence.CHECKPOINT_SOURCE,
            "decoder": self.evidence.E1_LATEST_STAGE_DECODER,
            "policy_id": self.evidence.e1_latest_stage.POLICY_ID,
            "profile": profile,
            "run_id": run_id,
            "long_family_hex": self.evidence.e1_latest_stage.model.LONG_FAMILY.hex(),
            "unsat_family_hex": self.evidence.e1_latest_stage.model.UNSAT_FAMILY.hex(),
            "terminal_stage": self.evidence.e1_latest_stage.model.PROFILE_TERMINALS[
                profile
            ],
            "minimum_success_count": 1,
            "clean_baseline_required": True,
            "contract": {
                name: {"path": f"contracts/{name}.json", **value}
                for name, value in receipts.items()
            },
        }
        return static_result, candidate_static, ap, payloads, receipts, acceptance

    def coherently_repin_candidate_static(self, static_result, payloads, acceptance):
        forged_payload = (
            json.dumps(static_result, indent=2, sort_keys=True).encode("ascii") + b"\n"
        )
        forged_receipt = self.module.receipt(forged_payload)
        run_manifest = json.loads(payloads["run_manifest"])
        run_manifest["candidate_static"] = forged_receipt
        run_payload = self.module.canonical(run_manifest)
        process_static = json.loads(payloads["static_check"])
        process_static["candidate"]["artifacts"]["candidate_static"] = forged_receipt
        process_static["run_binding"] = {
            "canonical_manifest_size": len(run_payload),
            "canonical_manifest_sha256": hashlib.sha256(run_payload).hexdigest(),
            "verified": True,
        }
        repinned_payloads = {
            "candidate_static": forged_payload,
            "run_manifest": run_payload,
            "static_check": self.module.canonical(process_static),
        }
        receipts = {
            name: self.module.receipt(payload)
            for name, payload in repinned_payloads.items()
        }
        acceptance["contract"] = {
            name: {"path": f"contracts/{name}.json", **value}
            for name, value in receipts.items()
        }
        return repinned_payloads, receipts

    def test_promotion_and_offline_verifier_bind_exact_candidate(self):
        _static, candidate_static, ap, payloads, receipts, acceptance = self.fixture()
        result = self.evidence.verify_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=ap,
        )
        self.assertTrue(result["verified"])
        self.assertEqual(result["profile"], "E1A")
        self.assertEqual(result["candidate_ap_sha256"], ap["sha256"])
        self.assertEqual(
            result["candidate_static_sha256"], candidate_static["sha256"]
        )

    def test_offline_verifier_accepts_common_core_path_bearing_receipts(self):
        _static, candidate_static, ap, payloads, receipts, acceptance = self.fixture()
        pinned_receipts = {
            name: {"path": f"/private/contracts/{name}.json", **receipt}
            for name, receipt in receipts.items()
        }
        result = self.evidence.verify_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=pinned_receipts,
            candidate_ap=ap,
        )
        self.assertTrue(result["verified"])
        self.assertEqual(
            result["candidate_static_sha256"], candidate_static["sha256"]
        )

    def test_offline_verifier_rejects_changed_candidate_ap(self):
        _static, _candidate_static, ap, payloads, receipts, acceptance = self.fixture()
        changed = copy.deepcopy(ap)
        changed["sha256"] = "f" * 64
        with self.assertRaises(self.evidence.EvidenceError):
            self.evidence.verify_offline_contract(
                acceptance,
                payloads=payloads,
                receipts=receipts,
                candidate_ap=changed,
            )

    def test_offline_verifier_rejects_missing_candidate_static(self):
        _static, _candidate_static, ap, payloads, receipts, acceptance = self.fixture()
        payloads.pop("candidate_static")
        receipts.pop("candidate_static")
        acceptance["contract"].pop("candidate_static")
        with self.assertRaisesRegex(self.evidence.EvidenceError, "contract"):
            self.evidence.verify_offline_contract(
                acceptance,
                payloads=payloads,
                receipts=receipts,
                candidate_ap=ap,
            )

    def test_offline_verifier_rejects_coherently_forged_candidate_static(self):
        static, _candidate_static, ap, payloads, _receipts, acceptance = self.fixture()
        forged = copy.deepcopy(static)
        forged["build_repro"]["linked_audit_verified"] = False
        forged_payload = (
            json.dumps(forged, indent=2, sort_keys=True).encode("ascii") + b"\n"
        )
        forged_receipt = self.module.receipt(forged_payload)

        run_manifest = json.loads(payloads["run_manifest"])
        run_manifest["candidate_static"] = forged_receipt
        run_payload = self.module.canonical(run_manifest)
        process_static = json.loads(payloads["static_check"])
        process_static["candidate"]["artifacts"]["candidate_static"] = forged_receipt
        process_static["run_binding"] = {
            "canonical_manifest_size": len(run_payload),
            "canonical_manifest_sha256": hashlib.sha256(run_payload).hexdigest(),
            "verified": True,
        }
        payloads = {
            "candidate_static": forged_payload,
            "run_manifest": run_payload,
            "static_check": self.module.canonical(process_static),
        }
        receipts = {
            name: self.module.receipt(payload) for name, payload in payloads.items()
        }
        acceptance["contract"] = {
            name: {"path": f"contracts/{name}.json", **value}
            for name, value in receipts.items()
        }
        with self.assertRaisesRegex(self.evidence.EvidenceError, "build closure"):
            self.evidence.verify_offline_contract(
                acceptance,
                payloads=payloads,
                receipts=receipts,
                candidate_ap=ap,
            )

    def test_offline_verifier_rejects_false_reconstruction_proofs(self):
        for name in (
            "independent_reconstruction",
            "independent_lz4_roundtrip",
            "independent_magiskboot_unpack",
        ):
            with self.subTest(name=name):
                static, _candidate_static, ap, payloads, _receipts, acceptance = (
                    self.fixture()
                )
                static["candidate"][name] = False
                payloads, receipts = self.coherently_repin_candidate_static(
                    static, payloads, acceptance
                )
                with self.assertRaisesRegex(
                    self.evidence.EvidenceError, "artifact closure"
                ):
                    self.evidence.verify_offline_contract(
                        acceptance,
                        payloads=payloads,
                        receipts=receipts,
                        candidate_ap=ap,
                    )

    def test_offline_verifier_rejects_candidate_contract_shape_changes(self):
        for operation in ("omit", "extra"):
            with self.subTest(operation=operation):
                static, _candidate_static, ap, payloads, _receipts, acceptance = (
                    self.fixture()
                )
                if operation == "omit":
                    static["candidate_contract"].pop("base_files")
                else:
                    static["candidate_contract"]["unexpected"] = True
                payloads, receipts = self.coherently_repin_candidate_static(
                    static, payloads, acceptance
                )
                with self.assertRaisesRegex(self.evidence.EvidenceError, "keys"):
                    self.evidence.verify_offline_contract(
                        acceptance,
                        payloads=payloads,
                        receipts=receipts,
                        candidate_ap=ap,
                    )

    def test_offline_verifier_rejects_candidate_contract_value_change(self):
        static, _candidate_static, ap, payloads, _receipts, acceptance = self.fixture()
        static["candidate_contract"]["profile_number"] = 2
        payloads, receipts = self.coherently_repin_candidate_static(
            static, payloads, acceptance
        )
        with self.assertRaisesRegex(self.evidence.EvidenceError, "E1A-bound"):
            self.evidence.verify_offline_contract(
                acceptance,
                payloads=payloads,
                receipts=receipts,
                candidate_ap=ap,
            )

    def test_offline_verifier_rejects_candidate_contract_type_aliases(self):
        cases = (
            ("profile_number", True),
            ("zero_crc_count", False),
            ("family_collision_count", False),
            ("safety_host_only", 1),
            ("safety_device_contact", 0),
        )
        for name, value in cases:
            with self.subTest(name=name):
                static, _candidate_static, ap, payloads, _receipts, acceptance = (
                    self.fixture()
                )
                contract = static["candidate_contract"]
                if name == "profile_number":
                    contract[name] = value
                elif name.startswith("safety_"):
                    contract["safety"][name.removeprefix("safety_")] = value
                else:
                    contract["reachable_record_contract"][name] = value
                payloads, receipts = self.coherently_repin_candidate_static(
                    static, payloads, acceptance
                )
                with self.assertRaisesRegex(self.evidence.EvidenceError, "E1A-bound"):
                    self.evidence.verify_offline_contract(
                        acceptance,
                        payloads=payloads,
                        receipts=receipts,
                        candidate_ap=ap,
                    )

    def test_offline_verifier_rejects_cross_payload_identity_substitution(self):
        for name in ("image", "boot_image", "init", "child"):
            with self.subTest(name=name):
                _static, _candidate_static, ap, payloads, _receipts, acceptance = (
                    self.fixture()
                )
                process_static = json.loads(payloads["static_check"])
                process_static["candidate"]["artifacts"][name] = self.identity(
                    f"forged-{name}".encode("ascii"), 999
                )
                payloads["static_check"] = self.module.canonical(process_static)
                receipts = {
                    item: self.module.receipt(payload)
                    for item, payload in payloads.items()
                }
                acceptance["contract"] = {
                    item: {"path": f"contracts/{item}.json", **value}
                    for item, value in receipts.items()
                }
                with self.assertRaisesRegex(
                    self.evidence.EvidenceError, "does not bind"
                ):
                    self.evidence.verify_offline_contract(
                        acceptance,
                        payloads=payloads,
                        receipts=receipts,
                        candidate_ap=ap,
                    )

    def test_offline_verifier_rejects_omitted_candidate_static_structure(self):
        static, _candidate_static, ap, payloads, _receipts, acceptance = self.fixture()
        forged = copy.deepcopy(static)
        forged["candidate"].pop("candidate_b_artifacts")
        forged_payload = (
            json.dumps(forged, indent=2, sort_keys=True).encode("ascii") + b"\n"
        )
        forged_receipt = self.module.receipt(forged_payload)
        run_manifest = json.loads(payloads["run_manifest"])
        run_manifest["candidate_static"] = forged_receipt
        payloads["run_manifest"] = self.module.canonical(run_manifest)
        process_static = json.loads(payloads["static_check"])
        process_static["candidate"]["artifacts"]["candidate_static"] = forged_receipt
        process_static["run_binding"] = {
            "canonical_manifest_size": len(payloads["run_manifest"]),
            "canonical_manifest_sha256": hashlib.sha256(
                payloads["run_manifest"]
            ).hexdigest(),
            "verified": True,
        }
        payloads["candidate_static"] = forged_payload
        payloads["static_check"] = self.module.canonical(process_static)
        receipts = {
            item: self.module.receipt(payload) for item, payload in payloads.items()
        }
        acceptance["contract"] = {
            item: {"path": f"contracts/{item}.json", **value}
            for item, value in receipts.items()
        }
        with self.assertRaisesRegex(self.evidence.EvidenceError, "keys"):
            self.evidence.verify_offline_contract(
                acceptance,
                payloads=payloads,
                receipts=receipts,
                candidate_ap=ap,
            )

    def test_offline_verifier_rejects_noncanonical_manifest(self):
        _static, _candidate_static, ap, payloads, _receipts, acceptance = self.fixture()
        parsed = json.loads(payloads["run_manifest"])
        payloads["run_manifest"] = json.dumps(parsed, indent=2).encode("ascii")
        receipts = {
            name: self.module.receipt(payload) for name, payload in payloads.items()
        }
        acceptance["contract"] = {
            name: {"path": f"contracts/{name}.json", **value}
            for name, value in receipts.items()
        }
        with self.assertRaisesRegex(self.evidence.EvidenceError, "run manifest"):
            self.evidence.verify_offline_contract(
                acceptance,
                payloads=payloads,
                receipts=receipts,
                candidate_ap=ap,
            )

    def test_offline_verifier_rejects_incoherent_e1b_profile(self):
        _static, _candidate_static, ap, payloads, receipts, acceptance = self.fixture()
        acceptance["profile"] = "E1B"
        acceptance["terminal_stage"] = (
            self.evidence.e1_latest_stage.model.PROFILE_TERMINALS["E1B"]
        )
        with self.assertRaisesRegex(self.evidence.EvidenceError, "run manifest"):
            self.evidence.verify_offline_contract(
                acceptance,
                payloads=payloads,
                receipts=receipts,
                candidate_ap=ap,
            )

    def test_offline_verifier_accepts_coherent_e1b_profile(self):
        _static, candidate_static, ap, payloads, receipts, acceptance = self.fixture(
            "E1B"
        )
        result = self.evidence.verify_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=ap,
        )
        self.assertTrue(result["verified"])
        self.assertEqual(result["profile"], "E1B")
        self.assertEqual(result["terminal_stage"], 0x3F)
        self.assertEqual(result["candidate_static_sha256"], candidate_static["sha256"])

    def test_offline_verifier_accepts_coherent_e2_profile(self):
        _static, candidate_static, ap, payloads, receipts, acceptance = self.fixture(
            "E2"
        )
        result = self.evidence.verify_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=ap,
        )
        self.assertTrue(result["verified"])
        self.assertEqual(result["profile"], "E2")
        self.assertEqual(result["terminal_stage"], 0x8F)
        self.assertEqual(result["candidate_static_sha256"], candidate_static["sha256"])

    def test_offline_verifier_rejects_repinned_e2_module_tampering(self):
        _static, _candidate_static, ap, payloads, _receipts, acceptance = self.fixture(
            "E2"
        )
        receipts = self.repin_candidate_static(
            payloads,
            acceptance,
            lambda value: value["candidate"]["module_closure"]["modules"][
                0
            ].__setitem__("sha256", "0" * 64),
        )
        with self.assertRaisesRegex(
            self.evidence.EvidenceError, "E2 stock rootfs closure"
        ):
            self.evidence.verify_offline_contract(
                acceptance,
                payloads=payloads,
                receipts=receipts,
                candidate_ap=ap,
            )

    def test_e2_rejects_substituted_ap_boot_member(self):
        static, candidate_static, ap, payloads, receipts, acceptance = self.fixture("E2")
        changed = copy.deepcopy(ap)
        changed["member"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(
            self.module.PromotionError, "AP boot member"
        ):
            self.module.derive(static, candidate_static, changed)
        with self.assertRaisesRegex(
            self.evidence.EvidenceError, "artifact closure"
        ):
            self.evidence.verify_offline_contract(
                acceptance,
                payloads=payloads,
                receipts=receipts,
                candidate_ap=changed,
            )

    def test_e2_ap_payload_is_independently_decoded_to_kernel_and_userspace(self):
        self.fixture("E2")
        module_closure = self.module.e2_closure.derive_module_closure(
            ROOT,
            ROOT / self.module.e2_closure.DEFAULT_VENDOR_RAMDISK,
            ROOT / self.module.e2_closure.DEFAULT_LZ4,
        )
        run_id = bytes.fromhex("1234567890abcdef1234567890abcdef")
        image = b"synthetic-image"
        required_strings = [
            b"/proc/s22_checkpoint",
            b"/proc/modules",
            b"/sys/class/udc",
            b"a600000.dwc3",
            b"/s22-e1-child",
            *(row["file"].encode("ascii") for row in module_closure["modules"]),
        ]
        init = static_aarch64_elf(
            self.module.e2_closure.EXPECTED_ELF_ENTRYPOINTS["init"],
            b"\0".join([run_id, *required_strings]),
        )
        child_token = self.module.e2_closure.p241.p233.legacy_e1.CHILD_TOKEN
        child = static_aarch64_elf(
            self.module.e2_closure.EXPECTED_ELF_ENTRYPOINTS["child"],
            child_token,
        )
        generic_entries = [
            ("init", 0o100750, init),
            ("s22-e1-child", 0o100750, child),
            *[(f"fixture-{index}", 0o040755, b"") for index in range(20)],
        ]
        ramdisk = lz4_store(
            newc(generic_entries)
        )
        boot = boot_v4(image, ramdisk)
        frame = lz4_store(boot)
        init_identity = self.identity(init, len(init))
        child_identity = self.identity(child, len(child))
        init_elf = self.module.e2_closure.e1_static.inspect_static_elf(
            init, "fixture init"
        )
        child_elf = self.module.e2_closure.e1_static.inspect_static_elf(
            child, "fixture child"
        )
        generic_rootfs = self.generic_rootfs(
            init_identity, child_identity, init_elf, child_elf
        )
        effective_rootfs = {
            "composition_order": ["generic", "vendor[0]/"],
            "entry_count": 474,
            "generic_rootfs": generic_rootfs,
            "no_duplicate_override_or_alias": True,
            "init": {**init_identity, "elf": init_elf, "run_id_count": 1},
            "child": {**child_identity, "elf": child_elf},
            "modules": [
                {
                    "file": row["file"],
                    "runtime": row["runtime_name"],
                    "layer": "vendor[0]/",
                }
                for row in module_closure["modules"]
            ],
            "module_count": 59,
            "module_closure_sha256": self.module.e2_closure.closure_sha256(
                module_closure
            ),
            "rdinit_override_absent": True,
            "verified": True,
        }
        closure = {
            "boot_img_lz4": self.identity(frame, len(frame)),
            "boot_image": self.identity(boot, len(boot)),
            "image": self.identity(image, len(image)),
            "init": init_identity,
            "child": child_identity,
            "run_id": run_id.hex(),
            "module_closure": module_closure,
            "effective_rootfs": effective_rootfs,
        }
        self.assertTrue(
            self.evidence.validate_e2_ap_payload(frame, closure)["verified"]
        )
        changed = copy.deepcopy(closure)
        changed["image"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(self.evidence.EvidenceError, "kernel identity"):
            self.evidence.validate_e2_ap_payload(frame, changed)

        forged_entries = list(generic_entries)
        forged_entries[0] = ("init", 0o100750, b"not-an-elf")
        forged_boot = boot_v4(image, lz4_store(newc(forged_entries)))
        forged_frame = lz4_store(forged_boot)
        forged_closure = copy.deepcopy(closure)
        forged_closure["boot_img_lz4"] = self.identity(
            forged_frame, len(forged_frame)
        )
        forged_closure["boot_image"] = self.identity(
            forged_boot, len(forged_boot)
        )
        forged_init = self.identity(b"not-an-elf", len(b"not-an-elf"))
        forged_closure["init"] = forged_init
        for rootfs_init in (
            forged_closure["effective_rootfs"]["init"],
            forged_closure["effective_rootfs"]["generic_rootfs"]["init"],
        ):
            rootfs_init.update(forged_init)
        with self.assertRaisesRegex(
            self.evidence.EvidenceError, "executable semantics"
        ):
            self.evidence.validate_e2_ap_payload(forged_frame, forged_closure)

        directories = [
            (f"fixture-{index}", 0o040755, b"") for index in range(20)
        ]

        def repinned_payload(
            entries,
            *,
            init_payload=init,
            child_payload=child,
        ):
            mutated_boot = boot_v4(image, lz4_store(newc(entries)))
            mutated_frame = lz4_store(mutated_boot)
            mutated_closure = copy.deepcopy(closure)
            mutated_closure["boot_img_lz4"] = self.identity(
                mutated_frame, len(mutated_frame)
            )
            mutated_closure["boot_image"] = self.identity(
                mutated_boot, len(mutated_boot)
            )
            for name, payload in (("init", init_payload), ("child", child_payload)):
                identity = self.identity(payload, len(payload))
                mutated_closure[name] = identity
                mutated_closure["effective_rootfs"][name].update(identity)
                mutated_closure["effective_rootfs"]["generic_rootfs"][name].update(
                    identity
                )
            return mutated_frame, mutated_closure

        duplicate_run_init = static_aarch64_elf(
            self.module.e2_closure.EXPECTED_ELF_ENTRYPOINTS["init"],
            b"\0".join([run_id, run_id, *required_strings]),
        )
        missing_required_init = static_aarch64_elf(
            self.module.e2_closure.EXPECTED_ELF_ENTRYPOINTS["init"],
            b"\0".join(
                [
                    run_id,
                    *(value for value in required_strings if value != b"/sys/class/udc"),
                ]
            ),
        )
        forbidden_init = static_aarch64_elf(
            self.module.e2_closure.EXPECTED_ELF_ENTRYPOINTS["init"],
            b"\0".join([run_id, *required_strings, b"/dev/block"]),
        )
        duplicate_token_child = static_aarch64_elf(
            self.module.e2_closure.EXPECTED_ELF_ENTRYPOINTS["child"],
            child_token + b"\0" + child_token,
        )
        semantic_mutations = {
            "init_uid": (
                [("init", 0o100750, init, 1, 0, 1), ("s22-e1-child", 0o100750, child), *directories],
                init,
                child,
            ),
            "init_gid": (
                [("init", 0o100750, init, 0, 1, 1), ("s22-e1-child", 0o100750, child), *directories],
                init,
                child,
            ),
            "init_mode": (
                [("init", 0o100755, init), ("s22-e1-child", 0o100750, child), *directories],
                init,
                child,
            ),
            "init_nlink": (
                [("init", 0o100750, init, 0, 0, 2), ("s22-e1-child", 0o100750, child), *directories],
                init,
                child,
            ),
            "run_id_cardinality": (
                [("init", 0o100750, duplicate_run_init), ("s22-e1-child", 0o100750, child), *directories],
                duplicate_run_init,
                child,
            ),
            "required_string_missing": (
                [("init", 0o100750, missing_required_init), ("s22-e1-child", 0o100750, child), *directories],
                missing_required_init,
                child,
            ),
            "forbidden_string_present": (
                [("init", 0o100750, forbidden_init), ("s22-e1-child", 0o100750, child), *directories],
                forbidden_init,
                child,
            ),
            "child_token_cardinality": (
                [("init", 0o100750, init), ("s22-e1-child", 0o100750, duplicate_token_child), *directories],
                init,
                duplicate_token_child,
            ),
        }
        for name, (entries, init_payload, child_payload) in semantic_mutations.items():
            with self.subTest(actual_cpio_mutation=name):
                mutated_frame, mutated_closure = repinned_payload(
                    entries,
                    init_payload=init_payload,
                    child_payload=child_payload,
                )
                with self.assertRaisesRegex(
                    self.evidence.EvidenceError, "executable semantics"
                ):
                    self.evidence.validate_e2_ap_payload(
                        mutated_frame, mutated_closure
                    )

    def test_e2_rejects_repinned_source_preimage_without_matching_run_id(self):
        _static, _candidate_static, ap, payloads, _receipts, acceptance = self.fixture(
            "E2"
        )

        def mutate(value):
            preimage = value["candidate_contract"]["identity_preimage"]
            preimage["sources"]["runtime_wrapper"]["sha256"] = "0" * 64
            value["candidate_contract"]["identity_preimage_sha256"] = hashlib.sha256(
                self.evidence._canonical(preimage)
            ).hexdigest()

        receipts = self.repin_candidate_static(payloads, acceptance, mutate)
        with self.assertRaisesRegex(
            self.evidence.EvidenceError, "source preimage or run ID"
        ):
            self.evidence.verify_offline_contract(
                acceptance,
                payloads=payloads,
                receipts=receipts,
                candidate_ap=ap,
            )

    def test_offline_verifier_rejects_repinned_impossible_e1b_closures(self):
        cases = {
            "empty_stock_derivation": lambda value: (
                value["candidate"]["module_closure"].__setitem__(
                    "stock_recovery_positions", {}
                ),
                value["candidate"]["module_closure"].__setitem__(
                    "vendor_metadata_hashes", {}
                ),
            ),
            "unbound_composition": lambda value: (
                value["candidate"]["effective_rootfs"].__setitem__(
                    "composition_order", ["generic"]
                ),
                [
                    row.__setitem__("layer", "vendor[99]/forged")
                    for row in value["candidate"]["effective_rootfs"]["modules"]
                ],
            ),
            "extra_non_dictionary_module": lambda value: value["candidate"][
                "effective_rootfs"
            ]["modules"].append("forged"),
        }
        for name, mutate in cases.items():
            with self.subTest(name=name):
                _static, _candidate_static, ap, payloads, _receipts, acceptance = (
                    self.fixture("E1B")
                )
                receipts = self.repin_candidate_static(
                    payloads, acceptance, mutate
                )
                with self.assertRaisesRegex(
                    self.evidence.EvidenceError, "E1B .*closure"
                ):
                    self.evidence.verify_offline_contract(
                        acceptance,
                        payloads=payloads,
                        receipts=receipts,
                        candidate_ap=ap,
                    )

    def test_promotion_rejects_e1b_rootfs_identity_tampering(self):
        cases = {
            "module_digest": lambda value: value["candidate"]["module_closure"][
                "modules"
            ][0].__setitem__("sha256", "0" * 64),
            "vendor_boot": lambda value: value["candidate"][
                "stock_vendor_boot"
            ].__setitem__("sha256", "0" * 64),
            "module_layer": lambda value: value["candidate"]["effective_rootfs"][
                "modules"
            ][0].__setitem__("layer", "generic"),
            "init_identity": lambda value: value["candidate"]["effective_rootfs"][
                "init"
            ].__setitem__("sha256", "0" * 64),
        }
        for name, mutate in cases.items():
            with self.subTest(name=name):
                static, candidate_static, ap, _payloads, _receipts, _acceptance = (
                    self.fixture("E1B")
                )
                mutate(static)
                with self.assertRaisesRegex(
                    self.module.PromotionError, "E1B effective"
                ):
                    self.module.derive(static, candidate_static, ap)

    def test_promotion_rejects_e2_rootfs_identity_tampering(self):
        static, candidate_static, ap, _payloads, _receipts, _acceptance = (
            self.fixture("E2")
        )
        static["candidate"]["effective_rootfs"]["modules"][0]["layer"] = (
            "vendor[1]/forged"
        )
        with self.assertRaisesRegex(self.module.PromotionError, "E2 effective"):
            self.module.derive(static, candidate_static, ap)

    def test_promotion_rejects_unverified_writer_exclusion(self):
        static_result, candidate_static, ap, _payloads, _receipts, _acceptance = (
            self.fixture()
        )
        static_result["candidate"]["writer_exclusion_verified"] = False
        with self.assertRaisesRegex(self.module.PromotionError, "independently closed"):
            self.module.derive(static_result, candidate_static, ap)

    def test_approval_binding_excludes_unreachable_p234_build_tools(self):
        _static, _candidate_static, _ap, _payloads, _receipts, acceptance = (
            self.fixture()
        )
        sources = self.core.execution_critical_source_receipts(acceptance)
        self.assertIn("e1_latest_stage_decoder", sources)
        self.assertIn("e1_latest_stage_design_model", sources)
        self.assertNotIn("e1_latest_stage_static_checker", sources)
        self.assertNotIn("e1_candidate_static_checker", sources)
        self.assertNotIn("e1_process_v2_promotion", sources)

    def test_e2_approval_binding_includes_exact_source_and_validator_closure(self):
        _static, _candidate_static, _ap, _payloads, _receipts, acceptance = (
            self.fixture("E2")
        )
        sources = self.core.execution_critical_source_receipts(acceptance)
        contract_sources = _static["candidate_contract"]["identity_preimage"][
            "sources"
        ]
        for name, expected in contract_sources.items():
            actual = sources[f"candidate_source_{name}"]
            self.assertEqual(
                {key: actual[key] for key in ("size", "sha256")}, expected
            )
        self.assertIn("candidate_intent", sources)
        self.assertIn("e2_boot_verify", sources)
        self.assertIn("e2_legacy_static_elf", sources)
        verification = {
            "candidate_source_receipts": copy.deepcopy(contract_sources)
        }
        self.core.verify_candidate_source_binding(
            acceptance, verification, sources
        )
        changed = copy.deepcopy(sources)
        changed["candidate_source_runtime_wrapper"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(
            self.core.F1V2Error, "execution-critical sources"
        ):
            self.core.verify_candidate_source_binding(
                acceptance, verification, changed
            )
        verification["candidate_source_receipts"].pop("runtime_wrapper")
        with self.assertRaisesRegex(self.core.F1V2Error, "incomplete"):
            self.core.verify_candidate_source_binding(
                acceptance, verification, sources
            )


if __name__ == "__main__":
    unittest.main()
