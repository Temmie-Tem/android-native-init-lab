# S22+ FYG8 P2.80 Post-Live Evidence Correction H0

Date: 2026-07-28 KST

## Verdict

`PASS_P280_POST_LIVE_EVIDENCE_CORRECTION_HOST_ONLY`

The review corrects one underclaim in the P2.80 F1 report, rejects one proposed
root cause against the exact FYG8 DT topology, and confirms two diagnostic
follow-ups. It performed no device contact, build, image change, approval,
transfer, reboot, or flash.

| Review claim | Result |
|---|---|
| `dwc3_gadget_run_stop(on=1) == 0` is only a software result | **REJECTED** |
| The omitted external eUSB2 repeater is the P2.80 no-attach cause | **RULED OUT for the exact FYG8 topology** |
| timeout handling reads but discards `current_speed` | **VERIFIED** |
| the original host-process exit needs explicit tracking | **VERIFIED; cause remains unresolved** |

## Run-Stop Hardware Meaning

The exact FYG8 `gadget.c` member has SHA256
`c121003d37f4fc9ab951f5d8811fe32736b21dadab985214996606578160c730`.
Its `dwc3_gadget_run_stop()` implementation:

1. sets `DWC3_DCTL_RUN_STOP`;
2. writes DCTL;
3. polls `DWC3_DSTS_DEVCTRLHLT`; and
4. returns `-ETIMEDOUT` unless `DEVCTRLHLT` clears before the bounded timeout.

The exact pull-up caller first obtains a positive runtime-PM result. A zero or
negative `pm_runtime_get_sync()` result returns before run-stop. It then calls
`dwc3_core_soft_reset()`, event-buffer setup, `__dwc3_gadget_start()`, and
`dwc3_gadget_run_stop(..., true)` while retaining that runtime-PM reference.

P2.80's clean nested return-zero trace therefore proves more than software
dispatch:

- the core soft reset returned success;
- event-buffer setup and gadget-start programming were invoked;
- speed programming and the DCTL RUN_STOP write were invoked; and
- DSTS reported the controller no longer halted before timeout.

`__dwc3_gadget_start()` is invoked without its return value being consumed in
this caller, so this review does not upgrade that invocation into a separate
success claim.

The result still does not prove an external electrical attach, host reset,
descriptor exchange, PHY or redriver output, or link progress beyond the
retained UDC state `not attached`. The corrected boundary is
**controller running, physical attach absent**, not merely
**software path returned zero**.

## External eUSB2 Repeater Hypothesis

### Module observation

The exact P2.80 materialized 60-module plan contains:

- `repeater.ko`, the generic repeater registry; and
- `phy-msm-snps-eusb2.ko`, the eUSB2 PHY driver.

It does not contain:

- `repeater-i2c-eusb2.ko`;
- `qti-regmap-debugfs.ko`; or
- `i2c-msm-geni.ko`.

The stock `modules.dep` confirms
`repeater-i2c-eusb2.ko` has hard module dependencies on
`qti-regmap-debugfs.ko` and `repeater.ko`. The exact eUSB2 PHY probe calls
`devm_usb_get_repeater_by_phandle()` before registering its PHY. The exact
repeater registry returns `-EPROBE_DEFER` when an enabled repeater node has not
registered a repeater device. On a board that actually selects this eUSB2
topology, the omitted device driver would therefore matter.

### Exact FYG8 topology

It is not this board's selected DWC3 topology.

The SHA-pinned 1,721,428-byte vendor DTB container
`2cd64d43a4f6b89a7c5523f3ef73fbb84dcad92c6d857e649cd1f0baa7c0080e`
contains four FYG8 variants. All four give the DWC3 child exactly:

```text
usb-phy =
  /soc/hsphy@88e3000
  /soc/ssphy@88e8000
```

Their compatible strings are:

```text
/soc/hsphy@88e3000  qcom,usb-hsphy-snps-femto
/soc/ssphy@88e8000  qcom,usb-ssphy-qmp-dp-combo
```

All four vendor DTBs contain zero eUSB2 or repeater nodes. All 11 entries in
the SHA-pinned DTBO
`97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`
also contain zero eUSB2/repeater node or DWC3 `usb-phy` override. The only
overlay `usb-phy` property belongs to the DisplayPort display node.

`layout-manifest.json` proves that the repeater module file exists in the stock
image; it does not prove that normal Android loaded or bound it. The normal
stock `modules.load` contains none of the eUSB2/repeater trio. They appear in
`modules.load.recovery`, which is not evidence for the P2.80 normal-boot
topology.

The missing `repeater-i2c-eusb2.ko` is therefore not a valid P2.80 root cause,
and adding it plus its bus/provider closure would spend a Full-LTO/F1 cycle on
an inactive DT branch. The P2.58 wording that treated `repeater.ko` as proof of
the active physical repeater closure was imprecise, but the exact DWC3 direct
PHY conclusion remains the femto HS PHY plus QMP SS PHY.

## Discarded Speed Observation

`p280_wait_configured()` reads both UDC `state` and `current_speed` on every
poll. On timeout it passes only `state`, its length, and the bind trace result
to `p280_timeout_detail()`. The final live `current_speed` value is therefore
not present in the retained record.

This is a real diagnostic loss, not a reinterpretation of P2.80. A future
versioned discriminator should retain the bounded exact speed class without
changing the closed P2.80 candidate or replaying it.

## Host-Process Interruption

The original invocation ended after durable `OBSERVED`; recovery later resumed
only the already-authorized rollback path. Host journal review found no OOM
kill, coredump, or process segfault in the relevant interval. No launcher exit
receipt survived, so the exact cause cannot be reconstructed.

This remains a host-tooling follow-up rather than a device-root-cause claim.
The next attended execution must preserve launcher stdout, stderr, exit status,
and a persistent session receipt. It must not change Process v2 recovery
semantics or justify another candidate attempt.

## Next

Do not add the inactive eUSB2 repeater closure and do not repeat P2.80. Narrow
the next H0 analysis to the exact active FYG8 path after a running DWC3 core:

1. `/soc/hsphy@88e3000` femto-HS PHY state and connect behavior;
2. QMP/redriver or parent connect-notify propagation where applicable;
3. VBUS override and the electrical attach boundary; and
4. a versioned retained `current_speed` observation if another discriminator
   is justified.

Controller start/halt is no longer an open branch. Actual link attach and
progress remain open.
