# S22+ mainline UFS handover to the upstream driver: design proposal (H0)

Status: **proposal, not adopted.** It grants no device authority. This is
step 4 of the operator's UFS roadmap. Steps 1–3 are closed:
- the 60-second floor (ML056);
- one persistent write, read back by stock Android and by later mainline boots (ML060–ML061);
- four of four healthy stability runs (ML062–ML065).

## Goal and end state

The end state is the generic kernel stack: `ufshcd` with `ufs-qcom` and the
QMP UFS PHY driver, then SCSI, `sd` and block devices. Once that runs, a
partition can be mounted read-only and later writable. That is the
precondition for a UFS-backed Debian root.

The fixed module's private UTP engine was always a probe. It cannot become a
block driver without rewriting `ufshcd`: queues, multiple slots, interrupts,
error recovery, power management and SCSI host registration.

## What carries over from the module

These facts were measured on this phone and become inputs to the upstream
configuration:

| Fact | Source run |
| --- | --- |
| Rails:<br>• vcc = L7B 2.504 V<br>• vccq = L9B 1.2 V<br>• vdda-pll = L6B 1.2 V<br>• parent S12B 1.256 V<br>• vdda-phy = L5B 0.88 V (shared with USB) | late overlay, ML054+ |
| Core and UniPro clocks at 300 MHz; GCC symbol-clock selectors 161/163/165 | ML054+ |
| SMMU stream `0xe0`, `dma-coherent`; the kernel blocks unmatched streams | ML057+ |
| The link starts first time; HCS 0x8→0xf; only PA LINERESET in the error log | ML054–ML065 |
| First TEST UNIT READY returns CHECK CONDITION, Target Failure and UNIT ATTENTION (ASC 0x29); one repeat passes | ML059–ML065 |
| LU0:<br>• 62,305,280 blocks of 4096 bytes<br>• GPT LBAs 1–3 match `a0de4421…` | ML059+ |
| Inline crypto off; plaintext raw reads equal stock Android's raw read | ML060 phase 2c |
| LBA 62,305,152 holds the `1155097a…` pattern | ML060–ML065 |

The pattern block is a continuity check. The first upstream run must read
the same bytes through `/dev/sdX`.

## Current kernel (floor Image `5139aab5`, Linux 7.2.11)

**Already built in:**
- `SCSI`, `BLK_DEV_SD`, `EFI_PARTITION`, `EXT4_FS`, `DEVTMPFS`;
- `REGULATOR_QCOM_RPMH`, `INTERCONNECT_QCOM_SM8450`, `SM_GCC_8450`, `PINCTRL_SM8450`, `ARM_SMMU`;
- `GENERIC_PHY`, `RESET_CONTROLLER`, `PM_DEVFREQ`, `DEVFREQ_GOV_SIMPLE_ONDEMAND`, `NLS`.

Those are everything `SCSI_UFSHCD`, `SCSI_UFS_QCOM` and `PHY_QCOM_QMP_UFS`
select or depend on.

**Off today:**
- `SCSI_UFSHCD`, `PHY_QCOM_QMP_UFS`, `SCSI_UFS_CRYPTO`, `SCSI_UFS_BSG`;
- `RPMB`, `BLK_SED_OPAL`, `SCSI_SCAN_ASYNC`.

**Device tree.** `sm8450.dtsi` has both `ufshc@1d84000` and `phy@1d87000`,
disabled. The in-tree `sm8450-samsung-r0q.dts` does not enable UFS, so
there is no upstream board precedent to copy.

## Architecture (recommended)

1. **The upstream drivers as loadable modules.** Build `ufshcd-core`,
   `ufshcd-pltfrm`, `ufs_qcom` and `phy-qcom-qmp-ufs` with `=m`. Their
   dependencies are already `=y`, so the **Image is expected to stay
   `5139aab5`**, along with its symvers and transport records. H0 must
   confirm this by rebuilding. If the Image changes, this becomes a kernel
   rebuild and the transport records need restaging.
2. **Late enable, same posture as today.** The authenticated 60-second
   witness and permit gate the step, as they do now. The witness still
   requires zero block devices. A small fixed stage module then:
   - registers the rails;
   - applies the late overlay, which sets the upstream nodes `okay`;
   - waits a bounded time for probe and scan to settle;
   - reports.

   The upstream modules are loaded before the overlay, so no probe can run
   before the permit.
