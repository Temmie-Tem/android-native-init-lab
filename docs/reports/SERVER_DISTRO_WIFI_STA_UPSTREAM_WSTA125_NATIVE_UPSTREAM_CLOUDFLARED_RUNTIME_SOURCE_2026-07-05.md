# WSTA125 Native Upstream + Cloudflared Runtime Source Gate

Date: 2026-07-05 05:56 KST

## Scope

WSTA124 proved the cloudflared runtime gate itself is bounded and cleanup-safe,
but the final live run stopped before packet-filter/runtime because the current
network state had no usable upstream egress route.  WSTA125 adds the missing
integration surface: hold the native-owned STA uplink service live while running
the WSTA124 runtime proof in the same chroot/Dropbear session.

This was a source/unit validation pass only.  No boot image was built or flashed,
no native reboot was executed, no Wi-Fi association was attempted, and no public
tunnel was opened by this WSTA125 run.

## Added

- `workspace/public/src/scripts/server-distro/run_wsta125_native_upstream_cloudflared_runtime.py`
  - default inert runner;
  - explicit gates for credentialed Wi-Fi, cloudflared runtime, public exposure,
    private URL artifact, cleanup, optional WSTA28 native reboot precondition,
    and the native uplink confirm token;
  - optional WSTA28 scan/materialization precondition;
  - SD work-image restore, chroot mount, temporary key-only Dropbear, service
    hardening assets, D-public helpers, and native uplink helper staging;
  - native `wifi uplink-service start` + confirmed autoconnect while the
    WSTA124 cloudflared runtime proof executes;
  - WSTA124 resolver sync, redacted egress-route preflight, packet-filter apply,
    runtime probe, private URL artifact capture, syscall trace capture, and
    cleanup reused in one held session;
  - cleanup for runtime, packet filter, uplink service, helper/profile staging,
    chroot, Wi-Fi state, and final selftest.

- `tests/test_server_distro_wsta125_native_upstream_cloudflared_runtime.py`
  - inert default safety;
  - explicit gate sequencing;
  - source safety and WSTA124 reuse assertions;
  - public-summary redaction checks;
  - mocked live path proving native uplink is started/confirmed and blocks
    before packet-filter/runtime when egress preflight fails;
  - print-template no-live behavior.

## Safety

WSTA125 preserves the existing boundaries:

- boot flash: no;
- userdata touch: no;
- switch-root: no;
- native reboot: only if `--run-wsta28-precondition` and `--allow-native-reboot`
  are both supplied;
- Wi-Fi connect/DHCP: only after explicit credentialed Wi-Fi gate and native
  confirm token;
- public tunnel: only after explicit cloudflared runtime/public exposure/private
  URL/cleanup gates;
- public URL values: private artifact only, not printed in JSON;
- resolver values and resolver targets: redacted in public summary.

## Validation

Commands run:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta125_native_upstream_cloudflared_runtime.py \
  tests/test_server_distro_wsta125_native_upstream_cloudflared_runtime.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  tests/test_server_distro_wsta125_native_upstream_cloudflared_runtime.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest discover \
  -s tests -p 'test_server_distro_wsta*.py'
```

Results:

- WSTA125 focused tests: `6 tests OK`;
- full server-distro WSTA regression: `409 tests OK`;
- default inert smoke returned
  `wsta125-blocked-native-upstream-runtime-live-required`, with all device/public
  action safety fields false.

The full WSTA regression still prints the existing expected WSTA94 runner-error
fixture JSON during tests.

## Next

Run WSTA125 live with the WSTA28 precondition and native-uplink profile enabled,
using the same explicit gates as the proven WSTA43/WSTA45 path plus the WSTA124
runtime gates.  If WSTA125 passes, fold its private runtime proof into
WSTA108/WSTA90 operator status and retire the WSTA124 `egress-route` blocker.
