/* Fixed continuation of one native-first installed-Debian boot. */
#ifndef S22PLUS_DEBIAN_HANDOFF_V1_H
#define S22PLUS_DEBIAN_HANDOFF_V1_H
#define DH_CONTINUE 39U
#define DH_CONTINUE_ACK 171U
#define DH_INIT_PROOF 172U
#define DH_RELEASE 40U
#define DH_RELEASE_ACK 173U
#define DH_STATE_TAG 174U
#define DH_STATE_PATH "/run/s22-debian/state"
#define DH_HOOK_PATH "/run/s22-debian/hook"
struct dh_state {
    struct sw_state native;
    uint8_t hook_sha[32],tag[32];
};
_Static_assert(sizeof(struct dh_state)==448,"Debian hook state ABI");
#endif
