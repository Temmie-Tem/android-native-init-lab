#include <errno.h>
#include <linux/genetlink.h>
#include <linux/netlink.h>
#include <linux/nl80211.h>
#include <linux/rtnetlink.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

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
#define NL80211_RO_VERSION "a90_nl80211_ro v1"

struct nl80211_ro_counts {
    int wiphy_count;
    int interface_count;
    int protocol_features_seen;
};

static int nla_len(const struct nlattr *attr) {
    return (int)attr->nla_len - NLA_HDRLEN;
}

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

static uint32_t nla_u32(const struct nlattr *attr, uint32_t fallback) {
    if (nla_len(attr) < (int)sizeof(uint32_t)) {
        return fallback;
    }
    return *(uint32_t *)nla_data(attr);
}

static const char *nla_string(const struct nlattr *attr) {
    if (nla_len(attr) <= 0) {
        return "";
    }
    return (const char *)nla_data(attr);
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
    memcpy((char *)attr + NLA_HDRLEN, data, len);
    memset(buf + *offset + attr_len, 0, aligned - attr_len);
    *offset += aligned;
    return 0;
}

static int send_genl(int fd,
                     uint16_t family_id,
                     uint8_t command,
                     uint16_t flags,
                     uint32_t seq,
                     const char *attr_name) {
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
    if (attr_name != NULL) {
        if (add_attr(buffer, sizeof(buffer), &offset, CTRL_ATTR_FAMILY_NAME,
                     attr_name, strlen(attr_name) + 1) < 0) {
            return -1;
        }
        nlh->nlmsg_len = (uint32_t)offset;
    }

    memset(&addr, 0, sizeof(addr));
    addr.nl_family = AF_NETLINK;
    if (sendto(fd, buffer, nlh->nlmsg_len, 0, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        return -1;
    }
    return 0;
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
    uint32_t seq = 1;

    if (send_genl(fd, GENL_ID_CTRL, CTRL_CMD_GETFAMILY, 0, seq, name) < 0) {
        return -1;
    }
    return recv_family_id(fd, seq);
}

static int query_protocol_features(int fd, int family_id, struct nl80211_ro_counts *counts) {
    char buffer[RECV_BUF_SIZE];
    uint32_t seq = 10;
    ssize_t received;
    struct nlmsghdr *nlh;
    int remaining;
    int rc = 0;

    if (send_genl(fd, (uint16_t)family_id, NL80211_CMD_GET_PROTOCOL_FEATURES, 0, seq, NULL) < 0) {
        printf("protocol_features: send_error errno=%d %s\n", errno, strerror(errno));
        return -1;
    }
    received = recv(fd, buffer, sizeof(buffer), 0);
    if (received < 0) {
        printf("protocol_features: recv_error errno=%d %s\n", errno, strerror(errno));
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
        if (nlh->nlmsg_type == NLMSG_ERROR) {
            struct nlmsgerr *err = (struct nlmsgerr *)NLMSG_DATA(nlh);
            printf("protocol_features: nlmsg_error errno=%d\n", -err->error);
            return err->error == 0 ? 0 : -1;
        }
        genlh = (struct genlmsghdr *)NLMSG_DATA(nlh);
        attr_len = (int)nlh->nlmsg_len - (int)NLMSG_LENGTH(sizeof(*genlh));
        if (attr_len < 0) {
            continue;
        }
        parse_attrs(attrs, NL80211_ATTR_MAX,
                    (struct nlattr *)((char *)genlh + GENL_HDRLEN),
                    attr_len);
        if (attrs[NL80211_ATTR_PROTOCOL_FEATURES] != NULL) {
            counts->protocol_features_seen = 1;
            printf("protocol_features: 0x%x\n",
                   nla_u32(attrs[NL80211_ATTR_PROTOCOL_FEATURES], 0));
        } else {
            printf("protocol_features: no_attr\n");
        }
    }
    return rc;
}

static int dump_wiphy(int fd, int family_id, struct nl80211_ro_counts *counts) {
    char buffer[RECV_BUF_SIZE];
    uint32_t seq = 20;
    bool done = false;

    if (send_genl(fd, (uint16_t)family_id, NL80211_CMD_GET_WIPHY, NLM_F_DUMP, seq, NULL) < 0) {
        printf("wiphy_dump: send_error errno=%d %s\n", errno, strerror(errno));
        return -1;
    }
    while (!done) {
        ssize_t received = recv(fd, buffer, sizeof(buffer), 0);
        struct nlmsghdr *nlh;
        int remaining;

        if (received < 0) {
            printf("wiphy_dump: recv_error errno=%d %s\n", errno, strerror(errno));
            return -1;
        }
        for (nlh = (struct nlmsghdr *)buffer, remaining = (int)received;
             NLMSG_OK(nlh, remaining);
             nlh = NLMSG_NEXT(nlh, remaining)) {
            struct genlmsghdr *genlh;
            struct nlattr *attrs[NL80211_ATTR_MAX + 1];
            int attr_len;
            uint32_t wiphy = UINT32_MAX;
            const char *name = "";

            if (nlh->nlmsg_seq != seq) {
                continue;
            }
            if (nlh->nlmsg_type == NLMSG_DONE) {
                done = true;
                break;
            }
            if (nlh->nlmsg_type == NLMSG_ERROR) {
                struct nlmsgerr *err = (struct nlmsgerr *)NLMSG_DATA(nlh);
                printf("wiphy_dump: nlmsg_error errno=%d\n", -err->error);
                return err->error == 0 ? 0 : -1;
            }
            genlh = (struct genlmsghdr *)NLMSG_DATA(nlh);
            attr_len = (int)nlh->nlmsg_len - (int)NLMSG_LENGTH(sizeof(*genlh));
            if (attr_len < 0) {
                continue;
            }
            parse_attrs(attrs, NL80211_ATTR_MAX,
                        (struct nlattr *)((char *)genlh + GENL_HDRLEN),
                        attr_len);
            if (attrs[NL80211_ATTR_WIPHY] != NULL) {
                wiphy = nla_u32(attrs[NL80211_ATTR_WIPHY], UINT32_MAX);
            }
            if (attrs[NL80211_ATTR_WIPHY_NAME] != NULL) {
                name = nla_string(attrs[NL80211_ATTR_WIPHY_NAME]);
            }
            printf("wiphy[%d]: index=%u name=%s\n", counts->wiphy_count,
                   wiphy == UINT32_MAX ? 0 : wiphy, name);
            counts->wiphy_count++;
        }
    }
    return 0;
}

static int dump_interfaces(int fd, int family_id, struct nl80211_ro_counts *counts) {
    char buffer[RECV_BUF_SIZE];
    uint32_t seq = 30;
    bool done = false;

    if (send_genl(fd, (uint16_t)family_id, NL80211_CMD_GET_INTERFACE, NLM_F_DUMP, seq, NULL) < 0) {
        printf("interface_dump: send_error errno=%d %s\n", errno, strerror(errno));
        return -1;
    }
    while (!done) {
        ssize_t received = recv(fd, buffer, sizeof(buffer), 0);
        struct nlmsghdr *nlh;
        int remaining;

        if (received < 0) {
            printf("interface_dump: recv_error errno=%d %s\n", errno, strerror(errno));
            return -1;
        }
        for (nlh = (struct nlmsghdr *)buffer, remaining = (int)received;
             NLMSG_OK(nlh, remaining);
             nlh = NLMSG_NEXT(nlh, remaining)) {
            struct genlmsghdr *genlh;
            struct nlattr *attrs[NL80211_ATTR_MAX + 1];
            int attr_len;
            uint32_t ifindex = 0;
            uint32_t iftype = 0;
            uint32_t wiphy = 0;
            const char *ifname = "";

            if (nlh->nlmsg_seq != seq) {
                continue;
            }
            if (nlh->nlmsg_type == NLMSG_DONE) {
                done = true;
                break;
            }
            if (nlh->nlmsg_type == NLMSG_ERROR) {
                struct nlmsgerr *err = (struct nlmsgerr *)NLMSG_DATA(nlh);
                printf("interface_dump: nlmsg_error errno=%d\n", -err->error);
                return err->error == 0 ? 0 : -1;
            }
            genlh = (struct genlmsghdr *)NLMSG_DATA(nlh);
            attr_len = (int)nlh->nlmsg_len - (int)NLMSG_LENGTH(sizeof(*genlh));
            if (attr_len < 0) {
                continue;
            }
            parse_attrs(attrs, NL80211_ATTR_MAX,
                        (struct nlattr *)((char *)genlh + GENL_HDRLEN),
                        attr_len);
            if (attrs[NL80211_ATTR_IFINDEX] != NULL) {
                ifindex = nla_u32(attrs[NL80211_ATTR_IFINDEX], 0);
            }
            if (attrs[NL80211_ATTR_IFNAME] != NULL) {
                ifname = nla_string(attrs[NL80211_ATTR_IFNAME]);
            }
            if (attrs[NL80211_ATTR_IFTYPE] != NULL) {
                iftype = nla_u32(attrs[NL80211_ATTR_IFTYPE], 0);
            }
            if (attrs[NL80211_ATTR_WIPHY] != NULL) {
                wiphy = nla_u32(attrs[NL80211_ATTR_WIPHY], 0);
            }
            printf("interface[%d]: ifindex=%u ifname=%s iftype=%u wiphy=%u\n",
                   counts->interface_count, ifindex, ifname, iftype, wiphy);
            counts->interface_count++;
        }
    }
    return 0;
}

int main(void) {
    struct nl80211_ro_counts counts;
    int fd;
    int family_id;
    int errors = 0;

    memset(&counts, 0, sizeof(counts));
    printf("%s\n", NL80211_RO_VERSION);

    fd = open_genl_socket();
    if (fd < 0) {
        printf("netlink=error errno=%d %s\n", errno, strerror(errno));
        return 2;
    }

    family_id = get_family_id(fd, "nl80211");
    if (family_id < 0) {
        printf("family=no name=nl80211 errno=%d %s\n", errno, strerror(errno));
        printf("nl80211=missing\n");
        close(fd);
        return 3;
    }
    printf("family nl80211 id=%d\n", family_id);

    if (query_protocol_features(fd, family_id, &counts) < 0) {
        errors++;
    }
    if (dump_wiphy(fd, family_id, &counts) < 0) {
        errors++;
    }
    if (dump_interfaces(fd, family_id, &counts) < 0) {
        errors++;
    }

    printf("summary: family=yes protocol_features=%d wiphy_count=%d interface_count=%d errors=%d\n",
           counts.protocol_features_seen,
           counts.wiphy_count,
           counts.interface_count,
           errors);
    close(fd);
    return errors == 0 ? 0 : 1;
}
