#!/usr/bin/env python3
# Host-only corrected eSoC provider call-graph FINITE/INFINITE classifier.
# Uses the REAL kallsyms token_index found by scanning (0x132ac88), derives exact
# token_table_start, parses num_syms/names/address-table, builds a bounded
# provider-private call graph, classifies external touchpoints, writes verdict.
import struct, re, subprocess, collections, bisect, traceback
BASE="tmp/wifi/v1331-esoc-disasm/"
IMG=BASE+"Image.stripped"
OBJ="aarch64-linux-gnu-objdump"
LG=open(BASE+"V2LOG.txt","w",buffering=1)
def lg(s):LG.write(s+"\n");LG.flush()
def u16(b,p):return struct.unpack_from("<H",b,p)[0]
def u64(b,p):return struct.unpack_from("<Q",b,p)[0]

ROOTS=["mdm_subsys_powerup","mdm4x_do_first_power_on","mdm_do_first_power_on",
 "sdx50m_toggle_soft_reset","mdm_cmd_exe","mdm_subsys_shutdown","mdm_status_change",
 "mdm_power_down","mdm_subsys_ramdump","sdx50m_power_down","mdm4x_power_on",
 "mdm9x55_setup_hw","sdx50m_setup_hw"]
CAT={"pcie":re.compile(r"(msm_pcie|pci_msm|dw_pcie|^pcie_|^pci_|_pcie)",re.I),
 "mhi":re.compile(r"(^mhi_|_mhi|mhi_arch|mhi_pci|bhi_)",re.I),
 "regulator":re.compile(r"(regulator_|rpmh_|^rpm_reg)",re.I),
 "gpio":re.compile(r"(gpio|pinctrl|tlmm|__gpiod|gpiod_)",re.I),
 "clk":re.compile(r"(clk_prepare|clk_enable|clk_set|clk_get|__clk_|clk_disable)",re.I),
 "irq":re.compile(r"(request_irq|request_threaded|enable_irq|disable_irq|free_irq|devm_request_irq|irq_set)",re.I),
 "wait":re.compile(r"(wait_for_completion|wait_for_err|schedule_timeout|msleep|usleep_range|__const_udelay|wait_event)",re.I),
 "subsys":re.compile(r"(subsys|__subsystem|sysmon|ssr_)",re.I),
 "esoc":re.compile(r"(esoc)",re.I),
 "scm":re.compile(r"(scm_call|qcom_scm)",re.I),
 "smem":re.compile(r"(smem|smp2p|glink|qcom_smd|rpmsg)",re.I),
 "pmic":re.compile(r"(spmi|pmic|qpnp|pm8|regmap)",re.I)}
PRIV=re.compile(r"^(mdm|sdx50m|esoc|mdm4x|mdm9|sdx|ext_)")

def solve_tt_start(img, ti):
    idx=[u16(img,ti+2*k) for k in range(256)]
    last=idx[255]
    for tt in range(ti-last-80, ti-last+8):
        if tt<0: continue
        ok=True
        for k in range(255):
            # token k spans [tt+idx[k], tt+idx[k+1]-1), NUL at tt+idx[k+1]-1
            if img[tt+idx[k+1]-1]!=0: ok=False; break
        if ok and img[ti-1]==0:  # NUL terminates last token before token_index
            return tt, idx
    # relaxed: just require terminators
    for tt in range(ti-last-80, ti-last+8):
        if tt<0: continue
        if all(img[tt+idx[k+1]-1]==0 for k in range(255)):
            return tt, idx
    return None, idx

def locate_tt(img):
    """Definitive: find tt where 256 NUL tokens' cumulative offsets equal the
    following u16 array. Verify hardcoded hint first, else full scan."""
    n=len(img)
    def check(tt):
        p=tt; cum=[]
        for k in range(256):
            cum.append(p-tt)
            e=img.find(b"\x00",p,p+48)
            if e<0: return None
            for c in img[p:e]:
                if c<0x09 or c>0x7e: return None
            p=e+1
        for pad in range(8):
            ti=p+pad
            if ti+512>n: return None
            if all(u16(img,ti+2*k)==cum[k] for k in range(256)):
                return tt,ti,[u16(img,ti+2*k) for k in range(256)]
        return None
    r=check(0x167b6c8)
    if r: return r
    i=n//4
    while i<n-2048:
        e=img.find(b"\x00",i,i+40)
        if e>i:
            r=check(i)
            if r: return r
        i+=1
    return None

