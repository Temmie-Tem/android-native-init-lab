# S22+ FYG8 P2.60 E3 ACM-banner design

Date: 2026-07-25 KST
Tier: H0
Status: `DESIGN_COMPLETE_P260_E3_ACM_BANNER_H0`
Device authority: none
Build or image authority: none

## Objective

Prove one exact native-PID1-to-host byte stream over generic CDC ACM while
preserving the P2.58A provider, transfer, rollback, and retained-evidence
closures.

E3 succeeds only when one run proves both:

1. the candidate reached its retained E3 terminal record; and
2. the host received the exact candidate-bound banner from the exact new ACM
   endpoint.

Neither half alone is E3 PASS. E4 request/response and every larger runtime
remain out of scope.

## Inherited proof

P2.58A already proves:

- the exact 60-module plan and order;
- every provider and driver-bind gate through
  `msm-dwc3/a600000.ssusb` and `dwc3/a600000.dwc3`;
- exact membership and identity of `a600000.dwc3` in `/sys/class/udc`;
- terminal native userspace execution;
- exact boot-only candidate and rollback transfers;
- retained A/B record decoding;
- final Android/root/supporting-partition health; and
- the canonical eight timeline events.

P2.60 does not reopen those findings. In particular, the exact accepted
`msm-dwc3/a600000.ssusb` symlink proves the FYG8 `mode` attribute owner. The
P2.59 external-review claim that the SSUSB driver remains ambiguous is retired.

The exact qualified kernel also contains configfs, libcomposite, generic ACM,
gadget serial, DWC3 gadget, and the needed UDC sysfs attributes. The matching
source proves:

- creating `functions/acm.usb0` allocates and registers `ttyGS0`;
- disconnected gadget-side writes queue in the serial FIFO;
- later `gserial_connect` starts transmission;
- `state` and `current_speed` are read-only UDC attributes; and
- `soft_connect` is a write-only escalation lever, not a primary-path
  requirement.

## Scope split

P2.60 changes two bounded closures:

1. **candidate source contract:** extend the P2.58A prefix with configfs,
   generic ACM, one queued banner, and post-bind state coordinates;
2. **Process v2 observation:** add one optional typed CDC-ACM observer, durable
   receipt recovery, and E3 `all_of` verdict semantics.

It does not change:

- the target profile;
- the 60-module plan or order;
- the checkpoint request ABI or retained slot layout;
- Odin invocation or boot-only archive rules;
- the state-machine transitions;
- the eight timeline event names;
- rollback or final-health logic; or
- permanent device boundaries.

## Versioned retained contract

P2.60 gets a new source-contract ID, run-ID domain, contract spec, decoder, and
source selector entry. The kernel request profile remains numeric profile 3,
reported to the host as `E2`, because E3 is an external capability rung over
the same E2 checkpoint ABI. Introducing profile 4 would change the request ABI
without adding proof.

The new step sequence is the complete P2.58A prefix through stage `0x87`,
followed by eight local E3 stages and a moved terminal:

| Stage | Kind/item | Exact progress claim |
|---|---|---|
| `0x88` | local/0 | `/config` is mounted as configfs and its filesystem magic is exact. |
| `0x89` | local/0 | One fresh gadget tree, descriptors, strings, `max_speed=high-speed`, configuration, ACM function, and exact function link are read back. |
| `0x8a` | local/0 | `ttyGS0` class identity and bounded `major:minor` are exact. |
| `0x8b` | local/0 | Matching `/dev/ttyGS0` is a character node; one owned nonblocking FD is open with raw termios read back. |
| `0x8c` | local/0 | The complete exact banner has been queued on that FD. |
| `0x8d` | local/0 | SSUSB is peripheral and the exact real UDC has reappeared after any role transition. |
| `0x8e` | local/0 | The gadget `UDC` attribute reads back exactly `a600000.dwc3`. |
| `0x8f` | local/0 | The UDC reports exactly `state=configured` and `current_speed=high-speed`. |
| `0x90` | terminal/0 | E3 device-side terminal success; the gadget FD remains open while PID1 parks. |

There are 89 total descriptors. Terminal ordinal is 88 and terminal generation
is 89. A successful retained A/B pair is expected to end with generation 88 at
stage `0x8f` and generation 89 at terminal `0x90`.

The contract spec, generated checkpoint table, kernel validator, runtime,
decoder, and tests must all derive this geometry from one descriptor source.
No independent stage allowlist, terminal constant, item bound, or generation
constant is permitted.

## Failure semantics

P2.60 adds no detail band.

- syscall and parser failures retain positive errno-form details in
  `0x001..0x7ff`;
