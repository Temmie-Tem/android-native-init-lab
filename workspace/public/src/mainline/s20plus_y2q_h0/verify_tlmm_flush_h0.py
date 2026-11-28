"""Boot the exact candidate on QEMU virt with synthetic TLMM/PDC dependencies."""
import argparse
import importlib.util
import json
import re
from pathlib import Path
import subprocess
import tempfile
import time

from tlmm_flush_h0 import decode

HERE = Path(__file__).resolve().parent
# HERE is workspace/public/src/mainline/s20plus_y2q_h0
PRIVATE = HERE.parents[3] / "private"
ANALYSIS = PRIVATE / "analysis"
REFERENCE = ANALYSIS / "s20plus-y2q-consolidated-20261127/qemu-review/deployed-ordered"
spec = importlib.util.spec_from_file_location("virt_fixture", ANALYSIS /
    "s20plus-y2q-pid1-next-20261127/elf-review/verify-retained-pair.py")
vm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vm)


def run(candidate, out, mode):
    out.mkdir(parents=True, exist_ok=False)
    dt = out/"virt.dtb"
    dt.write_bytes((REFERENCE/"virt.dtb").read_bytes())
    def put(*args):
        subprocess.run(["fdtput",args[0],dt,*args[1:]], check=True)
    tlmm = "/pinctrl@f100000"
    pdc = "/interrupt-controller@51000000"
    for n in (tlmm,pdc,"/reserved-memory/pdc@51000000"):
        put("-cp",n)
    put("-tx","/reserved-memory/pdc@51000000","reg","0","51000000","0","30000")
    put("-tx","/reserved-memory/pdc@51000000","no-map")
    put("-ts",tlmm,"compatible","qcom,sm8250-pinctrl")
    # First resource preserves the platform device name. The three resources
    # actually mapped by the driver are guest RAM models of its named tiles.
    put("-cp","/reserved-memory/tiles@53000000")
    put("-tx","/reserved-memory/tiles@53000000","reg","0","53000000","0","900000")
    put("-tx","/reserved-memory/tiles@53000000","no-map")
    put("-tx",tlmm,"reg","0","f100000","0","1000","0","53000000","0","300000",
        "0","53300000","0","300000","0","53600000","0","300000")
    put("-ts",tlmm,"reg-names","fixture-id","west","south","north")
    put("-tx",tlmm,"interrupts","0","50","4")
    put("-tx",tlmm,"gpio-controller")
    put("-tx",tlmm,"#gpio-cells","2")
    put("-tx",tlmm,"phandle","444")
    put("-tx",tlmm,"gpio-ranges","444","0","0","b5")
    put("-tx",tlmm,"wakeup-parent","445")
    put("-tx",pdc,"phandle","445")
    put("-ts",pdc,"compatible","qcom,sm8250-pdc","qcom,pdc")
    put("-tx",pdc,"reg","0","51000000","0","30000")
    put("-tx",pdc,"interrupt-controller")
    put("-tx",pdc,"#interrupt-cells","2")
    put("-tx",pdc,"qcom,pdc-ranges","0","60","10")
    if mode=="missing":
        put("-ts",pdc,"status","disabled")
    objects=candidate/"kernel-build"
    symbols={r[2]:int(r[0],16) for line in (objects/"System.map").read_text().splitlines() if len(r:=line.split())==3}
    asm = subprocess.check_output(["aarch64-linux-gnu-objdump", "-d", "--disassemble=deferred_probe_initcall",
                                   objects/"vmlinux"], text=True)
    calls = re.findall(r"^\s*([0-9a-f]+):.*\bbl\s+\w+ <driver_deferred_probe_trigger[^>]*>", asm, re.M)
    if len(calls) != 2:
        raise ValueError("expected two deferred trigger calls")
    first_trigger_call = int(calls[0], 16)
    seed=REFERENCE/"seed.ram"
    with tempfile.TemporaryDirectory() as tmp:
        socket=Path(tmp)/"gdb"
        # Only the fast control skips the first queue trigger in the VM;
        # the candidate still calls through the real start_flush_work().
        trace=f"""set pagination off
set confirm off
target remote {socket}
python
import gdb
from pathlib import Path
def reg(k):return int(gdb.parse_and_eval('$'+k))%(1<<64)
def stop(name):
 gdb.execute('thbreak *'+hex({symbols['y2q_open']} if name=='open' else {first_trigger_call}),to_string=True)
 gdb.execute('continue',to_string=True)
stop('open')
watched=reg('x0')
if {mode=='idle'!r}:
 stop('trigger')
 assert reg('pc') == {first_trigger_call}
 gdb.execute('set $pc=$pc+4')
def save(name):
 gdb.execute('maintenance packet Qqemu.PhyMemMode:1',to_string=True)
 Path({str(out)!r},name).write_bytes(bytes(gdb.selected_inferior().read_memory({vm.BASE-vm.GUARD},{vm.LENGTH+2*vm.GUARD})))
 gdb.execute('maintenance packet Qqemu.PhyMemMode:0',to_string=True)
if {mode!='idle'!r}:
 class AtWait(gdb.Breakpoint):
  def stop(self):return reg('x0')==watched and reg('x1')==4
 w=AtWait('*'+hex({symbols['y2q_flush']}),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
 gdb.execute('continue',to_string=True)
 assert reg('pc')=={symbols['y2q_flush']} and reg('x1')==4
 ret=reg('x30');entry_sp=reg('sp');w.delete()
 class Caller(gdb.Breakpoint):
  def stop(self):return reg('sp')==entry_sp
 c=Caller('*'+hex(ret),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
 gdb.execute('continue',to_string=True);c.delete()
 assert reg('pc')==ret
 save('before-wait.ram')
class End(gdb.Breakpoint):
 def stop(self):return reg('x0')==309
bp=End('*'+hex({symbols['y2q_progress']}),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
gdb.execute('continue',to_string=True)
assert reg('pc')=={symbols['y2q_progress']} and reg('x0')==309
save('after.ram')
end
detach
"""
        (out/"trace.gdb").write_text(trace)
        args=vm.qemu()+["-serial","stdio","-kernel",objects/"arch/arm64/boot/Image","-initrd",candidate/"initrd.gz",
            "-dtb",dt,"-append","console=ttyAMA0 rdinit=/init cpuidle.off=1","-S","-gdb",f"unix:{socket},server=on,wait=off",
            "-device",f"loader,file={seed},addr={vm.BASE-vm.GUARD:#x},force-raw=on"]
        with (out/"console.log").open("wb") as log, subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,env=vm.ENV) as guest:
            try:
                until=time.monotonic()+6
                while not socket.exists() and time.monotonic()<until:time.sleep(.02)
                with (out/"gdb.log").open("wb") as debug:
                    subprocess.run([vm.GDB,"-nx","-q","-batch","-x",out/"trace.gdb"],stdout=debug,stderr=subprocess.STDOUT,timeout=55,check=True)
            finally:
                guest.terminate()
    nonce=json.loads((candidate/"kernel-inputs.json").read_text())["nonce"]
    original = seed.read_bytes()
    tag = b"TLFIXED1" + bytes.fromhex(nonce)
    def recover(capture):
        raw = capture.read_bytes()
        assert raw.count(tag) == 1
        at = raw.index(tag)
        assert raw[:at] == original[:at] and raw[at+240:] == original[at+240:]
        window = raw[at:at+240]
        capture.with_suffix(".bin").write_bytes(window)
        return decode(window, nonce)

    rows = recover(out/"after.ram")
    last = max((r for r in rows if r["publisher"] == "pid1"), key=lambda r: r["sequence"])
    if mode == "missing":
        assert {"callback", "irq_ok", "wake_missing", "callback_return"} <= set(last["initial"])
        assert "supplier_pdc" not in last["initial"] and last["initial_first_rc"] == -517
        assert "wake_missing" in last["worker"] and last["worker_first_rc"] == -517
    else:
        assert {"supplier_pdc", "link_defer", "queue_inserted", "auto_request"} <= set(last["initial"])
        assert "callback" not in last["initial"] and last["initial_first_rc"] is None
        assert "pdc_published" in last["flush"]
    if mode == "idle":
        assert {"no_barrier", "returned_false"} <= set(last["flush"])
        assert not {"barrier", "before_wait", "after_wait", "returned_true"}.intersection(last["flush"])
        assert not last["worker"]
    else:
        if mode == "ready":
            assert {"wake_found", "irq_ok", "callback_return"} <= set(last["worker"])
            assert last["worker_first_rc"] == 0
        assert {"before_bus", "after_bus"} <= set(last["worker"])
        assert {"barrier", "before_wait", "after_wait", "returned_true"} <= set(last["flush"])
        assert "no_barrier" not in last["flush"]
        cut = recover(out/"before-wait.ram")
        assert any({"barrier","before_wait"} <= set(r["flush"]) for r in cut)
        assert not any({"after_wait","returned_true","returned_false"}.intersection(r["flush"]) for r in cut)
        (out/"before-wait.json").write_text(json.dumps(cut, indent=2)+"\n")
    (out/"decoded.json").write_text(json.dumps(rows,indent=2)+"\n")
    print(mode,rows,flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate",type=Path)
    parser.add_argument("output",type=Path)
    parser.add_argument("mode",choices=("ready","missing","idle"))
    a=parser.parse_args()
    run(a.candidate.resolve(),a.output.resolve(),a.mode)
