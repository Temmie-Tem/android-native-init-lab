# S22+ mainline USB switch observation and Android return

The 2026-11-25 attended MAX77705 run on SM-S906N / g0q / FYG8 closed
`OBSERVED_MAX77705_USB_SWITCH` / `ANDROID_CLOSED_HEALTHY`. The retained
decoder and the final owner both returned `OPEN_THEN_OTHER_AFTER_ATTACH`.
The owner authenticated the mainline USB response and rederived the
observation at closure.

| Observer time from first observation sequence | CONTROL1 | Event |
| ---: | ---: | --- |
| 0.011 s | 0x3f | First read, switch open |
| 10.020 s | 0x3f | Periodic read |
| 14.504 s | 0x00 | VBUS and charger change flags |
| 17.564 s | 0x00 | Voltage ADC change flag |

The record contains seven events and four successful CONTROL1 samples.
It also reports three I/O errors. Later VBUS and charger change events
at 17.768 s and 17.971 s have no CONTROL1 sample. The change flags alone
do not identify which physical edge they represent. No read returned
`COM_USB` (`0x09`), and the switch state at enumeration is unknown.

The host issued the cue 22.21 s into the evidence window and recorded the
operator's completed replug at 32.45 s. In its own time base, the host port
monitor first saw the USB2 port powered at 29.29 s, then default at 29.49 s
and configured at 29.59 s. The SuperSpeed port stayed unattached throughout
the 200 s capture. The capture lists the cable type as unknown.

After the operator confirmed physical Download, the same owner restored
original Android once. The first final health check lost the ADB target.
A health-only continuation verified rooted Android, the original device and
USB topology, a changed boot ID and matching boot, dtbo, recovery and
vendor_boot digests. Candidate and original Android each transferred once.
The candidate and grant are consumed.

The private run directory is
`workspace/private/outputs/s22plus-max77705-usb-h0-20261125-1/`.
`task-1/closed.json` binds the terminal result, source snapshot, canonical
timeline and raw index. The host port samples and transition summary are in
`cue-dialog/host-port-watch/`.
