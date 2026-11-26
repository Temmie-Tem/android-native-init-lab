# S22+ UFS V13 route composition (H0)

This report covers the H0 work that lets the adopted report-v13 late-UFS
experiment run without a USB replug
([policy](../operations/S22PLUS_MAINLINE_UFS_ROUTE_V1.md)). It ends with
a prepared ML054 task and no device action.

## Why

ML051 and ML052 used V13 and never reached the module. Every mainline USB
first response since ML021 needed a physical replug. One gated MAX77705
`CONTROL1_W(COM_USB)` removed the replug in seven consecutive cable-untouched
route-timer boots. On 2026-11-27 the operator chose UFS as the next step and
set no-replug as the baseline. The operator then approved the common-contract
delegation.

## Artifacts

| Input | V13 capability | UFS route capability |
| --- | --- | --- |
| Kernel Image | `c4f8d9b0…`, configuration `342fc571…` | `fb1fc155…`, configuration `881e450e…`: only `CONFIG_I2C_QCOM_GENI` `m` → `y`. `vmlinux.symvers` is byte-identical. |
| DT | `f918d309…` | `51b58a40…`: QUP0 and SE5 I2C `okay`, SE5 pinctrl removed. The prepared DT audit is identical. |
| Module | `5628f299…` | The same bytes. A rebuild against the new kernel is byte-identical. |
| Observer | V13 | V13 plus the route observer's reads and one gated write. The route header is rendered with two window checks. |

The kernel directory records (prepared, transport, unmarked and guard) are
derived field for field from ML035 by `records_i2c.py`, because
`guard_kernel.py` accepts only the ML028 configuration. The final candidate
`candidate-final-b` was built from main `886c1a4d04`.

## Reviews

| Unit | Result |
| --- | --- |
| Code and contract (v67, `c9c1b15ecb`) | Rounds 1 and 2 HOLD: the automatic return rejected the scope, recovery needed the guest header, and a late tick or scheduler delay could write after the window. Round 3 `UFS_ROUTE_PASS_GO`. |
| Recipe identity (v68, `dc3aea26b4`) | Found while building the final candidate. Rounds 1 and 2 HOLD: JSON `1` and float numbers were accepted. Round 3 `UFS_ROUTE_FIX_PASS_GO`, with canonical-byte comparison. |
| Start strobe (v69, `886c1a4d04`) | Prompted by the first owner-review HOLD: the strobe was unchecked. Round 1 HOLD on the policy overclaiming. Round 2 `UFS_ROUTE_STROBE_PASS_GO`, with a submission boundary. |
| Owner review of capability and candidate | Round 1 HOLD (strobe). Round 2 `UFS_ROUTE_CAPABILITY_PASS_GO` on capability-2 and candidate B. |

## Prepared task

ML054 (`2db30bfb…bf6`) uses capability-2 (review receipt `4e882ca6…`) and
qualified image `4adf304d…`. Its predecessor is route-timer run 6's healthy
closure. No grant or operation exists.

What a run can claim:
- the V13 link result;
- an authenticated USB first response with no physical action.

It cannot claim that the route write ran, because the V13 response layout is
unchanged and carries no route record.

Private directories:
- `workspace/private/outputs/s22plus-ufs-route-h0-20261127-1/`
- `workspace/private/outputs/s22plus-ml054-ufs-route-h0-20261127-1/`
