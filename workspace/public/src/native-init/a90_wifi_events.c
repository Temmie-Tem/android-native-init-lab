#include "a90_wifi.h"

#include <arpa/inet.h>
#include <errno.h>
#include <linux/genetlink.h>
#include <linux/if_addr.h>
#include <linux/if_link.h>
#include <linux/netlink.h>
#include <linux/nl80211.h>
#include <linux/rtnetlink.h>
#include <net/if.h>
#include <poll.h>
#include <signal.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/wait.h>
#include <unistd.h>

#include "a90_console.h"
#include "a90_log.h"
#include "a90_util.h"

#ifndef SOCK_CLOEXEC
#define SOCK_CLOEXEC 02000000
#endif

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

#define A90_WIFI_IFACE "wlan0"
#define A90_WIFI_SCAN_RECV_SIZE 65536
#define A90_WIFI_NETEVENTS_VERSION "a90-native-wifi-rtnetlink-events-v1"
#define A90_WIFI_NETEVENT_MAX_MS 30000
#define A90_WIFI_NETEVENT_MAX_STORED 16
#define A90_WIFI_NL80211_EVENTS_VERSION "a90-native-wifi-nl80211-events-v1"
#define A90_WIFI_CONNECT_EVENT_VERSION "a90-native-wifi-connect-event-v1"
#define A90_WIFI_NL80211_EVENT_MAX_MS 60000
#define A90_WIFI_NL80211_EVENT_MAX_STORED 16
#define A90_WIFI_CONNECT_EVENT_CHILD_WAIT_MS 240000

struct wifi_netevent {
    char type[16];
    char iface[IFNAMSIZ];
    char operstate[32];
    char ip4_label[64];
    unsigned int ifindex;
    unsigned int flags;
    int carrier;
    long monotonic_ms;
};

struct wifi_netevent_snapshot {
    int rc;
    int saved_errno;
    int socket_open;
    int timeout_ms;
    int event_count;
    int stored_count;
    struct wifi_netevent events[A90_WIFI_NETEVENT_MAX_STORED];
    char decision[64];
};

struct wifi_nl80211_family_info {
    int family_id;
    int group_count;
    int mlme_group_id;
    int scan_group_id;
    int config_group_id;
};

struct wifi_nl80211_event {
    char cmd[32];
    char iface[IFNAMSIZ];
    int cmd_id;
    unsigned int ifindex;
    long monotonic_ms;
};

struct wifi_nl80211_event_snapshot {
    int rc;
    int saved_errno;
    int socket_open;
    int timeout_ms;
    int family_id;
    int group_count;
    int mlme_group_id;
    int scan_group_id;
    int config_group_id;
    int mlme_joined;
    int scan_joined;
    int config_joined;
    int groups_joined;
    int event_count;
    int connect_event_count;
    int stored_count;
    long first_connect_event_ms;
    struct wifi_nl80211_event events[A90_WIFI_NL80211_EVENT_MAX_STORED];
    char decision[64];
};

struct wifi_nl80211_event_start {
    int (*fn)(void *ctx);
    void *ctx;
};

struct wifi_connect_event_child {
    const char *profile_name;
    int pipe_read;
    int pipe_write;
    int start_rc;
    int start_errno;
    int connect_rc;
    int child_status;
    int child_exit_code;
    int child_signal;
    int child_exited;
    int child_timed_out;
    pid_t pid;
};

static void wifi_read_attr(const char *path, const char *name, char *out, size_t out_size) {
    char attr_path[256];

    if (out == NULL || out_size == 0) {
        return;
    }
    out[0] = '\0';
    if (snprintf(attr_path, sizeof(attr_path), "%s/%s", path, name) >= (int)sizeof(attr_path) ||
        read_trimmed_text_file(attr_path, out, out_size) < 0) {
        snprintf(out, out_size, "-");
    }
}

static bool wifi_value_missing(const char *value) {
    return value == NULL || value[0] == '\0' || strcmp(value, "-") == 0;
}

static void wifi_ipv4_label(const char *ipv4, char *out, size_t out_size) {
    struct in_addr address;
    uint32_t value;

    if (out == NULL || out_size == 0) {
        return;
    }
    snprintf(out, out_size, "%s", "none");
    if (wifi_value_missing(ipv4)) {
        return;
    }
    if (inet_pton(AF_INET, ipv4, &address) != 1) {
        return;
    }
    value = ntohl(address.s_addr);
    snprintf(out,
             out_size,
             "%u.%u.%u.x",
             (unsigned int)((value >> 24) & 0xffU),
             (unsigned int)((value >> 16) & 0xffU),
             (unsigned int)((value >> 8) & 0xffU));
}

static bool wifi_netevent_iface_interesting(const char *iface) {
    return iface != NULL &&
           (strcmp(iface, A90_WIFI_IFACE) == 0 || strcmp(iface, "ncm0") == 0);
}

static void wifi_read_iface_attr(const char *iface, const char *name, char *out, size_t out_size) {
    char iface_path[128];

    if (out == NULL || out_size == 0) {
        return;
    }
    snprintf(out, out_size, "-");
    if (iface == NULL ||
        snprintf(iface_path, sizeof(iface_path), "/sys/class/net/%s", iface) >= (int)sizeof(iface_path)) {
        return;
    }
    wifi_read_attr(iface_path, name, out, out_size);
}

static int wifi_iface_carrier_value(const char *iface) {
    char carrier[16];
    char *end = NULL;
    long value;

    wifi_read_iface_attr(iface, "carrier", carrier, sizeof(carrier));
    if (wifi_value_missing(carrier)) {
        return -1;
    }
    errno = 0;
    value = strtol(carrier, &end, 10);
    if (errno != 0 || end == carrier) {
        return -1;
    }
    return value != 0 ? 1 : 0;
}

