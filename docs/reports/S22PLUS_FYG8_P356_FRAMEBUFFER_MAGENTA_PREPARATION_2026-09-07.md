# P356 framebuffer magenta comparison

P355 showed clean full-screen magenta using hardware solid fill, while the
ordinary P353/P354 pattern was corrupt. P356 puts magenta in the ordinary WC
framebuffer and explicitly disables hardware fill. This matches the intended
visible color across the two pixel-source paths; it is not a proved repair.

## Bounded change and interpretation

The visible 1080x2340 pixels are XRGB8888 `0x00ff00ff`. Each 4352-byte row retains
the original eight white padding pixels. Keeping padding distinct reduces the
chance that uniform data hides an incorrect pitch or padding read; it does not
prove addressing correctness. The existing synchronization barrier is unchanged.

Relative to P355, the atomic arrays and object/property counts are identical;
only the selected-plane `color_fill` value changes from `0x80ff00ff` to zero.
The name must resolve uniquely or the renderer stops before atomic. The exact
30HS tuple, selected primary, full geometry, one WC allocation, noise_layer_v1=0,
inherited-plane handling, twelve modules, readiness, privilege drop, one blocking
ALLOW_MODESET and no-retry behavior remain unchanged. No cache-control primitive,
driver patch, fallback or extra display transaction is added.

The exact driver reads color_fill before testing its enable bit; zero avoids
the solid-fill branch. Normal format setup does not request SDE_SSPP_SOLID_FILL.
That setup is dirty-state dependent. The source first-enable predicate is
`sde_plane_enabled(state) = state && state->fb && state->crtc`; the renderer's
required initial FB-zero state therefore makes the old state disabled, causing
`_sde_plane_sspp_atomic_check_mode_changed` to set DIRTY_ALL. The later old/new
FB comparison's NULL branch merely logs and is not this proof. The color-fill
property also maps to DIRTY_ALL. These are source-path facts, not live callback
or hardware-register telemetry.

Full magenta and any visible corruption need operator observation. White/error
fill, unchanged logo or an unobserved screen is not successful framebuffer-magenta
qualification. If clean, the result supports this particular constant-buffer
input; uniform color can hide faults and does not prove arbitrary pattern output.
If corrupt, the ordinary-buffer failure is reproduced without the prior shapes,
but the cause still needs investigation. Neither outcome alone isolates cache
coherency. Compare with the [P355 observed result](S22PLUS_FYG8_P355_HARDWARE_SOLID_FILL_PREPARATION_2026-09-07.md).

## Qualification and authority

Fresh P356 wrappers reuse seven hash-bound P353 machinery sources through the
existing fixed namespace projection. The renderer extends the sealed P355
generator. Shared evidence registration adds P356 to the existing dispatch
workload; shared live/recovery code is unchanged. Consumed artifacts remain
untouched. The existing one-way observer establishes authenticated host dispatch
only; visual evidence and exact rollback/final health remain separate.

The generated renderer fixture checks every visible and padding pixel, the
entire atomic array with color_fill=0 and noise=0, one buffer/one commit, inherited
plane offsets, absent/duplicate properties, invalid inputs and commit error
without retry. The retained source audit's 31 input hashes were reverified;
its synthetic source-function fixtures do not establish hardware behavior.

Fresh run identity is `c356f1e0a90b5e6d7c8a9b0c1d2e3f0b`. The identity-only,
same-length Image is
`41490944B/461a25751b357293a0837bbcb807e9cb064a8a231ce2aada7188bd78adc17255`.
Private artifacts are under `workspace/private/outputs/s22plus_fyg8_p356/`.
The reviewed kernel/modules are reused. A/B userspace, renderer, boot and AP
are byte-identical and actual AP/ramdisk joins pass. The renderer is a static
AArch64 ELF. Its identical executable copy ran the existing --h0-paint branch
under QEMU: every one of 10,183,680 bytes matched an independent oracle,
including 2,527,200 magenta visible pixels and 18,720 white padding pixels.
Paint SHA-256 is `d2459ade1d68462946b6762cd24fcd72c7fb8009cf615def3a914ac7a96eab20`.
This exercises the real generated binary with host memory, not live WC/DMA
coherency or physical panel output.

Candidate AP is
`30965801B/3527224aeaf2bb9c30fdb0423984b71a9588f422fa363df2bc303c3fc22a343c`,
containing only `boot.img.lz4`,
`30960360B/0f5f7466c9394a54078668bba68aac9205f39ca7378e415f1b18fd244bccff42`.
Renderer is `710008B/657c016485ffbdd8c9e2f59b54f77087cc5785f7637b239db19f69e23431a42a`.
Static qualification binds 111 source entries and is
`48286B/b8e485faa4fcb9d7391e3725cd4a58988953167bb978426f77f3a26b3bee1a3b`.
All 74 construction inputs remain exact. Rollback remains the original Magisk AP,
`23367721B/d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`.
P356 focused tests pass 21 cases and P355 regressions pass 21 cases. Touched
Python, repository boundary and document checks pass. Independent review is
PASS_GO with no open finding; private receipt SHA-256 is
`461f1686fcf756c15b9bdc764defa6988b40ffc4efb581d220b1dfb718428fe7`.
Actual offline promotion and final-path validation pass: ready manifest
`4686B/cc75f4ad020544678bcb78a7863af4d333744eae821eafab19b5ef3ab018be78`,
bundle `2b7cdd7d7eab255c27bdf989ed61036e50c2376ba6f746f8c055989e92a47bd2`.
All reviewed inputs were reverified unchanged before connected preparation.

The operator preapproved D0/D1 and confirmed physical availability. Connected
preparation will follow qualification. A separately returned fresh F1 code is
still required; no P356 device action has occurred at this H0 stage.
