# S22+ P424: calibrate the retained observer on a proved native carrier

Status: **H0 design; implementation/qualification pending; no device authority**.

The operator selected an independently established earliest observation path
before extending Debian initialization. P423 is consumed and closed healthy;
its [subsequent H0 diagnosis](S22PLUS_DEBIAN_EARLY_STAGE_P423_RUN_2026-10-13.md)
found no candidate marker and retained content consistent with older Android
logs. Several pre-logger failures remain indistinguishable. Only S22+ FYG8 is
selected; A90 and S20+ remain isolated.

## Bounded decision

Prepare one fresh **P424 native log calibration** on the physically proved
native UFS/settled-output-drain carrier used by the recent reader operations.
Keep that boot/USB preparation unchanged to avoid introducing another boot
variable. Select no storage command, root mount, filesystem writer, installed
Debian or additional initialization workload. The native carrier is a
diagnostic reference; Debian initial-PID1 ownership remains the product goal.

After authenticated native health, one fixed root helper will pin the exact
stock `sec_log_buf.ko`, attempt its insertion at most once, verify its binding,
and emit short run/boot-authenticated marker records. The helper runs through
the existing bounded fixed-command child and settled output collector. No
module syscall is added to PID1's synchronous service loop.

The same command separately verifies the exact marker in the current kernel
ring and in a bounded read of the stock current retained backend,
`/proc/ap_klog`. It returns only the exact marker bytes and bounded stage/error/
read accounting through the already authenticated USB channel. That live
evidence can identify a producer or backend failure before physical return.
The existing one-shot owner then requests physical Download and one original-A
return. Only after healthy closure does a fixed same-returned-boot D0 reader
compare the exact live backend marker with `last_kmsg`.

This distinction is required by the
[V3428R positive control](NATIVE_INIT_V3428R_S22PLUS_STOCK_TRANSITION_POSITIVE_CONTROL_LIVE_PASS_2026-07-10.md):
current `/dev/kmsg` acceptance alone is not proof that the Samsung retained
backend received a record. The old stock-origin control is historical evidence,
not authority or proof of the new native-origin experiment. The
[V3433 result](NATIVE_INIT_V3433_S22PLUS_V3432_PID1_KEYSTONE_LIVE_NO_PROOF_2026-07-11.md)
also rules out simply repeating a blind standalone PID1/logger candidate.

## Proof and recovery boundaries

Distinguish authenticated native health, helper entry and settlement, module
attempt/return/bind, kernel-ring readback, current retained-backend membership,
post-return retention, and Android health. Complete negative helper results
remain negative scientific evidence. Missing terminal bytes or an uncertain
module syscall stop the operation; neither a timeout nor a later record grants
replay. Physical original-A recovery stays available through the original
owner, and uncertain N/A effects never repeat.

No direct RAM mapping, new reserved region, logging-policy write, panic, kernel
change, persistent data write or other-partition payload is selected. The
stock logger retains ownership of its existing RAM/hooks. Current-backend
reads are fixed, bounded and private. No claim about earliest Debian entry,
P421's failure, installed services or automatic recovery follows from this
calibration. Only a proved observer can support a later incremental early-boot
candidate, which will have its own scope and qualification.

## Completion criterion

Before requesting any finite attended run grant, require implementation and
independent review of the narrow common/target adoption, fixed helper/profile,
existing owner's physical-return integration, live/retained result join and
actual A/B image qualification. Exercise real ARM64 producer/consumer behavior
and failures for insertion, binding, ring publication, retained-backend absence,
identity mismatch and incomplete output. Hardware substitutions must be explicit;
VM qualification never counts as physical retention. Preserve P423 and all
earlier consumed artifacts/journals unchanged.

This design is recorded before implementation. No connected action or new
grant has occurred in this bounded task.