static void wifi_netevent_store(struct wifi_netevent_snapshot *out,
                                const char *type,
                                const char *iface,
                                unsigned int ifindex,
                                unsigned int flags,
                                int carrier,
                                const char *operstate,
                                const char *ip4_label) {
    struct wifi_netevent *event;

    if (out == NULL || type == NULL || iface == NULL) {
        return;
    }
    ++out->event_count;
    if (out->stored_count >= A90_WIFI_NETEVENT_MAX_STORED) {
        return;
    }
    event = &out->events[out->stored_count++];
    memset(event, 0, sizeof(*event));
    snprintf(event->type, sizeof(event->type), "%s", type);
    snprintf(event->iface, sizeof(event->iface), "%s", iface);
    snprintf(event->operstate, sizeof(event->operstate), "%s",
             operstate != NULL && operstate[0] != '\0' ? operstate : "-");
    snprintf(event->ip4_label, sizeof(event->ip4_label), "%s",
             ip4_label != NULL && ip4_label[0] != '\0' ? ip4_label : "none");
    event->ifindex = ifindex;
    event->flags = flags;
    event->carrier = carrier;
    event->monotonic_ms = monotonic_millis();
    a90_logf("wifi",
             "netevent type=%s iface=%s ifindex=%u flags=0x%x carrier=%d operstate=%s ip4_label=%s raw_ip_redacted=1",
             event->type,
             event->iface,
             event->ifindex,
             event->flags,
             event->carrier,
             event->operstate,
             event->ip4_label);
}

static void wifi_netevent_parse_link(struct wifi_netevent_snapshot *out,
                                     const struct nlmsghdr *nlh,
                                     const char *type) {
    const struct ifinfomsg *ifi = (const struct ifinfomsg *)NLMSG_DATA(nlh);
    char iface[IFNAMSIZ];
    char operstate[32];

    if (ifi == NULL || if_indextoname((unsigned int)ifi->ifi_index, iface) == NULL) {
        return;
    }
    if (!wifi_netevent_iface_interesting(iface)) {
        return;
    }
    wifi_read_iface_attr(iface, "operstate", operstate, sizeof(operstate));
    wifi_netevent_store(out,
                        type,
                        iface,
                        (unsigned int)ifi->ifi_index,
                        (unsigned int)ifi->ifi_flags,
                        wifi_iface_carrier_value(iface),
                        operstate,
                        "none");
}

static void wifi_netevent_parse_addr(struct wifi_netevent_snapshot *out,
                                     const struct nlmsghdr *nlh,
                                     const char *type) {
    const struct ifaddrmsg *ifa = (const struct ifaddrmsg *)NLMSG_DATA(nlh);
    struct rtattr *attr;
    int attr_len;
    char iface[IFNAMSIZ];
    char raw_ip[64] = "-";
    char ip4_label[64];
    char operstate[32];

    if (ifa == NULL || ifa->ifa_family != AF_INET ||
        if_indextoname((unsigned int)ifa->ifa_index, iface) == NULL ||
        !wifi_netevent_iface_interesting(iface)) {
        return;
    }
    attr = IFA_RTA(ifa);
    attr_len = IFA_PAYLOAD(nlh);
    while (RTA_OK(attr, attr_len)) {
        int attr_type = attr->rta_type & NLA_TYPE_MASK;

        if ((attr_type == IFA_LOCAL || attr_type == IFA_ADDRESS) &&
            RTA_PAYLOAD(attr) >= (int)sizeof(struct in_addr)) {
            if (inet_ntop(AF_INET, RTA_DATA(attr), raw_ip, sizeof(raw_ip)) == NULL) {
                snprintf(raw_ip, sizeof(raw_ip), "%s", "-");
            }
            if (attr_type == IFA_LOCAL) {
                break;
            }
        }
        attr = RTA_NEXT(attr, attr_len);
    }
    wifi_ipv4_label(raw_ip, ip4_label, sizeof(ip4_label));
    wifi_read_iface_attr(iface, "operstate", operstate, sizeof(operstate));
    wifi_netevent_store(out,
                        type,
                        iface,
                        (unsigned int)ifa->ifa_index,
                        0,
                        wifi_iface_carrier_value(iface),
                        operstate,
                        ip4_label);
}

