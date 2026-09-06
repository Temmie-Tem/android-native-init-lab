/* Cached ioctl results only: no additional kernel operation on failure.
 * At most 16 mode rows and 31 driver-name bytes; never a kernel-log read. */
static struct {
    unsigned long ioctl_op;
    const char *ioctl_stage, *property_name;
    uint32_t property_object, resources_crtcs, resources_connectors;
    uint32_t connector, crtc, plane, mode_count, lowest_hz, matches;
    size_t driver_length;
    unsigned char driver_name[31];
    struct drm_mode_modeinfo modes[16];
} display_diag;

static void display_failure_context(void) {
    int saved = errno;
    fprintf(stderr, "DISPLAY_DIAG ioctl=%lu call=%s object=%u property=%s "
        "crtcs=%u connectors=%u connector=%u crtc=%u plane=%u "
        "mode_count=%u lowest_hz=%u matches=%u\n",
        display_diag.ioctl_op,
        display_diag.ioctl_stage ? display_diag.ioctl_stage : "none",
        display_diag.property_object,
        display_diag.property_name ? display_diag.property_name : "none",
        display_diag.resources_crtcs, display_diag.resources_connectors,
        display_diag.connector, display_diag.crtc, display_diag.plane,
        display_diag.mode_count, display_diag.lowest_hz, display_diag.matches);
    fprintf(stderr, "DISPLAY_DIAG driver_length=%zu driver_hex=", display_diag.driver_length);
    size_t n = display_diag.driver_length;
    if (n > sizeof(display_diag.driver_name)) n = sizeof(display_diag.driver_name);
    for (size_t i = 0; i < n; ++i) fprintf(stderr, "%02x", display_diag.driver_name[i]);
    fputc('\n', stderr);
    for (uint32_t i = 0; i < display_diag.mode_count && i < 16; ++i) {
        const struct drm_mode_modeinfo *m = &display_diag.modes[i];
        fprintf(stderr, "DISPLAY_DIAG mode=%u width=%u height=%u hz=%u clock=%u "
            "hs=%u he=%u htotal=%u hskew=%u vs=%u ve=%u vtotal=%u vscan=%u "
            "flags=%u type=%u name_hex=", i, m->hdisplay,
            m->vdisplay, m->vrefresh, m->clock, m->hsync_start, m->hsync_end,
            m->htotal, m->hskew, m->vsync_start, m->vsync_end, m->vtotal,
            m->vscan, m->flags, m->type);
        for (size_t j = 0; j < sizeof(m->name) && m->name[j]; ++j)
            fprintf(stderr, "%02x", (unsigned char)m->name[j]);
        fputc('\n', stderr);
    }
    errno = saved;
}
