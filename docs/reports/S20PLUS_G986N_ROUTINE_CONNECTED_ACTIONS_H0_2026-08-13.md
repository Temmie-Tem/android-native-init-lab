# S20+ G986N routine connected actions H0 design

Date: 2026-08-13
Target: Samsung Galaxy S20+ 5G `SM-G986N` / `y2q` / `y2qksx`
Exact build: `G986NKSS8IYC2`
Tier: H0 policy and execution design
Result: **PASS_GO - ROUTINE D1 ACTIVATED**

## Purpose

The prior D0-only contract treated an inactive file copied to shared storage
like a partition payload and had no representation for installing one pinned
APK. That was disproportionate for ordinary setup and forced the operator to
perform simple ADB work manually. This change creates one reusable, narrow
routine-action model without weakening any partition, boot-only, recovery,
rollback, target-isolation, or evidence boundary.

## Proposed capability

The common process distinguishes three ordinary effects:

- D0: exact bounded read-only snapshots;
- D1 control: one normal reboot or one entry into Download/recovery; and
- D1 setup: one exact Package Manager APK install or one exact inactive file
  stage to shared user storage.

A current direct operator request names one invocation. There is no special
approval sentence, standing background authority, automatic retry, or implied
next action.

The S20+ implementation closes the target tuple, firmware incremental, ADB
binary, action names, Magisk package and APK identity, AP identity, destination,
minimum free space, atomically claimed staging directory, and verification
commands.
It exposes no arbitrary serial, ADB path, artifact, destination, shell, package,
reboot argument, or command option.

## Hazard disposition

| Hazard | Closure |
|---|---|
| wrong attached device | global inventory plus exact model/device/product selection before any selected-target command |
| artifact substitution | regular non-symlink fixed path, exact size and SHA-256 before device contact |
| storage exhaustion | fixed 20 GiB minimum free-space gate before AP transfer |
| overwrite/concurrency | fixed host active guard plus atomic failing-if-present creation of a new artifact-specific remote directory; no rename or overwrite primitive |
| truncated/corrupt AP | device SHA-256 of the file inside the newly claimed directory |
| hidden partition operation | no Odin, fastboot, block path, root, sideload, recovery payload, or partition command surface |
| reboot replay | exactly one dispatch; result remains health/mode pending and says replay false |
| action after unresolved mode/health | setup and further control remain forbidden until bounded read or operator evidence resolves state |
| identifier leakage | serial, topology, and boot ID persist only as SHA-256 |
| cross-target action | every selected command uses only the exact S20+ serial; S22+/A90/other counts are zero |
| post-effect verifier failure | durable effect intent and fixed active guard remain; failure records possible effect and blocks replay |

## Permanent boundaries preserved

The common boundary now states explicitly that a normal OS-mediated Package
Manager/shared-storage write is not a partition payload. The new process writes
only Android package-manager state for one pinned APK or inactive bytes under
shared user storage. It never sends a partition image or raw/filesystem write
to Download mode, bootloader, recovery, a block device, partition mount, or an
executable runtime. All non-boot partition payloads remain forbidden, and F1
still requires a separate exact boot-only process, rollback, recovery, journal,
review, and fresh approval.

S22+ and A90 contracts are not changed or activated by this proposal. Their
identity, commands, artifacts, approvals, and evidence remain separate.

## Independent review and activation

Independent review returned `PASS_GO` with no unresolved finding after two
remediation cycles. The first found missing mechanical no-replay/health-pending
guarding and a non-atomic `test && mv` publish. The second found a control
resolver that accepted non-exact effect evidence. The final closure uses one
fixed O_EXCL-style durable host guard, effect intents written before commands,
an atomic failing-if-present remote directory claim with no rename/publish, and
strict control effect/result parsing that rejects forged or extra events.

The reviewed pre-activation hashes were:

- runner:
  `709a89fb35f643170a72e613105af68816a0a17ee622865f2d7ebdac6442c444`;
- focused routine-action test:
  `379f0ec0422498a7a3d78ea774b551dacb65a45f5591dfd681161f29df55a6ec`;
- common routine policy:
  `7cfa44c7cade7445edbf8134aff52ac6a8a292d123a4b9b5830256470188bb18`;
- risk-tier contract:
  `6834a727196c4939d7c333abfa74934066d932efd78e6ed5921a8ce62a1e3a12`;
- S20+ target contract:
  `ed4a71db1d1b8d358f05ec60b92fa5f2bc0239f78e1afa3313f01d4d233bead9`;
- common contract/registry:
  `e77456b44417ec3989cfd06964f42aedef0ecf9af19b0cafd0ac230309eb961c`.

Host-only tests passed `47/47` before activation. Mechanical activation changed
only status, registry, report, goal, and matching documentation assertions; it
did not change the reviewed runner or its effect machinery. The S20+ section is
now binding. A current direct operator request still names only one action per
invocation. No live action result is claimed by this activation.
