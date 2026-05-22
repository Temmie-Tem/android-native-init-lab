# Native Init V631 Per-Node Sibling-SSCTL Proof Plan

- date: `2026-05-23 KST`
- cycle: `v631`
- native build: `A90 Linux init 0.9.66 (v631)`
- scope: opt-in boot-image proof
- target: split the V630 ADSP/CDSP/SLPI sibling SSCTL proof into independent
  per-node child attempts so one blocking node cannot hide the others.

## Background

V630 proved the post-ACM one-shot safety model works:

```text
disabled-smoke: PASS
armed proof: ADSP write rc=0, then child timeout before CDSP/SLPI evidence
rollback: PASS
```

V630 did not advance service `74`, WLAN-PD, WLFW/BDF, or Wi-Fi link-up. The
active blocker is still below Wi-Fi HAL and around sibling SSCTL/service
publication.

## Design

V631 keeps the V630 safety model and changes only the proof granularity:

- arm flag: `/cache/native-init-sibling-ssctl-v631`
- required flag content: `run`
- proof log: `/cache/native-init-sibling-ssctl-v631.log`
- execution point: after USB ACM console attach
- per-node targets:
  - `adsp` -> `/sys/kernel/boot_adsp/boot`
  - `cdsp` -> `/sys/kernel/boot_cdsp/boot`
  - `slpi` -> `/sys/kernel/boot_slpi/boot`
- isolation: one forked child per node
- timeout: `5000ms` per node
- safety stop: if a timed-out child cannot be reaped, stop remaining nodes

## Guardrails

V631 must not:

- run before ACM console attach;
- start service-manager, CNSS, Wi-Fi HAL, supplicant, or hostapd;
- touch `boot_wlan`, `qcwlanstate`, or `shutdown_wlan`;
- scan/connect/link-up, use credentials, run DHCP, change routes, or ping
  externally;
- repeat automatically after the one-shot flag is consumed.

## Live Gate

1. Flash V631 with the arm flag absent.
2. Verify disabled-smoke boot and cmdv1 reachability.
3. Arm `/cache/native-init-sibling-ssctl-v631` with exact content `run`.
4. Reboot once into V631 armed proof.
5. Collect version, status, timeline, proof log, and dmesg markers.
6. Roll back to `stage3/boot_linux_v319.img`.

## Success Criteria

V631 passes if it classifies one of these outcomes with rollback completed:

- `v631-per-node-service74-advanced`
- `v631-per-node-sibling-sysmon-only`
- `v631-per-node-timeout-map`
- `v631-per-node-unreaped-stop`
- `v631-disabled-smoke-only`

Native Wi-Fi connection and `google.com` ping remain the final objective and
are not authorized by V631 unless lower service `74`/WLAN-PD/WLFW markers
advance enough to justify the next Wi-Fi stage.

