# Native Init v244 CNSS Identity Probe

- generated: `2026-05-19`
- result: `PASS`
- decision: `cnss-identity-probe-pass`
- reason: harmless child satisfied uid/gid/groups/`CAP_NET_ADMIN` contract inside private Android execution namespace
- device baseline: `A90 Linux init 0.9.59 (v159)`
- boot image change: none
- daemon start: not executed
- evidence: `tmp/wifi/v244-cnss-identity-probe-live4/`

## Implementation

- plan: `docs/plans/NATIVE_INIT_V244_CNSS_IDENTITY_PROBE_PLAN_2026-05-19.md`
- helper: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- host tool: `scripts/revalidation/wifi_cnss_identity_probe.py`
- helper version: `a90_android_execns_probe v8`
- helper SHA-256: `4ce17edfdfe9935da8a320e5a570d301517d518d0ae1dcadaef8bafec7415647`
- remote helper: `/cache/bin/a90_android_execns_probe`

## Validation

- `scripts/revalidation/build_android_execns_probe_helper.sh` — PASS
- `python3 -m py_compile scripts/revalidation/wifi_cnss_identity_probe.py` — PASS
- `git diff --check` — PASS
- `python3 scripts/revalidation/wifi_cnss_identity_probe.py probe --out-dir tmp/wifi/v244-cnss-identity-probe-live4` — PASS

## Live Evidence

| item | value |
| --- | --- |
| v243 contract | `cnss-launcher-contract-ready` |
| output decision | `cnss-identity-probe-pass` |
| helper deploy | PASS |
| helper cmdv1 run | PASS |
| namespace status | `namespace-ready` |
| APEX materialization | `<private-bind-farm>` |
| pre-exec status | `pass` |
| child exit | `0` |
| daemon start | not executed |

## Identity / Capability Result

| field | value |
| --- | --- |
| pre-exec uid/gid | `1000` / `1000` |
| pre-exec groups | `1010,3003,3005` |
| pre-exec `CAP_NET_ADMIN` effective/permitted/inheritable | `1` / `1` / `1` |
| ambient raise | PASS |
| post-exec target | `/system/bin/toybox cat /proc/self/status` |
| post-exec uid/gid | `1000` / `1000` |
| post-exec groups | `1010,3003,3005` |
| post-exec `CapEff` | `0000000000001000` |
| post-exec `CapPrm` | `0000000000001000` |
| post-exec `CapAmb` | `0000000000001000` |

## Important Correction From v241

v241 used a private `/apex` symlink farm to close the VNDK v30/current linker-list gap. v244 showed that a symlink-only APEX farm is not enough for harmless Android dynamic exec because bionic resolves `/apex/com.android.runtime` through `/system/apex/...` and rejects it against namespace permitted paths. The helper now uses a private bind-backed APEX farm, while still providing the `com.android.vndk.v30` alias inside the private namespace.

## Still Blocked

- `cnss-daemon` start-only attempt
- `cnss_diag`
- Wi-Fi scan/connect/link-up/credential/DHCP/routing
- Android property service emulation
- SELinux domain transition equivalence
- `/dev/diag` and `/dev/qrtr` runtime gaps
- global `/system/vendor` and `/vendor` alias outside private helper namespace

## Interpretation

v244 closes the non-starting launcher identity/capability prerequisite. A future start-only runner can now reuse the v244 private namespace and identity setup, but must still be an explicit opt-in experiment with timeout, process-group cleanup, postflight, and reboot-only recovery policy.
