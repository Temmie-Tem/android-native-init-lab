# S22+ resident native baseline V2 H0 qualification

Status: **H0 capability complete; independent PASS_GO with no blocking findings.**
Target: **SM-S906N / g0q / S906NKSS7FYG8**.

The [V2 policy](../operations/S22PLUS_NATIVE_BASELINE_V2.md) and its separate
common-incorporated exception implement normal `N -> E -> N`: an admitted
resident baseline, a distinct one-shot experiment, then restoration of the
same admitted baseline. Android A is the explicit exit or failure fallback.
There was no device contact, grant, operation reservation, transfer, live
bootstrap or admission in this H0 unit. P386's earlier thirty-minute observation
and completed Android return remain the last live result recorded by this work.

## Resulting capability

The existing baseline owner accepts a separate `native-baseline-v2` request and
private run root. P387 / v0.2.0-rc.5 is the proposed N; P388 / v0.2.0-rc.6 is the
first distinct E. One declaration catalog selects their exact runtime identity,
observer, byte inputs and archive interpretation. Both use the already qualified
resident C implementation. The initial E workload is the fixed native-health
pair with clean DETACH, descriptor close/reopen, fresh authentication, optional
bounded HUD evidence and exact timely CONTROL/Download return.

The role owner reopens N/E/A before departure, requires admitted N and fresh
same-boot native health, claims E globally once, and permits normal N restoration
only after the complete E workload and return proof. The restored N must have a
new boot identity, fresh nonces, two complete health authentications and actual
final DETACH/descriptor close. A terminal is a past authenticated health snapshot.

N admission binds its selected declaration and actual byte sources. The full
catalog remains a current host-review input, so adding E does not by itself
change N's native identity. Every N role has an exclusive intent; admission
never removes the original installation claim or permits an E replay. Native
service has no normal lifetime ceiling. Signed 64-bit authentication ordinals
remain separate from the finite three-reservation/600-second attended grant,
60-second observers and existing per-command/session limits.

Failure stops native work and leaves only the original exact A, at most once.
Its separately frozen recovery closure covers the sources actually used for
transport, archive, target, raw evidence and final health. It excludes unavailable
N/E AP/build inputs. The first A dispatch still reopens exact A and recovery
authority; proven A completion resumes health only, even if the old AP disappears.
Uncertain A delivery remains consumed and requires operator intervention.

## Production artifacts and H0 evidence

Selected private builds are under
`workspace/private/outputs/s22plus-native-baseline-v2/{p387,p388}/build-2/`.
Each reuses its already validated identical A/B static AArch64 init/renderer and
exact provider outputs, verifies all source/toolchain/linkage inputs, and creates
fresh identical A/B packages. Production readers decode the actual sole
`boot.img.lz4` member, compare the complete boot/ramdisk inventory and reopen A.
`file` identifies both init and renderer as static AArch64 executables. No new
native numeric syscall flags or resident C behavior were introduced here.

| Role | AP bytes | SHA-256 |
| --- | ---: | --- |
| Proposed P387 N | 31,150,121 | `98bc0e8f2f902a5e587afd9fe2a0f3ed61efed65a21efe0e9acf03b8414e9565` |
| One-shot P388 E | 31,150,121 | `79fe300fa2fc222a15f6e03c68a84e9b480d1701d213b246f65bf8ba046bcd34` |
| Exact Android A | 23,367,721 | `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` |

The H0 evidence directory is
`workspace/private/outputs/s22plus-native-baseline-v2-h0-20260912/`.
Earlier build/probe outputs remain retained; `review-probe-4` is the final
artifact/static/promotion/full-bundle qualification. Full combined N/E request
serialization is recorded separately and is not a physical target binding or
approval proposal.

