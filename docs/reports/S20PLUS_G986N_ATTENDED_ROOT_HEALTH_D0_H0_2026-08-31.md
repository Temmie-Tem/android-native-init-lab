# S20+ G986N attended root-health D0 H0 design

Date: 2026-08-31

Target: Samsung Galaxy S20+ 5G (`SM-G986N` / `y2q` / `y2qksx` /
`G986NKSS8IYC2`)

Status: **BINDING ACTIVE - POST-ROTATION PASS_GO**

## Purpose

Define and mechanically activate the smallest target-specific connected read
that can re-establish the
current resident-root health baseline with one fixed `su -c` command. This is
an attended read-only D0 capability. It does not broaden `su` into a generic
maintenance interface and does not inherit authority from routine D0, the
autonomous-research proposal, the completed resident-root F1 run, or active N1
R1 capability.

This report records the H0 implementation, dormant qualification, and
mechanical activation. It is not a run approval, connected-run receipt, or
device-state result.

## Authority boundary

The permanent common rules in `AGENTS.md` and the binding S20+ target contract
remain higher precedence. The exact S20+ tuple must be selected anew, and no
identity, command, approval, evidence, or result transfers to or from S22+ or
A90. Existing resident root is a precondition to test, not authority to invoke
`su`.

The target-contract section is `BINDING - ATTENDED ROOT-HEALTH D0 ACTIVE`.
The reviewed runner path is
`workspace/public/src/scripts/revalidation/s20plus_g986n_attended_root_health_d0.py`,
and its activation constant is `ATTENDED_ROOT_HEALTH_D0_ACTIVE = True`.
`--render-plan` remains host-only; `--connected` still requires a fresh direct
operator request and attendance.

The reviewed dormant runner was 39,830 bytes at SHA-256
`89c93b815dda6a5ad80d4e926958cfc0ce9758b563c307d286057647ebe3622b` and
activation-only normalized SHA-256
`86f7d49fc533750e9d641ae1d481fd2603f4b90e20e9051ef5e6a5080464848c`.
The 35,704-byte focused test SHA-256 is
`3ebb9d538e73bd69985fa9aa4f2904cad5a3a524aaaba2722b095ce67a07111e`.
Mechanical activation changed the runner boolean, made its module help text
status-neutral, and rotated only the named authority/test assertions. The
active runner is 39,820 bytes at SHA-256
`7967f85dc1418473c66b418cedfc2c15063a141fed2550d040eb122fec04584a`; its
normalized SHA-256 is
`0c4c15a014d181b43f85a00a55d335e6256663969664c95c1adf953049038b91`.
The active 35,922-byte focused test SHA-256
is `70f43252ba163f854eb21c325a5087c470a7d9305bb114c593266a5457bc3cb7`.
Four existing document-assertion tests changed only the target header and/or
exact S20+ registry-row strings:

| Test | Predecessor size / SHA-256 | Active size / SHA-256 |
|---|---|---|
| onboarding D0 | 13,218 / `40875785faf27edc2315f3735b8f200e657c0c1e4ca9fc4743d6d5c73d7ffa9c` | 13,281 / `214ae02ed69023b2096010add91e0b29502976ccece80233925281c152c343d9` |
| routine D0 | 12,332 / `19c2483934327be3e9b6815c853e69768fcca0c07a29f44547e88368c4fa5f9e` | 12,370 / `a713846021822a0f28c1514e4813c3735a10e89397dafb6daaed394d4cd07101` |
| routine actions | 37,204 / `e90eccc5bc7d5980682cdaced7bef3f4cd437b3001a5b2122cfb4f5eca7a7960` | 37,242 / `533255e6a97d18c932f236e2d68e8f25e7223ffee798ee18c4f7216ee574fedc` |
| bootstrap F1 | 96,409 / `e6325fe50fa030f455959d66004d28669df12d3484ad7aa3dfa431c2650af0ac` | 96,447 / `4ec89126082b1da183246397794b5ad5af9cad10dbd4bf2bdba2b764424e1112` |
The public script, quoted public shell argument, root script, and quoted root
shell argument are 423, 449, 584, and 594 bytes with SHA-256
`f17aac6c9c946968b18ac91a05c6d8f006fef1857533518495a97d5e71d9813b`,
`0fa4c7d3b01941f467f5ad2da51059f5b7ae5d054267a39fdca2cac878f8e4f9`,
`128ba6294378442b9e2a580086c2a8f6fc2f06afe30e642066f9bca4af314da1`, and
`e5db5a7bb0fb78553e033649bc16496c008b9e5882b88f0c84234c1dede657aa`.

