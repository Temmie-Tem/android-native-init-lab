#include <errno.h>
#include <linux/genetlink.h>
#include <linux/netlink.h>
#include <linux/nl80211.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>
#include <net/if.h>

#ifndef NLA_ALIGNTO
#define NLA_ALIGNTO 4
#endif

#ifndef NLA_ALIGN
#define NLA_ALIGN(len) (((len) + NLA_ALIGNTO - 1) & ~(NLA_ALIGNTO - 1))
#endif

#ifndef NLA_HDRLEN
#define NLA_HDRLEN ((int)NLA_ALIGN(sizeof(struct nlattr)))
#endif

#ifndef NLA_TYPE_MASK
#define NLA_TYPE_MASK ~(NLA_F_NESTED | NLA_F_NET_BYTEORDER)
#endif

#define RECV_BUF_SIZE 65536
#define VERSION "a90_nl80211_scan_once v1"

static void *nla_data(const struct nlattr *attr) {
    return (void *)((const char *)attr + NLA_HDRLEN);
}

static bool nla_ok(const struct nlattr *attr, int remaining) {
    return remaining >= (int)sizeof(*attr) &&
           attr->nla_len >= sizeof(*attr) &&
           attr->nla_len <= remaining;
}

static struct nlattr *nla_next(struct nlattr *attr, int *remaining) {
    int aligned = NLA_ALIGN(attr->nla_len);

    *remaining -= aligned;
    return (struct nlattr *)((char *)attr + aligned);
}

static unsigned int nla_type(const struct nlattr *attr) {
    return attr->nla_type & NLA_TYPE_MASK;
}

static void parse_attrs(struct nlattr **attrs, int max_attr, struct nlattr *attr, int len) {
    memset(attrs, 0, sizeof(struct nlattr *) * (size_t)(max_attr + 1));
    while (nla_ok(attr, len)) {
        unsigned int type = nla_type(attr);

        if (type <= (unsigned int)max_attr) {
            attrs[type] = attr;
        }
        attr = nla_next(attr, &len);
    }
}

static int add_attr(char *buf, size_t buf_size, size_t *offset, int type, const void *data, size_t len) {
    struct nlattr *attr;
    size_t attr_len = NLA_HDRLEN + len;
    size_t aligned = NLA_ALIGN(attr_len);

    if (*offset + aligned > buf_size) {
        errno = EMSGSIZE;
        return -1;
    }
    attr = (struct nlattr *)(buf + *offset);
    attr->nla_type = (unsigned short)type;
    attr->nla_len = (unsigned short)attr_len;
    if (len > 0 && data != NULL) {
        memcpy((char *)attr + NLA_HDRLEN, data, len);
    }
    memset(buf + *offset + attr_len, 0, aligned - attr_len);
    *offset += aligned;
    return 0;
}

static struct nlattr *nest_start(char *buf, size_t buf_size, size_t *offset, int type) {
    struct nlattr *attr;
    size_t aligned = NLA_ALIGN((size_t)NLA_HDRLEN);

    if (*offset + aligned > buf_size) {
        errno = EMSGSIZE;
        return NULL;
    }
    attr = (struct nlattr *)(buf + *offset);
    attr->nla_type = (unsigned short)(type | NLA_F_NESTED);
    attr->nla_len = (unsigned short)NLA_HDRLEN;
    memset(buf + *offset + NLA_HDRLEN, 0, aligned - (size_t)NLA_HDRLEN);
    *offset += aligned;
    return attr;
}

static void nest_end(struct nlattr *attr, size_t offset, const char *buf) {
    attr->nla_len = (unsigned short)((buf + offset) - (const char *)attr);
}

static int open_genl_socket(void) {
    struct sockaddr_nl local;
    int fd = socket(AF_NETLINK, SOCK_RAW | SOCK_CLOEXEC, NETLINK_GENERIC);

    if (fd < 0) {
        return -1;
    }
    memset(&local, 0, sizeof(local));
    local.nl_family = AF_NETLINK;
    if (bind(fd, (struct sockaddr *)&local, sizeof(local)) < 0) {
        close(fd);
        return -1;
    }
    return fd;
}