The final single-N/E request is 184,423 bytes; the combined N/E request is
360,249 bytes (SHA-256
`6bca95f127960b497d1ad292e71051905425027152e491a9803ebad9cd00ba9a`).
It reopens through the actual request reader with only the H0 path namespace
redirected outside the live run root. Both remain below the unchanged 1 MiB
bound. The target is `H0_UNBOUND`, and no grant or approval proposal is created.

Validation covers:

- Eleven V2 tests using two independently compiled production resident C/PTY peers,
  actual protocol/HMAC/raw/descriptor/registry/AP/owner/final-health readers,
  and explicit USB/Odin/ADB/root-health fixtures. The full native-source terminal
  is 33,027 bytes for 121 native inputs and rederives through the actual reader.
- Normal N bootstrap, N-to-E-to-N and explicit A exit; native reentry beyond the
  former service ceiling; equal or consumed E rejection before departure;
  E/returned-N failures; grant expiry and recovery-source mismatch; missing
  native inputs during A recovery and health-only continuation after completed A.
- Twenty-one publication cuts before/after E/N/A start, delivery and result,
  plus native observer/terminal boundaries. Retained evidence stays unchanged;
  interrupted native roles and uncertain A intent never replay. Complete native
  raw/close proof supports H0-only terminal repair.
- Full N/E execution-source coverage, including conditional transport and
  final-health sources. Each real closure's 186 unique paths equals the reviewed
  source set; changing final-health input changes capability identity while an
  E-only catalog change preserves the selected N's native admission identity.
- Thirty-three existing baseline/protocol/backend/guard/health/terminal tests.
  Fourteen existing resident observer/backend/lifecycle/binding tests pass after
  the historical P386 receipt assertion is bound to its original commit
  `b555d6e0708fb27fbd57914000672ef0fff278f8`. All 118 historical native source
  inputs match; the consumed result and its source pins are unchanged.

The first and third full-bundle probes stopped when source inputs changed during
ongoing H0 implementation. The second passed; the fourth refreshes its source
receipts after review coverage was completed. The legacy test's
initial failure was a historical-source/current-checkout comparison, not a
device or runtime failure. Both initial outputs remain private evidence.

## Review, preservation and live limits

Independent review covers the common exception, target adoption and reachable
role/profile/archive/guard/raw/recovery closure. The final source set contains
186 inputs; its compact sorted JSON with trailing newline has publication SHA-256
`d34db8c9bc335bf87a4336f409262f918429916c57fac692eb2057fb72c79e88`.
The [published review receipt](../../workspace/public/src/device-action/bindings/s22plus_native_baseline_v2_review.json)
records **PASS_GO**, no findings, exact limits, source receipts and qualification
results. All 58 distinct tests pass. Selected Python compiles, document links,
policy pins, repository boundary and whitespace checks pass.

The public source binding uses the exact bytes selected for this scoped commit.
The separately retained working-tree variant has SHA-256
`f9f067806d777e2c1764a6f6481929efecc0e35290e49df31408c51043d8f738`;
only `AGENTS.md` differs. Pre-existing S20+ edits in that file and other files
are preserved and excluded; only the new common-details digest hunk is included
from the shared file. Independent review checks both complete AGENTS variants
and their S22 semantic equivalence. The published capability receipt deliberately
does not activate the differing local working tree. Its source check must fail
until that exact source-set mismatch is resolved under current review. No
working-tree edit, hash normalization, private receipt substitution or bypass
is used to open authority.

The original P386 execution sources were preserved before changes. Its consumed
run, original review and approval remain untouched. Native baseline V1's policy
bytes and common pin remain unchanged, and P385 admission/consumption is not
relabeled as resident admission. A90 and S20+ received no commands.

The next live proof is fresh attended P387 bootstrap qualification, followed by
a separately bound distinct E roundtrip under current finite authority. Neither
live resident admission nor the complete target N/E/N loop is proved here.
Physical pixels, uninterrupted liveness, CPU-sensor exposure and automatic
failure recovery retain their previous uncertainty. Capability PASS_GO creates
no device grant or unattended authority.
