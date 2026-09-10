/* Short-lived fixed read-only mode. No DRM operation or file-content census. */
#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/statvfs.h>
#include <sys/vfs.h>
#include <time.h>
#include <unistd.h>
#include <linux/magic.h>

struct ms_file {const char *name;uint64_t size;unsigned mode;};
static const struct ms_file ms_files[]={MS_MANIFEST_ROWS};
_Static_assert(sizeof(ms_files)/sizeof(ms_files[0])==MS_MANIFEST_COUNT,"metadata manifest count");
struct ms_section {char data[1024];size_t used,limit;int bad;};
struct ms_packet {char data[4096];size_t used;};
static void ms_add(struct ms_section *s,const char *format,...) {
    if(s->bad)return;
    va_list args;va_start(args,format);
    int n=vsnprintf(s->data+s->used,s->limit-s->used,format,args);va_end(args);
    if(n<0||(size_t)n>=s->limit-s->used){s->bad=1;return;}
    s->used+=(size_t)n;
}
static int ms_section_end(struct ms_packet *p,struct ms_section *s,const char *label) {
    if(s->bad){s->used=0;s->bad=0;ms_add(s,"%s status=unavailable error=%d\n",label,EOVERFLOW);}
    if(s->bad||s->used>sizeof(p->data)-p->used)return -1;
    memcpy(p->data+p->used,s->data,s->used);p->used+=s->used;return 0;
}
static int ms_uint(const char *s,uint64_t *out) {
    if(!*s)return 0;
    uint64_t n=0;
    for(;*s;s++){if(*s<'0'||*s>'9'||n>(UINT64_MAX-(unsigned)(*s-'0'))/10U)return 0;n=n*10U+(unsigned)(*s-'0');}
    *out=n;return 1;
}
static int ms_mul(uint64_t a,uint64_t b,uint64_t *out) {
    if(b&&a>UINT64_MAX/b)return 0;
    *out=a*b;return 1;
}
static int ms_clock(uint64_t *out) {
    struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t))return errno;
    if(t.tv_sec<0||t.tv_nsec<0||t.tv_nsec>=1000000000L||
       (uint64_t)t.tv_sec>(UINT64_MAX-(uint64_t)t.tv_nsec/1000000U)/1000U)return ERANGE;
    *out=(uint64_t)t.tv_sec*1000U+(uint64_t)t.tv_nsec/1000000U;return 0;
}
static int ms_proc_open(const char *path) {
    int f=open(path,O_RDONLY|O_CLOEXEC|O_NOFOLLOW|O_NONBLOCK);if(f<0)return -errno;
    struct stat st;struct statfs fs;int e=0;
    if(fstat(f,&st)||fstatfs(f,&fs))e=errno;
    else if(!S_ISREG(st.st_mode)||fs.f_type!=PROC_SUPER_MAGIC)e=ENODEV;
    if(e){close(f);return -e;}return f;
}
/* Caller provides limit+1 bytes. Parse only after a complete EOF observation. */
static int ms_text(const char *path,char *out,size_t limit,size_t *used) {
    *used=0;int f=ms_proc_open(path);if(f<0)return -f;int e=0;
    for(;;){
        ssize_t n=read(f,out+*used,limit+1U-*used);
        if(n<0){if(errno==EINTR)continue;e=errno;break;}
        if(!n)break;
        *used+=(size_t)n;if(*used>limit){e=EFBIG;break;}
    }
    if(close(f)&&!e)e=errno;
    if(!e&&memchr(out,0,*used))e=EILSEQ;
    if(!e)out[*used]=0;
    return e;
}
static void ms_meminfo(struct ms_section *s) {
    static const char *keys[]={"MemTotal","MemAvailable","MemFree","RbinTotal","RbinAlloced",
        "RbinFree","RbinCached","RbinPool","CmaTotal","CmaFree","Shmem","Cached","Slab",
        "SReclaimable","SUnreclaim","KernelStack","PageTables","Percpu","SwapTotal","SwapFree",
        "HugepagePool","AnonPages"};
    enum {COUNT=sizeof(keys)/sizeof(keys[0])};
    uint64_t values[COUNT]={0};unsigned char seen[COUNT]={0};unsigned count=0;
    char text[8193];size_t size=0;int e=ms_text("/proc/meminfo",text,8192,&size);
    if(!e){
        char *save=NULL;
        for(char *line=strtok_r(text,"\n",&save);line;line=strtok_r(NULL,"\n",&save)) {
            char *colon=strchr(line,':');if(!colon)continue;*colon=0;
            for(unsigned i=0;i<COUNT;i++)if(!strcmp(line,keys[i])){
                char *value=colon+1;while(*value==' '||*value=='\t')value++;
                char *end=value;while(*end>='0'&&*end<='9')end++;
                if(*end!=' '&&*end!='\t'){e=EINVAL;break;}
                *end++=0;while(*end==' '||*end=='\t')end++;
                if(seen[i]||strcmp(end,"kB")||!ms_uint(value,&values[i])){e=EINVAL;break;}
                seen[i]=1;count++;
            }
            if(e)break;
        }
    }
    if(e){ms_add(s,"MEM status=unavailable error=%d read_bytes=%zu\n",e,size);return;}
    ms_add(s,"MEM status=%s unit=KiB read_bytes=%zu",count==COUNT?"ok":"partial",size);
    for(unsigned i=0;i<COUNT;i++){
        if(seen[i])ms_add(s," %s=%" PRIu64,keys[i],values[i]);
        else ms_add(s," %s=NA",keys[i]);
    }
    ms_add(s,"\n");
}
static int ms_token_safe(const char *s) {
    size_t n=strlen(s);if(!n||n>80)return 0;
    for(size_t i=0;i<n;i++)if(!isalnum((unsigned char)s[i])&&!strchr("_.,:+*=-",s[i]))return 0;
    return 1;
}
static void ms_cmdline(struct ms_section *s) {
    static const char *keys[]={"kasan","kasan.stacktrace","kfence.sample_interval","page_owner",
        "page_pinner","slub_debug","stack_depot_disable"};
    unsigned occurrences[sizeof(keys)/sizeof(keys[0])]={0};
    char text[8193];size_t size=0;int e=ms_text("/proc/cmdline",text,8192,&size);
    if(e){ms_add(s,"CMD status=unavailable error=%d read_bytes=%zu\n",e,size);return;}
    int root=0;const char *fstype="absent";unsigned index=0;char *save=NULL;
    ms_add(s,"CMD status=ok read_bytes=%zu",size);
    for(char *t=strtok_r(text," \t\r\n",&save);t;t=strtok_r(NULL," \t\r\n",&save)) {
        char *eq=strchr(t,'=');size_t n=eq?(size_t)(eq-t):strlen(t);
        if(n==4&&!memcmp(t,"root",4)){root=1;continue;}
        if(n==10&&!memcmp(t,"rootfstype",10)){
            fstype=eq&&!strcmp(eq+1,"tmpfs")?"tmpfs":eq&&!strcmp(eq+1,"ramfs")?"ramfs":"other";continue;
        }
        for(unsigned i=0;i<sizeof(keys)/sizeof(keys[0]);i++)if(strlen(keys[i])==n&&!memcmp(t,keys[i],n)){
            occurrences[i]++;
            if(!ms_token_safe(t)){s->bad=1;return;}
            ms_add(s," arg%u=%s",index++,t);
        }
    }
    ms_add(s," root_present=%d rootfstype=%s",root,fstype);
    for(unsigned i=0;i<sizeof(keys)/sizeof(keys[0]);i++)ms_add(s," %s_count=%u",keys[i],occurrences[i]);
    ms_add(s,"\n");
}
static int ms_directory(int parent,const char *name) {
    int f=parent<0?open(name,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC):
        openat(parent,name,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    return f<0?-errno:f;
}
static int ms_ram(int f,struct stat *st,struct statfs *fs) {
    if(f<0)return -f;
    if(fstat(f,st)||fstatfs(f,fs))return errno;
    if(!S_ISDIR(st->st_mode)||(fs->f_type!=TMPFS_MAGIC&&fs->f_type!=RAMFS_MAGIC))return ENODEV;
    return 0;
}
static void ms_fs(struct ms_section *s,const char *label,int f) {
    struct stat st;struct statfs fs;int e=ms_ram(f,&st,&fs);
    if(e){ms_add(s,"FS name=%s status=unavailable error=%d\n",label,e);return;}
    if(fs.f_type==RAMFS_MAGIC){ms_add(s,"FS name=%s status=ok type=ramfs accounting=unavailable\n",label);return;}
    struct statvfs v;
    if(fstatvfs(f,&v)){ms_add(s,"FS name=%s status=unavailable error=%d\n",label,errno);return;}
    uint64_t unit=v.f_frsize?v.f_frsize:v.f_bsize,total,free_bytes,avail;
    if(!unit||v.f_bfree>v.f_blocks||v.f_bavail>v.f_bfree||
       !ms_mul(v.f_blocks,unit,&total)||!ms_mul(v.f_bfree,unit,&free_bytes)||!ms_mul(v.f_bavail,unit,&avail)){
        ms_add(s,"FS name=%s status=unavailable error=%d\n",label,EOVERFLOW);return;
    }
    ms_add(s,"FS name=%s status=ok type=tmpfs total_bytes=%" PRIu64 " free_bytes=%" PRIu64
        " avail_bytes=%" PRIu64 "\n",label,total,free_bytes,avail);
}
static void ms_file_totals(struct ms_section *s,int root,int modules) {
    struct stat root_st,dir_st;struct statfs root_fs,dir_fs;
    int e=ms_ram(root,&root_st,&root_fs);if(!e)e=ms_ram(modules,&dir_st,&dir_fs);
    if(!e&&root_st.st_dev!=dir_st.st_dev)e=EXDEV;
    if(e){ms_add(s,"FILES status=unavailable error=%d expected=%u\n",e,MS_MANIFEST_COUNT);return;}
    unsigned present=0,valid=0,missing=0,mismatch=0,errors=0;uint64_t logical=0,allocated=0;
    for(unsigned i=0;i<MS_MANIFEST_COUNT;i++){
        struct stat st;
        if(fstatat(modules,ms_files[i].name,&st,AT_SYMLINK_NOFOLLOW|AT_NO_AUTOMOUNT)){
            if(errno==ENOENT)missing++;else errors++;continue;
        }
        present++;
        if(!S_ISREG(st.st_mode)||st.st_dev!=dir_st.st_dev||st.st_uid||st.st_gid||st.st_nlink!=1||
           (st.st_mode&07777)!=ms_files[i].mode||st.st_size<0||(uint64_t)st.st_size!=ms_files[i].size||st.st_blocks<0){mismatch++;continue;}
        uint64_t blocks;if(!ms_mul((uint64_t)st.st_blocks,512,&blocks)||
            logical>UINT64_MAX-(uint64_t)st.st_size||allocated>UINT64_MAX-blocks){e=EOVERFLOW;break;}
        logical+=(uint64_t)st.st_size;allocated+=blocks;valid++;
    }
    if(e){ms_add(s,"FILES status=unavailable error=%d expected=%u\n",e,MS_MANIFEST_COUNT);return;}
    ms_add(s,"FILES status=%s expected=%u present=%u metadata_match=%u missing=%u mismatch=%u errors=%u"
        " logical_bytes=%" PRIu64 " allocated_metadata_bytes=%" PRIu64 " content_verified=0\n",
        valid==MS_MANIFEST_COUNT?"ok":"partial",MS_MANIFEST_COUNT,present,valid,missing,mismatch,errors,logical,allocated);
}
struct ms_cache {char name[65];uint64_t nominal,objects,pages,slabs;};
struct ms_slab {struct ms_cache top[5];unsigned top_count,records,valid,bad;uint64_t seen[1024];};
static int ms_cache_name(const char *s) {
    if(!*s||strlen(s)>64)return 0;
    for(;*s;s++)if(!isalnum((unsigned char)*s)&&!strchr("_.:-()/",*s))return 0;
    return 1;
}
static int ms_slab_row(struct ms_slab *s,char *line,uint64_t page_size) {
    if(++s->records>1024)return E2BIG;
    char *tok[17],*save=NULL;unsigned n=0;
    for(char *p=strtok_r(line," \t",&save);p&&n<17;p=strtok_r(NULL," \t",&save))tok[n++]=p;
    if(n!=16||strcmp(tok[6],":")||strcmp(tok[7],"tunables")||strcmp(tok[11],":")||
       strcmp(tok[12],"slabdata")||!ms_cache_name(tok[0])){s->bad++;return 0;}
    uint64_t v[16]={0};
    for(unsigned i=1;i<16;i++)if(i!=6&&i!=7&&i!=11&&i!=12&&!ms_uint(tok[i],&v[i])){s->bad++;return 0;}
    if(v[1]>v[2]||v[13]>v[14]||!v[3]||!v[4]||!v[5]){s->bad++;return 0;}
    uint64_t hash=1469598103934665603ULL;
    for(const unsigned char *p=(const unsigned char *)tok[0];*p;p++){hash^=*p;hash*=1099511628211ULL;}
    for(unsigned i=0;i<s->valid;i++)if(s->seen[i]==hash){s->bad++;return 0;}
    struct ms_cache c={0};strcpy(c.name,tok[0]);c.pages=v[5];c.slabs=v[14];uint64_t pages;
    if(!ms_mul(c.slabs,c.pages,&pages)||!ms_mul(pages,page_size,&c.nominal)||!ms_mul(v[2],v[3],&c.objects)||
       c.objects>c.nominal){s->bad++;return 0;}
    s->seen[s->valid++]=hash;
    unsigned i=0;while(i<s->top_count&&(s->top[i].nominal>c.nominal||
        (s->top[i].nominal==c.nominal&&strcmp(s->top[i].name,c.name)<0)))i++;
    if(i<5){unsigned end=s->top_count<5?s->top_count++:4;for(unsigned j=end;j>i;j--)s->top[j]=s->top[j-1];s->top[i]=c;}
    return 0;
}
static void ms_slabs(struct ms_section *out) {
    int f=ms_proc_open("/proc/slabinfo");if(f<0){ms_add(out,"SLAB status=unavailable error=%d\n",-f);return;}
    long page=sysconf(_SC_PAGESIZE);int e=page>0?0:EINVAL,header=0,too_long=0;
    struct ms_slab s={0};char buffer[1024],line[513];size_t bytes=0,used=0;
    while(!e){
        size_t want=262145U-bytes;if(want>sizeof(buffer))want=sizeof(buffer);
        ssize_t n=read(f,buffer,want);
        if(n<0){if(errno==EINTR)continue;e=errno;break;}if(!n)break;
        bytes+=(size_t)n;if(bytes>262144U){e=EFBIG;break;}
        for(ssize_t i=0;i<n;i++){
            unsigned char c=(unsigned char)buffer[i];if(!c){e=EILSEQ;break;}
            if(c=='\n'){
                if(too_long){s.bad++;too_long=0;used=0;continue;}
                line[used]=0;used=0;
                if(!header){if(strcmp(line,"slabinfo - version: 2.1")){e=EINVAL;break;}header=1;continue;}
                if(line[0]=='#'||!line[0])continue;
                e=ms_slab_row(&s,line,(uint64_t)page);if(e)break;
            }else if(!too_long){if(used==512)too_long=1;else line[used++]=(char)c;}
        }
    }
    if(close(f)&&!e)e=errno;
    if(!header&&!e)e=EINVAL;
    if(used||too_long)s.bad++;
    ms_add(out,"SLAB status=%s error=%d read_bytes=%zu records=%u parsed=%u bad=%u page_size=%ld estimate=nominal\n",
        e||s.bad?"partial":"ok",e,bytes,s.records,s.valid,s.bad,page);
    for(unsigned i=0;i<s.top_count;i++)ms_add(out,"CACHE name=%s pages=%" PRIu64 " slabs=%" PRIu64
        " nominal_bytes=%" PRIu64 " object_bytes=%" PRIu64 "\n",s.top[i].name,s.top[i].pages,s.top[i].slabs,s.top[i].nominal,s.top[i].objects);
}
static int ms_gem_line(char *line,uint64_t values[7]) {
    static const char *keys[]={"seq=","ms=","alloc=","retired=","live=","peak=","bytes="};
    char *save=NULL,*t=strtok_r(line," ",&save);if(!t||strcmp(t,"HUD_MEM"))return 0;
    for(unsigned i=0;i<7;i++){
        t=strtok_r(NULL," ",&save);size_t n=strlen(keys[i]);
        if(!t||strncmp(t,keys[i],n)||!ms_uint(t+n,&values[i]))return 0;
    }
    if(strtok_r(NULL," ",&save)||!values[0]||values[0]>UINT32_MAX||!values[2]||values[2]>601||values[0]<values[2]||
       values[3]+1!=values[2]||values[4]!=1||values[5]!=(values[2]==1?1U:2U)||values[6]!=MS_GEM_BUFFER_BYTES)return 0;
    return 1;
}
static void ms_gem(struct ms_section *s,int work) {
    struct stat ds;struct statfs fs;int e=ms_ram(work,&ds,&fs),f=-1;
    if(!e){f=openat(work,"hud.log",O_RDONLY|O_NOFOLLOW|O_CLOEXEC|O_NONBLOCK);if(f<0)e=errno;}
    struct stat st;
    if(!e&&(fstat(f,&st)))e=errno;
    if(!e&&(!S_ISREG(st.st_mode)||st.st_uid||st.st_nlink!=1||(st.st_mode&0777)!=0400||st.st_dev!=ds.st_dev||st.st_size<0))e=EINVAL;
    char data[16385];size_t got=0;off_t offset=0;uint64_t value[7]={0};int found=0,bad=0;
    if(!e){
        offset=st.st_size>16384?st.st_size-16384:0;size_t wanted=(size_t)(st.st_size-offset);
        while(got<wanted){ssize_t n=pread(f,data+got,wanted-got,offset+(off_t)got);
            if(n<0){if(errno==EINTR)continue;e=errno;break;}if(!n){e=EIO;break;}got+=(size_t)n;}
        data[got]=0;if(memchr(data,0,got))e=EILSEQ;
        if(!e){
            char *p=data,*end;
            if(offset){end=strchr(p,'\n');p=end?end+1:data+got;}
            while((end=strchr(p,'\n'))){*end=0;
                if(!strncmp(p,"HUD_MEM ",8)){
                    uint64_t next[7];if(ms_gem_line(p,next)){
                        if(found&&(next[0]<=value[0]||next[1]<value[1]))bad=1;
                        memcpy(value,next,sizeof(value));found=1;
                    }else bad=1;
                }p=end+1;
            }
        }
    }
    if(f>=0&&close(f)&&!e)e=errno;
    uint64_t now=0;int clock_error=ms_clock(&now);
    if(e||clock_error||!found||bad||value[1]>now){ms_add(s,"GEM status=unavailable error=%d\n",e?e:clock_error?clock_error:ENODATA);return;}
    ms_add(s,"GEM status=%s source=renderer_last_retirement seq=%" PRIu64 " age_ms=%" PRIu64
        " allocations=%" PRIu64 " retired=%" PRIu64 " live_handles=%" PRIu64 " peak_handles=%" PRIu64
        " requested_bytes=%" PRIu64 " physical_bytes=NA\n",now-value[1]>5000?"stale":"ok",value[0],now-value[1],value[2],value[3],value[4],value[5],value[6]);
}
static int memory_snapshot(const char *phase) {
    if(strcmp(phase,"early")&&strcmp(phase,"late"))return 126;
    uint64_t start=0,end=0;int clock_error=ms_clock(&start);struct ms_packet packet={0};
    struct ms_section s={.limit=128};
    ms_add(&s,"S22MEM1 BEGIN phase=%s start_ms=%" PRIu64 " clock_error=%d\n",phase,start,clock_error);
    if(ms_section_end(&packet,&s,"BEGIN"))return 125;
    s=(struct ms_section){.limit=1024};ms_meminfo(&s);if(ms_section_end(&packet,&s,"MEM"))return 125;
    s=(struct ms_section){.limit=512};ms_cmdline(&s);if(ms_section_end(&packet,&s,"CMD"))return 125;
    int root=ms_directory(-1,"/"),lib=root<0?root:ms_directory(root,"lib");
    int modules=lib<0?lib:ms_directory(lib,"modules"),work=root<0?root:ms_directory(root,"s22-root-work");
    if(lib>=0)close(lib);
    s=(struct ms_section){.limit=512};ms_fs(&s,"root",root);ms_fs(&s,"modules",modules);ms_fs(&s,"work",work);
    if(ms_section_end(&packet,&s,"FS"))return 125;
    s=(struct ms_section){.limit=512};ms_file_totals(&s,root,modules);if(ms_section_end(&packet,&s,"FILES"))return 125;
    s=(struct ms_section){.limit=1024};ms_slabs(&s);if(ms_section_end(&packet,&s,"SLAB"))return 125;
    s=(struct ms_section){.limit=256};ms_gem(&s,work);if(ms_section_end(&packet,&s,"GEM"))return 125;
    for(unsigned i=0;i<3;i++){int f=i==0?root:i==1?modules:work;if(f>=0)close(f);}
    int end_error=ms_clock(&end);
    s=(struct ms_section){.limit=128};ms_add(&s,"S22MEM1 END phase=%s end_ms=%" PRIu64 " clock_error=%d\n",phase,end,end_error);
    if(ms_section_end(&packet,&s,"END"))return 125;
    size_t sent=0;while(sent<packet.used){ssize_t n=write(STDOUT_FILENO,packet.data+sent,packet.used-sent);
        if(n<0&&errno==EINTR)continue;
        if(n<=0)return 125;
        sent+=(size_t)n;}
    return 0;
}
