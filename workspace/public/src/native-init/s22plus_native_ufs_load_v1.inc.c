/* Fixed stock-driver initialization after the existing E3/display providers.
 * The generated table is bound to the sealed FYG8 vendor ramdisk. No caller
 * chooses a module, parameter, block operation, key operation or retry.
 */
static void ufs1_prepare(void) {
    int flags=O_RDONLY|O_DIRECTORY|O_CLOEXEC|O_NOFOLLOW;
    int root=open("/",flags);if(root<0)fail("ufs-root-open");
    int lib=openat(root,"lib",flags);if(lib<0)fail("ufs-lib-open");
    int modules=openat(lib,"modules",flags);if(modules<0)fail("ufs-modules-open");
    if(close(lib)||close(root))fail("ufs-parent-close");
    for(unsigned i=0;i<sizeof(ufs1_modules)/sizeof(ufs1_modules[0]);i++) {
        const struct ufs1_module *m=&ufs1_modules[i];
        int fd=openat(modules,m->name,O_RDONLY|O_CLOEXEC|O_NOFOLLOW);
        if(fd<0)fail("ufs-module-open");
        struct stat st;if(fstat(fd,&st))fail("ufs-module-stat");
        require(S_ISREG(st.st_mode)&&st.st_nlink==1&&st.st_uid==0&&st.st_gid==0&&
            (st.st_mode&0777)==0644&&(uint64_t)st.st_size==m->size,"ufs-module-binding");
        printf("UFS_LOAD_BEGIN index=%u\n",i);fflush(stdout);
        if(syscall(SYS_finit_module,fd,"",0))fail("ufs-module-insertion");
        if(close(fd))fail("ufs-module-close");
        printf("UFS_LOAD_DONE index=%u\n",i);fflush(stdout);
    }
    if(close(modules))fail("ufs-modules-close");
    /* Successful insertion does not establish LU0 readiness or GPT recovery.
     * A separate fixed authenticated census must provide actual read evidence.
     */
}
