# eSoC PON sequence — actual C source analysis (2026-06-02)

**Host-only. Correction + deeper finding.** Earlier handoffs said the provider
body was unavailable (only kernel strings). That was WRONG: the full esoc-mdm
driver C source is on disk at
`tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/esoc/`
(esoc-mdm-4x.c, **esoc-mdm-pon.c**, esoc-mdm-drv.c, esoc-mdm.h) — unpacked during
the V766 OSRC build. We can read the exact PON logic, not just strings.

## The exact A90 PON sequence (esoc-mdm-pon.c + esoc-mdm-4x.c)
ext-sdx50m uses `sdx50m_ops` -> `sdx50m_pon_ops`:
`.pon = mdm4x_do_first_power_on`, `.soft_reset = sdx50m_toggle_soft_reset`.

A90 DTS has **NO `qcom,mdm-auto-boot`** (grep empty in r3q + sdx dtsi), so
`esoc->auto_boot = false`. Therefore on `ESOC_PWR_ON` the driver runs the FULL
power-on (esoc-mdm-4x.c:207+):
```
ESOC_PWR_ON:
  AP2MDM_ERRFATAL = 0 ; AP2MDM_ERRFATAL2 = 0
  mdm_do_first_power_on()  == mdm4x_do_first_power_on():
     mdm_toggle_soft_reset(false) == sdx50m_toggle_soft_reset():
        AP2MDM_SOFT_RESET = assert(0)          # PM8150L GPIO9
        usleep_range(120000,180000)            # 120-180ms hold
        AP2MDM_SOFT_RESET = de-assert(1)
     msleep(150)                               # allow PON to complete
     AP2MDM_STATUS = 1                          # TLMM GPIO135 high
     # A90 has NO qcom,mdm2ap-pblrdy-gpio -> else branch:
     esoc_clink_queue_request(ESOC_REQ_IMG)     # ask userspace for image
  mdm_enable_irqs()                             # now MDM2AP_STATUS irq armed
```
Modem readiness then arrives as the **MDM2AP_STATUS rising IRQ** (GPIO142),
handled in mdm_status_change() (esoc-mdm-4x.c:577): on value==1 -> `mdm->ready =
true`. With auto_boot=false there is NO BOOT_DONE shortcut; readiness is purely
the GPIO142 IRQ.

## Where native is stuck — now pinned to source
Native's long-known block: `/dev/subsys_esoc0` open -> `mdm_subsys_powerup`
D-state (V849/V902 wchan). That D-state is INSIDE this PON path — the
`usleep_range(120000..)` soft-reset hold and `msleep(150)` of
`mdm4x_do_first_power_on`, reached via `subsys_start -> powerup()`. So native DOES
enter the real PON code and DOES drive GPIO9 assert/de-assert + GPIO135=1 +
ESOC_REQ_IMG. It then waits for the GPIO142/MDM2AP IRQ that never comes.

This sharpens the blocker to ONE hardware question: native executes the correct
GPIO9 PON toggle (120ms assert) and GPIO135=1, but the SDX50M never raises
MDM2AP. Either (a) the GPIO9 PON pulse is electrically ineffective on this boot
(PMIC pad not actually driven / wrong polarity / PS_HOLD not latched), or (b) the
modem needs a main rail that the bootloader normally leaves on but native's boot
path does not. The provider only READS MDM_PMIC_PWR_STATUS; it never enables a
modem rail — so if a rail is off, the provider cannot fix it.

## Why the loop's forced-RC1 path can't substitute
Forced RC1 enumerate (V1370+) drives PCIe PERST but does NOT run ESOC_PWR_ON, so
GPIO9 PON / GPIO135 / ESOC_REQ_IMG never fire on that path — the endpoint is dead
at PERST. The natural path (subsystem_get(esoc0) -> ESOC_PWR_ON) is the only one
that actually powers the modem, and it is exactly the one that D-state-blocks.

## What remains (honest split)
- Host-resolvable, NOT yet done: read esoc-mdm-4x.c probe/setup
  (mdm4x_pon_setup, gpio request, soft_reset_inverted, MDM_PMIC_PWR_STATUS wiring)
  to confirm GPIO9 polarity/`soft_reset_inverted` and whether any rail/regulator
  is requested in probe. Also check XBL/ABL/modem partition dumps (not yet on
  disk) for who powers the SDX50M main rail at cold boot.
