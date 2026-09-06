# P356: framebuffer magenta corruption observed, exact rollback completed

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
The operator subsequently held this physical-reconnect proposal and requested
host-only software/transport diagnosis; it remains inactive.


## Host-only ADB offline diagnosis

At the operator's request, preserved logs were compared with the earlier return,
and only host process state and cached USB sysfs state were read. No device
command, reconnect, ADB server restart, reboot, tracing attachment or F1 action
was performed. A90/S20+ received no command.

The retained 05:12 return shows a transport shutdown followed by new reader and
writer threads and another authentication response. Subsequent P356 D0 verified
rooted health. At 05:37:11 the failed D1 likewise reached an authentication
response; at 05:37:14 the kernel recorded a SuperSpeed reset and an ADB interface
claim warning, alongside ADB read shutdown and write timeout. At 05:37:15 new
reader/writer threads appeared, but the captured ADB log has no subsequent
key-fetch/authentication-response progress. This locates the observed divergence
at the replacement transport; it does not prove which peer stopped first.

The host's cached USB identity matches the selected target. It remains configured
and authorized at SuperSpeed, with power/control=on and runtime_status=active.
The later kernel capture contains no additional selected-topology reset or
disconnect after 05:37:14. These observations weaken a continuing physical
disconnection or current runtime-suspend explanation; neither excludes a
transient link fault. The ADB server still exists, its executable matches the
installed 34.0.5-debian binary, and its reader threads wait in USB URB reap while
writer threads wait on futexes. This is compatible with an idle/stalled protocol
exchange, not proof that either daemon is healthy. Thread waits alone do not
attribute a particular thread to S22+ or establish a deadlock.

