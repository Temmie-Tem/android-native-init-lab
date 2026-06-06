import struct,hashlib
BASE="tmp/wifi/v1331-esoc-disasm/"
k=open(BASE+"bootunpack/kernel","rb").read()
sz=struct.unpack_from("<I",k,16)[0];img=k[20:20+sz]
o=open(BASE+"NS.txt","w",buffering=1)
def w(s):o.write(s+"\n");o.flush()
def u64(p):return struct.unpack_from("<Q",img,p)[0]
def u32(p):return struct.unpack_from("<I",img,p)[0]
tt=0x167b6c8
def frame(start):
    o=start;c=0
    while o<tt:
        ln=img[o];o+=1
        if ln==0:return c,o-1
        o+=ln;c+=1
        if c>900000:return c,o
    return c,o
# probe anchors inside names
for back in (50000,150000,400000,800000,1500000,2500000,3500000):
    p=tt-back
    c,e=frame(p)
    w("back=%d pos=0x%x count=%d end_off_from_tt=%d"%(back,p,c,e-tt))
# find the long run start by scanning: first pos (coarse) whose frame ends within 16K of tt with count>=30000
w("--- scan for names runs (end within 16K of tt) ---")
found=[]
p=tt-3*1024*1024
step=1
# to bound, scan but skip ahead when frame bails early
while p<tt-20000:
    c,e=frame(p)
    if c>=30000 and (tt-e)>=0 and (tt-e)<=16384:
        found.append((p,c,e))
        if len(found)<=6:
            w("RUN pos=0x%x count=%d gap=%d u64@pos=0x%x u64@pos-8=0x%x"%(p,c,tt-e,u64(p) if p+8<=len(img) else 0, u64(p-8)))
        # jump to just after this start to find next distinct run start quickly
        p+=max(1, c//4)  # heuristic skip
    else:
        p+=1
    if len(found)>=6: break
w("found_runs=%d"%len(found))
# Now, for the smallest run pos, examine the bytes before it for num_syms (u64 == count)
if found:
    p0=found[0][0]
    w("--- u64 dump before first run pos 0x%x ---"%p0)
    for d in range(8,80,8):
        w("@-%d: u64=0x%x dec=%d"%(d,u64(p0-d),u64(p0-d)))
w("done")
