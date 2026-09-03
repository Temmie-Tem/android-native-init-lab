# S20+ G986N staged TWRP-fastbootd preparation probe H0

Status: `CONSUMED_NO_PROOF_RETURNED_HEALTHY`

## Why this is separate

The consumed retained-T2 census armed its fixed background enable once, but no
`18d1:4ee0` entry appeared. Physical TWRP System return and fresh Android health
closed it as `NO_PROOF`; its enable cannot be replayed. The volatile `/tmp` log
did not survive reboot, so that terminal does not distinguish mount, configfs,
service, endpoint, or later gadget-switch failure.

This successor does not repeat the census. It stops before USB role switching
and asks only whether preparation can reach four explicit stages while ADB is
still attached.

## Fixed staged action

One synchronous fixed root-ADB script, after a durable one-use intent:

1. rechecks exact controller, stopped fastbootd, direct unmounted
   `/dev/usb-ffs/fastboot`, absent configfs `ffs.fastboot`, ADB-only links,
   current UDC, `bcdUSB=0320`, and `bcdDevice=0419`;
2. mounts one volatile FunctionFS instance with the reviewed fixed options and
   emits `stage=functionfs-mounted`;
3. creates the sole absent configfs function and emits
   `stage=configfs-function-created`;
4. starts the existing fastbootd service and emits `stage=service-running`;
5. waits for `ep0`, `ep1`, and `ep2`, then emits `stage=endpoints-ready`.

A second fixed read rechecks those states plus unchanged ADB `f1`, absent `f2`,
the same UDC, `mtp,adb`, and running adbd. Recovery identity, boot, topology,
and the other-device inventory must remain unchanged.

The scripts contain no UDC detach/write, VID/PID/string write, fastboot gadget
link, fastboot host command, block path, partition operation, or persistent
path. Success and every post-intent failure require physical TWRP System return
and fresh exact Android health. No stage is retried.

## Exact closure

- active runner: 41,056 bytes, SHA-256
  `60b3e72996c87eb884ade79112301a541d5af400bbed102dd1e7a46fd71703c4`;
- activation-normalized runner SHA-256:
  `8c52caa352779509d17e675fd544089e4e3b6ccb22cde1a6aab878e39a225b26`;
- terminal-owner focused test: 12,815 bytes, SHA-256
  `b2e93d7c5070cbaf01e71f94d00823972041476b5bd6c0b4557ad1e5929389dc`;
- fixed preparation script: 1,978 bytes, SHA-256
  `11d05212679b5b2c488688393a3cc1ba7773b66e27e9821b212ff3c07c710b9a`;
- fixed post-state script: 987 bytes, SHA-256
  `34e74bf7cbfb5185d60d28b265397873a81b41407ab44ddec49d64c5dc8e9481`;
- consumed predecessor terminal: 1,456 bytes, SHA-256
  `8979538332be37879700b2f455e77eb9e12c1ed4ccc3efbdb5d7d49bde90b0a4`;
- consumed predecessor marker: 534 bytes, SHA-256
  `df486135a3619871e76b891a4b4a0f8f90d1693d0b43a9cc4629c52c3f947153`.

Thirteen focused tests cover dormant gating, exact predecessor consumption,
stage-prefix classification, intent-before-effect, no USB switch/fastboot
surface, failed-stage stop, local/global intent cut recovery, effect-free abort,
raw-capture-bound success, final-result strictness, and run-root containment.
`py_compile`, focused tests, and `git diff --check` pass. Raw-first classification
is device-touching but non-legacy because all acquisition uses the common raw
capture module.

Independent dormant review returned `PASS_GO` with CRITICAL/MAJOR/MINOR
`0/0/0`, including exact closure, consumed-predecessor rederivation, raw
ordinal continuity, staged ordering, forbidden-surface absence, uncertainty,
and physical return. Mechanical activation set `LIVE_ACTIVE=true` and rotated
only the declared full runner/test identities and status. No live invocation
is standing: retained-T2 entry and the probe each require a fresh direct
attended request.

Activation-only independent review also returned `PASS_GO` with
CRITICAL/MAJOR/MINOR `0/0/0`. It reconstructed the exact dormant runner/test
hashes by reversing only the activation atoms, confirmed the embedded scripts
and normalized identity unchanged, and recorded reviewer device contacts and
writes as `0/0`.

## Live result

The one-use intent was consumed. The preparation command returned zero but its
70-byte stdout was only `mount`'s `ENOENT` diagnostic, so no declared stage was
proved and classification remained `invalid-output`. The command-result
SHA-256 is
`50042ef670fd700d907773eee4f046039cdb693f1127d9878049a2909d97903e`;
the raw stdout SHA-256 is
`6dd9ce2743aaca177c1194e88b0ec4e88493c72f0d59ab1496163855b926ae3a`.

No USB switch, fastboot command, persistent write, or partition operation
occurred. Physical TWRP System return reached fresh exact healthy Android. The
1,275-byte final result SHA-256 is
`ea9a201bf1bd9a093c70a3791ebf4fb1b1b4f489788bfe2660ee2c1d5372221d`
with verdict
`NO_PROOF_S20PLUS_G986N_TWRP_FASTBOOTD_PREP_RETURNED_HEALTHY`; replay is false.
Exact T2 ramdisk init ordering explains the stop: it creates
`functions/ffs.fastboot` before mounting `functionfs fastboot`, while this
consumed probe did the inverse. A distinct Q1 may correct only that order.
