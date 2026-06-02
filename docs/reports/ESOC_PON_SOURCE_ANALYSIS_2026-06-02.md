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
