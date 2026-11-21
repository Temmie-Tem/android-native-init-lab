# S22+ mainline replug dependency: root-cause plan (H0)

Date: 2026-11-22
Target: Galaxy S22+ `SM-S906N` / `g0q`, Linux 7.2.11 mainline + Debian RAM PID1.
Scope: host-only source and evidence analysis. No device contact, no build,
no candidate created. Nothing here grants device authority.

## Problem

On mainline, the host sees the phone's USB gadget only after a physical
replug at the phone end:
- ML041, ML048 and ML050 left the cable untouched and saw no endpoint in
  73–88 samples.
- ML021, ML047 and ML052 replugged once and authenticated.

The replug cue is what cost ML051 and ML052. Removing the dependency removes
the cue, the attach interlock timing and the operator burden together.

## Evidence

| Source | Finding |
|---|---|
| Stock FYG8 base DT and DTBO | MAX77705 sits on `i2c@994000` (QUP0 SE5, mainline `i2c5`). The PMIC is at `0x66`; the USBC/MUIC client is at `0x25` (`(0x4a >> 1)`). The same bus carries an FSA4480 at `0x42`. The stock SE5 node uses GSI `dmas` and `qcom,shared`. |
| Samsung `max77705-muic.h:363-392` | CONTROL1 = NoBCComp[7] / RCPS[6] / D+[5:3] / D−[2:0]. `COM_OPEN=0x3f` and `COM_USB=0x09`, both with NoBCComp=0 ("compare with BC1.2"). The header says nothing about the IC switching on its own. |
| Samsung `max77705-muic.c` | The driver always commands the switch itself. Probe runs initial detection (`:2301-2308`, `:2641`), and a USB/CDP attach writes `COM_USB` (`:1147-1158`, `:1415-1420`). Shutdown calls `com_to_open()` (`:2710-2723`). So a reboot from Android, including into Download, leaves `COM_OPEN` commanded. XBL `muic_init` also issues CONTROL1 opcodes on every boot, with unknown payload. |
| P3.17 (Samsung-kernel candidate) | One boot-time read returned `0x3f`, inherited from the boot chain. Causality of the later enumeration is unknown because the connection was physically moved. |
| Mainline 7.2.11 | The `max77705` MFD has only rgb, charger and haptic cells (`drivers/mfd/max77705.c:18-21`). Nothing drives the USBC/MUIC client, and the selected config has `MFD_MAX77705` unset and `TYPEC=n`. `dwc3-qcom` forces VBUS-valid override at probe and on run-stop (`dwc3-qcom.c` around 590-602 and 688-692). That largely bypasses the missing-initial-VBUS failure seen in upstream commit 9835a6ef. |
| S22 r0q prior art | Attempt 4b: the UDC stayed `not attached`, a software reconnect failed, and a physical replug worked. Attempt 23 fixed it with a 12-patch bundle, applied all at once with no isolation. The bundle had a MAX77705 **CCIC** driver at `0x25`, `dr_mode otg` with role-switch default peripheral, a connector graph and a dwc3 patch. |
| Tab S8+ CCIC patches (the r0q source, local copy) | The base `max77705-typec.patch` does not write CONTROL1. The bundle's `max77705-typec-source-attach.patch` does. Its message says that on the tablet, with a mouse attached and powered, "the MUIC switch (CTRL1) read 0x00, open. Writing COM_USB (0x09) with opcode 0x06 enumerated the mouse at once." The patch then writes `COM_USB` every time it sets a data role, with the comment "The firmware leaves the MUIC switch open across an attach" (`r0q-port/kernel/upstream-patches/tabs8/max77705-typec-source-attach.patch`, header and `max77705_usbc_set_data_role`). So the r0q fix that worked does include an explicit `COM_USB` write. |
| r0q mainline `i2c5` | The r0q DT enables `qupv3_id_0` and `i2c5` but never enables `gpi_dma0`, which is disabled in `sm8450.dtsi`. The boot log records `i2c_qcom_geni OK (/dev/i2c-0 = i2c5)`. On this sibling board, SE5 therefore runs in FIFO mode under mainline. The MAX77705 IRQ comes from PM8350C GPIO 5, not TLMM. |

