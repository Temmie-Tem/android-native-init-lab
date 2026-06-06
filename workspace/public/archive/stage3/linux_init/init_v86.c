/*
 * A90 native init v86.
 *
 * This version is the KMS/draw API extraction after v85.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v86/00_prelude.inc.c"
#include "v86/10_core_log_console.inc.c"
#include "v86/20_device_display.inc.c"
#include "v86/30_status_hud.inc.c"
#include "v86/40_menu_apps.inc.c"
#include "v86/50_boot_services.inc.c"
#include "v86/60_shell_basic_commands.inc.c"
#include "v86/70_storage_android_net.inc.c"
#include "v86/80_shell_dispatch.inc.c"
#include "v86/90_main.inc.c"
