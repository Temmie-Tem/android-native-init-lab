import struct
BASE="tmp/wifi/v1331-esoc-disasm/"
k=open(BASE+"bootunpack/kernel","rb").read()
sz=struct.unpack_from("<I",k,16)[0];img=k[20:20+sz]
o=open(BASE+"RB.txt","w",buffering=1)
def w(s):o.write(s+"\n");o.flush()
def u64(p):return struct.unpack_from("<Q",img,p)[0]
tt=0x167b6c8
def frame(start):
    p=start;c=0
    while p<tt:
        ln=img[p];p+=1
        if ln==0:return c,p-1
        p+=ln;c+=1
        if c>900000:return c,p
    return c,p
# Scan window before tt for relative_base (kernel VA) followed by num_syms then names->tt
lo=max(0,tt-9*1024*1024)
hits=0
p=lo&~7
while p<tt-32:
    v=u64(p)
    if (v>>24)==0xffffff80:   # arm64 kernel VA high bits
        ns=u64(p+8)
        if 80000<=ns<=300000:
            c,e=frame(p+16)
            if e==tt and abs(c-ns)<=2:
                w("RELBASE@0x%x rel=0x%x num_syms=%d framecount=%d end-tt=%d"%(p,v,ns,c,e-tt))
                # offsets table start
                offs=p-4*ns
                w("offsets_start=0x%x first_off=%d last_off_via=%d"%(offs, struct.unpack_from('<i',img,offs)[0], struct.unpack_from('<i',img,p-4)[0]))
                hits+=1
                if hits>=3: break
    p+=8
if not hits:
    w("no relbase triple; dumping any kernel-VA u64 in last 2MB")
    p=(tt-2*1024*1024)&~7;cnt=0
    while p<tt-8 and cnt<12:
        v=u64(p)
        if (v>>24)==0xffffff80:
            w("VA@0x%x =0x%x next8=%d"%(p,v,u64(p+8)));cnt+=1
        p+=8
w("done hits=%d"%hits)
