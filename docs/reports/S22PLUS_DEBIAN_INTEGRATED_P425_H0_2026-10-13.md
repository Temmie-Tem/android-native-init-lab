# S22+ Debian-owned integrated boot: P425 H0 implementation

Status: **DESIGN_RECORDED_IMPLEMENTATION_IN_PROGRESS**

The operator requested execution-code correction and qualification of a complete
Debian-owned initial boot through installed init, services and SSH. This report
records that structural implementation before the integrated runtime is changed.
It follows the [integration synthesis](S22PLUS_DEBIAN_INTEGRATION_SYNTHESIS_2026-10-13.md).
The selected target is only `SM-S906N/g0q/S906NKSS7FYG8`. No device action,
candidate consumption or grant is part of this H0 implementation.

## Bounded result

Produce one fresh boot-only integrated candidate with reproducible artifacts,
an actual ARM64 Debian initramfs-to-installed-SysVinit/SSH rehearsal, meaningful
negative paths, and an independent review of the reachable implementation.
Record Samsung-specific hardware substitutions separately. Completion of H0
qualification does not establish physical services, SSH or recovery.

P424 remains consumed and closed healthy. Its retained PRE and the earlier
P418 raw evidence motivate the binding correction; no historical execution,
source snapshot, journal or qualification is relabelled.

## Reuse and initial ownership

The retained FYG8 kernel starts the Debian-generated `/init` shell as actual
initial-namespace PID1. Fixed temporary children perform the minimal platform
preparation and measure that shell, `/init`, their source-bound executable and
current boot. The shell then execs a small fixed root-transition entry as PID1;
it owns no general native console, renderer or resident service manager. The
existing protected root admission, RAM witness, installed init and sequential
Debian startup hooks are reused. The final owner is installed SysVinit.

The first ACM descriptor is acquired by the temporary PID1 entry. The initial
shell measurement is explicitly a preceding same-boot observation, not a claim
that the shell remains PID1 after exec. Host challenge, root-transition proof,
installed-init proof, service progress and pinned SSH must join that same boot.
The native predecessor's `three-workers-reaped` claim is not applicable here;
actual absence of other userspace/children is required with a distinct label.

## Hardware sequence and observations

Correct the stock logger path to the observed `8.samsung,kernel_log_buf` and
distinguish module, driver link, resolved target and proc-backend failures.
The fixed module inputs keep their actual Image/export CRC and digest checks.

Compare actual effects with the successful native carrier, including intermediate
provider settlement rather than only the final module list. The native path has
a SPMI/PM8350c/GPIO binding barrier after platform module 67 and before the
GENI/I2C/Max77705 consumers. The prior early helper omitted that barrier.
The native path also publishes the first USB gadget before its UFS preparation;
the integrated order must account for this difference. Display-side suppliers
are under source review; the whole display runtime is not an assumed dependency.

Use the existing first `g1` object throughout ACM-to-NCM transition. Preserve
the fixed service observation: rcS and runlevel completion, then 13 samples of
init/cron/sshd over at least 120 seconds, before the authenticated release.
Keep bounded early RAM/retained evidence and the existing post-root durable
records. USB evidence loss, local progress and actual network access remain
separate results. Missing records never prove non-execution.

## Storage, closure and validation boundaries

Before native_data becomes writable, require the existing exact target/GPT,
partition RO, clean superblock, restricted checker and full immutable-root
admission, including the narrowly declared mutable data. No format, reinstall,
repair, general block writer or other-partition mutation is introduced.
Do not infer current dirty state from P415 or full current integrity from P422.

The intended terminal flow is the selected fixed SSH shutdown followed by one
attended physical original-A return and complete Android32 health. Unknown
execution or failed startup stops the candidate; original-A recovery remains
separately owned and never replays an uncertain transfer. Physical use requires
the reviewed exact integrated scope, current bindings and a fresh finite grant.

Validation will include the actual binding predicate on host and ARM64, A/B
helpers/initramfs/boot packaging, the real installed root and startup children,
same-boot authenticated service/SSH evidence, clean VM shutdown, and rejection
of wrong identity, incomplete providers, dirty/mismatched root and bad protocol
transcripts. Samsung module/UDC behavior remains a hardware substitution in VM.

## Current implementation evidence

The shared fixed logger predicate and all three existing consumers are corrected.
Fourteen binding fixtures passed on both host and ARM64 (28 executions), including
the observed name, the historical wrong name, missing nodes, wrong types/owners
and a dangling driver link. All three physical ARM64 consumers compile. These
results establish the correction's logic, not live probe completion.

Integrated implementation, full VM qualification and independent final review
are pending. Candidate P425 is reserved here as an H0 construction identity only.