- a missing previously proven E2 gate uses `0x800 + gate_index`;
- a malformed/read-error E2 gate uses `0x900 + gate_index`;
- timeout uses `ETIMEDOUT`;
- an exact readback mismatch uses the narrowest existing errno-form value,
  normally `EIO`, `EINVAL`, `ENODEV`, or `EPROTO`.

Before each E3 checkpoint, the runtime revalidates the established E2 gates in
ascending order. The earliest regression wins and is recorded at the current
E3 frontier stage, preserving generation monotonicity. Stage `0x8d` is allowed
to poll through a temporary UDC absence caused by a real role transition; it
must re-establish the exact P2.58A UDC oracle before publishing progress.

A checkpoint-store failure still parks on the last durable coordinate. It
must not continue side effects after losing its retained witness.

## Device-side sequence

### 1. Configfs

Create `/config`, mount configfs with `MS_NOSUID | MS_NODEV | MS_NOEXEC`, and
accept `EBUSY` only when `statfs` proves `CONFIGFS_MAGIC`.

Create one gadget under `/config/usb_gadget/g1`. Every directory, regular
attribute, and symlink is bounded and read back. Unexpected pre-existing
objects, non-directory types, wrong symlink targets, short writes, or
normalization mismatches fail closed.

The fixed local-lab descriptors are:

```text
idVendor       0x04e8
idProduct      0x6861
bcdUSB         0x0200
bcdDevice      0x0003
manufacturer   Android Native Init Lab
product        S22+ E3 ACM
configuration  acm
bmAttributes   0x80
MaxPower       500
max_speed      high-speed
function       acm.usb0
```

Only the configfs gadget `max_speed` is written. The SSUSB `speed` attribute is
not written: FYG8 source shows that changing it can schedule asynchronous USB
restart work. Capping the gadget driver at high speed is sufficient and avoids
that extra state transition.

### 2. Candidate-bound identity

The existing 16-byte source-contract run ID is reused; no live challenge is
introduced.

```text
USB serial = "S22E3" + lowercase_hex(run_id)
banner     = "S22PLUS-FYG8-E3:" + lowercase_hex(run_id) + "\n"
```

The serial is 37 ASCII bytes and the banner is 49 bytes. Both are generated by
the P2.60 contract spec, embedded in the runtime, reproduced by the manifest
builder, and re-derived during offline bundle validation. A manifest literal
that differs from the verified candidate run ID fails before D0.

Exact literals and raw bytes remain private. Tracked evidence records only the
format, size, source-contract identity, and SHA256.

This is candidate/build binding, not E4 freshness. Approval already binds the
candidate AP, manifest, source closure, and expected ACM values.

### 3. TTY materialization and raw mode

Creating `functions/acm.usb0` must be followed by a bounded poll for
`/sys/class/tty/ttyGS0/dev`. Parse exactly one bounded decimal
`major:minor` pair with overflow rejection.

Create `/dev/ttyGS0` only when absent. If it already exists, require a regular
direct path to a character node with matching `st_rdev`; never unlink an
unexpected node.

Open once with:

```text
O_RDWR | O_NOCTTY | O_NONBLOCK | O_CLOEXEC
```

Use `TCGETS`, a local `cfmakeraw` equivalent, `TCSETS`, and `TCGETS` readback.
The verified result must have input, output, and local processing disabled and
an 8-bit `CLOCAL | CREAD` control mode. No `tcflush` occurs.

This is load-bearing. FYG8 initializes gadget serial from `tty_std_termios`,
whose defaults include `OPOST | ONLCR`, canonical mode, and echo. Full write
count without raw mode would not define exact wire bytes.

### 4. Queue before connect

Write the 49-byte banner through the one owned nonblocking FD before role
selection and UDC binding. Retry only `EINTR` and bounded `EAGAIN`; require
complete progress and exact total count.

Do not close, reopen, flush, or write the banner again. The same FD remains
open through stages `0x8d..0x90` and the terminal park. This preserves the
disconnected FIFO and removes host-open timing from the device path.

### 5. Role and UDC bind

Read `/sys/devices/platform/soc/a600000.ssusb/mode` first.

- exact `peripheral`: skip the write;
- exact `none` or `host`: write `peripheral`, then poll exact readback;
- malformed or any other value: fail closed.

After a write, poll the P2.58A UDC oracle for at most five seconds. Do not bind
until exact `a600000.dwc3` membership and symlink identity are restored.

Require the gadget's `UDC` attribute to be empty before its first write. Write
`a600000.dwc3` once and require exact readback. Never unbind or retry the bind
in the primary path.

### 6. Post-bind discriminator

