from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p319_stock_candidate_build.py"
)
OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "stock-witness-runtime-v1-20260821-42"
)
PHASE2_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "stock-witness-runtime-v1-20260821-43"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p319_stock_witness_runtime", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("unable to load stock-witness runtime auditor")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class P319StockWitnessRuntimeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.bound = cls.module._bound_auditor_module()
        cls.result = json.loads((OUTPUT / "result.json").read_bytes())
        cls.sources = {
            path.name: path.read_bytes()
            for path in (OUTPUT / "stock-sources").iterdir()
        }
        cls.helper = cls.module._load_parser_helpers()
        cls.runtime = cls.sources[cls.module.RUNTIME_INCLUDE_NAME]

    def test_private_result_is_durable_and_audit_only_reproduces(self):
        result = OUTPUT / "result.json"
        state = result.stat()
        self.assertEqual(stat.S_IMODE(state.st_mode), 0o400)
        self.assertEqual(state.st_nlink, 1)
        self.assertEqual(len(result.read_bytes()), 382_264)
        self.assertEqual(
            self.module.sha256(result.read_bytes()),
            "982f903f7685f63e5b2fbadebc5a3bbef5d98f009207ac352bda80777b09e886",
        )
        self.assertEqual(
            self.bound.build_result(OUTPUT, audit_only=True), self.result
        )

    def test_phase2_is_host_only_and_auditable(self):
        result_path = PHASE2_OUTPUT / "result.json"
        phase2_result = json.loads(result_path.read_bytes())
        self.assertEqual(phase2_result["phase2"]["userspace_compiles"], 3)
        self.assertEqual(phase2_result["phase2"]["boot_builds"], 2)
        self.assertEqual(phase2_result["phase2"]["ap_builds"], 2)
        self.assertEqual(phase2_result["scope"]["userspace_compiles"], 3)
        self.assertEqual(phase2_result["scope"]["boot_builds"], 2)
        self.assertEqual(phase2_result["scope"]["ap_builds"], 2)
        self.assertFalse(phase2_result["scope"]["device_contact"])
        self.assertTrue(phase2_result["phase2"]["candidate"]["byte_identical"])
        self.assertTrue(phase2_result["phase2"]["candidate"]["exact_one_member_generic_overlay"])
        self.assertEqual(phase2_result["phase2"]["candidate"]["vendor_layer_stock_modules"], 72)
        self.assertEqual(
            phase2_result["phase2"]["candidate"]["overlay_members"],
            [
                "lib/modules/s22plus_dwc3_event_latch.ko",
            ],
        )
        self.assertTrue(phase2_result["phase2"]["candidate"]["inherited_modules_not_copied"])
        self.assertEqual(
            self.bound.build_result(PHASE2_OUTPUT, audit_only=True), phase2_result
        )

    def test_stock_domain_abi_width_and_chain_are_distinct(self):
        profile = self.result["profile"]
        self.assertEqual(profile["domain"], "S22PLUS-FYG8-MAX77705-STOCK-V1")
        self.assertEqual(profile["encoding"], 4)
        self.assertEqual(profile["payload_abi"], 3)
        self.assertEqual(profile["status_width"], 3)
        self.assertEqual(
            profile["chain"], ["irq", "initial_status", "classification", "probe"]
        )
        self.assertTrue(profile["parent_unavailable"])
        self.assertTrue(profile["w5_unavailable"])
        self.assertFalse(profile["enhanced_witness_claimable"])
        self.assertTrue(profile["parent_w5_and_five_byte_claim_rejected"])
        self.assertTrue(profile["unsupported_parent_w5_markers_rejected"])
        self.assertTrue(profile["auxiliary_form2_deferred_accepted"])
        self.assertFalse(profile["late_diagnostic_reachable"])
        self.assertNotEqual(profile["domain"], "S22PLUS-FYG8-MAX77705-DIAG-V5")

    def test_reachable_runtime_keeps_prefix_and_cuts_diagnostic_tail(self):
        body = self.helper._c_function_body(self.runtime, "p318_run")
        self.assertIn(b"p260_create_gadget", body)
        self.assertIn(b"p260_bind_udc", body)
        self.assertIn(b"p313_wait_state_window", body)
        self.assertIn(b"p319_stock_publish(tty_fd);", body)
        for forbidden in (
            b"p316_", b"p317_", b"p241_finit_module", b"P316_DIAG",
            b"p316_observe_diagnostic", b"p317_capture_policy",
            b"i2c", b"I2C",
        ):
            self.assertNotIn(forbidden, body)
        self.assertNotIn(b"p316_prepare_overrides();", self.sources[self.module.RUNTIME_NAME])

    def test_enhanced_markers_are_rejected_and_not_staged(self):
        observer = self.helper._c_function_body(self.runtime, "p319_witness_observe_v2")
        self.assertIn(b"max77705_usbc_umask_irq", observer)
        self.assertIn(b"p319_observe_class2", observer)
        self.assertIn(b"p319_observe_deferred", observer)
        self.assertIn(b"P319_DETAIL_WITNESS_GRAMMAR_CONTRADICTION", observer)
        self.assertEqual(observer.count(b"p319_observe_irq("), 1)
        self.assertEqual(observer.count(b"p319_observe_initial("), 1)
        self.assertEqual(observer.count(b"p319_observe_class1("), 1)
        self.assertEqual(observer.count(b"p319_observe_probe("), 1)
        initial = self.helper._c_function_body(self.runtime, "p319_observe_initial")
        self.assertNotIn(b"CC0:", initial)
        self.assertNotIn(b"CC1:", initial)
        self.assertNotIn(b"initial_status[3] =", initial)
        self.assertNotIn(b"initial_status[4] =", initial)

    def test_stock_encoder_is_not_the_inherited_diagnostic_encoder(self):
        encoder = self.helper._c_function_body(
            self.runtime, "s22plus_max77705_p319_stock_encode"
        )
        self.assertIn(b"STOCK_DETAIL_COMPLETE 0x6724U", self.runtime)
        self.assertIn(b"STOCK_DETAIL_INCOMPLETE 0x6725U", self.runtime)
        self.assertIn(b"STOCK_DETAIL_AMBIGUOUS 0x6726U", self.runtime)
        self.assertIn(b"STOCK-V1\\0", self.runtime)
        self.assertNotIn(b"s22plus_max77705_p319_encode_envelope_v5(", encoder)
        self.assertNotIn(b"s22plus_max77705_p318_encode_envelope(", encoder)
        self.assertNotIn(b"s22plus_max77705_binding_witness", encoder)
        self.assertIn(b"STOCK_PARENT_UNAVAILABLE", encoder)
        self.assertIn(b"STOCK_W5_UNAVAILABLE", encoder)

    def test_executed_c_stock_encoder_fixture_accepts_only_stock_states(self):
        start = self.runtime.index(b"/* P3.19 stock-emitter envelope")
        end = self.runtime.index(b"static __attribute__((noreturn)) void p319_stock_publish")
        encoder = self.runtime[start:end]
        bypass_start = encoder.index(b"static void p319_stock_bypass_to_pair")
        bypass_end = encoder.index(b"static int s22plus_max77705_p319_stock_encode", bypass_start)
        encoder = encoder[:bypass_start] + encoder[bypass_end:]
        header = b'''#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdio.h>
#include <limits.h>
#define S22PLUS_MAX77705_ENVELOPE_SIZE 128U
#define S22PLUS_MAX77705_ENVELOPE_CRC_OFFSET 124U
#define S22PLUS_MAX77705_ENVELOPE_PAYLOAD_OFFSET 48U
#define S22PLUS_MAX77705_P319_WITNESS_FLAG (1U << 5U)
#define S22PLUS_MAX77705_P319_PAYLOAD_USED 76U
#define S22PLUS_MAX77705_P319_STOCK_ENCODING 4U
#define S22PLUS_MAX77705_P319_STOCK_STATUS_WIDTH 3U
#define S22PLUS_MAX77705_P319_STOCK_PAYLOAD_ABI 3U
#define S22PLUS_MAX77705_P319_VALID_MODULE69 (1U << 3U)
#define S22PLUS_MAX77705_P319_VALID_MODULE71 (1U << 4U)
#define S22PLUS_MAX77705_P319_VALID_MODULE72 (1U << 5U)
#define S22PLUS_MAX77705_P319_VALID_INITIAL (1U << 6U)
#define S22PLUS_MAX77705_P319_VALID_CLASS1 (1U << 7U)
#define P319_WITNESS_ABI_VERSION 2U
#define P319_WITNESS_MASK_PROBE (1U << 0U)
#define P319_WITNESS_MASK_IRQ (1U << 1U)
#define P319_WITNESS_MASK_INITIAL (1U << 2U)
#define P319_WITNESS_MASK_CLASS1 (1U << 3U)
#define P319_WITNESS_MASK_CLASS2 (1U << 4U)
#define P319_WITNESS_MASK_DEFERRED (1U << 5U)
#define P319_WITNESS_MASK_PARENT (1U << 6U)
#define P319_KMSG_MAX_MODULES 73U
#define P319_KMSG_MAX_TOTAL_RECORDS 4096U
#define P319_KMSG_MAX_TOTAL_BYTES 1048576ULL
#define P319_DETAIL_WITNESS_GRAMMAR_CONTRADICTION 0x6020L
#define P319_DETAIL_WITNESS_COUNTER_OVERFLOW 0x6021L
#define P319_DETAIL_WITNESS_BOUNDARY 0x6022L
static size_t cstr_len(const char *s) { return strlen(s); }
static int p260_bytes_equal(const char *a, const char *b, size_t n) {
    return memcmp(a, b, n) == 0;
}
static uint32_t s22plus_max77705_envelope_crc_update(uint32_t c, const uint8_t *d, size_t n) {
    for (size_t i = 0; i < n; ++i) { c ^= d[i]; for (unsigned b = 0; b < 8; ++b) c = (c >> 1) ^ (0xedb88320U & (0U - (c & 1U))); }
    return c;
}
static void s22plus_max77705_store_le16(uint8_t *o, uint16_t v) { o[0] = v; o[1] = v >> 8; }
static void s22plus_max77705_store_le32(uint8_t *o, uint32_t v) { o[0] = v; o[1] = v >> 8; o[2] = v >> 16; o[3] = v >> 24; }
static void s22plus_max77705_p319_store_le24(uint8_t *o, uint32_t v) { o[0] = v; o[1] = v >> 8; o[2] = v >> 16; }
static void s22plus_max77705_p319_store_le64(uint8_t *o, uint64_t v) { for (unsigned i = 0; i < 8; ++i) o[i] = v >> (i * 8U); }
struct p319_module_result_state_v1 { uint32_t index; int32_t result; uint8_t name_length; uint8_t valid; char name[64]; };
struct p319_witness_summary_state_v2 {
    uint32_t abi_version, witness_mask, probe_count, irq_count, initial_status_count, parent_mask_count, classification_form1_count, classification_form2_count, deferred_status_count, malformed_count;
    uint64_t classification_form1_index, classification_form2_index; int32_t classification_form2_attached_dev;
    uint8_t classification_form1_name_length, classification_form2_name_length; char classification_form1_name[64], classification_form2_name[64];
    uint32_t module_loads, module_drains, drains, initial_status[5], parent_mask_readback; int32_t irq[5];
    uint64_t record_count, record_bytes, first_sequence, last_sequence; uint8_t first_sequence_valid, last_sequence_valid, active_module_valid, initial_chain_stage, initial_chain_complete, initial_chain_ambiguous;
    uint32_t active_module_index, initial_chain_module_index; struct p319_module_result_state_v1 target_modules[3];
};
'''
        main = b'''
static int check(uint8_t *e, uint16_t detail, uint16_t expected) { return e[0]=='M' && e[1]=='X' && e[2]=='D' && e[3]=='5' && e[43]==4 && e[48]==3 && e[104]==3 && detail==expected; }
int main(void) {
    struct p319_witness_summary_state_v2 w = {0}; uint8_t e[128]; uint16_t d = 0;
    w.abi_version=2; w.module_loads=73; w.module_drains=73; w.witness_mask=0x0f; w.probe_count=1; w.irq_count=1; w.initial_status_count=1; w.classification_form1_count=1; w.initial_chain_stage=4; w.initial_chain_complete=1; w.initial_chain_module_index=72; w.initial_status[0]=0x27; w.initial_status[1]=5; w.initial_status[2]=0x82;
    const char *names[3]={"i2c-msm-geni.ko","mfd_max77705.ko","pdic_max77705.ko"}; for (unsigned i=0;i<3;++i) { w.target_modules[i].valid=1; w.target_modules[i].index=i==0?69:(i==1?71:72); w.target_modules[i].result=0; w.target_modules[i].name_length=(uint8_t)strlen(names[i]); memcpy(w.target_modules[i].name,names[i],strlen(names[i])); }
    w.classification_form2_count=2; w.deferred_status_count=3; w.witness_mask|=P319_WITNESS_MASK_CLASS2|P319_WITNESS_MASK_DEFERRED;
    if (s22plus_max77705_p319_stock_encode(&w,0,e,&d)!=0 || !check(e,d,0x6724) || e[48+59]!=2 || e[48+60]!=3) return 1;
    w.classification_form2_count=0; w.deferred_status_count=0; w.witness_mask=0x0f; w.initial_status[3]=1; if (s22plus_max77705_p319_stock_encode(&w,0,e,&d)==0) return 2; w.initial_status[3]=0; w.witness_mask|=P319_WITNESS_MASK_PARENT; if (s22plus_max77705_p319_stock_encode(&w,0,e,&d)==0) return 3;
    w.witness_mask=0x0f; w.initial_chain_complete=0; w.initial_chain_stage=3; w.initial_chain_module_index=0; if (s22plus_max77705_p319_stock_encode(&w,1,e,&d)!=0 || !check(e,d,0x6725)) return 4;
    w.initial_chain_ambiguous=1; if (s22plus_max77705_p319_stock_encode(&w,2,e,&d)!=0 || !check(e,d,0x6726)) return 5; return 0;
}
'''
        with tempfile.TemporaryDirectory(prefix="p319-stock-encoder-c-") as directory:
            root = Path(directory)
            source = root / "fixture.c"
            binary = root / "fixture"
            source.write_bytes(header + encoder + main)
            compile_result = subprocess.run(
                ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", source, "-o", binary],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
            run_result = subprocess.run([binary], capture_output=True, text=True, check=False)
            self.assertEqual(run_result.returncode, 0, run_result.stderr)

    def test_executed_c_stock_publisher_uses_two_terminal_positions(self):
        start = self.runtime.index(b"/* P3.19 stock-emitter envelope")
        end = self.runtime.index(b"static __attribute__((noreturn)) void p319_stock_publish")
        encoder = self.runtime[start:end]
        publisher = (
            b"static __attribute__((noreturn)) void "
            + self.helper._c_function_body(self.runtime, "p319_stock_publish")
        )
        self.assertNotIn(b"p316_", publisher)
        header = b'''#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdlib.h>
#include <limits.h>
#define S22PLUS_MAX77705_ENVELOPE_SIZE 128U
#define S22PLUS_MAX77705_ENVELOPE_CRC_OFFSET 124U
#define S22PLUS_MAX77705_ENVELOPE_PAYLOAD_OFFSET 48U
#define S22PLUS_MAX77705_P319_WITNESS_FLAG (1U << 5U)
#define S22PLUS_MAX77705_P319_PAYLOAD_USED 76U
#define S22PLUS_MAX77705_P319_STOCK_ENCODING 4U
#define S22PLUS_MAX77705_P319_STOCK_STATUS_WIDTH 3U
#define S22PLUS_MAX77705_P319_STOCK_PAYLOAD_ABI 3U
#define S22PLUS_MAX77705_P319_VALID_MODULE69 (1U << 3U)
#define S22PLUS_MAX77705_P319_VALID_MODULE71 (1U << 4U)
#define S22PLUS_MAX77705_P319_VALID_MODULE72 (1U << 5U)
#define S22PLUS_MAX77705_P319_VALID_INITIAL (1U << 6U)
#define S22PLUS_MAX77705_P319_VALID_CLASS1 (1U << 7U)
#define P319_WITNESS_ABI_VERSION 2U
#define P319_WITNESS_MASK_PROBE (1U << 0U)
#define P319_WITNESS_MASK_IRQ (1U << 1U)
#define P319_WITNESS_MASK_INITIAL (1U << 2U)
#define P319_WITNESS_MASK_CLASS1 (1U << 3U)
#define P319_WITNESS_MASK_CLASS2 (1U << 4U)
#define P319_WITNESS_MASK_DEFERRED (1U << 5U)
#define P319_WITNESS_MASK_PARENT (1U << 6U)
#define P319_KMSG_MAX_MODULES 73U
#define S22PLUS_MAX77705_A_DETAIL 0x0da3U
#define P313_DETAIL_CHECKPOINT_POSITION_CONTRADICTION 0x6720L
static size_t cstr_len(const char *s) { return strlen(s); }
static int p260_bytes_equal(const char *a, const char *b, size_t n) { return memcmp(a, b, n) == 0; }
static uint32_t s22plus_max77705_envelope_crc_update(uint32_t c, const uint8_t *d, size_t n) { for (size_t i=0;i<n;++i) { c ^= d[i]; for (unsigned b=0;b<8;++b) c = (c>>1) ^ (0xedb88320U & (0U-(c&1U))); } return c; }
static void s22plus_max77705_store_le16(uint8_t *o, uint16_t v) { o[0]=v; o[1]=v>>8; }
static void s22plus_max77705_store_le32(uint8_t *o, uint32_t v) { o[0]=v; o[1]=v>>8; o[2]=v>>16; o[3]=v>>24; }
static void s22plus_max77705_p319_store_le24(uint8_t *o, uint32_t v) { o[0]=v; o[1]=v>>8; o[2]=v>>16; }
static void s22plus_max77705_p319_store_le64(uint8_t *o, uint64_t v) { for (unsigned i=0;i<8;++i) o[i]=v>>(i*8U); }
struct p319_module_result_state_v1 { uint32_t index; int32_t result; uint8_t name_length; uint8_t valid; char name[64]; };
struct p319_witness_summary_state_v2 {
 uint32_t abi_version,witness_mask,probe_count,irq_count,initial_status_count,parent_mask_count,classification_form1_count,classification_form2_count,deferred_status_count,malformed_count;
 uint64_t classification_form1_index,classification_form2_index; int32_t classification_form2_attached_dev;
 uint8_t classification_form1_name_length,classification_form2_name_length; char classification_form1_name[64],classification_form2_name[64];
 uint32_t module_loads,module_drains,drains,initial_status[5],parent_mask_readback; int32_t irq[5];
 uint64_t record_count,record_bytes,first_sequence,last_sequence; uint8_t first_sequence_valid,last_sequence_valid,active_module_valid,initial_chain_stage,initial_chain_complete,initial_chain_ambiguous;
 uint32_t active_module_index,initial_chain_module_index; struct p319_module_result_state_v1 target_modules[3];
};
static struct p319_witness_summary_state_v2 fixture;
static struct { int progress; int terminal; unsigned int generation; } g_checkpoint;
static int expect_contradiction;
static int p319_witness_summary_state_v2_copy(struct p319_witness_summary_state_v2 *out) { *out=fixture; return 0; }
static void p290_fail_next(long value) { if (value != P313_DETAIL_CHECKPOINT_POSITION_CONTRADICTION || g_checkpoint.progress || !expect_contradiction) exit(20); exit(0); }
static long s22_max77705_checkpoint_payload_progress_position(void *checkpoint, unsigned int position, unsigned int detail, uint8_t *payload) { (void)payload; if (checkpoint != &g_checkpoint || position != 105U || detail != S22PLUS_MAX77705_A_DETAIL) exit(11); g_checkpoint.progress=1; return 0; }
static long s22_max77705_checkpoint_payload_terminal_position(void *checkpoint, unsigned int position, unsigned int detail, uint8_t *payload) { (void)payload; if (checkpoint != &g_checkpoint || position != 106U || detail != 0x6724U) exit(12); g_checkpoint.terminal=1; return 0; }
static __attribute__((noreturn)) void p292_park_after_checkpoint_error(long value) { (void)value; exit(13); }
static __attribute__((noreturn)) void p290_park_after_confirmed_publication(void) { if (expect_contradiction) exit(21); exit(g_checkpoint.progress && g_checkpoint.terminal ? 0 : 14); }
'''
        main = b'''int main(int argc, char **argv) {
 fixture.abi_version=2; fixture.module_loads=73; fixture.module_drains=73; fixture.witness_mask=0x0f; fixture.probe_count=1; fixture.irq_count=1; fixture.initial_status_count=1; fixture.classification_form1_count=1; fixture.initial_chain_stage=4; fixture.initial_chain_complete=1; fixture.initial_chain_module_index=72; fixture.initial_status[0]=0x27; fixture.initial_status[1]=5; fixture.initial_status[2]=0x82;
 const char *names[3]={"i2c-msm-geni.ko","mfd_max77705.ko","pdic_max77705.ko"}; for (unsigned i=0;i<3;++i) { fixture.target_modules[i].valid=1; fixture.target_modules[i].index=i==0?69:(i==1?71:72); fixture.target_modules[i].name_length=(uint8_t)strlen(names[i]); memcpy(fixture.target_modules[i].name,names[i],strlen(names[i])); }
 if (argc > 1) { expect_contradiction=1; if (strcmp(argv[1], "generation-104") == 0) g_checkpoint.generation=104U; else if (strcmp(argv[1], "generation-106") == 0) g_checkpoint.generation=106U; else if (strcmp(argv[1], "terminal") == 0) { g_checkpoint.generation=105U; g_checkpoint.terminal=1; } else return 19; p319_stock_publish(0); return 15; }
 g_checkpoint.generation=105U;
 p319_stock_publish(0); return 15;
}
'''
        with tempfile.TemporaryDirectory(prefix="p319-stock-publisher-c-") as directory:
            root = Path(directory); source = root / "fixture.c"; binary = root / "fixture"
            source.write_bytes(header + encoder + publisher + main)
            compile_result = subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", source, "-o", binary], capture_output=True, text=True, check=False)
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
            run_result = subprocess.run([binary], capture_output=True, text=True, check=False)
            self.assertEqual(run_result.returncode, 0, run_result.stderr)
            bypass_result = subprocess.run([binary, "generation-106"], capture_output=True, text=True, check=False)
            self.assertEqual(bypass_result.returncode, 0, bypass_result.stderr)
            self.assertEqual(subprocess.run([binary, "generation-104"], capture_output=True, text=True, check=False).returncode, 0)
            self.assertEqual(subprocess.run([binary, "terminal"], capture_output=True, text=True, check=False).returncode, 0)

    def test_crc_resolution_and_image_table_binding(self):
        closure = self.result["module_crc_closure"]
        self.assertEqual(closure["module_count"], 73)
        self.assertEqual(closure["total_imports"], 3_566)
        self.assertEqual(
            closure["provider_resolution"],
            {
                "fixed_image_imports": 3_238,
                "earlier_module_imports": 328,
                "total_resolved_imports": 3_566,
            },
        )
        self.assertEqual(closure["duplicate_provider_count"], 0)
        self.assertEqual(closure["ambiguous_provider_count"], 0)
        self.assertEqual(closure["missing_provider_count"], 0)
        self.assertTrue(closure["ordered_crc_closed"])
        self.assertEqual(closure["image_derived_vermagic_suffix"],
                         self.result["fixed_image_abi"]["image_vermagic"]["suffix"])
        sections = self.result["fixed_image_abi"]["sections"]
        self.assertEqual(self.result["fixed_image_abi"]["image_provider_count"], 7222)
        self.assertTrue(sections["__ksymtab_strings"]["raw_bounds_checked"])
        self.assertNotIn("sha256_vmlinux", sections["__ksymtab_strings"])
        self.assertNotIn("value_field_differences", sections["__ksymtab"])
        self.assertNotIn("value_field_differences", sections["__ksymtab_gpl"])
        self.assertEqual(
            self.result["fixed_image_abi"]["image_ikconfig"]["run_id_hex"],
            "b9cc424d0d184f5accbce94a844e817d",
        )
        self.assertEqual(
            self.result["fixed_image_abi"]["image_ikconfig"]["unsat_tag_hex"],
            "ecbfff41d2c5ed22383db45dedfb622d",
        )
        self.assertEqual(
            self.result["fixed_image_abi"]["image_ikconfig"]["decompressed"]["size"],
            185508,
        )
        self.assertNotIn("vmlinux", self.result["fixed_image_abi"])
        self.assertNotIn("symvers", self.result["fixed_image_abi"])
        self.assertFalse(
            self.result["fixed_image_abi"]["same_magic"][
                "full_release_token_equality_required"
            ]
        )

    def test_executed_checkpoint_allowlist_positive_and_adjacent_negative(self):
        with tempfile.TemporaryDirectory(prefix="p319-checkpoint-source-") as source_dir:
            checkpoint = self.module.materialize_stock_sources(Path(source_dir) / "stock")[self.module.CHECKPOINT_NAME]
        p288 = self.helper._c_function_body(checkpoint, "p288_detail_allowed")
        stock = self.helper._c_function_body(checkpoint, "s22_max77705_detail_allowed")
        header = b'''#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#define S22_MAX77705_FIRST_POSITION 105U
#define S22_MAX77705_TERMINAL_POSITION 106U
#define S22_MAX77705_FIRST_DETAIL 0xda3U
#define S22_MAX77705_TERMINAL_DETAIL_FIRST 0x6701U
#define S22_MAX77705_TERMINAL_DETAIL_LAST 0x6709U
#define S22_MAX77705_MUX_DETAIL_FIRST 0x6710U
#define S22_MAX77705_MUX_DETAIL_LAST 0x6714U
#define S22_P233_OUTCOME_PROGRESS 0U
#define S22_P233_OUTCOME_FAILURE 2U
#define S22_P248_STEP_NORMAL 0U
#define S22_P248_STEP_GATE 1U
#define S22_P248_STEP_TERMINAL 2U
#define S22_P248_DETAIL_ERRNO_MAX 0x7ffU
#define S22_P248_DETAIL_REGRESSION_BASE 0x800U
#define S22_P248_DETAIL_REGRESSION_MAX 0x8ffU
#define S22_P248_DETAIL_READ_ERROR_BASE 0x900U
#define S22_P248_DETAIL_READ_ERROR_MAX 0x9ffU
#define S22_MAX77705_STOCK_DETAIL_FIRST 0x6724U
#define S22_MAX77705_STOCK_DETAIL_LAST 0x6726U
#define S22_P292_PUBLICATION_OPEN_BASE 0x100U
#define S22_P292_PUBLICATION_WRITE_BASE 0x200U
#define S22_P292_PUBLICATION_CLOSE_BASE 0x300U
#define S22_P292_PUBLICATION_ERRNO_MAX 0x7fU
struct s22_p248_step { uint8_t stage; uint8_t item_index; uint8_t kind; };
static const struct s22_p248_step k_p248_e2_steps[107] = {[106] = {0, 0, S22_P248_STEP_TERMINAL}};
struct p288_detail_rule { size_t ordinal; uint8_t outcome; uint16_t detail; };
static const struct p288_detail_rule k_p288_detail_rules[1] = {{0, 0, 0}};
static int p288_tuple_allowed(size_t ordinal, uint8_t outcome, uint16_t detail) { (void)ordinal; (void)outcome; (void)detail; return 0; }
'''
        main = b'''int main(void) {
    if (!p288_detail_allowed(106, 2, 0x6724) || !s22_max77705_detail_allowed(106, 2, 0x6724)) return 1;
    if (p288_detail_allowed(106, 2, 0x6723) || s22_max77705_detail_allowed(106, 2, 0x6723)) return 2;
    if (p288_detail_allowed(106, 2, 0x6727) || s22_max77705_detail_allowed(106, 2, 0x6727)) return 3;
    if (p288_detail_allowed(105, 2, 0x6724) || s22_max77705_detail_allowed(105, 2, 0x6724)) return 4;
    return 0;
}
'''
        with tempfile.TemporaryDirectory(prefix="p319-checkpoint-allowlist-c-") as directory:
            root = Path(directory)
            source = root / "fixture.c"
            binary = root / "fixture"
            source.write_bytes(header + b"static int " + p288 + b"\nstatic int " + stock + b"\n" + main)
            compiled = subprocess.run(
                ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", source, "-o", binary],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            executed = subprocess.run([binary], capture_output=True, text=True, check=False)
            self.assertEqual(executed.returncode, 0, executed.stderr)

    def test_exact_plan_module_and_phase_scope(self):
        plan = self.result["plan"]
        self.assertEqual(plan["module_count"], 73)
        self.assertEqual(plan["eud_index"], 38)
        self.assertEqual(plan["rows"][38]["file"], "eud.ko")
        self.assertEqual(plan["rows"][72]["file"], "pdic_max77705.ko")
        self.assertEqual(len(list((OUTPUT / "module-bytes").iterdir())), 73)
        self.assertFalse(self.result["phase2_inputs"]["boot_build"])
        self.assertFalse(self.result["phase2_inputs"]["ap_build"])
        self.assertEqual(self.result["scope"]["boot_builds"], 0)
        self.assertEqual(self.result["scope"]["ap_builds"], 0)
        self.assertEqual(self.result["scope"]["userspace_compiles"], 0)
        self.assertFalse(self.result["scope"]["device_contact"])

    def test_no_clobber(self):
        with tempfile.TemporaryDirectory(prefix="p319-stock-noclobber-") as directory:
            root = Path(directory) / "occupied"
            root.mkdir()
            marker = root / "marker"
            marker.write_bytes(b"unchanged")
            with self.assertRaises(self.module.AuditError):
                self.module.build_result(root)
            self.assertEqual(marker.read_bytes(), b"unchanged")

    def test_direct_import_and_old_code_new_auditor_are_fail_closed(self):
        with self.assertRaises(self.module.AuditError):
            self.module.build_result(OUTPUT, audit_only=True)
        with tempfile.TemporaryDirectory(prefix="p319-auditor-drift-") as directory:
            changed = Path(directory) / "auditor.py"
            changed.write_bytes(SCRIPT.read_bytes() + b"\n# auditor drift\n")
            changed.chmod(0o400)
            original_auditor = self.bound.AUDITOR
            try:
                self.bound.AUDITOR = changed
                with self.assertRaises(self.bound.AuditError):
                    self.bound._load_bound_auditor_source()
            finally:
                self.bound.AUDITOR = original_auditor

    def test_v5_source_identity_and_receipt_mutations_fail_closed(self):
        with tempfile.TemporaryDirectory(prefix="p319-v5-source-copy-") as directory:
            root = Path(directory) / "materialized-sources"
            shutil.copytree(self.module.V5_SOURCES, root)
            original = root / self.module.PLAN_NAME
            original.chmod(0o600)
            original.write_bytes(original.read_bytes() + b"\n")
            original.chmod(0o400)
            with self.assertRaises(self.module.AuditError):
                self.module._v5_materialized_source_identities(
                    self.module.V5_RECEIPT.read_bytes(), root
                )

    def test_materialized_stock_source_mode_mutation_is_fail_closed(self):
        name = self.module.CHECKPOINT_NAME
        payload = (OUTPUT / "stock-sources" / name).read_bytes()
        with tempfile.TemporaryDirectory(prefix="p319-stock-source-hostile-") as directory:
            path = Path(directory) / name
            path.write_bytes(payload)
            path.chmod(0o600)
            with self.assertRaises(self.bound.AuditError):
                self.bound.stable_bytes(
                    path, "hostile stock source mode", 2 * 1024 * 1024,
                    self.bound.identity(payload), required_mode=0o400,
                    required_nlink=1,
                )

    def test_private_latch_snapshot_is_the_only_module_authority(self):
        _, static_result, materialization, _ = self.bound._reviewed_module_inputs()
        plan = self.bound.parse_plan(
            (self.bound.V5_SOURCES / self.bound.PLAN_NAME).read_bytes()
        )
        with tempfile.TemporaryDirectory(prefix="p319-latch-snapshot-hostile-") as directory:
            snapshot = Path(directory) / "module-bytes"
            shutil.copytree(self.bound.PINNED_MODULE_SNAPSHOT, snapshot)
            latch = snapshot / "s22plus_dwc3_event_latch.ko"
            external = Path(directory) / "external-latch.ko"
            external.write_bytes(b"external widened latch")
            external.chmod(0o600)
            self.bound.LATCH = external
            old_root = self.bound.PINNED_MODULE_SNAPSHOT
            try:
                self.bound.PINNED_MODULE_SNAPSHOT = snapshot
                # The widened external path is deliberately irrelevant: the
                # private snapshot remains the sole module authority.
                payloads, _, _ = self.bound._load_exact_module_payloads(
                    plan, static_result, materialization
                )
                self.assertIn("s22plus_dwc3_event_latch.ko", payloads)

                # A snapshot mode change is rejected before any module
                # import/export audit can consume it.
                latch.chmod(0o600)
                with self.assertRaises(self.bound.AuditError):
                    self.bound._load_exact_module_payloads(plan, static_result, materialization)
                latch.chmod(0o400)

                # A byte mutation is rejected against the reviewed static
                # identity, and a hardlink is rejected by nlink=1.
                original = latch.read_bytes()
                latch.chmod(0o600)
                latch.write_bytes(bytes([original[0] ^ 1]) + original[1:])
                latch.chmod(0o400)
                with self.assertRaises(self.bound.AuditError):
                    self.bound._load_exact_module_payloads(plan, static_result, materialization)
                latch.chmod(0o600)
                latch.write_bytes(original)
                latch.chmod(0o400)
                hardlink = Path(directory) / "latch-hardlink.ko"
                os.link(latch, hardlink)
                with self.assertRaises(self.bound.AuditError):
                    self.bound._load_exact_module_payloads(plan, static_result, materialization)
            finally:
                self.bound.PINNED_MODULE_SNAPSHOT = old_root
                delattr(self.bound, "LATCH")

    def test_snapshot_mode_extra_child_and_code_mutation_fail_closed(self):
        name = "s22plus_dwc3_event_latch.ko"
        original = (OUTPUT / "module-bytes" / name).read_bytes()
        expected = self.bound.identity(original)
        with tempfile.TemporaryDirectory(prefix="p319-module-hostile-") as directory:
            root = Path(directory) / "module-bytes"
            root.mkdir(mode=0o700)
            path = root / name
            path.write_bytes(original)
            path.chmod(0o400)
            path.chmod(0o600)
            with self.assertRaises(self.bound.AuditError):
                self.bound.stable_bytes(path, "hostile module mode", 8 * 1024 * 1024, expected, required_mode=0o400, required_nlink=1)
            path.chmod(0o600)
            path.write_bytes(bytes([original[0] ^ 1]) + original[1:])
            path.chmod(0o400)
            with self.assertRaises(self.bound.AuditError):
                self.bound.stable_bytes(path, "hostile module bytes", 8 * 1024 * 1024, expected, required_mode=0o400, required_nlink=1)
            extra = root / "unexpected.ko"
            extra.write_bytes(b"x")
            extra.chmod(0o400)
            with self.assertRaises(self.bound.AuditError):
                self.bound._strict_directory(root, "hostile module set", {name})

    def test_input_image_tool_and_candidate_mode_mutations_fail_closed(self):
        image_bytes = (OUTPUT / "inputs" / "fixed-Image").read_bytes()
        with tempfile.TemporaryDirectory(prefix="p319-input-hostile-") as directory:
            image = Path(directory) / "fixed-Image"
            image.write_bytes(image_bytes)
            image.chmod(0o600)
            with self.assertRaises(self.bound.AuditError):
                self.bound.stable_bytes(image, "hostile Image mode", 64 * 1024 * 1024, self.bound.IMAGE_IDENTITY, required_mode=0o400, required_nlink=1)
            image.chmod(0o400)
            hardlink = Path(directory) / "fixed-Image.hardlink"
            os.link(image, hardlink)
            with self.assertRaises(self.bound.AuditError):
                self.bound.stable_bytes(image, "hostile Image hardlink", 64 * 1024 * 1024, self.bound.IMAGE_IDENTITY, required_mode=0o400, required_nlink=1)
        with tempfile.TemporaryDirectory(prefix="p319-tool-drift-") as directory:
            fake = Path(directory) / "file"
            fake.write_bytes(b"tool drift")
            fake.chmod(0o700)
            old_path = self.bound.TOOL_PATHS["file"]
            try:
                self.bound.TOOL_PATHS["file"] = fake
                with self.assertRaises(self.bound.AuditError):
                    self.bound._bind_tools()
            finally:
                self.bound.TOOL_PATHS["file"] = old_path
        with tempfile.TemporaryDirectory(prefix="p319-candidate-hostile-") as directory:
            candidate = Path(directory) / "boot.img"
            candidate.write_bytes(b"candidate")
            candidate.chmod(0o600)
            with self.assertRaises(self.bound.AuditError):
                self.bound.stable_bytes(candidate, "hostile candidate mode", 1024, self.bound.identity(b"candidate"), required_mode=0o400, required_nlink=1)

    def test_decoded_image_provider_crc_mutation_is_rejected(self):
        image_path = OUTPUT / "inputs" / "fixed-Image"
        mutated = bytearray(image_path.read_bytes())
        crc_offset = self.result["fixed_image_abi"]["sections"]["__kcrctab"]["image_offset"]
        mutated[crc_offset] ^= 1
        with tempfile.TemporaryDirectory(prefix="p319-image-map-drift-") as directory:
            path = Path(directory) / "Image"
            path.write_bytes(mutated)
            path.chmod(0o400)
            old_image, old_identity = self.bound.IMAGE, self.bound.IMAGE_IDENTITY
            try:
                self.bound.IMAGE = path
                self.bound.IMAGE_IDENTITY = self.bound.identity(bytes(mutated))
                with self.assertRaises(self.bound.AuditError):
                    self.bound.audit_same_magic_and_image()
            finally:
                self.bound.IMAGE, self.bound.IMAGE_IDENTITY = old_image, old_identity

    def test_wrong_run_external_provenance_cannot_bless_or_change_result(self):
        baseline = self.bound.audit_same_magic_and_image()
        with tempfile.TemporaryDirectory(prefix="p319-wrong-run-provenance-") as directory:
            root = Path(directory)
            wrong = {
                "VMLINUX": root / "vmlinux",
                "SYMVERS": root / "vmlinux.symvers",
                "CONFIG": root / ".config",
            }
            for path in wrong.values():
                path.write_bytes(b"wrong run\n")
                path.chmod(0o400)
            old = {name: getattr(self.bound, name, None) for name in wrong}
            try:
                for name, path in wrong.items():
                    setattr(self.bound, name, path)
                self.assertEqual(self.bound.audit_same_magic_and_image(), baseline)
            finally:
                for name, value in old.items():
                    if value is None:
                        delattr(self.bound, name)
                    else:
                        setattr(self.bound, name, value)
        fixed = baseline
        self.assertNotIn("vmlinux", fixed)
        self.assertNotIn("symvers", fixed)
        self.assertEqual(
            set(self.result["inputs"]),
            {
                "child_source", "image", "p311_base_boot", "p318_candidate_patch",
                "p318_static_check_result", "p319_module_materialization_receipt",
                "parser_receipt", "v5_receipt",
            },
        )

    def test_image_ikconfig_duplicate_corrupt_and_trailing_markers_fail_closed(self):
        image_path = OUTPUT / "inputs" / "fixed-Image"
        original_image = image_path.read_bytes()
        marker_start = original_image.find(self.bound.IKCONFIG_ST)
        payload_start = marker_start + len(self.bound.IKCONFIG_ST)
        marker_end = original_image.find(self.bound.IKCONFIG_ED, payload_start)
        self.assertGreater(marker_start, 0)
        self.assertGreater(marker_end, payload_start)
        mutations = []
        corrupt = bytearray(original_image)
        corrupt[payload_start + 32] ^= 1
        mutations.append(bytes(corrupt))
        mutations.append(original_image + self.bound.IKCONFIG_ST)
        trailing = bytearray(original_image)
        trailing[marker_end - 1] ^= 1
        mutations.append(bytes(trailing))
        for index, mutated in enumerate(mutations):
            with self.subTest(index=index), tempfile.TemporaryDirectory(prefix="p319-ikconfig-hostile-") as directory:
                image = Path(directory) / "Image"
                image.write_bytes(mutated)
                image.chmod(0o400)
                old_image, old_identity = self.bound.IMAGE, self.bound.IMAGE_IDENTITY
                try:
                    self.bound.IMAGE = image
                    self.bound.IMAGE_IDENTITY = self.bound.identity(mutated)
                    with self.assertRaises(self.bound.AuditError):
                        self.bound.audit_same_magic_and_image()
                finally:
                    self.bound.IMAGE, self.bound.IMAGE_IDENTITY = old_image, old_identity

    def test_image_vermagic_and_layout_mutations_fail_closed(self):
        original = (OUTPUT / "inputs" / "fixed-Image").read_bytes()
        marker = b" SMP preempt mod_unload modversions aarch64"
        marker_offset = original.find(marker)
        self.assertGreater(marker_offset, 0)
        mutated = bytearray(original)
        mutated[marker_offset + 5] ^= 1
        with tempfile.TemporaryDirectory(prefix="p319-vermagic-hostile-") as directory:
            image = Path(directory) / "Image"
            image.write_bytes(mutated)
            image.chmod(0o400)
            old_image, old_identity = self.bound.IMAGE, self.bound.IMAGE_IDENTITY
            try:
                self.bound.IMAGE = image
                self.bound.IMAGE_IDENTITY = self.bound.identity(bytes(mutated))
                with self.assertRaises(self.bound.AuditError):
                    self.bound.audit_same_magic_and_image()
            finally:
                self.bound.IMAGE, self.bound.IMAGE_IDENTITY = old_image, old_identity
        old_layout = self.bound.IMAGE_SECTION_LAYOUT
        try:
            altered = {name: dict(spec) for name, spec in old_layout.items()}
            altered["__kcrctab"]["image_offset"] += 4
            self.bound.IMAGE_SECTION_LAYOUT = altered
            with self.assertRaises(self.bound.AuditError):
                self.bound.audit_same_magic_and_image()
        finally:
            self.bound.IMAGE_SECTION_LAYOUT = old_layout

    def test_module_snapshot_is_logical_not_absolute_path_bound(self):
        for row in self.result["module_crc_closure"]["modules"]:
            for path in row["source_paths"]:
                self.assertNotIn("/mnt/", path)
                self.assertNotIn("/home/", path)
                self.assertTrue(path.startswith("private-module-snapshot/"))

    def test_report_ledger_and_goal_record_the_new_boundary(self):
        report = (ROOT / "docs/reports/S22PLUS_FYG8_P319_STOCK_WITNESS_RUNTIME_FOLLOWUP_H0_2026-08-21.md").read_text()
        provenance_report = (ROOT / "docs/reports/S22PLUS_FYG8_P319_STOCK_IMAGE_PROVENANCE_REPAIR_H0_2026-08-21.md").read_text()
        ledger = (ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md").read_text()
        goal = (ROOT / "GOAL.md").read_text()
        self.assertIn("Status: **PASS_GO; H0 ONLY; NO LIVE AUTHORITY**", report)
        self.assertIn("Verdict: **PASS_GO_P319_STOCK_WITNESS_RUNTIME_BUILD_INDEPENDENT_REVIEW_H0_CAPABILITY_V1**", report)
        self.assertIn("621623bbf3e48161", report)
        self.assertIn("44f4b412aa904237", report)
        self.assertIn("h0-stock-witness-runtime-16", ledger)
        self.assertIn("P319_STOCK_WITNESS_RUNTIME_IMPLEMENTED_REVIEW_PENDING", ledger)
        self.assertIn("h0-stock-witness-runtime-followup-20", ledger)
        self.assertIn("h0-stock-witness-runtime-review-16", ledger)
        self.assertIn("621623bb", ledger)
        self.assertIn("44f4b412", ledger)
        self.assertIn("stock-witness runtime/build closure", goal)
        self.assertIn("bd94a638`/`231316f0", goal)
        self.assertIn("superseded intermediate receipts", goal)
        self.assertIn("current authority exclusively `-32`/`-33`", goal)
        self.assertIn("Status: **PASS_GO; H0 ONLY; NO LIVE AUTHORITY**", provenance_report)
        self.assertIn("PASS_GO_P319_STOCK_IMAGE_PROVENANCE_REPAIR_H0_CAPABILITY_V1", provenance_report)
        self.assertIn("e721bf2a24", provenance_report)
        self.assertIn("a6e1734bdd527eb5", provenance_report)
        self.assertIn("e491c79722c3ae08", provenance_report)
        self.assertIn("h0-stock-image-provenance-repair-followup-23", ledger)
        self.assertIn("113532", provenance_report)
        self.assertIn("574132854258ac2affd038bc98f9629663c9f1c6aa95cfc8585101c1abe0d29e", provenance_report)
        self.assertIn("f811e202", provenance_report)
        self.assertIn("P319_STOCK_IMAGE_PROVENANCE_REPAIR_BOOKKEEPING_CORRECTION_NO_NEW_OBLIGATION", ledger)
        self.assertIn("focused stock-runtime tests 24/24", ledger)
        self.assertIn("h0-stock-image-provenance-repair-22", ledger)
        self.assertIn("P319_STOCK_IMAGE_PROVENANCE_REPAIR_IMPLEMENTED_REVIEW_PENDING", ledger)
        self.assertIn("a6e1734bdd527eb5", ledger)
        self.assertIn("e491c79722c3ae08", ledger)
        self.assertIn("Image-only IKCONFIG", goal)
        self.assertIn("a6e1734b", goal)
        self.assertIn("current authority exclusively `-32`/`-33`", goal)
        self.assertIn("Image-only IKCONFIG", goal)
        self.assertLessEqual(len(goal.splitlines()), 900)


if __name__ == "__main__":
    unittest.main()
