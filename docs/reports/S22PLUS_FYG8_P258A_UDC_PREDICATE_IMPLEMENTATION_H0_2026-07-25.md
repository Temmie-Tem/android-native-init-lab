# S22+ FYG8 P2.58A UDC predicate implementation (H0)

Date: 2026-07-25 KST
Tier: H0
Status: `PASS_P258A_UDC_PREDICATE_IMPLEMENTATION_HOST_ONLY`
Live authority: none

## Result

P2.58A implements the bounded repair selected by P2.58:

- the UDC gate now asks whether the exact FYG8 controller is present and has
  the expected symlink identity;
- unrelated UDC peers, including built-in `dummy_udc.0`, no longer make the
  gate fail;
- malformed directory records, duplicate target entries, a non-symlink target,
  and an unexpected target basename fail closed; and
- successful DWC3-core observation starts one fresh five-second UDC dwell
  instead of consuming only the remainder of the shared deadline.

The exact 60-module plan, checkpoint ABI, stage/detail geometry, and kernel
patch are byte-identical to P2.57. Only the static PID1 runtime changes.
Therefore this H0 unit does not require another kernel Full-LTO build. It does
not yet prove that a packaged candidate reuses the exact P2.57 Image; that
identity must be checked by the linked candidate audit before packaging.

No image, AP archive, manifest, device binding, approval, Odin session, or live
run was created.

## Recurrence Prevention

The P2.57 singleton predicate was not merely an implementation typo. Earlier
stock reports already recorded the valid two-entry topology, but that evidence
remained prose while the source checker validated only strings, compilation,
and internal contract consistency. A flawed design could therefore pass every
review and static check.

P2.58A closes that class of failure with executable external ground truth:

1. `stock-usb-runtime-topology.json` now records the complete known-good UDC
   member set, not only the selected gadget UDC.
2. `s22plus_fyg8_p258_contract_spec.py` is the single semantic oracle for the
   target name, symlink identity, dwell, and fixture expectations.
3. Contract generation refuses to proceed unless the canonical stock topology
   is exactly the measured `a600000.dwc3 + dummy_udc.0` state.
4. The oracle executes known-good, negative, malformed, duplicate, and
   unrelated-peer cases. It explicitly demonstrates that the retired
   singleton predicate rejects the known-good stock state.
5. Mutation tests remove the target or peer from the canonical topology and
   require fail-closed rejection.
6. P2.57 checkpoint, plan, and kernel-patch SHA256 values are pinned. Any
   accidental kernel-contract drift fails generation instead of silently
   triggering another expensive build.

This is deliberately a small recurrence guard, not a new policy layer. It
tests behavior at the boundary where the previous checker only tested syntax.

## Exact Gate Semantics

The corrected gate enumerates `/sys/class/udc` with the existing bounded
directory parser. It permits arbitrary unrelated entries but requires exactly
one entry named `a600000.dwc3`. The target path is then checked with
`newfstatat(..., AT_SYMLINK_NOFOLLOW)` and bounded `readlinkat`; the final
symlink component must also be `a600000.dwc3`.

The host oracle fixes the intended truth table:

| Topology | Result |
|---|---|
| no target | fail |
| `dummy_udc.0` only | fail |
| `a600000.dwc3` only | pass |
| target plus `dummy_udc.0` | pass |
| target plus another unrelated UDC | pass |
| duplicate target model input | fail |
| wrong target type or symlink identity | fail |

After gate index 10, DWC3 core stage `0x86`, succeeds, the runtime resets its
monotonic deadline to five seconds and disables the inherited zero-wait drain.
Earlier regression checks remain active. No sleep or deadline is added to the
preceding 60-module and provider-gate sequence.

## Static Evidence

The source contract produced:

- unchanged P2.57 checkpoint receipt:
  `00c98bce5cdedf16718269667490a2f09f33894a8ab5469d02d80a6cdf5ca644`;
- unchanged P2.57 kernel-patch receipt:
  `f0b355de0fb82a7f18ed4b744fe4f925b72fcf736b120dbd313099cf0b32ae2a`;
- unchanged P2.57 60-module plan receipt:
  `b68a6c4d5bafa864f91e0be21c53aefc5a288741c0b8870833ea603a26e3f015`;
- new P2.58A runtime receipt:
  `70866617ae90b0aecba444dfb2bb2f11ca500828ada8207b29cc0d8e3bb75284`;
- linked static userspace receipt:
  `db4b19caf659d8bc4a8fe872b3a446cc4510acafbfb712ed524c82c59672a362`;
  and
- byte-identical output from two independent static AArch64 userspace links.

The materialized kernel patch clean-applies to the pinned source. The source
contract, stock-closure selector, linked-audit selector, and proof-bound build
adapter all recognize the versioned P2.58A contract.

Focused validation passed:

```text
P2.57 + P2.58A combined: 25 tests
P2.45/P2.48/P2.52/P2.54/P2.57/P2.58A historical set: 74 tests
```

## Proof Boundary

P2.58A proves that the next observation contract no longer rejects the known
good FYG8 UDC topology and gives the asynchronous role worker a bounded dwell.
It does not prove:

- that `a600000.dwc3` was present during the completed P2.57 live run;
- that a future direct-PID1 boot will publish the real UDC;
- role-worker, PM, reset, PHY, or gadget-init success;
- USB enumeration, configfs binding, ACM, or host communication; or
- candidate Image identity before the linked packaging audit runs.

If a future corrected observation still ends at stage `0x87`, the next
diagnostic scope is limited to role-work entry and PM/reset/gadget-init return
coordinates. The singleton predicate must not be reintroduced, and no role or
configfs write follows from this H0 result.

## Next Bounded Unit

Run one independent execution-closure review of the runtime-only delta, then
materialize the static userspace payload and prove through the linked audit
that the packaged candidate uses the exact already-qualified P2.57 kernel
Image. Only after deterministic boot-only packaging, Process v2 preflight,
connected D0, and fresh exact approval may a new F1 be considered.
