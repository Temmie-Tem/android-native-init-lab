# S22+ Debian shutdown into Download V1

Status: **REVIEW_GATED_CAPABILITY**. This specialization selects only
`post-autoboot-p460-download-v1`, namespace `p461`, `debian-autoboot-v1` and
the existing V3 `debian-autoboot` owner on `SM-S906N/g0q/S906NKSS7FYG8`.
Definition and H0 qualification do not open a device grant.

## Bounded successor and recovery

Retain the [persistent cron configuration workload](S22PLUS_DEBIAN_CRON_CONFIG_V1.md):
two Debian boots, four admitted native_data writable lifetimes, one ordinary
first reboot, the same exact configuration creation/consumption/retirement and
one original-A return. The new final control replaces power-off with one Samsung
Download request after normal SysV service/filesystem cleanup. Debian init
remains host PID1. There is no new resident supervisor, third boot, package
installation, additional persistent file, repair or other-partition writer.

The original 300000 ms absolute deadline per boot, two fixed 360-second host
observation windows and one attended operation within 3600 seconds remain.
One fresh qualified N, current exact target/health, verified original A,
demonstrated physical Download recovery, current independent review and the
operator's finite attended grant are mandatory. All P460 artifacts and effects
remain consumed. Expected baseline M is 30; the existing reviewed fixed D0
must establish the actual physical baseline before image qualification.

Successful normal return requires completed second-boot service/SSH/workload
evidence, one authenticated final intent, actual exact Download arrival, one
original-A transfer and Android health/closure without manual Download entry.
Acceptance, USB departure and Download arrival are separate facts. Physical
fallback can close the owner healthy but cannot prove automatic return.
Departure, exact Download arrival and original-A dispatch share one 90-second
window starting at the original final-control intent, clipped to the original
grant. Observation or continuation never renews that window.
On uncertainty, preserve the intent and original owner; never repeat control,
module insertion or transfer. Only the existing attended original-A recovery
and, after raw-proved A, health-only continuation remain available.

## RAM shutdown handoff

The new source-bound runtime domain distinguishes final shutdown through
Download from previous power-off selections. The first control remains an
explicit ordinary reboot intent. The final forced SSH command accepts only
`download`, appends the selected terminal intent to completed runtime evidence,
returns that snapshot and enters SysV runlevel 6 with packaged `shutdown -r`.
It exposes no caller-supplied command, path or restart argument.

The existing RAM inittab selects a RAM copy of the exact packaged serial rc
dispatcher for runlevel 6. All ordinary K01–K05 scripts retain their order.
The final K06 reboot entry selects the fixed RAM hook instead of packaged
`reboot`; only that hook owns the final syscall. It checks the selected phase,
same-boot authenticated state, complete runtime intent and the actual
native_data root. An exclusive RAM claim precedes any preparation or control.
Absent/wrong intent, repeated claim or expired deadline parks without a
fallback reboot or power-off. Bounded RAM error records are available only
after the unique claim and log open succeed; earlier rejection may leave no
record. The RAM inittab replaces the
runlevel-6 sulogin fallback with the existing fixed park behavior.

Root identity and read-only filesystem state must be checked at the final
hook, independently of `umountroot`/dispatcher exit status. A read-only bind
flag alone is insufficient. The normal scripts perform synchronization and
root remount; no raw superblock write or filesystem repair is added. Final
Download arrival does not by itself establish complete on-disk consistency.

The hook and its selected module assets survive in the existing bounded `/run`
tmpfs. No final-script bind under `/etc/init.d` is relied upon after `umountfs`.
The first phase issues one ordinary restart syscall. Only the final phase
prepares the stock Download route, then issues one RESTART2 with the literal
`download`. A returned syscall has no alternate control. A surviving park
does not guarantee device quiescence after a helper or kernel failure.

## Exact stock preparation and effects

Use only the five exact retained stock bytes and parameters declared by
`s22plus_fyg8_p363_return_spec.py`, in its order: SDAM provider,
`sec_reboot_cmd`, `sec_qc_rbcmd`, `qcom-dload-mode` with `download_mode=0`,
then `sec_qc_qcom_reboot_reason`. These are RAM assets, hash/size/metadata checked
and inserted once from the same no-follow descriptor using actual target UAPI
flags. There is no unload, retry, arbitrary module or generic NVMEM interface.

Before the final writer, both SDAM providers must resolve to the exact retained
DT nodes and the bounded read-only command-registry observation must establish
Reboot Notifier priority 250, a default handler and exact `download` command.
Asynchronous registration may be observed for at most five seconds within the
original deadline. The final writer must bind its exact stock platform node.
Only bounded stage/error identifiers are recorded; no pointers or raw NVMEM
data are exported. Blocking kernel calls remain physically recoverable work;
a userspace deadline cannot interrupt them.

The selected initialization explicitly includes NODUMP/disable_sdi from
`download_mode=0`, subsequent FULLDUMP during Samsung writer probe, the stock
SEC_DEBUG_MODE IMEM write on writer registration and the normal notifier's
later NODUMP request. Late preparation shortens but does not eliminate that
window. The stock writer's existing read-error `kfree(ERR_PTR)` hazard and
internal bounded write/readback attempts remain part of this attended scope.
Its diagnostics do not establish successful Download. Firmware persistence of
disable_sdi is not inferred. No panic, watchdog, dump acquisition, EDL, alternate
firmware reset or raw host partition write is authorized.

## Qualification and proof

Retain the complete root comparisons, four mount-count boundaries, exact
first-pair retention and configuration settlement rules. Add only five P460
authenticated final-producer file expectations under their original source
snapshot; they do not assert post-Android retrieval or current clean state.
No unknown file or failed configuration is learned into the next root.

Independent review covers the common/target specialization, actual RAM assets,
producer/consumer grammar, final helper, stock preparation, SysV order, host
Download observation, connector entry and original recovery path. Qualification
must exercise the actual ARM64 implementation and packaged dispatcher, including
wrong/absent intent, writable root, repeated claim, preparation failure and
returned syscall without alternate control. Physical and VM hardware
substitutions remain explicit. A VM power-off substituting the unsupported
Samsung Download firmware path is not physical Download proof.

This capability remains attended and does not activate deferred physical or
automatic failure recovery. Healthy closure permits only a fresh subsequent
operation under its applicable authority; it never replays consumed effects.