int a90_wifi_netevents_collect(int timeout_ms, struct wifi_netevent_snapshot *out) {
    struct sockaddr_nl local;
    int fd;
    long started_ms;
    long deadline_ms;

    if (out == NULL) {
        return -EINVAL;
    }
    memset(out, 0, sizeof(*out));
    out->timeout_ms = timeout_ms;
    snprintf(out->decision, sizeof(out->decision), "%s", "wifi-netevents-unstarted");
    if (timeout_ms < 0 || timeout_ms > A90_WIFI_NETEVENT_MAX_MS) {
        out->rc = -EINVAL;
        out->saved_errno = EINVAL;
        snprintf(out->decision, sizeof(out->decision), "%s", "wifi-netevents-invalid-timeout");
        return out->rc;
    }
    fd = socket(AF_NETLINK, SOCK_RAW | SOCK_CLOEXEC, NETLINK_ROUTE);
    if (fd < 0) {
        out->rc = -errno;
        out->saved_errno = errno;
        snprintf(out->decision, sizeof(out->decision), "%s", "wifi-netevents-socket-failed");
        return out->rc;
    }
    out->socket_open = 1;
    memset(&local, 0, sizeof(local));
    local.nl_family = AF_NETLINK;
    local.nl_groups = RTMGRP_LINK | RTMGRP_IPV4_IFADDR;
    if (bind(fd, (struct sockaddr *)&local, sizeof(local)) < 0) {
        out->rc = -errno;
        out->saved_errno = errno;
        snprintf(out->decision, sizeof(out->decision), "%s", "wifi-netevents-bind-failed");
        (void)close(fd);
        return out->rc;
    }

    started_ms = monotonic_millis();
    deadline_ms = started_ms + timeout_ms;
    for (;;) {
        struct pollfd poll_fd;
        int wait_ms = (int)(deadline_ms - monotonic_millis());
        int poll_rc;
        char buffer[8192];
        ssize_t received;
        struct nlmsghdr *nlh;
        int remaining;

        if (wait_ms < 0) {
            break;
        }
        memset(&poll_fd, 0, sizeof(poll_fd));
        poll_fd.fd = fd;
        poll_fd.events = POLLIN;
        poll_rc = poll(&poll_fd, 1, wait_ms);
        if (poll_rc == 0) {
            break;
        }
        if (poll_rc < 0) {
            if (errno == EINTR) {
                continue;
            }
            out->rc = -errno;
            out->saved_errno = errno;
            snprintf(out->decision, sizeof(out->decision), "%s", "wifi-netevents-poll-failed");
            (void)close(fd);
            return out->rc;
        }
        received = recv(fd, buffer, sizeof(buffer), 0);
        if (received < 0) {
            if (errno == EINTR) {
                continue;
            }
            out->rc = -errno;
            out->saved_errno = errno;
            snprintf(out->decision, sizeof(out->decision), "%s", "wifi-netevents-recv-failed");
            (void)close(fd);
            return out->rc;
        }
        for (nlh = (struct nlmsghdr *)buffer, remaining = (int)received;
             NLMSG_OK(nlh, remaining);
             nlh = NLMSG_NEXT(nlh, remaining)) {
            if (nlh->nlmsg_type == NLMSG_ERROR) {
                const struct nlmsgerr *err = (const struct nlmsgerr *)NLMSG_DATA(nlh);

                out->rc = err->error < 0 ? err->error : -EIO;
                out->saved_errno = err->error < 0 ? -err->error : EIO;
                snprintf(out->decision, sizeof(out->decision), "%s", "wifi-netevents-netlink-error");
                (void)close(fd);
                return out->rc;
            }
            if (nlh->nlmsg_type == RTM_NEWLINK) {
                wifi_netevent_parse_link(out, nlh, "newlink");
            } else if (nlh->nlmsg_type == RTM_DELLINK) {
                wifi_netevent_parse_link(out, nlh, "dellink");
            } else if (nlh->nlmsg_type == RTM_NEWADDR) {
                wifi_netevent_parse_addr(out, nlh, "newaddr");
            } else if (nlh->nlmsg_type == RTM_DELADDR) {
                wifi_netevent_parse_addr(out, nlh, "deladdr");
            }
        }
    }
    (void)close(fd);
    out->rc = 0;
    snprintf(out->decision,
             sizeof(out->decision),
             "%s",
             out->event_count > 0 ? "wifi-netevents-events-observed" : "wifi-netevents-timeout-no-events");
    return 0;
}

int a90_wifi_netevents_once(int timeout_ms) {
    struct wifi_netevent_snapshot snapshot;
    int rc;
    int i;

    rc = a90_wifi_netevents_collect(timeout_ms, &snapshot);
    a90_console_printf("[wifi netevents]\r\n");
    a90_console_printf("version=%s\r\n", A90_WIFI_NETEVENTS_VERSION);
    a90_console_printf("monitor=rtnetlink\r\n");
    a90_console_printf("groups=RTMGRP_LINK,RTMGRP_IPV4_IFADDR\r\n");
    a90_console_printf("ifaces=wlan0,ncm0\r\n");
    a90_console_printf("timeout_ms=%d\r\n", snapshot.timeout_ms);
    a90_console_printf("socket_open=%d\r\n", snapshot.socket_open);
    a90_console_printf("event_count=%d\r\n", snapshot.event_count);
    a90_console_printf("stored_count=%d\r\n", snapshot.stored_count);
    a90_console_printf("raw_ip_redacted=1\r\n");
    a90_console_printf("secret_values_logged=0\r\n");
    a90_console_printf("connect_attempted=0\r\n");
    a90_console_printf("dhcp_attempted=0\r\n");
    a90_console_printf("external_ping_attempted=0\r\n");
    for (i = 0; i < snapshot.stored_count; ++i) {
        const struct wifi_netevent *event = &snapshot.events[i];

        a90_console_printf("event.%d.type=%s\r\n", i, event->type);
        a90_console_printf("event.%d.iface=%s\r\n", i, event->iface);
        a90_console_printf("event.%d.ifindex=%u\r\n", i, event->ifindex);
        a90_console_printf("event.%d.flags=0x%x\r\n", i, event->flags);
        a90_console_printf("event.%d.carrier=%d\r\n", i, event->carrier);
        a90_console_printf("event.%d.operstate=%s\r\n", i, event->operstate);
        a90_console_printf("event.%d.ip4_label=%s\r\n", i, event->ip4_label);
        a90_console_printf("event.%d.monotonic_ms=%ld\r\n", i, event->monotonic_ms);
    }
    a90_console_printf("rc=%d\r\n", snapshot.rc);
    a90_console_printf("saved_errno=%d\r\n", snapshot.saved_errno);
    a90_console_printf("decision=%s\r\n", snapshot.decision);
    a90_logf("wifi",
             "netevents decision=%s rc=%d events=%d stored=%d timeout_ms=%d",
             snapshot.decision,
             snapshot.rc,
             snapshot.event_count,
             snapshot.stored_count,
             snapshot.timeout_ms);
    return rc;
}

static void *wifi_nla_data(const struct nlattr *attr) {
    return (void *)((const char *)attr + NLA_HDRLEN);
}

static bool wifi_nla_ok(const struct nlattr *attr, int remaining) {
    return remaining >= (int)sizeof(*attr) &&
           attr->nla_len >= sizeof(*attr) &&
           attr->nla_len <= remaining;
}

static struct nlattr *wifi_nla_next(struct nlattr *attr, int *remaining) {
    int aligned_len = NLA_ALIGN(attr->nla_len);

    *remaining -= aligned_len;
    return (struct nlattr *)((char *)attr + aligned_len);
}

static unsigned int wifi_nla_type(const struct nlattr *attr) {
    return attr->nla_type & NLA_TYPE_MASK;
}

static int wifi_nla_payload_len(const struct nlattr *attr) {
    if (attr == NULL || attr->nla_len < NLA_HDRLEN) {
        return 0;
    }
    return (int)attr->nla_len - NLA_HDRLEN;
}

static void wifi_parse_attrs(struct nlattr **attrs, int max_attr, struct nlattr *attr, int len) {
    memset(attrs, 0, sizeof(struct nlattr *) * (size_t)(max_attr + 1));
    while (wifi_nla_ok(attr, len)) {
        unsigned int attr_type = wifi_nla_type(attr);

        if (attr_type <= (unsigned int)max_attr) {
            attrs[attr_type] = attr;
        }
        attr = wifi_nla_next(attr, &len);
    }
}

