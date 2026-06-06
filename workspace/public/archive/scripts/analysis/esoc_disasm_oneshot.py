#!/usr/bin/env python3
# Host-only. One-shot: kallsyms parse + bounded provider call-graph + verdict.
# Writes short-line files: V.txt (verdict, read top), VLOG.txt (progress).
import struct, re, subprocess, collections, bisect, traceback
BASE = "tmp/wifi/v1331-esoc-disasm/"
IMG = BASE + "Image.stripped"
OBJ = "aarch64-linux-gnu-objdump"
VLOG = open(BASE + "VLOG.txt", "w", buffering=1)
def lg(s): VLOG.write(s + "\n"); VLOG.flush()
def u16(b,o): return struct.unpack_from("<H",b,o)[0]
def u64(b,o): return struct.unpack_from("<Q",b,o)[0]

ROOTS=["mdm_subsys_powerup","mdm4x_do_first_power_on","mdm_do_first_power_on",
 "sdx50m_toggle_soft_reset","mdm_cmd_exe","mdm_subsys_shutdown","mdm_status_change",
 "mdm_power_down","mdm_subsys_ramdump","sdx50m_power_down"]
CAT={"pcie":re.compile(r"(msm_pcie|pci_msm|dw_pcie|pcie_|^pci_)",re.I),
 "mhi":re.compile(r"(^mhi_|_mhi_|mhi_arch|mhi_pci)",re.I),
 "regulator":re.compile(r"(regulator_|rpmh|^rpm_)",re.I),
 "gpio":re.compile(r"(gpio|pinctrl|tlmm)",re.I),
 "clk":re.compile(r"(clk_|_clk$|clk_prepare|clk_enable)",re.I),
 "irq":re.compile(r"(request_irq|^irq_|enable_irq|disable_irq|free_irq|devm_request)",re.I),
 "wait":re.compile(r"(wait_for_|^complete$|complete\(|schedule_timeout|msleep|usleep|__delay|wait_event)",re.I),
 "subsys":re.compile(r"(subsys|__subsystem|sysmon|ssr_)",re.I),
 "esoc":re.compile(r"(esoc)",re.I),
 "scm":re.compile(r"(scm_|qcom_scm)",re.I),
 "smem":re.compile(r"(smem|smp2p|glink|qcom_smd|rpmsg)",re.I)}
PRIV=re.compile(r"^(mdm|sdx50m|esoc|mdm4x|mdm9|sdx)")

def find_tt(img,hint):
    n=len(img)
    def at(start):
        o=start;cnt=0
        while cnt<256:
            e=img.find(b"\x00",o,o+64)
            if e<0:return None
            if e-o>48:return None
            for c in img[o:e]:
                if c<0x09 or c>0x7e:return None
            o=e+1;cnt+=1
        te=o
        for pad in range(0,8):
            ti=te+pad
            if ti+512>n:break
            if u16(img,ti)==0:
                ok=True;prev=0
                for k in range(1,256):
                    v=u16(img,ti+2*k)
                    if v<prev or v>(te-start):ok=False;break
                    prev=v
                if ok:return(start,te,ti)
        return None
    r=at(hint)
    if r:return r
    i=n//3
    while i<n-2048:
        r=at(i)
        if r:return r
        i+=1
    return None

def frame_count(img,start,tt):
    o=start;c=0;n=len(img)
    while o<tt:
        ln=img[o];o+=1
        if ln&0x80:
            if o>=n:return c,o
            ln=(ln&0x7f)|(img[o]<<7);o+=1
        if ln==0:return c,o-1
        o+=ln;c+=1
        if c>800000:break
    return c,o

def decode(img,ns,N,ti_vals,tt):
    names=[];o=ns;n=len(img)
    for _ in range(N):
        if o>=n:return None,None
        ln=img[o];o+=1
        if ln&0x80:
            ln=(ln&0x7f)|(img[o]<<7);o+=1
        if ln==0 or o+ln>n:return None,None
        rec=img[o:o+ln];o+=ln
        s=bytearray()
        for t in rec:
            toff=ti_vals[t]
            te=img.find(b"\x00",tt+toff)
            s+=img[tt+toff:te]
        names.append(bytes(s))
    return names,o