## Hypotheses

1. **Open switch (H1).** CONTROL1 is `0x3f` at candidate boot, so D+/D− never
   reach the connector. This is supported for the boot state by the P3.17
   read and by the stock shutdown path.
   - **The tension:** if only the AP can change the switch, a replug should
     not fix it. So either the IC re-routes on a new attach (no source
     evidence), or H1 is not the whole story.
   - The r0q fix writes `COM_USB` explicitly, and on the tablet a host-mode
     attach left the switch open until that write. So the IC does not close
     the switch on every attach.
   - **A reconciling reading (PLAUSIBLE).** NoBCComp=0 means "compare with
     BC1.2". The IC may route to USB on its own only when it runs BC1.2,
     which happens on a sink attach with VBUS from a PC, as in our replug.
     The tablet's mouse case was a source attach, where BC1.2 does not run.
     This fits both data points but has no direct evidence. Stage 1 tests it.
2. **Host gave up (H2).** The pull-up reaches the host, enumeration fails, and
   the host waits for a new connect change. No run captured host-side kernel
   logs or hub port status, so this is untested.
3. **CC / Type-C attach state (H3).** XBL also runs `ccic_init`. With a
   C-to-C cable the host's data path depends on CC attach, which a replug
   redoes. This does not apply with a C-to-A cable.
4. **DWC3 start state (H4).** This is weakened by the forced VBUS override and
   by r0q's failed software reconnect, but it is not tested on g0q.
5. **FSA4480 (H5).** Low. Samsung parks it at USB pass-through (`0x98`), and
   whether it sits in series on D+/D− is unverified.

The phone-side state ("UDC bound but not attached") has never been observed
on g0q. ML050's retained records were lost.

## Plan, cheapest first

### Stage 0: host-only, no phone change

On the next attended mainline run of any kind, including the pending UFS
retry, capture the following during the untouched-cable window:
- the host kernel log;
- the selected hub port's status (connect and enable bits, via sysfs or
  `usbmon`);
- the cable type (C-to-A or C-to-C).

How to read the result:

| Host shows | Reading |
|---|---|
| A connect change or enumeration errors | The pull-up crosses the connector. H1 is refuted for that boot and H2 leads. |
| No connect at all | H1, H3 and "pull-up never asserted" survive. Go to Stage 1. |

The phone image does not change. This only adds host capture to a run that
happens anyway.

### Stage 1: read-only phone observation

1. **Kernel changes.** Build an Image with `I2C_QCOM_GENI=y` and
   `QCOM_GPI_DMA=y`. Both are `=m` today and the RAM archive carries no
   modules, so a DT change alone cannot work.
2. **DT changes in `g0q.dtsi`:**
   - enable `qupv3_id_0` and `i2c5`. Following r0q, leave `gpi_dma0` off,
     since FIFO mode worked there. If the hardware reports FIFO disabled on
     g0q, probe defers. That is a safe `NO_PROOF`, not a hazard.
   - **TLMM: keep it disabled (preferred).** ML017 disabled TLMM after
     earlier unexplained failures, and every passing run since has had it
     off. Instead, delete the `i2c5` pinctrl properties and rely on the boot
     chain's pin mux; XBL's `muic_init` already uses SE5. If the pins are not
     muxed, I2C fails cleanly. The fallback is r0q's route: enable TLMM with
     the reserved ranges and the stock pull-up and drive 2 on gpio206/207.
     That reintroduces the variable ML017 removed, so it needs its own review.
3. **Debian observer, via i2c-dev.** Find the adapter by its `994000.i2c`
   name. Then:
   - **First,** read and record UIC_INT (`0x02`, read-to-clear). XBL's last
     command may have left a stale `APCmdResI` and response latched.
   - Issue CONTROL1_R with opcode `0x05`: out `0x21..`, start with `0x41`,
     poll BIT7 with a bound, read the response at `0x51`, and require the
     opcode echo to match.
   - Read the FSA4480 registers `0x04` and `0x05`.
   - Keep sampling. VBUSDetI and CHGTypI in UIC_INT time-stamp a physical
     replug at the IC.
