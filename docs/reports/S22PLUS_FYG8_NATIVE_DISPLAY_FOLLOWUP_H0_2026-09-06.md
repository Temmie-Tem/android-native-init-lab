# S22+ display follow-up: selection, providers and persistence

Target: SM-S906N / g0q / S906NKSS7FYG8. Date: 2026-09-06.
H0 only: retained firmware, raw evidence, source and ELF inspection. No device
command, module load, display ioctl, firmware transfer or P349 change occurred.
This follows the [initial display investigation](S22PLUS_FYG8_NATIVE_DISPLAY_RESEARCH_H0_2026-09-06.md).

## Result

Three questions advanced:

- **Recorded selection found:** retained boot evidence contains
  `msm_drm.dsi_display0=ss_dsi_panel_S6E3FAC_AMB655AY01_FHD:`.
  This is a recorded boot choice, not a fresh panel-bind observation.
- **Exact binary/provider CRC checks closed within the declared graph:**
  50 modules, 2,965 versioned imports, no missing files, CRC mismatches or
  ambiguous providers in that graph. This is not probe safety or live load proof.
- **CPU rendering has a source-supported write-combine route:** a vendor GEM
  allocation can request write-combine scanout memory rather than use the
  cached dumb-buffer default. Visible output remains untested.

A concrete hazard prevents treating the stock module as ready for the current
boot-only display experiment: it links persistent Samsung debug/parameter
services. A display error and even certain diagnostic sysfs reads can write a
partition; a dependency's probe can also write. Merely withholding `/dev/block`
nodes does not exclude that probe's device-number lookup fallback.

## Panel selection chain

`dsi_display.c:2765` parses `dsi_display0/1` up to the first colon and enables
the boot selection. During probe (`:6325`), an enabled selection finds the
named panel node under MDP and invokes Samsung panel initialization. Otherwise
it follows `qcom,dsi-default-panel`; with DSI parser configuration enabled,
absent boot selection can additionally request the `dsi_prop` firmware path.
`samsung_panel_initialize` in `ss_dsi_panel_common.c:8205` selects the compiled
panel implementation by the supplied name.

The exact parameter above was recovered from the already retained P349 first
D0 baseline capture, 2,097,136 bytes, SHA-256
`ccc108547e1260a1c37203507e2cfd87c8b99596ca879273b38a1e77621960ba`.
Its size/hash were rechecked against the preserved D0 stop receipt. That stop
still means the capture is **not a clean F1 baseline**. Finding a parameter in
it neither cleans that result nor proves a present display mode. The parameter
is consistent with the g0q DT panel declaration identified in the initial report.
No full command line, unique panel identifier or device identifier is published.

Still required for a later display proposal: bind the selected DT/boot inputs,
confirm the actual connector and mode through a separately scoped observation,
and avoid hardcoding the first panel declaration or `card0`.

## Exact module and declared provider graph

The earlier extracted `vendor_dlkm.img` was absent. The retained firmware ZIP
was streamed through its AP tar and LZ4/sparse layers, retaining only the
57,610,240-byte logical vendor_dlkm image. The existing LP geometry/table parser
was reused; the final partition SHA-256 matched the recorded
`e5386d68ccf9ad1a12cfa4cf447e704bddcef94b0442e61765f3dba580186b26`.
The full super image was not written to disk.

The existing bounded F2FS reader recovered `msm_drm.ko` and required providers.
Missing first-stage providers were recovered from the retained vendor_boot
ramdisk using the existing vendor-boot/LZ4/newc parsers. Every selected module
was hash-checked against the recorded module inventories. `msm_drm.ko` is an
AArch64 relocatable ELF, 11,733,384 bytes, SHA-256
`7b790074a73cd457d1f483c93e9abec040bca0b0cb07d9c71283b8d6bd396ec9`.

The exact P349 Image was checked against its recorded identity, and all five
export/string/CRC section ranges were checked against their existing byte pins.
The established PREL32 export decoder supplied provider CRCs directly from that
Image. An unrelated `vmlinux.symvers` was not accepted as authority.

| Check | Result |
| --- | ---: |
| Declared transitive graph, including display module | 50 modules, acyclic |
| Modules outside the current 73-module USB plan | 22 |
| All versioned imports in the graph | 2965 |
| Display-module imports | 758 |
| Display imports supplied by the exact Image | 684 |
| Display imports supplied by modules in the graph | 74 |
| Missing/ambiguous/CRC-mismatched imports within that graph | 0 |

The 22 additional names are `dev_ril_bridge`, `gh_arm_drv`, `gh_dbl`,
`gh_irq_lend`, `gh_mem_notifier`, `gh_msgq`, `gh_rm_drv`, `hdcp`, `lcd`,
`llcc-qcom`, `mem_buf_dev`, `msm-mmrm`, `msm_dma_iommu_mapping`, `msm_drm`,
`msm_ext_display`, `panel_event_notifier`, `qseecom-mod`, `sec_input_notifier`,
`sec_panel_notifier`, `sec_param`, `sec_qc_dbg_partition` and `smcinvoke_mod`.
This is a dependency inventory, **not a module-load instruction**.

