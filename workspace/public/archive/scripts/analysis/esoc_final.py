#!/usr/bin/env python3
# Host-only FINITE/INFINITE classifier on the DECOMPRESSED kernel (vmlinux.raw).
# Self-locates kallsyms (cumulative cross-check), parses names+addresses,
# self-calibrates VA->file base by bl-target hit rate, builds bounded
# provider-private call graph, classifies external touchpoints, writes verdict.
import struct, re, subprocess, collections, bisect, traceback, hashlib
BASE="tmp/wifi/v1331-esoc-disasm/"
KSRC=BASE+"bootunpack/kernel"   # stable UNCOMPRESSED_IMG-wrapped raw arm64 Image
OBJ="aarch64-linux-gnu-objdump"
LG=open(BASE+"FINALLOG.txt","w",buffering=1)
def lg(s):LG.write(s+"\n");LG.flush()
def u16(b,p):return struct.unpack_from("<H",b,p)[0]
def u64(b,p):return struct.unpack_from("<Q",b,p)[0]

ROOTS=["mdm_subsys_powerup","mdm4x_do_first_power_on","mdm_do_first_power_on",
 "sdx50m_toggle_soft_reset","mdm_cmd_exe","mdm_subsys_shutdown","mdm_status_change",
 "mdm_power_down","mdm_subsys_ramdump","sdx50m_power_down","mdm4x_power_on",
 "sdx50m_setup_hw","mdm9x55_setup_hw","mdm4x_setup_hw"]
CAT={"pcie":re.compile(r"(msm_pcie|pci_msm|dw_pcie|^pcie_|^pci_|_pcie)",re.I),
 "mhi":re.compile(r"(^mhi_|_mhi|mhi_arch|mhi_pci|bhi_)",re.I),
 "regulator":re.compile(r"(regulator_|rpmh_|^rpm_reg)",re.I),
 "gpio":re.compile(r"(gpio|pinctrl|tlmm|gpiod_)",re.I),
 "clk":re.compile(r"(clk_prepare|clk_enable|clk_set|clk_get|__clk_|clk_disable|clk_bulk)",re.I),
 "irq":re.compile(r"(request_irq|request_threaded|enable_irq|disable_irq|free_irq|devm_request_irq|irq_set|gic_)",re.I),
 "wait":re.compile(r"(wait_for_completion|wait_for_err|schedule_timeout|msleep|usleep_range|__const_udelay|wait_event|__delay)",re.I),
 "subsys":re.compile(r"(subsys|__subsystem|sysmon|ssr_)",re.I),
 "esoc":re.compile(r"(esoc)",re.I),
 "scm":re.compile(r"(scm_call|qcom_scm|__scm)",re.I),
 "smem":re.compile(r"(smem|smp2p|glink|qcom_smd|rpmsg)",re.I),
 "pmic":re.compile(r"(spmi|pmic|qpnp|pm8|regmap)",re.I)}
PRIV=re.compile(r"^(mdm|sdx50m|esoc|mdm4x|mdm9|sdx|ext_)")

def locate_tt(img):
    n=len(img)
    def check(tt):
        p=tt;cum=[]
        for k in range(256):
            cum.append(p-tt)
            e=img.find(b"\x00",p,p+48)
            if e<0:return None
            for c in img[p:e]:
                if c<0x09 or c>0x7e:return None
            p=e+1
        for pad in range(8):
            ti=p+pad
            if ti+512>n:return None
            if all(u16(img,ti+2*k)==cum[k] for k in range(256)):
                return tt,ti,[u16(img,ti+2*k) for k in range(256)]
        return None
    i=n//8
    while i<n-2048:
        e=img.find(b"\x00",i,i+40)
        if e>i:
            r=check(i)
            if r:return r
        i+=1
    return None

