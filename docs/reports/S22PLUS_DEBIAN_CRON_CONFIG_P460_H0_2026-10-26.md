# P460 persistent cron configuration: H0 qualification

Status: **PASS_H0_PRODUCTION_CRON_CONFIG / independent PASS_GO**.
No device action, physical baseline read, new finite grant or physical
execution is included in this change.

## Bounded capability

The selected target is S22+ FYG8 only. The completion criterion is an actual
packaged cron reading one disk cron.d configuration after an ordinary Debian
reboot, producing the fixed integrity report, and retiring that exact
configuration before final shutdown. This specializes the existing two-boot,
four-lifetime attended owner; it does not install a package or extend a device
budget. [The exact policy](../operations/S22PLUS_DEBIAN_CRON_CONFIG_V1.md)
defines the two file creations, one successful-path unlink and RAM-only
failure cleanup. A90, S20+ and unrelated server work remain untouched.

The first boot creates and authenticates the configuration's contents, inode,
ownership, mode, link count and nanosecond mtime/ctime. First-boot dispatches
cannot write a report. Both second-boot protected admissions require that same
file and the original completed early/runtime pair. The second-boot cron job
must join the current boot, hook, root and actual daemon ancestry. Successful
retirement waits for the worker and cron/PAM processes, unlinks the held exact
inode once, synchronizes its parent, and starts a fully verified new daemon.

## Independent failure-boundary finding

The intermediate review found that readable full-size RAM completion or
revocation records could survive a failed final synchronization/close. Treating
their contents as success could incorrectly advance to configuration removal.

P460 now requires a final atomic RAM success directory published only after
the completion record's checked close, followed by worker settlement. Normal
retirement also requires a fresh revocation claim and the successful return of
all its checked operations. An existing abort record cannot satisfy that
condition. P459's original wire format and retained producer records remain
unchanged. Dedicated full-size completion, failed abort-claim and revocation
failure cases exercise this boundary.

## Evidence and current validation

The initial H0 image uses an explicitly synthetic clean M=26 baseline. It is
not a fresh observation of the physical device. The five P459 final producer
expectations were independently rederived from the original source snapshot
and original authenticated control captures; they do not claim post-Android
retrieval. No historical approval, source snapshot or consumed action is
repinned.

The actual ARM64 normal path has passed two kernel boots with the installed
cron/PAM package, initial and installed Debian PID1, both 120-second local
service windows and the fixed SSH observations. The mount count advances
26→30. The first boot proves configuration creation without a report; the
second proves consumption, the 512-byte report, single unlink, new daemon
readiness and final configuration absence on the clean virtual filesystem.

For the new failure fixtures, the first guest executes its actual ordinary
reboot and QEMU exits at that boundary. The driver preserves the real clean
first filesystem and starts the second QEMU kernel on the same image/disk.
This explicit H0 hardware substitution preserves genuine inode/time identity;
it does not reconstruct configuration after the normal path has removed it.

One test observation required correction: after a checked partial creation and
the expected stop, the driver force-stops the failed kernel. A direct debugfs
read of that dirty image does not replay its committed journal and may not see
the newly created name. The live checked partial-write/stop evidence remains
valid; that raw lookup establishes neither post-stop presence nor absence.
The test must not turn this observation limit into a producer failure or a
reason to replay an effect.

The final source passes **49 actual ARM64 cases**: the normal two-boot path,
two clean controls, 22 retained root rejection cases, 12 configuration-root
cases and 12 configuration-runtime cases. The full production consumer
rederives all outcomes from the retained raw evidence. **71 focused tests**
also pass, including the existing P459 consumer, P460 factory selection,
authenticated phase/identity checks and final result serialization. The actual
normal VM proofs survive the production terminal's save/reopen path; a late
second-boot observation failure retains only first-boot proof.

The boot-only archive passes packaging with an explicit H0-synthetic result,
`physical_readiness=false`, and no physical `image.json`. A fresh isolated
Python process from an unrelated directory rejects that package through the
original physical image entry with `synthetic baseline cannot qualify device
use`. The same process independently rederives all 49 corpus results while
file writes, process execution, network and raw acquisition are denied.
The 154 host and 175 runtime source inputs remain unchanged. Python compilation,
ARM64 A/B build and ELF inspection, document links, diff whitespace and the
repository privacy boundary check pass.

The independent review rechecks the same 154 host and 175 runtime inputs,
original owner/recovery path, all 49 raw outcomes, actual AP/CPIO payload and
A/B identity in an effect-denied process. It returns **PASS_GO**, with no open
findings, for the capability only. The original capability consumer accepts
the newly recorded review. This does not grant a physical operation.

Private build, raw VM, packaging and review evidence is retained under
`workspace/private/outputs/s22plus-debian-cron-config-p460-h0-20261025-1/`.
The failed initial test observation and its original build remain preserved.

## Past-failure checklist and proof limits

ABI, IO, SEMANTIC, WIRE, PERSIST, ROUTE, ARTIFACT, AUDIT and HOST apply to the
compiled producer, exact configuration/report joins and original owner path.
ARM64 A/B compilation, checked real producers, authenticated distinct domains,
actual two-boot behavior, bounded raw captures and focused consumer tests
provide evidence, including the complete negative corpus above. DISPLAY is
inapplicable to this headless unit. RETURN remains the original attended
Download/original-A route and has not been exercised in this H0 work.

This work does not prove a physical P460 boot, unattended recovery, package
installation, general configuration management, guaranteed cleanup after
failure, or current/post-shutdown physical native_data consistency. A later
physical candidate still needs the reviewed fixed D0, fresh complete admission,
exact artifact/health/recovery binding and the existing finite attended grant.
