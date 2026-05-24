# Native Init V769 RKP_CFP Python3 Packaging Plan

## Goal

Turn the V767 ICNSS/QCACLD instrumented-object build into an `Image`-producing
diagnostic kernel build by repairing Samsung `scripts/rkp_cfp` Python2 host
compatibility inside the disposable V766 source tree.

## Scope

- Source scope: `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source`
- Runner: `scripts/revalidation/native_wifi_rkp_cfp_packaging_v769.py`
- Evidence: `tmp/wifi/v769-rkp-cfp-python3-packaging/`
- Mutation scope: ignored disposable source tree only

## Gate Rules

- Allowed: Python3 compatibility repair for `scripts/rkp_cfp/*.py`
- Allowed: `py_compile` of repaired RKP_CFP scripts
- Allowed: bounded host kernel build using the V767 toolchain path
- Blocked: boot image write, flash, reboot, live handoff, device command
- Blocked: service-manager, Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping

## Repair Strategy

1. Replace Python2-only iterator calls (`xrange`, `iteritems`, `.next`) with Python3 equivalents.
2. Replace removed `pipes.quote` usage with `shlex.quote`.
3. Force `subprocess.Popen(..., stdout=PIPE)` call sites used by RKP_CFP parsing to text mode.
4. Force `multiprocessing` start method to `fork` so local instrumentation callbacks do not require pickle serialization under Python 3.14.
5. Compile-check `instrument.py`, `common.py`, and `debug.py`.
6. Rerun the bounded full kernel build and classify final `Image` readiness.

## Success Criteria

- `rkp-cfp-py-compile` returns `rc=0`.
- Kernel build returns `rc=0`.
- `out/arch/arm64/boot/Image` exists.
- ICNSS/QCACLD instrumented objects still exist and preserve all 19 `A90V765` markers.
- Runner manifest proves no boot image write, device command, Wi-Fi action, credential use, DHCP, route, or external ping occurred.

## Next If Pass

Create a separate diagnostic boot-image staging gate that packages the V769
instrumented `Image` with existing boot artifacts, still without flashing until
explicitly gated.
