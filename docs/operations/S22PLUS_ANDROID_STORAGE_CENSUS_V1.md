# S22+ Android storage census V1

Status: **REVIEW_GATED_FIXED_FOREGROUND_D0**. The exact S22+ target adopts this
profile only with current independent V3 capability `PASS_GO`. It is bound to
the current foreground 64 GiB native-storage research task. It does not open,
renew or consume an old V3 grant. It authorizes no mode change or transfer.

The consumed native census closed healthy with metadata `NO_PROOF`. Its P393
kernel has no built-in Qualcomm UFS driver, and the reviewed native
initialization does not load UFS. Vendor-ramdisk inventory includes UFS module
files; their availability does not establish driver activation. The raw empty
exit-1 response does not prove the exact failed
precondition or temporary-alias cleanup. An unchanged native retry is not the
selected path. Android provides a separately initialized storage environment.

## Entry and fixed transcript

The entry point is `s22plus_native_task_v3.py android-storage`, implemented in
`s22plus_native_android_storage_v1.py`. It requires one closed V3 task whose
last operation proves an original-A return and exact rooted Android health.
That original raw sequence rederives, the exact A artifact is present and
hash-verified, and its source snapshot matches the current reviewed closure.
The old grant is provenance only. Reaching Android still needs its own current
transition authority; this D0 profile cannot perform that transition.

The shared target lease is held and no F1 recovery owner may be pending. The
caller creates one new private output directory and performs this transcript:

1. The existing seven-command Android health bracket selects the exact
   operator-owned `SM-S906N/g0q/S906NKSS7FYG8` serial and physical USB lane,
   numeric root identity, boot identity and original boot/supporting digests.
2. One bound-serial `adb features` read must advertise `shell_v2` in its
   one-feature-per-line CLI output. Without it,
   metadata is not attempted. One fixed `adb shell -T` / root-shell command
   then resolves Android's existing
   `/dev/block/by-name/userdata`, checks its canonical sysfs ancestry against
   the exact `1d84000.ufshc` controller and LU0, and verifies the existing
   parent block node's device number before any block read. It checks 4096-byte
   logical blocks and aligned capacity. Its matching geometry brackets cover
   only the same six initial and five final metadata blocks as the native
   census. It creates no node, mount or file and loads no module.
3. Exactly one post-read seven-command health bracket runs, including after a
   failed metadata command. It must establish the same boot/properties and
   exact rooted original-A health. It never repeats metadata or a transition.

All commands are fixed; the caller cannot supply a shell fragment, block
device, LBA, count or utility. The Android command uses the existing system
Toybox. A failed guard reports a fixed stage label to stderr. Both raw streams
are saved before parsing, with at most 65,536 stdout bytes and 16,384 stderr
bytes and a 15-second metadata timeout. The shell-v2 feature query is bounded
to ten seconds and 16,384 bytes. This transport preserves binary stdout,
separate remote stderr and the child exit status; there is no legacy fallback.
Existing health commands retain their
own smaller output limits and timeouts; the full D0 has a 600-second host-boot
bound. Host restart, source change, target ambiguity or changed health stops it.

## Result and limits

The existing GPT decoder requires complete CRC-valid primary/backup headers
and tables within the fixed capture, matching entries, nonoverlapping extents,
and agreement with the userdata sysfs extent. An unsupported shape or a failed,
truncated, timed-out or diagnostic metadata command remains `NO_PROOF`.
Metadata qualification and final Android health are separate fields.

Raw GPT bytes, names and unique identifiers stay private. This profile reads
no userdata file, encryption key or other-LU block data. It writes no storage,
issues no write ioctl, and grants no partition, formatting, module-loading,
reboot or recovery authority. It cannot qualify modified-GPT recovery.

No metadata command is retried in this run. A failed health bracket preserves
the raw evidence and stops new commands. A complete raw terminal may be
rederived in H0 without another device read. Normal D0 operation needs no
physical attendance or repeated human prompt under this adopted foreground
scope. The separate V3 Android-return operation retains its own finite grant
and recovery mode.
