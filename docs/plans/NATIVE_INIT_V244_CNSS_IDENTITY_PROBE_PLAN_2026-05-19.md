# Native Init v244 CNSS Identity Probe Plan

- target: non-starting CNSS launcher identity/capability probe
- baseline: v243 launcher contract PASS
- implementation: extend `a90_android_execns_probe` with `identity-probe`
- daemon start: still blocked
- output: `tmp/wifi/v244-cnss-identity-probe/`

## Goal

v243 defined the native launcher contract for a future bounded
`cnss-daemon` start-only attempt:

- uid/gid: `system=1000`
- supplemental groups: `inet=3003`, `net_admin=3005`, `wifi=1010`
- capability: `CAP_NET_ADMIN`
- namespace: same private Android execution namespace that passed v241

v244 proves this contract on a harmless child inside that namespace. It must
not execute `cnss-daemon`.

## Implementation

- Bump `a90_android_execns_probe` to `v8`.
- Add `--mode identity-probe`.
- Reuse v241 namespace setup:
  - private `/dev/null`
  - real linkerconfig copy
  - private bind-backed APEX farm with VNDK v30/current alias
  - private read-only vendor mount
- Fork a harmless child that:
  - chroots into the private namespace
  - sets supplemental groups
  - preserves capabilities across UID transition
  - drops to uid/gid `1000`
  - restricts capability set to `CAP_NET_ADMIN`
  - attempts ambient `CAP_NET_ADMIN` raise
  - prints uid/gid/groups/capability state
  - execs only `/system/bin/toybox cat /proc/self/status`
  - verifies post-exec uid/gid/groups and ambient/effective/permitted
    `CAP_NET_ADMIN` from `/proc/self/status`
- Fix the v241 symlink-only APEX alias limitation for dynamic exec:
  - linker-list tolerated the symlink farm
  - harmless `/system/bin/toybox` exec requires bind-backed `/apex` entries so
    bionic namespace realpath checks stay inside permitted `/apex/...` paths
- Add `scripts/revalidation/wifi_cnss_identity_probe.py` to build, deploy,
  execute, parse, and report the probe.

## Guardrails

- No `cnss-daemon` execution.
- No `cnss_diag` execution.
- No Wi-Fi scan/connect/link-up.
- No rfkill write.
- No ICNSS bind/unbind.
- No persistent Android partition write.

## Validation

```bash
scripts/revalidation/build_android_execns_probe_helper.sh
python3 -m py_compile scripts/revalidation/wifi_cnss_identity_probe.py
git diff --check
python3 scripts/revalidation/wifi_cnss_identity_probe.py probe
```

Expected decision:

- `cnss-identity-probe-pass`

If the probe fails, the next step is fixing launcher identity/capability handling,
not starting `cnss-daemon`.
