# Native Init v283 ICNSS/WLFW Start-Only Delta Plan

## Summary

- target: v283 bounded CNSS start-only ICNSS/WLFW readiness delta observer
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- new tool: `scripts/revalidation/wifi_icnss_wlfw_start_delta_observer.py`
- daemon execution: bounded `cnss-daemon` start-only through the existing guarded
  helper
- packet transmission: no QRTR nameservice transmission from this observer
- QMI payload: no direct QMI payload from this observer
- sysfs/debugfs/control writes: none from this observer
- scan/connect/link-up/credentials/DHCP/routing: blocked

v282 showed that no-start native state has ICNSS core bound but no direct
WLFW/firmware-ready state file. v283 performs a bounded start-only run and
compares ICNSS/WLFW read-only state before and after. The "during" evidence is
the helper transcript and captured live `/proc/<cnss-daemon>/status` while the
child is running; serial remains single-command, so v283 does not attempt a
second concurrent serial observer.

## References

- Qualcomm ICNSS source shows firmware-ready indication handling and host-driver
  probe gating:
  https://android.googlesource.com/kernel/msm/+/android-7.1.0_r0.2/drivers/soc/qcom/icnss.c
- Qualcomm ICNSS QMI source shows WLFW service connection state logging:
  https://android.googlesource.com/kernel/msm/+/79a5a3af469e5d38c649dbe3dc7340d96990fd68/drivers/soc/qcom/icnss_qmi.c
- Qualcomm ICNSS devicetree binding describes WLAN FW communication over QMI:
  https://android.googlesource.com/kernel/msm/+/157ab4a1b7d2bf3275a20ee90d855bec184d742e/Documentation/devicetree/bindings/cnss/icnss.txt
- Linux debugfs documentation is used to keep debugfs as non-stable,
  no-mount/no-write evidence unless explicitly planned:
  https://docs.kernel.org/filesystems/debugfs.html

## Scope

The observer records:

- before/after v282 readiness snapshots:
  - ICNSS platform binding and WLAN module state
  - existing debugfs names only
  - `/sys/kernel/shutdown_wlan`
  - WLAN netdev/wiphy visibility
  - filtered dmesg readiness lines
  - CNSS process table cleanliness
- nested `wifi_cnss_start_only_runner.py` evidence:
  - preflight
  - helper dry-run plan
  - bounded live `cnss-daemon -n -l` transcript when explicitly approved
  - helper-side child status/maps and cleanup result

## Decision Model

Expected likely decision:

```text
icnss-wlfw-start-no-readiness-delta
```

This means the bounded start-only run completed and cleaned up, but did not
change ICNSS/WLFW readiness surfaces.

Alternative decisions:

- `icnss-wlfw-start-readiness-log-delta-cleaned`: readiness-looking dmesg delta
  appeared and postflight cleaned up.
- `icnss-wlfw-start-readiness-surface-delta-cleaned`: sysfs/debugfs readiness
  candidates changed and postflight cleaned up.
- `icnss-wlfw-start-readiness-delta-cleaned`: other readiness evidence changed
  and postflight cleaned up.
- `icnss-wlfw-start-delta-readiness-leak`: postflight `wlan*` or wiphy became
  visible.
- `icnss-wlfw-start-delta-process-leak`: postflight CNSS process table is not
  clean.
- `icnss-wlfw-start-delta-start-failed`: start-only runner failed its safety
  gate.
- `icnss-wlfw-start-delta-not-observed`: runner did not reach observable
  `start-only-pass`.

## Guardrails

v283 must not:

- send QRTR nameservice packets
- send direct QMI request payloads
- run Wi-Fi scan/connect/link-up/credential/DHCP/routing commands
- run `cnss_diag`, HAL, supplicant, wificond, or hostapd
- run ICNSS bind/unbind, `driver_override`, rfkill unblock, recovery, ramdump,
  or assert controls
- mount or write debugfs
- mutate firmware paths or Android partitions
- reboot automatically

The only live execution is the already validated CNSS `start-only` helper path,
bounded by runtime timeout and postflight cleanup checks.

## Validation

Static:

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_icnss_wlfw_start_delta_observer.py \
  scripts/revalidation/wifi_icnss_wlfw_readiness_surface.py \
  scripts/revalidation/wifi_cnss_start_only_runner.py \
  scripts/revalidation/a90ctl.py

git diff --check
```

Plan and preflight:

```bash
python3 scripts/revalidation/wifi_icnss_wlfw_start_delta_observer.py \
  --out-dir tmp/wifi/v283-icnss-wlfw-start-delta-plan \
  plan

python3 scripts/revalidation/wifi_icnss_wlfw_start_delta_observer.py \
  --out-dir tmp/wifi/v283-icnss-wlfw-start-delta-preflight \
  preflight
```

Live bounded run:

```bash
python3 scripts/revalidation/wifi_icnss_wlfw_start_delta_observer.py \
  --out-dir tmp/wifi/v283-icnss-wlfw-start-delta-live-$(date +%Y%m%d-%H%M%S) \
  --max-runtime-sec 10 \
  run \
  --allow-daemon-start \
  --assume-yes \
  --i-understand-reboot-only-recovery
```

Postflight:

```bash
python3 scripts/revalidation/a90ctl.py --json version
python3 scripts/revalidation/a90ctl.py status
python3 scripts/revalidation/a90ctl.py run /cache/bin/toybox pidof cnss-daemon || true
python3 scripts/revalidation/a90ctl.py cat /proc/net/dev
```

## Acceptance

- start-only execution is bounded and uses the existing guarded runner.
- helper transcript proves `cnss-daemon` was observable and reaped.
- before/after readiness snapshots are stored.
- no QRTR nameservice packet or direct QMI payload is sent by the observer.
- postflight has no `cnss-daemon`, no `cnss_diag`, no `wlan*`, and no wiphy.
- evidence is written under `tmp/wifi/v283-*` with private output handling.