For up to 30 seconds, poll:

```text
/sys/class/udc/a600000.dwc3/state
/sys/class/udc/a600000.dwc3/current_speed
```

Publish stage `0x8f` only when they are exactly `configured` and `high-speed`.
Continue checking exact UDC membership and prior-gate regression during the
poll. A configured non-high-speed state is `EPROTO`; a bounded non-configured
state ends as `ETIMEDOUT`.

This is the only new post-bind diagnostic. `soft_connect`, tracefs, debugfs,
Type-C policy emulation, and general USB tracing remain later escalation
options only if this coordinate requires them.

## Manifest extension

The existing retained `acceptance` object remains unchanged. E3 adds one
optional sibling:

```json
{
  "observation": {
    "timeout_sec": 90,
    "acceptance": {"kind": "...", "source_contract_id": "...", "profile": "E2"},
    "candidate_observer": {
      "kind": "exact_cdc_acm_banner_v1",
      "usb_vendor_id": "04e8",
      "usb_product_id": "6861",
      "usb_serial": "<private candidate-bound value>",
      "usb_driver": "cdc_acm",
      "usb_interface_number": "00",
      "banner_hex": "<private exact bytes>"
    }
  }
}
```

For retained-only manifests, `candidate_observer` is absent and legacy verdict
semantics remain intact. For E3 it is mandatory and exact-key validation
applies.

The generic core validates shape and bounds. The selected source contract
re-derives the expected E3 observer object from the verified candidate run ID.
This avoids copying P2.60 constants into the generic runner.

The approval binding already includes the complete `observation` object and
therefore binds the candidate observer without a new approval primitive.

Implementation bumps the host-core and live-adapter versions. Historical
closed runs remain evidence at their original commit; no active transaction is
being migrated.

## Host interference guard

The current host runs ModemManager, and the E3 ACM interface has the
class/subclass/protocol shape that the strict filter accepts as an AT-capable
candidate. Opening with `TIOCEXCL` after enumeration is insufficient because
ModemManager may win first.

The original design used manager-level `InhibitDevice`. Two pre-candidate live
aborts corrected that design:

1. the installed D-Bus policy permits `InhibitDevice` only to root; and
2. after root authorization, ModemManager returned
   `WrongState: Modem not exported in the bus`.

The second result is structural. Upstream `mm_device_inhibit()` explicitly
rejects a device until a modem object has completed probing and is exported,
because inhibition during probing would split port ownership. Therefore that
API cannot protect a future ACM interface before ModemManager probes it.

E3 instead installs one transient, candidate-exact udev filter before Download:

```text
/usr/bin/pkexec /usr/bin/setpriv --pdeathsig SIGTERM \
    /usr/bin/python3 -I -B -c <closure-bound-root-helper> \
    <base64-exact-rule> <rule-sha256>
```

The unprivileged observer renders and hashes the exact rule before launching
`pkexec`. The root process receives an immutable argv snapshot of the embedded
stdlib-only helper and rule payload; it does not import or execute a
user-writable repository file after authorization. The helper validates the
payload against a strict grammar and hash, creates one fixed file under
`/run/udev/rules.d`, verifies it with absolute-path `udevadm verify`, reloads
udev rules, and prints one hash-bound arm line. The two rules match only the
approved candidate's exact VID, PID, serial, interface, and prepared physical
topology. They set
`ID_MM_DEVICE_IGNORE=1` on the USB device and both
`ID_MM_DEVICE_IGNORE=1` and `ID_MM_PORT_IGNORE=1` on its TTY. No current
Android identity matches this rule.

The helper removes the file and reloads udev on normal release, EOF,
`SIGTERM`/`SIGINT`/`SIGHUP`, or a 300-second self-deadline. Parent death sends
`SIGTERM`. A stale or changed fixed rule is fail-closed rather than overwritten.
Launch and arm failures retain at most 16 KiB of raw output and a structured
failure receipt under the private run directory.

Rules:

- install the exact temporary rule regardless of the service's current active
  state, because activation can race future enumeration;
- failure to install, verify, reload, retain, or cleanly release the exact
  temporary rule is fail-closed and never treated as an armed guard;
- the candidate endpoint must retain both udev ignore properties and its exact
  physical path and USB identity before the TTY is opened;
- the root helper receives parent-death protection and is held through
  candidate observation;
- early child exit invalidates ACM acceptance;
- normal release uses the helper control pipe and is bounded; a release
  problem is recorded and never blocks the already authorized rollback, but
  it prevents E3 PASS.

No global `systemctl stop`, daemon configuration edit, `/etc` or `/usr` udev
change, or persistent host policy change belongs in E3.

