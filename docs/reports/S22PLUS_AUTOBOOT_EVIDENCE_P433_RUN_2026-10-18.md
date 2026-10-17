# S22+ P433: P432 initial Debian PID1 and early preparation recovered

Status: **PASS_AUTHENTICATED_LOCAL_PROGRESS; ANDROID_CLOSED_HEALTHY**.
The separately approved P433 reader is consumed and closed. Execution date:
2026-10-18 (Asia/Seoul). No F1 owner remains; A90 and S20+ received no command.

P433 recovered P432's complete 10,972-byte early record. Authentication against
the exact physical P432 run, key and measured sources proves Debian's initial
PID1, 76 preparation-module completions, six subsequent client returns and all
14 chained file records. The last authenticated record was generated at
3,565 ms of the writer kernel's BOOTTIME. It precedes file close and unmount.
This timestamp is not the time at which the boot stopped.

The installed-runtime record is **ABSENT_IN_HOME_VIEW**. The protected reader
observed `state=1`, `recover=1`, `orphan=0`; it performed no mount or JBD2 replay.
Installed Debian init, rcS/rc2, services, NCM/SSH and clean shutdown remain
unproved. Missing home-block data cannot establish that the file was never
created or that installed init never ran.

The [P432 operation's original terminal](S22PLUS_DEBIAN_AUTOBOOT_P432_RUN_2026-10-18.md)
remains `NO_PROOF / ANDROID_CLOSED_HEALTHY`. This later, separately owned
acquisition adds authenticated local progress without changing that terminal,
replaying its candidate or promoting its VM results to physical evidence.

## Exact acquired evidence and its meaning

| Observation | Result | Meaning |
| --- | --- | --- |
| Early file | READ, 10,972 of 10,972 bytes | Exact physical-writer authentication succeeds |
| Imported preparation log | 8,924 bytes; 76 module completions | Includes the fixed UFS preparation sequence |
| Subsequent clients | Six BEGIN/return pairs, all error 0 | Fixed loading calls completed for all six clients |
| File chain | All 14 records, no partial tail or client error | Complete early pre-unmount record sequence |
| Runtime file | ABSENT_IN_HOME_VIEW | No installed-runtime record was acquired |
| Reader filesystem view | `state=1 recover=1 orphan=0` | Journal replay is required; full consistency is not established |

The six clients are `msm_geni_se`, `gpi`, `i2c_msm_geni`, `spu_verify`,
`mfd_max77705` and `pdic_max77705`. Together with the preceding 76 modules,
the fixed loading sequence has completion evidence for all 82 calls. This
does not establish every peripheral's functionality or later USB networking.
The header binds the measured initial Debian shell/init/helper and fixed
supervisor-child ancestry. The file survives P432's physical Android recovery
and the separate P433 reader boot.

The collector reports `EARLY_PRE_UNMOUNT` as the highest authenticated stage.
That name is grounded in the exact physical producer: `fl_file()` writes its
last record before closing the file and parent; `fl_write_mount()` subsequently
unmounts and verifies restored protection, superblock and GPT. Only successful
cleanup and child settlement permit the initial shell to execute
`/sbin/autoboot-init`. That entry verifies its RAM receipt and performs the
second protected root admission before the installed-init transition. The
runtime record begins later in the installed-init hook.

Consequently, the unobserved interval starts after the final early record and
includes cleanup/settlement, the automatic entry, second admission, root
transition and installed-init evidence creation. The current records do not
identify a failing call within that interval, nor establish an upper bound on
actual execution. Dirty home blocks can omit committed journal-only updates.
No journal recovery, extra file read or new writable boot is selected here.

## Authority, acquisition and return

The operator returned the exact prepared one-operation/1800-second attended
grant and confirmed presence with usable physical Download recovery. P433
`v0.8.0-rc.2` used the [qualified two-file reader](S22PLUS_AUTOBOOT_EVIDENCE_P433_H0_2026-10-18.md)
at commit `70e9d196d087cd943478bf5ff901462bf1059bee`, its separate source-bound
`PASS_GO`, unchanged actual package and original-A return artifact.

The owner repeated exact Android preflight, transferred N once, authenticated
native health, sent one fixed reader EXEC, detached, authenticated the same
boot for normal return CONTROL and transferred original A once. The reader
retained partition-only RO and performed 21 bounded library reads totaling
177,152 bytes. It mounted no filesystem and made no persistent write.

After the completed original-A transfer, the first final root-health read
reported that the selected ADB device was not found. Its raw failure is
preserved. The existing recovery path reused the completed A transfer and
continued only bounded health verification. There was no second A transfer,
reboot, reader invocation or manual Download step.

Final health proves a changed Android boot, exact original boot and supporting
partitions, root, complete matching GPT and Android32 capacity of
34,357,624,832 bytes. The terminal is `ANDROID_CLOSED_HEALTHY`,
`recovered=true`, `research_closed=true`. Recovery bookkeeping reflects the
health continuation; it does not imply another transfer or native_data repair.

## Canonical timeline

Times are seconds from P433's own grant opening. Native boot-ready is the
authenticated-health boundary immediately before the fixed reader intent.
Session close includes the H0 evidence audit after healthy Android return.

| Event | Seconds |
| --- | ---: |
| Live session start | 0.000 |
| Candidate transfer intent | 15.234 |
| Candidate transfer complete | 16.721 |
| Candidate boot ready / fixed reader intent | 41.858 |
| Fixed read complete | 45.400 |
| Original-A transfer intent | 53.498 |
| Original-A transfer complete | 55.048 |
| Final Android health complete | 103.776 |
| Session close and H0 audit | 131.408 |

## Retained verification

H0 closure rederives initial health, both transfers, the fixed read, normal
return and final health. It audits 617 raw command captures, preserves the one
transient read failure, verifies the source snapshots and consumed claim,
confirms exactly one N/A pair and leaves the original journal and terminal
unchanged. The task is closed with its one-operation budget exhausted.

The H0 collector checks both closed writer/reader owners and the physical
writer build, saves the acquisition and raw early file before parsing, then
authenticates the header, imported log and complete chain. Runtime evidence
remains unavailable, with no invented boot/nonce join. It issues no device
command and grants no replay. Private raw bytes, identifiers, keys and records
remain under
`workspace/private/outputs/s22plus-autoboot-evidence-p433-h0-20261018-1/`.
