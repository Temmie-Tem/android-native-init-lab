/*
 * A90 native init v123.
 *
 * This version hardens Batch 1 root-control surfaces: tcpctl auth/bind,
 * service dangerous gating, and reconnect cleanup fail-closed behavior.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v123/00_prelude.inc.c"
#include "v123/10_core_log_console.inc.c"
#include "v123/20_device_display.inc.c"
#include "v123/30_status_hud.inc.c"
#include "v123/40_menu_apps.inc.c"
#include "v123/50_boot_services.inc.c"
#include "v123/60_shell_basic_commands.inc.c"
#include "v123/70_storage_android_net.inc.c"
#include "v123/80_shell_dispatch.inc.c"
#include "v123/90_main.inc.c"