## Exact host endpoint selection

Before Download, store an immutable private baseline proving that the exact E3
VID/PID/serial is absent and recording hashes of existing ACM identities.

After candidate transfer and exact Download departure:

1. scan `/sys/class/tty/ttyACM*` and `/sys/bus/usb/devices` directly;
2. require exactly one new endpoint matching VID, PID, synthetic serial,
   `cdc_acm`, interface `00`, and the prepared physical topology;
3. require the tty sysfs object and `/dev` node to agree on character-device
   major/minor;
4. open with `O_RDWR | O_NOCTTY | O_NONBLOCK | O_CLOEXEC`;
5. require `TIOCEXCL`;
6. set host raw termios without any input/output flush;
7. read at most `expected_banner_size + 1` bytes until the 90-second
   observation deadline;
8. require exact byte equality;
9. wait a fixed 250 ms no-extra-byte settle; and
10. revalidate FD, sysfs identity, driver, serial, and topology.

Other unrelated ACM endpoints are allowed. Basename alone, first
`/dev/ttyACM0`, udev display strings, or token containment can never select the
candidate.

The existing historical `HostTTY.open(flush=True)` helper is not suitable:
`TCIOFLUSH` can discard the prequeued banner. E3 either uses a dedicated small
observer helper or an explicit `flush=False` path with a behavioral prequeued
byte test.

## Durable observation receipt

Raw bytes are written first to an exclusive private regular file and fsynced.
Only then is an exclusive JSON receipt written and fsynced. The receipt binds:

- approval binding, bundle, manifest, and candidate AP hashes;
- candidate-observer specification hash;
- Download-departure receipt;
- physical-topology and endpoint-identity hashes;
- ModemManager guard receipt hash;
- raw file path, size, and SHA256;
- exact/extra-byte result;
- bounded timing; and
- one classification.

Expected classifications are finite and non-throwing after candidate transfer:

```text
accepted
endpoint-timeout
endpoint-ambiguous
identity-mismatch
open-failed
exclusive-failed
guard-lost
read-timeout
byte-mismatch
extra-byte
interrupted-before-receipt
```

These are host observation outcomes, not retained `detail` values. Expected
negative outcomes proceed directly to rollback rather than requiring a second
runner invocation.

`OBSERVED` is appended only after a valid bound receipt exists. Its journal
details and `live-state.json` contain receipt hashes and classification, not
raw identifiers or banner bytes.

## Resume semantics

Recovery reopens observation evidence before normalizing `CANDIDATE_FLASHED`.

- valid accepted receipt: re-derive `candidate_observer_accepted=true`;
- valid diagnostic receipt: preserve its exact non-positive classification;
- raw file without a committed receipt: ignore it and record
  `interrupted-before-receipt`;
- missing evidence: record `interrupted-before-receipt`;
- malformed or binding-mismatched evidence: fail closed for proof while
  continuing the preauthorized rollback path.
- cleanup-confirmed guard expiry or uncommanded exit: preserve an already
  accepted exact ACM receipt with `candidate_observer_guard_warning`; if ACM
  is absent, classify the observation as indeterminate and refuse E3 PASS;
- missing, malformed, stale-instance, or cleanup-uncertain guard-release
  evidence: re-derive `candidate_observer_guard_released=false`, continue
  rollback, and refuse E3 PASS.

The resumed `candidate_boot_ready` event uses both re-derived ACM and
guard-release values. It must not unconditionally write `proof:false`, repeat
candidate observation, or repeat candidate transfer.

A parser/report failure after a valid receipt cannot downgrade the evidence or
cause another live transition.

## Verdict matrix

For E3 define:

```text
C = exact candidate transfer completed
D = Download endpoint departed
A = exact bound ACM receipt accepted
G = guard result supports the observation: commanded release, or exact ACM
    plus cleanup-confirmed expiry/uncommanded-exit warning
R = post-rollback retained E3 terminal accepted
K = exact rollback and final health complete
```

`K` is mandatory for every closed non-recovery result.

| C/D | A | G | R | Closed verdict |
|---|---:|---:|---:|---|
| true | true | true | true | `PASS_F1_V2_CANDIDATE_PROVEN_AND_ROLLED_BACK` |
| true | false | true | true | `DIAGNOSTIC_F1_V2_RETAINED_ONLY_ROLLED_BACK` |
| true | true | true | false | `DIAGNOSTIC_F1_V2_ACM_ONLY_ROLLED_BACK` |
| any | false | false | any | `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK` |
| otherwise | any | false | any | `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK` |
| otherwise | any | true | any | `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK` |

