# S22+ UFS upstream handover, phase 4a (H0): build, gate, overlay, PHY tables

Status: **phase 4a done, host-only, no device action.** The operator approved
all four questions of the
[step-4 design](S22PLUS_MAINLINE_UFS_UPSTREAM_DRIVER_DESIGN_H0_2026-11-28.md)
on 2026-11-28 ("1~4 전부 승인할게, 4a부터 진행해"). The operator also
pre-approved a kernel rebuild if one was needed. None was.

## Result

| Check | Result |
| --- | --- |
| Upstream modules against the unchanged floor kernel | Built. Image `5139aab5`, symvers `fb83fba4`, config `881e450e` all unchanged. All four modules resolve every symbol against `vmlinux.symvers`. They import no `qcom_scm_`, `qcom_ice_`, `blk_crypto_` or `g0q_` symbol. |
| Write gate | Rendered into `ufshcd.c`, built, 14 tests pass |
| Late overlay | Applies to the route DT `51b58a40`. It changes only the two UFS nodes (status and additions) and adds one regulator device. |
| PHY tables vs the module's FYG8 tables | Unmodified upstream matches 121 of 128 final registers. After the g0q rendering, 127 of 128 match. The remaining register is written by upstream's own power-on. |
| Gate refusals vs probe | Every refused write is on a path whose failure probe ignores |

### Why the drivers are not built `=m` in the kernel tree

The floor kernel has `CONFIG_IKCONFIG=y`. Turning on `SCSI_UFSHCD=m` in its
`.config` would change the configuration embedded in the Image. The four
drivers are therefore built as external modules with `M=` against a copy of
`transport-build-floor`, using the retained toolchain (gcc 15.2,
`50d09618…`). Their Kconfig dependencies are already `=y`. The optional
parts, such as crypto, BSG, RPMB, HWMON and fault injection, stay out
because their symbols are unset.

| Module (gate + g0q PHY build) | SHA-256 |
| --- | --- |
| `ufshcd-core.ko` (gated) | `61d14646…` |
| `ufshcd-pltfrm.ko` | `fdee3d83…` |
| `ufs-qcom.ko` | `d8226117…` |
| `phy-qcom-qmp-ufs.ko` (g0q values) | `208a23c6…` |

Building twice reproduced the unchanged modules byte for byte.

## Write gate

`g0q_ufs_gate.h` holds the policy. `gate_render.py` inserts it into the
pinned `ufshcd.c` (`a99c7260…` → `9d419ac2…`). Each insertion must match
exactly once, or the render refuses.

- **SCSI.** In `ufshcd_queuecommand()`, before any state handling.
  - Allowed: TEST UNIT READY, REQUEST SENSE, INQUIRY, REPORT LUNS, READ
    CAPACITY(10), READ CAPACITY(16) (service action 0x10 only), MODE
    SENSE(6/10), READ(6/10/16), SYNCHRONIZE CACHE(10/16), and START STOP
    UNIT to the device W-LU (0xD0) only.
  - Anything else completes at once as CHECK CONDITION, ILLEGAL REQUEST /
    INVALID COMMAND OPERATION CODE, with no retry.
- **Device management.** In `ufshcd_issue_dev_cmd()`, on the composed UPIU
  just before execution.
  - Allowed: NOP OUT, query READ DESCRIPTOR, READ ATTRIBUTE, READ FLAG, and
    SET FLAG `fDeviceInit`.
  - Anything else returns `-EACCES`.
  - This covers all three reserved-command users: query/NOP, raw UPIU and
    advanced RPMB. It is also the only `blk_execute_rq()` call in the file.
- **No low-power state.**
  - Capabilities cleared after the `ufs-qcom` init: clock gating,
    hibern8-with-gating, clock scaling, WriteBooster (both), auto-bkops
    suspend, aggressive power collapse, runtime-PM autosuspend, crypto and
    TX equalization.
  - Auto-hibernate is disabled (`ahit = 0`).
  - The device W-LU never gets `pm_runtime_allow()`, so it keeps the SCSI
    default: runtime PM forbidden.
- **Counters.** The read-only module parameter `g0q_gate` reports:
  - allowed and refused counts per class;
  - a 256-bit bitmap of refused SCSI opcodes;
  - the first eight refused queries as `opcode<<8 | idn`;
  - the capabilities before and after the clear;
  - the auto-hibernate and W-LU flags.

The fixture checks every SCSI opcode × service action × 7 LUN classes. It
also checks every UPIU type × query opcode × IDN. Further tests confirm:
- no write-like opcode passes anywhere;
- START STOP UNIT passes only to the W-LU;
- each upstream query write listed in the design is refused;
- the source of each render is pinned.

### Refusals vs probe (code read, 7.2.11)

**Fatal steps in `ufshcd_device_init`.** These can fail probe:
- link startup;
- NOP verify;
- set and poll `fDeviceInit` (allowed);
- device-parameter reads;
- the HS gear change in `ufshcd_post_device_init`.

**Refused writes, all on paths that ignore failure:**
- `ufshcd_set_dev_ref_clk` (return ignored; it writes only if the value differs);
- `ufshcd_set_active_icc_lvl` and `ufshcd_set_timestamp_attr` (void);
- `ufshcd_set_rtt` (void, and only for UFS 4.0; this device is UFS 3.1);
- `ufshcd_force_reset_auto_bkops`, which would clear `fBackgroundOpsEn` and write EE control (void);
- `ufshcd_write_ee_control` in probe (return ignored);
- `ufshcd_temp_notif_probe`.

