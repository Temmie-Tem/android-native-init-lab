/* Read a first-bind snapshot from the selected fresh kernel. No SCM calls. */
#include <sys/stat.h>

#if !defined(CANARY_H0_VM) || !defined(CANARY_DEBIAN_RAM)
#error "SCM USB observation requires the H0 Debian RAM profile"
#endif
_Static_assert(G0Q_BODY_SIZE == 356U, "SCM readout requires a 356-byte signed body");

/* The model has its own wire domain and cannot represent the board device. */
#ifdef SCM_USB_LIFECYCLE_MODEL
#define SCM_PLATFORM_NAME "firmware:scm-model"
#define SCM_OF_NODE "/sys/firmware/devicetree/base/firmware/scm-model"
#define SCM_DRIVER "/sys/bus/platform/drivers/vm_scm_lifecycle"
#define SCM_COMPAT "lab,scm-lifecycle"
#else
#define SCM_PLATFORM_NAME "firmware:scm"
#define SCM_OF_NODE "/sys/firmware/devicetree/base/firmware/scm"
#define SCM_DRIVER "/sys/bus/platform/drivers/qcom_scm"
#define SCM_COMPAT "qcom,scm-sm8450\0qcom,scm"
#endif
#define SCM_DEVICE "/sys/bus/platform/devices/" SCM_PLATFORM_NAME

enum scm_usb_state {
    SCM_INDETERMINATE = 0,
    SCM_UNBOUND = 1,
    SCM_BOUND = 2
};

struct scm_binding_sample {
    dev_t device;
    ino_t inode;
    int driver;
    int waiting_attribute;
};

static int scm_capture(struct scm_binding_sample *sample)
{
    char path[PATH_MAX];
    struct stat st;
    if (!realpath(SCM_DEVICE "/of_node", path) || strcmp(path, SCM_OF_NODE) ||
        stat(SCM_DEVICE, &st))
        return -1;
    sample->device = st.st_dev;
    sample->inode = st.st_ino;

    const char expected[] = SCM_COMPAT;
    char compat[sizeof(expected) + 1];
    size_t length;
    if (read_small(SCM_OF_NODE "/compatible", compat, sizeof(compat), &length) ||
        length != sizeof(expected) || memcmp(compat, expected, length))
        return -1;

    if (lstat(SCM_DEVICE "/driver", &st)) {
        if (errno != ENOENT)
            return -1;
        sample->driver = 0;
    } else {
        if (!S_ISLNK(st.st_mode) || !realpath(SCM_DEVICE "/driver", path) ||
            strcmp(path, SCM_DRIVER) || stat(SCM_DRIVER "/" SCM_PLATFORM_NAME, &st) ||
            st.st_dev != sample->device || st.st_ino != sample->inode)
            return -1;
        sample->driver = 1;
    }
    if (lstat(SCM_DEVICE "/waiting_for_supplier", &st)) {
        if (errno != ENOENT)
            return -1;
        sample->waiting_attribute = 0;
    } else {
        if (!S_ISREG(st.st_mode))
            return -1;
        sample->waiting_attribute = 1;
    }
    return 0;
}

static enum scm_usb_state scm_observe(void)
{
    struct scm_binding_sample before, after;
    if (scm_capture(&before) || scm_capture(&after) ||
        before.device != after.device || before.inode != after.inode ||
        before.driver != after.driver ||
        before.waiting_attribute != after.waiting_attribute)
        return SCM_INDETERMINATE;
    if (after.driver && !after.waiting_attribute)
        return SCM_BOUND;
    if (!after.driver && after.waiting_attribute)
        return SCM_UNBOUND;
    return SCM_INDETERMINATE;
}