Impossible combinations, such as accepted ACM evidence without the bound
candidate transfer or Download departure, are result-validation errors and
cannot close.

`candidate_boot_ready.proof` means `C && D && A && G`. Retained acceptance is
not available until after rollback and therefore belongs only in the final
verdict.

For manifests without `candidate_observer`, the current retained-only PASS and
no-proof rules remain unchanged. The implementation must branch by observer
kind rather than globally weakening legacy validators.

## Implementation closure

P2.61 should add or modify only:

- one P2.60 contract spec, decoder, source contract, linked audit adapter, and
  selector entries;
- generated E3 runtime/checkpoint/plan materialization through that source
  contract;
- one generic `device_action_cdc_acm_observer_v1.py` helper;
- the manifest validator and source-contract observer binding;
- live orchestration, durable observation validation, resume, and verdict
  matrix;
- focused tests and implementation report; and
- the canonical Process v2 documentation after behavior exists.

Do not fork a candidate-specific live runner. Do not copy the 60-module plan,
P2.58A UDC oracle, Odin wrapper, rollback code, or final-health code.

## Static validation

Implementation is not complete until all of the following pass.

### Contract and runtime

- P2.58A prefix, module plan, and gate identities are byte-identical.
- The new step sequence has 89 descriptors and terminal generation 89.
- Removing, reordering, duplicating, or changing any E3 stage fails.
- Independent kernel-validator generation accepts every exact stage and
  rejects old-terminal or wrong-item requests.
- The P2.58A decoder still replays its historical records unchanged.
- The P2.60 decoder accepts only its own run ID and exact terminal geometry.
- Two source generations and two freestanding links are byte-identical.
- A static AArch64 link has the intended entrypoint and contains no libc/CRT.
- Runtime and manifest serial/banner derivations are byte-identical.
- Generated-C semantic fixtures cover raw-termios masks, identity formatting,
  role no-op/write decisions, UDC state/speed decisions, and failure mapping.

### Host observer

- exact endpoint, duplicate, absent, wrong topology, wrong driver, wrong
  interface, wrong serial, and stale-baseline fixtures;
- prequeued banner survives open and raw setup, proving no flush;
- partial, mismatch, extra-byte, timeout, disconnect, and identity-change
  fixtures;
- mandatory `TIOCEXCL` failure;
- exact transient-rule arm, embedded-helper compilation, payload/hash binding,
  verify/reload failure, early or nonzero helper exit, missing ignore
  properties, collision, and cleanup fixtures;
- exact embedded-helper lifecycle in an isolated user namespace, with ordered
  `verify`, arm reload, release unlink, and cleanup reload calls;
- immutable raw/receipt ordering and crash injection at each boundary;
- accepted, diagnostic, missing, malformed, and stale receipt resume cases;
- exhaustive E3 verdict truth table and legacy retained-only regression;
- canonical eight-event timeline with no ad-hoc timeline shape; and
- no raw actual device serial, topology, or private banner in tracked output.

Use no-LTO or thin host builds for these loops. Full LTO is reserved for the
final candidate after source readiness and independent review.

## Review and rollout

Because P2.61 changes the manifest validator, live runner, resume path, and
verdict logic, one independent safety review is mandatory. Review only:

- candidate-observer schema and source binding;
- ModemManager/TTY ownership;
- raw receipt and resume;
- the E3 verdict matrix; and
- unchanged rollback reachability from every post-candidate failure.

The review does not reopen Odin, module-provider, target-profile, or
supporting-partition policy.

After host implementation and review:

1. derive a fresh candidate intent;
2. run two clean reproducible Full-LTO builds;
3. independently compare and qualify the boot-only AP;
4. create a private E3 manifest;
5. run ordinary connected D0 preparation;
6. obtain one fresh exact F1 approval; and
7. execute one candidate attempt plus mandatory rollback.

No approval is carried by this design.

## Explicit non-goals

- no E4 host-to-device nonce or command;
- no shell, login, supervisor, NCM, network, Debian, or hot reload;
- no Samsung `usb_f_ss_acm.ko`;
- no module-plan growth or reorder;
- no DT/DTBO or kernel-config change;
- no global ModemManager stop or persistent udev edit;
- no SSUSB speed write;
- no `soft_connect` in the primary path;
- no Type-C/PD policy emulation;
- no repeated banner or reconnect loop;
- no new timeline event or state-machine transition;
- no candidate, D0, F1, build, image, or device action in P2.60.

## Design verdict

```text
DESIGN_COMPLETE_P260_E3_ACM_BANNER_H0
```

The next bounded unit is P2.61 implementation and static validation. It remains
H0 and must stop before any Full-LTO candidate build or connected/device step.
