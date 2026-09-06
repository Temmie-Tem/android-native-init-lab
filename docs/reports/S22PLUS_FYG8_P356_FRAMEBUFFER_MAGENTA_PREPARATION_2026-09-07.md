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


## Connected preparation stop

The operator preapproved D0/D1 and physical availability. First D0 in
`p356-ready1-prepared-20260907-1` preserved the expected baseline rejection after
initial exact rooted FYG8 health passed. The nonreusable stop result is
`3252B/1e0507aae85828e38e55f1b7a2bee96ec3405494060af6767b9dc461e2ebfb7c`;
complete observer is
`2097136B/9374d5e50d50ee617b004315315e6e4e45f3a45d1badb611f596692ccbcc5f0a`.
Actual stop-result reopening passed.

The unchanged reviewed one-normal-reboot primitive passed its H0 self-test and
sent one reboot. It then failed `normal reboot did not return healthy within
bound` after the 240-second return window. S22+ remained ADB offline in retained
inventories. The operator reported Android lock/home screen. No additional
reboot, host reconnect, server restart or candidate action was sent. The D1
start record remains intact and no normal success result was created. Do not
create a replacement PASS or treat the operator's screen report as machine health.

Host kernel evidence shows normal USB disconnect/re-enumeration, then a
SuperSpeed reset and ADB interface error. The ADB log shows authentication
followed by transport shutdown/write timeout at that reset. This establishes a
correlated transport failure, not its underlying cause or a firmware diagnosis.
The logs remain private. One later raw-first bounded host inventory again found
only the selected S22+ offline; it sent no device command and did not establish
late root health. A90/S20+ received no command.

The current preparation is stopped and no F1 token was issued. Evidence links
are retained in private `d1-timeout-observation.json`, SHA-256
`408b4be48e4652ea4ef3f05850e81220bc533880c7a1a53cc2d6e0a61d4a1452`.
P356's H0 artifact remains unconsumed; the original D1 is not replayable.

## Prospective separate observability restoration

A separate, forward-looking one-time scope has been defined privately: after a
fresh explicit operator request, reconnect only the S22+ cable once on the same
port, then use existing raw-first exact D0 identity/health readers once. There
is no automated reconnect, reboot, transport control or F1 preparation call.
The current topology must match the original D1 topology; failed or ambiguous
observation stops without another reconnection. The original D1 timeout and
missing success result stay unchanged. Health restoration does not automatically
resume F1 preparation or retroactively qualify that D1.

The plan and fixed observation helper passed independent `PASS_GO_H0_PROPOSAL`
review, private receipt SHA-256
`253994844639c15480b7be3378953c5dc960dbc44f6dba78ff2b5f5db8318f54`.
The helper compiles and its reviewed source/input hashes were reverified.
This is a reviewed proposal, not active recovery authority. No manual reconnect or observation-helper execution occurred in this unit;
the next step is the operator's fresh explicit decision on that separate scope.
