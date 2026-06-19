#include "a90_changelog.h"

#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#define ENTRY(label, summary, d1, d2, d3, d4, d5) \
    { label, summary, { d1, d2, d3, d4, d5 } }

static const struct a90_changelog_entry changelog_entries[] = {
    ENTRY("0.10.15 v2849", "AUDIO STATUS PRODUCTIZATION",
          "0.10.15 v2849 AUDIO STATUS PRODUCTIZATION",
          "Adds read-only audio productization markers to audio status",
          "Shows latest proven audio run, version, and build tag in screen status",
          "Records boot-chime and stop-execute validation provenance",
          "Keeps mixer, PCM, SET-cal, route, and smart-amp behavior unchanged"),
    ENTRY("0.10.14 v2847", "AUDIO STOP EXECUTE",
          "0.10.14 v2847 AUDIO STOP EXECUTE",
          "Adds bounded audio stop internal-speaker-safe --execute cleanup",
          "Resets the proven core route without touching smart-amp gain or boost",
          "Reports no-active PCM and SET-cal state before cleanup",
          "Rollback target remains v2321 after live validation"),
    ENTRY("0.10.13 v2845", "AUDIO BOOT CHIME",
          "0.10.13 v2845 AUDIO BOOT CHIME",
          "Adds compile-time gated best-effort PID1 boot chime autoplay",
          "Uses the bundled SET-cal and bounded chime preset path",
          "Runs without host artifact deployment or manual audio command",
          "Keeps amplitude and duration inside the proven safe cap"),
    ENTRY("0.10.12 v2843", "AUDIO BUNDLED SETCAL",
          "0.10.12 v2843 AUDIO BUNDLED SETCAL",
          "Bundles the private SET-cal manifest and payload package into the ramdisk",
          "Lets native audio chime replay calibration without host-side deployment",
          "Preserves private raw payload handling outside public source",
          "Keeps rollback to v2321 after each live playback validation"),
    ENTRY("0.10.11 v2840", "AUDIO CHIME SCREEN",
          "0.10.11 v2840 AUDIO CHIME SCREEN",
          "Adds display-only screenapp audio-chime and APPS/AUDIO CHIME surfaces",
          "Describes the known-good chime preset without starting playback",
          "Keeps the proven audio play path as the execution backend",
          "Separates readable operation from mixer or PCM mutation"),
    ENTRY("0.10.10 v2838", "AUDIO CHIME PRESET",
          "0.10.10 v2838 AUDIO CHIME PRESET",
          "Adds manual audio chime preset over the proven audio play route",
          "Uses bounded duration and low amplitude for audible confirmation",
          "Reuses ADSP, SET-cal, route, PCM, and cleanup stages",
          "Maintains the speaker-protection safety cap"),
    ENTRY("0.10.9 v2835", "AUDIO HELP SURFACE",
          "0.10.9 v2835 AUDIO HELP SURFACE",
          "Updates help and cmdmeta verbose with current audio subcommands",
          "Keeps screenapp audio status, profile, stages, map, and chime discoverable",
          "Preserves read-only command metadata for host automation",
          "Does not add new playback or route writes"),
    ENTRY("0.10.0 v2812", "AUDIO CORE PROMOTION",
          "0.10.0 v2812 AUDIO CORE PROMOTION",
          "Promotes native audio play core after on-device audible proof",
          "Integrates ADSP, snd nodes, App Type, SET-cal, route, PCM, and cleanup",
          "Keeps the rollback net at v2321 after validation",
          "Marks audio as a first-class native-init feature track"),
    ENTRY("0.9.68 v724", "QRTR SERVICE-LOCATOR BOOT PROOF",
          "0.9.68 v724 QRTR SERVICE-LOCATOR BOOT PROOF",
          "Adds opt-in post-ACM QRTR/service-locator lower companion proof",
          "Starts only qrtr-ns, pd-mapper, rmt_storage, and tftp_server",
          "Spawns helper out-of-line so PID1 returns to shell without waiting",
          "Keeps CNSS daemon, Wi-Fi HAL, scan/connect, credentials, and external ping blocked"),
    ENTRY("0.9.67 v641", "FIRMWARE-BACKED SIBLING SSCTL PROOF",
          "0.9.67 v641 FIRMWARE-BACKED SIBLING SSCTL PROOF",
          "Mounts apnhlos and modem firmware surfaces read-only before proof",
          "Reuses one-shot arm flag and per-node timeout/reap handling",
          "Stops proof on firmware mount failure but continues to shell",
          "Keeps Wi-Fi HAL, scan/connect, credentials, and external ping blocked"),
    ENTRY("0.9.66 v631", "PER-NODE SIBLING SSCTL PROOF",
          "0.9.66 v631 PER-NODE SIBLING SSCTL PROOF",
          "Splits ADSP/CDSP/SLPI boot-node proof into independent child attempts",
          "Logs per-node status, timeout, and reap result before continuing",
          "Stops only if a timed-out child cannot be reaped safely",
          "Keeps Wi-Fi HAL, qcwlanstate, scan/connect, credentials, and external ping blocked"),
    ENTRY("0.9.65 v630", "SIBLING SSCTL BOOT-WINDOW PROOF",
          "0.9.65 v630 SIBLING SSCTL BOOT-WINDOW PROOF",
          "Adds opt-in one-shot ADSP/CDSP/SLPI sibling SSCTL proof",
          "Runs only after USB ACM console attach and removes the arm flag first",
          "Uses forked child timeout so PID1 continues to shell on failure",
          "Keeps Wi-Fi HAL, qcwlanstate, scan/connect, credentials, and external ping blocked"),
    ENTRY("0.9.61 v319", "SERIAL TRANSFER APPEND",
          "0.9.61 v319 SERIAL TRANSFER APPEND",
          "Adds bounded appendfile command for ACM serial transfer staging",
          "Expands cmdv1x decode buffer and shell line size to 4096 bytes",
          "Keeps appendfile scoped to A90 runtime/cache/temp workspaces",
          "Prepares private property namespace proof without toybox sh pipelines"),
    ENTRY("0.9.60 v261", "PID1 ORPHAN REAPER",
          "0.9.60 v261 PID1 ORPHAN REAPER",
          "Adds PID1 waitpid(-1) orphan/zombie reap polling",
          "Blocks future CNSS start-only retries when process-table residue exists",
          "Adds reaper command and pid1guard summary coverage",
          "Prepares clean-state validation before QRTR/QMI probing"),
    ENTRY("0.9.59 v159", "TRACEFS FEASIBILITY",
          "0.9.59 v159 TRACEFS FEASIBILITY",
          "Adds read-only tracefs and ftrace feasibility command",
          "Reports tracefs/debugfs support, mount state, current tracer, and readable samples",
          "Adds tracefs summary to status and bootstatus",
          "Keeps tracefs mount, tracing_on, and current_tracer writes disabled"),
    ENTRY("0.9.58 v158", "WATCHDOG FEASIBILITY",
          "0.9.58 v158 WATCHDOG FEASIBILITY",
          "Adds read-only watchdog inventory command",
          "Reports watchdog class devices, readable sysfs attributes, and device node presence",
          "Adds watchdog summary to status and bootstatus",
          "Keeps /dev/watchdog* stat-only and never opens watchdog devices"),
    ENTRY("0.9.57 v157", "PSTORE FEASIBILITY",
          "0.9.57 v157 PSTORE FEASIBILITY",
          "Adds read-only pstore and ramoops feasibility command",
          "Reports pstore filesystem support, mount state, entries, and ramoops hints",
          "Adds pstore summary to status and bootstatus",
          "Keeps pstore mount and reboot persistence tests opt-in for later"),
    ENTRY("0.9.56 v156", "THERMAL POWER MAP",
          "0.9.56 v156 THERMAL POWER MAP",
          "Adds read-only thermal and power sensor map command",
          "Reports thermal zones, trip points, cooling devices, and power supplies",
          "Adds sensormap summary to status and bootstatus",
          "Prepares long-run stability analysis with named sensors"),
    ENTRY("0.9.55 v155", "KERNEL DIAG BUNDLE",
          "0.9.55 v155 KERNEL DIAG BUNDLE",
          "Adds host kernel diagnostics evidence bundle",
          "Captures kernelinv, diag, longsoak, exposure, wifiinv, and wififeas",
          "Keeps pstore, tracefs, watchdog, Wi-Fi, and network controls read-only",
          "Prepares evidence for thermal, pstore, watchdog, and tracefs decisions"),
    ENTRY("0.9.54 v154", "KERNEL INVENTORY",
          "0.9.54 v154 KERNEL INVENTORY",
          "Adds read-only kernel capability inventory command",
          "Reports config.gz, filesystems, mounts, cgroup, pstore, and tracefs",
          "Maps thermal, power_supply, watchdog, and USB gadget presence",
          "Keeps pstore, tracefs, watchdog, and network controls read-only"),
    ENTRY("0.9.53 v153", "LONGSOAK SECURITY",
          "0.9.53 v153 LONGSOAK SECURITY",
          "Adds bounded device-owned longsoak export",
          "Hardens longsoak helper log writes against symlink clobber",
          "Makes host long soak evidence bundle private",
          "Removes host cat of device-provided longsoak paths"),
    ENTRY("0.9.52 v152", "POWER THERMAL TREND",
          "0.9.52 v152 POWER THERMAL TREND",
          "Adds device JSONL trend analysis to long soak report",
          "Summarizes battery, power, thermal, memory, load, and uptime ranges",
          "Extends bundle inputs with trend-enriched correlation JSON",
          "Keeps recorder format backward-compatible"),
    ENTRY("0.9.51 v151", "LONG SOAK BUNDLE",
          "0.9.51 v151 LONG SOAK BUNDLE",
          "Adds host bundle for long soak evidence files",
          "Collects status, bootstatus, timeline, and log path transcripts",
          "Bundles correlation and disconnect classifier outputs",
          "Prepares handoff-ready soak artifacts"),
    ENTRY("0.9.50 v150", "HOST DISCONNECT CLASSIFIER",
          "0.9.50 v150 HOST DISCONNECT CLASSIFIER",
          "Adds host-side ACM/NCM reachability classifier",
          "Separates bridge, serial, NCM, and device recorder evidence",
          "Writes JSON and Markdown disconnect reports",
          "Keeps device-side longsoak supervisor behavior unchanged"),
    ENTRY("0.9.49 v149", "LONG SOAK SUPERVISOR",
          "0.9.49 v149 LONG SOAK SUPERVISOR",
          "Adds recorder health and stale-sample detection",
          "Reports longsoak health in status and bootstatus",
          "Adds longsoak selftest warning coverage",
          "Keeps host/device correlation workflow unchanged"),
    ENTRY("0.9.48 v148", "LONG SOAK CORRELATION",
          "0.9.48 v148 LONG SOAK CORRELATION",
          "Adds host/device long soak report tool",
          "Exports device recorder JSONL through host harness",
          "Checks host failures and device sequence continuity",
          "Prepares overnight soak evidence workflow"),
    ENTRY("0.9.47 v147", "LONG SOAK STATUS",
          "0.9.47 v147 LONG SOAK STATUS",
          "Adds longsoak status snapshot API",
          "Adds sample count and last-record summary",
          "Shows longsoak summary in status and bootstatus",
          "Adds host summary JSON for long soak observations"),
    ENTRY("0.9.46 v146", "LONG SOAK FOUNDATION",
          "0.9.46 v146 LONG SOAK FOUNDATION",
          "Adds device-side long soak recorder helper",
          "Adds longsoak shell/service control",
          "Adds host long soak observation harness",
          "Keeps recorder alive across host disconnects"),
    ENTRY("0.9.45 v145", "INPUT CANCEL HARNESS",
          "0.9.45 v145 INPUT CANCEL HARNESS",
          "Adds host validation for waitkey q cancel path",
          "Adds host validation for waitgesture q cancel path",
          "Keeps blocking input commands cancel-safe before network work",
          "Preserves v144 inputmonitor foreground app behavior"),
    ENTRY("0.9.44 v144", "INPUTMON APP API",
          "0.9.44 v144 INPUTMON APP API",
          "Moves inputmonitor foreground command loop into inputmon app module",
          "Keeps HUD stop and restore as small lifecycle callbacks",
          "Reduces auto-HUD include-tree foreground app residue",
          "Preserves inputmonitor raw and gesture UI behavior"),
    ENTRY("0.9.43 v143", "INPUT COMMAND API",
          "0.9.43 v143 INPUT COMMAND API",
          "Moves waitkey command handler into input command module",
          "Moves waitgesture command handler into input command module",
          "Moves inputlayout command handler into input command module",
          "Preserves inputmonitor foreground HUD lifecycle"),
    ENTRY("0.9.42 v142", "CUTOUT APP API",
          "0.9.42 v142 CUTOUT APP API",
          "Moves cutout calibration state into displaytest module",
          "Moves cutout key event handling into app API",
          "Keeps displaytest/cutout UX unchanged",
          "Preserves v141 renderer split"),
    ENTRY("0.9.41 v141", "LOG NETWORK APP API",
          "0.9.41 v141 LOG NETWORK APP API",
          "Moves LOG summary renderer into a module",
          "Moves NETWORK summary renderer into a module",
          "Keeps menu routing unchanged",
          "Preserves v140 cpustress baseline"),
    ENTRY("0.9.40 v140", "CPUSTRESS APP API",
          "0.9.40 v140 CPUSTRESS APP API",
          "Moves CPU stress app lifecycle into a module",
          "Keeps screen menu stress UX unchanged",
          "Keeps helper process-group cleanup policy",
          "Preserves v139 controller behavior"),
    ENTRY("0.9.39 v139", "AUTOHUD CONTROLLER",
          "0.9.39 v139 AUTOHUD CONTROLLER",
          "Groups auto-HUD loop state",
          "Centralizes menu/app transitions",
          "Keeps menu UX unchanged",
          "Preserves v138 soak baseline"),
    ENTRY("0.9.38 v138", "EXTENDED SOAK",
          "0.9.38 v138 EXTENDED SOAK",
          "Adds release-candidate soak harness",
          "Repeats integrated safety gates",
          "Records long-running validation evidence",
          "Keeps runtime behavior unchanged"),
    ENTRY("0.9.37 v137", "VALIDATION MATRIX",
          "0.9.37 v137 VALIDATION MATRIX",
          "Adds integrated validation harness",
          "Covers selftest/pid1guard/exposure",
          "Covers policy/service/network status",
          "Keeps runtime behavior unchanged"),
    ENTRY("0.9.36 v136", "STRUCTURE AUDIT 3",
          "0.9.36 v136 STRUCTURE AUDIT 3",
          "Post-v135 module ownership and duplicate policy audit checkpoint.",
          "No new network exposure or user-facing runtime feature added.",
          "Records keep/split/merge candidates",
          "Reserves v137 for validation matrix expansion"),
    ENTRY("0.9.35 v135", "POLICY MATRIX",
          "0.9.35 v135 POLICY MATRIX",
          "Adds policycheck command",
          "Checks menu command allowlist",
          "Checks power page command policy",
          "Covers side-effect subcommands"),
    ENTRY("0.9.34 v134", "EXPOSURE GUARDRAIL",
          "0.9.34 v134 EXPOSURE GUARDRAIL",
          "Adds exposure status command",
          "Reports ACM/NCM/tcpctl/rshell boundary",
          "Adds exposure section to diag",
          "Keeps network services opt-in"),
    ENTRY("0.9.33 v133", "CHANGELOG SERIES",
          "0.9.33 v133 CHANGELOG SERIES",
          "Groups changelog by version series",
          "Adds 0.9.x/0.8.x/older menus",
          "Keeps shared changelog table",
          "Preserves detail page renderer"),
    ENTRY("0.9.32 v132", "CHANGELOG CLEANUP",
          "0.9.32 v132 CHANGELOG CLEANUP",
          "Removes legacy changelog enums",
          "Removes per-version draw functions",
          "Keeps shared changelog table only",
          "Confirms v131 hold UX"),
    ENTRY("0.9.31 v131", "MENU HOLD TIMER",
          "0.9.31 v131 MENU HOLD TIMER",
          "Adds timer-based hold scrolling",
          "Removes dependency on EV_KEY repeat",
          "Keeps VOL+DN physical back",
          "Keeps v130 menu hints"),
    ENTRY("0.9.30 v130", "MENU HOLD BACK",
          "0.9.30 v130 MENU HOLD BACK",
          "Adds hold-repeat volume scrolling",
          "Adds volume combo physical back",
          "Clarifies menu/about footer hints",
          "Keeps v129 changelog paging"),
    ENTRY("0.9.29 v129", "CHANGELOG PAGING",
          "0.9.29 v129 CHANGELOG PAGING",
          "Shares changelog list data",
          "Adds ABOUT page navigation",
          "Keeps button UX stable",
          "Prepares long history growth"),
    ENTRY("0.9.28 v128", "MENU SUBCOMMAND POLICY",
          "Keeps v127 busy-gate mitigation",
          "Allows read-only subcommands",
          "Blocks mutation while menu visible",
          "Adds subcommand-aware controller API",
          NULL),
    ENTRY("0.9.27 v127", "MENU BUSY GATE",
          "Closes F023 busy-gate gap",
          "Uses deny-by-default menu policy",
          "Allows observation commands only",
          "Blocks run/write/mount/mknod paths",
          NULL),
    ENTRY("0.9.26 v126", "SECURITY BATCH6",
          "Keeps retained-source compatibility",
          "Fixes v84 changelog route",
          "Restores v42 run stdin behavior",
          "Adds strict input event validation",
          NULL),
    ENTRY("0.9.25 v125", "SECURITY BATCH4",
          "Uses owner-only diagnostics/logs",
          "Adds private emergency log fallback",
          "Makes HUD log tail opt-in",
          "Reduces passive display leakage",
          NULL),
    ENTRY("0.9.24 v124", "SECURITY BATCH2",
          "Verifies runtime helper SHA-256",
          "Adds no-follow storage/log writes",
          "Adds mountsd SD identity gate",
          "Makes tcpctl install fail closed",
          NULL),
    ENTRY("0.9.23 v123", "SECURITY BATCH1",
          "Requires tcpctl token auth",
          "Binds tcpctl to NCM device IP",
          "Moves tcpctl helper to ramdisk",
          "Marks service mutation dangerous",
          NULL),
    ENTRY("0.9.22 v122", "WIFI REFRESH",
          "Adds wifiinv refresh summary",
          "Adds wififeas refresh summary",
          "Compares v103/v104 baselines",
          "Keeps Wi-Fi bring-up blocked",
          NULL),
    ENTRY("0.9.21 v121", "PID1 GUARD",
          "Adds a90_pid1_guard.c/h",
          "Adds pid1guard shell command",
          "Adds status/bootstatus summary",
          "Runs guard during boot splash",
          NULL),
    ENTRY("0.9.20 v120", "COMMAND GROUP API",
          "Adds command group enum",
          "Adds command table metadata",
          "Adds cmdgroups inventory command",
          "Keeps command handlers in place",
          NULL),
    ENTRY("0.9.19 v119", "MENU ROUTE API",
          "Adds menu action route helper",
          "Removes long changelog case block",
          "Fixes top changelog app category",
          "Preserves screenmenu behavior",
          NULL),
    ENTRY("0.9.18 v118", "SHELL META API",
          "Adds shell metadata helpers",
          "Adds cmdmeta command inventory",
          "Formats command flags consistently",
          "Keeps dispatch logic stable",
          NULL),
    ENTRY("0.9.17 v117", "PID1 SLIM ROADMAP",
          "Records v117-v122 guardrails",
          "Sets PID1 slim roadmap baseline",
          "Keeps verified boot path stable",
          "Prepares Wi-Fi refresh phase",
          NULL),
    ENTRY("0.9.16 v116", "DIAG BUNDLE 2",
          "Extends diagnostics evidence",
          "Captures runtime/helper/service state",
          "Adds network and rshell evidence",
          "Improves host bundle collection",
          NULL),
    ENTRY("0.9.15 v115", "RSHELL HARDENING",
          "Adds rshell audit view",
          "Uses 0600 token state",
          "Rejects invalid tokens",
          "Validates NCM smoke rollback",
          NULL),
    ENTRY("0.9.14 v114", "HELPER DEPLOY 2",
          "Improves helper deployment visibility",
          "Records manifest and plan paths",
          "Keeps runtime helper fallback",
          "Adds deploy log evidence",
          NULL),
    ENTRY("0.9.13 v113", "RUNTIME PACKAGE LAYOUT",
          "Defines package-friendly runtime paths",
          "Documents helper manifest contract",
          "Keeps SD/cache fallback behavior",
          "Prepares userland packaging",
          NULL),
    ENTRY("0.9.12 v112", "USB SERVICE SOAK",
          "Runs opt-in NCM/tcpctl soak",
          "Verifies host ping/TCP control",
          "Checks ACM rollback",
          "Confirms USB service recovery",
          NULL),
    ENTRY("0.9.11 v111", "EXTENDED SOAK RC",
          "Runs 10-cycle host soak",
          "Checks final service state",
          "Checks final selftest state",
          "Preserves recovery-friendly baseline",
          NULL),
    ENTRY("0.9.10 v110", "APP CONTROLLER CLEANUP",
          "Moves auto-menu IPC helpers",
          "Centralizes menu state policy",
          "Keeps app routing behavior",
          "Prepares shell/controller split",
          NULL),
    ENTRY("0.9.9 v109", "STRUCTURE AUDIT 2",
          "Audits post-v108 boundaries",
          "Records next cleanup targets",
          "Keeps verified source layout",
          "No user-visible feature change",
          NULL),
    ENTRY("0.9.8 v108", "APP INPUTMON API",
          "Splits input monitor app",
          "Keeps raw/gesture trace UI",
          "Preserves button regression tests",
          "Completes UI app split cycle",
          NULL),
    ENTRY("0.9.7 v107", "APP DISPLAYTEST API",
          "Splits display test app",
          "Keeps colors/font/safe pages",
          "Keeps cutout calibration path",
          "Preserves visual regression tests",
          NULL),
    ENTRY("0.9.6 v106", "APP ABOUT API",
          "Splits ABOUT app renderer",
          "Adds a90_app_about.c/h",
          "Moves version/changelog screens",
          "Keeps app controller stable",
          NULL),
    ENTRY("0.9.5 v105", "SOAK RC",
          "Adds native soak validator",
          "Runs recovery-friendly baseline",
          "Keeps Wi-Fi active bring-up blocked",
          "Completes v96-v105 long plan",
          NULL),
    ENTRY("0.9.4 v104", "WIFI FEASIBILITY",
          "Adds Wi-Fi feasibility gate",
          "Compares current evidence",
          "Keeps bring-up no-go by default",
          "Documents missing kernel-facing gates",
          NULL),
    ENTRY("0.9.3 v103", "WIFI INVENTORY",
          "Adds read-only WLAN inventory",
          "Captures firmware/rfkill paths",
          "Avoids active Wi-Fi mutation",
          "Builds baseline evidence",
          NULL),
    ENTRY("0.9.2 v102", "DIAGNOSTICS",
          "Adds diagnostics module",
          "Adds host diag collection",
          "Collects read-only evidence",
          "Improves troubleshooting bundle",
          NULL),
    ENTRY("0.9.1 v101", "SERVICE MANAGER",
          "Adds service command view",
          "Tracks autohud/tcpctl/adbd/rshell",
          "Adds common service metadata",
          "Preserves manual controls",
          NULL),
    ENTRY("0.9.0 v100", "REMOTE SHELL",
          "Adds token-auth TCP rshell",
          "Runs over USB NCM",
          "Adds host smoke helper",
          "Keeps disabled unless started",
          NULL),
    ENTRY("0.8.29 v98", "HELPER DEPLOY",
          "Adds helper inventory",
          "Tracks preferred/fallback helpers",
          "Documents manifest path",
          "Keeps ramdisk helper fallback",
          NULL),
    ENTRY("0.8.28 v97", "SD RUNTIME ROOT",
          "Adds SD runtime root contract",
          "Keeps cache fallback",
          "Creates runtime directory layout",
          "Adds runtime command",
          NULL),
    ENTRY("0.8.27 v96", "STRUCTURE AUDIT",
          "Audits v95 module boundaries",
          "Fixes stale console markers",
          "Records cleanup plan",
          "No user-visible feature change",
          NULL),
    ENTRY("0.8.26 v95", "NETSERVICE USB API",
          "Splits USB gadget helpers",
          "Splits netservice policy",
          "Preserves ACM/NCM UX",
          "Keeps tcpctl helper path",
          NULL),
    ENTRY("0.8.25 v94", "BOOT SELFTEST",
          "Adds boot selftest API",
          "Runs non-destructive checks",
          "Surfaces pass/warn/fail summary",
          "Keeps boot warn-only",
          NULL),
    ENTRY("0.8.24 v93", "STORAGE API",
          "Splits storage API",
          "Tracks SD/cache backend",
          "Preserves mountsd command",
          "Keeps critical partition guardrails",
          NULL),
    ENTRY("0.8.23 v92", "SHELL CONTROLLER",
          "Splits shell metadata",
          "Splits controller policy",
          "Keeps command handlers in tree",
          "Preserves screenmenu behavior",
          NULL),
    ENTRY("0.8.22 v91", "CPUSTRESS HELPER",
          "Moves CPU stress outside PID1",
          "Adds static helper process",
          "Uses run API cancellation",
          "Keeps menu stress UX",
          NULL),
    ENTRY("0.8.21 v90", "METRICS API",
          "Splits metrics snapshot API",
          "Moves battery/CPU/GPU/MEM reads",
          "Keeps HUD display behavior",
          "Preserves stress telemetry",
          NULL),
    ENTRY("0.8.20 v89", "MENU CONTROL API",
          "Splits menu model/state",
          "Makes screenmenu nonblocking",
          "Keeps blindmenu foreground rescue",
          "Preserves app routing",
          NULL),
    ENTRY("0.8.19 v88", "HUD API",
          "Splits HUD renderer",
          "Moves boot splash/log tail drawing",
          "Keeps display/menu UX",
          "Prepares menu split",
          NULL),
    ENTRY("0.8.18 v87", "INPUT API",
          "Splits physical input API",
          "Moves gesture decoder",
          "Keeps button menu actions",
          "Improves boot summary time",
          NULL),
    ENTRY("0.8.17 v86", "KMS DRAW API",
          "Splits KMS framebuffer API",
          "Splits draw primitives",
          "Keeps HUD/menu logic",
          "Preserves display tests",
          NULL),
    ENTRY("0.8.16 v85", "RUN SERVICE API",
          "Splits run/service lifecycle",
          "Tracks service PIDs centrally",
          "Reduces zombie/stale PID risk",
          "Keeps command UX",
          NULL),
    ENTRY("0.8.15 v84", "CMDPROTO API",
          "Splits cmdv1/cmdv1x protocol",
          "Keeps shell dispatch in tree",
          "Preserves framed host result",
          "Keeps raw reboot controls",
          NULL),
    ENTRY("0.8.14 v83", "CONSOLE API",
          "Splits console fd handling",
          "Moves attach/readline/cancel",
          "Hides raw console fd",
          "Preserves serial bridge UX",
          NULL),
    ENTRY("0.8.13 v82", "LOG TIMELINE API",
          "Splits log module",
          "Splits boot timeline module",
          "Preserves logpath/timeline commands",
          "Keeps SD/cache log fallback",
          NULL),
    ENTRY("0.8.12 v81", "CONFIG UTIL API",
          "Splits config/util base",
          "Keeps PID1 single binary",
          "Prepares module boundaries",
          "No user-visible feature change",
          NULL),
    ENTRY("0.8.11 v80", "SOURCE MODULES",
          "Splits PID1 source includes",
          "Keeps one static init binary",
          "Improves source navigation",
          "Prepares compiled modules",
          NULL),
    ENTRY("0.8.10 v79", "BOOT SD PROBE",
          "Adds SD boot health check",
          "Uses SD runtime when healthy",
          "Falls back to cache when needed",
          "Shows storage warning",
          NULL),
    ENTRY("0.8.9 v78", "SD WORKSPACE",
          "Adds ext4 SD workspace",
          "Adds mountsd command",
          "Keeps cache fallback",
          "Avoids main storage experiments",
          NULL),
    ENTRY("0.8.8 v77", "DISPLAY TEST PAGES",
          "Splits display test pages",
          "Adds color/font/safe previews",
          "Adds cutout calibration",
          "Improves visual testing",
          NULL),
    ENTRY("0.8.7 v76", "AT FRAGMENT FILTER",
          "Filters serial AT fragments",
          "Reduces unknown command noise",
          "Keeps shell command behavior",
          "Improves bridge readability",
          NULL),
    ENTRY("0.8.6 v75", "QUIET IDLE REATTACH",
          "Suppresses idle reattach spam",
          "Keeps requested reattach logs",
          "Improves HUD log tail signal",
          "Preserves serial recovery",
          NULL),
    ENTRY("0.8.5 v74", "CMDV1 ARG ENCODING",
          "Adds cmdv1x argv encoding",
          "Supports whitespace arguments",
          "Keeps cmdv1 compatibility",
          "Improves host wrapper safety",
          NULL),
    ENTRY("0.8.4 v73", "CMDV1 PROTOCOL",
          "Adds A90P1 framed results",
          "Reports rc/status/duration",
          "Improves host verification",
          "Keeps raw commands available",
          NULL),
    ENTRY("0.8.3 v72", "DISPLAY TEST FIX",
          "Fixes display test rendering",
          "Keeps safe-area calibration",
          "Improves screen validation",
          "Preserves menu navigation",
          NULL),
    ENTRY("0.8.2 v71", "MENU LOG TAIL",
          "Adds menu live log tail",
          "Uses empty screen space",
          "Keeps status HUD visible",
          "Improves operator feedback",
          NULL),
    ENTRY("0.8.1 v70", "INPUT MONITOR APP",
          "Adds input monitor app",
          "Shows raw/gesture traces",
          "Helps button mapping debug",
          "Preserves menu actions",
          NULL),
    ENTRY("0.8.0 v69", "INPUT GESTURE LAYOUT",
          "Adds gesture layout",
          "Maps single/double/long/combo",
          "Improves physical-button UX",
          "Keeps no-touch operation",
          NULL),
    ENTRY("0.7.5 v68", "LOG TAIL + HISTORY",
          "Adds HUD log tail history",
          "Expands changelog history",
          "Improves ABOUT visibility",
          "Preserves menu structure",
          NULL),
    ENTRY("0.7.4 v67", "DETAIL CHANGELOG UI",
          "Reduces ABOUT text scale",
          "Opens changelog version list",
          "Adds version detail screens",
          "Improves credits screen",
          NULL),
    ENTRY("0.7.3 v66", "ABOUT + VERSIONING",
          "Adds semantic version display",
          "Adds made-by credit",
          "Adds ABOUT folder",
          "Adds versioning docs",
          NULL),
    ENTRY("0.7.2 v65", "SPLASH SAFE LAYOUT",
          "Adds splash safe layout",
          "Avoids clipped footer text",
          "Improves notch/punch-hole fit",
          "Keeps boot transition",
          NULL),
    ENTRY("0.7.1 v64", "CUSTOM BOOT SPLASH",
          "Adds A90 native init splash",
          "Replaces TEST boot pattern",
          "Keeps HUD transition",
          "Improves boot identity",
          NULL),
    ENTRY("0.7.0 v63", "APP MENU",
          "Adds hierarchical app menu",
          "Adds CPU stress app",
          "Uses physical buttons",
          "Keeps status HUD",
          NULL),
    ENTRY("0.6.0 v62", "CPU DIAGNOSTICS",
          "Adds CPU stress diagnostics",
          "Shows CPU status details",
          "Adds dev node guards",
          "Improves runtime testing",
          NULL),
    ENTRY("0.5.1 v61", "CPU/GPU USAGE HUD",
          "Adds CPU/GPU usage percent",
          "Shows thermal metrics",
          "Improves HUD telemetry",
          "Validates with stress load",
          NULL),
    ENTRY("0.5.0 v60", "NETSERVICE BOOT",
          "Adds opt-in boot netservice",
          "Starts NCM/tcpctl by flag",
          "Validates reconnect recovery",
          "Keeps default disabled",
          NULL),
    ENTRY("0.4.1 v59", "AT SERIAL FILTER",
          "Ignores modem AT probes",
          "Reduces serial noise",
          "Keeps console usable",
          "Improves bridge sessions",
          NULL),
    ENTRY("0.4.0 v55", "NCM TCP CONTROL",
          "Adds USB NCM operations",
          "Adds TCP nettest helper",
          "Validates bidirectional payload",
          "Builds network control path",
          NULL),
    ENTRY("0.3.0 v53", "MENU BUSY GATE",
          "Adds first menu busy policy",
          "Protects foreground menu control",
          "Keeps serial hide command",
          "Improves UI safety",
          NULL),
    ENTRY("0.2.0 v40", "SHELL LOG HUD CORE",
          "Adds shell/log/HUD baseline",
          "Adds boot timeline",
          "Adds run helper path",
          "Improves native init control",
          NULL),
    ENTRY("0.1.0 v1", "NATIVE INIT ORIGIN",
          "Boots custom static init",
          "Runs stock Android kernel",
          "Provides rescue shell",
          "Starts native userspace project",
          NULL),
};

