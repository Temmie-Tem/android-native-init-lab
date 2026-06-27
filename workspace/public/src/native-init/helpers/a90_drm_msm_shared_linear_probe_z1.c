// No-present DRM msm shared-linear allocation preflight for GPU Z1.

#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <unistd.h>

#include <drm/drm.h>
#include <drm/drm_fourcc.h>
#include <drm/drm_mode.h>
#include <drm/msm_drm.h>

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

#ifndef DRM_CLOEXEC
#define DRM_CLOEXEC O_CLOEXEC
#endif

#define Z1_WIDTH 960U
#define Z1_HEIGHT 720U
#define Z1_BPP 4U
#define Z1_STRIDE (Z1_WIDTH * Z1_BPP)
#define Z1_BYTES ((uint64_t)Z1_STRIDE * Z1_HEIGHT)

static int ioctl_retry(int fd, unsigned long request, void *arg) {
    int rc;

    do {
        rc = ioctl(fd, request, arg);
    } while (rc < 0 && errno == EINTR);
    return rc;
}

static int negative_errno(void) {
    int saved = errno;

    return saved > 0 ? -saved : -EIO;
}

static int read_trimmed(const char *path, char *out, size_t out_size) {
    FILE *fp;

    if (out_size == 0) {
        errno = EINVAL;
        return -1;
    }
    fp = fopen(path, "r");
    if (fp == NULL) {
        return -1;
    }
    if (fgets(out, (int)out_size, fp) == NULL) {
        fclose(fp);
        errno = EIO;
        return -1;
    }
    fclose(fp);
    out[strcspn(out, "\r\n")] = '\0';
    return 0;
}

static int ensure_card0_path(char *out, size_t out_size) {
    char dev_info[64];
    unsigned int major_num;
    unsigned int minor_num;
    struct stat st;

    if (snprintf(out, out_size, "/dev/dri/card0") >= (int)out_size) {
        errno = ENAMETOOLONG;
        return -1;
    }
    if (stat(out, &st) == 0 && S_ISCHR(st.st_mode)) {
        return 0;
    }
    if (read_trimmed("/sys/class/drm/card0/dev", dev_info, sizeof(dev_info)) < 0) {
        return -1;
    }
    if (sscanf(dev_info, "%u:%u", &major_num, &minor_num) != 2) {
        errno = EINVAL;
        return -1;
    }
    if (mkdir("/dev/dri", 0755) < 0 && errno != EEXIST) {
        return -1;
    }
    if (mknod(out, S_IFCHR | 0600, makedev(major_num, minor_num)) < 0 && errno != EEXIST) {
        return -1;
    }
    return 0;
}

static int open_card0(char *node_path, size_t node_path_size) {
    int fd;

    if (ensure_card0_path(node_path, node_path_size) < 0) {
        return -1;
    }
    fd = open(node_path, O_RDWR | O_CLOEXEC);
    if (fd < 0) {
        return -1;
    }
    return fd;
}

static int get_cap(int fd, uint64_t capability, uint64_t *value) {
    struct drm_get_cap cap;

    memset(&cap, 0, sizeof(cap));
    cap.capability = capability;
    if (ioctl_retry(fd, DRM_IOCTL_GET_CAP, &cap) < 0) {
        return negative_errno();
    }
    *value = cap.value;
    return 0;
}

static int msm_gem_info_u64(int fd, uint32_t handle, uint32_t info, uint64_t *value) {
    struct drm_msm_gem_info arg;

    memset(&arg, 0, sizeof(arg));
    arg.handle = handle;
    arg.info = info;
    if (ioctl_retry(fd, DRM_IOCTL_MSM_GEM_INFO, &arg) < 0) {
        return negative_errno();
    }
    *value = arg.value;
    return 0;
}

static int close_gem_handle(int fd, uint32_t handle) {
    struct drm_gem_close close_arg;

    if (handle == 0U) {
        return 0;
    }
    memset(&close_arg, 0, sizeof(close_arg));
    close_arg.handle = handle;
    if (ioctl_retry(fd, DRM_IOCTL_GEM_CLOSE, &close_arg) < 0) {
        return negative_errno();
    }
    return 0;
}

static uint32_t sample_word(const volatile uint32_t *words, uint32_t index) {
    return words[index];
}

