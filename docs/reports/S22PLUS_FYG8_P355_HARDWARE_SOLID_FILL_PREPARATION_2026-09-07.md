# P355 hardware magenta solid-fill comparison

P354 reproduced the prior speckles and lower-area corruption after adding an
explicit noise disable. P355 changes the selected plane's pixel-source branch
using the exact vendor driver's existing `color_fill` property. The intended
observation is a full magenta field, followed by ordinary exact rollback and
verified healthy FYG8 return. This is a diagnostic comparison, not a proved fix.

## Design and interpretation

The sole atomic transaction addition relative to P354 is selected-plane
`color_fill=0x80ff00ff`: bit 31 enables fill and the low 24 bits request magenta.
The renderer resolves the name uniquely; missing or duplicate property stops
before the one blocking ALLOW_MODESET atomic ioctl. There is no register access,
fallback, second commit or retry. The exact 30HS tuple, primary routing,
noise_layer_v1=0, twelve display modules, readiness, privilege drop, full geometry
and inherited-plane handling remain unchanged.

The original WC framebuffer remains allocated, painted with the P353/P354
red/blue/green/black-cross pattern and submitted. If the hardware fill is active,
its output should differ clearly from those buffer pixels. Observing the old
pattern, white, unchanged logo or an unobserved screen is not successful magenta
qualification. The driver prioritizes its own error state by forcing white.

Exact `sde_plane_flush` tests the enable bit and calls `_sde_plane_color_fill`.
The helper invokes `setup_solidfill`, selects ABGR8888, overrides source geometry
and scaler/decimation, and sets `SDE_SSPP_SOLID_FILL`. This is not solely a memory
cache toggle: FB/GEM/SMMU preparation may still run, and format/scaler behavior
also changes. A clean magenta field would favor further investigation of the
normal buffer-fetch/format/scaler path but would not establish a cache fault.
Corrupt magenta would weaken normal framebuffer pixel reads as the sole cause
and motivate downstream composition/output investigation. Neither observation
alone proves the internal hardware state or diagnoses physical damage.

The four existing exact-source fixture cases cover ordinary non-fill, a color
without the enable bit, enabled opaque magenta with format/scaler effects, and
priority error-white behavior. All 31 source inputs in that retained audit were
reverified unchanged; its synthetic hardware callbacks do not establish live
panel behavior. See the [source investigation](S22PLUS_FYG8_P353_IMAGE_CORRUPTION_H0_2026-09-07.md)
and [P354 closed comparison](S22PLUS_FYG8_P354_NOISE_DISABLE_H0_2026-09-07.md).

## Binding and validation

Fresh P355 command/run/Image/observer namespaces reuse the seven sealed P353
machinery sources through the existing fixed projection pattern. The P355
renderer extends the hash-bound P354 generator; consumed source/artifact bytes
remain unchanged. The shared evidence registry adds P355 to the existing
static-display-dispatch workload. Shared live observer/recovery code is unchanged.

The generated renderer fixture checks the complete atomic arrays, selected-plane
count 11, the added color value, inherited-plane offsets, retained noise zero,
every original painted pixel including padding, one buffer/one commit, missing
and duplicate color/noise properties, prior invalid state cases and commit error
without retry. Host-generated C supervisor/prefix/receipt tests retain the
one-way dispatch, local output drain and existing 60-second deadline behavior.

Authenticated host dispatch is still the only positive machine observation.
The observer does not wait for a display response or assert a clean image,
executed fill or hardware state. Operator visual evidence and final rooted FYG8
health are separate results. Physical Download and exact rollback remain
mandatory; a child timeout or process exit is not a recovery mechanism.

Private build and verification artifacts are under
`workspace/private/outputs/s22plus_fyg8_p355/`. Fresh run identity is
`c355f1e0a90b5e6d7c8a9b0c1d2e3f0b`; Image identity is
`41490944B/936d6705d7471bee8c63500f1ede413083069a8a221bfe75cc1a9cc9c1c10d41`.
The inherited same-length Image transformation changes identity only; the
reviewed kernel and modules are reused, not rebuilt or functionally patched.

A/B userspace, renderer, boot and AP are byte-identical; the renderer is a static
AArch64 ELF. Actual AP/boot/ramdisk joins pass. P355 focused tests pass 21 cases;
P354 regressions pass 21. Touched Python compiles. All 73 construction inputs
and 110 static source entries are exact; the unchanged module/plan/prerequisite/
KMS/child joins were checked against P354's retained receipt.

Candidate AP is
`30965801B/d100d9bcfb5d1ab77db22c599d1f2bfbc02e7a30423f5002f35012aa5f9569d9`,
with only `boot.img.lz4`,
`30960599B/e95f2bc5a76972afdccc074d30b53d9813b8ee3d7f7ebe5290624d8441454edf`.
Renderer is `710032B/3a0f925b80584058eae9f98e38b15027e6919bc14bab026b28b98ddecb0efb94`.
Static qualification is
`48075B/0e7cc2d4ea4b68afc07ef768fd595b90ead0a30f22a1b14f7e7502e06a1c8df2`.
Exact rollback remains the original Magisk AP,
`23367721B/d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`.
Independent review returned PASS_GO with no open finding. Its private receipt is
`independent-review.json`, SHA-256
`254a1d77bcee086071890f7e34367e7715f64ba39fe8b5f122e4283817403ec6`.
The actual offline preparation CLI and final-path bundle validation pass.
Ready manifest is
`4686B/5672b4a5e466e81ea036935dfc5175d763550af4cf0e3c562516cfc2e1cae866`;
bundle is `db1e480252b11fbbfe18291698ef60184d01c14cabf891a1d8efea0f305892de`.
Repository boundary, links and diff checks pass. These qualify the capability,
not a device effect or image quality.
The operator authorized D0/D1 through F1 code issuance and confirmed physical
availability. No P355 connected action has yet occurred. A separately returned
exact F1 approval is required before any candidate transfer.
