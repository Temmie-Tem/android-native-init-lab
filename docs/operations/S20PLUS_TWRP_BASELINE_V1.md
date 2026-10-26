# S20+ retained-T2 TWRP baseline

Status: The prospective baseline policy is defined; connected use requires the
matching independently reviewed capability record. Live qualification is recorded
in the target goal/report, not inferred from this document.

## Purpose and scope

For new S20+ boot-only native-init experiments, use the already retained T2 TWRP
as the normal preparation and terminal recovery environment. Full Android/Magisk
boot is no longer the default terminal requirement for new owners implementing
this profile. Existing consumed runs and their completion criteria do not change.
Existing activated owners that explicitly require Android retain that requirement
until their reachable starting, return and terminal paths adopt this profile.

Recovery health and boot restoration are separate evidence. A successful TWRP
identity read proves recovery health; it reads no boot-partition contents.
An F1 terminal still requires its one fixed boot rollback transfer and the
existing transfer/result validation. TWRP health never upgrades an uncertain
transfer to completed or an absent candidate witness to PROVED.

No new recovery image is flashed. No TWRP UI install, backup/restore, mount,
format, raw block access, arbitrary root command or additional partition scope
is introduced. Android health is required when the bounded task specifically
changes/tests Android compatibility or an unexplained condition requires it;
it is not requested merely because another native-init experiment ended.

## Exact health predicate

Reuse the retained T2 terminal and the fixed identity/metadata producer and parser
in `s20plus_g986n_twrp_boot_identity_d0.py`: exact selected serial and topology,
ADB recovery state, root UID 0, TWRP `3.7.1_12-AstroForge_v2`, exact build and
security properties, `mtp,adb`, running adbd, the pinned T2 marker, stable boot
identity, and the fixed boot inode/sysfs metadata. Boot metadata is not boot-byte
verification. Entering from Android requires a different boot ID from the source.

A fresh direct foreground request for baseline qualification authorizes one
`adb reboot recovery` from exact healthy Android followed by bounded observation,
or a read-only qualification of already-running exact TWRP. The owner validates
the unguarded retained-T2 closure before acquiring its own shared action guard.
Inside that transaction it reuses the exact fixed collector with the validated
predecessor; it does not bypass the standalone D0's absent-guard requirement or
accept a foreign guard. Qualified machine observation closes this owner's guard
without a separate screen-confirmation ceremony.

Normal disappearance/offline/Android-to-recovery progress is a bounded readiness
wait. Wrong serial, a second matching target, malformed output or a failed exact
T2 identity is a stop. The readiness wait cannot resend the reboot. If reporting
is interrupted, resume may observe the current recovery and close the original
transaction; it cannot repeat the mode transition. Failure evidence is retained
as bounded command results/digests and non-private fixed-property fields.

## Future F1 integration

A new F1 owner must bind this predicate at both preparation and terminal stages,
carry its exact serial/topology/boot through its existing lease and guard, and
provide a reviewed recovery-to-Download transition. It must restore the fixed
boot image once and then reach qualified TWRP. If the transfer tool boots System,
that is not silently claimed to be a direct TWRP return: the actual return route
must be declared and qualified. Physical recovery remains the fallback for a
hung candidate; an ordinary successful recovery reboot does not prove automatic
recovery from a hang.

This policy and its baseline checker do not prepare or authorize an F1 candidate.
The checker has no Odin or partition-transfer command. Once its live qualification
passes, the default baseline is retained T2; each future F1 owner still needs only
its relevant new transition/terminal integration review, not repeated review of
unchanged T2 identity logic or a repeated Android roundtrip.