This check does not yet qualify the union with every current USB module,
soft-dependency ordering, configuration/CFI behavior, actual driver binds,
IOMMU/power suppliers or module-probe effects. Adding all 22 is not established
as a minimal or safe display implementation.

## CPU-buffer route

The initial report's cache concern is narrowed:

- `msm_gem_dumb_create` uses `MSM_BO_SCANOUT | MSM_BO_CACHED`.
- `msm_ioctl_gem_new` accepts flags within `MSM_BO_FLAGS` and routes them to
  `msm_gem_new_handle`; `msm_gem_new_impl` explicitly permits `MSM_BO_WC`.
- `msm_gem_mmap_obj:226` uses `pgprot_writecombine` for a WC object. The UAPI
  defines both WC and scanout flags.
- The framebuffer preparation path obtains IOVAs. `msm_gem_sync` exists, but
  its located call sites are DSI command/reg-DMA buffers; that alone is not a
  general CPU scanout-buffer synchronization proof.

A minimal renderer should therefore evaluate explicit WC scanout allocation,
checked pitch/size arithmetic and a supported linear RGB format. Discover the
actual connector/CRTC/plane and properties, map the owned GEM buffer, draw a
fresh identifier/counter, validate the atomic state, then commit it. CPU write
ordering, buffer lifetime and completed presentation still require qualification.
Do not overwrite an actively scanned buffer and assume visibility; a bounded
two-buffer design can make distinct commits easier to verify.

No explicit input fence is needed by the proposed CPU-only design. In this
vendor source `_sde_plane_set_input_fence:590` treats **0** as no fence; generic
assumptions that `-1` is the correct property value must not be transplanted.
The eventual implementation must inspect and preserve the actual vendor
property semantics through every atomic commit.

## Persistent-effect findings and independent review

Independent reviewer `p349_safety_design_review` checked the following source
paths and conditions. This was a finding review, not capability PASS or authority.

| Path | Trigger and consequence |
| --- | --- |
| `sde_plane_wait_input_fence` -> `ss_inc_ftout_debug` | Non-NULL input fence times out; increments and writes debug-partition data. Exact display ELF relocations call `sec_qc_dbg_part_read/write`. |
| `ss_dpci_show` / `ss_dpci_dbg_show` -> `update_dpui_log` -> `dpci_notifier_callback` | A sysfs **read** clears and writes retained debug data. Broad sysfs collection is not read-only by assumption. |
| `ss_window_color_store` -> `sec_param_set` | Explicit attribute write changes parameter storage; keep outside the fixed interface. |
| `__qc_dbg_part_init_reset_header` | Provider probe writes an initialized reset header if the existing magic is absent. Avoiding input fences does not remove this trigger. |

The provider source is
`kernel_platform/msm-kernel/drivers/samsung/debug/qcom/dbg_partition/sec_qc_dbg_partition.c`.
It opens storage read/write and its write path reaches `generic_perform_write`
and synchronous completion. The recovered provider ELF contains the reset-header
initializer and calls its read/write implementations; its imports include
`blkdev_get_by_path`, `blkdev_get_by_dev`, `name_to_dev_t` and
`generic_perform_write`.

Probe first tries a block-device path, then falls back to `name_to_dev_t` and
`blkdev_get_by_dev`. Inspected g0q declarations use a PARTUUID-form selector;
`name_to_dev_t` can resolve it through registered block devices without a
filesystem node. Private selector values are intentionally omitted.

Exports return false when the provider's global state is absent, but that state
is published only after initialization. A late probe failure therefore does not
prove that initialization made no write. Similarly, `sec_param_set` can fail
without a write backend, but a backend may register later. Do not rely on a
momentarily unbound provider or an empty `/dev` as permanent containment.

These paths are outside the intended volatile screen witness. Before any live
design, prefer a source-built display configuration that removes persistent
debug/parameter dependencies, then rederive its exact symbol/probe closure.
Whether configuration switches alone suffice remains a question for that H0
build investigation. No permanent boundary is relaxed and no stock module is
loaded to test these effects.

## Evidence and remaining work

Private receipts, extracted files and scripts are under
`workspace/private/outputs/s22-display-followup/`. Final graph receipt:
`module-audit-final.json`, SHA-256
`95daf2e0c32ebc8a2b41c14dcb2c898dfadddcfa0cd3d1b57c18dd98a69ed8ea`.
It explicitly records no device contact or probe/runtime qualification.

The next useful H0 unit is a minimal display build with persistent diagnostic
paths removed, followed by exact provider/configuration checks and a small
CPU-renderer test design. The selected-panel and WC investigations now have
concrete source/retained-evidence support; actual native screen output remains
unproved. This research does not expand or resume P349.
