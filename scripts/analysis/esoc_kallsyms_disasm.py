#!/usr/bin/env python3
"""Host-only static analysis: parse stock v724 kernel kallsyms, build a call
graph for the proprietary ext-sdx50m eSoC provider power-up path, and classify
whether the remaining native Wi-Fi bring-up gap is FINITE (enumerable
gpio/regulator/clk steps the provider drives itself) or INFINITE (the provider
hands off to PCIe/MHI driver cascades = re-implementing Android).

NO device contact. NO writes to the device. Pure PC-side disassembly of
stage3/boot_linux_v724.img's kernel Image.

Usage:
  esoc_kallsyms_disasm.py <Image.stripped> [report_out.md]
"""
import sys, os, struct, re, subprocess, collections

OBJDUMP = "aarch64-linux-gnu-objdump"

# Functions of interest (proprietary provider, present in kallsyms but not OSRC)
ROOTS = [
    "mdm_subsys_powerup",
    "mdm4x_do_first_power_on",
    "mdm_do_first_power_on",
    "sdx50m_toggle_soft_reset",
    "mdm_cmd_exe",
    "mdm_subsys_shutdown",
    "mdm_status_change",
]

# Categories that decide finite vs infinite. If the provider's transitive
# closure CALLS pcie/mhi bring-up directly, the cascade is self-contained
# (lean finite). If it only touches gpio/regulator/clk/pinctrl and then waits,
# PCIe/MHI must be orchestrated externally (lean infinite / coupled).
CAT = {
    "pcie":     re.compile(r"(msm_pcie|pci_msm|dw_pcie|pcie_|^pci_)", re.I),
    "mhi":      re.compile(r"(mhi_|^mhi)", re.I),
    "regulator":re.compile(r"(regulator_|_regulator|rpmh|^rpm_)", re.I),
    "gpio":     re.compile(r"(gpio|gpiod_|pinctrl|msm_gpio|tlmm)", re.I),
    "clk":      re.compile(r"(clk_|_clk$|clk_prepare|clk_enable)", re.I),
    "irq":      re.compile(r"(request_irq|irq_|enable_irq|disable_irq|free_irq)", re.I),
    "wait":     re.compile(r"(wait_for_|complete|schedule_timeout|msleep|usleep|__delay|wait_event)", re.I),
    "subsys":   re.compile(r"(subsys|subsystem_|__subsystem|sysmon|ssr_)", re.I),
    "esoc":     re.compile(r"(esoc)", re.I),
    "scm":      re.compile(r"(scm_|qcom_scm|__scm)", re.I),
    "power":    re.compile(r"(pm_|power_|runtime_|pinctrl_pm)", re.I),
}

def u64(b, o): return struct.unpack_from("<Q", b, o)[0]
def s32(b, o): return struct.unpack_from("<i", b, o)[0]
def u16(b, o): return struct.unpack_from("<H", b, o)[0]

def find_token_table(img, hint=None):
    """token_table = 256 consecutive NUL-terminated strings; token_index = 256
    u16 right after, aligned. Scan for a run of 256 short NUL-terminated tokens."""
    # Heuristic: token strings are short (<=~30) printable-ish. Scan windows.
    # We anchor by trying every offset where a plausible 256-string run starts is
    # too slow; instead use the known structure: token_index[0]==0 and entries
    # monotonic-ish. Fall back to brute scan over a coarse grid.
    n = len(img)
    # token_table is in the kallsyms data area, well past .text. Search the back
    # third of the image at byte granularity but cheaply: look for 256 NUL-terminated
    # strings each len 0..40 with mostly printable bytes.
    def try_at(start):
        o = start; cnt = 0
        while cnt < 256:
            e = img.find(b"\x00", o, o+64)
            if e < 0: return None
            ln = e - o
            if ln > 48: return None
            s = img[o:e]
            for c in s:
                if c < 0x09 or c > 0x7e: return None
            o = e + 1; cnt += 1
        tt_end = o
        # token_index: 256 u16 after alignment. index[0] should be 0.
        for pad in range(0, 8):
            ti = tt_end + pad
            if ti + 512 > n: break
            if u16(img, ti) == 0:
                # validate monotonic non-decreasing and < table length
                ok = True; prev = 0
                for k in range(1, 256):
                    v = u16(img, ti + 2*k)
                    if v < prev or v > (tt_end - start): ok = False; break
                    prev = v
                if ok:
                    return (start, tt_end, ti)
        return None
    # fast path: verify caller-supplied hint offset first
    if hint is not None:
        r = try_at(hint)
        if r: return r
    # coarse then fine: tokens often start right after a NUL run. Scan whole back half.
    start_scan = n // 3
    i = start_scan
    while i < n - 2048:
        r = try_at(i)
        if r: return r
        i += 1
    return None

