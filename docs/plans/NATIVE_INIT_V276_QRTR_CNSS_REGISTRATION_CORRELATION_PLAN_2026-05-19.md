# Native Init v276 QRTR/CNSS Registration Correlation Plan

## Summary

- target: v276 QRTR/CNSS registration-state correlation
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- new tool: `scripts/revalidation/wifi_qrtr_cnss_registration_correlator.py`
- packet transmission: none
- daemon execution: none

v273 showed WDS/DMS QRTR nameservice readback timeouts. v275 then showed the
source-backed WLFW service id `69` also times out in native state. v276 does not
send more packets. It correlates prior readback evidence with current read-only
QRTR/CNSS/kernel/process/netdev state to decide whether the blocker is service-id
selection, QRTR kernel readiness, or missing userspace/platform registration.

## Inputs

Prior evidence:

- `tmp/wifi/v273-qrtr-readback-matrix-live-20260519-110229/manifest.json`
- `tmp/wifi/v275-wlfw-qrtr-readback-live-20260519-111529/manifest.json`
- `tmp/wifi/v274-wlfw-service-locator/manifest.json`

Live read-only captures:

- `version`, `status`, `netservice status`, `selftest verbose`
- `cat /proc/net/protocols`, `/proc/net/dev`, `/proc/net/netlink`, optional `/proc/net/qrtr`
- `ls /proc/net`, `/sys/class/net`, optional rfkill/ieee80211 classes
- read-only `/dev` and `/sys` search for `qrtr`, `qmi`, `cnss`, `icnss`, `wlan`, `diag`, `ipa`
- `ps -A -o pid,stat,comm`
- no-send `a90_qrtr_probe` if present

## Decision Model

Expected PASS decision:

```text
qrtr-cnss-registration-gap-classified
```

This means:

- QRTR kernel/socket readiness is still present.
- Prior WDS/DMS/WLFW nameservice readback evidence exists and all service cases
  produced zero service notifications.
- Current native state has no `cnss-daemon` process, no `wlan*` interface, and
  no strong registered Wi-Fi QRTR endpoint surface.
- Therefore the next blocker is registration/runtime state, not another blind
  service-id retry or QMI request payload.

Alternative decisions:

- `qrtr-cnss-state-incomplete`: required evidence is missing or stale.
- `qrtr-cnss-platform-surface-visible`: static CNSS/WLAN/QRTR platform sysfs or
  devicetree surfaces exist, but active QRTR service notifications remain absent.
- `qrtr-cnss-registration-visible`: active QRTR/device endpoint surfaces appear
  and should be inspected before any next step.
- `qrtr-cnss-safety-regression`: daemon, wlan, or unsafe state appears after the
  no-payload correlation pass.

## Guardrails

v276 must not:

- send QRTR nameservice packets or QMI payloads
- start `cnss-daemon`, `cnss_diag`, HAL, supplicant, wificond, hostapd, DHCP,
  or routing commands
- scan/connect/link-up Wi-Fi
- mutate rfkill, ICNSS, firmware paths, Android partitions, property service,
  perfd, kmsg, `/data/vendor/wifi`, or routing
- reboot or remount partitions

## References

- Linux QRTR registers the `QIPCRTR` protocol family and nameservice during
  protocol initialization: https://codebrowser.dev/linux/linux/net/qrtr/af_qrtr.c.html
- Android common kernel QRTR source shows control-port behavior and local port
  assignment rules: https://android.googlesource.com/kernel/common/+/aef3a58b06fa9d452ba863999ac34be1d0c65172/net/qrtr/af_qrtr.c

## Validation

Run:

```bash
python3 scripts/revalidation/wifi_qrtr_cnss_registration_correlator.py \
  --out-dir tmp/wifi/v276-qrtr-cnss-registration-correlation \
  run
```

Static:

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_qrtr_cnss_registration_correlator.py \
  scripts/revalidation/wifi_qrtr_readback_matrix.py \
  scripts/revalidation/a90ctl.py

git diff --check
```

Postflight:

```bash
python3 scripts/revalidation/a90ctl.py --json version
python3 scripts/revalidation/a90ctl.py status
python3 scripts/revalidation/a90ctl.py run /cache/bin/toybox pidof cnss-daemon || true
python3 scripts/revalidation/a90ctl.py cat /proc/net/dev
```

## Acceptance

- v276 sends no packets and starts no daemon.
- required v273/v274/v275 manifests are loaded and checked.
- live read-only captures pass required checks.
- result classifies the current blocker without QMI payload escalation.
- final postflight leaves `cnss-daemon` absent and no `wlan*` interface present.