static int send_genl(int fd,
                     uint16_t family_id,
                     uint8_t command,
                     uint16_t flags,
                     uint32_t seq,
                     const char *family_name,
                     uint32_t ifindex,
                     bool include_ifindex,
                     bool include_wildcard_ssid) {
    char buffer[1024];
    struct nlmsghdr *nlh = (struct nlmsghdr *)buffer;
    struct genlmsghdr *genlh;
    struct sockaddr_nl addr;
    size_t offset;

    memset(buffer, 0, sizeof(buffer));
    nlh->nlmsg_len = NLMSG_LENGTH(sizeof(*genlh));
    nlh->nlmsg_type = family_id;
    nlh->nlmsg_flags = NLM_F_REQUEST | flags;
    nlh->nlmsg_seq = seq;
    nlh->nlmsg_pid = 0;
    genlh = (struct genlmsghdr *)NLMSG_DATA(nlh);
    genlh->cmd = command;
    genlh->version = 1;
    offset = NLMSG_ALIGN(nlh->nlmsg_len);
    if (family_name != NULL) {
        if (add_attr(buffer, sizeof(buffer), &offset, CTRL_ATTR_FAMILY_NAME,
                     family_name, strlen(family_name) + 1) < 0) {
            return -1;
        }
    }
    if (include_ifindex) {
        if (add_attr(buffer, sizeof(buffer), &offset, NL80211_ATTR_IFINDEX,
                     &ifindex, sizeof(ifindex)) < 0) {
            return -1;
        }
    }
    if (include_wildcard_ssid) {
        struct nlattr *scan_ssids = nest_start(buffer, sizeof(buffer), &offset, NL80211_ATTR_SCAN_SSIDS);

        if (scan_ssids == NULL) {
            return -1;
        }
        if (add_attr(buffer, sizeof(buffer), &offset, 1, NULL, 0) < 0) {
            return -1;
        }
        nest_end(scan_ssids, offset, buffer);
    }
    nlh->nlmsg_len = (uint32_t)offset;

    memset(&addr, 0, sizeof(addr));
    addr.nl_family = AF_NETLINK;
    if (sendto(fd, buffer, nlh->nlmsg_len, 0, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        return -1;
    }
    return 0;
}

static int recv_family_id(int fd, uint32_t seq) {
    char buffer[RECV_BUF_SIZE];
    ssize_t received;
    struct nlmsghdr *nlh;
    int remaining;

    received = recv(fd, buffer, sizeof(buffer), 0);
    if (received < 0) {
        return -1;
    }
    for (nlh = (struct nlmsghdr *)buffer, remaining = (int)received;
         NLMSG_OK(nlh, remaining);
         nlh = NLMSG_NEXT(nlh, remaining)) {
        struct genlmsghdr *genlh;
        struct nlattr *attrs[CTRL_ATTR_MAX + 1];
        int attr_len;

        if (nlh->nlmsg_seq != seq) {
            continue;
        }
        if (nlh->nlmsg_type == NLMSG_ERROR) {
            struct nlmsgerr *err = (struct nlmsgerr *)NLMSG_DATA(nlh);

            errno = err->error < 0 ? -err->error : EIO;
            return -1;
        }
        if (nlh->nlmsg_type == NLMSG_DONE) {
            break;
        }
        genlh = (struct genlmsghdr *)NLMSG_DATA(nlh);
        attr_len = (int)nlh->nlmsg_len - (int)NLMSG_LENGTH(sizeof(*genlh));
        if (attr_len < 0) {
            continue;
        }
        parse_attrs(attrs, CTRL_ATTR_MAX,
                    (struct nlattr *)((char *)genlh + GENL_HDRLEN),
                    attr_len);
        if (attrs[CTRL_ATTR_FAMILY_ID] != NULL) {
            return (int)*(uint16_t *)nla_data(attrs[CTRL_ATTR_FAMILY_ID]);
        }
    }
    errno = ENOENT;
    return -1;
}

static int get_family_id(int fd, const char *name) {
    const uint32_t seq = 1;

    if (send_genl(fd, GENL_ID_CTRL, CTRL_CMD_GETFAMILY, 0, seq, name, 0, false, false) < 0) {
        return -1;
    }
    return recv_family_id(fd, seq);
}

static int recv_ack(int fd, uint32_t seq) {
    char buffer[RECV_BUF_SIZE];

    for (;;) {
        ssize_t received = recv(fd, buffer, sizeof(buffer), 0);
        struct nlmsghdr *nlh;
        int remaining;

        if (received < 0) {
            return -1;
        }
        for (nlh = (struct nlmsghdr *)buffer, remaining = (int)received;
             NLMSG_OK(nlh, remaining);
             nlh = NLMSG_NEXT(nlh, remaining)) {
            if (nlh->nlmsg_seq != seq) {
                continue;
            }
            if (nlh->nlmsg_type == NLMSG_ERROR) {
                struct nlmsgerr *err = (struct nlmsgerr *)NLMSG_DATA(nlh);

                if (err->error == 0) {
                    return 0;
                }
                errno = err->error < 0 ? -err->error : EIO;
                return -1;
            }
            if (nlh->nlmsg_type == NLMSG_DONE) {
                return 0;
            }
        }
    }
}

static int trigger_scan(int fd, int family_id, uint32_t ifindex) {
    const uint32_t seq = 2;

    if (send_genl(fd, (uint16_t)family_id, NL80211_CMD_TRIGGER_SCAN, NLM_F_ACK,
                  seq, NULL, ifindex, true, true) < 0) {
        return -1;
    }
    return recv_ack(fd, seq);
}

static int dump_scan_count(int fd, int family_id, uint32_t ifindex, int *scan_count) {
    char buffer[RECV_BUF_SIZE];
    const uint32_t seq = 3;
    bool done = false;

    *scan_count = 0;
    if (send_genl(fd, (uint16_t)family_id, NL80211_CMD_GET_SCAN, NLM_F_DUMP,
                  seq, NULL, ifindex, true, false) < 0) {
        return -1;
    }
    while (!done) {
        ssize_t received = recv(fd, buffer, sizeof(buffer), 0);
        struct nlmsghdr *nlh;
        int remaining;

        if (received < 0) {
            return -1;
        }
        for (nlh = (struct nlmsghdr *)buffer, remaining = (int)received;
             NLMSG_OK(nlh, remaining);
             nlh = NLMSG_NEXT(nlh, remaining)) {
            struct genlmsghdr *genlh;
            struct nlattr *attrs[NL80211_ATTR_MAX + 1];
            int attr_len;

            if (nlh->nlmsg_seq != seq) {
                continue;
            }
            if (nlh->nlmsg_type == NLMSG_DONE) {
                done = true;
                break;
            }
            if (nlh->nlmsg_type == NLMSG_ERROR) {
                struct nlmsgerr *err = (struct nlmsgerr *)NLMSG_DATA(nlh);

                if (err->error == 0) {
                    done = true;
                    break;
                }
                errno = err->error < 0 ? -err->error : EIO;
                return -1;
            }
            genlh = (struct genlmsghdr *)NLMSG_DATA(nlh);
            attr_len = (int)nlh->nlmsg_len - (int)NLMSG_LENGTH(sizeof(*genlh));
            if (attr_len < 0) {
                continue;
            }
            parse_attrs(attrs, NL80211_ATTR_MAX,
                        (struct nlattr *)((char *)genlh + GENL_HDRLEN),
                        attr_len);
            if (attrs[NL80211_ATTR_BSS] != NULL) {
                (*scan_count)++;
            }
        }
    }
    return 0;
}

int main(int argc, char **argv) {
    const char *ifname = argc > 1 ? argv[1] : "wlan0";
    int delay_ms = argc > 2 ? atoi(argv[2]) : 5000;
    unsigned int ifindex;
    int fd;
    int family_id;
    int scan_count = 0;
    int saved_errno;

    if (delay_ms < 0) {
        delay_ms = 0;
    }
    if (delay_ms > 30000) {
        delay_ms = 30000;
    }

    printf("nl80211_scan_once.version=%s\n", VERSION);
    printf("nl80211_scan_once.ifname=%s\n", ifname);
    printf("nl80211_scan_once.credentials=0\n");
    printf("nl80211_scan_once.connect=0\n");
    printf("nl80211_scan_once.dhcp_routing=0\n");
    printf("nl80211_scan_once.external_ping=0\n");
    printf("nl80211_scan_once.raw_results_redacted=1\n");

    ifindex = if_nametoindex(ifname);
    if (ifindex == 0) {
        saved_errno = errno;
        printf("nl80211_scan_once.ifindex=0\n");
        printf("nl80211_scan_once.errno=%d\n", saved_errno);
        printf("nl80211_scan_once.result=interface-missing\n");
        return 30;
    }
    printf("nl80211_scan_once.ifindex=%u\n", ifindex);

    fd = open_genl_socket();
    if (fd < 0) {
        saved_errno = errno;
        printf("nl80211_scan_once.netlink_open=0\n");
        printf("nl80211_scan_once.errno=%d\n", saved_errno);
        printf("nl80211_scan_once.result=nl80211-unavailable\n");
        return 31;
    }
    printf("nl80211_scan_once.netlink_open=1\n");

    family_id = get_family_id(fd, "nl80211");
    if (family_id < 0) {
        saved_errno = errno;
        close(fd);
        printf("nl80211_scan_once.family_id=0\n");
        printf("nl80211_scan_once.errno=%d\n", saved_errno);
        printf("nl80211_scan_once.result=family-missing\n");
        return 32;
    }
    printf("nl80211_scan_once.family_id=%d\n", family_id);
    printf("nl80211_scan_once.trigger_attempted=1\n");

    if (trigger_scan(fd, family_id, ifindex) < 0) {
        saved_errno = errno;
        close(fd);
        printf("nl80211_scan_once.trigger_rc=-1\n");
        printf("nl80211_scan_once.trigger_errno=%d\n", saved_errno);
        printf("nl80211_scan_once.result=trigger-failed\n");
        return 33;
    }
    printf("nl80211_scan_once.trigger_rc=0\n");
    printf("nl80211_scan_once.trigger_errno=0\n");
    printf("nl80211_scan_once.delay_ms=%d\n", delay_ms);
    usleep((useconds_t)delay_ms * 1000U);

    if (dump_scan_count(fd, family_id, ifindex, &scan_count) < 0) {
        saved_errno = errno;
        close(fd);
        printf("nl80211_scan_once.scan_result_count=0\n");
        printf("nl80211_scan_once.errno=%d\n", saved_errno);
        printf("nl80211_scan_once.result=dump-failed\n");
        return 34;
    }
    close(fd);
    printf("nl80211_scan_once.scan_result_count=%d\n", scan_count);
    if (scan_count > 0) {
        printf("nl80211_scan_once.result=pass\n");
        return 0;
    }
    printf("nl80211_scan_once.result=zero-bss\n");
    return 35;
}
