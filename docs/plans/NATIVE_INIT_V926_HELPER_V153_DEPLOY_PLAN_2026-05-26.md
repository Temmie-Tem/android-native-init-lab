# Native Init V926 Helper v153 Deploy Plan

## Goal

Deploy the V925-built `a90_android_execns_probe v153` helper to
`/cache/bin/a90_android_execns_probe` and verify remote checksum parity before
running another CNSS-before-eSoC live gate.

## Scope

V926 is deploy-only. It may write only the helper path under `/cache/bin`.
It must not start service-manager, Wi-Fi HAL, CNSS actors, scan/connect,
credentials, DHCP/routes, external ping, or native Wi-Fi bring-up.

## Inputs

- Local helper artifact:
  `tmp/wifi/v925-execns-helper-v153-build/a90_android_execns_probe`
- Expected SHA-256:
  `ef9b5b779909be67a6cf9a29e14f5445505220ec6a9c651c888ff48acda1326e`
- V925 report:
  `docs/reports/NATIVE_INIT_V925_CNSS_RUNTIME_NAMESPACE_SUPPORT_2026-05-26.md`

## Transfer Strategy

Preferred path is NCM if host IP and device ping are already ready. If NCM is
not ready or host sudo is unavailable, V926 falls back to serial `appendfile`
with a safe chunk size below the cmdv1x console line limit.

The V926 wrapper defaults to serial because NCM is not guaranteed on this host.
It uses chunk size `1800`, which keeps encoded cmdv1x lines below the safe
line limit.

## Hard Guardrails

- Write target is limited to `/cache/bin/a90_android_execns_probe`.
- No Android boot, ADB, boot image write, partition write, firmware mutation,
  GPIO/sysfs/debugfs write, module load/unload, service-manager, Wi-Fi HAL,
  CNSS actor start, scan/connect, credentials, DHCP/routes, external ping, or
  Wi-Fi bring-up.
- Helper usage may be invoked with no arguments only for marker/mode evidence.

## Success Criteria

- Local helper exists, has helper marker `v153`, and contains the
  `wifi-companion-mdm-helper-cnss-before-subsys-trigger-capture` mode token.
- Native status/selftest remain healthy before deploy.
- Serial line-size check passes.
- Deploy writes all chunks, decodes, chmods, atomically replaces the target, and
  verifies the remote SHA-256 equals the local helper SHA-256.
- Post-deploy state still has no service-manager/HAL/CNSS actor/Wi-Fi bring-up.

## Expected Next

If V926 passes, V927 should run a bounded compact
`wifi-companion-mdm-helper-cnss-before-subsys-trigger-capture` live gate using
helper `v153`.
