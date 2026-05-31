import struct
BASE="tmp/wifi/v1331-esoc-disasm/"
k=open(BASE+"bootunpack/kernel","rb").read()
sz=struct.unpack_from("<I",k,16)[0];img=k[20:20+sz]
o=open(BASE+"NS2.txt","w",buffering=1)
def w(s):o.write(s+"\n");o.flush()
def u64(p):return struct.unpack_from("<Q",img,p)[0]
def u32(p):return struct.unpack_from("<I",img,p)[0]
tt=0x167b6c8
def frame(start):
    p=start;c=0
    while p<tt:
        ln=img[p];p+=1
        if ln==0:return c,p-1
        p+=ln;c+=1
        if c>900000:return c,p
    return c,p
# binary-search names_start: smallest pos in [tt-3MB, tt] whose frame reaches tt
# with the maximal saturated count. First find max count from a deep anchor.
deep=tt-3*1024*1024
maxc,me=frame(deep)
w("deep pos=0x%x count=%d end-tt=%d"%(deep,maxc,me-tt))
# scan upward (toward tt) to find where count drops below maxc -> that boundary+?
# Actually names_start is the smallest pos giving count==maxc AND end==tt.
# Walk pos from deep upward; once we pass names_start, count decreases.
# find first pos where frame==maxc and end==tt, scanning a fine grid near expected.
# Expected names_start ~ tt - (bytes for maxc records). Avg record ~ a few bytes.
# Just scan from deep upward in steps, record transitions.
prev=None
pos=deep
boundary=None
while pos<tt-1000:
    c,e=frame(pos)
    if e==tt and c==maxc:
        boundary=pos  # keep latest pos that still yields maxc (closest to names_start from below)
        pos+=1
    else:
        # once c<maxc consistently we've passed names_start
        if boundary is not None and c<maxc:
            break
        pos+=1
    if pos-deep>4_000_000: break
w("names_start≈0x%x maxc=%d"%(boundary if boundary else 0, maxc))
ns=boundary
if ns:
    w("--- u64/u32 before names_start ---")
    for d in range(0,96,8):
        w("@ns-%d u64=0x%x dec=%d"%(d,u64(ns-d),u64(ns-d)))
    for d in range(0,48,4):
        w("@ns-%d u32=%d"%(d,u32(ns-d)))
    # bytes at names_start
    w("ns bytes=%s"%img[ns:ns+24].hex())
    # decode first 3 records lengths
    p=ns
    for r in range(4):
        ln=img[p];w("rec%d len=%d toks=%s"%(r,ln,img[p+1:p+1+ln].hex()));p+=1+ln
w("done")