The upstream [ADB connection handling](https://android.googlesource.com/platform/packages/modules/adb/+/refs/tags/android-14.0.0_r1/adb.cpp)
calls handle_offline during new-connection handling before returning online, so
the INFO `offline` line alone is not an authentication-rejection verdict.
The upstream [Linux USB backend](https://android.googlesource.com/platform/packages/modules/adb/+/refs/tags/android-14.0.0_r1/client/usb_linux.cpp)
also maps a dead write handle to ETIMEDOUT and provides an explicit USB reset
path. Consequently the timeout text alone does not prove a five-second stall,
and a kernel reset line alone does not identify its initiator. The corresponding
upstream transport Reset path logs a reset, which is absent from this capture;
that limits support for an explicit ADB Reset call but does not exclude every
host-initiated reset. These Android 14 upstream files are explanatory references,
not a verified source closure for the installed Ubuntu/Debian package.

Conclusion: a USB/ADB transport re-establishment stall is observed; physical
cable failure, host backend failure and device adbd/gadget failure remain
unproved causes. There is no evidence here of P356 candidate failure because it
has never been transferred. Fresh machine health remains unavailable. The
original D1 timeout stays unchanged, the manual restore proposal remains on
hold, and no automatic preparation resume is authorized. Any diagnostic reset
would be a separate device-connected control action, beyond this read-only unit.

Private captures, upstream source copies and their digest index are under
`workspace/private/outputs/s22plus_fyg8_p356/adb-offline-h0-20260907/`.


## Operator reconnection and fresh preparation

The operator reported completing the separately proposed manual reconnection.
A bounded query to the existing host ADB server found the exact S22+ in `device`
state. Kernel evidence records re-enumeration; this verifies observable return,
not a cable-fault diagnosis or an exact physical manipulation count.
The operator then explicitly requested health verification and assessment of
fresh P356 preparation, with separate F1 approval still required.

The unchanged reviewed one-shot D0 observer passed
`PASS_P356_LATE_D0_HEALTH_ONLY`. Exact serial/topology, rooted FYG8, Android boot
completion, stopped boot animation, original boot/supporting hashes and absent
Download endpoint all passed. The private result is
`1449B/e194e171dd7e5ad4a7f94a6ef78752585c87bbc51a9d00da84f38cc2df2d222c`.
This closes the separate health-observation invocation. Original D1 start,
timeout and absent success result remain unchanged; no reboot was repeated.

Incident-scoped independent review returned
`PASS_FRESH_D0_PREPARATION_SCOPE_ONLY`, receipt SHA-256
`92aecb223d1d17b636084fac5f0725070bb52592a181d4a12e6d02c0de4f81bf`.
Existing ordinary fresh preparation is bounded observation, explicitly permitted
after stop and separately requested by the operator. It does not consume a D1
PASS or authorize an effect continuation. All 104 previously reviewed execution
inputs and eight artifacts remain unchanged; the actual host validator again
returned `PASS_DEVICE_ACTION_F1_LIVE_V2_HOST_READY`.

One fresh ordinary preparation in `p356-ready1-prepared-20260907-2` passed
`PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY` and produced `prepared.json`,
SHA-256 `1cdbbf5ac9b75c44408379f2ecde56f2bf946fdb67b5564e454cfafe4403ab81`.
The prepared record binds the current target, boot, baseline, artifacts and
execution closure and emits a new separate F1 approval token. Its device-write,
reboot, partition-transfer and F1-authority flags are all false. No P356 candidate
has been transferred, and A90/S20+ received no command. The next action requires
the returned exact attended F1 approval; the original failed D1 is not resumed.


## Approved F1 execution and recovered close

The operator returned the exact fresh prepared F1 token. Candidate AP
`30965801B/3527224aeaf2bb9c30fdb0423984b71a9588f422fa363df2bc303c3fc22a343c`
was transferred once; authenticated parent identity and display-request dispatch
passed. The operator reported magenta with stripes/corruption and supplied a
private photograph showing horizontal dark gaps that become increasingly dense
toward the lower display. **Clean framebuffer magenta was not achieved.**
The original photo is retained privately as
`177019B/39f580686215b528eaa08da70e6cbdc18af1c8e3c6bb9202e4a4681ba813991a`.

After observation closed, the original execute invocation stopped with
`measured USB endpoint evidence failed` while awaiting physical Download.
The durable journal was at OBSERVED; no rollback intent or transfer had begun.
The error and raw endpoint evidence were preserved. One same-journal
preauthorized `--recover` invocation completed the exact Magisk rollback
`23367721B/d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`.
Candidate transfer and observation were not replayed. The endpoint-observation
error's cause is unproved; it is not reclassified as benign or as cable movement.
This deviation is distinct from the earlier ordinary-D1 ADB timeout, whose
original failure remains unchanged.

Final rooted FYG8, boot completion, original boot/supporting hashes and absent
Download all pass. The run is CLOSED/19 with recovery_required=false. Result
`22804B/5669fe0560774de7cdf4ad6aa6c19c076a8c29c1c337e2b049347025c081ac0d`
reports `PASS_F1_V2_P356_STATIC_DISPLAY_DISPATCH_AND_ROLLED_BACK`: that machine
verdict proves dispatch and recovery, not clean image quality or internal
display execution. No active lease or new action remains. A90/S20+ received no
command. P356 is consumed and never replayable.

The operator also supplied an Android-boot comparison photo showing the SKT 5GX
logo on a white field without P356's conspicuous horizontal gaps/lower breakup.
It is retained privately as
`102782B/121b07adbaddae7fdd5805da788432fe8da86f87b6522a21f936712a5aa43760`.
Its Android-boot context is operator-reported, not a same-instant machine binding;
photo texture and exposure are not pixel measurements. Together with P355's
clean hardware fill, it supports prioritizing differences in the native ordinary
buffer path and Android display setup over a persistent panel defect. It does
not identify a cache, format, address mapping, scaler or timing cause. No new
experiment or device read is implied by this comparison.

Canonical timeline (UTC; readiness labels retain the runner's dispatch/health
semantics and do not promote visual proof):

- `live_session_start`: `2026-09-06T21:23:44.032387Z`
- `candidate_flash_start`: `2026-09-06T21:24:12.218627Z`
- `candidate_flash_done`: `2026-09-06T21:24:13.855171Z`
- `candidate_boot_ready`: `2026-09-06T21:24:38.128741Z`
- `rollback_flash_start`: `2026-09-06T21:26:28.202610Z`
- `rollback_flash_done`: `2026-09-06T21:26:29.738133Z`
- `rollback_boot_ready`: `2026-09-06T21:27:00.842427Z`
- `live_session_end`: `2026-09-06T21:27:00.862366Z`

Actual prepared/result reopening passed after closure. Scoped document/link,
private-identifier and repository boundary checks pass; execution inputs were
unchanged, so no image rebuild or unrelated regression suite was required.
