# S22+ FYG8 Lane W Static Readiness Cross-Check

Date: 2026-07-12 KST  
Target: `SM-S906N/g0q/S906NKSS7FYG8`  
Scope: host-only read-only cross-check; no candidate source, payload, or image

## Verdict

`GO_STOCK_MODULE_PAYLOAD_REVIEW_ONLY_R1_REBUILT_BYTES_NOT_SUBSTITUTABLE`

The 15-module Lane W order is complete against the exact shipped vendor-ramdisk
inventory and topologically valid for every selected `modules.dep` hard edge.
All 15 stock module files rehash to their inventory pins. The FYG8 source still
contains the required parser, writer, nvmem, Recovery control, asynchronous
registration, and debugfs readiness mechanisms.

This closes the scheduled static readiness cross-check only. It does not open
candidate implementation, packaging, or live work.

## Exact Stock Payload

| Order | Module | Stock bytes | Stock SHA256 |
|---:|---|---:|---|
| 1 | `smem.ko` | 28,704 | `27a80d5598329d6a526384d09806de63983204988748ea4e7d3fccfafc24a524` |
| 2 | `minidump.ko` | 37,312 | `e5e6f4dfe1ddac2cd4f8d15c11a50d4d32b6e9de278fedbed44747630a5c554d` |
| 3 | `qcom-scm.ko` | 218,384 | `e12ba8661808c2c47acf42c9939157e509fcdb5b98f6e650f79b92dba18a1af3` |
| 4 | `qcom_wdt_core.ko` | 48,640 | `ef484fb4f1f17586ff63852e0ea9579d07f275f7966ad117d20039055c2d7599` |
| 5 | `gh_virt_wdt.ko` | 18,944 | `f030c5486a41b1fbe4b0ea3aa85a401dd16daa1f1a551a626f6ea424ee90dd39` |
| 6 | `regmap-spmi.ko` | 17,264 | `d5e078a80ebdfb515b04fa677268f72e4d29cf0fd2dfb391c8d0d98d851b03b1` |
| 7 | `qti-regmap-debugfs.ko` | 30,360 | `86fde3cb4c527e5c97e16235563451a5fe2951e21d7cd2a1bbc3a2b696d0f2f5` |
| 8 | `spmi-pmic-arb.ko` | 76,168 | `8ac8226d33ffa8806aa8a1c633293bcff5b83a492fbe3b05c58b1253119d36e0` |
| 9 | `qcom-spmi-pmic.ko` | 20,672 | `6218c5a217548fdd60c79449a0417753552f2ab1e8967514ecb6fc547aa4eecf` |
| 10 | `nvmem_qcom-spmi-sdam.ko` | 15,352 | `211a627ab5768382b2eb32ccb4ee51356969b83bbe9357b323dca0b917e5a156` |
| 11 | `qcom-dload-mode.ko` | 28,360 | `20b209f284202bac177017bc7b46b9730c7d0f063666adb277667b5340163be8` |
| 12 | `sec_reboot_cmd.ko` | 35,368 | `560b05535402808d0921725021c4da2124443b0ada729a49c24abea2a1b76f95` |
| 13 | `sec_qc_rbcmd.ko` | 43,840 | `2e549ffe439378732c1a69e0f118a043c1e335908f163fa246e94715eb0ddbcd` |
| 14 | `sec_qc_qcom_reboot_reason.ko` | 28,640 | `873bcd3141e296c68a2f4d1d2a1930509dd408878e5b495ac007a67316e91f30` |
| 15 | `qcom-reboot-reason.ko` | 13,928 | `503af4c6f89da53760632c45e132b97bcf2d59659ffbef6841405513dfee70d9` |

Source of truth:
`docs/module-map/s22plus-fyg8/inventory.tsv` plus the exact extracted
vendor-ramdisk `/lib/modules` corpus. Every row remains `STATIC_VERIFIED` and
has the FYG8 `-gki-30958166-abS906NKSS7FYG8` vermagic.

## Dependency Order

The selected hard edges are:

```text
minidump -> smem
qcom_wdt_core -> qcom-scm, minidump, smem
gh_virt_wdt -> qcom_wdt_core, qcom-scm, minidump, smem
qcom-spmi-pmic -> regmap-spmi, qti-regmap-debugfs
qcom-dload-mode -> qcom-scm, minidump, smem
sec_qc_rbcmd -> sec_reboot_cmd
sec_qc_qcom_reboot_reason -> sec_qc_rbcmd, sec_reboot_cmd,
  qcom-dload-mode, qcom-scm, minidump, smem
```

All dependency targets precede their consumers. There are zero selected-edge
topology violations. The SDAM/SPMI relation remains a runtime device/provider
edge rather than a `modules.dep` symbol edge, so phase barriers remain required.

## Source Revalidation

| Source | SHA256 | Revalidated fact |
|---|---|---|
| `sec_qc_rbcmd_command.c` | `f866acb097c45c05ee6b8033cdb54669bebc6f95ca49d516df53c93d641b7bee` | strict `download`; predefined `recovery` |
| `sec_qc_qcom_reboot_reason.c` | `04fa225fb3850a5d104d17a27a3f323102e5f3886fe11a4964670857489d5712` | obtains `restart_reason`; write/read-verify path |
| `qcom-reboot-reason.c` | `e27584d3be139592a3e7a1d656cff42c8bc7841fe1e1cd717cf9ee0bd50ae69c` | `recovery -> 0x01`; notifier priority 255 |
| `qcom-spmi-pmic.c` | `e4eb9413ebab813dc025b990322227ac73d6364fa1998be7a2f2b22fa57e015e` | `devm_of_platform_populate()` creates child devices |
| `builder_pattern.h` | `ab41baf2348effa3df14897d700ad743464554ef7c478daa2470e7e864ba4633` | asynchronous `kthread_run()` registration path |
| `sec_reboot_cmd.c` | `2b2a18fe93569d59ae47b12348fb3faad0e1557985ed05dda95b9b06e2f7b010` | debugfs registered-command list and Reboot Notifier priority output |
| `waipio_GKI.config` | `6c868b7a344da8dba0100ab290ae99407769cb0d72ea6f9e725a871f4213d320` | `CONFIG_NVMEM_SPMI_SDAM=m` |

The GKI boot IKCONFIG says `CONFIG_NVMEM_SPMI_SDAM` is unset because the SDAM
driver belongs to the separate vendor-module configuration. The shipped module,
vendor config, and generated msm-kernel config consistently establish the
modular provider. Treating the GKI IKCONFIG alone as the vendor-module config
would be an incorrect negative.

## R1 Output Cross-Check

The historical R1 v2 result contains every one of the 15 module names. For each
name it also records exactly one stripped staging artifact with the same byte
size as the shipped module:

```text
name_present=15/15
stripped_size_match=15/15
stripped_sha256_match_stock=0/15
```

The byte mismatch is not attributed in this host-only unit because the actual
R1 module bytes remain remote-only. Possible build metadata, signing, or strip
differences are hypotheses, not findings. The prior R2 v1 CRC closure proves
symbol-version compatibility, not byte identity, and R2 itself is currently
reopened on the independent kernel-banner defect.

Consequences:

1. A future Lane W payload must copy the exact stock modules listed above from
   the pinned vendor-ramdisk corpus.
2. It must not silently substitute same-name R1 rebuilt modules.
3. If a later design intentionally tests rebuilt modules, that is a different
   payload identity and requires a separate static and live policy.

## Remaining Gates

- R1 v3/R2 v2 re-close is still required for Lane K and R3.
- Lane W implementation remains unopened. No shared init, mode file, module
  payload, ramdisk, boot image, or AP was produced here.
- The future implementation must preserve the exact stock module hashes,
  provider barriers, canonical `of_node` checks, bounded debugfs oracle, and
  W0 -> W1 -> W2 stop-on-failure order from the design report.
- Every candidate and live rung still needs a fresh narrow SHA-pinned policy
  and explicit attended approval.

