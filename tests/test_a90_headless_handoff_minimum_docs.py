"""Public-only checks for the A90 headless isolation H0 boundary."""

from __future__ import annotations

import os
from pathlib import Path
import unittest


REPO = Path(__file__).resolve().parents[1]
GOAL = REPO / "GOAL_A90.md"
CONTRACT = REPO / "docs/operations/targets/A90_TARGET_CONTRACT.md"
PLAN = REPO / (
    "docs/plans/"
    "A90_HEADLESS_HANDOFF_MINIMUM_AND_WIFI_OWNERSHIP_DECISION_2026-08-13.md"
)
REDUCTION = REPO / (
    "docs/plans/"
    "A90_UFS_HANDOFF_ARCHITECTURE_AND_PRODUCTION_REDUCTION_PLAN_2026-08-12.md"
)
DIAGNOSTIC_DESIGN = REPO / (
    "docs/plans/"
    "A90_ATOMIC_WIFI_OWNERSHIP_DIAGNOSTIC_RESIDENT_DESIGN_2026-08-14.md"
)
ISOLATED_DESIGN = REPO / (
    "docs/plans/"
    "A90_HEADLESS_NATIVE_WIFI_ISOLATED_DEBIAN_DESIGN_2026-08-14.md"
)
COMPARISON = REPO / (
    "docs/plans/"
    "A90_H16_H24_ISOLATED_DEBIAN_COMPARISON_BASELINE_2026-08-14.md"
)
INCIDENT = REPO / (
    "docs/reports/"
    "A90_NATIVE_WIFI_SIDECAR_PROC_ROOT_EXPOSURE_HOST_INCIDENT_2026-08-13.md"
)
H24 = REPO / (
    "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/"
    "phase3-minimal-h24/manifest.toml"
)
H16 = REPO / (
    "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/"
    "phase3-minimal-h16/manifest.toml"
)
H16_INCIDENT = REPO / (
    "docs/reports/"
    "A90_H16_PERSISTENT_DEBIAN_RETURN_OBSERVER_INCIDENT_2026-08-10.md"
)
H24_INCIDENT = REPO / (
    "docs/reports/"
    "A90_H24_PERSISTENT_HUD_BOOTSTRAP_EINVAL_INCIDENT_2026-08-12.md"
)
FIRSTBOOT_AUDIT = REPO / (
    "docs/reports/"
    "A90_H14_IMMUTABLE_FIRSTBOOT_ISOLATED_DEBIAN_MISMATCH_H0_2026-08-14.md"
)
H14_CONTENT = REPO / (
    "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/"
    "phase3-minimal-h14/userdata-content-manifest.json"
)
LEDGER = REPO / "docs/operations/CAMPAIGN_LEDGER_A90.md"
MAIN = REPO / "workspace/public/src/native-init/v724/90_main.inc.c"
HELPER = REPO / "workspace/public/src/native-init/helpers/a90_android_execns_probe.c"
HANDOFF = REPO / "workspace/public/src/native-init/a90_server_distro.c"
BENCH = REPO / "workspace/public/src/native-init/a90_benchmark.c"
BENCH_PARSER = REPO / (
    "workspace/public/src/scripts/server-distro/a90_boot_benchmark_v1.py"
)
H16_FINALIZER = REPO / (
    "workspace/public/src/scripts/server-distro/"
    "a90_h16_persistent_physical_return_v1.py"
)
REAPER = REPO / "workspace/public/src/native-init/a90_reaper.c"
SHELL_DISPATCH = REPO / (
    "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"
)
RETIRED_W0_RUNNER = REPO / (
    "workspace/public/src/scripts/server-distro/"
    "a90_h24_wifi_ownership_w0_runner_v1.py"
)
RETIRED_W0_TEST = REPO / "tests/test_a90_h24_wifi_ownership_w0_v1.py"
H26_MANIFEST = REPO / (
    "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/"
    "phase3-minimal-h26/manifest.toml"
)


