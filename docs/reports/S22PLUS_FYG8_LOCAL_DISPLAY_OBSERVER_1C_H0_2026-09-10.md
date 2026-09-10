# S22+ local display observer 1C H0

Status: **implementation, H0 validation and independent PASS_GO complete.**
Target: SM-S906N / g0q / S906NKSS7FYG8. This supplies the compatible observer
for the prospective [local display lifecycle](../operations/S22PLUS_FYG8_LOCAL_DISPLAY_LIFECYCLE_V1.md).
It opens no transport and registers no candidate or live owner. Existing
P381/P383 observers, consumed results and activation records are unchanged.

## Behavior and evidence

The new direct Python adapter receives the owner's existing source-bound IO,
an explicit native identity and the 16 direct source receipts. It verifies the
`local-display-v1` profile and authenticated OPEN/boot/preparation binding. The
receipt records the direct-source digest and cached-before-auth stage61/62
semantics. A future owner must also bind its full platform/bootstrap/IO closure;
the adapter's direct-source binding does not substitute for that closure or
establish physical target/artifact identity.

Fixed native health runs first: EXEC3 with the unchanged native-health command,
then fresh idle STATUS4, using the existing shared consumer. Optional HUD work
never supplies those health facts. When at least 26 seconds remain, EXEC5 waits
three seconds then reads the fixed RAM `hud.log`; its 15-second command limit,
delivery 2, cleanup 2 and CONTROL delivery 2/flush 5 are reserved before admission.
Otherwise HUD is not requested. The owner receives the actual CONTROL sequence:
6 after HUD, or 5 after the skip. Its callback must return before CONTROL bytes
are sent; original deadlines are never renewed. This finite reserve does not
prove recovery from kernel, host I/O or device transport stalls.

A failed/stalled HUD, command failure, missing log, output truncation or stale
telemetry leaves native health and display observation separate. An integrity
or transport error stops new sends. Partial results retain only health already
validated before the failure, with absent boot/nonce fields represented as null.
The original bounded raw stream is captured before parsing. There is no reopen,
second session, arbitrary command or retry path.

The new log decoder accepts states 0..8, at most 916 increasing frame sequences,
nondecreasing uptime including same-tick lifecycle transitions, and existing
601-sample/freshness/value limits. It permits sequence gaps without claiming
lossless logging. A single valid frame is a reported matched-flip observation;
distinct fresh memory/CPU and gauge sample counts remain optional observations.
Neither frames nor local WAIT_AUTH establish PID1, physical pixels or continuous
liveness. Physical visibility is always UNPROVED in machine results.

Known failure/kernel-log markers invalidate display qualification, preventing
HUD-looking raw diagnostic text from becoming flip evidence. Signal-attempt,
exit and wait-error lines remain distinct records; an attempted signal is never
called a successful reap. Optional gauge diagnostic text makes no probe claim.
The 1MiB log limit and existing command-output/raw-capture limits are unchanged.

Retained replay uses the same source-bound handshake consumer, then the shared
CRC/HMAC/frame consumer. It allows exactly health/STATUS/CONTROL or
health/STATUS/HUD/CONTROL, checks response phase order and validates the actual
health prefix before evaluating optional HUD output. Live and replay receipts
match, including the skip and failed-HUD cases. CONTROL acceptance is not
Download-arrival or rollback proof.

## Validation

- 11 new observer tests passed in 14.565 seconds: actual production local PID1,
  renderer and collector join with real host fork/exec/socket/pipe operations;
  WAIT_AUTH before OPEN; complete retained replay; all local states and limits;
  HUD stall/read failure/output loss; deadline skip; owner rejection; early
  handshake failure; corrupted peer frame after health; diagnostic injection.
- 15 unchanged native-health/shared-wire regressions passed in 2.402 seconds.
- Touched Python compiles and whitespace checks pass. No native C source changed;
  reviewed phase1B ARM64 A/B component validation remains applicable.

The integration fixture supplies numeric root/PID1, mounts, module/DRM hardware
and fixed health-command output. Those are explicit H0 fixture limits, not new
on-device proof. The renderer, lifecycle, authenticated wire, subprocess/output
path and retained consumer execute their production code.

Initial independent review identified three concrete issues: absent BOOT_ID
masked early failure, HUD lacked remaining-budget admission, and raw display
failure diagnostics could supply apparent frames. All three were repaired and
covered by the negative corpus. Independent reviewer `native_refactor_review`
returned PASS_GO against the hashes below after reviewing the final report and
independently passing four decoder and three production-join tests. All 16
direct native sources remain equal to reviewed phase1B; their compact receipt
digest is `bf8474d9d7890203c487e43628c54b4ce49174629be17a23e575a2c457043ca0`.

| Source | SHA-256 |
| --- | --- |
| `s22plus_local_display_observer_v1.py` | `a8bb2f38a43254b977f5578b39533099505862a16c79e805158988532fe310f7` |
| `test_s22plus_local_display_observer_v1.py` | `cf8b6fc2312eb4d61c16ef112bc6f1bba0b8bf8accc57f25d33166f9dbcaa0fd` |
| unchanged `s22plus_native_baseline_health_v1.py` | `e5b421fa130e035ac853caa56af08a51e13656df18957ef92b20f92c1274a3eb` |
| unchanged `s22plus_root_console_v1.py` | `2805aecba8bebaa1174288fd53018a6fc52c4101c05fb6206bc88e1391128f40` |
| unchanged `s22plus_native_source_v1.py` | `dd5b6d3c6057331b48462e9e6b1f7fe01c0f7ad08556cdc513a43bd84b0c598f` |

This unit supplies compatible H0 observation semantics. Live adoption still
requires a fresh artifact/source/target binding through an authorized owner.
It allocates no AP, READY manifest, new run, grant, version or tag. The separate
USB arrival repair and historical P383 second-boot NO_PROOF are not display
qualification results. A90 and S20+ are outside this unit.
