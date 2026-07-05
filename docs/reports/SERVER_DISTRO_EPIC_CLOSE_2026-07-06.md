# Server-Distro Epic Close

Date: 2026-07-06 KST
Scope: A90 server-distro epic close-out after WSTA232 and WSTA233

## Verdict

CLOSED.  The A90 server-distro epic has reached the operator-chartered stopping
point: the default-off server profile is live-proven, D-harden has been rolled
up as complete, the single persistence smoke has been measured, and the device
has been rolled back to the v2321 clean baseline with `selftest fail=0`.

Do not open new WSTA/D-harden levers in this epic.  The remaining work below is
intentionally classified as post-close productization or next-target work.

## Proven Appliance Path

The viable A90 shape is a native-owned control plane with Debian services
launched under bounded, explicit gates:

```text
native PID1 owns boot, display/control, SD runtime, USB/NCM/tcpctl
  -> SD-backed Debian root/chroot or staged appliance assets
  -> loopback-only service payloads
  -> explicit outbound tunnel/public gate when operator-authorized
  -> checked cleanup and v2321 rollback as the recovery net
```

Evidence:

- D4D proved a real Debian userdata appliance handoff: Debian 12.14, sysvinit as
  PID1, key-only Dropbear over the USB-local admin path, and clean v2321
  rollback.  Report:
  `docs/reports/SERVER_DISTRO_D4D_USERDATA_APPLIANCE_HANDOFF_2026-07-03.md`.
- D-public proved the public smoke path: loopback-only HTTP marker, outbound
  Cloudflare quick Tunnel, and public HTTPS marker return with the URL kept
  private.  Report:
  `docs/reports/SERVER_DISTRO_DPUBLIC_LIVE_PUBLISH_2026-07-04.md`.
- The D-public HUD proof showed the Debian-side KMS status HUD and loopback
  smoke service can run together during the live appliance demonstration.
  Report:
  `docs/reports/SERVER_DISTRO_DPUBLIC_BOOT_VISUAL_HUD_2026-07-04.md`.
- WSTA110 proved the service launcher inside the SD-backed Debian chroot:
  `dpublic-smoke-httpd` launches as the non-root service user with
  `NoNewPrivs=1`, zero effective capabilities, and loopback-only network
  intent.  Report:
  `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA110_SERVICE_LAUNCHER_CHROOT_LIVE_2026-07-05.md`.
- WSTA120 and WSTA209 proved the admin SSH boundary: non-root admin login works,
  root login is rejected, and the Dropbear admin daemon also runs under the
  derived seccomp profile.  Reports:
  `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA120_DROPBEAR_ADMIN_LIVE_2026-07-05.md`
  and
  `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA209_DROPBEAR_ADMIN_SECCOMP_LIVE_2026-07-05.md`.

## D-Harden State

WSTA232 is the canonical close-out rollup:

```text
state=D_HARDEN_COMPLETE_DEFAULT_OFF
complete=true
server_state=SERVER_PROFILE_READY_DEFAULT_OFF
public_state=PUBLIC_OFF
blocking_before_enforcement=[]
launcher_remaining_profiles=[]
syscall_remaining_profiles=[]
```

Landed or parked levers:

```text
seccomp_real_services=true
capability_drop_nonroot_services=true
native_uplink_root_boundary=true
legacy_iptables_loopback_default_drop=true
cloudflared_egress_allowlist=true
apparmor_parked_unavailable=true
```

Representative evidence:

- WSTA207 loaded/enforced the seccomp canary in the chroot transport.
- WSTA209 proved `dropbear-admin-usb` remains functional under seccomp while
  root login stays rejected.
- WSTA213 made native Wi-Fi/uplink operations a native-owned boundary, not a
  Debian launcher target.
- WSTA219 proved the attended legacy-iptables loopback/default-drop public path
  and cleanup/restore.
- WSTA230 folded the attended cloudflared egress allowlist proof into operator
  status with route values redacted and public state returning to `PUBLIC_OFF`.
