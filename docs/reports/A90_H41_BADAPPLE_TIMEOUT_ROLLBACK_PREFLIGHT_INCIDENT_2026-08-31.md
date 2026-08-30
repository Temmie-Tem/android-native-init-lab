# A90 H41 Bad Apple Timeout and Rollback Preflight Incident

- Target: operator-owned Samsung Galaxy A90 5G only
- Run: `a90-h41-f1-20260830-02`
- Candidate: `0.12.008 / h41-badapple-video-demo-v2`
- Candidate SHA-256: `5aa3ca852e1cd9d89a23cfd0223a64fe98e5e0e356d71dc6543da6afe6389574`
- Classification: runtime failure observed; original rollback consumed before helper dispatch

The reviewed late-Recovery transaction wrote and prefix-read back the exact H41
candidate and confirmed its System return. During the manual demo window, the
operator selected Bad Apple and observed `FAILED RC=-110`. In the compiled H41
path, `-110` is the bounded audio-worker/video readiness timeout. This proves
only the H41 run's timeout outcome; it does not prove playback, and it does not
transfer the H37 operator-observed playback into H41.

After the operator closed the H41 menu, the same transaction durably published
`30-rollback-intent.json` and `31-rollback-launched.json`. Its first adapter
inventory then found H41 Native `04e8:6861` and a separate Samsung/TWRP
`04e8:6860` on different host ports. The adapter rejected the non-single-
Samsung state before constructing or dispatching the flash helper. The exact
rollback log contains only `001-effect-usb-inventory.{stdout,stderr}`; there is
no flash-helper stdout/stderr, ADB inventory, Recovery transition, push, boot
write, readback, or System-return receipt. Therefore the original rollback
invocation is consumed and never replays, while its V2321 write count is zero.

After the operator disconnected the other Samsung device, host USB inventory
showed one H41 A90 Native endpoint. That later observation is readiness for a
separately reviewed recovery continuation, not proof that a rollback occurred.
The active guard and H41 candidate guard remain. The continuation may contain
no candidate path and must bind the exact manifest, original journal and logs,
both guards, exact V2321 artifact, sole Native endpoint, current independent
review, and a fresh approval before one newly journaled V2321 rollback. A
separate durable phase under the same approval may perform one read-only V2321
health observation only after the operator closes the returned menu.

This report grants no live authority. H41 playback is not proved; the observed
`RC=-110` is not promoted into a general audio or video refutation. S22+ and
S20+ were not contacted and receive no authority from this incident.
