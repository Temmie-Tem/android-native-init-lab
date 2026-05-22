# Native Init V613 MDM3/ESOC Targeted Observer Prep Report

- date: `2026-05-23 KST`
- status: `prepared`; live observer is **not** executed yet
- runner: `scripts/revalidation/native_wifi_mdm3_esoc_targeted_observer_v613.py`
- plan evidence: `tmp/wifi/v613-mdm3-esoc-plan-static/`
- preflight evidence: `tmp/wifi/v613-mdm3-esoc-preflight-current/`

## Scope

V613 prep adds a native targeted observer for the V612 lower-surface delta. It
reuses the V609 firmware mount, `subsys_modem` holder, and no-CNSS lower
companion observer path, then adds a no-close `subsys_esoc0` holder with reboot
cleanup.

The observer must not start CNSS, service-manager, Wi-Fi HAL, `wificond`,
supplicant, hostapd, scan/connect/link-up, credentials, DHCP, routes, or
external ping.

## Static Validation

```text
py_compile: pass
plan decision: v613-mdm3-esoc-targeted-observer-plan-ready
current preflight decision: v613-preflight-blocked
current blocker: v490-current-policy-load
```

The current preflight blocker is expected after the V612 rollback reboot because
SELinux policy-load proof freshness is per boot.

## Safety Contract

```text
subsys_modem: open and hold
subsys_esoc0: open and hold
explicit close before reboot: forbidden
cleanup: reboot boundary
kernel WARNING/reference mismatch: failure
```

The runner explicitly checks `subsys_esoc0` char-device visibility before live
execution and records `mdm3` state before deciding whether the lower publication
path advanced.

## Next Gate

Recommended live sequence:

1. Refresh current-boot V401/V490.
2. Run V613 preflight.
3. Run V613 live with the exact approval phrase.
4. Verify native rollback after reboot cleanup.
5. If `mdm3=ONLINE`, sibling sysmon, service-notifier `180/74`, or WLFW service
   `69` appears, move to a CNSS-only follow-up. Otherwise, keep HAL/scan/connect
   blocked.