## Fixed command closure

A freshly requested active invocation performs exactly six bounded host invocations,
in this order:

| Ordinal | Scope | Fixed operation |
|---:|---|---|
| 1 | global | inventory every ADB row |
| 2 | exact selected S20+ | read `get-devpath` |
| 3 | exact selected S20+ | fixed unprivileged pre-snapshot |
| 4 | exact selected S20+ | `shell su -c` with one runner-owned, shell-quoted root-health literal |
| 5 | exact selected S20+ | byte-identical fixed unprivileged post-snapshot |
| 6 | global | repeat the complete ADB inventory |

The two inventories are exactly `[adb, devices, -l]`; `get-devpath` is exactly
`[adb, -s, <internally-selected-serial>, get-devpath]`. They require rc zero,
empty stderr, a 10-second timeout, and at most 32 KiB combined output. Both
public snapshots are exactly
`[adb, -s, <internally-selected-serial>, exec-out, sh, -c,
shlex.quote(<public-snapshot-script>)]`, with rc zero, empty stderr, a 20-second timeout,
an 8-KiB combined-output bound, and these complete script bytes including the
final newline:

```sh
set -eu
emit_prop() {
    printf '%s=' "$1"
    /system/bin/getprop "$2"
}
emit_prop model ro.product.model
emit_prop device ro.product.device
emit_prop product_name ro.product.name
emit_prop incremental ro.build.version.incremental
emit_prop boot_completed sys.boot_completed
emit_prop bootanim init.svc.bootanim
printf 'selinux='; /system/bin/getenforce
printf 'boot_id='; /system/bin/cat /proc/sys/kernel/random/boot_id
```

Both inventories must contain one and only one healthy selected
`model:SM_G986N` / `device:y2q` / `product:y2qksx` row. Every selected command
uses only that row's exact serial selector. Exactly one selected-row `usb:`
metadata token must equal `usb:<get-devpath>` and remain byte-identical in the
final unchanged sanitized inventory. The pre/post snapshots bind
the exact keys `model`, `device`, `product_name`, `incremental`,
`boot_completed`, `bootanim`, `selinux`, and `boot_id`, with values
`SM-G986N`, `y2q`, `y2qksx`, incremental `G986NKSS8IYC2`, completed Android,
stopped boot animation, enforcing SELinux, and the current boot ID. The runner
must reject target, selection, devpath, public-field, health, or boot drift
rather than probe another device or retry.

The sole root command is exactly
`[adb, -s, <internally-selected-serial>, shell, su, -c,
shlex.quote(<root-read-script>)]`. It has a 30-second timeout, rc zero, empty
stderr, no more than 4 KiB combined output, and these complete script bytes
including the final newline:

```sh
set -eu
uid=$(/system/bin/id -u)
gid=$(/system/bin/id -g)
context=$(/system/bin/cat /proc/self/attr/current)
magisk_version=$(/data/adb/magisk/magisk -v)
magisk_version_code=$(/data/adb/magisk/magisk -V)
selinux=$(/system/bin/getenforce)
pid1_exe=$(/system/bin/readlink /proc/1/exe)
pid1_context=$(/system/bin/cat /proc/1/attr/current)
printf '%s\n' \
    "uid=$uid" \
    "gid=$gid" \
    "context=$context" \
    "magisk_version=$magisk_version" \
    "magisk_version_code=$magisk_version_code" \
    "selinux=$selinux" \
    "pid1_exe=$pid1_exe" \
    "pid1_context=$pid1_context"
```

