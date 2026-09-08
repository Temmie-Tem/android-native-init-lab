# S22+ P369 control during a fixed display-child wait

P369 separates control availability from display progress. The fixed renderer
submits three swaps, flushes its exact run-bound WAIT_ENTERED marker, and repeats
one-second nanosleep without further rendering. PID1 sends READY after return
preparation and successful clone. The host waits ten seconds from READY, then
sends its one durable-intent CONTROL irrespective of display progress.
The existing sixty-second outer deadline is unchanged.

## Evidence contract

READY and ACK now preserve a frozen control-readiness snapshot (zero submissions,
no observed child exit). They are not display completion or liveness evidence.
The bounded parent pipe parser continues after READY. A duplicate or out-of-order
marker is ineligible; malformed or foreign-run markers do not qualify.

After authenticating and consuming CONTROL, PID1 samples the exact child with
wait4(WNOHANG) and signs one stage-44/event-5 checkpoint before ACK. It records
the observed submission count, exact marker, marker age of at least two
monotonic seconds, and a fresh wait4 return of zero. Qualification requires all
four facts, exactly three submissions and no signed child exit. Missing or
negative facts do not block ACK/Download; they yield NO_PROOF. Authentication,
transport, clock/wait4 and diagnostic-write errors retain their existing stops.
No syscall or alternate reboot is retried. Diagnostic records remain bounded
at 49 frames and raw replay enforces the same authenticated grammar.

The complete live result additionally requires exact Download arrival within
the existing thirty-second window, the one exact Magisk rollback and final
rooted FYG8 health. Physical-intervention absence remains a separate operator
observation. A fixed wait marker plus one unreaped-child sample is not continuous
liveness, pixel proof, PID1-failure recovery or blocked-driver/kernel recovery.
P368 is consumed and unchanged; unattended F1 remains inactive.

## Host qualification

Seven focused tests exercise the actual generated renderer and native console,
Python observer, retained evidence and the joined arrival/final-health paths.
Kernel, DRM, ADB, Odin and USB behavior are explicit H0 fixtures. The actual
rendered C remains alive after its third submission and wait marker. The native
fixture's clock scales by thirty; its host observation interval scales with it.
An explicit young-marker clock fixture exercises the insufficient-age branch.

The exact wait qualifies in the joined fixture. Pre-marker stall, foreign marker,
fourth submission, child exit, signal and insufficient marker age all preserve
one CONTROL while failing qualification. Immediate CONTROL before any marker
also works and remains NO_PROOF. An actually transmitted bad MAC causes no
reboot syscall; duplicate transmitted CONTROL bytes cause only one syscall.
These last two are native parser tests, not claims that malformed host evidence
would pass the production raw validator. Retained checkpoint mutations reject.

The final batch passes 117 tests: seven new, five P368, nine P367, 76 common F1
and 20 goal-research tests. All fifteen changed Python files compile. Independent
prebuild review and its separate seven-test run passed. An earlier bad-MAC test
patched an unused codec instance; the corrected fixture targets the actual
sender and checks transmitted bytes. No production check was weakened.

## Artifacts

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Image | 41490944 | `8005433404304dd66fbd72af2d8a4dad0d025f3d18d0ce5021f6e48ab9642a8c` |
| A/B identical AP | 31006761 | `70903e2baa1520805011dff3e96b924031c9b9c2051d294303192f07458f950b` |
| Static ARM64 init | 150784 | `1ba82468637792bc2f022740bf35c5c05440fa55e237b2f3f9db059e521f456b` |
| Static ARM64 renderer | 710040 | `50031047521746a7556e41f7cc6c73fba29b91000dac7c083551c6036f32a96a` |

Both A/B userspace/package outputs match. The Image uses the retained validated
P344 identity-only transform; native userspace changes are separately bound.
All 160 build inputs remain unchanged. The new native checkpoint source is
included in both build and static closures. Only the regular allowed
`boot.img.lz4` is packaged. Private artifacts and evidence remain under
`workspace/private/outputs/s22plus_fyg8_p369/`.

This preparation grants no device effect. Fresh exact connected preparation
and returned attended F1 approval remain required; physical Download recovery
must be available for the original failure cases.

## Final review and publication

Independent source/artifact review returned PASS_GO with no blocking findings.
It checked all 160 build inputs, 206 static closure entries, A/B identities and
the final seven focused tests. The private review receipt SHA-256 is
`78f56fc85de51540e8c3effbefc4560afd0c7d8756402aa8be4399ec2ce624b6`.
The actual common offline verification and publication passed; the ready
manifest is `workspace/public/src/device-action/manifests/s22plus_fyg8_p369_process_v2_ready_1.json` (5054 bytes,
SHA-256 `f36cae04d35e449d8e3f6509daeb88ec96e6c861bd4687e9688ad3c7a457c138`). Published bundle SHA-256:
`092493e711d1edf16709a30722d4ec9377d003002c70554eb16e9f824d9eb638`. These steps performed no device contact.

The prospective goal-research review was refreshed for the changed live-owner
registration and target clause. The prior receipt is retained exactly. The
review checked P368 CLOSED/19 and no pending D1, F1 owner or research grant;
the current runtime review gate passes. No historical grant or consumed source
binding was rewritten and no new research grant was opened.

## Fresh connected preparation

One fixed read-only `--prepare` completed in
`p369-ready1-prepared-20260908-1`. The D0 result is
`PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY`: exact rooted FYG8, Android
completion, original boot/supporting partition hashes and absent Download all
passed. The current exact boot and target binding are retained privately.
No reboot, mode transition, candidate transfer or rollback occurred in this unit;
A90 and S20+ received no command. The prepared binding awaits its separately
returned attended F1 approval and creates no unattended session.

The actual prepared bundle reopened against its current source, artifact and
private D0 evidence. Prepared record: 33389 bytes, SHA-256
`e461f9c4440f29515573e515f567900b770204f19087744c2d74a1362d27fb71`. Changed-file compile, relevant
regressions, independent review, diff/link checks and the staged repository
boundary check pass. This is prepared capability evidence, not live wait recovery.
