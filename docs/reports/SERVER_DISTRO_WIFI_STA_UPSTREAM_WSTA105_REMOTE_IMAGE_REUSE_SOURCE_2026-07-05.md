# WSTA105 Remote Image Reuse Source Gate

Date: 2026-07-05 01:47 KST host clock
Scope: WSTA42/WSTA88 repeated D-public image-prep cost reduction
Device action: none
Boot flash / native reboot: none
Wi-Fi / DHCP / public tunnel / public smoke: none

## Summary

WSTA104 proved the WSTA88 persistent public workflow, but each nested WSTA42 run
still repeated redundant remote 2GiB SHA scans in the no-mutation image-prep
path.  The existing safety model was already good: WSTA42 verifies the local
image SHA, checks the remote work image, checks the remote clean image, restores
work from clean when drifted, and blocks if the resulting work image SHA does
not match.

WSTA105 keeps that safety model and removes only duplicate post-hashes that are
already proven by stronger same-function evidence:

- If the clean image SHA was just read and already matches, `remote_clean_sha_after`
  is recorded as skipped with source `remote_clean_sha_before`.
- If the work image SHA was just read and already matches, `remote_sha_after` is
  recorded as skipped with source `remote_sha_before`.
- If work was restored from clean, `remote_sha_after` is recorded as skipped with
  source `remote_work_restore_from_clean.restored_sha256`; the restore command
  already computes and checks the work image SHA before returning `restored=true`.
- If clean is missing or drifted, WSTA42 still installs clean and re-hashes clean.
- If work is missing or drifted, WSTA42 still restores work from clean.
- If clean support is disabled, the legacy direct-upload path still performs the
  final remote work SHA check.

This reduces the common WSTA88 initial/renewal path from four remote image SHA
scans per WSTA42 no-op image prep to two: work-before and clean-before.  A full
WSTA88 renewal run can avoid up to four redundant 2GiB remote reads when both
work and clean images are already verified.

## Validation

Host-side:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta42_native_uplink_dpublic_tunnel.py \
  workspace/public/src/scripts/server-distro/run_wsta43_orchestrated_native_uplink_dpublic.py \
  workspace/public/src/scripts/server-distro/run_wsta55_short_lived_public_proof.py \
  workspace/public/src/scripts/server-distro/run_wsta58_renewal_manual_stop_proof.py \
  workspace/public/src/scripts/server-distro/run_wsta80_persistent_operator_execute_gate.py \
  workspace/public/src/scripts/server-distro/run_wsta88_persistent_operator_workflow.py \
  workspace/public/src/scripts/server-distro/run_wsta94_packet_filter_live_gate.py

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_server_distro_wsta42_native_uplink_dpublic_tunnel \
  tests.test_server_distro_wsta43_orchestrated_native_uplink_dpublic \
  tests.test_server_distro_wsta55_short_lived_public_proof \
  tests.test_server_distro_wsta58_renewal_manual_stop_proof \
  tests.test_server_distro_wsta80_persistent_operator_execute_gate \
  tests.test_server_distro_wsta88_persistent_operator_workflow \
  tests.test_server_distro_wsta94_packet_filter_live_gate
```

Result: `Ran 78 tests ... OK`.

Focused coverage added:

- drifted work image restores from clean without host re-upload and uses the
  restore command's verified work SHA as `remote_sha_after`;
- missing clean image uploads clean once, restores work, and uses the restore
  command's verified work SHA as `remote_sha_after`;
- already-verified clean/work images do not upload, restore, or run duplicate
  post-hashes, while still recording the evidence source for each skipped SHA.

## Next

The next WSTA polish unit should make this improvement visible to operators:
surface an image-prep summary in the persistent workflow/public-state output so
WSTA88 runs show whether image prep performed upload, restore, or verified
reuse.
