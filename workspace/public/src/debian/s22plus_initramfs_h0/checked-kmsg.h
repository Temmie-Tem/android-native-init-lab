/* Shared bounded exact ring readback, not post-return retention proof. */
#ifndef S22_CHECKED_KMSG_H
#define S22_CHECKED_KMSG_H
static int checked_kmsg(const char *line,int n) {
    int error=0;
    int reader=open("/dev/kmsg",O_RDONLY|O_NONBLOCK|O_NOFOLLOW|O_CLOEXEC);
    if(reader<0)return fs1_error();
    struct stat st;
    if(fstat(reader,&st) || !S_ISCHR(st.st_mode) || st.st_rdev!=makedev(1,11) ||
        st.st_uid || st.st_gid || (st.st_mode&07777)!=0600 || lseek(reader,0,SEEK_END)<0) {
        close(reader);return EPROTO;
    }
    int fd=open("/dev/kmsg",O_WRONLY|O_NONBLOCK|O_NOFOLLOW|O_CLOEXEC);
    if(fd<0){close(reader);return fs1_error();}
    if(fstat(fd,&st) || !S_ISCHR(st.st_mode) || st.st_rdev!=makedev(1,11) ||
        st.st_uid || st.st_gid || (st.st_mode&07777)!=0600)error=EPROTO;
    /* This kernel may return full length when dropping a write. Require exact
     * bounded ring readback; it still is not post-reboot retention proof. */
    if(!error && write(fd,line,(size_t)n)!=n)error=EIO;
    if(close(fd)&&!error)error=fs1_error();
    size_t total=0;bool found=false;struct timespec start,current;
    if(clock_gettime(CLOCK_BOOTTIME,&start))error=EIO;
    while(!error && !found && total<65536) {
        if(clock_gettime(CLOCK_BOOTTIME,&current)){error=EIO;break;}
        int64_t elapsed=(int64_t)(current.tv_sec-start.tv_sec)*1000000000LL+current.tv_nsec-start.tv_nsec;
        if(elapsed<0 || elapsed>=500000000LL){error=ETIMEDOUT;break;}
        char raw[2048];size_t available=65536-total;
        if(available>sizeof(raw))available=sizeof(raw);
        ssize_t amount=read(reader,raw,available);
        if(amount>0) {
            total+=(size_t)amount;
            char *body=memchr(raw,';',(size_t)amount);
            if(body && (size_t)(raw+amount-body-1)==(size_t)n-4 && !memcmp(body+1,line+4,(size_t)n-4))found=true;
        }else if(amount<0 && errno!=EAGAIN && errno!=EINTR){error=fs1_error();break;}
        else if(amount==0){error=EIO;break;}
        if(clock_gettime(CLOCK_BOOTTIME,&current)){error=EIO;break;}
        elapsed=(int64_t)(current.tv_sec-start.tv_sec)*1000000000LL+current.tv_nsec-start.tv_nsec;
        if(elapsed<0 || elapsed>=500000000LL){error=ETIMEDOUT;break;}
        if(!found) {struct timespec delay={0,1000000};if(nanosleep(&delay,NULL))error=fs1_error();}
    }
    if(!error && !found)error=ENOMSG;
    if(close(reader)&&!error)error=fs1_error();
    return error;
}
#endif
