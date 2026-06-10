# V2189 Fresh Local Security Rescan

Date: 2026-06-10
Baseline: `A90 Linux init 0.9.261 (v2189-security-p0-stage-fix)`
Git HEAD: `eeb11b10`
Scope: active workspace native-init source, active revalidation host tools, third-party boot tooling used by the current builder, V2189 security P0 guardrails, and accepted trusted-lab root-control boundaries.

This is a local targeted rescan, not a Codex Cloud scanner replacement.

## Summary

- PASS: 10
- WARN: 1
- FAIL: 0
- New implementation blocker from this local scan: `0`

## Results

| id | status | check | evidence | note |
|---|---|---|---|---|
| S001 | PASS | native root-control listeners stay bound to the USB-local device address | `a90_config.h` binds tcpctl/rshell to `NETSERVICE_DEVICE_IP`; active native listener files have no broad bind literal. | Keeps F001/F003/F005/F030-style root-control exposure below USB-local NCM. |
| S002 | PASS | netservice-started tcpctl requires token authentication | `a90_tcpctl.c` gates privileged `run` behind auth; `a90_netservice.c` writes a private no-follow token and starts tcpctl with `auth=required`. | Covers the historical unauthenticated tcpctl finding family for the active path. |
| S003 | PASS | host serial bridge wrapper is localhost-default and pins Samsung ACM identity | `a90_bridge.py` and `serial_tcp_bridge.py` default to localhost and require/pin the Samsung serial identity unless explicitly overridden. | F021/F030 remain accepted trusted-lab boundaries; this check prevents accidental LAN exposure as the default. |
| S004 | PASS | flash handoff requires a caller-pinned image hash and verifies readback | `native_init_flash.py` refuses unpinned images, seals a no-follow local copy, rejects group/world-writable boot images, checks boot-block readback, and the active Wi-Fi runner pins the V2189 SHA. | Closes the pre-promotion flash identity P0 for `v2189-security-p0-stage-fix`. |
| S005 | PASS | Wi-Fi runtime dirs and supplicant config have root-owned/private modes | `a90_wificfg.c` keeps `/cache/a90-wifi` root-owned, exposes only the control socket dir to UID/GID 1010, and writes supplicant config by no-follow temp+rename with `0600`. | Prevents the stale staged config/runtime ownership class from becoming a promoted baseline property. |
| S006 | PASS | Wi-Fi root-executed artifacts are verified before exec | `a90_wifi.c` verifies parent dirs and executable files with no-follow open, regular-file/root-owner/not group-or-world writable checks, and reports `supplicant.root_exec_*`. | Closes the staged standalone supplicant root-exec P0 exposed by V2188 and fixed in V2189. |
| S007 | PASS | host Wi-Fi profile staging hardens cache artifacts and redacts secrets | `a90_wifi_profile_stage.py` and the active connect runner re-own standalone Wi-Fi artifacts as root, remove group/other write bits, and fail/flag evidence if secrets leak. | Keeps profile staging compatible with the V2189 device-side root-exec checks. |
| S008 | PASS | boot-image archive extraction keeps path traversal checks | `certify_bootimg.py` still validates archive members and avoids plain `shutil.unpack_archive`. | Preserves the previous host archive-extraction mitigation in the current third-party workspace path. |
| S009 | PASS | exposure guardrails remain wired and token values stay hidden | `a90_exposure.*` labels F021/F030 as accepted boundaries and diagnostics hide token values. | Makes the accepted local root-control boundary machine-visible instead of implicit. |
| S010 | PASS | dead Wi-Fi test-boot scaffolding is not compiled by active builders | Active `build_native_init_boot_v*.py` files do not define `-DA90_WIFI_TEST_BOOT`; the large research block in `v724/90_main.inc.c` remains source debt, not current binary behavior. | Architecture cleanup remains important, but this specific block is not a V2189 promotion security blocker. |
| S011 | WARN | accepted local root-control channels remain intentionally present | USB ACM root shell, localhost serial bridge, and USB-local NCM tcpctl are still intentional lab rescue/control channels. | Do not expose bridge/tcpctl/rshell on LAN or Wi-Fi without a new authentication and threat model. |

## Interpretation

The local targeted scan found no new implementation blocker in the active V2189 promotion path. The remaining warning is the intentional trusted-lab local root-control boundary.

Promotion remains conditioned on the separate live validation evidence and the architecture-debt disposition.

## Reproduction

```bash
python3 workspace/public/src/scripts/revalidation/local_security_rescan.py \
  --baseline 'A90 Linux init 0.9.261 (v2189-security-p0-stage-fix)' \
  --out docs/security/scans/SECURITY_FRESH_SCAN_V2189_2026-06-10.md
git diff --check
```