def load_token_strings(img, tt_start, tt_end):
    toks = []
    o = tt_start
    while o < tt_end and len(toks) < 256:
        e = img.find(b"\x00", o, tt_end+1)
        toks.append(img[o:e]); o = e + 1
    return toks

def decode_names(img, names_start, count, token_index, tt_start, toks):
    """Decode `count` kallsyms records starting at names_start. Returns
    (list_of_names, end_offset) or (None, None) on inconsistency."""
    names = []
    o = names_start
    n = len(img)
    for _ in range(count):
        if o >= n: return None, None
        ln = img[o]; o += 1
        # kernels >=5.x use 2-byte length when high bit set; 4.14 single byte.
        if ln & 0x80:
            # ULEB128-ish 2-byte (defensive; unlikely on 4.14)
            ln2 = img[o]; o += 1
            ln = (ln & 0x7f) | (ln2 << 7)
        if ln == 0 or o + ln > n: return None, None
        rec = img[o:o+ln]; o += ln
        # decode tokens -> string
        s = bytearray()
        for ti in rec:
            # token_index[ti] = byte offset of token in token_table
            toff = token_index[ti]
            # find string
            te = img.find(b"\x00", tt_start + toff)
            s += img[tt_start+toff:te]
        names.append(bytes(s))
    return names, o

def frame_count(img, start, tt_start):
    """Count well-framed kallsyms records from `start` until we reach/pass
    tt_start or hit an invalid record. Framing only (no token resolution) for
    speed. Returns (count, end_offset)."""
    o = start; cnt = 0
    n = len(img)
    while o < tt_start:
        ln = img[o]; o += 1
        if ln & 0x80:
            if o >= n: return cnt, o
            ln = (ln & 0x7f) | (img[o] << 7); o += 1
        if ln == 0: return cnt, o-1
        o += ln
        cnt += 1
        if cnt > 800000: break
    return cnt, o

