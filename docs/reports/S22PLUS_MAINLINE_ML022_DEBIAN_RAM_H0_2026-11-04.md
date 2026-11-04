# ML022: packaged Debian SysVinit as RAM PID1

Status: **H0 QUALIFIED / INDEPENDENT PASS_GO / FIXED D0 READY /
EXACT ATTENDED APPROVAL PENDING**.

After ML021 proved live mainline RAM PID1 and authenticated USB, the selected
next unit is actual Debian SysVinit as initial RAM PID1, directly starting one
fixed evidence child at runlevel 2. Two rounds each with Claude Opus 5.5 High
and Gemini 4 Argon High compared this with Type-C automation and further
baseline repeats. Both discussions preferred this bounded functional step.
These are advisory discussions, separate from independent capability review.

The candidate retains ML021's functional kernel, configuration, DT and PHY
correction, with a fresh key, candidate identity and V1 marker literals. The
identity-specific marker bytes require a fresh Image and loader build; unchanged
functional source and raw PHY/idle evidence can be reused at their exact input
scope. The retained ML021 grant is consumed and is never reused.

The RAM filesystem contains the exact signed Debian `sysvinit-core` 3.14-4
executable, its dynamic loader and three shared-library files from four fixed
arm64 packages, the static evidence child and a two-line inittab. `/init`
selects the package executable directly. The ordinary runlevel-2 `once` entry
uses SysVinit's direct-exec `@` syntax; no pre-init wrapper, shell, getty, SSH,
package manager, installed root or block-device workload is included.

Success requires the actual `/proc/1/exe` package hash; a measured child PID
above 1 with PPID 1; actual child executable and inittab hashes; runlevel 2 and
previous level N; single-level NSpid and equal PID namespace consistency; and
the existing kernel/DT/initrd, timer, CPU, zero-block-device and authenticated
one-response proof. Namespace equality is only a consistency check. Initial
namespace meaning depends on the reviewed boot path, its absence of namespace
creation and the actual packaged startup qualification. A new wire domain,
request/response magic and explicit artifact mode prevent legacy canary proof
from acquiring Debian meaning.

The standard package startup includes CAD-disable `reboot(0)` semantics,
signal handlers, console setup, RAM utmp/runlevel/initctl state, and the linked
libselinux's early proc/sysfs and unavailable selinuxfs probes. Its normal fixed
configuration requests no halt, reset or reboot. Other built-in package signal
and fault handlers are still present: the direct shutdown helper is absent,
and a SIGSEGV path may fork and attempt a RAM core file. The responder parks
after its one bounded exchange; that is not a claim that all SysVinit activity
or inherited hardware has stopped. Physical Download and the original A remain
the only qualified return/recovery route.

## H0 observations and selected checks

A small same-Image QEMU feasibility probe first proved direct packaged PID1,
runlevel 2 and PPID 1. The complete observer then exposed a setup incompatibility:
the linked libselinux leaves sysfs mounted, and the responder's second sysfs
mount returned EBUSY. A separate diagnostic build identified the exact failing
syscall before repair. The Debian-only repair checks `statfs(/sys)` for actual
SYSFS_MAGIC and uses that existing filesystem; it never accepts EBUSY alone.
The complete same-kernel VM then passed the new authenticated Debian proof.
All failed and successful H0 raw evidence remains private. These preliminary
probes do not replace the final candidate's exact VM/artifact qualification.

The fresh candidate now passes that qualification: packaged PID1 is 1, its
direct observer is PID 52 with PPID 1, and runlevel/previous are 2/N. The actual
ARM64 response passes the new host decoder. A separate wrong-key boot rejects
one request with no response. Complete positive raw evidence is independently
rechecked without another boot. The first qualification collector incorrectly
required a negative QEMU exit code even though QEMU handled SIGTERM and returned
zero; raw stderr identified normal host termination. The checker was corrected
and the same complete captures revalidated into a fresh result, without
rebuilding or restarting either VM.

The actual fresh loader passes 20 instruction cases, 1,051 copy cases and
three real exception-level entry cases. The V1 writers pass 342 cases and six
real exception-level cases. Two independently packaged boot/AP outputs match.
The larger Debian initramfs is included in the actual copy/layout checks.
All kernel source changes from ML021 are the fresh V1 literals; config, DT and
the seven compared PHY/idle objects match. Complete retained PHY and CPUidle
parameter evidence is reused with its original provenance.

Focused tests pass 67 cases across wire, raw socket, owner/terminal, return
identity and diagnostic-mode regressions, plus nine fixed-runtime artifact
cases. New cases reject cross-mode requests/responses, invalid child/parent,
namespace/runlevel, executable/inittab hashes and extra/mutated CPIO members.
The owner tests preserve one-shot original-A recovery if the lazy candidate
validator is unavailable. Touched Python compiles; both observer variants are
cross-compiled static AArch64 executables and the packaged init is AArch64 PIE.
The actual qualified image additionally passes admission, while six copied
mode/identity/qualification/parent-proof mutations are rejected.

Independent review verified all 104 source and 597 artifact/raw pins, reproduced
both sealed observer ELFs, rechecked the signed package and CPIO closure,
rederived positive/wrong-key VM captures without another boot and roundtripped
both APs to the actual loader. The new mainline capability and backend V28 are
qualified together. Prior receipts remain unchanged, and the live connector
confirms the same resident worker with a fresh reviewed backend per request.

The exact candidate and prospective task are prepared. One authorized fixed
preapproval D0 completed all seven original-Android health reads, each with
successful producer status and empty stderr. No grant, candidate control or
partition transfer occurred. The finite one-operation, 1800-second attended
approval remains a separate required input. The optional physical attach cue
retains all ML021 issuance, race, completion and separate Download conditions.

Applicable past-failure checklist rows:

- **ARTIFACT / SEMANTIC / ABI:** exact signed .deb members, recursive ELF
  dependency closure and actual package startup inspected. Fixed CPIO member
  names, types, ownership, nodes, symlinks and data are regenerated and compared.
  Final candidate cross-build, ARM64 wire and actual loader checks pass.
- **WIRE / ROUTE:** explicit Debian mode, domain, size and status are being
  joined through the live producer, raw capture, verifier and one-shot owner.
  Schema confusion, malformed proof and existing failure paths pass focused tests.
- **PERSIST / HOST / RETURN:** private raw-first capture, original 120-second
  observation window, one connection/request, one-shot N/A, final health and
  health-only continuation retain their existing scope. Representative owner
  failure tests and current source-bound review pass. Only the named fixed
  preapproval D0 ran in this unit; no control or payload was sent.
- **DISPLAY / persistent storage / watchdog:** no changed driver or workload;
  none is a new success prerequisite or a demonstrated capability here.

Private discussion, package/source inspection and before/after provider usage
records are under `workspace/private/outputs/s22plus-ml021-next-discussion-20261104-1/`.
Candidate work and preserved H0 failures are under
`workspace/private/outputs/s22plus-mainline-ml022-debian-ram-h0-20261104-1/`.
Token totals, account-wide quota movement, list-price estimates and unknown
subscription billing remain separate. No provider fallback or retry was used.

Independent review and fixed preapproval readiness are complete; the exact
finite attended approval remains pending. No new grant is armed. A90 and S20+ were not
accessed. Persistence, full Debian services, SSH, endurance, automatic recovery,
USB attach without replug and marker retention remain outside the result claim.
