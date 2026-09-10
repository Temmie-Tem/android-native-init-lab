/* Optional successful-lifecycle observations on the existing HUD log pipe. */
static unsigned hud_mem_alloc,hud_mem_retired,hud_mem_live,hud_mem_peak,hud_mem_lines,hud_mem_disabled;
static void hud_mem_allocated(void) {
    ++hud_mem_alloc;++hud_mem_live;if(hud_mem_live>hud_mem_peak)hud_mem_peak=hud_mem_live;
    if(hud_mem_alloc>601||hud_mem_live>2)hud_mem_disabled=1;
}
static void hud_mem_retired_one(void) {
    if(!hud_mem_live){hud_mem_disabled=1;return;}
    --hud_mem_live;++hud_mem_retired;
}
static void hud_mem_record(uint32_t sequence) {
    if(hud_mem_disabled||hud_mem_lines>=32||hud_mem_live!=1)return;
    struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t)||t.tv_sec<0||t.tv_nsec<0||t.tv_nsec>=1000000000L)return;
    if((uint64_t)t.tv_sec>(UINT64_MAX-(uint64_t)t.tv_nsec/1000000U)/1000U)return;
    uint64_t ms=(uint64_t)t.tv_sec*1000U+(uint64_t)t.tv_nsec/1000000U;
    char text[128];int n=snprintf(text,sizeof(text),"HUD_MEM seq=%u ms=%" PRIu64
        " alloc=%u retired=%u live=%u peak=%u bytes=%zu\n",sequence,ms,hud_mem_alloc,hud_mem_retired,hud_mem_live,hud_mem_peak,BYTES);
    if(n<=0||(size_t)n>=sizeof(text)){hud_mem_disabled=1;return;}
    ++hud_mem_lines;
    if(write(STDERR_FILENO,text,(size_t)n)!=n)hud_mem_disabled=1;
}