def main():
    lg("read")
    img=open(IMG,"rb").read()
    lg("len=%d"%len(img))
    r=locate_tt(img)
    if r is None: raise RuntimeError("token_table not located")
    tt,ti,idx=r
    lg("tt_start=0x%x ti=0x%x last=%d"%(tt,ti,idx[255]))
    # sanity: decode a few tokens
    sample=[]
    for k in (0,1,2,10,50,100,200,255):
        sp=tt+idx[k]; e=img.find(b"\x00",sp,sp+64); sample.append(img[sp:e])
    lg("toks=%s"%b",".join(sample))
    # num_syms scan: names directly after num_syms u64; framing-only count==N.
    def frame(start):
        o=start;c=0;N=len(img)
        while o<tt:
            ln=img[o];o+=1
            if ln&0x80:
                if o>=N:return c,o
                ln=(ln&0x7f)|(img[o]<<7);o+=1
            if ln==0:return c,o-1
            o+=ln;c+=1
            if c>900000:break
        return c,o
    lo=max(0,tt-8*1024*1024);pos=lo&~7;best=None
    while pos<tt-16:
        N=u64(img,pos)
        if 30000<=N<=600000:
            c,end=frame(pos+8)
            if c==N:
                gap=tt-end;mm=(((N+255)>>8)+1)*8+128
                if 0<=gap<=mm: best=(pos,N);break
        pos+=8
    if not best:raise RuntimeError("no numsyms")
    num_pos,N=best
    lg("N=%d num_pos=0x%x"%(N,num_pos))
    # decode names
    names=[];o=num_pos+8
    for _ in range(N):
        ln=img[o];o+=1
        if ln&0x80: ln=(ln&0x7f)|(img[o]<<7);o+=1
        rec=img[o:o+ln];o+=ln
        s=bytearray()
        for t in rec:
            sp=tt+idx[t]; e=img.find(b"\x00",sp); s+=img[sp:e]
        names.append(bytes(s))
    lg("decoded names")
    # addresses
    rel=u64(img,num_pos-8); off_s=num_pos-8-4*N; addrs=None;layout=None
    if off_s>=0 and (rel>>48)==0xffff:
        offs=struct.unpack_from("<%di"%N,img,off_s)
        a=[rel+o if o>=0 else -o-1 for o in offs]
        if sum(1 for i in range(1,min(3000,N)) if a[i]>=a[i-1])>2850: addrs=a;layout="base-rel-percpu"
    if addrs is None and off_s>=0:
        offs=struct.unpack_from("<%di"%N,img,off_s)
        a=[rel+(o&0xffffffff) for o in offs]
        if sum(1 for i in range(1,min(3000,N)) if a[i]>=a[i-1])>2850: addrs=a;layout="base-rel"
    if addrs is None:
        abs_s=num_pos-8*N
        if abs_s>=0:
            a=list(struct.unpack_from("<%dQ"%N,img,abs_s))
            if sum(1 for i in range(1,min(3000,N)) if a[i]>=a[i-1])>2850 and (a[N//2]>>48)==0xffff: addrs=a;layout="absolute"
    if addrs is None:raise RuntimeError("no addrs rel=0x%x"%rel)
    lg("layout=%s rel=0x%x"%(layout,rel))
    # symbol tables
    name2a={};pairs=[]
    for i in range(N):
        nm=names[i]
        if not nm:continue
        s=nm[1:].decode("latin1")
        if not s or s[0]=="$":continue
        name2a.setdefault(s,addrs[i]); pairs.append((addrs[i],s))
    al=sorted(set(a for a,_ in pairs))
    nxt={al[i]:(al[i+1] if i+1<len(al) else al[i]+0x400) for i in range(len(al))}
    a2n={}
    for a,s in sorted(pairs): a2n.setdefault(a,s)
    text=name2a.get("_text") or name2a.get("_stext") or al[0]
    present=[r for r in ROOTS if r in name2a]
    lg("text=0x%x syms=%d roots=%s"%(text,len(al),",".join(present)))
    if not present: raise RuntimeError("no roots present (have %d syms)"%len(al))
    def calls(fn):
        a=name2a.get(fn)
        if a is None:return []
        s=a-text;e=nxt[a]-text
        if not(0<=s<len(img)) or not(0<e-s<0x20000):return []
        open("/tmp/_ch.bin","wb").write(img[s:e])
        try:txt=subprocess.run([OBJ,"-D","-b","binary","-m","aarch64","--adjust-vma=0x%x"%a,"/tmp/_ch.bin"],capture_output=True,text=True,timeout=40).stdout
        except Exception:return []
        out=[]
        for ln in txt.splitlines():
            m=re.search(r"\b(bl|b)\s+0x([0-9a-f]+)",ln)
            if not m:continue
            tgt=int(m.group(2),16); nm=a2n.get(tgt)
            if nm is None:
                j=bisect.bisect_right(al,tgt)-1
                if j>=0 and tgt-al[j]<0x4000: nm=a2n.get(al[j])
            if nm and nm!=fn: out.append(nm)
        return out
    seen=set();reached=set();edges=[];q=collections.deque(present);ncall=0;MAX=600
    while q and ncall<MAX:
        f=q.popleft()
        if f in seen:continue
        seen.add(f);ncall+=1
        for c in calls(f):
            reached.add(c); edges.append((f,c))
            if c not in seen and PRIV.search(c) and c in name2a: q.append(c)
        if ncall%50==0: lg("bfs n=%d q=%d reached=%d"%(ncall,len(q),len(reached)))
    lg("bfs done n=%d reached=%d private=%d"%(ncall,len(reached),len(seen)))
    allsyms=reached|set(present)
    cc={k:[s for s in sorted(allsyms) if rgx.search(s)] for k,rgx in CAT.items()}
    pcie=len(cc["pcie"]);mhi=len(cc["mhi"])
    if pcie or mhi:
        verdict="SELF-CASCADE: provider closure references PCIe/MHI (pcie=%d mhi=%d) -> one trigger fans out => FINITE auto-cascade"%(pcie,mhi)
    else:
        verdict="MULTI-SUBSYSTEM-FINITE: provider closure touches gpio/reg/clk/irq/wait only, NO pcie/mhi -> provider asserts AP2MDM + waits MDM2AP; PCIe RC + MHI need INDEPENDENT bring-up (finite but separate subsystems, not auto-cascade)"
    V=open(BASE+"V2.txt","w",buffering=1)
    V.write("VERDICT %s\n"%verdict)
    V.write("cats pcie=%d mhi=%d gpio=%d reg=%d clk=%d irq=%d wait=%d esoc=%d subsys=%d scm=%d smem=%d pmic=%d\n"%(
        pcie,mhi,len(cc["gpio"]),len(cc["regulator"]),len(cc["clk"]),len(cc["irq"]),len(cc["wait"]),
        len(cc["esoc"]),len(cc["subsys"]),len(cc["scm"]),len(cc["smem"]),len(cc["pmic"])))
    V.write("roots_present %s\n"%",".join(present))
    V.write("private_funcs %d reached %d N %d layout %s\n"%(len(seen),len(reached),N,layout))
    V.close()
    D=open(BASE+"V2DETAIL.txt","w",buffering=1)
    for k in CAT: D.write("%s(%d): %s\n"%(k,len(cc[k])," ".join(cc[k][:50])))
    D.write("\n-- private provider funcs reached --\n%s\n"%" ".join(sorted(seen)))
    D.write("\n-- root direct callees --\n")
    for r in present: D.write("%s: %s\n"%(r," ".join(sorted(set(calls(r)))[:80])))
    D.close()
    lg("DONE verdict written")

try: main()
except Exception: lg("EXC "+traceback.format_exc().replace("\n"," | "))
