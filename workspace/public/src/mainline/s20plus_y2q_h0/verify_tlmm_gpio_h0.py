"""Capture the real callback, wait and caller-return boundaries on an isolated QEMU CPU."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import time

from build_tlmm_gpio_h0 import OUT, prior
from tlmm_gpio_h0 import EVENTS, FLUSH, decode, outcomes
from verify_tlmm_flush_h0 import REFERENCE, vm

FIXTURE_SHA = "a6bd64910d6cef08a4e7ed2b77d3a67dfc8ae583c14c659020d4e4f846938d49"


def trace(socket, out, symbols, mode):
    # GDB reads RAM at real instruction boundaries. It never changes guest registers.
    return f"""set pagination off
set confirm off
target remote {socket}
python
import gdb
from pathlib import Path
symbols = {symbols!r}
def reg(name):
    return int(gdb.parse_and_eval('$' + name)) % (1 << 64)
class Match(gdb.Breakpoint):
    def __init__(self, address, predicate):
        super().__init__('*' + hex(address), type=gdb.BP_HARDWARE_BREAKPOINT, internal=True)
        self.predicate = predicate
    def stop(self):
        return self.predicate()
def reach(address, predicate=lambda: True):
    bp = Match(address, predicate)
    gdb.execute('continue', to_string=True)
    assert reg('pc') == address and predicate()
    bp.delete()
def save(name):
    gdb.execute('maintenance packet Qqemu.PhyMemMode:1', to_string=True)
    raw = gdb.selected_inferior().read_memory({vm.BASE-vm.GUARD}, {vm.LENGTH+2*vm.GUARD})
    Path({str(out)!r}, name + '.ram').write_bytes(bytes(raw))
    gdb.execute('maintenance packet Qqemu.PhyMemMode:0', to_string=True)
reach(symbols['y2q_open'])
work = reg('x0')
if {mode in ("ready", "range-defer")!r}:
    reach(symbols['y2q_note'], lambda: reg('x1') == {EVENTS.index('gpio_add')})
    device = reg('x0')
    reach(symbols['y2q_note'], lambda: reg('x0') == device and reg('x1') == {EVENTS.index('directions_done')})
    save('direction-loop-exit')  # Before the done bit is published.
    reach(symbols['y2q_callback_result'], lambda: reg('x0') == device)
    resume, caller_sp = reg('x30'), reg('sp')
    reach(resume, lambda: reg('sp') == caller_sp)
    save('callback-receipt')
if {mode != "no-tlmm"!r}:
    reach(symbols['y2q_flush'], lambda: reg('x0') == work and reg('x1') == {FLUSH.index('after_wait')})
    resume, caller_sp = reg('x30'), reg('sp')
    reach(resume, lambda: reg('sp') == caller_sp)
    save('after-wait')  # Still in __flush_work(), before its outer return.
