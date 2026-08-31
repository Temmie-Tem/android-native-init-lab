# S20+ G986N autonomous public-health ADB child seccomp v1 H0

Date: 2026-08-31

Target: Samsung Galaxy S20+ 5G (`SM-G986N` / `y2q` / `y2qksx` /
`G986NKSS8IYC2`)

Status: **H0 PASS_GO_NOT_ACTIVE; NO EXECUTOR OR LIVE AUTHORITY**

## Outcome

An exact x86-64 classic-seccomp filter candidate now models the minimum child
launch boundary required by the restricted ADB proxy design. It is a
deterministic generator, parser, interpreter, and isolated harmless-helper
probe. It is not installed in a production ADB child and it exposes no
connected CLI, socket, network, ADB, `su`, Odin, USB, or device operation.

The filter checks `AUDIT_ARCH_X86_64`, traps the complete x32 syscall namespace
before any default-allow path, unconditionally traps native `bind`, `listen`,
`clone`, `fork`, `vfork`, `clone3`, and `execve`, and admits `execveat` only
when its five raw argument values match one exact held-fd transition. Every
other native x86-64 syscall is default-allowed; this is a launch-prevention
candidate, not a general syscall allowlist or sandbox.

The required modeled child order is:

```text
fork direct child
  -> PR_SET_NO_NEW_PRIVS
  -> install exact classic-BPF bytes
  -> execveat(exact held CLOEXEC fd, exact pointer values, AT_EMPTY_PATH)
```

Installation or exec failure is terminal and never authorizes retry. The
public CLI is render-only and all operational, executor, coordination,
contract, mechanical-activation, and live-authority gates remain false.

## Exact identities and validation

The qualified source is
`workspace/public/src/scripts/revalidation/s20plus_g986n_autonomous_public_health_adb_seccomp_v1_h0.py`,
47,577 bytes at SHA-256
`0c5ee2a7c293dd9c04d152945e29a7f5c278bce6f7960cfdc19979d8fc79d23e`.
Its normalized SHA-256 is
`cf041861841f79d9fe158f4c650b27d5b596aff9cea26acb68e66e5a3eabe3e6`.
The focused hostile test is 30,103 bytes at SHA-256
`d8ab5ea91385375c5af28b562869a1125cd56fbdca339e21902f44317e7a0db7`.

The exact filter contains 53 instructions and 424 bytes at SHA-256
`6f2e13a14ff7e17668fa6501535dc097960e5b1d02a83b7443d3ea86e103aaa5`.
The generator's packed bytes round-trip through the strict parser and match
the independently interpreted policy.

Qualification is bound only to the observed Ubuntu x86-64 host closure:

- Linux `x86_64`, 64-bit little-endian pointers;
- kernel release `7.0.0-30-generic`;
- glibc 2.43 and Ubuntu 26.04 host identity recorded by the model;
- exact ADB `/usr/lib/android-sdk/platform-tools/adb`, 716,968 bytes, SHA-256
  `05a1a4435e436230931acd8737fd68f31542d652731d3ca8c464cab7a42be226`;
  and
- isolated test helper `/usr/bin/gnutrue`, 35,288 bytes, SHA-256
  `7d659da07aad1d5d1ed79e9f2822d24d2dea47ceec4c7e2e71718a177dc20b4b`.

`py_compile`, render validation, scoped diff checking, and 42/42 focused tests
pass. The isolated fork-child probes execute only the pinned harmless helper:
the exact transition returns normally, native and representative x32 forbidden
syscalls terminate with `SIGSYS`, and every raw execveat argument mismatch is
trapped. The importing process never installs the filter.

## Hostile review corrections

The first frozen candidate received `NO_GO` because x32 shares
`AUDIT_ARCH_X86_64`; without testing `__X32_SYSCALL_BIT`, x32 syscall numbers
could reach the native default-allow return. The corrected program loads the
syscall number immediately after the architecture check, tests bit
`0x40000000`, and traps before every later branch. Tests cover the full modeled
x32 number range and representative bind/listen/process/exec calls, including
isolated kernel probes.

A second independent review returned `NO_GO` because the initial claim
boundary mentioned only pathname bytes. Classic BPF sees the numeric
`pathname`, `argv`, and `envp` pointers but cannot dereference any of them. The
final source now states all three limitations and requires a separate exact
executor-owned pathname/argv/environment byte closure. A hostile test keeps
the same allowed pointer values while changing argv to `kill-server` and the
environment to a TCP server socket; the filter still returns ALLOW, proving
that content is outside this filter's authority.

After both corrections, exact-byte independent review returned `PASS_GO` with
HIGH/MEDIUM/LOW `0/0/0`. A final status-only rotation changed
`REVIEW_PENDING_NOT_ACTIVE` to `PASS_GO_NOT_ACTIVE` and did not change the
normalized source or any operational gate.

## Claim and activation boundary

This unit proves only the deterministic filter bytes, exact native/x32 branch
behavior, required installation order, and isolated helper behavior on the
bound host. It does not prove:

- the content of pathname, argv, or environment behind allowed pointer values;
- one-shot state after the first successful execveat;
- post-exec CLOEXEC fd-number and virtual-address reuse closure;
- compatibility or terminal signal disposition of the pinned ADB executable;
- a production child installer, private proxy, no-input executor, journal,
  recovery composition, or cross-code interlock; or
- target-contract activation, a campaign opening, or device authority.

Those items remain explicit unresolved gates. In particular, the future
executor must own immutable exact pathname/argv/environment bytes and compose
them with the held ADB fd, private proxy, and same-process campaign handoff.
`PASS_GO_NOT_ACTIVE` cannot be used to run ADB or contact the S20+.
