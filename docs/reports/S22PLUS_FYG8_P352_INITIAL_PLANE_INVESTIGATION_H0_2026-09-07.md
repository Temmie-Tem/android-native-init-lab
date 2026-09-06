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

## Initial proposed H0 unit (superseded by the narrower follow-up below)

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

## Follow-up: one static first frame

The operator narrowed the functional objective to an observable transition from
the boot logo to one identifiable static image. A counter sequence, buffer
alternation, completed display disable and post-display USB response are not
success criteria for that first-frame proof. Physical Download entry by the
operator, exact rollback and final health remain separate run outcomes. This
follow-up investigates that narrower design; it does not change the consumed
P352 contract or activate a successor.

### Result and proposed first submission

The source supports a fresh one-buffer, one-blocking-atomic-commit design without
a preceding userspace TEST_ONLY ioctl. It provides a concrete implementation
direction; actual vendor validation and visible hardware output remain unproved.

1. Before the first atomic request, cache the complete bounded initial
   connector/CRTC/plane topology and relevant properties. Record each plane's
   ID, CRTC and FB, including the exact object rejected by any guard.
2. Bind one selected primary CRTC/connector/plane in the fresh native-driver
   context. Reject other active CRTCs, unexpected connector attachments and
   nonzero inherited FBs. Zero-FB attachments to the selected CRTC form the
   explicitly handled inherited set; zero FB alone is not proof of splash
   ownership. Do not silently ignore that set or infer it from the selected ID.
3. Allocate and paint one ordinary WC scanout buffer, then create a fresh mode
   blob for the already selected exact returned timing. Resolve and validate
   all properties before submitting the atomic request.
4. Submit the complete desired state once, with the CRTC first, then connector,
   then every relevant plane. Include the selected plane once; explicitly
   detach the other inherited planes in this same transaction. There is no
   separate blank-screen transaction before drawing.
5. Use `DRM_MODE_ATOMIC_ALLOW_MODESET` without TEST_ONLY, NONBLOCK or a requested
   page-flip event. Preserve the submitted bytes and returned status. On error,
   stop the display attempt without another userspace atomic request; the
   kernel's existing internal lock-backoff behavior is not a new user retry.
6. Keep the DRM fd, FB, GEM and mapping owned during the attended observation
   window. The operator's observation of the unique image proves first output;
   the run then uses physical Download entry and ordinary exact rollback.

| Atomic object | Desired properties |
| --- | --- |
| Selected CRTC, first | Fresh `MODE_ID`, `ACTIVE=1` |
| Selected connector | `CRTC_ID` set to selected CRTC |
| Selected primary plane | New `FB_ID`, selected `CRTC_ID`, source origin zero, source dimensions in 16.16, destination origin zero and full 1080x2340 dimensions |
| Each other inherited plane on that CRTC | `FB_ID=0`, `CRTC_ID=0` |

No additional mandatory scalar property was found in the inspected path beyond
the normal mode/routing/FB/rectangle set. The selected plane must still advertise
the format and compatible CRTC. Source defaults are primary `zpos=0`, alpha 255,
no color fill and nonsecure framebuffer translation; validate the expected
first-boot properties rather than relying on arbitrary inherited application
state. This is not proof that every live hardware configuration will pass.

### Why TEST_ONLY is unnecessary for this proposed sequence

Core `drm_atomic.c:1344–1355` calls `drm_atomic_check_only()` before the real
driver commit. That check includes core plane/CRTC/connector validation and
`mode_config.atomic_check`; vendor `msm_drv.c:163–180` routes to the KMS check.
Omitting a separate TEST_ONLY ioctl therefore retains these checks while
avoiding a separate duplicate/discard cycle before the real request. Property
parsing can still change old splash bookkeeping even when validation fails;
the previous failure/no-retry limitation remains.

The CRTC-first order lets its duplicate clear the old masks before the connector
and plane setters rebuild the new masks. Core `drm_atomic_uapi.c:116–162` sets
enable from the fresh mode blob, `298–340` inserts the connector into the new
connector mask, and `179–216` inserts the selected plane into the new plane mask.
The source-bound fixture reproduces those attachment-mask effects. It also
demonstrates the negative control: omitting an inherited plane can leave that
plane's old attachment stale even though the new CRTC mask contains only the
selected plane.

### How the old image is excluded from hardware composition

Explicit nulling does not guarantee a per-plane hardware disable callback here.
The vendor duplicate has already cleared the old CRTC, and the new CRTC for an
excluded plane is also NULL. Core `drm_atomic_helper.c:2533–2573` may skip that
plane under the `DRM_PLANE_COMMIT_ACTIVE_ONLY` flag used by `msm_atomic.c:586–587`.

