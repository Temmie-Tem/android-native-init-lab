/* Shared RAM dispatcher and nonblocking channel. The selecting owner defines
 * its finite budget/lifetime and authenticated record stage. */
#include <sys/statvfs.h>
static void ap_channel_close(void) {
    if(ap_receive>=0 && (!ap.script_done || ap.script_open))ap.flags|=AP_CHANNEL;
    if(ap_receive>=0 && close(ap_receive))ap.flags|=AP_IO;
    if(ap_send>=0 && close(ap_send))ap.flags|=AP_IO;
    ap_receive=ap_send=-1;
}
static int ap_dispatcher_prepare(void) {
    int fd=fs1_pin_file("/usr/lib/init/rc",ap_rc_size,ap_rc_sha,true);if(fd<0)return ap_error();
    int error=ap_close(fd,0);if(error)return error;
    fd=fs1_pin_file("/usr/lib/init/rcS",ap_rcs_size,ap_rcs_sha,true);if(fd<0)return ap_error();
    if((error=ap_close(fd,0)))return error;
    if(ap_expired())return ETIMEDOUT;
    fd=open(AP_DISPATCHER,O_RDWR|O_CREAT|O_EXCL|O_CLOEXEC|O_NOFOLLOW,0500);if(fd<0)return ap_error();
    struct statfs fs;struct statvfs vfs;uint8_t check[sizeof(ap_dispatcher)];
    error=fstatfs(fd,&fs) || fs.f_type!=AP_TMPFS || fstatvfs(fd,&vfs) ? EIO : 0;
    if(!error && vfs.f_flag&ST_NOEXEC)error=EACCES;
    if(!error && (write(fd,ap_dispatcher,sizeof(ap_dispatcher))!=(ssize_t)sizeof(ap_dispatcher) ||
        pread(fd,check,sizeof(check),0)!=(ssize_t)sizeof(check) || memcmp(check,ap_dispatcher,sizeof(check))))error=EIO;
    if((error=ap_close(fd,error)))return error;
    int sockets[2];if(socketpair(AF_UNIX,SOCK_DGRAM|SOCK_NONBLOCK|SOCK_CLOEXEC,0,sockets))return ap_error();
    /* fd3 remains absent in the parent; mandatory reporting checks rely on it. */
    ap_receive=fcntl(sockets[0],F_DUPFD_CLOEXEC,10);ap_send=fcntl(sockets[1],F_DUPFD_CLOEXEC,10);
    error=ap_receive<0 || ap_send<0 ? ap_error() : 0;
    error=ap_close(sockets[0],error);error=ap_close(sockets[1],error);
    if(error)ap_channel_close();
    return error;
}
static int ap_child_channel(void) {
    if(ap_send<0)return 0;
    int error=dup3(ap_send,3,0)<0 ? ap_error() : 0;
    if(error)return -error;
    int type=0; socklen_t size=sizeof(type);
    int flags=fcntl(3,F_GETFL);
    if(getsockopt(3,SOL_SOCKET,SO_TYPE,&type,&size) || type!=SOCK_DGRAM ||
       flags<0 || !(flags&O_NONBLOCK) || fcntl(3,F_GETFD)!=0)return -EPROTO;
    return 1;
}
static void ap_parent_fork(void) {
    if(ap_send<0)return;
    ap_begin(0);
    if(close(ap_send))ap.flags|=AP_IO;
    ap_send=-1;ap_charge();
}
static void ap_packets(void) {
    if(ap_receive<0)return;
    for(unsigned n=0;n<8 && !ap_expired();++n) {
        char packet[80];struct iovec iov={packet,sizeof(packet)-1};struct msghdr message={.msg_iov=&iov,.msg_iovlen=1};
        ssize_t got=recvmsg(ap_receive,&message,MSG_DONTWAIT);
        if(got<0){if(errno!=EAGAIN)ap.flags|=AP_CHANNEL;break;}
        if(!got || message.msg_flags&MSG_TRUNC || memchr(packet,0,(size_t)got)){ap.flags|=AP_CHANNEL;break;}
        packet[got]=0;struct ap_packet decoded;
        if(ap_packet_parse(packet,&decoded) || decoded.sequence!=ap.packet_sequence+1 ||
           ap.packets>=AP_SCRIPT_RECORD_CAP || ap.script_done ||
           (!ap.packet_sequence && decoded.kind!='D')){ap.flags|=AP_CHANNEL;break;}
        if(decoded.kind=='D') {
            if(ap.packet_sequence){ap.flags|=AP_CHANNEL;break;}
        } else if(decoded.kind=='B') {
            if(ap.script_open || decoded.id<=ap.script_id){ap.flags|=AP_CHANNEL;break;}
            ap.script_open=1;ap.script_id=decoded.id;
        } else if(decoded.kind=='E') {
            if(!ap.script_open || decoded.id!=ap.script_id){ap.flags|=AP_CHANNEL;break;}ap.script_open=0;
        } else {
            if(ap.script_open){ap.flags|=AP_CHANNEL;break;}ap.script_done=1;
        }
        ap.packet_sequence=decoded.sequence;++ap.packets;
        ap_record(AP_SCRIPT_STAGE,decoded.result,0,decoded.sequence,decoded.id,(unsigned)decoded.kind,0);
    }
    if(ap.flags&AP_CHANNEL)ap_channel_close();
}