def main():
    lg("read")
    img=open(IMG,"rb").read()
    lg("readlen=%d"%len(img))
    tt=find_tt(img,0x1948bf0)
    if not tt:raise RuntimeError("no tt")
    tt_s,tt_e,ti=tt
    lg("tt=0x%x ti=0x%x"%(tt_s,ti))
    ti_vals=[u16(img,ti+2*k) for k in range(256)]
    lo=max(0,tt_s-6*1024*1024);pos=lo&~7;best=None
    while pos<tt_s-16:
        N=u64(img,pos)
        if 30000<=N<=600000:
            ns=pos+8
            c,end=frame_count(img,ns,tt_s)
            if c==N:
                gap=tt_s-end;mm=(((N+255)>>8)+1)*8+64
                if 0<=gap<=mm:
                    names,_=decode(img,ns,N,ti_vals,tt_s)
                    if names and any(b"mdm_subsys_powerup" in x for x in names):
                        best=(pos,N,names);break
        pos+=8
    if not best:raise RuntimeError("no numsyms")
    num_pos,N,names=best
    lg("N=%d num_pos=0x%x"%(N,num_pos))
    rel=u64(img,num_pos-8)
    off_s=num_pos-8-4*N
    addrs=None;layout=None
    if off_s>=0 and (rel>>48)==0xffff:
        offs=struct.unpack_from("<%di"%N,img,off_s)
        a=[rel+o if o>=0 else -o-1 for o in offs]
        if sum(1 for i in range(1,min(2000,N)) if a[i]>=a[i-1])>1900:
            addrs=a;layout="base-rel-percpu"
    if addrs is None and off_s>=0:
        offs=struct.unpack_from("<%di"%N,img,off_s)
        a=[rel+(o&0xffffffff) for o in offs]
        if sum(1 for i in range(1,min(2000,N)) if a[i]>=a[i-1])>1900:
            addrs=a;layout="base-rel"
    if addrs is None:
        abs_s=num_pos-8*N
        if abs_s>=0:
            a=list(struct.unpack_from("<%dQ"%N,img,abs_s))
            if sum(1 for i in range(1,min(2000,N)) if a[i]>=a[i-1])>1900 and (a[N//2]>>48)==0xffff:
                addrs=a;layout="absolute"
    if addrs is None:raise RuntimeError("no addrs")
    lg("layout=%s rel=0x%x"%(layout,rel))
    # build sym tables (skip mapping/$ syms)
    name2a={};pairs=[]
    for i in range(N):
        nm=names[i]
        if not nm:continue
        s=nm[1:].decode("latin1")
        if not s or s[0]=="$":continue
        name2a.setdefault(s,addrs[i])
        pairs.append((addrs[i],s))
    al=sorted(set(a for a,_ in pairs))
    nxt={al[i]:(al[i+1] if i+1<len(al) else al[i]+0x400) for i in range(len(al))}
    a2n={}
    for a,s in sorted(pairs):a2n.setdefault(a,s)
    text=name2a.get("_text") or name2a.get("_stext") or al[0]
    lg("text=0x%x syms=%d"%(text,len(al)))
    present=[r for r in ROOTS if r in name2a]
    lg("roots=%s"%",".join(present))
    def calls(fn):
        a=name2a.get(fn)
        if a is None:return []
        s=a-text;e=nxt[a]-text
        if not(0<=s<len(img)) or not(0<e-s<0x20000):return []
        open("/tmp/_ch.bin","wb").write(img[s:e])
        cmd=[OBJ,"-D","-b","binary","-m","aarch64","--adjust-vma=0x%x"%a,"/tmp/_ch.bin"]
        try:txt=subprocess.run(cmd,capture_output=True,text=True,timeout=40).stdout
        except Exception:return []
        out=[]
        for ln in txt.splitlines():
            m=re.search(r"\b(bl|b)\s+0x([0-9a-f]+)",ln)
            if not m:continue
            tgt=int(m.group(2),16)
            nm=a2n.get(tgt)
            if nm is None:
                idx=bisect.bisect_right(al,tgt)-1
                if idx>=0 and tgt-al[idx]<0x4000:nm=a2n.get(al[idx])
            if nm and nm!=fn:out.append(nm)
        return out
    # bounded BFS: recurse only into provider-private helpers
    seen=set();reached=set();q=collections.deque(present);ncall=0;MAX=400
    while q and ncall<MAX:
        f=q.popleft()
        if f in seen:continue
        seen.add(f);ncall+=1
        for c in calls(f):
            reached.add(c)
            if c not in seen and PRIV.search(c) and c in name2a:q.append(c)
        if ncall%50==0:lg("bfs n=%d q=%d reached=%d"%(ncall,len(q),len(reached)))
    lg("bfs done n=%d reached=%d"%(ncall,len(reached)))
    allsyms=reached|set(present)
    cc={k:[s for s in sorted(allsyms) if rgx.search(s)] for k,rgx in CAT.items()}
    pcie=len(cc["pcie"]);mhi=len(cc["mhi"])
    if pcie or mhi:
        verdict="MIXED-SELFCASCADE pcie=%d mhi=%d : provider code path itself references PCIe/MHI -> one trigger fans out (lean FINITE cascade)"%(pcie,mhi)
    else:
        verdict="FINITE-SCOPE pcie=0 mhi=0 : provider only drives gpio/reg/clk/irq then waits; PCIe RC+MHI are a SEPARATE subsystem needing independent bring-up (multi-subsystem finite, NOT auto-cascade)"
    V=open(BASE+"V.txt","w",buffering=1)
    V.write("VERDICT %s\n"%verdict)
    V.write("cats pcie=%d mhi=%d gpio=%d reg=%d clk=%d irq=%d wait=%d esoc=%d subsys=%d scm=%d smem=%d\n"%(
        pcie,mhi,len(cc["gpio"]),len(cc["regulator"]),len(cc["clk"]),len(cc["irq"]),
        len(cc["wait"]),len(cc["esoc"]),len(cc["subsys"]),len(cc["scm"]),len(cc["smem"])))
    V.write("roots %s\n"%",".join(present))
    V.write("reached %d layout %s N %d\n"%(len(reached),layout,N))
    V.close()
    # detail file
    D=open(BASE+"VDETAIL.txt","w",buffering=1)
    for k in CAT:
        D.write("%s(%d): %s\n"%(k,len(cc[k])," ".join(cc[k][:40])))
    D.write("\n--root direct callees--\n")
    for r in present:
        D.write("%s: %s\n"%(r," ".join(sorted(set(calls(r)))[:60])))
    D.close()
    lg("VERDICT WRITTEN")

try:
    main()
except Exception:
    lg("EXC "+traceback.format_exc().replace("\n"," | "))
