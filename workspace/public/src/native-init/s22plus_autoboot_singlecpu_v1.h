/* Fixed read-only checks for the H0 single-CPU candidate. Driver software
 * state and survival do not prove that a hardware reset/pet succeeded. */
#ifndef S22_AUTOBOOT_SINGLECPU_V1_H
#define S22_AUTOBOOT_SINGLECPU_V1_H
#ifdef S22_AUTOBOOT_SINGLECPU
static int sc_cpu(void) {
    char text[32];
    int error=fs1_read_text("/sys/devices/system/cpu/online",text,sizeof(text));
    return error ? error : strcmp(text,"0\n") ? EPROTO : 0;
}
static int sc_valid(uint64_t value) {
    /* CPU-online mask 1 and driver-enabled bit 8. All other bits reserved.
     * This exact FYG8 module has no pet_time/user_pet_enabled sysfs files. */
    return value==257U;
}
static int sc_observe(uint64_t *value) {
    char disable[16];
    int error=sc_cpu();if(error)return error;
#ifdef S22_ROOT_INSPECT_VIRT_TEST
    /* The generic VM has no Samsung watchdog. Only its disable sysfs value
     * is modeled; online CPU state above/below is always the real kernel. */
    strcpy(disable,"0\n");
#else
    if((error=fs1_read_text("/sys/bus/platform/devices/hypervisor:qcom,gh-watchdog/disable",disable,sizeof(disable))))
        return error;
#endif
    if(strcmp(disable,"0\n"))return EPROTO;
    if((error=sc_cpu()))return error;
    *value=257U;return 0;
}
#else
static int sc_valid(uint64_t value){return value==0;}
#endif
#endif
