# P352 initial-plane investigation — H0 only

The retained P352 stop is compatible with the vendor continuous-splash producer:
it can attach a plane to a CRTC without assigning a DRM framebuffer. The actual
failed plane tuple was not logged, so this is a source- and binary-supported
explanation, not proof that the live conflicting plane belonged to splash.

A separate finding affects the next handoff design: the vendor atomic duplicate
callbacks modify the old splash state before allocation can fail. A first
`TEST_ONLY` request cannot be assumed to preserve that bookkeeping. P352 stopped
before buffer allocation and atomic submission; this later path did not cause
its observed renderer failure.

Scope: retained evidence, private vendor/kernel source, exact consumed module
disassembly, source-function H0 fixtures, and historical A90 comparison. No
device command, candidate preparation, production change, guard relaxation or
consumed-state edit occurred. P352 remains CLOSED/19, NO_PROOF, rollback verified.
See the [closed result and timeline](S22PLUS_FYG8_P352_SOURCE_BOUND_DISPLAY_H0_2026-09-07.md).

## What the retained run establishes

All twelve insertions and readiness passed. The renderer observed `msm_drm`,
thirteen modes and one exact selected 30HS match, then exited 1 at 200 ms with
`competing-plane`. The initial-state guard runs before buffer creation and any
atomic test or frame submission. The operator saw only the boot logo.

The selected connector/CRTC/plane IDs are not the rejected plane's tuple. Neither
the retained child output nor the rollback observer captures supplies that
missing tuple. The two retained rollback captures are byte-identical; their two
XBL splash-enabled messages do not identify Linux plane assignments or prove
the failed plane's owner. Static catalogs and DT cannot recover the actual
hardware pipe bitmap from that boot.

## Continuous-splash producer and GETPLANE

Private vendor source base:
`workspace/private/outputs/s22-display-build-h0/display-drivers/msm/`.
Private core DRM source base:
`workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/kernel_platform/common/drivers/gpu/drm/`.

| Source site | Established behavior |
| --- | --- |
| `msm_drv.c:903–909` | Mode-config reset and DRM registration precede continuous-splash configuration. |
| `sde/sde_kms.c:3254–3307`, `_sde_kms_update_planes_for_cont_splash` | Validated physical/virtual pipe membership and source address lead to plane CRTC assignment, CRTC plane-mask insertion and the splash flag; this producer does not assign a framebuffer. |
| `sde/sde_kms.c:3449–3630` | Splash configuration establishes CRTC/mode and connector/encoder routing and invokes the plane producer. |
| Core `drm_plane.c:522–574`, `drm_mode_getplane` | CRTC and framebuffer IDs are read independently from atomic plane state; CRTC visibility also depends on the lease. A nonzero CRTC with zero FB is representable. |
| `sde/sde_rm.c:2090`, `sde/sde_hw_ctl.c:935–970` | Staged physical/virtual pipe membership comes from CTL layer registers. Catalog primary-plane selection alone does not identify inherited ownership. |

The actual P352 guard permits its selected plane with zero FB but rejects another
plane attached to the selected CRTC, even if that other plane has zero FB.
Consequently, the vendor producer supplies a concrete route to the observed
guard rejection without proving which route occurred live. Zero FB is not a
sufficient criterion for ignoring an attached plane.

## First atomic request changes old splash bookkeeping

