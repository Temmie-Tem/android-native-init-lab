# Native Init v407 Composite Wi-Fi HAL Retry Plan

## Objective

Retry the bounded composite Wi-Fi HAL start-only smoke after V406 proved the
`system_ext` VNDK v30 linker dependency closure.

V405 reached the composite start-only boundary but failed before the observe
window because `android.hardware.wifi@1.0.so` was not visible. V406 fixed that
specific blocker with helper v24 and `v30-to-system-ext-v30`.

## Scope

V407 is still start-only. It may start only:

- `servicemanager`
- `hwservicemanager`
- first Wi-Fi HAL candidate `vendor.wifi_hal_ext`

The run must stay inside one helper-owned private namespace and use:

```text
--vndk-apex-alias-mode v30-to-system-ext-v30
```

## Explicit Non-Goals

- no Wi-Fi scan/connect/link-up;
- no credentials, supplicant association, DHCP, routing, or default route;
- no `wificond`, supplicant, hostapd;
- no CNSS/diag lifecycle widening;
- no rfkill write, ICNSS bind/unbind, module load/unload, firmware mutation;
- no Android partition write;
- no persistence or boot/autostart changes.

## New Artifact

- runner: `scripts/revalidation/wifi_composite_hal_start_only_v407_runner.py`

The runner reuses the V405 composite engine but changes the required conditions:

- helper SHA: `7ec11d95085f1c3dc370884725b080b44150bf8b0a5f7d897df048188a815063`
- helper marker: `a90_android_execns_probe v24`
- V406 input: `tmp/wifi/v406-system-ext-vndk-linker-list-live-20260520-100627/manifest.json`
- private APEX mode: `v30-to-system-ext-v30`

## Gate Sequence

1. Run plan mode: no device command.
2. Run preflight: read-only device commands only.
3. Confirm run without approval is fail-closed and executes no device command.
4. Commit the approval packet.
5. Only after exact operator approval, run bounded start-only retry.
6. Review postflight process and Wi-Fi link cleanliness before widening scope.

## Required Future Approval Phrase

```text
approve v407 composite Wi-Fi HAL start-only retry only; no scan/connect/link-up and no Wi-Fi bring-up
```

## Success Criteria

V407 approval packet is ready when:

- plan mode returns `v407-composite-hal-start-only-retry-plan-ready`;
- preflight returns `v407-composite-hal-start-only-retry-preflight-ready`;
- no-approval run returns `v407-composite-hal-start-only-retry-approval-required`;
- V406 linker-list input is pass;
- helper v24 SHA and `v30-to-system-ext-v30` mode are confirmed;
- process and Wi-Fi link surfaces are clean;
- all non-approved paths report no mutation, no daemon start, no HAL start, and no Wi-Fi bring-up.

