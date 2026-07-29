# S22+ FYG8 P2.86 deep-suspend guard reachability H0

Date: 2026-07-29
Tier: H0, host-only static derivation
Candidate run ID: `c6cde593033d6f1be93f82c8ff5a81e8`
Source contract: `s22plus-fyg8-p286-parent-tail-bounded-restart-v1`

## Question

P2.86 relies on the disconnected HS PHY suspend path reaching:

```text
msm_hsphy_set_suspend(..., 1)
  -> clocks off
  -> msm_hsphy_enable_power(..., false)
```

The helper call is guarded by four runtime conditions:

```c
if (phy->cable_connected || (phy->phy.flags & PHY_HOST_MODE))
        /* shallow suspend */
else if (!phy->dpdm_enable)
        if (!(phy->phy.flags & EUD_SPOOF_DISCONNECT))
                /* clocks/LDO-off helper path */
```

This audit asks whether the exact frozen 60-module bare-PID1 peripheral-stop
closure can reach that helper path. It does not treat helper dispatch as proof
that an idempotent guard was passed, that a regulator provider accepted a
disable, or that an analog rail physically collapsed.

## Exact source provenance

The reconstructed FYG8 source inputs are:

| Input | SHA256 |
|---|---|
| `SM-S906N_15_base_osrc/Kernel.tar.gz` | `86e2f73412c65fadff0b15bbf0eac9140610f70250514ac0bddbf3b53fb5f7bf` |
| `S906NKSS7FYG8_osrc/S906NKSS7FYG8_kernel.tar.gz` | `23ef2b27de8843e271d41405b3c0b1a71bfa668615c8f0f12a1e5c4395ec851a` |

The FYG8 delta has no member for any source used below:

- `drivers/usb/phy/phy-msm-snps-hs.c`
- `drivers/usb/dwc3/dwc3-msm-core.c`
- `drivers/soc/qcom/eud.c`
- `drivers/power/supply/qcom/smb5-lib.c`
- `arch/arm64/configs/vendor/waipio_sec_defconfig`
- `qcom/proprietary/devicetree/qcom/waipio.dtsi`
- `qcom/proprietary/devicetree/qcom/waipio-usb.dtsi`

The cited base members are therefore the exact reconstructed FYG8 sources for
this derivation.

## Result

Verdict:

```text
PASS_P286_DEEP_SUSPEND_HELPER_PATH_STRUCTURALLY_REACHABLE_H0
```

All four guards are false in the exact P2.86 peripheral-stop closure.

### 1. `PHY_HOST_MODE` is false

`dwc3-msm-core.c:6438-6450` sets the HS PHY `PHY_HOST_MODE` flag only when
starting host mode. The corresponding host-stop path clears it at
`:6568-6587`. The peripheral start/stop helper at `:6633-6766` does not set the
flag. The other HS flag set at `:7045-7048` is conditional on system resume
while already in host mode.

The P2.86 state machine invokes the peripheral stop helper at
`dwc3-msm-core.c:6882-6893`. No host transition exists in the frozen candidate
sequence. The flag is therefore false at the relevant suspend.

### 2. `cable_connected` is false before suspend

`dwc3_otg_start_peripheral(..., 0)` calls
`usb_phy_notify_disconnect(mdwc->hs_phy, ...)` at
`dwc3-msm-core.c:6712-6723`.

The exact callback is `msm_hsphy_notify_disconnect()` at
`phy-msm-snps-hs.c:844-850`, which assigns:

```c
phy->cable_connected = false;
```

This precedes the child `pm_runtime_put_sync()` at core `:6730-6743` and the
parent PM put in the helper tail at `:6762`. Parent runtime suspend reaches
`dwc3_msm_suspend()` and then `usb_phy_set_suspend(hs, 1)`.

Common `gadget.c` soft-disconnect, pull-up, and gadget-suspend paths contain no
PHY disconnect notification. The load-bearing clear is the vendor-core call
above, and its ordering is explicit.

### 3. `dpdm_enable` remains false

`struct msm_hsphy` is allocated with `devm_kzalloc()` at
`phy-msm-snps-hs.c:1570-1581`, so the initial value is false.

All direct assignments are closed:

| Value | Exact source locations | Producer |
|---|---|---|
| true | `:980`, `:1002` | virtual `dpdm` regulator enable callback |
| true | `:1309` | internal charger-detection preparation |
| false | `:1021`, `:1036` | virtual regulator disable callback |
| false | `:1338` | charger-detection teardown |

The only base-source external consumer of a regulator named `dpdm` is
`drivers/power/supply/qcom/smb5-lib.c:1123-1169`. It is built through
`qpnp-smb5-main`, which is not enabled by the exact waipio configuration and is
absent from the frozen 60-module plan. The exact waipio/g0q DT closure also has
no `dpdm-supply` consumer.

