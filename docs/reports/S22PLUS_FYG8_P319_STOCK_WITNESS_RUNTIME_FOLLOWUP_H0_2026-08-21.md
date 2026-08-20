# S22+ FYG8 P3.19 stock-witness runtime follow-up H0

Status: **PASS_GO; H0 ONLY; NO LIVE AUTHORITY**
Verdict: **PASS_GO_P319_STOCK_WITNESS_RUNTIME_BUILD_INDEPENDENT_REVIEW_H0_CAPABILITY_V1**

This follow-up records the independent changed-closure PASS_GO for the stock-
witness runtime/build unit. It supersedes neither the `-06`/`-07` nor
`-08`/`-09` receipts and adds no device, ADB, USB, Odin, transfer, recovery,
replay, or live action.
The final no-clobber outputs are `-24` (Phase 1) and `-25` (Phase 2). The
earlier `-10`/`-11` through `-23` outputs remain preserved as superseded
evidence; no prior receipt was overwritten.

## Review repairs

The auditor now uses the predecessor bootstrap contract: a fresh module is
executed with the exact current auditor bytes injected, and build/audit calls
are rejected when `_BOUND_AUDITOR_SOURCE` is absent, non-bytes, or differs
from a stable reread. An old-code/current-AUDITOR substitution is a hostile
failure. `--audit-only` reopens every output child and compares exact bytes,
mode `0400`, and link count one; directories are mode `0700` with exact child
sets. The V5 receipt `05ee3385...` and all twelve materialized-source
identities are strict inputs, so source comments and receipt fields cannot
drift.

The P290 checkpoint transform adds only the exact stock terminal range
`0x6724..0x6726` to both `p288_detail_allowed` and
`s22_max77705_detail_allowed`. The bound P318 patch is
`42020` bytes / `d839850e...`; an executed C fixture accepts the range and
rejects `0x6723`, `0x6727`, and the adjacent ordinal. Form-2
`muic_lookup_vps_table` and the deferred seven-register line remain valid
auxiliary grammar: they set counts/masks and are encoded at payload bytes 59
and 60, but never become primary chain stages. Only parent `0x23`/W5 and a
five-byte initial claim are contradictions.

Module identity is derived from the exact P318 static result
(`554578` / `2a4d639b...`) and P319 materialization receipt
(`10658` / `8b8c1f5a...`). The snapshot has exactly 73 direct children, each
mode `0400`, link count one; every row's name, index, runtime name, size, and
SHA-256 is checked. Imports/exports are always read from that snapshot, not
from a second vendor tree. Decoded Image PREL32 names and parallel Image CRC
tables produce 7,222 providers and must exactly equal P310 symvers; the module
load closure is 3,566/3,566 (3,238 fixed-Image and 328 earlier-module), with
zero missing, ambiguous, or duplicate providers. A CRC mutation in either
authority fails closed.

Phase 2 no longer imports the mutable P286/P318 builders. It binds the exact
compiler flags and environment scrub, fixed tool identities, fixed
`magiskboot`/LZ4, and a local deterministic USTAR+MD5 AP writer. The package
starts from clean P311 `boot.img`
(`100663296` bytes / `58b38211...`), replaces `init` and the child, and adds
only the four delta modules: latch, `spu_verify`, `mfd_max77705`, and
`pdic_max77705`. The inherited 69 modules are not copied into generic ramdisk.
The child source is separately preserved and reopened as `1112` bytes /
`2af86dda...` mode `0400`, link count one.
The P318 packaging script is retained only as a reviewed lineage input; it is
not imported or executed by this successor auditor.

## Exact 73-row module plan

