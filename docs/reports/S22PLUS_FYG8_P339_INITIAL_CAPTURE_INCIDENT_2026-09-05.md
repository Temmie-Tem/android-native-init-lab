# P339 initial diagnostic capture incident

Target: `SM-S906N / g0q / S906NKSS7FYG8`.

## Retained experiment

Run: `p339-ready2-prepared-20260905-2`, manifest `p339_process_v2_ready_2`.
The journal and transfer receipts prove one candidate and one exact Magisk
rollback completed, both with Odin return code zero. No second attempt exists.
The retained state has `final_verified=false`; no `live-result.json` exists.
This run is consumed and cannot be replayed. It is not a closed F1 PASS.

Candidate AP: `28631081B/80830eed6818528577e3dd5d68af79743b55a014b1dd4e2c8a3c5f54711b47d3`.
Rollback AP: `23367721B/d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`.
Private evidence remains under
`workspace/private/runs/device-action-f1-live-v2/p339-ready2-prepared-20260905-2/`.

## Two host defects

The raw capture is 97 bytes, SHA-256
`4724b51f7d04cd2bcfa0efe03c8ee78a3304cc68def41fa44f32c56694739d8c`:
the exact 49-byte P339 banner, stage 0/code 0, and stage 3/code 1.
Host OPEN TX is 32 bytes, SHA-256
`e8fa40fb59801fe06eb22af4190a3c8c3f47d6e720d328a7848c85668a35bfa9`.

1. `_P339_INITIAL_OBSERVER` loads the retained P335 exchange implementation.
   After stage 0, its real `_exchange_one()` expects stage 1. Stage 3 is
   rejected and `exchange_retained()` closes the descriptor. The P339
   post-collection parser therefore cannot obtain stages 4 through 7, even
   if the device sends them. Their absence from the capture is not proof of
   absence from the device's output.
2. `_p339_validate_receipt()` assumes the reason is frame 0 and total frame
   count is `1 + word_count`. The actual initial stream includes stage 0,
   so its reason is frame 1 and count is `2 + word_count`. This rejects an
   existing `candidate-observer.json` and produces the misleading
   `interrupted-before-receipt` state. The raw and JSON files were retained.

The device's original header-grammar rejection remains unexplained. The
retained stage-3 code distinguishes it from the later OPEN semantic check,
but does not identify the bytes read by the device. No HMAC, command or
resident success is claimed for this run.

## Host-only repair qualification

`s22plus_fyg8_open_failure_capture.py` installs on a private initial codec.
At first-OPEN stage 3/code 1 or 4 it receives at most four existing 24-byte
diagnostic frames through the original raw writer and deadline. It checks
exact header/payload size, type, sequence, CRC and word order. It then returns
the original failure frame to the original rejecting parser. No transmission,
OPEN retry, connection reopen, timeout extension or successful proof is added.

Seven focused tests exercise the actual bound initial exchange over local
sockets: original 97-byte cut, complete 193-byte capture for codes 1/4,
partial/EOF and silent tails, malformed/order/CRC/size bounds, four-word cap,
and unchanged three-session authenticated success. All pass. These are
host simulations, not new device results. Independent review confirmed the
collector's bounded scope; live integration and the receipt-index repair
remain to be completed and reviewed before the successor is ready.

## Recovery status

Final health originally timed out while S22+ ADB was unauthorized. One
exact-target host-side ADB reconnect restored the same device and topology;
the other connected Samsung device received no command. Ordinary recovery
then stopped before device collection on a prepared bundle hash mismatch.
The current executable-source closure equals the retained closure. The
bundle mismatch still requires diagnosis; no preparation, journal, receipt
or approval was rewritten to bypass it. Final health and closure remain
pending, so a successor has no F1 readiness or authority yet.
