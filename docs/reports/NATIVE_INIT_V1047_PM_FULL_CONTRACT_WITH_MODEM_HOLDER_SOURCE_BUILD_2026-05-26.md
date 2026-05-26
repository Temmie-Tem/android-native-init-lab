# V1047 PM Full Contract with Modem Holder — Source/Build-Only

- date: `2026-05-26`
- scope: Source/build-only — add modem pre-holder before `pm_proxy_helper` in helper
- decision: `v1047-pm-full-contract-with-modem-holder-source-build-pass`
- pass: `True`
- evidence: binary at `/tmp/a90_android_execns_probe_v178_test`

## Summary

V1047 implements the subsys_modem holder prerequisite identified by V1046. The Android
init contract shows `vendor.per_proxy_helper` opens `/dev/subsys_modem` at `post-fs-data`,
by which point `pm-service` (class core, auto-start) has already opened `/dev/subsys_modem`
(refcount ≥ 1). Native context had no such pre-holder, so `pm_proxy_helper` was the first
opener (refcount 0 → 1, triggering PIL boot) — likely causing the D-state block seen in
V867.

V1047 adds a modem pre-holder child that opens `/dev/subsys_modem` BEFORE `pm_proxy_helper`
starts. With refcount already ≥ 1, `pm_proxy_helper` opens it as a second holder without
triggering PIL boot.

## Helper Changes (v177 → v178)

New service-manager-order value:
```
after-mdm-helper-esoc-fd-with-pm-full-contract-with-modem-holder
```

New allow flag:
```
--allow-pm-full-contract-with-modem-holder
```

New run_order (modem-pre-holder first):
```
property-shim,modem-pre-holder,pm_proxy_helper,per_mgr_light,pm_proxy,mdm_helper,
pm-full-contract-fd-gate,esoc0-fd-gate,servicemanager,hwservicemanager,vndservicemanager,
cnss_diag,cnss_daemon,wlfw-precondition-gate,subsys_esoc0-open-child
```

### Modem Pre-Holder Sequence

1. `pipe2()` + `fork()` before `pm_proxy_helper` spawn
2. Child: `open("/dev/subsys_modem", ...)` → PIL boot completes → writes
   `modem_pre_holder_opened=1` to pipe → `close(pipe_wr)` → `pause()` loop (holds fd)
3. Parent: drains pipe (up to 90 s timeout for PIL boot), reads
   `modem_pre_holder_opened=1`, confirms child still alive via `WNOHANG waitpid`
4. `pm_proxy_helper` starts with modem refcount ≥ 1 — no new PIL boot
5. Holder killed at `composite_cleanup_children` time (after all composite children)

### Evidence Fields Added

| field | meaning |
| --- | --- |
| `modem_pre_holder_start_attempted` | 1 if holder fork attempted |
| `modem_pre_holder_pid` | holder child PID |
| `modem_pre_holder_opened` | 1 if child opened `/dev/subsys_modem` and is holding |
| `modem_pre_holder_confirmed` | same (final summary value) |
| `pm_full_contract_with_modem_holder_matrix` | 1 for the new order value |

### pm_full_contract_matrix Semantics

`pm_full_contract_matrix` is now `true` for both:
- `after-mdm-helper-esoc-fd-with-pm-full-contract` (original)
- `after-mdm-helper-esoc-fd-with-pm-full-contract-with-modem-holder` (new)

All existing gate/poll/postflight logic (`pm_full_contract_seen`,
`pm-full-contract-fd-gate`, `pm_full_contract_poll`) applies to both.

## Build Artifact

```
binary: /tmp/a90_android_execns_probe_v178_test  (deploy target: /cache/bin/a90_android_execns_probe)
sha256: 7df75c618f58d599ece1a6017f66040aff57badb8955a70e07de2a77a3561c75
size:   1336728 bytes
arch:   ELF 64-bit LSB executable, ARM aarch64, statically linked
```

Verified:
```bash
file /tmp/a90_android_execns_probe_v178_test  # static, aarch64
aarch64-linux-gnu-readelf -d ...              # no dynamic section
strings ...  | grep v178                      # a90_android_execns_probe v178 present
```

## Validation

```bash
python3 -m py_compile scripts/revalidation/android_vendor_init_rc_handoff_v1046.py  # existing
aarch64-linux-gnu-gcc -static -Os -Wall -Wextra \
  -o /tmp/a90_android_execns_probe_v178_test \
  stage3/linux_init/helpers/a90_android_execns_probe.c
```

## Guardrails

No device contact, deploy, live actor start, subsystem open, Wi-Fi HAL, scan/connect,
DHCP/routes, credentials, external ping, sysfs write, GPIO write, or boot image write
occurred in V1047 (source/build-only).

## Next

V1048 should deploy helper v178 and run a preflight (no live allow flags) to verify:
- Remote sha256 matches
- `--version` / default check-only shows `a90_android_execns_probe v178`
- New mode token visible in usage output
- Selftest fail=0, actor-clean, Wi-Fi-link-clean

V1049 should run the bounded live gate with:
```
--mode wifi-companion-mdm-helper-cnss-service-manager-matrix
--service-manager-order after-mdm-helper-esoc-fd-with-pm-full-contract-with-modem-holder
--allow-pm-full-contract-with-modem-holder
--assume-yes
```

Gate: `modem_pre_holder_confirmed=1` AND `pm_full_contract_seen=1` (both
`pm_proxy_helper` and `per_mgr` hold `/dev/subsys_modem`) without PIL boot block.

Do not widen to `ks`, MHI pipe, Wi-Fi HAL, scan/connect, DHCP/routes, credentials,
external ping, or boot image writes in V1048/V1049.
