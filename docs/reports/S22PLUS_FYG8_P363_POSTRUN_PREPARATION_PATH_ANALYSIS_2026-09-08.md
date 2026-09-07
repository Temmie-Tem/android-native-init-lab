# P363 post-run preparation-path analysis

P363 remains consumed, CLOSED/19 and `NO_PROOF_OBSERVER`, with exact rollback
and final health verified. This investigation performed H0 analysis and two
fixed exact-target root D0 metadata invocations. It performed no reboot,
module insertion, mount, native command, candidate transfer or recovery effect.
A90/S20+ received no command. No production execution source was changed.

The confirmed defect is silent loss of a preparation error before renderer
creation. The original native errno and first failing call remain unavailable;
the reproduction below does not identify that call in the consumed run.

## What the retained exchange actually proves

The actual prefix consumer replayed all 365 received and 208 transmitted bytes
with the bound private authentication key. Authentication, authenticated kernel
boot identity and the parent identity command passed. The sequence-4
`P363_DISPLAY_ONCE` frame was fully written by the host. No received byte follows
the identity response, and no CONTROL intent exists. The observer stopped at
`ten-submissions-and-return-ready-read` after 60.028114 seconds.

`authenticated-session-error` is the enclosing failure class, not proof that
HMAC authentication failed. Likewise, the terminal projection's zero completed
sessions and false display-proof fields must not be read as proof that no
sequence-4 host write occurred. A complete host write does not independently
prove native receipt, renderer creation or visible pixels. These clarifications
do not edit the consumed raw bytes, journal or terminal result.

The operator saw no pattern, only a black screen or logo. P361's prior visual
success and identical renderer bytes remain valid historical evidence. This
run does not independently establish whether that renderer started.

## Confirmed silent-error path

The generated P363 execution function consumes its display slot and calls
`p363_prepare_return()` before pipe creation, clone or renderer exec. Any
nonzero preparation return immediately exits that function. Preparation includes
same-FD module validation/insertion, SDAM provider checks, one read-only debugfs
mount, command-registry readiness and the final writer binding.

The inherited P353 console then recognizes the fixed display command and enters
an infinite `p282_poll_delay()` loop **before** examining that return value.
It publishes no preparation errno or failure stage. This previously supported
one-way display dispatch; P363 added preparation and a required response while
retaining that silent terminal branch.

Relevant public sources:

- [P363 preparation before renderer creation](../../workspace/public/src/scripts/revalidation/s22plus_fyg8_p363_research_shell_runtime.py)
- [Inherited display-command console park](../../workspace/public/src/scripts/revalidation/s22plus_fyg8_p353_research_shell_runtime.py)
- [Preparation operations](../../workspace/public/src/native-init/s22plus_native_return_modules_v1.inc.c)
- [Host readiness wait and enclosing failure projection](../../workspace/public/src/scripts/revalidation/s22plus_fyg8_p363_research_shell_observer.py)

Four regenerated functions matched the executed build's saved C byte-for-byte.
The actual init ELF matched the qualified digest. Its AArch64 disassembly also
shows the execution-function return followed by the display-command branch into
an unconditional delay loop before the generic nonzero-return check. Thus this
is present in the transferred binary, not merely in a later source description.

## Behavioral reproduction and its limits

A bounded local-socket test used the actual C framing, authentication, console
and park logic with the existing H0 platform wrappers. Only the preparation
result was injected; it did not call a real module loader or reboot syscall.
Two distinct failures, `ENOENT` and `EPROTO`, both produced:

- successful authentication and parent identity exchange;
- no renderer creation and a live parent parked indefinitely;
- no CONTROL intent and a host readiness timeout;
- the same 365/208-byte receive/transmit lengths as the live record.

These are structurally matching exchanges, not byte-identical transcripts:
nonces and other fixture values differ. Different preparation failures collapse
to the same observed outcome. The test proves the information-loss mechanism,
not which error or kernel operation occurred on the S22+.
The host reproduction passed; its C fixture also cross-compiled to a static
AArch64 ELF. The existing module tests mock finit_module, provider metadata and
registry reads; the full protocol tests replace module preparation with success.
Their prior PASS did not qualify real stock module probe completion.

## Conditions checked without another candidate

Exact root D0 verified current Android health before and after each invocation.
Both expected SDAM DT suffixes, `sdam@7100` and `sdam@7200`, occurred exactly once.
The dynamically numbered provider names are not identities. All five stock
modules report `live` in current Android. This checks the intended stock paths;
it does not prove their preparation in the consumed native boot.

The debugfs registry file was not readable from the current root invocation.
A separate D0 showed debugfs registered in `/proc/filesystems`, its mount point
present, and no `debugfs=` override in the current kernel command line. The
actual candidate Image's embedded configuration enables `CONFIG_DEBUG_FS` and
`CONFIG_DEBUG_FS_ALLOW_ALL`. Thus absence of compiled debugfs support is not an
explanation; registry availability in the native run remains unproved. No mount
was attempted to turn this observation into a different device action.
Linux documents filesystem registration separately from compiled debugfs APIs;
the local target source was checked for its actual behavior rather than assuming
current upstream behavior transfers to this device. See the
[kernel parameter documentation](https://www.kernel.org/doc/html/v5.15/admin-guide/kernel-parameters.html?highlight=pcie_aspm).

The previous exact stock module dependency/CRC audit found no unresolved edge;
that result was retained, not upgraded to probe success. Source and stock ELF
inspection agree that sec_qc_rbcmd registers its command table asynchronously.
The final writer is not required by that registration path, so no such circular
registration dependency was found. The actual qcom-dload-mode parameter setter
calls SCM operations for `download_mode=0` and returns its boolean-parser result;
SCM/probe completion in the native run is not established by this analysis.
Renderer submission-line spelling matches the parent parser, and the native tty
is opened nonblocking. No evidence supports changing renderer pixels, retrying a
module or merely increasing the timeout.

## Separate USB recovery incident

USB snapshot23 failed with endpoint departure after candidate observation closed.
It did not cause the earlier absence of readiness evidence. The physical cause
remains unproved. Same-journal exact rollback and final health stay verified.
Neither the USB diagnostic nor successful recovery identifies a preparation errno.

## Smallest next evidence requirement

Another native observation needs to preserve a bounded stage and return code
before the existing terminal park: preparation entry, each module insertion,
provider/registry checks, final binding and renderer creation. A pre-call stage
would identify the last entered operation even if it never returns; a returned
error must reach the host before parking. Records should contain fixed stage
IDs and bounded codes, not pointers, memory contents or arbitrary text.
Partial protocol progress must be reported separately from complete candidate
qualification. The renderer can remain unchanged. Missing preparation proof
must still prohibit native Download and retain physical recovery.

This is a diagnosis requirement, not an implemented or activated successor.
The actual first failing native call cannot be recovered from the retained
transcript. A fresh diagnostic capability needs its scoped implementation,
independent review, qualification and fresh attended F1 binding; P363 is never
replayed. The operator's investigation D0/D1/root permission does not authorize
a new candidate transfer.

Private evidence is under
`workspace/private/outputs/s22plus_fyg8_p363/postrun-analysis-20260908-1/`, with
exact D0 records under `workspace/private/runs/device-action-d0-p363-postrun/`.
`phase-and-failure-result.json` and `analysis-evidence-join.json` bind the replay,
reproductions, actual init/source identities, disassembly and D0 receipts.
