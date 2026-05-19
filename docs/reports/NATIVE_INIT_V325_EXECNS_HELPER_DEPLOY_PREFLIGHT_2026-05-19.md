# v325 Execns Helper Deploy Preflight Report

- date: `2026-05-19`
- scope: host-only helper build/deploy preflight
- device command: none
- device mutation: none
- result: `PASS`

## Summary

v325 verifies the helper artifact needed by the v321/v322 private property
lookup path before any device deployment. The source contains
`a90_android_execns_probe v11`, while the ignored default local artifact at
`stage3/linux_init/helpers/a90_android_execns_probe` is still `v10`.

The preflight builds a fresh v11 artifact into private evidence, records the
stale default artifact, and keeps deployment to `/cache/bin/a90_android_execns_probe`
as a separate explicit device-mutation step.

## Evidence

- tool: `scripts/revalidation/wifi_execns_helper_deploy_preflight.py`
- evidence: `tmp/wifi/v325-execns-helper-deploy-preflight/`
- built artifact: `tmp/wifi/v325-execns-helper-deploy-preflight/a90_android_execns_probe`
- decision: `execns-helper-deploy-preflight-ready`
- pass: `true`
- expected marker: `a90_android_execns_probe v11`
- built sha256: `f40db33a2823662f64d7a2b3c6dca9ce174801208c14c4a83647a12db1ce636b`
- local default status: `stale`
- local default marker: `a90_android_execns_probe v10`
- local default sha256: `1c0234f5468f053ae559c5307124db4682f6ed89a1644312194eca730a623750`
- deploy target: `/cache/bin/a90_android_execns_probe`
- device commands executed: `false`
- device mutations: `false`

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_execns_helper_deploy_preflight.py
python3 scripts/revalidation/wifi_execns_helper_deploy_preflight.py \
  --out-dir tmp/wifi/v325-execns-helper-deploy-preflight \
  run
git diff --check
```

Observed output:

```text
decision: execns-helper-deploy-preflight-ready
pass: True
built_marker: a90_android_execns_probe v11
local_default_status: stale
built_artifact: /home/temmie/dev/A90_5G_rooting/tmp/wifi/v325-execns-helper-deploy-preflight/a90_android_execns_probe
deploy_target: /cache/bin/a90_android_execns_probe
```

## Interpretation

- Future property lookup live work must not rely on the ignored default helper
  artifact unless it is rebuilt to v11 first.
- The safe deployment source for the next device-mutation step is the freshly
  built v11 artifact recorded in the v325 evidence directory.
- V317 live private property namespace proof remains blocked until the exact
  approval phrase is provided.

Required phrase:

```text
approve v317 minimal private property namespace proof only; no daemon start and no Wi-Fi bring-up
```

## Next Step

If the approval phrase is provided, run the V317 minimal live proof. The fresh
v11 helper is for the later V320 private property lookup stage after V317 PASS
evidence exists. If approval is not provided, continue host-only or read-only
Wi-Fi/kernel inventory work.
