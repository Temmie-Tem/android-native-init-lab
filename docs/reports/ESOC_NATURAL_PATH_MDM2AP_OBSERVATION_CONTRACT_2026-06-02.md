# Live observation contract — natural ESOC_PWR_ON path, MDM2AP/GPIO142 response (2026-06-02)

**Handoff for the loop. Read before designing the next live cycle.** This pins
the ONE next live experiment after the host-side static/config closure. It is a
contract, not a nudge: the trigger, the measurement, the success/fail labels, and
the hard stops are all fixed here. The loop owns the mechanical
source/build → artifact-sanity → rollbackable handoff → classify cycles (its
proven strength); it does NOT own re-framing this experiment.

## Why we are here (host closure, do not re-litigate)
Three static/config layers are now host-verified at parity with Android and are
CLOSED as the differentiator:
- bootloader (xbl/abl/pmic-config): non-differential — only the boot partition is
  flashed; identical on both sides.
- eSoC provider source (`ESOC_PON_SOURCE_ANALYSIS_2026-06-02.md`): PON polarity
  correct (`soft_reset_inverted=0` ⇒ assert LOW 120ms → de-assert HIGH; matches
  V1276 idle + V1318 pulse), and the provider has ZERO regulator code — it cannot
  and does not power the modem rail.
- DTB (`ESOC_DTB_PARITY_2026-06-02.md`): non-differential — appended SoC dtb
  matches source; mdm3/esoc board layer comes from shared dtb/dtbo partitions and
  is live-proven correct on native (GPIO135/142/9 claim + polarity parity).

So the AP/software side is correct. The single remaining unknown is hardware: when
native's (correct) GPIO9 PON pulse + GPIO135 assert + ESOC_REQ_IMG land, does the
SDX50M actually power up and answer on MDM2AP/GPIO142? That is not on disk.

## The experiment

### Trigger — natural path ONLY
Drive the modem through the provider's natural
`__subsystem_get(esoc0)` → `subsys_start` → `mdm_subsys_powerup` path, exactly as
the PM-first / mdm_helper / pm-service route already reaches it (V1238 / V1303 /
V1586 / V1589). The provider then runs `mdm4x_do_first_power_on`
(GPIO9 PON pulse → msleep(150) → GPIO135=1 → ESOC_REQ_IMG) on its own.

**Forbidden as trigger or anywhere in the window:**
- forced RC1 enumerate (`rc_sel=2` + `case=11`, sysfs `debug/enumerate`, any
  pci-msm debug case write) — it is downstream of MDM2AP and contaminates the
  observation (V1370–V1559 proved it cannot substitute).
- fake-ONLINE / system-info spoof to advance pm-service (inverted causality,
  `ESOC_PMSERVICE_CAUSALITY_HANDOFF`).
- any PMIC/GPIO/GDSC/regulator write, eSoC notify/`BOOT_DONE`, global PCI rescan,
  platform bind/unbind.

### Measurement — over a single long window, read-only
Reuse the EXISTING clean natural-path observers; do NOT invent new write paths.
Build on the V1467-class exact-provider PIL+GPIO tracepoint test boot
(`A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_PIL_TRACEPOINT_SAMPLER` +
`..._TRACEPOINT_SAMPLER`, `rc1_watcher_delay_ms=0`, `rc1_retry_count=0` — i.e. NO
RC1 writer), plus the `mdm2ap_errfatal_pcie_timing` sampler
(`--pm-observer-late-per-proxy-mdm2ap-errfatal-pcie-timing-sampler`, V1326) which
already carries GPIO142 IRQ delta and MDM-errfatal IRQ delta fields.

Capture, in the SAME window, from the provider trigger through at least the
Android modem-PON window (Android needs ~255 ms esoc0→PCIe; hold ≥ several
seconds past `mdm_subsys_powerup` entry, e.g. the long-window samplers already
used in V1472/V1474):
1. PIL notif `fw=esoc0` start (proves provider entered the path).
2. GPIO1270 (PM8150L GPIO9) PON pulse low→high — confirm the native pulse fires.
3. GPIO135/AP2MDM set 1 — confirm AP-side assert.
4. **GPIO142/MDM2AP**: tracepoint lines AND `/proc/interrupts` IRQ count delta —
   the discriminator.
5. **mdm errfatal** GPIO141/53 IRQ delta.
6. (context, expected absent) PCIe RC1/LTSSM, MHI, WLFW, `wlan0`.

### Success / fail labels (fixed)
- `mdm2ap-responds`: GPIO142 toggles or its IRQ count increments after GPIO135
  assert ⇒ NEW progress; the modem is answering — proceed to classify the next
  downstream gate.
- `mdm2ap-silent-natural-path`: full PON trace present (esoc0 PIL + GPIO9 pulse +
  GPIO135=1) but GPIO142 + errfatal IRQ counts stay 0 through the long window ⇒
  confirms the block is the modem not answering on the *clean* natural path
  (removes the forced-RC1 contamination caveat from V1552). This is a PASS as a
  classification, not a failure.
- `provider-did-not-trigger`: esoc0 PIL / `mdm_subsys_powerup` never reached ⇒
  route regression, fix the route, not the modem.

Transport loss or no rollback = FAIL (not a result). Rollback to
`stage3/boot_linux_v724.img` and verify selftest `fail=0` every run.

## Honest expectation (do not over-run on this)
GPIO142=0 is already seen in V1318/V1328/V1552; this run's NEW value is only the
clean-natural-path confirmation (label `mdm2ap-silent-natural-path`). **One run is
enough to set that label.** Do NOT spin dozens of timing/window variants on it —
that is the V1370–V1559 failure mode. Once `mdm2ap-silent-natural-path` is
recorded, STOP and hand back: the next move is a *separately user-authorized*
bounded modem-rail/PMIC experiment (the V1250–V1255 power-write-gate direction),
which is a new explicit gate and must NOT be entered autonomously from this
observation.

## Hard stops (unchanged, restated)
No forced RC1/case writes, no fake-ONLINE, no PMIC/GPIO/GDSC/regulator writes, no
eSoC notify/`BOOT_DONE`, no global PCI rescan, no platform bind/unbind, no Wi-Fi
HAL/scan/connect, no credentials, no DHCP/routes, no external ping, no flash or
partition write outside the approved test-boot↔v724 rollback.

## Refs
`ESOC_PON_SOURCE_ANALYSIS_2026-06-02.md`, `ESOC_DTB_PARITY_2026-06-02.md`,
`ESOC_PMSERVICE_CAUSALITY_HANDOFF_2026-06-02.md`,
`ESOC_PROVIDER_STATIC_ANALYSIS_2026-06-01.md`; V1318 (clean GPIO135/142/1270
trace), V1326/V1328 (mdm2ap_timing sampler), V1467/V1469 (exact-provider PIL+GPIO
tracepoint, no RC1 writer), V1238/V1303/V1586 (natural provider trigger),
V1552 (forced-RC1-contaminated GPIO142 silence), V1250–V1255 (power-write-gate,
the separately-gated next step).