WriteBooster configuration is skipped because its capability is cleared.

UIC DME commands are not gated. They are the volatile UniPro and M-PHY
attributes of link startup, gear change and peer tuning.

## Late overlay

`upstream_overlay.py` renders the overlay (`d33d058e…`) for the route DT
`51b58a40`. It follows the upstream SM8450 QRD/HDK wiring, which matches the
module's measured rails exactly:
- vcc = L7B 2.504 V, 1.1 A;
- vccq and vdd-hba = L9B 1.2 V, 1.2 A;
- vdda-pll = L6B 1.2 V;
- vdda-phy = the existing USB-held L5B node;
- the L6/L9 parent is S12B.

The regulators are a new ordinary `qcom,pm8350-rpmh-regulators` device,
`regulators-9`, under apps RSC. It holds only `smps12`, `ldo6`, `ldo7` and
`ldo9`, each with min = max. S12B is fixed at the stock 1.256 V.

**Changes from the design:**
- **Rail authority needs no kernel change.** The transport kernel denies
  ordinary RPMh, ICC and clk-rpmh requests only from the issuer task while
  the private arena is open (`g0q_rpmh_deny_ordinary`). The handover stage
  never opens the arena, so upstream votes go through the ordinary
  frameworks from any context. The approved fixed-value rule is enforced by
  the regulator core: voltages are fixed by constraints, modes are limited
  to LPM/HPM, and these rails have no other consumer. L7B gets no Linux
  parent, so no vote reaches the shared BOB rail.
- **No `reset-gpios`.** The route DT keeps TLMM disabled. Enabling it would
  bring up the generic pinctrl driver for the whole SoC. Without the GPIO,
  `ufs-qcom` takes its no-device-reset path (`-EOPNOTSUPP`, ignored by
  `ufshcd`). If 4b's link startup needs the pulse, the fallback is TLMM
  `okay` plus `reset-gpios = <&tlmm 210 GPIO_ACTIVE_LOW>`. Line 210 is the
  `UFS_RESET` pad at TLMM offset `0xde000`, the module's `0x0f1de000`
  window.
- **ICE stays off.** The dtsi's `qcom,ice` remains, but `SCSI_UFS_CRYPTO` is
  off (the stub) and no ICE driver exists.

The validator checks that the overlay:
- changes no pre-existing node except the status of `ufshc` and `phy` and the added properties;
- adds no node beyond the regulator device;
- wires every supply as listed above;
- sets no reset GPIO and no BOB parent.

`dt-validate` is not installed. The properties were checked by hand against
`ufs-common.yaml`, `qcom,ufs.yaml` and `qcom,rpmh-regulator.yaml`. The node
name follows the `^regulators(-[0-9])?$` rule in `qcom,rpmh-rsc.yaml`.

## PHY tables

Final register maps were compared, last write wins. The module's FYG8
tables are rate A plus the 2nd lane (128 registers). Upstream `sm8450` uses
the `sm8350` tables. `ufs-qcom` powers the PHY up at the host's maximum gear
on controller major 4, so the G4 overlay applies.

| | Same | Differ | Module only |
| --- | ---: | ---: | ---: |
| Upstream, G4 overlay | 121 | 4 (TX `RES_CODE_LANE_OFFSET_TX/RX`, both lanes: stock 0x03/0x06 vs 0x09/0x09) | 3 (RX `GM_CAL` 0x0f on both lanes; PCS `POWER_DOWN_CONTROL`) |
| After `phy_render.py` | 127 | 0 | 1 (PCS `POWER_DOWN_CONTROL`, written by upstream power-on) |

The board-tuned stock values are what the module's links used in
ML054–ML065. The render (`47e941f3…` → `4b23baa0…`) changes only those
three table entries.

## Next: phase 4b (read-only probe)

1. **A stage module.** It must not open the arena. It:
   - applies the overlay with the four modules already loaded;
   - waits for probe and the LU scan, bounded at 120 s;
   - publishes the gate counters and probe state.
2. **Observer.** After the module, the observer reads LU0 LBAs 1–3 and LBA
   62,305,152 from `/dev/sdX` with O_DIRECT. The expected values are GPT
   `a0de4421…` and pattern `1155097a…`.
3. **Report and host decoder.** A new report version and its host decoder.
4. **The remaining pieces:** candidate, capability, review and run approval.

Per the operator's direction, contract text for the new effect class goes
in with the 4b adoption.

## Files

- Public:
  - `workspace/public/src/mainline/s22plus_ufs_upstream_h0/` (`g0q_ufs_gate.h`, `gate_render.py`, `phy_render.py`, `upstream_overlay.py`)
  - `tests/test_s22plus_ufs_upstream_gate_v1.py`
- Private: `workspace/private/outputs/s22plus-ufs-upstream-h0-20261128-1/`
  - `build_upstream_modules.py`, `phy_table_diff.py`
  - `modules-plain/`, `modules-gate-1/`, `modules-gate-2/`, `overlay-1/`
  - `phy-table-diff{,-g0q}.json`
