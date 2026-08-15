# Security Hardening Review: A90 SD-Free Inputs And Evidence

## Evidence Basis

This H0 review binds 22 public artifacts from baseline revision
`fda348a072eba8a53c2de7c9904c52429a7dddaf`, rebound after the later H24
13-entry/11-role and `WP-H0-1` status corrections, with collection SHA256
`2dc2e08896417f6d1b94765a7c95fbec968d98c2b7d8cdfb4fda0473cb634319`.

The current code is not simply “SD-based” or “cache-ready.” H24 still hard-gates
an SD evidence bind and compiles an SD property snapshot. Native Wi-Fi already
has a cache reader and public legacy staging code, but that staging path is a
live credential mutation with generic tcpctl overwrite semantics and no current
A90 authority. The cache property prefix is only a consumer path. The selected
future design already requires native-only cache receipts and a per-boot server
host key, but it has not defined the input producer boundary.

See [`context.md`](context.md) for exact anchors and the observed/inferred split.

## Constraints

- A90 only; H24 stays installed and its consumed D1 is never replayed.
- H0 only. No credential was read and no staging path was executed.
- Only boot may be a partition payload; UFS remains read-only.
- A cache path in source is not an authorized or durable producer.
- Wi-Fi secrets, public client keys, server private keys, property compatibility
  data, and evidence must not share one generic trust namespace.
- No headless identity is allocated until both SD dependencies and the input
  producer boundary are reviewed.

## Opportunity Portfolio

| Opportunity | Options | Recommendation | Proposal |
| --- | --- | --- | --- |
| Remove SD without replacing it with a larger mutable trust bundle | Embed all inputs in boot; transplant the SD bundle to cache; split typed channels and minimize property state | Select the typed-channel design. Reject boot-embedded Wi-Fi secrets and a wholesale cache transplant for production. | [Detailed proposal](proposals/typed-sd-free-input-evidence.md) |

## Recommendation Summary

Use four channels rather than one bundle:

1. **Boot-public:** one canonical client public key, using the existing builder
   validation pattern. No client private key enters the artifact.
2. **Persistent-private:** one versioned Wi-Fi profile generation under a new
   exact root-only cache namespace. Provisioning/rotation is a separately
   reviewed one-use attended capability; the legacy tcpctl stager is evidence,
   not authority.
3. **Compatibility:** no property snapshot if service ablation permits it;
   otherwise one manifest-bound minimal deterministic seed. A full private
   snapshot is not the production default.
4. **Output evidence:** native-only append records in cache plus independent
   strict SSH observation on the host. Debian receives no evidence write path.

The per-boot server host private key is a fifth lifetime but not a persistent
input: trusted bootstrap generates it inside child-private tmpfs, retrieves only
its public fingerprint, and destroys it with the child namespace.

## Exact Sequence

1. Finish H0 property/service ablation and freeze the four schemas.
2. Independently review any new credential-provision boundary; current code and
   this document grant no live write.
3. Implement host validators, native consumers, native receipt writer, and
   negative tests without allocating a successor identity.
4. Prove the installed boot artifact has no reachable SD evidence/property/
   profile path and does not contain a Wi-Fi PSK or server private key.
5. Only then allocate and qualify a fresh successor.
6. After an attended boot-only install reaches exact resident health, remove the
   SD card while attended and perform the contract-required no-SD D0.
7. Only after that proof may a separate attended D1 handoff be requested.

## Next Decisions

1. Decide whether the reduced WLAN backend needs any property area at all.
2. If it does, freeze the minimum key/value/file set and its deterministic
   producer; the current private snapshot remains uninspected and unproved.
3. Design the one-use Wi-Fi provision/rotate capability separately from the
   candidate and evidence paths.
4. Set byte, fsync, boot-latency, WLAN-ready, SSH-ready, memory, and recovery
   budgets before implementation.

This review grants no device, D0, D1, F1, candidate, handoff, UFS mutation, or
SD-removal authority.