def parse_kallsyms(img):
    n = len(img)
    tt = find_token_table(img, hint=0x1948bf0)
    if not tt: raise RuntimeError("token_table not found")
    tt_start, tt_end, ti_off = tt
    log("  tt_start=0x%x tt_end=0x%x ti_off=0x%x" % (tt_start, tt_end, ti_off))
    token_index = [u16(img, ti_off + 2*k) for k in range(256)]
    toks = load_token_strings(img, tt_start, tt_end)

    # markers sit between names and token_table. Brute force num_syms in a window
    # before token_table. names directly follows num_syms (8B) in 4.14 layout.
    win_lo = max(0, tt_start - 6*1024*1024)
    best = None
    pos = win_lo & ~7
    while pos < tt_start - 16:
        N = u64(img, pos)
        if 30000 <= N <= 600000:
            ns = pos + 8  # names directly follow num_syms (u64) in 4.14 layout
            cnt, end = frame_count(img, ns, tt_start)
            if cnt == N:
                gap = tt_start - end
                markers_max = (((N+255)>>8)+1)*8 + 64
                if 0 <= gap <= markers_max:
                    names, end2 = decode_names(img, ns, N, token_index, tt_start, toks)
                    if names is not None and any(b"mdm_subsys_powerup" in nm for nm in names):
                        best = (pos, N, ns, names, end2)
                        break
        pos += 8
    if not best:
        raise RuntimeError("num_syms/names anchor not found")
    num_pos, N, names_start, names, names_end = best
    log("  num_pos=0x%x N=%d names_start=0x%x names_end=0x%x" % (num_pos, N, names_start, names_end))

    # addresses: base-relative layout. offsets[N] (s32) then relative_base(u64)
    # then num_syms(u64 at num_pos). So relative_base at num_pos-8.
    rel_base = u64(img, num_pos - 8)
    addrs = None
    layout = None
    # try base-relative
    off_arr_start = num_pos - 8 - 4*N
    if off_arr_start >= 0 and (rel_base >> 48) == 0xffff:
        offs = struct.unpack_from("<%di" % N, img, off_arr_start)
        a = []
        # CONFIG_KALLSYMS_ABSOLUTE_PERCPU: off>=0 -> base+off ; off<0 -> -off-1
        for off in offs:
            if off >= 0: a.append(rel_base + off)
            else:        a.append(-off - 1)
        # sanity: mostly increasing kernel VAs
        inc = sum(1 for i in range(1, min(2000, N)) if a[i] >= a[i-1])
        if inc > 1900:
            addrs = a; layout = "base-relative-percpu"
    if addrs is None:
        # try plain base-relative (all offsets positive)
        if off_arr_start >= 0:
            offs = struct.unpack_from("<%di" % N, img, off_arr_start)
            a = [rel_base + (off & 0xffffffff) for off in offs]
            inc = sum(1 for i in range(1, min(2000, N)) if a[i] >= a[i-1])
            if inc > 1900:
                addrs = a; layout = "base-relative"
    if addrs is None:
        # absolute u64 table
        abs_start = num_pos - 8*N
        if abs_start >= 0:
            a = list(struct.unpack_from("<%dQ" % N, img, abs_start))
            inc = sum(1 for i in range(1, min(2000, N)) if a[i] >= a[i-1])
            if inc > 1900 and (a[N//2] >> 48) == 0xffff:
                addrs = a; layout = "absolute"
    if addrs is None:
        raise RuntimeError("address table not resolved")

    return {
        "N": N, "names": names, "addrs": addrs, "rel_base": rel_base,
        "tt_start": tt_start, "ti_off": ti_off, "num_pos": num_pos,
        "names_start": names_start, "layout": layout,
    }

LOG = None
def log(s):
    if LOG: LOG.write(s + "\n"); LOG.flush()

def main():
    global LOG
    img_path = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "esoc_disasm_report.md"
    LOG = open(out + ".log", "w", buffering=1)
    log("STAGE read-image")
    img = open(img_path, "rb").read()
    log("STAGE read-ok len=%d" % len(img))
    log("STAGE parse-kallsyms")
    ks = parse_kallsyms(img)
    log("STAGE parse-ok N=%d layout=%s" % (ks["N"], ks["layout"]))
    N = ks["N"]; names = ks["names"]; addrs = ks["addrs"]

    # strip leading type char from names; build name->addr (skip mapping syms)
    sym = []  # (addr, name)
    for i in range(N):
        nm = names[i]
        if not nm: continue
        t = chr(nm[0]); name = nm[1:].decode("latin1")
        if name in ("$x", "$d") or name.startswith("$"): continue
        sym.append((addrs[i], name, t))
    # sort by addr to compute extents
    by_addr = sorted(set((a, nm) for a, nm, t in sym))
    name2addr = {}
    for a, nm, t in sym:
        name2addr.setdefault(nm, a)
    # extent: next distinct addr
    addr_list = sorted(set(a for a, _ in by_addr))
    next_addr = {}
    for i, a in enumerate(addr_list):
        next_addr[a] = addr_list[i+1] if i+1 < len(addr_list) else a + 0x400
    # addr -> name (first)
    addr2name = {}
    for a, nm in by_addr:
        addr2name.setdefault(a, nm)

    # text base = _text (Image byte 0)
    text_va = name2addr.get("_text") or name2addr.get("_stext") or min(addr_list)
    def va2off(va): return va - text_va
    def off_ok(o): return 0 <= o < len(img)

    def disasm_calls(fname):
        """Return list of callee names reached by BL/B from fname."""
        a = name2addr.get(fname)
        if a is None: return None
        start = va2off(a); end = va2off(next_addr[a])
        if not (off_ok(start) and end > start and end - start < 0x20000): return []
        cmd = [OBJDUMP, "-D", "-b", "binary", "-m", "aarch64",
               "--adjust-vma=0x%x" % a,
               "--start-address=0x%x" % a, "--stop-address=0x%x" % (a + (end-start)),
               img_path]
        # objdump on the whole file with start/stop in file-offset terms:
        # easier: carve the bytes.
        chunk = img[start:end]
        tmpf = "/tmp/_esoc_chunk.bin"
        open(tmpf, "wb").write(chunk)
        cmd = [OBJDUMP, "-D", "-b", "binary", "-m", "aarch64",
               "--adjust-vma=0x%x" % a, tmpf]
        try:
            txt = subprocess.run(cmd, capture_output=True, text=True, timeout=60).stdout
        except Exception as e:
            return []
        callees = []
        for line in txt.splitlines():
            m = re.search(r"\b(bl|b)\s+0x([0-9a-f]+)", line)
            if not m: continue
            tgt = int(m.group(2), 16)
            # resolve to nearest symbol <= tgt
            nm = addr2name.get(tgt)
            if nm is None:
                # nearest lower
                import bisect
                idx = bisect.bisect_right(addr_list, tgt) - 1
                if idx >= 0:
                    base = addr_list[idx]
                    if tgt - base < 0x4000:
                        nm = addr2name.get(base)
            if nm and nm != fname:
                callees.append((m.group(1), nm))
        return callees

    def categorized(s):
        return any(rgx.search(s) for rgx in CAT.values())
    GENERIC = re.compile(r"^(printk|memcpy|memset|memmove|strn?cmp|strn?cpy|strlen|"
                         r"_raw_spin|spin_|mutex_|__stack_chk|panic|dump_stack|"
                         r"kmalloc|kfree|kmem_|kzalloc|vmalloc|vfree|__warn|warn_|"
                         r"snprintf|sprintf|vsnprintf|seq_|simple_|__const_udelay|"
                         r"preempt_|rcu_|down_|up_|wake_up|__might_sleep|might_fault|"
                         r"_cond_resched|copy_to_user|copy_from_user|__memcpy|memchr|"
                         r"kstrtoull|kstrtoint|of_|fwnode_|device_property|dev_err|"
                         r"dev_warn|dev_info|dev_dbg|_dev_info|sysfs_|kobject_)")

    # BFS: only RECURSE into provider-private (uncategorized, non-generic) symbols.
    # Categorized callees (pcie/mhi/gpio/regulator/...) are recorded as touchpoints
    # but not expanded -- we only care THAT the provider reaches them.
    seen = set(); reached = set(); edges = []
    q = collections.deque()
    present_roots = [r for r in ROOTS if r in name2addr]
    for r in present_roots: q.append(r)
    MAXN = 2500
    nproc = 0
    while q and nproc < MAXN:
        f = q.popleft()
        if f in seen: continue
        seen.add(f); nproc += 1
        if nproc % 100 == 0: log("  bfs nproc=%d q=%d reached=%d" % (nproc, len(q), len(reached)))
        cs = disasm_calls(f) or []
        for kind, callee in cs:
            reached.add(callee)
            edges.append((f, kind, callee))
            if callee in seen: continue
            if categorized(callee): continue          # touchpoint: don't expand
            if GENERIC.search(callee): continue        # generic helper: don't expand
            if callee not in name2addr: continue
            q.append(callee)
    log("  bfs done nproc=%d reached=%d" % (nproc, len(reached)))
    seen = reached | seen

    # categorize all reached symbols
    catcount = {k: [] for k in CAT}
    for s in sorted(seen):
        for k, rgx in CAT.items():
            if rgx.search(s):
                catcount[k].append(s)

    pcie_hits = catcount["pcie"]; mhi_hits = catcount["mhi"]
    gpio_hits = catcount["gpio"]; reg_hits = catcount["regulator"]
    clk_hits = catcount["clk"]; pin_present = any("pinctrl" in s for s in gpio_hits)

    # verdict
    if pcie_hits or mhi_hits:
        verdict = "INFINITE-LEANING: provider closure directly reaches PCIe/MHI bring-up -> self-cascade present, but that means crossing into full PCIe+MHI+Sahara orchestration (driver cascade)."
        # Actually: if provider itself drives PCIe+MHI, the *single* gate (power on) cascades -> FINITE-ish.
        verdict2 = "REINTERPRET: provider directly invoking PCIe/MHI means one trigger fans out automatically => FINITE cascade (the kernel does the rest once provider runs)."
    else:
        verdict = "FINITE-LEANING (provider scope): closure touches gpio/regulator/clk/irq/wait only, NOT pcie/mhi. Provider asserts AP2MDM + waits for MDM2AP; PCIe RC + MHI are a SEPARATE subsystem -> they must be brought up by the PCIe/MHI drivers independently (external orchestration)."
        verdict2 = "Implication: enabling PCIe RC1 GDSC + msm_pcie probe + MHI controller is a DISTINCT finite step set, not auto-driven by the eSoC provider. Net: FINITE but multi-subsystem."

    lines = []
    lines.append("# eSoC provider call-graph FINITE/INFINITE verdict (disasm-confirmed)")
    lines.append("")
    lines.append("kallsyms: N=%d layout=%s rel_base=0x%x text_va=0x%x tt@0x%x" % (
        N, ks["layout"], ks["rel_base"], text_va, ks["tt_start"]))
    lines.append("roots present: %s" % ", ".join(present_roots))
    lines.append("missing roots: %s" % ", ".join(r for r in ROOTS if r not in name2addr))
    lines.append("transitive symbols reached: %d (cap %d)" % (len(seen), MAXN))
    lines.append("")
    lines.append("## category hit counts in transitive closure")
    for k in CAT:
        lines.append("- %-10s : %d" % (k, len(catcount[k])))
    lines.append("")
    lines.append("## VERDICT")
    lines.append(verdict)
    lines.append(verdict2)
    lines.append("")
    for k in ("pcie", "mhi", "regulator", "gpio", "clk", "wait", "esoc", "scm", "subsys"):
        sample = catcount[k][:25]
        lines.append("### %s (%d): %s" % (k, len(catcount[k]), ", ".join(sample)))
    lines.append("")
    lines.append("## direct callees of each root")
    for r in present_roots:
        cs = disasm_calls(r) or []
        uniq = sorted(set(c for _, c in cs))
        lines.append("### %s -> (%d) %s" % (r, len(uniq), ", ".join(uniq[:60])))
    report = "\n".join(lines)
    open(out, "w").write(report)
    # short stdout
    print("PARSE OK N=%d layout=%s reached=%d" % (N, ks["layout"], len(seen)))
    print("pcie=%d mhi=%d gpio=%d reg=%d clk=%d wait=%d esoc=%d" % (
        len(pcie_hits), len(mhi_hits), len(gpio_hits), len(reg_hits),
        len(clk_hits), len(catcount["wait"]), len(catcount["esoc"])))
    print("VERDICT:", verdict.split(":")[0])
    print("report ->", out)

if __name__ == "__main__":
    main()
