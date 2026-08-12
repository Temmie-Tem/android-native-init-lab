# A90 H25 HUD chroot and self-test replay host incident

Date: 2026-08-12
Target: operator-owned Samsung Galaxy A90 5G only
Tier: H0 host-only
Status: `NO_GO_RETIRED`

## Scope

H25 `0.11.193` was a draft successor to the installed H24 resident. It tried to
replace H24's failing persistent-HUD private-root bootstrap with a `chroot`
design and to qualify that path through a stored boot self-test. The draft was
reviewed before any runner, connected D0, approval, transfer, reboot, handoff,
or device effect existed.

The independent reviewer issued no `PASS_GO`. The reviewed frozen checkpoint
was capability closure `546eae09...ea37` / 28 and native closure
`45827184...64ec` / 142. Those hashes identify retired evidence only and grant
no authority.

## Confirmed findings

### High

1. `chroot` changed pathname resolution but did not detach the complete old
   mount graph. The surviving child retained a mount-namespace capability that
   could expose native mounts after `/proc` moved into Debian. This contradicted
   the H24 private-root isolation claim.
2. The transient HUD self-test could create a shared parent mount and mutate or
   remove a fixed private-root directory that it had not first proved absent
   and owned. Cleanup did not restore an exact parent pre-state.
3. The purported stored boot result was not boot-origin-bound or immutable.
   Manual or hot-reload self-test paths could rerun the same helper and replace
   a failed or missing boot result, and the helper also reran on an armed boot.
   This violated no-replay evidence semantics.

### Medium

1. Timeout cleanup sent `SIGKILL` but did not require exact child reap/gone
   proof before publication.
2. The parent-mount absence check used a parser that could accept truncated or
   malformed observation as no mount.
3. A positive nonzero child receipt return code could bypass the exact parent
   root and descriptor validation path.

### Low

1. A validation failure could leave a stale raw `state=running` status even
   though the service had not published a pidfile.

## Disposition

- H25 is `NO_GO_RETIRED`; no issue is waived.
- Its draft source changes and manifest were removed. Its untracked build
  output was moved to trash and was never committed.
- H25 version, build identity, enable/latch paths, artifacts, qualification,
  and evidence are never reused or reinterpreted.
- The next successor is a fresh headless design that omits persistent native
  HUD from the critical handoff. A future display capability is separate and
  requires its own design and review.
- Installed H24 and its consumed terminal journal were not modified. No H24
  effect may be replayed.

## Contact and evidence boundary

The clean independent review reported device, `/dev`, USB, network,
`workspace/private`, S22+ path, S20+ path, and file-modification contacts all
zero. This report contains no private artifact, raw log, device identifier,
credential, or network identifier.