```text
00 s22plus_dwc3_event_latch.ko  01 qcom_hwspinlock.ko  02 smem.ko
03 minidump.ko  04 qcom-scm.ko  05 qcom_wdt_core.ko  06 gh_virt_wdt.ko
07 cmd-db.ko  08 debug-regulator.ko  09 icc-debug.ko  10 iommu-logger.ko
11 phy-generic.ko  12 proxy-consumer.ko  13 gdsc-regulator.ko
14 clk-qcom.ko  15 clk-dummy.ko  16 gcc-waipio.ko  17 qcom_iommu_util.ko
18 qnoc-qos.ko  19 sec_class.ko  20 abc.ko  21 sec_debug.ko
22 secure_buffer.ko  23 qcom_ipc_logging.ko  24 qcom-pdc.ko
25 pinctrl-msm.ko  26 pinctrl-waipio.ko  27 qcom_rpmh.ko  28 clk-rpmh.ko
29 rpmh-regulator.ko  30 icc-bcm-voter.ko  31 qrtr.ko  32 socinfo.ko
33 icc-rpmh.ko  34 dispcc-waipio.ko  35 qnoc-waipio.ko  36 arm_smmu.ko
37 qmi_helpers.ko  38 eud.ko  39 phy-msm-ssusb-qmp.ko  40 repeater.ko
41 redriver.ko  42 usb_notify_layer.ko  43 qcom_glink.ko
44 qcom_glink_smem.ko  45 qcom_smd.ko  46 rproc_qcom_common.ko
47 pdr_interface.ko  48 pmic_glink.ko  49 switch_class.ko
50 common_muic.ko  51 vbus_notifier.ko  52 if_cb_manager.ko
53 pdic_notifier_module.ko  54 usb_typec_manager.ko
55 usb_f_ss_mon_gadget.ko  56 phy-msm-snps-hs.ko  57 phy-msm-snps-eusb2.ko
58 qc_usb_audio.ko  59 dwc3-msm.ko  60 usb_notifier_qcom.ko
61 ucsi_glink.ko  62 spmi-pmic-arb.ko  63 pinctrl-spmi-gpio.ko
64 qti-regmap-debugfs.ko  65 regmap-spmi.ko  66 qcom-spmi-pmic.ko
67 msm-geni-se.ko  68 gpi.ko  69 i2c-msm-geni.ko  70 spu_verify.ko
71 mfd_max77705.ko  72 pdic_max77705.ko
```

The row-38 EUD identity is derived from the exact plan, not a stale literal.

## Receipts and validation

The final Phase-1 receipt is
`workspace/private/outputs/s22plus_fyg8_p319/stock-witness-runtime-v1-20260821-24/result.json`,
`380738` bytes, SHA-256
`621623bbf3e481619a22041c99f476f423b3e65d9435f0e44f15e9a618cd1af3`.
The final Phase-2 receipt is the corresponding `-25/result.json`, `391575`
bytes, SHA-256
`44f4b412aa904237c1eb569a9b33f8aecc6b452931bf7699ea832e93bcf4d4f2`.
Both are mode `0400`, link count one; the bound successor auditor is
`108025` bytes, SHA-256 `c482bf6b38f226145750365bccd99ce3286de69dc0299c527cde1ec5b98329b3`.
Both receipts regenerate byte-identically through `--audit-only` without
writing the existing output.

The focused stock-runtime suite is **21/21** after adding the checkpoint,
auxiliary-count, self-bind, V5-source, and hostile-input tests. The relevant
predecessor closure is **94/94**, exactly these four modules:

| test module | tests |
|---|---:|
| `test_s22plus_fyg8_p319_candidate_witness_parser_v2.py` | 25 |
| `test_s22plus_fyg8_p319_candidate_witness_carrier_v5.py` | 35 |
| `test_s22plus_fyg8_p319_successor_module_plan_v2.py` | 15 |
| `test_s22plus_fyg8_p319_successor_module_materialization.py` | 19 |

The full append-only ledger tail now audits to **41 total / 27 resolved /
14 unresolved** obligations. The exact resolution is
`h0-stock-witness-runtime-review-16`; other unresolved topics are unchanged.
The PASS_GO row creates no device authority.

`py_compile` and `git diff --check` are required before commit. The prior
`-06`/`-07`, `-08`/`-09`, `-20`/`-21`, `-22`/`-23`, and intermediate outputs remain
append-only superseded evidence; none was overwritten.

## Boundary

This follow-up is independently reviewed PASS_GO under the resolved
`stock-witness-runtime` obligation. It creates no D0, D1, F1, recovery,
replay, or live authority; fresh candidate intent, qualification, and attended
approval remain separate requirements.