The normal duplicate-state contract is to copy current state into temporary
state that can be checked and discarded. The core documentation describes that
interface and temporary-state cleanup; it is context, not evidence about this
Samsung binary. [Linux 5.10 DRM KMS documentation](https://www.kernel.org/doc/html/v5.10/gpu/drm-kms.html).

In the inspected vendor implementation:

- `sde_plane.c:4411–4414`: the duplicate callback clears the **old** plane's CRTC
  and splash flag before calling the state allocator.
- `sde_crtc.c:4306–4313`: it clears the **old** CRTC plane/connector/encoder masks,
  enable and splash flag before allocation; active/mode are retained there.
- `sde_connector.c:1425–1428`: it clears the **old** connector's CRTC and splash
  flag before allocation.

Core `drm_atomic_uapi.c:988–1017,1389–1426` reaches these duplicate callbacks
during property parsing, before choosing the `TEST_ONLY` branch. Temporary-state
cleanup in `drm_atomic.c:155–209` does not restore those old-object mutations.
The same limitation applies to the inspected allocation-error path and the
state-clear/backoff path for `EDEADLK`; this does not prove a live deadlock.

Core `drm_atomic.c:1229–1246` collects affected planes from the old CRTC plane
mask. Since the vendor duplicate can already clear it, a successor cannot rely
on that helper alone to include every inherited plane. Actual splash resource
release is in the vendor real complete-commit path (`sde_kms.c:1575` and
`1279–1310`), not the test-only cleanup path. Bookkeeping changes and hardware
handoff completion therefore require separate qualification.

This proves a software-state mutation relevant to first-commit design. It does
not establish panel failure, memory corruption, successful handoff, or an
automatic recovery capability.

## Exact module and bounded executable checks

The inspected consumed `msm_drm.ko` is `10534768` bytes, SHA-256
`f4e5e9f5cf737f6e128e3bd904f3cadcb961552aa8a2ade86d2b94e01b2239e4`.
Its identity matches the retained P352 module binding. AArch64 disassembly
confirms the producer's CRTC/mask/flag stores and all three old-state clears
before allocation. Core GETPLANE/atomic paths were source-inspected; they were
not independently disassembled from the kernel Image. All eleven modified
vendor build inputs also match the retained final-input receipt.

The private H0 fixture executes the full source splash-plane producer, full
GETPLANE function and unchanged renderer guard with synthetic kernel objects,
pipe masks, addresses and lease behavior. Four bitmap cases cover no inherited
plane, selected-only, other-only and both planes. Additional cases cover address
exclusion and the three actual duplicate-function prefixes through allocation
failure. All eight recorded cases pass. The non-splash plane control retains its
old CRTC; splash allocation failures retain the demonstrated old-state changes.

Host compilation with warnings as errors, fixture execution, AArch64 object
compilation and `file` inspection passed; the private generator passes
`py_compile`. Synthetic layouts and stubbed address validation are not kernel
ABI or hardware validation. Success tails, complete atomic ioctls, TEST_ONLY
cleanup, resource release and recovery are not emulated by this fixture.

Independent source and binary review returned
`PASS_H0_ANALYSIS_NOT_HANDOFF_QUALIFIED`, with no blocking finding for this
analysis. It independently checked the fixture and key binary stores. This is
not a successor capability PASS_GO.

## What the early A90 work contributes

Historical commit `0731e5d0fc` retains `stage3/linux_init/init_v17.c` and later
versions. V17 uses a connected connector/encoder/CRTC, creates and maps a dumb
buffer, registers a framebuffer and submits the initial image with legacy
`SETCRTC`. V25 adds the two-buffer `ADDFB2`/page-flip path. Neither inspected
version inventories competing planes with GETPLANE or uses atomic TEST_ONLY.
The retained V72 source at `dc853fe0a0` continues the legacy initial SETCRTC path;
its historical report records bridge/display-test behavior, not new physical
screen verification in this investigation.

That history identifies a useful first-frame route to compare. It does not
establish S22+ compatibility: the S22+ CRTC callbacks in `sde_crtc.c:6973–6988`
bind legacy set-config/page-flip to atomic helpers. Core
`drm_atomic_helper.c:3011–3031` calls `__drm_atomic_helper_set_config` and atomic
commit; `drm_atomic.c:1481–1554` obtains the CRTC and primary-plane states through
the same duplicate machinery. Switching to SETCRTC therefore does not bypass
the discovered splash bookkeeping. Historical retry and DRM-master tolerance
were not ported. No A90 or S20+ device was contacted.

## Next bounded H0 unit

Design the first display handoff around a complete initial plane snapshot and
explicit handling of every relevant inherited attachment. Cache and report the
exact rejected plane/CRTC/FB tuple before any mutating ioctl. Distinguish a
qualified splash state from unrelated or unexplained ownership; do not accept
all zero-FB attachments or merely remove the existing guard.

Qualify successful first commit and disable, allocation/validation failure,
and TEST_ONLY followed by real commit against the actual vendor duplicate and
resource-release behavior. Determine the smallest implementation from those
results; this report does not choose an unqualified ioctl sequence or require a
kernel patch. A fresh candidate and device run remain separate work. P352's
consumed approval and journal cannot be reused.

Private evidence is under
`workspace/private/outputs/s22plus_fyg8_p352/plane-state-audit-20260907/`:
`research-audit.json` is `9586B`, SHA-256
`88a10882369b7304e39e9e56b2270be11bd6532c8f80d902d1569575797acbe9`.
It binds the inspected inputs, private source-function fixture, disassembly,
historical A90 extracts and independent review. Original vendor sources, raw
captures and disassembly remain private.