struct a90_changelog_series_cache {
    struct a90_changelog_series public;
    char label[A90_CHANGELOG_SERIES_LABEL_MAX];
    char summary[A90_CHANGELOG_SERIES_SUMMARY_MAX];
    char key[16];
    size_t entry_indices[A90_CHANGELOG_MAX_ENTRIES];
};

static struct a90_changelog_series_cache changelog_series[A90_CHANGELOG_MAX_SERIES];
static size_t changelog_series_total;
static bool changelog_series_ready;

static void a90_changelog_series_key(const char *label, char *out, size_t out_size) {
    const char *first_dot;
    const char *second_dot;
    size_t len;

    if (out_size == 0) {
        return;
    }
    out[0] = '\0';
    if (label == NULL) {
        snprintf(out, out_size, "other");
        return;
    }

    first_dot = strchr(label, '.');
    if (first_dot == NULL) {
        snprintf(out, out_size, "other");
        return;
    }
    second_dot = strchr(first_dot + 1, '.');
    if (second_dot == NULL || second_dot == label) {
        snprintf(out, out_size, "other");
        return;
    }

    len = (size_t)(second_dot - label);
    if (len + 2 >= out_size) {
        len = out_size > 3 ? out_size - 3 : 0;
    }
    if (len == 0) {
        snprintf(out, out_size, "other");
        return;
    }
    memcpy(out, label, len);
    out[len] = '\0';
}