The internal `msm_hsphy_prepare_chg_det()` has one caller, the PHY port-state
work at `phy-msm-snps-hs.c:1371`. That work and its notifiers are initialized
only when the HS PHY node itself has an `extcon` property
(`:1756-1763`, `:1777-1787`). The exact HS PHY node in
`waipio-usb.dtsi:108-126` has no such property. The separate SSUSB parent has
`extcon = <&eud>` at `waipio-usb.dtsi:51`; that does not initialize the PHY's
charger-detection worker.

`dwc3-msm` only obtains, reads, and registers a notifier on the optional dpdm
regulator. It does not enable it. Consequently neither the external regulator
callback nor the internal charger-detection producer can set `dpdm_enable` in
the frozen closure.

The EUD-valued early branch at `phy-msm-snps-hs.c:978-981` is inside the same
unreached regulator enable callback and does not independently change this
result.

### 4. `EUD_SPOOF_DISCONNECT` remains false

The exact plan loads `eud.ko` before the HS PHY and DWC3, and the exact DT
enables the EUD node. `eud.c:633-801` can probe it and can preserve a
bootloader-enabled EUD state. The module parameter nevertheless defaults to
disabled at `eud.c:93`, and P2.86 supplies no EUD parameter or sysfs write.

More importantly, EUD activation is not itself the spoof flag producer.
`EUD_SPOOF_DISCONNECT` is set only at
`dwc3-msm-core.c:3975-3988`, after `check_eud_state` is set by the EUD-named
extcon notifier at `:4488-4558`.

The exact `waipio_sec_defconfig:80-84` has:

```text
CONFIG_USB_NOTIFIER=m
```

`IS_ENABLED(CONFIG_USB_NOTIFIER)` is therefore true. The DWC3 extcon
registration function returns immediately at
`dwc3-msm-core.c:4612-4614`, before the notifier registrations at
`:4627-4658`. The exact FYG8 `dwc3-msm.ko` independently matches that compiled
shape: it retains the downstream EUD state strings but has no
`dwc3_msm_vbus_notifier` implementation symbol.

No other assignment sets `check_eud_state`, and the remaining
`EUD_SPOOF_DISCONNECT` occurrence at core `:3998-4004` only clears the flag.
The spoof-disconnect guard therefore remains false.

## Exact reached boundary

With the four guards false, `msm_hsphy_set_suspend()` reaches
`phy-msm-snps-hs.c:816-818`:

```c
msm_hsphy_enable_clocks(phy, false);
msm_hsphy_enable_power(phy, false);
```

This is consistent with the P2.84 retained `0x8f/detail=0xc18` evidence that
the zero-return stop helper and nested suspend boundary executed. The static
derivation adds that the software guard structure does not make the deep-off
helper unreachable.

## Proof boundary

This H0 result proves:

- the deep-off helper call is structurally reachable in the exact P2.86
  module, DT, configuration, and peripheral-stop closure;
- no frozen-plan dpdm consumer or PHY charger-detection worker holds the
  `dpdm_enable` guard true; and
- the compiled DWC3 notifier choice prevents production of
  `EUD_SPOOF_DISCONNECT`.

It does not prove:

- passage beyond `msm_hsphy_enable_power()`'s
  `power_enabled == on` idempotent guard;
- that each regulator provider accepted and completed a disable;
- that another consumer did not retain a shared regulator vote; or
- physical voltage collapse on any HS PHY rail.

An already-active EUD or another shared-regulator vote can still affect the
electrical result without changing the software guard-reachability verdict.

### Idempotent-guard follow-up

The complete assignment closure for `power_enabled` is:

```text
phy-msm-snps-hs.c:386  power_enabled == on -> immediate zero return
phy-msm-snps-hs.c:479  power_enabled = true
phy-msm-snps-hs.c:552  already false -> disable-side early return
phy-msm-snps-hs.c:555  power_enabled = false
```

The setter at line 479 is reached only through successful
`msm_hsphy_enable_power(..., true)` completion. The clearer at line 555 is
reached only through the actual disable path. For the selected `on=false`
call, line 386 is therefore idempotent only if the last relevant state was
already false.

This closes the state-variable mechanism but not its last-writer ordering.
The retained P2.80/P2.84 evidence does not prove that the final completed
enable was later than every possible disable before the selected stop, nor
does the zero-return helper observation distinguish line 386 from completion
through line 555. The exact disposition remains:

```text
NO_PROOF_P286_POWER_ENABLED_IDEMPOTENT_GUARD_PASSED_H0
```

Closing that boundary requires new runtime evidence. It is not a reason to
change the frozen P2.86 candidate before its next run.

## Decision

This H0 unit finds no new P2.86 F1 blocker and proposes no candidate,
module-plan, contract, or `SOURCE_KEYS` change. It supports the selected
suspend-then-DWC3-restart strategy at the software guard level.

P2.86 must still complete Full-LTO A/B identity proof, linked/static/package
gates, ready-manifest generation, and D0. Any F1 remains separately gated by a
fresh exact approval; this report grants no device authority.
