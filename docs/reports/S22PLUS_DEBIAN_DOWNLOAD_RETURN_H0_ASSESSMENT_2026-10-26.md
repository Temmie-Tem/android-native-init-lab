# Debian Download return: H0 mechanism and shutdown assessment

The next useful capability is a **healthy Debian shutdown into measured Samsung
Download**, followed by the existing original-A return and Android health
closure. Static evidence supports a concrete stock-module route. It does not
yet prove that route in the current Debian boot, or recovery from a failed
workload, lost SSH, blocked module probe or hung kernel.

This assessment is **H0 complete; implementation and device qualification remain
prospective**. It changes no execution source, policy, activation, consumed
artifact or device state. P460 remains consumed and `ANDROID_CLOSED_HEALTHY`.
Only S22+ FYG8 was selected; A90 and S20+ were untouched.

## Exact inputs and limits

The baseline is P460's actual physical build and its retained installed-root
archive, rather than a generic upstream Linux or SysV example. Five reboot
functions in the current Image match the retained actual-image disassembly
bytes: `__arm64_sys_reboot`, `kernel_restart`, `kernel_restart_prepare`,
`machine_restart` and `psci_sys_reset`. Reference source identities were checked
against the retained P362 analysis. This is a function-level join; the complete
reference vmlinux is not claimed identical to the current Image.

The installed SysV packages are version **3.14-4**. Selected scripts, inittab,
runlevel links and the actual ARM64 halt/reboot ELF were extracted from the
hash-bound archive already used by protected root admission. These are retained
installation inputs, not a new current-device read. Package changes after that
admission are not inferred.

## Known FYG8 route and smallest retained stock set

The kernel's RESTART2 path passes `download` through reboot notifiers before
device shutdown and the architecture restart handler. The inspected PSCI
handler ignores the command string and invokes firmware reset with zero
arguments. Thus merely passing the string to this PSCI path does not itself
communicate Samsung Download intent to firmware.

The retained Samsung command handler maps exact `download` to PON reason
`0x15`. Its Samsung IMEM reason is `NOT_HANDLE` for this command. The generic
Qualcomm reboot-reason table has no equivalent `download` entry; `bootloader`
is not an interchangeable spelling. This identifies the known stock route,
without claiming that every possible custom implementation requires it.

P460 contains 82 selected modules, none of the five retained return modules.
All five exact stock ELFs were rechecked against their original pins and the
current Image/module export CRCs. Their 141 imports resolve without ambiguity
or CRC mismatch. Relative to those 82 modules, the stock writer's ELF dependency
closure adds four modules; its DT-backed NVMEM provider adds the fifth:

| Module | Role in the retained route |
| --- | --- |
| `nvmem_qcom-spmi-sdam` | Supplies the DT-selected SDAM NVMEM cells. |
| `sec_reboot_cmd` | Reboot notifier and command registry. |
| `sec_qc_rbcmd` | Samsung command-to-reason mapping. |
| `qcom-dload-mode` | Supplies the writer's download-mode control dependency. |
| `sec_qc_qcom_reboot_reason` | Writes the PON reason and registers reset-state handlers. |

This is the smallest retained stock dependency set identified for that writer,
not an absolute minimum over alternative driver designs. ABI resolution does
not prove device probe completion. The pinned stock DT analysis supplies the
Samsung reboot-notifier priority 250, writer notifier priority 220 and
reboot-stage command selection; the provider links are DT dependencies rather
than ELF imports. A later boot must establish the actual provider and writer
bindings and completed asynchronous command registration.

The stock route has material effects before the final syscall:

- `qcom-dload-mode` with `download_mode=0` requests NODUMP and disable_sdi.
  The Samsung writer's probe then requests FULLDUMP; its normal reboot notifier
  later requests NODUMP. Late insertion can shorten that interval, not remove it.
- Writer registration writes the stock SEC_DEBUG_MODE IMEM reason. Local source
  does not establish the firmware persistence semantics of disable_sdi.
- The exact writer contains the previously confirmed `kfree(ERR_PTR)` read-error
  path. Its bounded internal write/readback loop can exhaust without propagating
  Download success to the caller; one host syscall is not one internal NVMEM write.

These effects belong in the future capability's explicit scope and independent
review. The historical [P363 target clause](../operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md)
does not activate them for Debian. Its old preparation helper also must not be
copied as a newly qualified implementation. The later
[native V3 physical result](S22PLUS_NATIVE_SESSION_V3_LIVE_2026-09-15.md)
is useful normal-return precedent, not proof for Debian or a failed kernel.

## Actual SysV shutdown findings

The current [forced SSH producer](../../workspace/public/src/scripts/revalidation/s22plus_debian_reboot_v1.py)
records phase-1 reboot or phase-2 shutdown intent, captures evidence and invokes
`shutdown -r now` or `shutdown -h now`. The
[hook](../../workspace/public/src/native-init/s22plus_debian_handoff_hook_v1.c)
requires the correct phase, actual installed init, completed evidence and live
pinned cron/sshd processes. Its acceptance is healthy-workload control, not a
general failure-recovery route.

