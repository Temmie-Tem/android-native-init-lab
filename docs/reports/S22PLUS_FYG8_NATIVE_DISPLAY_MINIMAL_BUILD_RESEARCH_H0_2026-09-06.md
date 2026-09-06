# S22+ FYG8 minimal display build research — H0

Date: 2026-09-06. Target: SM-S906N / g0q / S906NKSS7FYG8.
Status: research complete; reduced module build and native display remain unproved.

## Scope and conclusion

Follow-up to [the binary, panel and cache investigation](S22PLUS_FYG8_NATIVE_DISPLAY_FOLLOWUP_H0_2026-09-06.md).
The next useful unit is an isolated vendor display-module build with persistent
Samsung diagnostic paths removed, retaining the existing kernel identity where
compatible. This is a build hypothesis, not a qualified configuration. No device
command, module load, renderer execution, candidate change or activation occurred.
P349 remains separate and paused; other targets were untouched.

## Current-source findings

The source root is the retained private P290 worktree's
`vendor/qcom/opensource/display-drivers/`. Ten current source hashes are recorded
in `workspace/private/outputs/s22-display-followup/minimal-build-source-identities.json`.
This receipt identifies inspected bytes, not equivalence to the stock binary.

- `msm/Kbuild` selects both `config/gki_waipiodisp.conf` and its forced
  `gki_waipiodispconf.h` for the non-VM Waipio branch. Both enable DP and HDCP.
  A make-variable change alone therefore does not demonstrate matching C gates.
- Kbuild also includes Samsung panel configuration and a common header that
  defines `CONFIG_DISPLAY_SAMSUNG`. Its common object list includes debug,
  sysfs, POC and SPI. Disabling DP/HDCP alone cannot remove the earlier proven
  Samsung persistence paths.
- `ss_dsi_panel_debug.c:1265` places partition helpers and `ss_register_dpci`
  under `CONFIG_SEC_DEBUG`, but the call at line 1377 is under
  `CONFIG_SEC_PARAM`. Turning off only SEC_DEBUG while retaining SEC_PARAM
  leaves a source-level definition/call mismatch. Both gates must be considered
  together; effective preprocessing and linking remain necessary.
- `ss_dsi_panel_sysfs.c:654` contains a file-backup write inside `#if 0`.
  That text is unreachable in this source configuration and is not counted as
  an active write hazard. The previously verified debug/parameter paths remain
  distinct findings.
- `ss_ddi_poc_common.c` contains erase/write dispatch and a write file operation.
  The selected AMB655AY01 source search finds a `read_flash` assignment, without
  a POC writer assignment in that file. This does not establish selected-panel
  NVM write reachability or its absence: common/indirect registration still needs
  examination before claiming a persistence-free result.

## Smallest proposed implementation unit

1. Use an isolated source/output location; preserve P349 inputs. Reconstruct the
   exact kernel build interface, generated headers, toolchain and provider symbol
   data. The display Makefile supports an external module build through KERNEL_SRC
   and M, but that alone does not establish a ready or compatible build environment.
2. Remove the two diagnostic persistence paths coherently at the display consumer,
   checking both built-in and module forms of configuration macros. Keep kernel
   structure layout and ABI assumptions explicit; do not globally rewrite the
   existing kernel configuration to silence imports.
3. Keep DSI/SDE and the selected panel. Treat DP, HDCP, writeback, VM and diagnostic
   facilities as reduction candidates, not a proven removable list. Pair make
   configuration with forced headers and resolve reachable shared references.
   POC/SPI removal or constrained dispatch needs its own reachability evidence.
4. Compile and inspect the resulting AArch64 module; inspect effective gates,
   imports and reachable code. Recompute provider closure against the exact Image
   and the combined USB/display plan. The stock 50-module audit does not qualify
   a rebuilt module or that combined plan. Review changed execution-critical code
   before any later device qualification.

No reduced build was attempted here. Available workspace space was approximately
2 GiB; full-kernel rebuilding is not justified for this source question. Prepared
headers and symbol data were not established by this investigation. Build success,
ABI/CFI compatibility, provider initialization and runtime health are still open.

## Public material checked

- [Linux 5.10 KMS documentation](https://docs.kernel.org/5.10/gpu/drm-kms.html)
  describes framebuffer, plane, CRTC and connector relationships. It supports the
  generic KMS design, not this Samsung panel's successful initialization.
- [Linux DRM userspace API](https://www.kernel.org/doc/html/latest/gpu/drm-uapi.html)
  describes node roles and atomic interface behavior. Current upstream guidance
  must be checked against the retained vendor UAPI; it is not an FYG8 contract.
- [AOSP libdrm modetest source](https://android.googlesource.com/platform/external/libdrm/+/refs/heads/main/tests/modetest/modetest.c),
  observed blob `d9e761e6cfa001b5fb3d4bb2932dc76ffed917a5`, supplies resource,
  property and modesetting examples. It is a renderer reference, not an approved
  command to run on the target or a substitute for vendor buffer/fence semantics.
- [samsung-sm8450-kernel vendor sources](https://github.com/samsung-sm8450-kernel/vendor_qcom_opensource)
  expose a display-drivers tree on lineage-19.1. This is useful related source;
  no byte identity with SM-S906N FYG8 was established. It does not replace the
  retained Samsung source and extracted-module provenance.

The search did not establish an exact FYG8 native-PID1 display recipe. Public
examples reduce renderer design work, but leave the vendor module problem open.

## Renderer and proof remaining after build qualification

Use the previously identified WC allocation path as a candidate, two owned
buffers, runtime-discovered compatible objects/modes/formats and explicit commit
completion. TEST_ONLY is not a displayed frame; nonblocking return is not completion.
Preserve exact vendor fence semantics. Do not infer a usable mode from DT alone.
A visible run marker plus changing counter must be correlated with authenticated
same-boot PID1 evidence. A supervised helper would show PID1-managed output, not
prove that PID1 itself issued the display calls. Helper isolation cannot recover
an arbitrary kernel display stall. No unattended live authority follows.

## Validation and independent review

A read-only independent review found no material overclaim in the paired-gate,
forced-common-object and POC reachability conclusions. It explicitly retained
preprocessor/binary verification as future work and rejected treating source
configuration as live safety proof. Documentation links and diff checks apply;
there is no build/test PASS or device PASS from this research.