- Hardware-only, needs LIVE: whether the 120ms GPIO9 assert actually reaches the
  modem PS_HOLD and whether MDM2AP ever toggles — a bounded read-only observation
  of the natural ESOC_PWR_ON path (NOT forced RC1, NOT fake-ONLINE), watching
  GPIO142/MDM2AP IRQ count during the powerup window.

## Source refs (on disk)
- esoc-mdm-pon.c:45 sdx50m_toggle_soft_reset, :80 mdm4x_do_first_power_on,
  :321 sdx50m_pon_ops
- esoc-mdm-4x.c:207 ESOC_PWR_ON, :577 mdm_status_change, :958 auto_boot parse
- A90 DTS: no qcom,mdm-auto-boot; ap2mdm-soft-reset-gpio=<pm8150l_gpios 9>;
  no qcom,mdm2ap-pblrdy-gpio

## Host follow-up (2026-06-02): probe/setup + polarity + regulator — RESOLVED

The "host-resolvable, not yet done" item above is now done. Read
`esoc-mdm-pon.c` parse/setup, `esoc-mdm-4x.c` gpio table, and the A90 DTS.

### GPIO9 PON polarity — CONFIRMED CORRECT on native (no defect)
- `mdm4x_pon_dt_init` (esoc-mdm-pon.c:263) reads
  `qcom,ap2mdm-soft-reset-gpio` flags; `OF_GPIO_ACTIVE_LOW` -> `soft_reset_inverted=1`.
- A90 DTS: `qcom,ap2mdm-soft-reset-gpio = <&pm8150l_gpios 9 0>`, and
  `pm8150l_gpios` has `#gpio-cells = <2>`, so the 3rd cell `0` is the flags =>
  NOT active-low => **`soft_reset_inverted = 0`**.
- With inverted=0, `sdx50m_toggle_soft_reset` (esoc-mdm-pon.c:45):
  **assert = 0 (drive LOW), de-assert = 1 (drive HIGH)**. Sequence = pulse LOW
  for the `usleep_range(120000,180000)` window, then HIGH; idle = HIGH.
- LIVE cross-check matches exactly: V1276 found native PMIC GPIO9 steady-state
  `out/high` (== de-asserted idle), identical to Android V919; V1318 captured a
  native GPIO1270 (PMIC GPIO9) **low->high pulse** before GPIO135. So native
  drives the PON line with the correct polarity, level, and idle state.
  => Do NOT spend live cycles "fixing" GPIO9 polarity/pinctrl. It is right.

### Provider has ZERO power/regulator code — CONFIRMED
- `grep -rn regulator|vreg|supply` across all of `drivers/esoc/*.c|h` = **none**.
- The only "power" symbols are GPIOs the provider reads/asserts, not rails:
  - `MDM_PMIC_PWR_STATUS` (esoc-mdm.h:67): an INPUT the AP reads
    (`gpio_direction_input`, esoc-mdm-pon.c:299) — and A90 DTS does NOT populate
    `qcom,mdm-pmic-pwr-status`, so it is invalid/skipped.
  - `AP2MDM_PMIC_PWR_EN` (esoc-mdm-4x.c:51): an output to enable a modem PMIC —
    A90 DTS does NOT populate `qcom,ap2mdm-pmic-pwr-en-gpio`, so it is never
    driven.
- Therefore the eSoC provider, by construction, drives **no modem main rail**.
  Its entire AP-side power lever is the GPIO9 PON pulse, which native does
  correctly. If the SDX50M main VDD is off, nothing in this driver turns it on.

### Who powers the SDX50M main rail — NOT on disk
- No XBL/ABL/sbl/NON-HLOS/modem partition dump exists in the repo
  (`find ... -iname '*xbl*' / '*abl*' / '*NON-HLOS*' / '*modem*.img'` = none).
- So the cold-boot agent that brings up the SDX50M main rail (bootloader/PMIC
  HW default) is genuinely not present in any on-disk artifact.

### Net host conclusion (firmly grounded this time)
The **entire AP/software side is host-verified complete and correct**: right PON
polarity (source + 2 live captures agree), GPIO135 assert, ESOC_REQ_IMG queued,
auto_boot=false full path. The provider provably cannot and does not power the
modem rail. The single remaining unknown — is the SDX50M main rail actually
powered when native's PON pulse lands — is **not on disk** and is hardware/
bootloader-level. The only way to advance is a bounded read-only LIVE observation
of the natural `__subsystem_get(esoc0)` -> `mdm_subsys_powerup` window watching
the MDM2AP/GPIO142 IRQ count (NOT forced RC1, NOT fake-ONLINE, no PMIC/GPIO write).
