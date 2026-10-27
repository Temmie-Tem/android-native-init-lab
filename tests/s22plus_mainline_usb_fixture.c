/* H0 VM only: execute the real production usb() function against dummy_hcd.
 * Module loading exists only in this harness, never the production initramfs.
 */
#define main unused_production_main
#include "../workspace/public/src/mainline/s22plus_canary_h0/init.c"
#undef main
#include <sys/syscall.h>
int main(void) {
    if(getpid()!=1)return 90;
    deadline=now_ms()+30000;
    const char *paths[]={"/dev","/proc","/sys","/config"};
    for(unsigned i=0;i<4;i++)if(folder(paths[i],0755))return 91;
    if(mount("devtmpfs","/dev","devtmpfs",0,NULL))return 92;
    int fd=open("/dev/ttyAMA0",O_RDWR);if(fd<0)return 93;
    for(int i=0;i<3;i++)if(dup2(fd,i)<0)return 94;
    if(fd>2)close(fd);
    if(mount("proc","/proc","proc",0,NULL)||mount("sysfs","/sys","sysfs",0,NULL))park(errno);
    fd=open("/dummy_hcd.ko",O_RDONLY|O_CLOEXEC);if(fd<0)park(errno);
    if(syscall(SYS_finit_module,fd,"",0))park(errno);
    if(close(fd))park(errno);
    if(if_nametoindex("usb0"))park(EEXIST);
    dprintf(2,"USB_FIXTURE_BEFORE_BIND_NETDEV_ABSENT\n");
    int error=usb();if(error)park(error);
    if(!if_nametoindex("usb0"))park(ENODEV);
    fd=socket(AF_INET,SOCK_DGRAM|SOCK_CLOEXEC,0);if(fd<0)park(errno);
    struct ifreq r;memset(&r,0,sizeof(r));strcpy(r.ifr_name,"usb0");
    if(ioctl(fd,SIOCGIFADDR,&r))park(errno);
    struct in_addr expected;if(inet_pton(AF_INET,canary_device_ip,&expected)!=1)park(EINVAL);
    if(((struct sockaddr_in*)&r.ifr_addr)->sin_addr.s_addr!=expected.s_addr)park(EINVAL);
    if(ioctl(fd,SIOCGIFFLAGS,&r)||!(r.ifr_flags&IFF_UP))park(EINVAL);
    if(close(fd))park(errno);
    char actual[128];size_t size;
    if(read_small("/config/usb_gadget/g0q-canary/UDC",actual,sizeof(actual),&size))park(EIO);
    if(size!=strlen(canary_udc)+1||memcmp(actual,canary_udc,size-1)||actual[size-1]!='\n')park(EINVAL);
    dprintf(2,"USB_FIXTURE_AFTER_BIND_NETDEV_ADDRESS_UP_PASS\n");
    park(0);
}
