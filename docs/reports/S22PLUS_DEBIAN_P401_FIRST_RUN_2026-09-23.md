# S22+ P401 first Debian attempt: unproved, healthy Android return

Date: 2026-09-23 KST (2026-09-22 UTC). Target: `SM-S906N/g0q/S906NKSS7FYG8`.

The first attended P401 `v0.4.0-rc.1` operation closed
`NO_PROOF_ANDROID_CLOSED_HEALTHY`. One exact candidate boot transfer completed,
but its expected Debian NCM endpoint was not observed within 180 seconds.
Installation, Debian PID 1, SSH and the native filesystem's resulting state
remain **UNPROVED**. The owner stopped research without another candidate,
workload, Debian reboot or shutdown request.

The operator entered physical Download. One exact original-A transfer completed.
A fresh read-only health continuation then proved healthy rooted Android,
original boot/supporting partition hashes, unchanged full GPT and Android32
statfs total 34,357,624,832 bytes. The final Android boot differs from the
fresh execution-start boot. The F1 owner is retired; the grant closed after
525.267 seconds. Candidate and installation claims remain consumed.

## Canonical journal-derived timeline

Times are seconds from the original 7200-second grant opening. Intent and
completion are separate durable records; this table does not infer inner
device execution from a completed transfer.

| Elapsed | Event | Evidence boundary |
| ---: | --- | --- |
| 16.817 | Owner opened | Exact reviewed source, target, artifacts and grant |
| 26.594–30.496 | Android Download request and departure | One control intent/result |
| 39.563–41.175 | Candidate transfer | One candidate/install claim and completed Odin capture |
| 221.742 | Research stopped | `Debian NCM arrival unproved` after bounded observation |
| 221.750 | Physical recovery armed | Original-A recovery remains owned |
| 386.870–388.247 | Original-A transfer | Operator-reported physical Download, exact measured endpoint, one transfer |
| 525.267 | Healthy Android terminal published | Complete raw health/GPT/statfs rederivation |
| 525.275 | Terminal journal record | No further device effect; owner retired |

Fresh execution health passed before Download. No host NetworkManager profile
was created because no matching Debian interface arrived. There were zero SSH,
workload, Debian reboot and Debian shutdown attempts, and zero extra recovery
transfers. No A90 or S20+ target-specific command was issued.

## Operator observation and causal limits

The operator reported that the boot screen appeared to have been reached,
there was no observed boot loop, and the screen did not subsequently change.
This is retained as an operator observation, not proof of Debian execution.
The candidate has no display renderer, so an unchanged screen is compatible
with more than one boot state. Its bootstrap also deliberately pauses rather
than exits on a fatal guard failure; no retained target-stage record establishes
whether that happened here.

The missing NCM observation does not localize a failure to the kernel, module
loading, storage binding, extraction, init handoff or Debian USB service. It
also does not prove that extraction never started. The bootstrap log is in RAM
and was not retrieved through SSH. Android return does not undo possible native
filesystem writes or prove the old witness/root contents still unchanged.
The independently qualified H0 artifact/VM results retain their original scope;
they are not promoted to Samsung boot proof by this attempt.

## Read-only recovery continuation

After the proved original-A transfer, readiness observed Android boot completion.
The first final-health inventory succeeded, but the following exact-target
`get-devpath` returned status 1 with target-not-found diagnostics. There was no
timeout, overflow or capture-producer fault. The cause of that brief absence
is not established.

The existing recovery owner resumed from the durable A intent/result. It
skipped transfer and performed only its fixed fresh read-only health bracket,
GPT/statfs observation and final bracket. All passed. The failed capture remains
separate and unchanged; later health does not retroactively validate it.

## Retained evidence and next boundary

Private evidence is in the preparation output's `p401-first-boot-run-3`:

| Record | Bytes | SHA-256 |
| --- | ---: | --- |
| Immutable terminal | 956 | `e15acd4deb95c8e584628bf882b6168f6394709ca65622448e389d727caa9b39` |
| Raw-rederived closure audit | 1,600 | `5cd8ec3c4ecde915bb35aa72157d175caed6e54ad38dab897b1985b3f06b166f` |
| Research-stop assessment | 1,742 | `a7d076b9cf659becfa18e457e4612768bd3589f608a447b7e46617c0c991a53b` |

The journal, exact grant, private transfer captures, failed and successful
Android reads, operator observation, global claims and source review are
preserved. [H0 preparation](S22PLUS_DEBIAN_FIRST_BOOT_H0_2026-09-21.md) and the
[first-boot policy](../operations/S22PLUS_DEBIAN_FIRST_BOOT_V1.md) retain their
original meanings.

Next work is H0 comparison of the retained physical bootstrap/USB path with
the previously working FYG8 bring-up and assessment of the missing early-stage
evidence. No cause, successor candidate or new device authority is established
by this report. Do not repeat P401, reinstall, clear its markers or repair the
filesystem under the closed grant.