The installed reboot command accepts `-m download`, but the package manual says
`-m` implies forced execution. Actual ARM64 disassembly and a guarded QEMU
execution of that exact ELF show a further problem: when RESTART2 returns, it
unconditionally attempts ordinary `RB_AUTOBOOT`, then CAD control and a PID1
signal, and exits zero. In the H0 execution every control call was intercepted
and returned EPERM. This reproduces fall-through, not an actual reboot. Therefore
that package command cannot be used directly for a single-attempt Download
return, nor substituted for the complete SysV shutdown sequence.

The installed serial rc6 order stops services and processes, then runs
`umountnfs.sh`, `networking`, `umountfs`, `umountroot` and finally `reboot`.
The `.legacy-bootordering` marker selects the serial dispatcher. Three fixtures
ran the actual package scripts with explicitly recorded path substitutions and
inert control commands under a host syscall guard:

1. `umountfs` preserves `/run`, but selects a RAM bind mounted at
   `/etc/init.d/reboot` for unmount. Replacing only that final script with a RAM
   bind is therefore insufficient.
2. All three `umountroot` remount attempts can fail while the script exits zero.
3. The serial rc dispatcher reaches K06 even when a fixture K05 exits nonzero.

Consequently, reaching the final runlevel script does not establish successful
root synchronization/read-only transition. The fixture mount table is synthetic;
these results do not diagnose a failed cleanup in P460 or prove its final on-disk
state. P460's final native_data consistency remains unmeasured.

## Bounded implementation proposal

Retain Debian init as host PID1, the existing workload and its finite owner.
For a successor of the current two-boot unit, retain the ordinary first reboot
and replace only the final power-off route with explicit Download intent.
Do not add a native resident supervisor or require a general recovery framework.

1. Extend the existing authenticated intent mechanism with an exact final
   Download operation. Bind run, boot, phase and one consumed control slot before
   entering shutdown. An absent or invalid intent selects no fallback control;
   phase-1 ordinary reboot remains an explicit, separate selection.
2. Use the existing RAM inittab mechanism to enter a RAM-resident copy of the
   packaged rc dispatcher for runlevel 6. Preserve its normal K01–K05 service
   and filesystem order; select the fixed Download helper at K06 for the final
   intent. Keep the helper, modules and records under surviving `/run`, rather
   than relying on a final-script bind that `umountfs` removes. The dispatcher
   change should be narrow and checked against the exact packaged input.
3. At K06, establish the intended native_data root and its actual read-only
   filesystem state, rather than trusting script exit status or a read-only bind
   flag alone. Record bounded cleanup outcomes. Prepare the five exact modules
   once, late in this final phase, using target-UAPI file validation, fixed
   parameters, exact provider/registry checks and visible preparation errors.
   This timing is a proposal; device probe completion after service settlement
   remains an attended qualification question.
4. Use a small fixed helper to issue exactly one RESTART2 `download` call after
   fresh intent and root-state checks. If it returns, preserve a bounded RAM
   result and enter the declared failure wait without another reboot, power-off,
   unload or module retry. Prevent normal dispatcher fall-through from reaching
   the package's terminal reboot command. The installed inittab also contains a
   runlevel-6 sulogin fallback; its prospective RAM handling must be explicit.
   A surviving wait process is not proof of quiescence after a helper/kernel crash.
5. Reuse the host's durable owner and original-A recovery machinery. Observe
   actual exact-target Download arrival before transferring A once, then verify
   Android health and durable closure. SSH acceptance, USB absence and a dark
   display are insufficient Download evidence.

H0 implementation checks should exercise the actual ARM64 final helper and
packaged dispatcher together: ordinary first phase, valid final intent, absent
or wrong intent, root still writable, preparation failure and returned restart
syscall. Verify no alternate control on the latter paths and that the RAM
handoff survives ordinary unmount selection. Changed control, recovery and
policy semantics require the repository's independent review before activation.
These are qualification cases for the new route, not new standing gates on
unrelated experiments.

The first device qualification remains one fresh, finite **attended** operation
with the exact rollback and demonstrated physical Download path. Success is the
completed workload followed by measured Download, original A and healthy Android
without manual buttons on the normal return. A physical fallback may close the
run healthy while leaving automatic return `NO_PROOF`. This assessment requests
no new device operation and does not reuse the consumed P460 grant.

## Relation to unattended research

Once normal return is demonstrated, a separate practical scope can consider
unattended normal operation with finite topic/time/count limits, stopping new
research on failure and deferring physical recovery until the operator returns.
The existing native-origin deferred-recovery exception does not cover this
Debian route. Such a proposal must address the concrete residual powered-device
state and any time-sensitive hazard, rather than infer safe recovery from a
timeout. It does not require proving automatic recovery from every possible
kernel hang before considering the narrower attended capability above.

Fully automatic failure recovery is a later, failure-class-specific claim.
Healthy closure can admit a fresh prospective experiment under its applicable
authority; it never replays a consumed or uncertain action.

Private evidence is retained under
`workspace/private/outputs/s22plus-debian-download-return-assessment-h0-20261026-1/`.
`assessment-result.json` and `evidence-manifest.json` bind the current-image
function comparison, module ABI/provenance results, selected root files,
guarded actual-ELF execution and packaged-script fixtures. Raw ELF, disassembly,
DT contents and fixture outputs remain private. No device command or new external
model call occurred in this assessment.
