# S22+ FYG8 P2.58A UDC predicate implementation (H0)

Date: 2026-07-25 KST
Tier: H0
Status: `PASS_P258A_UDC_PREDICATE_IMPLEMENTATION_HOST_ONLY`;
`INDEPENDENT_REVIEW_GO`
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

The exact 60-module plan, checkpoint ABI, stage/detail geometry, and generated
base/template kernel patch are byte-identical to P2.57. Only the static PID1
runtime changes at this H0 implementation boundary.

The earlier conclusion that a later P2.58A candidate could therefore reuse the
P2.57 Image was incorrect. Candidate intent binds the selected source-contract
domain and source receipts into a fresh run ID and UNSAT tag, then embeds both
in the final kernel config patch. A fresh P2.58A intent produced run ID
`deef1386c0e1c857e69f9107297d5dd6` and final patch SHA256
`a6984ff80351c215ce50bae3ecdb9441038ad486c4b1ca825510ddddb6ca6230`;
both differ from P2.57. Its clean-build preflight passed, so the actual
candidate boundary requires new Full-LTO A/B qualification. This correction
does not invalidate the completed H0 predicate implementation.

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
   member set and explicitly identifies the earlier tracked live report from
   which that field was backfilled. Both files are candidate source receipts.
2. `s22plus_fyg8_p258_contract_spec.py` is the single semantic oracle for the
   target name, symlink identity, dwell, and fixture expectations.
3. Implementation and candidate qualification refuse to proceed unless the
   canonical stock topology and its cited evidence agree on
   `a600000.dwc3 + dummy_udc.0`.
4. The decision helper embedded in the generated runtime is compiled for the
   host and executes known-good, negative, duplicate, identity, and
   unrelated-peer cases plus three dwell-trigger cases. It explicitly
   demonstrates that the retired singleton predicate rejects the known-good
   stock state.
5. Mutation tests remove the target or peer from the canonical topology and
   require fail-closed rejection.
6. Mutation tests reject inverted identity logic, drain re-enable, missing
   topology members, and changed expected results.
7. P2.57 checkpoint, plan, and kernel-patch SHA256 values are pinned. Any
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

The two UDC names are historical live evidence. The symlink-type and basename
rows are executable contract fixtures, not claims that the July 9 collector
captured those metadata. The read-only stock collector now records entry names,
target link type, and target destination for future refreshes.

After gate index 10, DWC3 core stage `0x86`, succeeds, the runtime resets its
monotonic deadline to five seconds and disables the inherited zero-wait drain.
Earlier regression checks remain active. No sleep or deadline is added to the
preceding 60-module and provider-gate sequence.

## Static Evidence

The source contract produced:

- unchanged P2.57 checkpoint receipt:
  `00c98bce5cdedf16718269667490a2f09f33894a8ab5469d02d80a6cdf5ca644`;
- unchanged P2.57 base/template kernel-patch receipt:
  `f0b355de0fb82a7f18ed4b744fe4f925b72fcf736b120dbd313099cf0b32ae2a`;
- unchanged P2.57 60-module plan receipt:
  `b68a6c4d5bafa864f91e0be21c53aefc5a288741c0b8870833ea603a26e3f015`;
- new P2.58A runtime receipt:
  `c6e36729b7603caacc1c026a57b163678bb749ae2a578da9f8eebdb6af63cfa6`;
- linked static userspace receipt:
  `db4b19caf659d8bc4a8fe872b3a446cc4510acafbfb712ed524c82c59672a362`;
  and
- byte-identical output from two independent static AArch64 userspace links.
  The linked binary remains identical to the pre-hardening P2.58A result
  because the compiler inlines the new pure helpers into equivalent runtime
  code.

The materialized kernel patch clean-applies to the pinned source. The source
contract, stock-closure selector, linked-audit selector, and proof-bound build
adapter all recognize the versioned P2.58A contract.

Focused validation passed:

```text
P2.57 + P2.58A combined: 32 tests
historical source/pivot contracts plus stock collector: 88 tests
stock collector focused: 7 tests
```

## Independent Review And Repair

The first independent execution-closure review returned `NO-GO` despite the
current runtime itself tracing correctly. It found that:

- Python fixtures did not execute or exactly bind the generated C;
- the topology oracle and its source report were absent from candidate identity
  receipts;
- the P2.58A closure adapter returned P2.57 labels and had a broken standalone
  entrypoint; and
- the newly extended stock collector initially violated its own shell-token
  rule and later accepted partial stdout despite a failed directory read.

The repair embeds pure decision and dwell-trigger helpers in the production
generated runtime, executes those exact bytes in a host-native C harness,
requires exact critical blocks, and rejects the reviewer-provided identity and
drain mutations. Candidate-intent integration now proves that both topology
sources are identity inputs. The closure adapter has version-correct labels.

The collector now requires successful UDC-directory read, exact two-member
topology, symlink status, and target basename. Directly collected topology is
accepted only with exact collector schema, pass result, target, stock identity,
read success, and link identity. Historical backfill remains separately and
honestly labeled.

After those repairs the same reviewer returned `GO` with no remaining
actionable finding. No device or image work occurred during either review.

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

Complete two clean P2.58A Full-LTO builds from the fresh intent, require all six
qualified artifacts to be byte-identical, then materialize the static userspace
and run the versioned linked audit. Only after deterministic boot-only
packaging, Process v2 preflight, connected D0, and fresh exact approval may a
new F1 be considered.
