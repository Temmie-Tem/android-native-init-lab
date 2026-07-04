# WSTA85 Clean Image Cache Live Measurement Blocked

- Date: 2026-07-04
- Scope: bounded WSTA80 -> WSTA58 live measurement after WSTA84 clean-image cache
- Resident: `A90 Linux init 0.11.153 (v3397-wsta-execute-gate-screen)`
- Private run: `workspace/private/runs/server-distro/wsta85-clean-image-cache-live-20260704T122724Z/`
- Decision: `wsta80-blocked-wsta58-delegation`

## Summary

WSTA85 attempted the WSTA84 follow-up measurement: create a fresh default-off
operator packet/status tree, pass the WSTA80 execute gate, then delegate to
WSTA58 so the two WSTA55 legs could prove whether WSTA42 now restores the
working rootfs from the clean image instead of re-uploading it from the host.

The WSTA80 preflight passed, but the live delegation stopped before any WSTA42
rootfs image preparation ran:

```text
wsta80: wsta80-blocked-wsta58-delegation
wsta58: wsta58-blocked-initial-wsta55
initial WSTA55: wsta55-blocked-wsta45-publish
renewal WSTA55: wsta55-blocked-wsta45-publish
both WSTA43 runs: wsta43-blocked-reboot-materialization
both WSTA28 runs: wsta28-blocked-post-reboot-public-off-cleanup
```

There is no `wsta42_result.json` in the WSTA85 run tree.  Therefore WSTA85
does not prove or disprove the WSTA84 clean-image cache behavior.

## Root Cause

Both WSTA28 runs rebooted and reached healthy native-init, then blocked inside
the post-reboot public-off cleanup gate before WSTA27 materialization could
run.

The final `wifi status` state was public-off in both legs:

```text
autoconnect.decision=wifi-autoconnect-disabled
supplicant.process_count=0
secret_values_logged=0
wlan0_present=0
```

However, the WSTA28 gate required the individual cleanup command summaries to
include parsed `decision=` values.  In the initial leg, `wifi autoconnect
disable` and `wifi cleanup` returned `status=ok rc=0` but sparse parsed
decisions.  In the renewal leg, the noncritical `hide` command had a transport
summary miss while the final public-off state was still clean.  The gate was
therefore stricter than the safety property it was supposed to enforce.

## Post-Run Health

After the blocked run, the resident remained healthy:

```text
version: 0.11.153 build=v3397-wsta-execute-gate-screen
status: BOOT OK shell 6.2s
selftest: pass=12 warn=1 fail=0
transport: serial/ncm/tcpctl ready
storage: sd mounted rw
autohud: running
```

A manual cleanup/status check after the failure also reported:

```text
wifi autoconnect disable -> decision=wifi-autoconnect-disabled
wifi cleanup -> decision=wifi-cleanup-done
wifi status -> autoconnect disabled, supplicant count 0, secret_values_logged 0
```

## Safety

- No boot image was built or flashed for WSTA85.
- No forbidden partition was touched.
- No userdata format/populate or switch-root ran.
- The attempted WSTA58 delegation remained explicitly gated.
- Public URL values, confirm-token values, raw wireless credentials, network
  identifiers, routable addresses, gateway/DNS values, lease IDs, and device
  serials are not committed here.
- Private raw artifacts remain under `workspace/private/` only.

## Next

Fix WSTA28 so the cleanup gate accepts the final public-off state as the
load-bearing proof, while still failing closed when autoconnect remains enabled,
supplicant is still running, or secret logging is nonzero.  Then rerun the
WSTA58 live measurement.
