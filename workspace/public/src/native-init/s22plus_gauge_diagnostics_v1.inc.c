/* Retain a bounded first/changed failure or success record. Diagnostics do not
 * change measurement validity, restart a child, or perform additional I2C. */
enum gauge_read_failure {GAUGE_READ_OK,GAUGE_READ_OPEN,GAUGE_READ_FS,
    GAUGE_READ_IO,GAUGE_READ_OVERFLOW,GAUGE_READ_NUL,GAUGE_READ_CLOSE};
struct gauge_read_result {unsigned failure;int error;size_t size;};
static struct gauge_read_result gauge_read_text(const char *path,char *text,size_t capacity) {
    struct gauge_read_result r={0};
    int f=open(path,O_RDONLY|O_CLOEXEC|O_NOFOLLOW|O_NONBLOCK);
    if(f<0){r.failure=GAUGE_READ_OPEN;r.error=errno;text[0]=0;return r;}
    struct statfs fs;
    if(fstatfs(f,&fs)){r.failure=GAUGE_READ_FS;r.error=errno;goto done;}
    if(fs.f_type!=0x62656572L){r.failure=GAUGE_READ_FS;goto done;}
    for(;;) {
        char extra;
        ssize_t n=read(f,r.size<capacity-1?text+r.size:&extra,
            r.size<capacity-1?capacity-1-r.size:1);
        if(n<0){r.failure=GAUGE_READ_IO;r.error=errno;break;}
        if(!n)break;
        if(r.size==capacity-1){r.failure=GAUGE_READ_OVERFLOW;break;}
        r.size+=(size_t)n;
    }
    if(!r.failure&&memchr(text,0,r.size))r.failure=GAUGE_READ_NUL;
done:
    text[r.size]=0;
    if(close(f)&&!r.failure){r.failure=GAUGE_READ_CLOSE;r.error=errno;}
    return r;
}
static unsigned gauge_diag_count,gauge_diag_last=UINT32_MAX;
static int gauge_diag_errno,gauge_diag_detail_errno;
static unsigned gauge_diag_detail_failure;
static char gauge_diag_detail[193];
static void gauge_diag_record(unsigned sample_sequence,unsigned reason,
        struct gauge_read_result sample,const char *raw) {
    /* Eight records of at most 1152 bytes fit within the existing 256 KiB log
     * beside the 601-frame bound. Sequence/raw-value changes alone do not log. */
    if(gauge_diag_count>=8)return;
    char detail[193];struct gauge_read_result d=gauge_read_text(
        "/sys/module/s22plus_max77705_telemetry/parameters/diagnostic",detail,sizeof(detail));
    char signature[193];memcpy(signature,detail,d.size+1);
    char *counter=strstr(signature," read_ret=");
    if(!counter)counter=strstr(signature," attempts=");
    if(counter)*counter=0;
    if(reason==gauge_diag_last&&sample.error==gauge_diag_errno&&
       d.failure==gauge_diag_detail_failure&&d.error==gauge_diag_detail_errno&&
       !strcmp(signature,gauge_diag_detail))return;
    gauge_diag_last=reason;gauge_diag_errno=sample.error;
    gauge_diag_detail_failure=d.failure;gauge_diag_detail_errno=d.error;
    memcpy(gauge_diag_detail,signature,strlen(signature)+1);gauge_diag_count++;
    char line[1152];int n=snprintf(line,sizeof(line),
        "GAUGE_DIAG seq=%u reason=%u read=%u errno=%d diag_read=%u diag_errno=%d raw_hex=",
        sample_sequence,reason,sample.failure,sample.error,d.failure,d.error);
    if(n<0||(size_t)n>=sizeof(line))return;
    size_t used=(size_t)n;
    const char hex[]="0123456789abcdef";
    for(size_t i=0;i<sample.size&&i<256;i++) {
        unsigned c=(unsigned char)raw[i];line[used++]=hex[c>>4];line[used++]=hex[c&15];
    }
    memcpy(line+used," diag_hex=",10);used+=10;
    for(size_t i=0;i<d.size&&i<192;i++) {
        unsigned c=(unsigned char)detail[i];line[used++]=hex[c>>4];line[used++]=hex[c&15];
    }
    line[used++]='\n';
    /* One sub-PIPE_BUF write to the existing nonblocking diagnostics pipe.
     * Backpressure may lose a diagnostic; it never blocks or retries control. */
    if(write(STDERR_FILENO,line,used)!=(ssize_t)used)return;
}