- WSTA214 audited AppArmor and correctly parked it as unavailable under current
  kernel/runtime/userspace evidence.

Canonical reports:

```text
docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA207_SECCOMP_LIVE_CANARY_PASS_2026-07-05.md
docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA209_DROPBEAR_ADMIN_SECCOMP_LIVE_2026-07-05.md
docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA213_OPERATOR_STATUS_NATIVE_UPLINK_BOUNDARY_2026-07-05.md
docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA214_APPARMOR_FEASIBILITY_2026-07-05.md
docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA219_ATTENDED_DEFAULT_DROP_LIVE_2026-07-05.md
docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA230_OPERATOR_STATUS_CLOUDFLARED_EGRESS_LIVE_2026-07-05.md
docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA232_DHARDEN_COMPLETE_STATUS_2026-07-06.md
```

## Persistence Smoke

WSTA233 completed the single chartered persistence measurement with real
attended cold-boot evidence:

```text
disconnect_seen=true
reconnect_seen=true
serial_disconnect_reconnect=true
uptime_drop=true
pre_uptime_sec=5525.80
post_uptime_sec=33.89
decision=wsta233-cold-boot-persistence-smoke-live-pass
```

Classification:

```text
native-pid1-and-usb-control-persisted-debian-admin-services-manual-rebringup-required
```

Interpretation: native PID1, USB/NCM control, SD runtime, HUD, and tcpctl return
after the cold boot.  Debian admin SSH and loopback smoke were not running
before the cold boot and did not auto-start after it, so they remain manual
re-bring-up/productization work rather than a regression.

Rollback completed through the checked helper:

```text
native_version=0.9.285 build=v2321-usb-clean-identity-rodata
selftest_fail_zero=true
```

Report:

```text
docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA233_COLD_BOOT_PERSISTENCE_SMOKE_LIVE_PASS_2026-07-06.md
```

## Intentionally Not Done

These are not open blockers for this epic; they are explicit scope boundaries:

- **Full switch_root productization:** D3B/D4D proved the mechanics of
  `switch_root` and Debian PID1, but WSTA14 showed the WLAN handoff path still
  loses usable station behavior after Debian handoff: `wlan0` exists and is
  administratively up, but does not reach `RUNNING`/`LOWER_UP`, direct scan
  fails, and association remains below L3.  Keeping native PID1 as the durable
  hardware/control owner is the correct A90 posture.
- **Persistence auto-start supervisor:** WSTA233 measured the gap; it did not
  build a supervisor.  Auto-starting Debian admin SSH, smoke, or public tunnel
  is post-close productization and must be separately chartered.
- **Real service payload:** The proof payload remains a loopback smoke marker.
  No application payload, SLA, service persistence policy, or public product
  surface is part of this close-out.
- **Always-on public exposure:** Public exposure remains default-off.  Live
  public work requires an explicit attended gate, route redaction, and cleanup.
- **AppArmor profiles:** AppArmor is parked because the current evidence does
  not support it as an immediate D-harden lever.

## Kernel Ceiling

The A90 path is bounded by a vendor 4.14 kernel and a closed hardware bring-up
surface.  The server-distro work recovered a useful controlled appliance model,
but it did not create a maintainable kernel-rebuild path, upstreamable LSM
posture, or clean full-Linux ownership of WLAN/display/audio.

That is the reason to stop here and pivot only under a new operator charter,
with the expected next target being an unlocked GKI-class device such as S22+
SM-S906N where kernel rebuild and policy integration are first-class work rather
than reverse-engineered recovery work.

## Final State

Current committed close-out state:

```text
D-harden: complete/default-off
persistence smoke: live pass
public exposure: default-off
device boot: v2321 rollback baseline
final health: selftest fail=0
next action: halt and wait for operator next-target charter
```

This report is public-safe: it contains no raw public URL, tunnel credential,
Wi-Fi credential, route endpoint, SSH key value, MAC/BSSID, or raw private run
transcript.