Its complete accepted stdout is exactly these eight ordered lines:

```text
uid=0
gid=0
context=u:r:magisk:s0
magisk_version=30.7:MAGISK:R
magisk_version_code=30700
selinux=Enforcing
pid1_exe=/system/bin/init
pid1_context=u:r:init:s0
```

No prefix, suffix, reordered field, duplicate key, alternate whitespace,
unknown line, nonzero return, stderr byte, timeout, or truncation is accepted.
The observation would prove only the listed current-health facts. In
particular, stock PID 1 remains evidence against claiming global native PID 1;
this snapshot cannot establish native-init success, module health, recovery,
rollback, or F1 readiness.

## Explicitly absent surfaces

The proposed CLI accepts no serial, path, command, shell fragment, executable,
property, service, package, module, mount, credential, callback, backend, run
directory, or output destination. It exposes no interactive or generic `su`,
caller-selected `su -c`, second root command, arbitrary file read, file-byte
extraction, directory enumeration, root shell, or reusable root session.

Writes, file creation/removal, `chmod`, `chown`, settings/property/service or
SELinux mutation, package/module action, shared-storage operation, mount,
reboot, Download/recovery transition, Odin, payload transfer, block access,
and every partition operation are excluded. There is no automatic retry or
background/periodic use.

## Evidence and accounting design

The only private evidence root is
`workspace/private/runs/s20plus-g986n-attended-root-health-d0/`. The active
runner allocates its own closed-grammar no-clobber run directory, rejects
indirect or pre-existing evidence nodes, strictly parse typed data, publish
atomically without replacement, and fsync file and directory state.

Raw serial, devpath, boot ID, and full inventories must never be printed or
persisted. Their retained forms are SHA-256 only. A successful result accounts
for:

- two global inventory commands;
- four commands addressed to the exact S20+;
- one of those four as the fixed root command;
- zero device effects, writes, reboots, mode transitions, transfers, Odin, and
  partition operations; and
- zero commands addressed to S22+, A90, or any other target.

A failure records its actual executed prefix, bounded by no more than two
inventories, four selected-target commands, and one root command, while
retaining the same zero-effect and zero-other-target assertions.

A parser, evidence-publication, or reporting failure ends that invocation. It
does not justify repeating the root read inside the same invocation.

## Qualification and activation gates

1. The exact dormant runner and hostile tests add no caller-controlled command
   or destination.
2. The runner, scripts, helper, and test identities are frozen above.
3. The 28/28 focused suite covers dormancy; wrong, absent, unauthorized,
   duplicate, and replaced ADB
   rows; pre/post/final identity drift; root stdout order/schema/type and
   output/time bounds; identifier leakage; no-clobber/no-follow evidence;
   command accounting; and absence of mutation/control/transfer surfaces.
4. Independent hostile review covered the runner, tests, contract/report wording,
   higher-precedence interactions, and the exact proposed mechanical rotation
   of the section status, runner constant and identities, target header,
   `AGENTS.md` registry process cell, test assertions, and review record.
5. That review returned `PASS_GO`, HIGH/MEDIUM/LOW `0/0/0`, for the dormant
   bytes only. After the activation rotation, independent review returned
   `PASS_GO` with HIGH/MEDIUM/LOW `0/0/0` for the full active closure.
6. After activation, require a new direct operator request and
   attendance for every invocation. The request that initiated this design is
   not banked or carried forward as live authority.

## Work performed in this unit

This unit added and mechanically activated the reviewed runner, hostile tests,
target contract, registry row, goal, and this H0 report. It executed no ADB,
USB, `su`, device-network, Odin, reboot, transfer, partition, or live-evidence
command. It claims the explicit dormant and post-rotation `PASS_GO` verdicts
above; a fresh request and the first connected result remain pending.