static int wifi_add_attr(char *buf, size_t buf_size, size_t *offset, int type, const void *data, size_t len) {
    struct nlattr *attr;
    size_t attr_len = NLA_HDRLEN + len;
    size_t aligned_len = NLA_ALIGN(attr_len);

    if (*offset + aligned_len > buf_size) {
        errno = EMSGSIZE;
        return -1;
    }
    attr = (struct nlattr *)(buf + *offset);
    attr->nla_type = (unsigned short)type;
    attr->nla_len = (unsigned short)attr_len;
    if (len > 0 && data != NULL) {
        memcpy((char *)attr + NLA_HDRLEN, data, len);
    }
    memset(buf + *offset + attr_len, 0, aligned_len - attr_len);
    *offset += aligned_len;
    return 0;
}

static struct nlattr *wifi_nest_start(char *buf, size_t buf_size, size_t *offset, int type) {
    struct nlattr *attr;
    size_t aligned_len = NLA_ALIGN((size_t)NLA_HDRLEN);

    if (*offset + aligned_len > buf_size) {
        errno = EMSGSIZE;
        return NULL;
    }
    attr = (struct nlattr *)(buf + *offset);
    attr->nla_type = (unsigned short)(type | NLA_F_NESTED);
    attr->nla_len = (unsigned short)NLA_HDRLEN;
    memset(buf + *offset + NLA_HDRLEN, 0, aligned_len - (size_t)NLA_HDRLEN);
    *offset += aligned_len;
    return attr;
}

static void wifi_nest_end(struct nlattr *attr, size_t offset, const char *buf) {
    attr->nla_len = (unsigned short)((buf + offset) - (const char *)attr);
}

static int wifi_open_genl_socket(void) {
    struct sockaddr_nl local;
    struct timeval timeout;
    int socket_fd = socket(AF_NETLINK, SOCK_RAW | SOCK_CLOEXEC, NETLINK_GENERIC);

    if (socket_fd < 0) {
        return -1;
    }
    memset(&local, 0, sizeof(local));
    local.nl_family = AF_NETLINK;
    if (bind(socket_fd, (struct sockaddr *)&local, sizeof(local)) < 0) {
        close(socket_fd);
        return -1;
    }
    memset(&timeout, 0, sizeof(timeout));
    timeout.tv_sec = 5;
    if (setsockopt(socket_fd, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout)) < 0) {
        close(socket_fd);
        return -1;
    }
    return socket_fd;
}