reach(symbols['y2q_progress'], lambda: reg('x0') == 309)
save('outer-return')
end
detach
"""


def run(out, mode):
    out.mkdir(parents=True, exist_ok=False)
    out = out.resolve()
    dt = out / "virt.dtb"
    data = (prior.EXP / "verified-ready/virt.dtb").read_bytes()
    if hashlib.sha256(data).hexdigest() != FIXTURE_SHA:
        raise ValueError("retained QEMU fixture differs")
    dt.write_bytes(data)
    if mode == "range-defer":
        # PDC is a real provider in virt but has no pinctrl device. The OF range
        # lookup therefore exercises the driver's real post-wake error return.
        vm.dt_change(dt, "-tx", "/pinctrl@f100000", "gpio-ranges", "445", "0", "0", "b5")

    elif mode == "no-tlmm":
        vm.dt_change(dt, "-ts", "/pinctrl@f100000", "status", "disabled")

    elif mode == "other-tlmm":
        # The same model probes on the same deferred work but its bus ID is
        # f200000.pinctrl. Preserve the three named tile resources.
        vm.dt_change(dt, "-tx", "/pinctrl@f100000", "reg",
                     "0", "f200000", "0", "1000", "0", "53000000", "0", "300000",
                     "0", "53300000", "0", "300000", "0", "53600000", "0", "300000")
    obj = OUT / "kernel-build"
    needed = {"y2q_open", "y2q_note", "y2q_callback_result", "y2q_flush", "y2q_progress"}
    symbols = {name: int(addr, 16) for addr, _, name in
               (line.split() for line in (obj / "System.map").read_text().splitlines()) if name in needed}
    seed = REFERENCE / "seed.ram"
    with tempfile.TemporaryDirectory() as tmp:
        socket = Path(tmp) / "gdb"
        script = out / "trace.gdb"
        script.write_text(trace(socket, out, symbols, mode))
        args = vm.qemu() + ["-serial", "stdio", "-kernel", obj / "arch/arm64/boot/Image",
                            "-initrd", OUT / "initrd.gz", "-dtb", dt, "-append",
                            "console=ttyAMA0 rdinit=/init cpuidle.off=1", "-S",
                            "-gdb", f"unix:{socket},server=on,wait=off", "-device",
                            f"loader,file={seed},addr={vm.BASE-vm.GUARD:#x},force-raw=on"]
        with (out / "console.log").open("wb") as log, subprocess.Popen(
                args, stdout=log, stderr=subprocess.STDOUT, env=vm.ENV) as guest:
            try:
                deadline = time.monotonic() + 6
                while not socket.exists() and guest.poll() is None and time.monotonic() < deadline:
                    time.sleep(.02)
                with (out / "gdb.log").open("wb") as debug:
                    subprocess.run([vm.GDB, "-nx", "-q", "-batch", "-x", script], check=True,
                                   stdout=debug, stderr=subprocess.STDOUT, timeout=55)
            finally:
                guest.terminate()

    nonce = json.loads((OUT / "kernel-inputs.json").read_text())["nonce"]
    tag = b"TLFIXED2" + bytes.fromhex(nonce)
    baseline = seed.read_bytes()
    results = {}
    expected_rc = 0 if mode == "ready" else -517
    callback = [expected_rc] if mode in ("ready", "range-defer") else []
    snapshots = [] if not callback else [
        ("direction-loop-exit", [], False, False), ("callback-receipt", callback, False, False)]
    if mode != "no-tlmm":
        snapshots.append(("after-wait", callback, True, False))
    snapshots.append(("outer-return", callback, mode != "no-tlmm", mode != "no-tlmm"))
    for name, rc, wait, outer in snapshots:
        raw = (out / (name + ".ram")).read_bytes()
        assert raw.count(tag) == 1
        start = raw.index(tag)
        assert raw[:start] == baseline[:start] and raw[start+240:] == baseline[start+240:]
        rows = decode(raw[start:start+240], nonce)
        result = outcomes(rows)
        assert result == dict(worker_callback_rc=rc, wait_completed=wait, flush_returned_true=outer)
        worker = {event for row in rows for event in row["worker"]}
        if mode in ("ready", "range-defer"):
            assert {"wake_found", "gpio_add", "directions_begin"} <= worker
        if mode == "no-tlmm":
            assert any({"no_barrier", "returned_false"} <= set(row["flush"]) for row in rows)
        if not callback:
            assert not worker and not any(row["initial"] for row in rows)
        elif name == "direction-loop-exit":
            assert not {"directions_done", "gpio_ok", "gpio_error", "callback_return"} & worker
        else:
            assert "directions_done" in worker
            if mode == "ready":
                assert {"of_done", "irqchip_add", "irqchip_ok", "gpio_ok", "drvdata_set"} <= worker
                assert "gpio_error" not in worker
            else:
                assert "gpio_error" in worker
                assert not {"of_done", "irqchip_add", "gpio_ok", "drvdata_set"} & worker
        results[name] = dict(slots=rows, **result)
    (out / "observations.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("ready", "range-defer", "no-tlmm", "other-tlmm"))
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    run(args.out, args.mode)
