# S22+ native resident runtime H0 V1

Result: **PASS_RESIDENT_BUILD_H0; independent PASS_GO for H0 only.**
Target: **SM-S906N / g0q / S906NKSS7FYG8**.

The operator selected resident implementation and host validation, then explicitly
confirmed removing the 15-minute normal-runtime limit and designing PID1/userspace
for long residence. The bounded unit is complete. No device command, image
transfer, live activation or new grant occurred. Existing P385 image/admission,
consumed roles and its 900-second/eight-authentication contract remain unchanged.
All 160 inputs in its current review binding still match their recorded identities.

## Resulting runtime

The new [resident source composition](../../workspace/public/src/scripts/revalidation/s22plus_native_resident_source_v1.py)
reuses unchanged framing, root command execution, return preparation and DRM
machinery. New lifecycle/service fragments have no normal 900-second or
601-sample expiry. PID1 owns exactly one system collector, one hardware collector
and one renderer, without a respawn path. A blocked or unreaped worker retains its
slot; neither a signal attempt nor fresh telemetry clears an uncertain command.
Normal DETACH permits same-boot reauthentication with a 64-bit ordinal and a
192-bit random nonce prefix plus that ordinal. The per-command-session 600-second
budget and original command/output bounds remain finite. Exhaustion cannot wrap
counters or reuse a nonce.

The system collector reads bounded procfs data independently from all hardware
sysfs reads. The hardware collector retains the exact read-only gauge address,
register, model and parent ABI checks. Its separately composed provider uses
64-bit attempts and BOOTTIME, stops further bus reads after a fault, and has no
reload/reset path. A received sample is checked against a post-receive timestamp
so concurrent collection after the tick clock cannot become a false future-time
fault. EOF, a known nonzero worker exit, missing sensors and stale samples remain
distinct states.

CPU temperature is independent from battery temperature. The exact Waipio source
contains 13 selected types: `cpu-1-0` through `cpu-1-8` map to TSENS0 channels 5–13;
`cpu-0-0` through `cpu-0-3` map to TSENS1 channels 1–4. The collector discovers sysfs
indices once, rejects duplicate names and checks the selected type before and
after each reading. The HUD labels the maximum available temperature and sensor
coverage, for example `CPU COVERAGE: 13/13`; incomplete coverage is not proof of
the hottest CPU sensor. Bound source `waipio-thermal.dtsi` SHA-256:
`0579e14dceeb455aabcb456b7fec2322dd13b30eb39c99f64e3c50f2d3976f4d`.
Actual native exposure and thermal accuracy remain **UNPROVED**.

The renderer retains immutable painted buffers, at most two live GEM objects,
and retirement only after the matching flip event. Uncertain DRM work parks the
sole renderer without replay or reinitialization. Its counters no longer stop
at the old frame/log limits. PID1 retains 64 complete diagnostic records, each at
most 768 bytes; command-triggered export includes the retained range, evictions,
parser drops, partial-byte count and a complete footer. Renderer records include
observed producer drops. A complete export is a complete retained window;
lossless lifetime history is never inferred from it.

## Validation

The final focused suite passed **10 tests in 23.216 seconds**, using the actual
generated C and host consumers. Hardware, clocks, native credentials/mounts and
USB/DRM endpoints are explicitly identified fixtures.

| Check | Observed H0 result |
| --- | --- |
| Real PTY/authentication | 12 same-boot sessions, repeated RNG fixture, unique ordinal nonces, clean DETACH/reopen, one boot preparation and one final CONTROL |
| System and hardware producers | 100,000 samples each through 601/900, hour/day boundaries; fixed-name CPU selection, units, negative values, missing/duplicate/changed types, range failures and terminal gauge bus fault |
| Actual renderer | 1,001 immutable frames; accelerated day jumps; at most two GEM objects, matched-event retirement and no replay on the DRM negative corpus |
| Supervisor/command faults | Hardware stall/exit leaves system sequence and authenticated commands progressing; malformed OPEN, authenticated disconnect and boot-ID read failure refuse later authentication while local services continue |
| Resource/evidence bounds | Real 128/304-byte seqpacket IPC, 32/64-bit sequence boundaries, post-tick sample arrival, stale retention, month-scale service, unreaped/unknown child slots, 100,000 log records, partial/oversized input and producer backpressure |
| Target ABI | Exact FYG8 UAPI operands checked; statically linked AArch64 raw-syscall test under QEMU verifies BOOTTIME, file flags, ftruncate/lseek export, MSG_TRUNC, nonblocking backpressure, broken peer and close_range |
| Build | Static AArch64 PID1 and renderer A/B match; full-LTO provider A/B match and every imported symbol CRC matches the exact bound FYG8 Image |

Touched Python passed `py_compile`. The H0 builder creates ELF/module artifacts;
it creates no boot image or candidate activation. Build-1's native compile found
one misleading-indentation error; the source was corrected. Build-2 passed;
the subsequent EOF/reap and receive-timestamp fixes were compiled again in
Build-3. The unchanged provider's already validated A/B pair was reopened and
verified before reuse, preserving the failed-build evidence.

| Build-3 artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Native PID1 | 149,968 | `3522935aa95d1344f56fb1fa4416462715089bfd0b91120edca511be07af3225` |
| Renderer | 778,512 | `c494e49621afb04d4b8feb28c061e7acabeb7101de49ca1400b51cf3835590b5` |
| Gauge provider | 305,480 | `b47b7e14efbd685423b12e13563d402b43d46e9170d84bb1715d39e2e1566b1c` |

The new provider clock import is `ktime_get_with_offset`, CRC `c4f0da12`, reached
through the bound kernel's `ktime_get_boottime()` inline wrapper. This is a build
and exact linkage result, not proof that the module was loaded on a device.

## Independent review and retained evidence

The independent reviewer returned **PASS_GO for H0 only**, with no open blocking
findings. Review covered lifecycle entry, descriptor initialization, protocol
reentry/stop, worker ownership, freshness, CPU selection, bounded logging, DRM
uncertainty, provider composition and artifact production. Findings corrected
during the unit included double initialization, unowned fd-zero access after
setup failure, the outer boot-ID-failure park loop, checked clock conversion,
log-loss claims, export-footer length and receive/reap ordering. Passing the
review qualifies this H0 capability only.

Private evidence is retained under
`workspace/private/outputs/s22plus-native-resident-h0-v1/`:
`build-3/result.json`, A/B artifacts and source inputs, `final-tests.stderr`,
`p385-compatibility.json`, and `qualification.json`. The build result SHA-256 is
`ae3177d642206200a8d49a0d9a8359e6d451e287dbb29cb0815deba847878d18`;
the build-input map's canonical SHA-256 is
`7f1353bace30354ce06cf401add38fecb42b17a5014f5d7fcaa5a32032152de4`.
The qualification record separately binds the inherited host-reader inputs and
test/harness sources; the build-input map is not labelled a complete host-reader
execution closure.

Actual long-duration target operation, native CPU sensor exposure, physical HUD
visibility, recovery after kernel/DRM stalls and unattended operation remain
**UNPROVED**. Prospective device use requires its own reviewed resident adoption
with current target/artifact/attendance/recovery binding. H0 qualification does
not extend the consumed P385 runtime, renew its grant or authorize any other target.
