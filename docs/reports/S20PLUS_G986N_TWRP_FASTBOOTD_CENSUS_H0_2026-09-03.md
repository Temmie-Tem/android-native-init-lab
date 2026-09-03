# S20+ G986N retained-T2 volatile fastbootd census H0

Status: `CONSUMED_NO_PROOF_RETURNED_HEALTHY_TERMINAL`

## Corrected starting fact

The exact retained T2 image does contain the donor fastbootd binary and generic
system service bytes, but its selected root USB policy is intentionally
ADB-only. `SAFE_USB_RC` creates only `ffs.adb`, redirects a fastboot property
request to ADB, and its validator rejects `ffs.fastboot`, a fastboot FunctionFS
mount, or `start fastbootd`. Therefore an as-is read-only TWRP fastbootd census
was not a real live path. No device command was sent after discovering this.

The earlier classic-fastboot report and `GOAL_S20PLUS.md` now preserve that
distinction. Stock recovery has a structural fastbootd handoff; retained T2
has dormant binary/service substrate behind its deliberate ADB-only root USB
policy.

## Smallest nonpersistent successor

The repaired successor does not build or flash T3. It begins only in the
proved retained T2 recovery and uses one fixed no-input root-ADB script to:

1. mount one volatile FunctionFS instance named `fastboot` on the fixed
   existing `/dev/usb-ffs/fastboot` directory with fixed ownership options;
2. create the one absent volatile configfs `ffs.fastboot` function;
3. start the already defined fastbootd service and wait for its endpoints;
4. detach only the current volatile recovery gadget;
5. leave the adbd process untouched and replace only the validated configfs
   `f1` link from `ffs.adb` to `ffs.fastboot`;
6. set exact `18d1:4ee0`, `bcdDevice=0100` identity and rebind the same `a600000.dwc3`
   controller; and
7. leave all changes confined to that recovery boot's service, configfs,
   FunctionFS, and `/tmp` state.

The script opens no block device and changes no persistent file or persistent
property, image, partition, module, or package. Its fixed `ctl.start fastbootd`
property write is a volatile service control. Physical
System reboot clears the volatile state and remains the recovery path. Because
it does perform volatile service/configfs writes, the entry is classified D1
rather than mislabeled read-only.

## Census surface

The host accepts only one same-serial, same-topology `18d1:4ee0` endpoint with
one `ff/42/03` bulk interface with exact `bcdDevice=0100`. The pinned official Google fastboot may send
only these fixed requests, once each and in order:

1. `getvar is-userspace` — must return `yes`;
2. `getvar product`;
3. `getvar version-bootloader`; and
4. `getvar max-download-size`.

There is no `getvar all`, download phase, payload, boot, flash, erase,
set-active, reboot, fetch, OEM, logical-partition, lock/unlock, or
caller-selected command. Raw command bytes are captured durably before parsing.
The result remains pending until physical System return and fresh exact healthy
Android are proved.

## Implementation identity

- active runner: 60,738 bytes, SHA-256
  `9e89e9fd56630d571270faa2ee9410049c4fb8b5bd9ae8800f9a9bf840ac6225`;
- activation-normalized runner SHA-256:
  `7ea137f132f00f6fa208b647b9374d0e844560f0010174b6445d0a9d48bdd7be`;
- focused test: 33,031 bytes, SHA-256
  `f4ebe28f3114c18fa3aa8c3cd1dd4e0c652c0678a06434ebe08607b436a3036d`;
- preflight script: 2,044 bytes, SHA-256
  `ce11dd0302c3bad95d5a1be5729e65e9805259cfdeb9b09fa3c64825895418f7`;
- inner volatile-control script: 2,201 bytes, SHA-256
  `5aad2d2b57b20466a687cc9e5214ec45f386f65bf094ff5388f6ae77348efc23`;
- launch script: 2,969 bytes, SHA-256
  `48a554854395191f53d505a27498c56094d61d1b81bee29cf7330206f6abbf90`.

The runner pins the retained T2 predecessor, target/boot identity readers,
raw-capture path, Android health parser, classic census helper, and the
3,333,552-byte Platform-Tools fastboot SHA-256
`a686e2c7e8dc9cf4cba0cb8a2eef05f7b2bd682c925abd032fe203215d80b618`.

## H0 validation and authority

Twenty-three focused tests cover the activation gate, exact T2 ADB-only correction,
fixed preflight grammar, closed volatile script, endpoint binding, intent
ordering, exact four-query surface, `is-userspace=no` early stop, broken-link
and forged-receipt rejection, resumable pre-effect cuts, strict terminal/journal
validation, and fresh finalizer raw capture namespaces. `py_compile` and
`git diff --check` pass. The actual
43-node retained T2 predecessor and terminal SHA-256
`da24acd3b33c78f4ed41565858e5314bb2c3a1acaf020ac06fb83fd99ab84d05`
also revalidate host-only.

The first activated invocation stopped before preparation or enable intent:
four bounded recovery-ADB reads ran, while fastbootd/service/configfs changes
and fastboot requests remained zero. The guard was released and the consumed
marker remains absent. Its preflight expected recovery `bcdDevice=0100`; the
same bound USB topology proved the exact retained T2 actually enumerated as
`0419`. The repaired dormant bytes require `0419` before the effect and write
exact fastboot `0100`, manufacturer `samsung`, and product `SM-G986N` only
while detached. The next clean invocation again stopped in preflight with four
read-only ADB captures and no prepared/enable/entry/probe node, effect, guard,
or consumed marker. Because host descriptors do not prove configfs file bytes,
the repaired runner snapshots fixed nonsensitive fields before the host exact
comparison. That snapshot proved the fastboot FunctionFS mount was absent and
configfs `bcdUSB=0320`; all other reported prerequisites matched. The dormant
repair therefore binds that exact start and mounts only the fixed volatile
FunctionFS instance after enable intent. Independent boundary review returned
`PASS_GO` with findings `0/0/0`; runner, registry, target status, tests, report,
and goal were mechanically activated together.

The sole mount-bearing invocation then published its enable intent and an
`armed=true` result, but no exact `18d1:4ee0` entry arrived within the bounded
observation and no getvar intent was created. Replay remained false. Physical
TWRP System return produced fresh exact healthy Android; the terminal verdict
is `NO_PROOF_S20PLUS_G986N_TWRP_FASTBOOTD_RETURNED_HEALTHY`. The 1,456-byte
final result SHA-256 is
`8979538332be37879700b2f455e77eb9e12c1ed4ccc3efbdb5d7d49bde90b0a4`.
Persistent writes, partition operations, fastboot mutation commands, and all
other-target command counts are zero. The shared guard is absent and the
global enable claim remains consumed, so no further invocation is authorized.
