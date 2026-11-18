# S22+ mainline UFS: module predicates against upstream tolerance

H0 only. No device action, grant, candidate or capability change. This audit
reads the late-UFS module as it stands after V12 (`waipio_hci.c`,
`waipio_phy.c`, `g0q_stage.c`, `reset-pin.h` under
`workspace/public/src/mainline/s22plus_ufs_link_h0/`) against the selected
Linux 7.2.11 tree retained privately at
`workspace/private/outputs/s22plus-mainline-canary-h0-20261027-1/linux-7.2.11/`
and the FYG8 vendor `ufshcd.c` retained with ML043. Line numbers below refer
to those exact files.

## Why audit the frame now

ML036 through ML047 each ended with one guard refusal, and each refusal led
to the next attended run. Lined up, every refusal for which upstream has an
equivalent step was a condition upstream accepts without checking:

| Run | Refused condition | Upstream behaviour |
| --- | --- | --- |
| ML036/039 | HCE = 1 at module entry | `ufshcd_hba_execute_hce` stops an active controller unconditionally (`ufshcd.c:5089`) |
| ML042 | HCS UCRDY (`0x8`) after stop | `ufshcd_hba_stop` waits only for HCE = 0 (`ufshcd.c:5059-5071`) |
| ML043 | Stale IS UCCS (`0x400`) | no IS precondition; the ISR write-clears every read bit (`ufshcd.c:7400-7402`) |
| ML045/046 | CFG1 bit 0 immediate readback | `ufs_qcom_select_unipro_mode` writes without readback (`ufs-qcom.c:427`) |
| ML047 | IS UIC_ERROR (`0x4`) during DME_LINK_STARTUP | not enabled during link startup; cleared and ignored (below) |

ML040's reset-pin CTL guard is a module ownership check with no upstream
counterpart and is not counted. No refusal in the series identified a
hardware fault. Each identified a module predicate stricter than the driver
that brings this controller up on Linux and on FYG8. This is the pattern
recorded for the S22+ USB campaign: consecutive valid refusals with an
unchanged symptom are evidence about the instrument, not about the target.

## The ML047 refusal

The module's command poll (`waipio_hci.c`, `command()`) returns EIO on any
IS bit outside `UIC_COMMAND_COMPL | UIC_LINK_STARTUP`. ML047's first such
sample was `0x00000004`, before any completion.

Upstream treats the same bit as expected noise during link startup:

- After HCE, `ufshcd_hba_execute_hce` enables only `UFSHCD_UIC_MASK`
  (`ufshcd.c:5125`), which is UCCS plus power-mode/hibernate bits
  (`ufshci.h:197-200`). UIC_ERROR belongs to `UFSHCD_ERROR_MASK`
  (`ufshci.h:202`) and is not enabled until `ufshcd_make_hba_operational`.
- `ufshcd_intr` writes back every IS bit it read, then dispatches only the
  enabled subset (`ufshcd.c:7400-7404`). A latched UIC_ERROR is cleared
  without being handled.
- `ufshcd_wait_for_uic_cmd` returns the ARG2 result byte on completion and
  has no error-bit branch (`ufshcd.c:2603-2629`). The timeout is 500 ms
  (`ufshcd.c:53`), the same bound the module uses.
- `ufshcd_link_startup` then reads UECPA once, with the comment
  "Clear UECPA once due to LINERESET has happened during LINK_STARTUP"
  (`ufshcd.c:5337`). The FYG8 vendor driver carries the same line
  (vendor `ufshcd.c:4744`).

The ML047 sample is therefore consistent with an ordinary PA-layer LINERESET
indication that the module treated as terminal. It is not proof: the module
never read UECPA, so the originating layer is unobserved, and the link might
still have failed had polling continued. A second explanation remains open
(see CFG1 below). The two are distinguishable in one run if the module keeps
polling and records the UIC error-code registers.

## Remaining predicates on the reached path

All predicates before the link poll passed physically in ML046 and ML047
(stage 6, six local commands, link issued). They remain stricter than
upstream but have no evidence against them, so this audit does not propose
changing them.

