import struct
BASE="tmp/wifi/v1331-esoc-disasm/"
k=open(BASE+"bootunpack/kernel","rb").read()
sz=struct.unpack_from("<I",k,16)[0];img=k[20:20+sz]
o=open(BASE+"PS.txt","w",buffering=1)
def w(s):o.write(s+"\n");o.flush()
def u64(p):return struct.unpack_from("<Q",img,p)[0]
def u16(p):return struct.unpack_from("<H",img,p)[0]
tt=0x167b6c8;ti=0x167b9bf
idx=[u16(ti+2*kk) for kk in range(256)]
relpos=0x1619300;rel=u64(relpos);N=u64(relpos+8);names_start=relpos+16
w("rel=0x%x N=%d"%(rel,N))
names=[];off=names_start
for _ in range(N):
    ln=img[off];off+=1
    s=bytearray()
    for t in img[off:off+ln]:
        sp=tt+idx[t];e=img.find(b"\x00",sp);s+=img[sp:e]
    off+=ln;names.append(s[1:].decode('latin1'))
w("decoded=%d last_off=0x%x (tt=0x%x)"%(len(names),off,tt))
nameset=set(names)
# sample across the list to detect desync
for i in (0,10000,30000,60000,90000,120000,131000,N-1):
    w("name[%d]=%r"%(i,names[i] if i<N else "OOB"))
# known symbols presence
for s in ["msm_pcie_enumerate","msm_pcie_register_event","icnss_probe","subsys_register",
          "regulator_enable","platform_driver_register","mhi_async_power_up","mhi_register_controller",
          "wait_for_err_ready","subsystem_get","mdm_subsys_powerup","mdm4x_do_first_power_on",
          "sdx50m_toggle_soft_reset","mdm_cmd_exe","mdm_status_change","esoc_dev_init",
          "esoc_clink_register","esoc_register_client_hook"]:
    w("%-32s present=%s"%(s, s in nameset))
# how many names contain 'mdm' or 'esoc' or 'sdx'
for kw in ("mdm","esoc","sdx","pcie","mhi"):
    m=[x for x in names if kw in x]
    w("kw=%s count=%d sample=%s"%(kw,len(m),m[:8]))
w("done")