static const char *a90_changelog_series_kind(size_t index) {
    if (index == 0) {
        return "RECENT";
    }
    if (index == 1) {
        return "LEGACY";
    }
    return "OLDER";
}

static size_t a90_changelog_series_find(const char *key) {
    size_t index;

    for (index = 0; index < changelog_series_total; ++index) {
        if (strcmp(changelog_series[index].key, key) == 0) {
            return index;
        }
    }
    return (size_t)-1;
}

static void a90_changelog_build_series(void) {
    size_t entry_index;

    if (changelog_series_ready) {
        return;
    }

    for (entry_index = 0; entry_index < a90_changelog_count(); ++entry_index) {
        const struct a90_changelog_entry *entry = a90_changelog_entry_at(entry_index);
        char key[sizeof(changelog_series[0].key)];
        size_t series_index;
        struct a90_changelog_series_cache *series;

        a90_changelog_series_key(entry != NULL ? entry->label : NULL, key, sizeof(key));
        series_index = a90_changelog_series_find(key);
        if (series_index == (size_t)-1) {
            if (changelog_series_total >= A90_CHANGELOG_MAX_SERIES) {
                continue;
            }
            series_index = changelog_series_total++;
            series = &changelog_series[series_index];
            memset(series, 0, sizeof(*series));
            snprintf(series->key, sizeof(series->key), "%s", key);
            if (strcmp(key, "other") == 0) {
                snprintf(series->label, sizeof(series->label), "OTHER");
            } else {
                snprintf(series->label,
                         sizeof(series->label),
                         "%s.x %s",
                         key,
                         a90_changelog_series_kind(series_index));
            }
            series->public.label = series->label;
            series->public.summary = series->summary;
        } else {
            series = &changelog_series[series_index];
        }

        if (series->public.count < A90_CHANGELOG_MAX_ENTRIES) {
            series->entry_indices[series->public.count++] = entry_index;
        }
    }

    for (entry_index = 0; entry_index < changelog_series_total; ++entry_index) {
        struct a90_changelog_series_cache *series = &changelog_series[entry_index];

        snprintf(series->summary,
                 sizeof(series->summary),
                 "%u ENTRIES",
                 (unsigned int)series->public.count);
    }
    changelog_series_ready = true;
}