| Module predicate | Upstream | Physical status |
| --- | --- | --- |
| V6 handoff admission: HCS UCRDY set, no HEI/DEI, doorbells/IE zero, IS ⊆ UCCS, pin CTL `0xb` and high | none; unconditional stop | passed ML042+ |
| Post-stop quiescent: HCE/doorbells/run-stop/IE/AHIT zero, IS zero after V9 ack | none | passed ML044+ |
| Core reset 200 µs / 1 ms | identical (`ufs-qcom.c` `ufs_qcom_host_reset`) | passed |
| Device reset pulse 10–15 µs low/high | identical (`ufs-qcom.c:2238-2242`) | passed |
| L5 at 880–888 mV in NORMAL mode before load/enable | none | passed |
| CFG1 bit-1 PHY reset readback | write only (`ufs-qcom.h:295,306`) | passed |
| HCE enable wait requires HCE = 1 **and** UCRDY | HCE only, 1 ms × 50, three outer retries | passed |
| TX_FSM_STATE (`0x41`) = HIBERN8 from one DME_GET | polled for up to 100 ms (`ufs-qcom.c:384-424`, `ufs-qcom.h:15`) | passed |
| Before every UIC command: HCS = UCRDY only, IS = 0, IE = 0 | waits up to 500 ms for UCRDY only (`ufshcd.c:2546-2553`) | passed 7 times |
| Local-command poll: any IS bit besides UCCS is EIO | non-enabled bits ignored | passed 6 times |

Two post-completion predicates have not yet been reached:

- **Result byte zero and DEVICE_PRESENT.** Same as upstream
  (`ufshcd.c:5282-5290`).
- **HCS HEI/DEI (`0x10`/`0x20`) clear.** Upstream core never consults these
  bits; they appear only as definitions (`ufshci.h:216-217`). The module does
  nothing after the link command, so this check classifies the result and
  gates no later hardware effect. The raw post-completion HCS is already
  recorded, so a refusal here would still be fully classified.

## Sequence differences that are not predicates

- **QUNIPRO_SEL position.** Upstream selects CFG1 bit 0 at the end of
  `ufs_qcom_power_up_sequence`, after PHY calibrate and before lane clocks
  (`ufs-qcom.c:541`, inside `ufs_qcom_power_up_sequence` at `:488`, then `ufs_qcom_enable_lane_clks` in
  `ufs_qcom_hce_enable_notify`, `:589-605`). The module selects at stage 6,
  after lane clocks. ML045–ML047 read `0x1c00052c` before and after the write,
  with bit 0 clear. Whether bit 0 reads back on this controller at all is
  unknown (the ML046 analysis covers upstream commit 823150ecf04f). If the
  selection did not take effect, the controller would run link startup in
  the wrong UniPro mode. That is the second explanation for ML047.
- **Omitted HCE post-change work.** Upstream enables UTP/UniPro hardware
  clock gating (CFG2 CGC and three DME read-modify-writes) and ICE before
  link startup. The module omits both and sets CFG1 bit 31 instead. These are
  power and crypto settings. Nothing found links them to link startup.
- **Link attempts.** Upstream allows four DME_LINK_STARTUP attempts with a
  full `ufshcd_hba_enable` between them (`ufshcd.c:80`, `:5277-5303`). The
  module scope allows one. At probe, upstream assumes the device is active and
  does not repeat link startup (`ufshcd.c:11268-11274`).

## Proposed V13 (design only)

The operator selected keeping one link attempt and tolerating UIC_ERROR.

1. **Link poll.** During the issued DME_LINK_STARTUP only, admit
   `UIC_ERROR` alongside UCCS and ULSS. Keep polling until UCCS or the
   existing 500 ms bound. Every other bit, including all of
   `INT_FATAL_ERRORS`, keeps the V12 terminal refusal and its recorded
   sample. Local commands keep the V12 rule.
2. **Observation.** Record the bitwise OR of every IS sample read during the
   link poll. If that OR contains UIC_ERROR, then after the poll ends
   (completion, refusal or timeout) read UECPA, UECDL, UECN, UECT and UECDME
   (`0x38`–`0x48`) once each, in order and within the module budget. These
   registers clear on read. Upstream reads UECPA only after a successful
   link startup (`ufshcd.c:5337`) and all five in its error handler; on a
   failed startup it returns before that read. Reading them after a failed
   V13 link is therefore a diagnostic extension, declared as new MMIO
   accesses with a read-to-clear side effect.
3. **No other change.** No IS write, second link attempt, timing change or
   relaxation of a pre-link guard. The functional-success predicate stays
   as it is.

**Possible addition (operator decision).** Move the existing QUNIPRO_SEL
write and its pre/post samples to the upstream position, after PHY calibrate
and before lane clocks. Each change has its own observation in the same run:
the CFG1 post-sample shows whether bit 0 latches at the new position, and the
IS OR plus UEC registers show what happened during link startup. Leaving the
move out gives clean attribution for the link result. Including it saves an
attended run if the old position turns out to be the cause.

Before any physical step, V13 needs a new report tag (`0xd0000000`). It also
needs a check that the added fields fit the 256-byte report envelope on
every reachable path, matching guest/host decoders, focused host and
ARM64/QEMU tests covering UIC_ERROR alone, with completion, with fatal bits
and with timeout, a capability adoption and one independent review. The
existing ML047 capability, grant and evidence are not modified.
