# V1130 PM Observer Modem Holder Helper Build Plan

Date: `2026-05-27`

## Goal

Add source/build support for a bounded `/dev/subsys_modem` first-opener inside
the post-policy `pm-service` trigger observer.

## Rationale

V1128 proved V490 repairs provider registration and lets CNSS PM
register/connect return `0x0`, but the PM server then blocks opening
`/dev/subsys_modem`.

V1129 proved global firmware mount visibility alone does not move mss, mdm3,
WLFW, service 69, or `wlan0`. The next useful live gate needs the V1128/V1129
post-policy provider-positive CNSS order plus a bounded modem first-opener
contract.

## Scope

- Bump `a90_android_execns_probe` marker to `v213`.
- Add `--allow-pm-observer-modem-pre-holder`.
- Add `--pm-observer-modem-pre-holder`.
- Limit the holder to `wifi-companion-pm-service-trigger-observer`.
- Start the holder before `pm_proxy_helper` in the PM observer order.
- Open only `/dev/subsys_modem` with `O_NONBLOCK`.
- Do not add any `/dev/subsys_esoc0`, eSoC ioctl/control, Wi-Fi HAL,
  scan/connect, credential, DHCP/route, or external ping path.

## Guardrails

- Source/build only.
- No deploy.
- No device command.
- No PM actor, CNSS actor, Wi-Fi HAL, scan/connect, credentials, DHCP/route, or
  external ping.
- No partition write, boot image write, flash, or reboot.
- Live use must still require both the observer allow flag and the modem
  pre-holder allow flag.

## Success Criteria

V1130 passes if:

- source contains the v213 marker and new gated flags;
- source contains the nonblocking modem pre-holder path;
- source records `plain_retry=0`;
- the static aarch64 helper builds;
- binary strings contain the new marker and safety strings;
- the output is statically linked with no interpreter.

## Expected Next

V1131 should deploy helper `v213` and run a bounded live gate:

```text
V490 policy load
  -> global firmware mounts
  -> PM observer modem pre-holder
  -> provider-positive CNSS PM connect
  -> classify mss/mdm3/WLFW/wlan0 delta
```

Wi-Fi HAL and scan/connect remain blocked until the lower modem/eSoC state
advances.