The relevant hardware path is instead the CRTC blend rebuild. After state swap,
`sde_crtc.c:1582–1653` walks the current CRTC's planes and derives stages from
their pipe IDs. `sde_crtc.c:1839–1877` zeroes stage configuration, reconstructs
it from that set, marks mixer flush and invokes `setup_blendstage`.
`sde_hw_ctl.c:894–928` constructs four fresh CTL words and writes all four layer
registers. This is a replacement of the selected mixer's composition, not an
OR into retained hardware stage assignments. Encoder kickoff connects the
pending configuration to flush/start (`sde_encoder.c:4086–4136`).

In the same exact consumed module, disassembly confirms stage-config clearing
before the blend-builder call, zero initialization of the four CTL words and
four `sde_reg_write` calls. That corroborates the source operations; it does not
prove actual flush delivery, hardware latch, pipe mapping for the missing live
tuple or successful panel output. Splash resource release remains in the real
complete-commit path described above.

### Buffer and visible-proof details

The existing linear XRGB8888 allocation can remain: 1080x2340 pixels, pitch 4352
bytes, one buffer of 10183680 bytes. `msm_fb.c:300–317` requires a final accessed
span of 10183648 bytes, which fits. The exact linear-layout helper accepts the
padded pitch; `msm_gem.c:226–227` selects the WC mapping. The actual plane still
performs framebuffer layout/address preparation, including deferred SMMU work
when applicable (`sde_plane.c:1983–2047,781–807`); H0 does not establish that live
mapping succeeds.

A plain white screen is insufficiently specific: the vendor can force a white
plane on error (`sde_plane.c:2790–2795`). Use a fixed recognizable multicolor
pattern with a large static mark. The proof is that particular image replacing
the logo, not merely any brightness or color change. It does not require a
counter, refresh sequence or USB confirmation.

Blocking is also not a display-success witness. `msm_atomic.c:699–713` waits for
worker completion or executes the synchronous fallback, but
`sde_kms.c:1625–1630` handles some commit-done failures internally without
returning them as the ioctl errno. Report ioctl acceptance and operator-visible
output separately.

Resource retention needs no repeated drawing or new service. The successful
renderer must retain its existing resources during observation instead of
immediately returning or running the old cleanup. Closing the DRM file invokes
`drm_fb_release` (`drm_file.c:274`, `drm_framebuffer.c:774–807`), which can remove
an active FB through an atomic update (`1083–1116`). The existing child deadline
must be reconciled with that observation/physical-return window when implementing
the successor. This is not an indefinite-residency claim or a new requirement
to prove timed display retention.

### Validation and remaining work

Nine new bounded H0 cases pass: four inherited masks, an omitted-plane negative
control, real-commit wrapper reject/accept ordering, full CTL register replacement,
and linear format/pitch/span. Host warnings-as-errors compilation, execution,
AArch64 compilation, `file` inspection and generator `py_compile` pass. The
fixture uses exact core setters, commit wrapper, vendor mutation blocks, CTL
write function and linear-layout helper. Object layouts, duplicate success copy,
mode assignment, CTL encoding and the check result are synthetic or stubbed;
full atomic validation, SMMU, flush/latch and panel behavior are not emulated.

Independent review returned `PASS_H0_DESIGN_EVIDENCE_NOT_HANDOFF_QUALIFIED` and
confirmed the mask-to-stage-to-CTL source chain with the ACTIVE_ONLY and blocking
return limitations above. The nine fixtures were independently checked. This
is design evidence, not a capability PASS_GO or a successful display run.

The remaining work is implementation and scoped qualification of the fresh
static-image successor. Its contract, renderer and observer must use the newly
agreed visual success criterion instead of P352's ten flips, completed disable
and post-display USB requirement. That implementation must receive the required
changed-closure review; P352's consumed authority and artifacts stay unchanged.
No further broad source or web investigation is a prerequisite identified by
this bounded review. Runtime topology, actual commit acceptance and visible
transition can only be established by a later separately bound device run.

Private follow-up evidence:
`workspace/private/outputs/s22plus_fyg8_p352/static-first-frame-audit-20260907/`.
Its `research-audit.json` is `5177B`, SHA-256
`17dcaf17e442a33d56ef5e75881cf929d460f1ddfd83306bb30202dce8149f95`.
Fourteen earlier inspected inputs were reverified unchanged. No production code,
target contract, candidate, consumed record or device state changed in this
follow-up; A90 and S20+ received no command.
