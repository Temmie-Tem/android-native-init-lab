import os
BASE="tmp/wifi/v1331-esoc-disasm/"
P=BASE+"Image.stripped"
o=open(BASE+"PR.txt","w",buffering=1)
def w(s):o.write(s+"\n");o.flush()
fd=os.open(P,os.O_RDONLY)
sz=os.fstat(fd).st_size
w("size=%d"%sz)
tt=0x1948bf0
for mb in (1,2,4,6,8):
    span=mb*1024*1024
    start=max(0,tt-span)
    buf=os.pread(fd,span+0x4000,start)
    # access first, middle, last byte + a find
    acc=buf[0]+buf[len(buf)//2]+buf[-1]
    nul=buf.find(b"\x00")
    w("mb=%d ok len=%d acc=%d firstnul=%d"%(mb,len(buf),acc,nul))
os.close(fd)
w("alldone")