int main(void) {
    char node_path[128];
    int fd = -1;
    uint64_t dumb = 0;
    uint64_t addfb2_modifiers = 0;
    uint64_t prime = 0;
    struct drm_msm_gem_new gem;
    uint32_t handle = 0;
    uint32_t imported_handle = 0;
    uint32_t fb_id = 0;
    int prime_fd = -1;
    void *map = MAP_FAILED;
    uint64_t offset = 0;
    uint64_t iova = 0;
    uint64_t flags = 0;
    int rc_offset;
    int rc_iova;
    int rc_flags;
    int rc_mmap = -ENOSYS;
    int rc_prime_export = -ENOSYS;
    int rc_prime_import = -ENOSYS;
    int rc_addfb2 = -ENOSYS;
    int rc_rmfb = 0;
    int rc_close_import = 0;
    int rc_close_handle = 0;
    int rc;

    printf("probe.version=1\n");
    printf("probe.scope=z1-drm-msm-shared-linear-allocation-preflight\n");
    printf("probe.target.width=%u height=%u stride=%u bytes=%llu format=XB24 flags=MSM_BO_SCANOUT|MSM_BO_WC\n",
           Z1_WIDTH, Z1_HEIGHT, Z1_STRIDE, (unsigned long long)Z1_BYTES);

    fd = open_card0(node_path, sizeof(node_path));
    if (fd < 0) {
        printf("probe.open.rc=%d\n", negative_errno());
        printf("probe.result=z1-open-card0-failed\n");
        return 1;
    }
    printf("probe.node=/dev/dri/card0\n");
    if (get_cap(fd, DRM_CAP_DUMB_BUFFER, &dumb) == 0) {
        printf("probe.cap.dumb_buffer=%llu\n", (unsigned long long)dumb);
    }
    if (get_cap(fd, DRM_CAP_ADDFB2_MODIFIERS, &addfb2_modifiers) == 0) {
        printf("probe.cap.addfb2_modifiers=%llu\n", (unsigned long long)addfb2_modifiers);
    }
    if (get_cap(fd, DRM_CAP_PRIME, &prime) == 0) {
        printf("probe.cap.prime=0x%llx import=%d export=%d\n",
               (unsigned long long)prime,
               (prime & DRM_PRIME_CAP_IMPORT) ? 1 : 0,
               (prime & DRM_PRIME_CAP_EXPORT) ? 1 : 0);
    }

    memset(&gem, 0, sizeof(gem));
    gem.size = Z1_BYTES;
    gem.flags = MSM_BO_SCANOUT | MSM_BO_WC;
    if (ioctl_retry(fd, DRM_IOCTL_MSM_GEM_NEW, &gem) < 0) {
        rc = negative_errno();
        printf("probe.msm_gem_new.rc=%d\n", rc);
        printf("probe.result=z1-msm-gem-new-failed\n");
        close(fd);
        return 1;
    }
    handle = gem.handle;
    printf("probe.msm_gem_new.rc=0 handle=%u requested_size=%llu flags=0x%x\n",
           handle, (unsigned long long)gem.size, gem.flags);

    rc_offset = msm_gem_info_u64(fd, handle, MSM_INFO_GET_OFFSET, &offset);
    rc_iova = msm_gem_info_u64(fd, handle, MSM_INFO_GET_IOVA, &iova);
    rc_flags = msm_gem_info_u64(fd, handle, MSM_INFO_GET_FLAGS, &flags);
    printf("probe.msm_gem_info.offset.rc=%d value=0x%llx\n", rc_offset, (unsigned long long)offset);
    printf("probe.msm_gem_info.iova.rc=%d value=0x%llx\n", rc_iova, (unsigned long long)iova);
    printf("probe.msm_gem_info.flags.rc=%d value=0x%llx\n", rc_flags, (unsigned long long)flags);

    if (rc_offset == 0) {
        map = mmap(NULL, (size_t)Z1_BYTES, PROT_READ | PROT_WRITE, MAP_SHARED, fd, (off_t)offset);
        if (map == MAP_FAILED) {
            rc_mmap = negative_errno();
        } else {
            volatile uint32_t *words = (volatile uint32_t *)map;
            uint32_t word_count = (uint32_t)(Z1_BYTES / sizeof(uint32_t));

            words[0] = 0xff112233U;
            words[word_count / 2U] = 0xff445566U;
            words[word_count - 1U] = 0xff778899U;
            __sync_synchronize();
            printf("probe.mmap.sample first=0x%08x middle=0x%08x last=0x%08x words=%u\n",
                   sample_word(words, 0),
                   sample_word(words, word_count / 2U),
                   sample_word(words, word_count - 1U),
                   word_count);
            rc_mmap = 0;
        }
    }
    printf("probe.mmap.rc=%d\n", rc_mmap);

    {
        struct drm_prime_handle prime_arg;

        memset(&prime_arg, 0, sizeof(prime_arg));
        prime_arg.handle = handle;
        prime_arg.flags = DRM_CLOEXEC;
        if (ioctl_retry(fd, DRM_IOCTL_PRIME_HANDLE_TO_FD, &prime_arg) < 0) {
            rc_prime_export = negative_errno();
        } else {
            prime_fd = prime_arg.fd;
            rc_prime_export = 0;
        }
        printf("probe.prime.export.rc=%d fd_valid=%d\n", rc_prime_export, prime_fd >= 0 ? 1 : 0);
    }
    if (prime_fd >= 0) {
        struct drm_prime_handle prime_arg;

        memset(&prime_arg, 0, sizeof(prime_arg));
        prime_arg.fd = prime_fd;
        if (ioctl_retry(fd, DRM_IOCTL_PRIME_FD_TO_HANDLE, &prime_arg) < 0) {
            rc_prime_import = negative_errno();
        } else {
            imported_handle = prime_arg.handle;
            rc_prime_import = 0;
        }
        printf("probe.prime.import.rc=%d handle=%u same_handle=%d\n",
               rc_prime_import,
               imported_handle,
               imported_handle == handle ? 1 : 0);
    } else {
        printf("probe.prime.import.rc=%d handle=0 same_handle=0\n", rc_prime_import);
    }

    {
        struct drm_mode_fb_cmd2 addfb2;

        memset(&addfb2, 0, sizeof(addfb2));
        addfb2.width = Z1_WIDTH;
        addfb2.height = Z1_HEIGHT;
        addfb2.pixel_format = DRM_FORMAT_XBGR8888;
        addfb2.handles[0] = handle;
        addfb2.pitches[0] = Z1_STRIDE;
        addfb2.offsets[0] = 0;
        if (ioctl_retry(fd, DRM_IOCTL_MODE_ADDFB2, &addfb2) < 0) {
            rc_addfb2 = negative_errno();
        } else {
            fb_id = addfb2.fb_id;
            rc_addfb2 = 0;
        }
        printf("probe.addfb2.rc=%d fb_id=%u width=%u height=%u pitch=%u\n",
               rc_addfb2, fb_id, Z1_WIDTH, Z1_HEIGHT, Z1_STRIDE);
    }

    if (fb_id != 0U) {
        uint32_t rmfb_id = fb_id;

        if (ioctl_retry(fd, DRM_IOCTL_MODE_RMFB, &rmfb_id) < 0) {
            rc_rmfb = negative_errno();
        }
    }
    if (map != MAP_FAILED) {
        (void)munmap(map, (size_t)Z1_BYTES);
    }
    if (prime_fd >= 0) {
        (void)close(prime_fd);
    }
    if (imported_handle != 0U && imported_handle != handle) {
        rc_close_import = close_gem_handle(fd, imported_handle);
    }
    rc_close_handle = close_gem_handle(fd, handle);
    printf("probe.cleanup.rmfb.rc=%d close_import.rc=%d close_handle.rc=%d\n",
           rc_rmfb, rc_close_import, rc_close_handle);

    printf("probe.result=%s\n",
           rc_offset == 0 &&
           rc_mmap == 0 &&
           rc_prime_export == 0 &&
           rc_prime_import == 0 &&
           rc_addfb2 == 0 &&
           rc_rmfb == 0 &&
           rc_close_import == 0 &&
           rc_close_handle == 0
           ? "z1-drm-msm-shared-linear-preflight-pass"
           : "z1-drm-msm-shared-linear-preflight-partial");

    close(fd);
    return 0;
}