4. **Getting the evidence off the phone.** A late replug cue is still needed,
   because the replug is the only channel that brings the samples back (ML050
   retention returned nothing). Read CONTROL1 and UIC_INT again after the
   replug.

How to read the result:

| Observed | Reading |
|---|---|
| pre = `0x09` | H1 refuted |
| pre = `0x3f`, post-replug = `0x09` | the IC re-routes on attach (H1 with autonomy) |
| pre = `0x3f`, post-replug = `0x3f`, yet USB works | the switch is not the blocker; reread FSA4480 and H2/H3 |
| I2C fails | `NO_PROOF` for the switch |

### Stage 2: one write, only after Stage 1 reads `0x3f`

- Send a single `CONTROL1_W(0x09)` early in boot, then hold a no-touch
  sampling window.
- Issue the replug cue only **after** that window closes.
- **Success criterion:** the host enumerates before the cue. That would remove
  the replug dependency for this boot path.
- One run tests one subclaim. A write run cannot also test IC autonomy.

## Risks to resolve in Stage 1 review

- **Shared serial engine.** The stock SE5 is `qcom,shared`, and stock wraps
  transfers in GPI lock/unlock (`i2c-msm-geni.c` around 970-982, 1073-1080).
  Mainline has no shared-SE handling. The other execution environment is
  unidentified, and concurrent use could collide. Keep the transaction count
  tiny and identify the other user if possible.
- **GSI-only mode.** Mainline uses GPI only if `FIFO_IF_DISABLE` is set
  (`i2c-qcom-geni.c` around 1039-1048). Without `gpi_dma0`, probe defers
  forever. r0q's working FIFO-mode `i2c5` makes this less likely on g0q but
  does not prove it.
- **r0q as evidence.** The r0q port has used SE5 under mainline with no
  reported collision. That is an absence of reports, not proof that the
  shared-SE peer is idle.
- **Readback limits.** A readback proves the IC accepted the command, not that
  the switch conducts.
- **TLMM.** No `ps_hold` function exists on sm8450, so no new reset hook
  appears. The impact is believed low; reviewers should check it.
- **Charger, PD and firmware.** Stage 1/2 touch only the USBC mailbox, and
  only opcodes `0x05` and `0x06`. They do not touch the charger, PD, firmware
  update or reset. They exclude the Samsung updater path and the full CCIC
  bring-up flagged in the 2026-08-11 control-plane audit.

## Method note

- Two independent read-only cross-checks ran: a Claude subagent, and Codex
  `gpt-6.2-sol` (high effort, CLI 0.171.0, after two earlier attempts were
  rejected by the server). Key citations were spot-verified at source.
- Both reviewers recommend that the first discriminator make **no** CONTROL1
  write: read before and after one timed replug. A write run cannot also
  test IC autonomy.
- Codex pointed to the local `source-attach` patch. An earlier fetch agent
  had read only the base Tab S8+ patch and reported "no CONTROL1 write". That
  was true for that file but wrong for the bundle; this revision corrects it.
- The r0q boot log was read through a fetch agent; the r0q DT and patches were
  read from the local copy under
  `workspace/private/outputs/s22plus-mainline-canary-h0-20261027-1/r0q-port/`.

## Related

- [ML048 attach references](S22PLUS_MAINLINE_ML048_USB_ATTACH_REFERENCES_2026-11-11.md)
- [ML048 no-replug run](S22PLUS_MAINLINE_ML048_NO_REPLUG_RUN_2026-11-11.md)
- [ML050 retention analysis](S22PLUS_MAINLINE_ML050_RETENTION_ANALYSIS_2026-11-12.md)
- [MAX77705 control-plane successor feasibility](S22PLUS_FYG8_MAX77705_CONTROL_PLANE_SUCCESSOR_FEASIBILITY_H0_2026-08-11.md)
- [USB comprehensive audit](S22PLUS_FYG8_USB_COMPREHENSIVE_INVESTIGATION_AUDIT_H0_2026-08-30.md)
- [ML052 run](S22PLUS_MAINLINE_ML052_V13_RUN_2026-11-19.md)
