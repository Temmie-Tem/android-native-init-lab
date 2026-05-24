# Native Init V767 ICNSS/QCACLD Full Build Gate Plan

- date: `2026-05-25 KST`
- scope: host-only disposable full-kernel build gate for the V765 instrumentation patch
- runner: `scripts/revalidation/native_wifi_icnss_qcacld_full_build_v767.py`

## Goal

Prove whether the V765 `A90V765` ICNSS/QCACLD instrumentation patch survives
real kernel compilation after V766 source-apply and defconfig readiness. Keep
boot image packaging, flashing, and live device validation as separate gates.

## Inputs

- V760/V762: official Samsung OSRC source target files are staged and verified.
- V763: SM-A908N path is ICNSS/QCACLD SNOC, not CNSS2/MHI.
- V764: service180-gated `mdm_helper` can start but does not advance mdm3/WLFW.
- V765: review-only `A90V765` patch artifact generated.
- V766: patch applies cleanly and `r3q_kor_single_defconfig` passes.

## Contract

- use only ignored local `toolchains/` and `tmp/wifi/` material;
- mutate only the disposable V766 source tree under `tmp/wifi/`;
- stage Android/Samsung-compatible clang/GCC/make/OpenSSL prerequisites;
- apply minimal host-build compatibility repairs only inside the disposable tree;
- run a bounded full kernel build and capture first build blocker;
- record whether all ICNSS/QCACLD instrumented objects build and retain markers.

## Forbidden

- no mutation of tracked kernel source or `kernel_build/`;
- no boot image write, partition write, flash, or reboot;
- no device command;
- no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping;
- no claim that instrumentation solves missing WLFW service `69`.

## Success Criteria

- Toolchain prerequisites are classified.
- Full build either produces an `Image` or fails with a classified first blocker.
- If final image generation fails after Wi-Fi objects compile, all five
  instrumented target objects must exist and contain all 19 `A90V765` markers.
- The result must preserve the parallel root-cause branch:
  mdm3/esoc/`mdm_helper` classification remains separate from HDD/PLD logging.
