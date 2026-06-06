import struct, hashlib, gzip
BASE="tmp/wifi/v1331-esoc-disasm/"
o=open(BASE+"RX.txt","w",buffering=1)
def w(s):o.write(s+"\n");o.flush()

src="tmp/wifi/v1331-esoc-disasm/bootunpack/kernel"
k=open(src,"rb").read()
w("kernel src=%s len=%d sha=%s"%(src,len(k),hashlib.sha256(k).hexdigest()[:16]))
w("head64=%s"%k[:64].hex())
w("head_ascii=%r"%k[:24])

# Detect format
img=None
if k[:2]==b"\x1f\x8b":
    img=gzip.decompress(k); w("gzip -> %d"%len(img))
elif k[:16]==b"UNCOMPRESSED_IMG":
    sz=struct.unpack_from("<I",k,16)[0]
    img=k[20:20+sz]; w("UNCOMPRESSED_IMG sz=%d sliced=%d"%(sz,len(img)))
else:
    # maybe wrapper at different spot; search arm64 magic 'ARM\x64' = 41 52 4d 64 at off 0x38
    # arm64 Image: bytes 0..3 = code0 (b instr), magic 'ARMd' at offset 56 (0x38)
    pos=k.find(b"ARMd")
    w("ARMd at %d"%pos)
    if pos>=8:
        start=pos-56  # magic is at offset 0x38 from Image start
        if start>=0:
            img=k[start:]; w("sliced from arm64 hdr start=%d len=%d"%(start,len(img)))

if img is None:
    w("FORMAT UNKNOWN"); o.close(); raise SystemExit

# arm64 header check
magic=img[56:60]
w("arm64 magic@0x38=%r text_off=0x%x image_size=0x%x"%(
    magic, struct.unpack_from("<Q",img,8)[0], struct.unpack_from("<Q",img,16)[0]))
out=BASE+"Image.clean"
open(out,"wb").write(img)
w("wrote %s len=%d sha=%s"%(out,len(img),hashlib.sha256(img).hexdigest()[:16]))

# verify token_table locate (definitive cumulative check)
def u16(p):return struct.unpack_from("<H",img,p)[0]
def check(tt):
    p=tt;cum=[]
    for kk in range(256):
        cum.append(p-tt)
        e=img.find(b"\x00",p,p+48)
        if e<0:return None
        for c in img[p:e]:
            if c<0x09 or c>0x7e:return None
        p=e+1
    for pad in range(8):
        ti=p+pad
        if ti+512>len(img):return None
        if all(u16(ti+2*kk)==cum[kk] for kk in range(256)):
            return tt,ti
    return None
n=len(img);i=n//4;hit=None
while i<n-2048:
    e=img.find(b"\x00",i,i+40)
    if e>i:
        r=check(i)
        if r:hit=r;break
    i+=1
if hit:
    tt,ti=hit
    w("TOKENTABLE tt=0x%x ti=0x%x"%(tt,ti))
    sm=[];q=tt
    for kk in range(16):
        e=img.find(b"\x00",q);sm.append(img[q:e].decode('latin1'));q=e+1
    w("toks=%s"%"|".join(sm))
    # quick: is mdm_subsys_powerup present anywhere in image as literal? (token-compressed, so search raw substring won't work, but check token presence loosely)
else:
    w("TOKENTABLE NOT FOUND")
w("done")