class A90HeadlessHandoffBoundaryTests(unittest.TestCase):
    def test_current_h24_wifi_sidecar_and_shared_proc_hazard_is_exact(self) -> None:
        manifest = H24.read_text(encoding="utf-8")
        main = MAIN.read_text(encoding="utf-8")
        helper = HELPER.read_text(encoding="utf-8")
        handoff = HANDOFF.read_text(encoding="utf-8")

        self.assertIn('"-DA90_WIFI_PERSISTENT_HANDOFF_V1=1"', manifest)
        self.assertIn('"-DA90_WIFI_AUTOCONNECT_PRIVATE_MOUNT_NS=1"', manifest)
        direct = main[main.index("A90DIRECT_BOOT mode=min-network-wifi") :]
        direct = direct[: direct.index("if (direct_handoff_rc < 0)")]
        self.assertLess(
            direct.index("v1393_run_wifi_test_boot_once();"),
            direct.index("a90_auto_handoff_run_once();"),
        )
        self.assertIn("run_persistent_wifi_handoff", helper)
        self.assertIn("unshare(CLONE_NEWNS)", helper)
        self.assertNotIn("CLONE_NEWPID", helper)
        move = handoff[
            handoff.index("static int d3_move_core_mounts(") :
            handoff.index("static int d3_restore_core_mounts(")
        ]
        self.assertIn('d3_move_mount_one("/proc", "proc")', move)

    def test_contract_requires_isolation_decision_before_candidate(self) -> None:
        contract = " ".join(CONTRACT.read_text(encoding="utf-8").split())
        for phrase in (
            "Before allocating that identity, the Wi-Fi ownership boundary must be selected",
            "A90_WIFI_OWNERSHIP_ATOMICITY_GATE_V1",
            "attempted atomic diagnostic is `NO_GO_RETIRED`",
            "A90_HEADLESS_NATIVE_WIFI_ISOLATED_DEBIAN_DESIGN_2026-08-14.md",
            "fresh PID, mount, IPC, UTS, and network namespaces",
            "bound veth peer",
            "manifest-frozen A90 cgroup layout",
            "exact consoleless `/dev` described below",
            "No devpts is mounted and no PTY allocation is a product function",
            "complete `/dev` tmpfs is remounted read-only",
            "matching child procfs uses fixed `nosuid,nodev,noexec,hidepid=2`",
            "Writable proc or an unbounded global view is `NO_GO`",
            "exact new-flow-rate and concurrent-flow bounds",
            "one exact dormant SSH-ingress gate",
            "durable `INGRESS_OPEN_INTENT`",
            "durably recorded as `INGRESS_OPEN` before any host connection",
            "The fresh UTS namespace receives one fixed public hostname",
            "replace the inherited session with one proved-empty anonymous child session",
            "one reviewed inherited classic-seccomp isolation filter",
            "all `clone3`",
            "later user-namespace creation cannot regain mount/device capability",
            "permits direct `socket()` only for exact traced AF_INET TCP",
            "including QRTR, netlink/kobject",
            "static default-deny policy",
            "`GRND_RANDOM` is denied and `/dev/random` is absent",
            "dedicated UIDs' pipe pages",
            "`SCHED_OTHER`, priority 0, `SCHED_RESET_ON_FORK`",
            "`RLIMIT_RTPRIO=0`, `RLIMIT_RTTIME=0`",
            "three exact pidfd-controlled stop barriers",
            "binds its number/flags/link target/`st_dev:st_ino`",
            "proves no descriptor references that child namespace inode",
            "`NETWORK_PREP_INTENT`",
            "`NETWORK_PREPARED`",
            "`ROOT_PREP_INTENT`",
            "`CHILD_RELEASE_INTENT`",
            "manifest-fixed home",
            "historical H24 `/root/.ssh` overlay absent",
            "Server-side client authentication is a separate mandatory boundary",
            "only login-eligible identity",
            "public-key-only batch/identity-only behavior",
            "arbitrary commands and subsystems",
            "distinct non-login SSH-key-daemon UID/GID",
            "permanently non-dumpable",
            "all child-side private-key copies are explicitly zeroed",
            "nonzero-to-nonzero setuid is never treated as an implicit cap clear",
            "single key-daemon/listener tree",
            "sole bounded transient generator memory exception",
            "RLIMIT_CORE=0",
            "zero private output",
            "Cleanup outcomes append separately",
            "inherited-mm branch",
            "`/proc/<pid>/{maps,map_files}`",
            "`KEY_DAEMON_CLEAN_READY`",
            "`KEY_DAEMON_LISTEN_READY`",
            "`GENERATOR_PUBLIC_COMPLETE`",
            "sole native-receipt writer",
            "one transient internal `pipe2(O_CLOEXEC)` status channel",
            "Both pipes are close-on-exec and no descriptor is inherited by Debian init",
            "A90_H14_IMMUTABLE_FIRSTBOOT_ISOLATED_DEBIAN_MISMATCH_H0_2026-08-14.md",
            "separately versioned minimal Debian content manifest must",
            "current common contract activates no direct UFS filesystem-content mutation",
            "HEALTH_PENDING_PERSISTENT_DEBIAN",
            "No headless successor may inherit this process model",
        ):
            self.assertIn(phrase, contract)

    def test_h24_shell_inventory_is_retired_as_mutating_not_d0(self) -> None:
        dispatch = SHELL_DISPATCH.read_text(encoding="utf-8")
        reaper = REAPER.read_text(encoding="utf-8")
        goal = GOAL.read_text(encoding="utf-8")

        self.assertIn('a90_reaper_reap_orphans("shell-prompt")', dispatch)
        self.assertIn('a90_reaper_reap_orphans("cmd-end")', dispatch)
        self.assertIn("waitpid(-1, &status, WNOHANG)", reaper)
        self.assertIn("a `run`-based inventory is not connected read-only D0", goal)
        self.assertFalse(os.path.lexists(RETIRED_W0_RUNNER))
        self.assertFalse(os.path.lexists(RETIRED_W0_TEST))

    def test_plan_separates_minimum_test_features_and_later_removal(self) -> None:
        plan = PLAN.read_text(encoding="utf-8")
        plan_flat = " ".join(plan.split())
        reduction = (REPO / (
            "docs/plans/"
            "A90_UFS_HANDOFF_ARCHITECTURE_AND_PRODUCTION_REDUCTION_PLAN_2026-08-12.md"
        )).read_text(encoding="utf-8")
        reduction_flat = " ".join(reduction.split())
        for heading in (
            "## Current implementation inventory",
            "## Absolute production requirements",
            "## Wi-Fi ownership diagnostic disposition",
            "## Test and benchmark features",
            "## Removal schedule",
            "## Why the implementation became large",
        ):
            self.assertIn(heading, plan)
        self.assertIn("HEALTH_PENDING_PERSISTENT_DEBIAN", plan)
        self.assertIn("Native PID 1 retains the exact native Wi-Fi owner", plan)
        self.assertIn("Benchmark collection never delays", plan)
        intent = plan.index("  -> durable one-shot intent and latch")
        child = plan.index(
            "  -> one CHILD_READY child blocked on an empty control pipe"
        )
        resource = plan.index(
            "  -> exact scheduler plus pids/memory+swap/CPU/UFS-I/O cgroup bounds active"
        )
        network = plan.index(
            "  -> parent moves only the veth peer by netns FD, closes it, proves zero nsfs FD"
        )
        network_policy = plan.index(
            "  -> parent binds native-end/rule policy with no retained namespace handle"
        )
        self.assertLess(intent, child)
        self.assertLess(child, resource)
        self.assertLess(resource, network)
        self.assertLess(network, network_policy)
        self.assertIn(
            "durable intent is published before the first child or network effect",
            plan,
        )
        self.assertIn("bootstrap pipes are closed", plan)
        local_ready = plan.index(
            "  -> KEY_DAEMON_LOCAL_READY + LOCAL_PERSISTENT with exact SSH gate dormant"
        )
        ingress_intent = plan.index("  -> durable INGRESS_OPEN_INTENT")
        ingress_open = plan.index("  -> INGRESS_OPEN; every other ingress remains default-drop")
        host_auth = plan.index("  -> attended host pins the server key")
        self.assertLess(local_ready, ingress_intent)
        self.assertLess(ingress_intent, ingress_open)
        self.assertLess(ingress_open, host_auth)
        self.assertIn(
            "exactly three fixed control tokens and three parent continuations",
            plan_flat,
        )
        self.assertIn(
            "control pipe carries only the three fixed one-byte `N`/`R`/`X` opcodes",
            plan_flat,
        )
        self.assertNotIn("only the two fixed tokens", plan_flat)
        self.assertIn("durable `NETWORK_PREP_INTENT`", plan_flat)
        self.assertIn(
            "closes it immediately, and enumerates zero parent references to the child namespace",
            plan_flat,
        )
        self.assertIn("no parent nsfs descriptor pins a child namespace", plan_flat)
        self.assertIn("durable `ROOT_PREP_INTENT`", plan_flat)
        self.assertIn("durably publishes `CHILD_RELEASE_INTENT`", plan_flat)
        self.assertIn("dispatches publish `CHILD_RELEASED`", plan_flat)
        self.assertIn("zone/queue/veth/rules and empty child cgroups", plan)
        self.assertIn(
            "does not require sysvinit or firstboot to retain",
            plan,
        )
        self.assertIn(
            "separately versioned minimal rootfs before the first candidate",
            plan,
        )
        for phrase in (
            "public-key-only Dropbear",
            "Exactly one nonzero service account",
            "One immutable read-only probe is forced",
            "zero password/interactive/",
            "two non-aliasing manifest-fixed nonzero identities",
            "service UID cannot traverse the key tree",
            "zeroes every child-side key copy",
            "sole native-receipt writer",
            "`GENERATOR_CLEAN_READY` then public-only `GENERATOR_PUBLIC_COMPLETE`",
            "`KEY_DAEMON_CLEAN_READY` then `KEY_DAEMON_LISTEN_READY`",
            "preinstalled as an exact dormant set/handle",
            "durably publishes `INGRESS_OPEN_INTENT`",
            "before `INGRESS_OPEN`",
        ):
            self.assertIn(phrase, plan_flat)
        self.assertIn("atomic diagnostic grant no exception", reduction_flat)
        self.assertIn("no diagnostic identity", reduction_flat)
        self.assertIn(
            "installed artifact and runtime binding contain neither",
            reduction_flat,
        )
        self.assertIn(
            "minimal content Stage 2 precedes the candidate Stage 3",
            reduction_flat,
        )
        self.assertLess(
            reduction.index("### Stage 2: minimal Debian content prerequisite"),
            reduction.index("### Stage 3: fresh headless successor"),
        )

    def test_atomic_diagnostic_is_retired_and_not_live_authority(self) -> None:
        design = " ".join(DIAGNOSTIC_DESIGN.read_text(encoding="utf-8").split())
        for phrase in (
            "Status: `NO_GO_RETIRED`",
            "historical rejected design only",
            "different UID/GID/capability identities",
            "would defeat the production reduction objective",
            "No code, candidate identity, manifest, approval",
            "This retired diagnostic can never satisfy the gate",
        ):
            self.assertIn(phrase, design)

    def test_selected_isolated_debian_design_is_bounded_h0(self) -> None:
        design = " ".join(ISOLATED_DESIGN.read_text(encoding="utf-8").split())
        for phrase in (
            "Native PID 1 does not call the current in-place `switch_root`",
            "separate PID, mount, IPC, UTS, and network namespaces",
            "CLONE_NEWPID | CLONE_NEWNS | CLONE_NEWIPC | CLONE_NEWUTS | CLONE_NEWNET",
            "initial SysV IPC tables are empty",
            "fixed public hostname `a90-debian`",
            "joins one new anonymous empty session keyring",
            "never resolves `KEY_SPEC_USER_KEYRING`",
            "never calls `KEYCTL_GET_PERSISTENT`",
            "missing user, user-session, and persistent keyrings all remain missing",
            "denies `clone3` completely",
            "no `CLONE_NEW*` bit or unknown service flag",
            "complete supported post-bootstrap mount/root API corpus",
            "node-creation denial",
            "nested user/mount/PID/network namespace",
            "Direct `socket()` is allowed only for `AF_INET`",
            "AF_QIPCRTR/QRTR",
            "compat `socketcall` entry is denied completely",
            "no native/preexisting socket FD reaches the service identity",
            "selected consoleless PID 1 or Dropbear",
            "clears the inherited environment",
            "## Aggregate resource boundary",
            "it never selects, autodetects, or falls back",
            "same child is the only member",
            "one exact manifest-bound static bootstrap executable",
            "restores `FD_CLOEXEC` on both pipe ends, closes every other FD",
            "independently re-enumerates the same exact two-pipe FD set",
            "no retained netlink socket",
            "O_RDONLY|O_CLOEXEC",
            "no parent descriptor references that nsfs inode",
            "every later parent observation require zero retained child-namespace FDs",
            "`waitid(P_PIDFD, ..., WSTOPPED)`",
            "`NETWORK_PREPARED`",
            "`ROOT_PREP_INTENT`",
            "`ROOT_PREPARED`",
            "`CHILD_RELEASE_INTENT`",
            "exact third/final continuation count",
            "any required token-write or pidfd-signal dispatch result missing",
            "Native PID 1 never calls `setns`",
            "permanently drops `CAP_NET_ADMIN`",
            "barrier negatives for any child effect or any frame other than the unique",
            "`/dev/console` (5:1), `ttyGS0`",
            "proves `tty_nr=0`",
            "No devpts is mounted and no PTY allocation is a product function",
            "remounts `/dev` read-only",
            "`/dev/urandom` (1:9, 0444)",
            "two distinct manifest-fixed nonzero identities",
            "manifest-fixed service home `.ssh`",
            "H24's historical `/root/.ssh` is absent",
            "## Server-side SSH client-authentication boundary",
            "public-key-only client authentication",
            "exactly one login-eligible service account",
            "service account has no general shell",
            "local and remote TCP forwarding",
            "sole accepted session is forced",
            "`IdentitiesOnly`/batch public-key-only behavior",
            "A successful connection by any password",
            "separate non-login SSH-key-daemon UID/GID",
            "mode 0700 and key mode 0400",
            "sets itself permanently non-dumpable",
            "all host-key FDs are absent or close-on-exec",
            "explicitly zeroed before one exact `execveat(AT_EMPTY_PATH)`",
            "nonzero-to-nonzero ID transition is never assumed to clear capabilities",
            "one key-daemon/listener tree retains",
            "sole pre-`ROOT_PREPARED` private-key memory exception",
            "generator crash, signal, private output",
            "inherited-mm pre-exec branch",
            "clean bootstrap address space",
            "native PID-1 virtual mapping",
            "`KEY_DAEMON_CLEAN_READY`",
            "`KEY_DAEMON_LISTEN_READY`",
            "`GENERATOR_CLEAN_READY`",
            "`GENERATOR_PUBLIC_COMPLETE`",
            "clean bootstrap is their sole receipt writer",
            "one exact internal `pipe2(O_CLOEXEC)` status channel",
            "Wrong writer, multiple writers",
            "`KEY_DAEMON_LOCAL_READY`",
            "It cannot open ingress or claim SSH authentication",
            "`INGRESS_OPEN_INTENT`",
            "`INGRESS_OPEN`",
            "never inserts the activation element",
            "opens ingress twice",
            "negative parent-namespace-handle tests",
            "19. `RETURN`",
            "an inherited native anonymous secret VMA",
            "`MAP_SHARED` file/device mapping",
            "static default-deny filter",
            "`GRND_RANDOM` is denied",
            "pids.max * RLIMIT_NOFILE",
            "nice value of +10",
            "`IOPRIO_CLASS_BE` priority 7",
            "inherited `SCHED_FIFO`, `SCHED_RR`, `SCHED_DEADLINE`",
            "Cgroup accounting alone does not bound",
            "one dedicated conntrack zone and enforces both a maximum new-flow rate and a maximum concurrent-flow set",
            "packet/byte counters may only advance monotonically",
            "now-empty child cgroups",
            "requires a closed compatible precondition over the existing native network namespace",
            "never writes `ip_forward` or an existing all/default/wlan scalar",
            "reviewed veth and forwarding boundary",
            "default drop in both forwarding directions",
            "native-veth `INPUT` defaults to drop",
            "no native local listener is reachable from the child peer",
            "unexpected native-to-Debian `OUTPUT`",
            "The SD card is not a runtime dependency",
            "Neither is duplicated to a fixed post-exec descriptor",
            "EOF alone is never success",
            "separate attended host observer reach the exact forwarded port",
            "per-boot Ed25519 host key",
            "remounts the exact host-key tmpfs read-only",
            "Before any SSH attempt",
            "TOFU and `StrictHostKeyChecking=no` are forbidden",
            "never creates, replaces, rotates, or reads the server private key",
            "12,092-byte firstboot can start Dropbear",
            "mounting or binding native sysfs is forbidden",
            "proves the child proc superblock differs from native procfs",
            "remounts each mask and the child proc superblock read-only",
            "The only permitted global proc facts are the exact read-only scalar allowlist",
            "writable `/proc/sys` or `sysrq-trigger`",
            "explicitly does not carry forward H24's optional `ttyGS0`",
            "neither the node, FD, nor old `/dev` survives",
            "Only ownership-aware `waitid(P_PIDFD, ...)`",
            "locks the reviewed securebits against root/setuid capability regain",
            "`HEALTH_PENDING_PERSISTENT_DEBIAN`",
            "neither a shared network namespace nor a userspace proxy is an allowed fallback",
            "No H26 ordinal, version, build string",
            "This document is H0 only",
        ):
            self.assertIn(phrase, design)

        failure = design[
            design.index("## Failure and fallback") :
            design.index("## Production minimum and removals")
        ]
        post_release = failure[
            failure.index("after release but before persistent health") :
            failure.index("after persistent service begins")
        ]
        self.assertLess(
            post_release.index("first block every new veth traffic path and SSH accept/session path"),
            post_release.index("durably publish the immutable original failure"),
        )
        self.assertLess(
            post_release.index("durably publish the immutable original failure"),
            post_release.index("terminate the exact child PID namespace"),
        )
        self.assertLess(
            post_release.index("prove every member gone"),
            post_release.index("remove those exact network objects"),
        )
        self.assertLess(
            post_release.index("remove those exact network objects"),
            post_release.index("Append the cleanup result separately"),
        )

        reduction = " ".join(REDUCTION.read_text(encoding="utf-8").split())
        for phrase in (
            "consoleless no-PTY minimal-dev boundary",
            "global-kernel-object resource boundary",
            "exact scheduler/CPU/ioprio/uclamp normalization",
            "exact three-barrier bootstrap protocol",
            "exactly two bounded scalar bootstrap pipes created close-on-exec",
            "parent-to-child `N`/`R`/`X` control",
            "child-to-parent fixed-frame receipt",
            "bidirectional packet/byte rate, burst, and depth limits",
            "UDP/SYN/return floods",
            "exact Dropbear binary hash",
            "one run-bound boot-private public key",
            "general shell, arbitrary command/subsystem",
            "distinct locked non-login SSH-key-daemon UID/GID",
            "every child key copy is zeroed",
            "non-dumpable with `RLIMIT_CORE=0`",
            "no core/log/temp/private-output residue",
            "manifest-bound static clean bootstrap",
            "revalidates clean mapping provenance",
            "sole native-receipt writer",
            "one-at-a-time transient internal status channels",
            "`GENERATOR_PUBLIC_COMPLETE`",
            "`KEY_DAEMON_LISTEN_READY`",
            "one preinstalled dormant SSH-ingress handle",
            "`INGRESS_OPEN_INTENT`",
            "exact `INGRESS_OPEN` return/readback",
            "enumerate zero parent child-namespace FDs",
            "close and prove absent every scoped parent child-namespace FD",
        ):
            self.assertIn(phrase, reduction)
        self.assertNotIn("one close-on-exec bootstrap receipt pipe", reduction)

    def test_exact_h14_firstboot_is_rejected_for_isolated_minimum(self) -> None:
        audit = " ".join(FIRSTBOOT_AUDIT.read_text(encoding="utf-8").split())
        content = H14_CONTENT.read_text(encoding="utf-8")
        goal = GOAL.read_text(encoding="utf-8")

        for phrase in (
            "fd8625402c76b2ee0cc4a2aff07eed3b182c6dd12eba1a022a445ea428c8c84a",
            "it brings up `ncm0`",
            "firstboot invokes the Debian Wi-Fi helper",
            "unchanged H14/H24 UFS content is rejected",
            "inherit no private key buffer or private control, health, or log descriptor",
            "common contract activates no direct UFS filesystem-content mutation",
            "never creates, replaces, rotates, traverses, reads, or inherits it",
            "remounted read-only before release",
            "strict host-key checking without TOFU",
            "one independently reviewed nonprivileged consoleless PID 1",
            "does not assume the historical sysvinit binary or root identity is compatible",
            "not `/root/.ssh`",
            "Possessing one `authorized_keys` file is not proof",
            "exact Dropbear binary hash",
            "exactly one fixed nonzero service account",
            "negotiated public-key client method",
            "mode-0700/mode-0400 tree",
            "filtered non-dumpable key daemon",
            "zeroes child-side key copies",
            "sole manifest-pinned transient generator",
            "sole native-receipt writer",
            "`GENERATOR_PUBLIC_COMPLETE`",
            "`KEY_DAEMON_LISTEN_READY`",
            "`INGRESS_OPEN_INTENT`",
            "exact `INGRESS_OPEN` return/readback",
            "zero core/log/temp/private-output residue",
            "No H26 identity",
        ):
            self.assertIn(phrase, audit)
        for path in (
            "/usr/local/bin/a90-dpublic-smoke-httpd",
            "/usr/local/bin/a90-dpublic-hud-intent",
            "/etc/a90-dpublic/wifi-sta-enable",
        ):
            self.assertIn(path, content)
        self.assertIn(
            "It is not the first isolated-Debian rootfs",
            goal,
        )

    def test_h16_is_frozen_as_mechanical_not_server_success_baseline(self) -> None:
        comparison = COMPARISON.read_text(encoding="utf-8")
        comparison_flat = " ".join(comparison.split())
        h16_incident = " ".join(H16_INCIDENT.read_text(encoding="utf-8").split())
        h24_incident = " ".join(H24_INCIDENT.read_text(encoding="utf-8").split())
        ledger = LEDGER.read_text(encoding="utf-8")

        for phrase in (
            "first direct-UFS live **mechanical handoff-boundary baseline**",
            "H16's public 11,760 ms value is `boot_to_switch_root_ms`",
            "does not simply revert to H16",
            "Native PID 1 remains a minimal supervisor",
            "Fresh Debian PID namespace plus matching private procfs",
            "Preserve only the fresh/no-devtmpfs principle",
            "no devpts/ptmx/PTY",
            "`DEBIAN_EXEC_LOCAL`",
            "one-shot `INGRESS_OPEN`",
            "two bounded bootstrap control/receipt pipes created close-on-exec",
            "dedicated native read-only retrieval frame",
            "`HEALTH_PENDING_PERSISTENT_DEBIAN` while live",
            "no device or live authority",
        ):
            self.assertIn(phrase, comparison)
        self.assertIn(
            "It does not prove automatic native return, authenticated SSH, Debian PID 1",
            h16_incident,
        )
        self.assertIn("stopped at the outer `persistent-hud` stage", h24_incident)
        self.assertIn("switch_root_exec occurred at 11760 ms", ledger)
        self.assertIn("full server readiness remain unproved", ledger)
        self.assertIn("H16 and H24 effects are historical and consumed", comparison_flat)

    def test_h24_manifest_delta_is_rooted_in_h16_without_reuse_authority(self) -> None:
        h16 = H16.read_text(encoding="utf-8")
        h24 = H24.read_text(encoding="utf-8")
        comparison = COMPARISON.read_text(encoding="utf-8")

        self.assertIn('extends = "v3404-effective"', h16)
        self.assertIn('"-DA90_AUTO_HANDOFF_USERDATA_DYNAMIC_DEVT=1"', h16)
        self.assertIn('extends = "phase3-minimal-h16"', h24)
        for flag in (
            '"-DA90_UFS_OBSERVER_AUTH_OVERLAY_V1=1"',
            '"-DA90_UFS_FIRSTBOOT_OVERLAY_V1=0"',
            '"-DA90_UFS_PERSISTENT_NATIVE_HUD_V1=1"',
            '"-DA90_UFS_PERSISTENT_NATIVE_HUD_DELAYED_DRM_V1=1"',
            '"-DA90_UFS_PERSISTENT_NATIVE_HUD_PRIVATE_CARD_ROOT_V1=1"',
        ):
            self.assertIn(flag, h24)
        self.assertIn("Directly extends `phase3-minimal-h16`", comparison)
        self.assertIn("neither may be replayed or reinterpreted", comparison)

    def test_h16_benchmark_stages_map_to_new_non_safety_telemetry(self) -> None:
        parser = BENCH_PARSER.read_text(encoding="utf-8")
        finalizer = H16_FINALIZER.read_text(encoding="utf-8")
        comparison = COMPARISON.read_text(encoding="utf-8")
        comparison_flat = " ".join(comparison.split())

        for stage in (
            '"handoff_begin"',
            '"root_mounted"',
            '"writable_set_ready"',
            '"distro_init_verified"',
            '"display_marker_ready"',
            '"mount_moves_done"',
            '"switch_root_exec"',
        ):
            self.assertIn(stage, parser)
            self.assertIn(stage, finalizer)
        self.assertIn('"boot_to_switch_root_ms"', finalizer)
        self.assertIn('"handoff_begin_to_switch_root_ms"', finalizer)
        for phrase in (
            "`display_marker_ready` | removed; no headless equivalent",
            "`switch_root_exec` | `DEBIAN_EXEC_LOCAL`",
            "Performance collection is observational",
        ):
            self.assertIn(phrase, comparison)
        self.assertIn(
            "a faster benchmark never substitutes for safety",
            comparison_flat,
        )

    def test_no_successor_identity_or_live_authority_is_created(self) -> None:
        goal = GOAL.read_text(encoding="utf-8")
        incident = INCIDENT.read_text(encoding="utf-8")
        self.assertFalse(os.path.lexists(H26_MANIFEST))
        self.assertIn("No H26 identity or path is", goal)
        self.assertIn("no successor candidate allocated", incident)
        self.assertIn("grants no D0, D1,", incident)
        self.assertIn("Device, `/dev`, USB, network", incident)

    def test_current_benchmark_limit_and_ufs_followup_are_not_overclaimed(self) -> None:
        source = BENCH.read_text(encoding="utf-8")
        plan = PLAN.read_text(encoding="utf-8")
        self.assertIn('strcmp(name, "mmcblk0") == 0', source)
        self.assertIn("storage counters from exact UFS whole device `sda`", plan)
        self.assertIn("Missing telemetry is `na`", plan)


if __name__ == "__main__":
    unittest.main()
