# S22+ ML028 Debian rc-managed SSH cycle on hardware

The attended S22+ FYG8 run closed `PASS_DEBIAN_RC_SSH_CYCLE_RAM` and
`ANDROID_CLOSED_HEALTHY`. Packaged Debian SysVinit started SSH through rc2,
served one authenticated command as UID/GID 1000 with zero effective
capabilities, and ran rc6 against the original SSH master. Normal Download
then admitted the original Android image. This consumed one approved
operation with one N transfer and one A transfer.

The source was commit `aaf6af4d69`. The operator supplied the exact ML028
approval and confirmed physical attendance and usable Download recovery.
A fresh seven-read Android health check bound the starting target and
original A. [Candidate and qualification](S22PLUS_MAINLINE_ML028_RC_SSH_CYCLE_H0_2026-11-05.md)

## Same-boot service evidence

The packaged PID 1 and its direct observer authenticated the rc2 start and
the master's executable, PID and start time. After N completed and a sealed
USB census showed the endpoint absent, the owner issued one phone-end replug
cue. The operator reported completion. The host closed cue issuance before
starting the sole fixed SSH client. Its raw output joined the same boot ID
as the authenticated base frame.

One 88-byte control on the original socket requested runlevel 6. The 168-byte
authenticated reply joined the original master and observer to the successful
stop script and rc6 exit. The old master and pidfile had disappeared, and
the final process scan found zero matching packaged SSH executables.
The stop and rc6 records completed at 49.295 and 49.300 seconds of device
uptime. The scope is this packaged service in RAM. Persistent Debian, whole
system shutdown and recovery from a stalled kernel remain open milestones.

| Event | Seconds from host N launch |
| --- | ---: |
| Issued replug cue | 23.81 |
| Recorded operator completion | 47.84 |
| Sealed base frame | 62.89 |
| Closed cue issuance | 70.45 |
| Completed fixed SSH command | 78.39 |
| Recorded control intent | 82.18 |
| Completed ACK and socket EOF | 82.32 |
| Launched original A with revalidated Download ticket | 178.69 |

The host N launch and device boot use separate time origins. All experimental
evidence through ACK/EOF fit the original 120-second observation window.
Actual Download arrival had its own fixed deadline from the control intent,
capped by the original grant. A launched 96.50 seconds after intent within
that deadline. The interval includes host checks and dispatch. The sole
physical action during observation was the reported USB replug.

## Android health and closure

Original A completed through the normal return path. During its first health
bracket, the properties read exited zero with empty output. The following
root/digest read exited 1 with empty stdout and an ADB target-not-found
diagnostic. The owner preserved both raw captures and stopped. The two
accepted readiness observations, before the failed bracket and before the
fresh bracket, carried the same Android boot ID. The cause of the temporary
ADB loss remains undetermined.

After the raw A transfer was rederived, the original owner's health-only
continuation obtained seven complete health captures and closed the run.
The temporary host network profile was deleted and its absence verified.
The private journal records the initial Android Download control, N transfer,
service-cycle control and A transfer exactly once each.

The offline audit verified all 350 indexed raw captures. It distinguished the
single failed root read from three expected profile-absence results and
checked the normal Download ticket, original A, final health, cleanup and
absence of an unresolved F1 owner. The canonical timeline, raw index,
source snapshot and audit are retained with the private ML028 run.