static int wifi_send_genl(int socket_fd,
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
    if (family_name != NULL &&
        wifi_add_attr(buffer, sizeof(buffer), &offset, CTRL_ATTR_FAMILY_NAME,
                      family_name, strlen(family_name) + 1) < 0) {
        return -1;
    }
    if (include_ifindex &&
        wifi_add_attr(buffer, sizeof(buffer), &offset, NL80211_ATTR_IFINDEX,
                      &ifindex, sizeof(ifindex)) < 0) {
        return -1;
    }
    if (include_wildcard_ssid) {
        struct nlattr *scan_ssids = wifi_nest_start(buffer, sizeof(buffer), &offset, NL80211_ATTR_SCAN_SSIDS);

        if (scan_ssids == NULL ||
            wifi_add_attr(buffer, sizeof(buffer), &offset, 1, NULL, 0) < 0) {
            return -1;
        }
        wifi_nest_end(scan_ssids, offset, buffer);
    }
    nlh->nlmsg_len = (uint32_t)offset;

    memset(&addr, 0, sizeof(addr));
    addr.nl_family = AF_NETLINK;
    if (sendto(socket_fd, buffer, nlh->nlmsg_len, 0, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        return -1;
    }
    return 0;
}

static void wifi_copy_nla_string(const struct nlattr *attr, char *out, size_t out_size) {
    int payload_len;
    size_t copy_len;

    if (out == NULL || out_size == 0) {
        return;
    }
    out[0] = '\0';
    payload_len = wifi_nla_payload_len(attr);
    if (attr == NULL || payload_len <= 0) {
        return;
    }
    copy_len = (size_t)payload_len;
    if (copy_len >= out_size) {
        copy_len = out_size - 1;
    }
    memcpy(out, wifi_nla_data(attr), copy_len);
    out[copy_len] = '\0';
}

static int wifi_nla_u32(const struct nlattr *attr, uint32_t *out) {
    if (attr == NULL || out == NULL || wifi_nla_payload_len(attr) < (int)sizeof(*out)) {
        return -EINVAL;
    }
    memcpy(out, wifi_nla_data(attr), sizeof(*out));
    return 0;
}

static void wifi_parse_mcast_group_entry(struct wifi_nl80211_family_info *info,
                                         struct nlattr *group_attr) {
    struct nlattr *group_attrs[CTRL_ATTR_MCAST_GRP_MAX + 1];
    char name[64];
    uint32_t group_id = 0;
    int payload_len;

    if (info == NULL || group_attr == NULL) {
        return;
    }
    payload_len = wifi_nla_payload_len(group_attr);
    if (payload_len <= 0) {
        return;
    }
    wifi_parse_attrs(group_attrs,
                     CTRL_ATTR_MCAST_GRP_MAX,
                     (struct nlattr *)wifi_nla_data(group_attr),
                     payload_len);
    wifi_copy_nla_string(group_attrs[CTRL_ATTR_MCAST_GRP_NAME], name, sizeof(name));
    if (wifi_nla_u32(group_attrs[CTRL_ATTR_MCAST_GRP_ID], &group_id) < 0 || name[0] == '\0') {
        return;
    }
    ++info->group_count;
    if (strcmp(name, "mlme") == 0) {
        info->mlme_group_id = (int)group_id;
    } else if (strcmp(name, "scan") == 0) {
        info->scan_group_id = (int)group_id;
    } else if (strcmp(name, "config") == 0) {
        info->config_group_id = (int)group_id;
    }
}

static void wifi_parse_mcast_groups(struct wifi_nl80211_family_info *info, struct nlattr *groups_attr) {
    struct nlattr *group_attr;
    int remaining;

    if (info == NULL || groups_attr == NULL) {
        return;
    }
    group_attr = (struct nlattr *)wifi_nla_data(groups_attr);
    remaining = wifi_nla_payload_len(groups_attr);
    while (wifi_nla_ok(group_attr, remaining)) {
        wifi_parse_mcast_group_entry(info, group_attr);
        group_attr = wifi_nla_next(group_attr, &remaining);
    }
}

static int wifi_recv_family_info(int socket_fd,
                                 uint32_t seq,
                                 struct wifi_nl80211_family_info *info) {
    char buffer[A90_WIFI_SCAN_RECV_SIZE];
    ssize_t received = recv(socket_fd, buffer, sizeof(buffer), 0);
    struct nlmsghdr *nlh;
    int remaining;

    if (info == NULL) {
        errno = EINVAL;
        return -1;
    }
    memset(info, 0, sizeof(*info));
    if (received < 0) {
        return -1;
    }
    for (nlh = (struct nlmsghdr *)buffer, remaining = (int)received;
         NLMSG_OK(nlh, remaining);
         nlh = NLMSG_NEXT(nlh, remaining)) {
        struct genlmsghdr *genlh;
        struct nlattr *attrs[CTRL_ATTR_MAX + 1];
        int attr_len;
        uint16_t family_id = 0;

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
        wifi_parse_attrs(attrs,
                         CTRL_ATTR_MAX,
                         (struct nlattr *)((char *)genlh + GENL_HDRLEN),
                         attr_len);
        if (attrs[CTRL_ATTR_FAMILY_ID] == NULL ||
            wifi_nla_payload_len(attrs[CTRL_ATTR_FAMILY_ID]) < (int)sizeof(family_id)) {
            continue;
        }
        memcpy(&family_id, wifi_nla_data(attrs[CTRL_ATTR_FAMILY_ID]), sizeof(family_id));
        info->family_id = (int)family_id;
        wifi_parse_mcast_groups(info, attrs[CTRL_ATTR_MCAST_GROUPS]);
        return 0;
    }
    errno = ENOENT;
    return -1;
}

static int wifi_get_family_info(int socket_fd,
                                const char *name,
                                struct wifi_nl80211_family_info *info) {
    const uint32_t seq = 100;

    if (wifi_send_genl(socket_fd, GENL_ID_CTRL, CTRL_CMD_GETFAMILY, 0, seq, name, 0, false, false) < 0) {
        return -1;
    }
    return wifi_recv_family_info(socket_fd, seq, info);
}

static const char *wifi_nl80211_cmd_name(int cmd) {
    switch (cmd) {
        case NL80211_CMD_CONNECT:
            return "CONNECT";
        case NL80211_CMD_DISCONNECT:
            return "DISCONNECT";
        case NL80211_CMD_NEW_SCAN_RESULTS:
            return "NEW_SCAN_RESULTS";
        case NL80211_CMD_SCAN_ABORTED:
            return "SCAN_ABORTED";
        case NL80211_CMD_ROAM:
            return "ROAM";
        default:
            return "OTHER";
    }
}

static bool wifi_nl80211_cmd_interesting(int cmd) {
    return cmd == NL80211_CMD_CONNECT ||
           cmd == NL80211_CMD_DISCONNECT ||
           cmd == NL80211_CMD_NEW_SCAN_RESULTS ||
           cmd == NL80211_CMD_SCAN_ABORTED ||
           cmd == NL80211_CMD_ROAM;
}

static int wifi_join_genl_group(int socket_fd, int group_id) {
    int group = group_id;

    if (group_id <= 0) {
        errno = ENOENT;
        return -1;
    }
    return setsockopt(socket_fd, SOL_NETLINK, NETLINK_ADD_MEMBERSHIP, &group, sizeof(group));
}

static void wifi_nl80211_store_event(struct wifi_nl80211_event_snapshot *out,
                                     int cmd,
                                     unsigned int ifindex,
                                     const char *iface) {
    struct wifi_nl80211_event *event;

    if (out == NULL) {
        return;
    }
    ++out->event_count;
    if (cmd == NL80211_CMD_CONNECT) {
        ++out->connect_event_count;
        if (out->first_connect_event_ms <= 0) {
            out->first_connect_event_ms = monotonic_millis();
        }
    }
    if (out->stored_count >= A90_WIFI_NL80211_EVENT_MAX_STORED) {
        return;
    }
    event = &out->events[out->stored_count++];
    memset(event, 0, sizeof(*event));
    event->cmd_id = cmd;
    event->ifindex = ifindex;
    event->monotonic_ms = monotonic_millis();
    snprintf(event->cmd, sizeof(event->cmd), "%s", wifi_nl80211_cmd_name(cmd));
    snprintf(event->iface, sizeof(event->iface), "%s",
             iface != NULL && iface[0] != '\0' ? iface : "unknown");
    a90_logf("wifi",
             "nl80211_event cmd=%s cmd_id=%d iface=%s ifindex=%u raw_bssid_redacted=1 raw_ip_redacted=1",
             event->cmd,
             event->cmd_id,
             event->iface,
             event->ifindex);
}

static void wifi_nl80211_parse_event(struct wifi_nl80211_event_snapshot *out,
                                     const struct nlmsghdr *nlh) {
    const struct genlmsghdr *genlh = (const struct genlmsghdr *)NLMSG_DATA(nlh);
    struct nlattr *attrs[NL80211_ATTR_MAX + 1];
    uint32_t ifindex = 0;
    char iface[IFNAMSIZ] = "unknown";
    int attr_len;

    if (genlh == NULL || !wifi_nl80211_cmd_interesting(genlh->cmd)) {
        return;
    }
    attr_len = (int)nlh->nlmsg_len - (int)NLMSG_LENGTH(sizeof(*genlh));
    if (attr_len < 0) {
        return;
    }
    wifi_parse_attrs(attrs,
                     NL80211_ATTR_MAX,
                     (struct nlattr *)((char *)genlh + GENL_HDRLEN),
                     attr_len);
    if (wifi_nla_u32(attrs[NL80211_ATTR_IFINDEX], &ifindex) == 0 &&
        if_indextoname(ifindex, iface) != NULL) {
        if (strcmp(iface, A90_WIFI_IFACE) != 0) {
            return;
        }
    }
    wifi_nl80211_store_event(out, (int)genlh->cmd, ifindex, iface);
}

static int wifi_nl80211_events_collect_with_start(int timeout_ms,
                                                  struct wifi_nl80211_event_snapshot *out,
                                                  const struct wifi_nl80211_event_start *start) {
    struct wifi_nl80211_family_info family_info;
    int fd;
    long started_ms;
    long deadline_ms;

    if (out == NULL) {
        return -EINVAL;
    }
    memset(out, 0, sizeof(*out));
    out->timeout_ms = timeout_ms;
    snprintf(out->decision, sizeof(out->decision), "%s", "wifi-events-unstarted");
    if (timeout_ms < 0 || timeout_ms > A90_WIFI_NL80211_EVENT_MAX_MS) {
        out->rc = -EINVAL;
        out->saved_errno = EINVAL;
        snprintf(out->decision, sizeof(out->decision), "%s", "wifi-events-invalid-timeout");
        return out->rc;
    }
    fd = wifi_open_genl_socket();
    if (fd < 0) {
        out->rc = -errno;
        out->saved_errno = errno;
        snprintf(out->decision, sizeof(out->decision), "%s", "wifi-events-socket-failed");
        return out->rc;
    }
    out->socket_open = 1;
    if (wifi_get_family_info(fd, "nl80211", &family_info) < 0) {
        out->rc = -errno;
        out->saved_errno = errno;
        snprintf(out->decision, sizeof(out->decision), "%s", "wifi-events-family-info-failed");
        (void)close(fd);
        return out->rc;
    }
    out->family_id = family_info.family_id;
    out->group_count = family_info.group_count;
    out->mlme_group_id = family_info.mlme_group_id;
    out->scan_group_id = family_info.scan_group_id;
    out->config_group_id = family_info.config_group_id;
    if (wifi_join_genl_group(fd, family_info.mlme_group_id) == 0) {
        out->mlme_joined = 1;
        ++out->groups_joined;
    } else {
        out->saved_errno = out->saved_errno == 0 ? errno : out->saved_errno;
    }
    if (wifi_join_genl_group(fd, family_info.scan_group_id) == 0) {
        out->scan_joined = 1;
        ++out->groups_joined;
    } else {
        out->saved_errno = out->saved_errno == 0 ? errno : out->saved_errno;
    }
    if (wifi_join_genl_group(fd, family_info.config_group_id) == 0) {
        out->config_joined = 1;
        ++out->groups_joined;
    } else {
        out->saved_errno = out->saved_errno == 0 ? errno : out->saved_errno;
    }
    if (out->groups_joined <= 0) {
        out->rc = -(out->saved_errno != 0 ? out->saved_errno : ENOENT);
        snprintf(out->decision, sizeof(out->decision), "%s", "wifi-events-subscribe-failed");
        (void)close(fd);
        return out->rc;
    }
    if (start != NULL && start->fn != NULL) {
        int start_rc = start->fn(start->ctx);

        if (start_rc < 0) {
            out->rc = start_rc;
            out->saved_errno = -start_rc;
            snprintf(out->decision, sizeof(out->decision), "%s", "wifi-events-start-failed");
            (void)close(fd);
            return out->rc;
        }
    }

    started_ms = monotonic_millis();
    deadline_ms = started_ms + timeout_ms;
    for (;;) {
        struct pollfd poll_fd;
        int wait_ms = (int)(deadline_ms - monotonic_millis());
        int poll_rc;
        char buffer[A90_WIFI_SCAN_RECV_SIZE];
        ssize_t received;
        struct nlmsghdr *nlh;
        int remaining;

        if (wait_ms < 0) {
            break;
        }
        memset(&poll_fd, 0, sizeof(poll_fd));
        poll_fd.fd = fd;
        poll_fd.events = POLLIN;
        poll_rc = poll(&poll_fd, 1, wait_ms);
        if (poll_rc == 0) {
            break;
        }
        if (poll_rc < 0) {
            if (errno == EINTR) {
                continue;
            }
            out->rc = -errno;
            out->saved_errno = errno;
            snprintf(out->decision, sizeof(out->decision), "%s", "wifi-events-poll-failed");
            (void)close(fd);
            return out->rc;
        }
        received = recv(fd, buffer, sizeof(buffer), 0);
        if (received < 0) {
            if (errno == EINTR) {
                continue;
            }
            out->rc = -errno;
            out->saved_errno = errno;
            snprintf(out->decision, sizeof(out->decision), "%s", "wifi-events-recv-failed");
            (void)close(fd);
            return out->rc;
        }
        for (nlh = (struct nlmsghdr *)buffer, remaining = (int)received;
             NLMSG_OK(nlh, remaining);
             nlh = NLMSG_NEXT(nlh, remaining)) {
            if (nlh->nlmsg_type == NLMSG_ERROR) {
                const struct nlmsgerr *err = (const struct nlmsgerr *)NLMSG_DATA(nlh);

                out->rc = err->error < 0 ? err->error : -EIO;
                out->saved_errno = err->error < 0 ? -err->error : EIO;
                snprintf(out->decision, sizeof(out->decision), "%s", "wifi-events-netlink-error");
                (void)close(fd);
                return out->rc;
            }
            if (nlh->nlmsg_type == (unsigned int)family_info.family_id) {
                wifi_nl80211_parse_event(out, nlh);
            }
        }
    }
    (void)close(fd);
    out->rc = 0;
    snprintf(out->decision,
             sizeof(out->decision),
             "%s",
             out->event_count > 0 ? "wifi-events-observed" : "wifi-events-timeout-no-events");
    return 0;
}

int a90_wifi_events_collect(int timeout_ms, struct wifi_nl80211_event_snapshot *out) {
    return wifi_nl80211_events_collect_with_start(timeout_ms, out, NULL);
}

static int wifi_connect_event_start_child(void *ctx) {
    struct wifi_connect_event_child *child = (struct wifi_connect_event_child *)ctx;
    int pipe_fds[2];
    pid_t pid;

    if (child == NULL) {
        return -EINVAL;
    }
    child->start_rc = 0;
    child->start_errno = 0;
    child->connect_rc = -EINPROGRESS;
    child->pipe_read = -1;
    child->pipe_write = -1;
    if (pipe(pipe_fds) < 0) {
        child->start_errno = errno;
        child->start_rc = -errno;
        return child->start_rc;
    }
    pid = fork();
    if (pid < 0) {
        child->start_errno = errno;
        child->start_rc = -errno;
        (void)close(pipe_fds[0]);
        (void)close(pipe_fds[1]);
        return child->start_rc;
    }
    if (pid == 0) {
        int rc;
        ssize_t written;

        (void)close(pipe_fds[0]);
        a90_console_silence_child();
        rc = a90_wifi_connect_profile(child->profile_name);
        written = write(pipe_fds[1], &rc, sizeof(rc));
        (void)close(pipe_fds[1]);
        if (written != (ssize_t)sizeof(rc)) {
            _exit(2);
        }
        _exit(rc == 0 ? 0 : 1);
    }
    (void)close(pipe_fds[1]);
    child->pid = pid;
    child->pipe_read = pipe_fds[0];
    child->pipe_write = -1;
    return 0;
}

static void wifi_connect_event_wait_child(struct wifi_connect_event_child *child) {
    long deadline_ms;

    if (child == NULL || child->pid <= 0) {
        return;
    }
    deadline_ms = monotonic_millis() + A90_WIFI_CONNECT_EVENT_CHILD_WAIT_MS;
    for (;;) {
        pid_t got = waitpid(child->pid, &child->child_status, WNOHANG);

        if (got == child->pid) {
            child->child_exited = 1;
            break;
        }
        if (got < 0) {
            if (errno == EINTR) {
                continue;
            }
            child->child_status = -errno;
            break;
        }
        if (monotonic_millis() >= deadline_ms) {
            child->child_timed_out = 1;
            (void)kill(child->pid, SIGKILL);
            (void)waitpid(child->pid, &child->child_status, 0);
            child->child_exited = 1;
            break;
        }
        usleep(100000);
    }
    if (child->pipe_read >= 0) {
        int rc = -EIO;
        ssize_t n = read(child->pipe_read, &rc, sizeof(rc));

        if (n == (ssize_t)sizeof(rc)) {
            child->connect_rc = rc;
        }
        (void)close(child->pipe_read);
        child->pipe_read = -1;
    }
    if (child->child_exited && WIFEXITED(child->child_status)) {
        child->child_exit_code = WEXITSTATUS(child->child_status);
    } else {
        child->child_exit_code = -1;
    }
    if (child->child_exited && WIFSIGNALED(child->child_status)) {
        child->child_signal = WTERMSIG(child->child_status);
    } else {
        child->child_signal = 0;
    }
}

static int wifi_connect_event_status_carrier_up(struct a90_wifi_status_snapshot *status) {
    if (status == NULL) {
        return 0;
    }
    return strcmp(status->carrier, "1") == 0 ? 1 : 0;
}

int a90_wifi_connect_event_once(const char *profile_name, int timeout_ms) {
    struct wifi_nl80211_event_snapshot snapshot;
    struct wifi_connect_event_child child;
    struct wifi_nl80211_event_start start;
    struct a90_wifi_status_snapshot status;
    int status_rc;
    int carrier_up;
    int carrier_match;
    int rc;
    int i;

    if (timeout_ms <= 0) {
        timeout_ms = A90_WIFI_CONNECT_EVENT_DEFAULT_MS;
    }
    memset(&child, 0, sizeof(child));
    child.profile_name = profile_name;
    child.pipe_read = -1;
    child.pipe_write = -1;
    start.fn = wifi_connect_event_start_child;
    start.ctx = &child;

    rc = wifi_nl80211_events_collect_with_start(timeout_ms, &snapshot, &start);
    wifi_connect_event_wait_child(&child);
    memset(&status, 0, sizeof(status));
    status_rc = a90_wifi_status_snapshot(&status);
    carrier_up = status_rc == 0 ? wifi_connect_event_status_carrier_up(&status) : 0;
    carrier_match = snapshot.connect_event_count > 0 && carrier_up ? 1 : 0;
    if (rc == 0 && (child.connect_rc != 0 || !carrier_match)) {
        rc = child.connect_rc != 0 ? child.connect_rc : -ENOLINK;
    }

    a90_console_printf("[wifi connect-event]\r\n");
    a90_console_printf("version=%s\r\n", A90_WIFI_CONNECT_EVENT_VERSION);
    a90_console_printf("profile=%s\r\n",
                       profile_name != NULL && profile_name[0] != '\0' ? profile_name : "default");
    a90_console_printf("timeout_ms=%d\r\n", snapshot.timeout_ms);
    a90_console_printf("event.socket_open=%d\r\n", snapshot.socket_open);
    a90_console_printf("event.family_id=%d\r\n", snapshot.family_id);
    a90_console_printf("event.group.mlme.joined=%d\r\n", snapshot.mlme_joined);
    a90_console_printf("event.group.scan.joined=%d\r\n", snapshot.scan_joined);
    a90_console_printf("event.group.config.joined=%d\r\n", snapshot.config_joined);
    a90_console_printf("event.groups_joined=%d\r\n", snapshot.groups_joined);
    a90_console_printf("event.count=%d\r\n", snapshot.event_count);
    a90_console_printf("event.connect_count=%d\r\n", snapshot.connect_event_count);
    a90_console_printf("event.stored_count=%d\r\n", snapshot.stored_count);
    a90_console_printf("event.first_connect_monotonic_ms=%ld\r\n", snapshot.first_connect_event_ms);
    for (i = 0; i < snapshot.stored_count; ++i) {
        const struct wifi_nl80211_event *event = &snapshot.events[i];

        a90_console_printf("event.%d.cmd=%s\r\n", i, event->cmd);
        a90_console_printf("event.%d.cmd_id=%d\r\n", i, event->cmd_id);
        a90_console_printf("event.%d.iface=%s\r\n", i, event->iface);
        a90_console_printf("event.%d.ifindex=%u\r\n", i, event->ifindex);
        a90_console_printf("event.%d.monotonic_ms=%ld\r\n", i, event->monotonic_ms);
    }
    a90_console_printf("connect.child_pid=%ld\r\n", (long)child.pid);
    a90_console_printf("connect.start_rc=%d\r\n", child.start_rc);
    a90_console_printf("connect.start_errno=%d\r\n", child.start_errno);
    a90_console_printf("connect.rc=%d\r\n", child.connect_rc);
    a90_console_printf("connect.child_exited=%d\r\n", child.child_exited);
    a90_console_printf("connect.child_exit_code=%d\r\n", child.child_exit_code);
    a90_console_printf("connect.child_signal=%d\r\n", child.child_signal);
    a90_console_printf("connect.child_timed_out=%d\r\n", child.child_timed_out);
    a90_console_printf("status.rc=%d\r\n", status_rc);
    a90_console_printf("status.wlan0_present=%d\r\n", status.wlan0_present ? 1 : 0);
    a90_console_printf("status.carrier=%s\r\n", status.carrier);
    a90_console_printf("carrier_up=%d\r\n", carrier_up);
    a90_console_printf("event_carrier_match=%d\r\n", carrier_match);
    a90_console_printf("raw_bssid_redacted=1\r\n");
    a90_console_printf("raw_ip_redacted=1\r\n");
    a90_console_printf("secret_values_logged=0\r\n");
    a90_console_printf("connect_attempted=1\r\n");
    a90_console_printf("dhcp_attempted=0\r\n");
    a90_console_printf("external_ping_attempted=0\r\n");
    a90_console_printf("cleanup_attempted=0\r\n");
    a90_console_printf("rc=%d\r\n", rc);
    a90_console_printf("event.rc=%d\r\n", snapshot.rc);
    a90_console_printf("event.saved_errno=%d\r\n", snapshot.saved_errno);
    a90_console_printf("event.decision=%s\r\n", snapshot.decision);
    a90_console_printf("decision=%s\r\n",
                       rc == 0 && carrier_match ? "wifi-connect-event-carrier-match" :
                       snapshot.connect_event_count > 0 ? "wifi-connect-event-carrier-mismatch" :
                       "wifi-connect-event-missing-connect");
    a90_logf("wifi",
             "connect_event profile=%s rc=%d connect_rc=%d connect_events=%d carrier=%d secret_values_logged=0",
             profile_name != NULL && profile_name[0] != '\0' ? profile_name : "default",
             rc,
             child.connect_rc,
             snapshot.connect_event_count,
             carrier_up);
    return rc;
}

int a90_wifi_events_once(int timeout_ms) {
    struct wifi_nl80211_event_snapshot snapshot;
    int rc;
    int i;

    rc = a90_wifi_events_collect(timeout_ms, &snapshot);
    a90_console_printf("[wifi events]\r\n");
    a90_console_printf("version=%s\r\n", A90_WIFI_NL80211_EVENTS_VERSION);
    a90_console_printf("monitor=nl80211\r\n");
    a90_console_printf("groups=mlme,scan,config\r\n");
    a90_console_printf("timeout_ms=%d\r\n", snapshot.timeout_ms);
    a90_console_printf("socket_open=%d\r\n", snapshot.socket_open);
    a90_console_printf("family_id=%d\r\n", snapshot.family_id);
    a90_console_printf("mcast_group_count=%d\r\n", snapshot.group_count);
    a90_console_printf("group.mlme.id=%d\r\n", snapshot.mlme_group_id);
    a90_console_printf("group.mlme.joined=%d\r\n", snapshot.mlme_joined);
    a90_console_printf("group.scan.id=%d\r\n", snapshot.scan_group_id);
    a90_console_printf("group.scan.joined=%d\r\n", snapshot.scan_joined);
    a90_console_printf("group.config.id=%d\r\n", snapshot.config_group_id);
    a90_console_printf("group.config.joined=%d\r\n", snapshot.config_joined);
    a90_console_printf("groups_joined=%d\r\n", snapshot.groups_joined);
    a90_console_printf("event_count=%d\r\n", snapshot.event_count);
    a90_console_printf("stored_count=%d\r\n", snapshot.stored_count);
    a90_console_printf("raw_bssid_redacted=1\r\n");
    a90_console_printf("raw_ip_redacted=1\r\n");
    a90_console_printf("secret_values_logged=0\r\n");
    a90_console_printf("scan_attempted=0\r\n");
    a90_console_printf("connect_attempted=0\r\n");
    a90_console_printf("dhcp_attempted=0\r\n");
    a90_console_printf("external_ping_attempted=0\r\n");
    for (i = 0; i < snapshot.stored_count; ++i) {
        const struct wifi_nl80211_event *event = &snapshot.events[i];

        a90_console_printf("event.%d.cmd=%s\r\n", i, event->cmd);
        a90_console_printf("event.%d.cmd_id=%d\r\n", i, event->cmd_id);
        a90_console_printf("event.%d.iface=%s\r\n", i, event->iface);
        a90_console_printf("event.%d.ifindex=%u\r\n", i, event->ifindex);
        a90_console_printf("event.%d.monotonic_ms=%ld\r\n", i, event->monotonic_ms);
    }
    a90_console_printf("rc=%d\r\n", snapshot.rc);
    a90_console_printf("saved_errno=%d\r\n", snapshot.saved_errno);
    a90_console_printf("decision=%s\r\n", snapshot.decision);
    a90_logf("wifi",
             "events decision=%s rc=%d family_id=%d groups_joined=%d events=%d stored=%d timeout_ms=%d",
             snapshot.decision,
             snapshot.rc,
             snapshot.family_id,
             snapshot.groups_joined,
             snapshot.event_count,
             snapshot.stored_count,
             snapshot.timeout_ms);
    return rc;
}
