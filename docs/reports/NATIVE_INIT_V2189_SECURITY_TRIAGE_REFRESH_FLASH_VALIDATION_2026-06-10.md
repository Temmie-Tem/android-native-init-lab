# Native Init V2189 Security Triage Refresh Flash Validation

## Summary

- Candidate: `v2189-security-p0-stage-fix`
- Init: `A90 Linux init 0.9.261 (v2189-security-p0-stage-fix)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2189_security_p0_stage_fix.img`
- Boot SHA256: `f54becb2b720ad198413c2a0089912626ca295c79a96f13e0921cf4f05b39f51`
- Helper SHA256: `a4ef028aee167ab6a66b17389ade37427e85647d18e45270634f666b8efe1a44`
- Decision: `v2189-security-triage-refresh-flash-validation-pass`
- Result: PASS

## Scope

This validation flashes the post-triage V2189 image built after the active
security triage hardening set. It verifies pinned local image identity, recovery
handoff, boot partition readback, native boot, version, selftest, and a bounded
Wi-Fi scan/connect smoke on both saved private profiles.

The Wi-Fi smoke intentionally did not run DHCP, install routes, set DNS, or ping
external hosts.

## Flash Verification

- Local image marker matched `A90 Linux init 0.9.261 (v2189-security-p0-stage-fix)`.
- Local image size: `60948480`.
- Local image SHA256 matched the pinned expected SHA.
- Native-init to recovery handoff succeeded.
- Recovery ADB became ready.
- Sealed local image copy was pushed to recovery.
- ADB push speed: `83.9 MB/s`.
- Remote `/tmp/native_init_boot.img` SHA256 matched the pinned local SHA.
- `/dev/block/by-name/boot` write completed successfully.
- Boot partition prefix readback SHA256 matched the pinned local SHA.
- TWRP reboot to system completed successfully.
- Native selftest after reboot passed with `fail=0`.
- Version verification matched `A90 Linux init 0.9.261 (v2189-security-p0-stage-fix)`.

## Phase Timing

| phase | elapsed_sec | result |
| --- | ---: | --- |
| inspect local image | 0.083 | pass |
| native to recovery | 0.306 | pass |
| wait recovery ADB | 27.135 | pass |
| adb push | 0.846 | pass |
| remote sha256 | 0.097 | pass |
| boot dd write | 0.442 | pass |
| boot readback sha256 | 0.169 | pass |
| flash boot image | 1.554 | pass |
| reboot TWRP to system | 2.305 | pass |
| verify native init | 31.925 | pass |
| total | 63.375 | pass |

## Native Verification

```text
selftest: pass=11 warn=1 fail=0 duration=51ms entries=12
A90 Linux init 0.9.261 (v2189-security-p0-stage-fix)
version: 0.9.261 build=v2189-security-p0-stage-fix
```

## Wi-Fi Smoke

- Stored private profile inventory succeeded with `secret_values_logged=0`.
- 5 GHz-class profile status succeeded with `profile_valid=1`, secret files present, and owner-only modes.
- 2.4 GHz profile status succeeded with `profile_valid=1`, secret files present, and owner-only modes.
- Scan completed with `decision=wifi-scan-pass`.
- 5 GHz-class connect completed with `decision=wifi-connect-carrier-up`, `carrier_up=1`, and `wpa_state=COMPLETED`.
- 5 GHz-class associated frequency: `5745 MHz`; status reported RSSI `-51 dBm` and link speed `866 Mbps`.
- 2.4 GHz connect completed with `decision=wifi-connect-carrier-up`, `carrier_up=1`, and `wpa_state=COMPLETED`.
- 2.4 GHz associated frequency: `2412 MHz`; status reported RSSI `-45 dBm` and link speed `144 Mbps`.
- Both connect windows reported `credentials_logged=0`, `secret_values_logged=0`, `dhcp_routing=0`, and `external_ping=0`.
- Cleanup after each connect completed with `decision=wifi-cleanup-done`.
- Post-smoke status returned to idle: `operstate=down`, `carrier=0`, `supplicant.process_count=0`, and control socket missing.
- Final selftest remained `fail=0`.

## Interpretation

The physical device is now running the post-triage V2189 image with boot
partition readback matching the pinned source-built artifact. The refreshed SHA
also passes bounded Wi-Fi scan/connect smoke on both saved private profiles. The
remaining warning in selftest is the existing accepted trusted-lab boundary and
is not a new flash or Wi-Fi blocker.