size_t a90_changelog_count(void) {
    return sizeof(changelog_entries) / sizeof(changelog_entries[0]);
}

const struct a90_changelog_entry *a90_changelog_entry_at(size_t index) {
    if (index >= a90_changelog_count()) {
        return NULL;
    }
    return &changelog_entries[index];
}

size_t a90_changelog_detail_count(const struct a90_changelog_entry *entry) {
    size_t count = 0;

    if (entry == NULL) {
        return 0;
    }
    while (count < A90_CHANGELOG_DETAIL_MAX && entry->details[count] != NULL) {
        ++count;
    }
    return count;
}

size_t a90_changelog_series_count(void) {
    a90_changelog_build_series();
    return changelog_series_total;
}

const struct a90_changelog_series *a90_changelog_series_at(size_t index) {
    a90_changelog_build_series();
    if (index >= changelog_series_total) {
        return NULL;
    }
    return &changelog_series[index].public;
}

size_t a90_changelog_series_entry_count(size_t series_index) {
    const struct a90_changelog_series *series = a90_changelog_series_at(series_index);

    return series != NULL ? series->count : 0;
}

size_t a90_changelog_entry_index_for_series(size_t series_index, size_t entry_index) {
    a90_changelog_build_series();
    if (series_index >= changelog_series_total) {
        return (size_t)-1;
    }
    if (entry_index >= changelog_series[series_index].public.count) {
        return (size_t)-1;
    }
    return changelog_series[series_index].entry_indices[entry_index];
}

#undef ENTRY