def main():
    k=open(KSRC,"rb").read()
    lg("ksrc len=%d sha=%s head=%r"%(len(k),hashlib.sha256(k).hexdigest()[:16],k[:16]))
    if k[:16]==b"UNCOMPRESSED_IMG":
        sz=struct.unpack_from("<I",k,16)[0]; img=k[20:20+sz]
    else:
        img=k
    lg("img len=%d sha=%s magic@0x38=%r"%(len(img),hashlib.sha256(img).hexdigest()[:16],img[56:60]))
    r=locate_tt(img)
    if not r:raise RuntimeError("no token_table")
    tt,ti,idx=r
    lg("tt=0x%x ti=0x%x last=%d"%(tt,ti,idx[255]))
    sm=[]
    q=tt
    for k in range(12):
        e=img.find(b"\x00",q);sm.append(img[q:e].decode('latin1'));q=e+1
    lg("toks=%s"%"|".join(sm))
    # Layout (base-relative): kallsyms_offsets[N], relative_base(u64 kernel VA),
    # num_syms(u64), kallsyms_names. Anchor on relative_base = arm64 kernel VA.
    def frame(start):
        p=start;c=0
        while p<tt:
            ln=img[p];p+=1
            if ln==0:return c,p-1
            p+=ln;c+=1
            if c>900000:return c,p
        return c,p
    lo=max(0,tt-9*1024*1024);p=lo&~7;anchor=None
    while p<tt-32:
        v=u64(img,p)
        if (v>>24)==0xffffff80:
            ns=u64(img,p+8)
            if 80000<=ns<=300000:
                c,e=frame(p+16)
                if e==tt and abs(c-ns)<=3:
                    anchor=(p,v,ns);break
        p+=8
    if not anchor:raise RuntimeError("no relbase anchor")
    relpos,rel,N=anchor
    names_start=relpos+16; off_s=relpos-4*N
    lg("rel=0x%x N=%d names_start=0x%x off_s=0x%x"%(rel,N,names_start,off_s))
    names=[];o=names_start
    for _ in range(N):
        ln=img[o];o+=1
        s=bytearray()
        for t in img[o:o+ln]:
            sp=tt+idx[t];e=img.find(b"\x00",sp);s+=img[sp:e]
        o+=ln;names.append(bytes(s))
    offs=struct.unpack_from("<%di"%N,img,off_s)
    # CONFIG_KALLSYMS_ABSOLUTE_PERCPU: off>=0 -> rel+off ; off<0 -> -off-1
    addrs=[rel+x if x>=0 else -x-1 for x in offs]
    inc=sum(1 for i in range(1,min(5000,N)) if addrs[i]>=addrs[i-1])
    layout="base-rel-percpu"
    if inc<4500:
        addrs=[rel+(x&0xffffffff) for x in offs]; layout="base-rel"
    lg("layout=%s a0=0x%x aN=0x%x inc=%d"%(layout,addrs[0],addrs[-1],inc))
    name2a={};pairs=[]
    for i in range(N):
        nm=names[i]
        if not nm:continue
        s=nm[1:].decode("latin1")
        if not s or s[0]=="$":continue
        name2a.setdefault(s,addrs[i]);pairs.append((addrs[i],s))
    al=sorted(set(a for a,_ in pairs))
    nxt={al[i]:(al[i+1] if i+1<len(al) else al[i]+0x400) for i in range(len(al))}
    a2n={}
    for a,s in sorted(pairs):a2n.setdefault(a,s)
    present=[r for r in ROOTS if r in name2a]
    lg("syms=%d roots=%s"%(len(al),",".join(present)))
    if not present:raise RuntimeError("no roots; sample=%s"%",".join(list(name2a)[:20]))
    # calibrate base: file_off = va - base. Try candidates; maximize bl-target hits.
    def disasm_at(va,base,want_hits=False):
        s=va-base;e=nxt[va]-base
        if not(0<=s<len(img)) or not(0<e-s<0x20000):return None
        open("/tmp/_ch.bin","wb").write(img[s:e])
        try:txt=subprocess.run([OBJ,"-D","-b","binary","-m","aarch64","--adjust-vma=0x%x"%va,"/tmp/_ch.bin"],capture_output=True,text=True,timeout=40).stdout
        except Exception:return None
        return txt
    test=name2a[present[0]]
    bestbase=None;bestscore=-1
    aset=set(al)
    for base in (rel, al[0], addrs[0]):
        txt=disasm_at(test,base)
        if not txt:continue
        tg=re.findall(r"\bbl\s+0x([0-9a-f]+)",txt)
        if not tg:
            sc=0
        else:
            hit=sum(1 for t in tg if (int(t,16) in aset) or (bisect.bisect_right(al,int(t,16))-1>=0 and int(t,16)-al[bisect.bisect_right(al,int(t,16))-1]<0x2000))
            sc=hit/len(tg)
        lg("base 0x%x score=%.2f bls=%d"%(base,sc,len(tg)))
        if sc>bestscore:bestscore=sc;bestbase=base
    base=bestbase
    lg("CHOSEN base=0x%x score=%.2f"%(base,bestscore))
    def calls(fn):
        a=name2a.get(fn)
        if a is None:return []
        txt=disasm_at(a,base)
        if not txt:return []
        out=[]
        for ln in txt.splitlines():
            m=re.search(r"\bbl\s+0x([0-9a-f]+)",ln)
            if not m:continue
            t=int(m.group(1),16);nm=a2n.get(t)
            if nm is None:
                j=bisect.bisect_right(al,t)-1
                if j>=0 and t-al[j]<0x2000:nm=a2n.get(al[j])
            if nm and nm!=fn:out.append(nm)
        return out
    seen=set();reached=set();q=collections.deque(present);nc=0;MAX=800
    while q and nc<MAX:
        f=q.popleft()
        if f in seen:continue
        seen.add(f);nc+=1
        for c in calls(f):
            reached.add(c)
            if c not in seen and PRIV.search(c) and c in name2a:q.append(c)
        if nc%50==0:lg("bfs nc=%d q=%d reached=%d"%(nc,len(q),len(reached)))
    lg("bfs done nc=%d reached=%d priv=%d"%(nc,len(reached),len(seen)))
    alls=reached|set(present)
    cc={k:[s for s in sorted(alls) if rgx.search(s)] for k,rgx in CAT.items()}
    pcie=len(cc["pcie"]);mhi=len(cc["mhi"])
    if pcie or mhi:
        v="SELF-CASCADE pcie=%d mhi=%d : provider closure references PCIe/MHI -> one trigger fans out => FINITE auto-cascade"%(pcie,mhi)
    else:
        v="MULTI-SUBSYSTEM-FINITE pcie=0 mhi=0 : provider only drives gpio/reg/clk/irq then waits MDM2AP; PCIe RC + MHI need INDEPENDENT bring-up (finite, separate subsystems, not auto-cascade)"
    V=open(BASE+"FINAL_VERDICT.txt","w",buffering=1)
    V.write("VERDICT %s\n"%v)
    V.write("cats pcie=%d mhi=%d gpio=%d reg=%d clk=%d irq=%d wait=%d esoc=%d subsys=%d scm=%d smem=%d pmic=%d\n"%(
        pcie,mhi,len(cc["gpio"]),len(cc["regulator"]),len(cc["clk"]),len(cc["irq"]),len(cc["wait"]),
        len(cc["esoc"]),len(cc["subsys"]),len(cc["scm"]),len(cc["smem"]),len(cc["pmic"])))
    V.write("roots %s\n"%",".join(present))
    V.write("private %d reached %d N %d layout %s base 0x%x calib %.2f\n"%(len(seen),len(reached),N,layout,base,bestscore))
    V.close()
    D=open(BASE+"FINAL_DETAIL.txt","w",buffering=1)
    for k in CAT:D.write("%s(%d): %s\n"%(k,len(cc[k])," ".join(cc[k][:60])))
    D.write("\n-- private provider funcs --\n%s\n"%" ".join(sorted(seen)))
    D.write("\n-- root direct callees --\n")
    for rr in present:D.write("%s: %s\n"%(rr," ".join(sorted(set(calls(rr)))[:90])))
    D.close()
    lg("DONE")

try:main()
except Exception:lg("EXC "+traceback.format_exc().replace("\n"," | "))
