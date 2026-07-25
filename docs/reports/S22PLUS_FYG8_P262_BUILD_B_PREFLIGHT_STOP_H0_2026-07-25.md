# S22+ FYG8 P2.62 Build B preflight stop (H0)

Date: 2026-07-25 KST
Tier: H0
Status: `STOPPED_FAILS_TWICE_HOST_ONLY`
Live authority: none

## Established State

The corrected P2.60 v2 intent passed its exact source contract, two-link
userspace build, entrypoint check, and authority inventory. Clean Full-LTO
Build A completed in `38:21.05` with return code zero, peak RSS `24255324`
KiB, zero process swaps, and a locally rehashed immutable seven-file bundle.

No device was contacted. No candidate manifest, binding, approval, Odin
session, or F1 transaction exists.

## Failure

Build B preflight rejected twice with the same exact error:

`clean build requires absent output tree:
<canonical-source-tree>/out`

The first rejection's terminal output was lost at an asynchronous command
boundary. Before the second attempt, the three candidate patch base files,
repository-root `out/` absence, memory, disk, and empty partial result
directory were checked. That diagnosis missed that the build wrapper's clean
tree is `$SOURCE_TREE/out`, not the build repository's top-level `out/`.

The second attempt wrote durable stderr and exposed the exact path. The
wrapper behaved correctly and no Build B started.

## Stop And Recovery Boundary

The repeated material host-side failure triggers the active fails-twice stop.
No third preflight is run in this unit. Both empty failed result directories
and the stderr/return-code receipt are retained in private storage.

The frozen intent and Build A bundle did not change and remain valid host
inputs. Recovery is a separate H0 unit:

1. update the runbook so clean output always means `$SOURCE_TREE/out`;
2. prove the cleanup target's canonical parent is the exact source tree;
3. remove only that generated output after the Build A bundle is reverified;
4. use a new preflight result directory; and
5. stop again if any material preflight failure recurs.

This recovery does not authorize a device action and does not permit reuse of
a failed result directory.