3. **The upstream compatibles and bindings unchanged.** The overlay supplies:

   | Property | Value |
   | --- | --- |
   | `vcc-supply` | L7B |
   | `vccq-supply` | L9B |
   | PHY `vdda-phy-supply` | L5B |
   | PHY `vdda-pll-supply` | L6B |
   | `reset-gpios` | the dedicated `UFS_RESET` pad (H0 binds the TLMM line to the module's `0x0f1de000` window) |
   | `iommus` | `0xe0` |
   | `dma-coherent` | present |
   | `freq-table-hz` | from the dtsi (300 MHz max) |

   An overlay cannot delete the dtsi's `qcom,ice`. With
   `SCSI_UFS_CRYPTO=n`, `ufs_qcom_ice_init` is a stub. The ICE node also
   has no driver, so the design touches no ICE or SCM key path.

**Rejected alternatives:**
- **Hand a live link from the module to `ufshcd`.** `ufshcd` always enables
  the host itself and runs its own link startup, so it cannot attach to a
  running link.
- **Build the drivers into the kernel.** This changes the Image and every
  transport record. It buys nothing over modules plus a late overlay.

**Supply gap.** Upstream has no consumer for S12B's 1.256 V seed. The module
used its own "parent" consumer for that. Two options:
- declare S12B as the L6B/L9B parent with min = max 1.256 V, so the regulator core applies the voltage at registration;
- keep the module's seed in the stage module.

H0 picks one by reading the rpmh-regulator registration path.

## The write gate (the safety piece)

Upstream `ufshcd` issues device writes that the fixed module never did. In
the 7.2.11 `drivers/ufs/core/ufshcd.c`:

| Function | Query write | Persistence |
| --- | --- | --- |
| `ufshcd_complete_dev_init` | set `fDeviceInit` | already done by every V14+ run |
| `ufshcd_set_dev_ref_clk` | `bRefClkFreq`, only if it differs from the host's | persistent device config |
| `ufshcd_set_active_icc_lvl` | `bActiveICCLevel` | device config |
| `ufshcd_set_rtt` | `bMaxNumOfRTT` (UFS 4.0+ only) | device config |
| `ufshcd_set_timestamp_attr`, `ufshcd_update_rtc` | `qTimestamp`, `dSecondsPassed` | volatile |
| `ufshcd_force_reset_auto_bkops` | set/clear `fBackgroundOpsEn` | flag |
| `__ufshcd_wb_toggle`, `ufshcd_wb_set_resize_en` | WriteBooster flags and attributes | flag/attr |
| `__ufshcd_write_ee_control` | `wExceptionEventControl` | volatile |
| `ufs-txeq.c` | TX EQ settings ("valid settings are stored") | stored |
| `ufshcd_wl_shutdown`, suspend | START STOP UNIT to the device W-LU | power state |

The generic SCSI layer issues no media writes during scan. Without a gate,
though, nothing would prevent one later.

**Proposal: one compiled-in gate patch in `ufshcd-core`.** It sits at the
two choke points: SCSI submission (`ufshcd_queuecommand`) and query
submission. Everything is denied unless listed:

| Class | Allowed in 4b/4c |
| --- | --- |
| SCSI, any LU | TEST UNIT READY, REQUEST SENSE, INQUIRY, REPORT LUNS, READ CAPACITY(10/16), MODE SENSE(6/10), READ(6/10/16) |
| SCSI, device W-LU only | START STOP UNIT (the stock shutdown path) |
| SCSI, any LU | SYNCHRONIZE CACHE (nothing is dirty, since no write is allowed) |
| Query | all reads; set `fDeviceInit` |

Every refusal fails the command with an error and increments a per-opcode
(or per-IDN) counter, which the report carries. Upstream already handles the
refusals the design cares about as non-fatal:
- `ufshcd_set_dev_ref_clk` logs and continues;
- the ICC level and timestamp writes are void and only log.

H0 must confirm by reading the code that no refusal makes probe fail. Any
that does is decided on evidence: allow it, or keep the refusal.

**Capabilities.** The same patch clears the capabilities `ufs-qcom` sets:
- `CLK_GATING`, `HIBERN8_WITH_CLK_GATING`;
- `CLK_SCALING`, `WB_WITH_CLK_SCALING`;
- `AUTO_BKOPS_SUSPEND`, `WB_EN`, `AGGR_POWER_COLLAPSE`.

So there is no low-power transition and no clock or rail change after probe
until shutdown.

**Configs stay off:** `SCSI_UFS_BSG` (raw UPIU from userspace), `RPMB`,
`BLK_SED_OPAL`, `SCSI_UFS_CRYPTO`. The RAM root has no udev and no
automount.

The gate is the one place a later phase opens writes, for example to one
partition's LBA range. It is small enough for fixture tests, like
`ufs_storage.c`.

## RPMh authority (decision needed)

Today the four UFS rails pass through a private arena. It is one-shot,
bound to the issuing task, and closes 15 s after `g0q_rpmh_begin`. ICC is
covered by the held USB votes. Upstream breaks those assumptions:
- `ufshcd` probes in the module's context, but scans from an `async_schedule` worker;
- `ufs-qcom` votes interconnect bandwidth (`ufs-ddr`, `cpu-ufs`) at init and at the gear change;
- shutdown changes rails again.

**Recommendation.** Replace the issuer binding with a fixed-resource,
fixed-value rule:
- only these four rails, at their exact voltages, modes and loads;
- only the two UFS ICC paths;
- from any context;
- from the permit until the attended return.

The ordinary USB voting stays as it is. This is a change to the common
transport scope, so it needs operator approval.

## Phases

| Phase | Device effect | Done when |
| --- | --- | --- |
| **4a, H0** | none | The Image is unchanged with `=m`, or the restage is planned. The overlay passes `dtbs_check` against the upstream bindings. A gate fixture test covers every row above. The module's PHY tables are diffed against upstream `phy-qcom-qmp-ufs` SM8450 tables. The probe path is read for refusal tolerance. |
| **4b, read-only probe** | Upstream probe, link, HS gear change, LU scan; SCSI reads only; gate on | The SCSI host is registered. `sda`… appear. LU0's capacity is exact. LU0's GPT LBAs 1–3 match `a0de4421…`. LBA 62,305,152 = `1155097a…` (read with O_DIRECT). The gate reports zero allowed writes. Android closes healthy. |
| **4c, read-only mount** | `mount -o ro,noload` of one ext4 partition (`native_data`); gate still on | The mount succeeds and a fixed file list's digests match. The gate reports zero writes. |
| **4d, writable mount** | gate opens WRITE only inside the chosen partition's LBA range | Separate contract and approval. Out of scope here. |

The first 4b run uses upstream's negotiated maximum gear. If the gear change
fails, the report shows it, and the next run sets `limit-hs-gear`
(supported by `ufshcd-pltfrm`). 4b and 4c can run as one series of up to
four steps.

## Report and host verification (4b)

The stage module and the observer produce a new report version. It
carries:
- probe rc;
- link and gear (`PA_PWRMode`, gear, lanes);
- the SCSI host number;
- the LU count and sizes;
- the LU0 GPT digest and the test block digest;
- gate counters (allowed and refused per class);
- the `ufshcd` error-handler count;
- the settle time.

The host checks:
- the digests against the pinned GPT and pattern;
- that the allowed-write counter is zero;
- that the block devices appeared only after the permit.

The ordinary return, the Download control, original A and final health are
unchanged.

## Timing

The fixed module's 15-second budget does not fit the upstream driver. Its
probe, link, gear change and LU scan normally take a few seconds, and SCSI
timeouts are 30 s. Proposal: a 120-second settle bound from overlay apply,
inside the existing 540-second ceiling. The report is published at settle
or at the bound, whichever comes first.

## Contract changes needed

- **Common.** A new UFS effect class: the generic driver stack under the
  write gate. This covers:
  - the upstream link and HS gear change;
  - LU discovery;
  - block devices after the permit;
  - read-only SCSI;
  - the W-LU START STOP UNIT at shutdown;
  - read-only mount (4c).

  Also needed: the RPMh authority change above. Permanent boundary 2 stays
  closed to writes; 4d needs its own exception.
- **UFS link policy.** The ML030 sentence "the generic UFS host/PHY/ICE
  drivers and their SCSI discovery path stay disabled" is superseded for this
  class. ICE stays disabled.
- **Code.** About 150–250 lines:
  - the gate patch;
  - the overlay renderer;
  - the stage module (rails, overlay, settle, report);
  - the new report decoder;
  - a gate fixture;
  - build scripts for the four modules.

## Hazards

- **Device config writes.** The gate refuses them, and its counters prove
  the refusal per run.
- **Error-handler storms.** Host reset, device reset through the reset pad,
  and retries are bounded by the settle bound and the 540-second ceiling.
  Download recovery is unchanged.
- **Shutdown path.** `restart2("download")` now runs the `sd` and `ufshcd`
  shutdown: SYNCHRONIZE CACHE, then START STOP UNIT. That is the stock
  reboot behaviour, but it adds time before the reset. Qualification must
  time it.
- **The HS gear change is new hardware ground.** The module only ran in the
  slow default mode. If it fails, that costs a run, not data.
- **Shared rails.** L5B is shared with USB, and S12B is a parent rail.
  Fixed values only. Never a voltage change on L5B, which the module already
  refuses.

## Open questions for the operator

1. Approve the architecture: upstream drivers as modules plus a late
   overlay, with the Image unchanged if H0 confirms it?
2. Approve the write gate as the safety mechanism? It allows reads, the
   `fDeviceInit` set, and START STOP UNIT to the W-LU at shutdown.
3. Approve the RPMh authority change: fixed UFS resources from any context
   until the return, in place of the 15-second issuer arena?
4. Which partition is the read-only mount target in 4c? `native_data` is
   recommended (the existing ext4 Debian root).
