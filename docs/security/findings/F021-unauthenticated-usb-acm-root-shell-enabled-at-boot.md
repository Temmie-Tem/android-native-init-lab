# F021. Unauthenticated USB ACM root shell enabled at boot

## Metadata

| field | value |
|---|---|
| finding_id | `91b6b1ecbbdc81918025670e7c2fe9d6` |
| finding_url | https://chatgpt.com/codex/cloud/security/findings/91b6b1ecbbdc81918025670e7c2fe9d6 |
| severity | `medium` |
| status | `new` |
| detected_at | `2026-04-27T22:51:37.803965Z` |
| committed_at | `2026-04-24 17:11:57 +0900` |
| commit_hash | `6cbcb78c460c4362e168ee150cf5f90fcd298b7b` |
| relevant_paths | `stage3/linux_init/init_v30.c` |
| has_patch | `false` |

## CSV Description

This commit adds a new init implementation that automatically configures and binds a USB gadget serial interface, attaches it as stdin/stdout/stderr, and launches an interactive shell loop. There is no authentication, pairing, challenge-response, or physical-confirmation gate before command execution. The shell exposes highly privileged primitives (e.g., arbitrary execve via `run`, filesystem/device operations, and starting adbd with `--root_seclabel=u:r:su:s0`), enabling full system compromise by anyone with USB physical access during this boot stage.

## Codex Cloud Detail

Unauthenticated USB ACM root shell enabled at boot
Link: https://chatgpt.com/codex/cloud/security/findings/91b6b1ecbbdc81918025670e7c2fe9d6?repo=https%3A%2F%2Fgithub.com%2FTemmie-Tem%2FA90_5G_rooting&sev=&page=2
Criticality: medium (attack path: medium)
Status: new

# Metadata
Repo: Temmie-Tem/A90_5G_rooting
Commit: 6cbcb78
Author: shs02140@gmail.com
Created: 2026. 4. 28. 오전 7:51:37
Assignee: Unassigned
Signals: Security, Validated, Attack-path

# Summary
Introduced authentication flaw: unauthenticated root command interface over USB ACM in early boot, with command set allowing arbitrary code execution and system modification.
This commit adds a new init implementation that automatically configures and binds a USB gadget serial interface, attaches it as stdin/stdout/stderr, and launches an interactive shell loop. There is no authentication, pairing, challenge-response, or physical-confirmation gate before command execution. The shell exposes highly privileged primitives (e.g., arbitrary execve via `run`, filesystem/device operations, and starting adbd with `--root_seclabel=u:r:su:s0`), enabling full system compromise by anyone with USB physical access during this boot stage.

# Validation
## Rubric
- [x] Confirm commit introduction scope (new `init_v30.c` added in 6cbcb78).
- [x] Verify USB ACM interface is automatically exposed/bound (configfs gadget + UDC bind in `setup_acm_gadget`).
- [x] Verify there is no authentication gate before interactive command processing (`main` -> `attach_console` -> `shell_loop`).
- [x] Verify privileged command surface includes arbitrary execution/system modification (`run`, `writefile`, `mknod*`, `mountfs`, `startadbd`).
- [x] Demonstrate practical execution primitive with minimal PoC (`cmd_run` executes `/bin/sh -c ...`, producing root `id` output).
## Report
I validated the finding against commit 6cbcb78 (which introduces `stage3/linux_init/init_v30.c` as a new file: 3240 insertions).

What I tested first (compiled-stack workflow):
- Direct run attempt (debug build): `timeout 5 /tmp/init_v30_dbg` -> timed out (`exit_code:124`), no crash in container boot-mismatched environment (`logs/crash_attempt.txt`).
- ASan attempt: `timeout 5 /tmp/init_v30_asan` -> timed out (`exit_code:124`), no ASan finding (`logs/asan_valgrind_attempt.txt`).
- Valgrind attempt: not available (`valgrind_not_installed`).
- Debugger trace (LLDB): breakpoint hit in `setup_acm_gadget()` from `main()` (`init_v30.c:2227` called from `main:3209`), confirming execution path into USB gadget setup (`logs/debugger_trace.txt`).

Code evidence for the auth flaw:
- USB ACM gadget is auto-configured and enabled by writing UDC bind directly (`wf("/config/usb_gadget/g1/UDC", "a600000.dwc3")`) in `setup_acm_gadget()` (`stage3/linux_init/init_v30.c:2226-2258`).
- Console is attached directly to `/dev/ttyGS0` in `attach_console()` (`init_v30.c:2261-2268`).
- `main()` immediately enters `shell_loop()` after attach, with no authentication/pairing/challenge gate (`init_v30.c:3230-3234`).
- `shell_loop()` exposes privileged commands to any console user, including `writefile`, `mknodc/mknodb`, `mountfs`, `run`, `runandroid`, `startadbd` (`init_v30.c:3035-3164`).
- `cmd_run()` executes arbitrary paths via `execve(argv[1], &argv[1], envp)` (`init_v30.c:2807-2834`).
- `cmd_startadbd()` launches adbd with `--root_seclabel=u:r:su:s0` (`init_v30.c:2962-2966`).

Dynamic supporting PoC (primitive validation):
- I built a harness that includes `init_v30.c` and invokes `cmd_run()`.
- Command output: `[exit 0]` and generated `/tmp/init_v30_poc_id` containing `uid=0(root) gid=0(root)` (`logs/poc_cmd_run_execution.txt`).
- This confirms arbitrary command execution capability of the exposed shell primitive once console access is obtained.

Conclusion: the reported unauthenticated USB ACM root command interface is valid and introduced in this commit.

# Evidence
stage3/linux_init/init_v30.c (L2226 to 2258)
  Note: Automatically configures and enables the USB ACM gadget (`UDC` bind), exposing the serial interface without any access control.
```
static int setup_acm_gadget(void) {
    if (mount("configfs", "/config", "configfs", 0, NULL) != 0 && errno != EBUSY) {
        return -1;
    }

    ensure_dir("/config/usb_gadget", 0770);
    ensure_dir("/config/usb_gadget/g1", 0770);
    ensure_dir("/config/usb_gadget/g1/strings", 0770);
    ensure_dir("/config/usb_gadget/g1/strings/0x409", 0770);
    ensure_dir("/config/usb_gadget/g1/configs", 0770);
    ensure_dir("/config/usb_gadget/g1/configs/b.1", 0770);
    ensure_dir("/config/usb_gadget/g1/configs/b.1/strings", 0770);
    ensure_dir("/config/usb_gadget/g1/configs/b.1/strings/0x409", 0770);
    ensure_dir("/config/usb_gadget/g1/functions", 0770);
    ensure_dir("/config/usb_gadget/g1/functions/acm.usb0", 0770);

    wf("/config/usb_gadget/g1/idVendor", "0x04e8");
    wf("/config/usb_gadget/g1/idProduct", "0x6861");
    wf("/config/usb_gadget/g1/bcdUSB", "0x0200");
    wf("/config/usb_gadget/g1/bcdDevice", "0x0100");
    wf("/config/usb_gadget/g1/strings/0x409/serialnumber", "REDACTED-DEVICE-SERIAL");  /* device identifier redacted in public tree */
    wf("/config/usb_gadget/g1/strings/0x409/manufacturer", "samsung");
    wf("/config/usb_gadget/g1/strings/0x409/product", "SM8150-ACM");
    wf("/config/usb_gadget/g1/configs/b.1/strings/0x409/configuration", "serial");
    wf("/config/usb_gadget/g1/configs/b.1/MaxPower", "900");

    if (create_symlink("/config/usb_gadget/g1/functions/acm.usb0",
                       "/config/usb_gadget/g1/configs/b.1/f1") < 0) {
        return -1;
    }

    wf("/config/usb_gadget/g1/UDC", "a600000.dwc3");
    return 0;
```

stage3/linux_init/init_v30.c (L2807 to 2834)
  Note: Shell command `run` executes arbitrary binaries via `execve`, providing direct root code execution from the unauthenticated console.
```
static void cmd_run(char **argv, int argc) {
    static char *const envp[] = {
        "PATH=/cache:/cache/bin:/bin:/system/bin",
        "HOME=/",
        "TERM=vt100",
        "LD_LIBRARY_PATH=/cache/adb/lib",
        NULL
    };
    pid_t pid;
    int status;

    if (argc < 2) {
        cprintf("usage: run <path> [args...]\r\n");
        return;
    }

    pid = fork();
    if (pid < 0) {
        cprintf("run: fork: %s\r\n", strerror(errno));
        return;
    }

    if (pid == 0) {
        dup2(console_fd, STDIN_FILENO);
        dup2(console_fd, STDOUT_FILENO);
        dup2(console_fd, STDERR_FILENO);
        execve(argv[1], &argv[1], envp);
        cprintf("run: execve(%s): %s\r\n", argv[1], strerror(errno));
```

stage3/linux_init/init_v30.c (L3035 to 3164)
  Note: Command dispatcher exposes sensitive primitives (`writefile`, `mknod*`, `mountfs`, `run`, `runandroid`, `startadbd`) to any connected console user.
```
        if (strcmp(argv[0], "help") == 0) {
            cmd_help();
        } else if (strcmp(argv[0], "version") == 0) {
            cmd_version();
        } else if (strcmp(argv[0], "status") == 0) {
            cmd_status();
        } else if (strcmp(argv[0], "uname") == 0) {
            cmd_uname();
        } else if (strcmp(argv[0], "pwd") == 0) {
            cmd_pwd();
        } else if (strcmp(argv[0], "cd") == 0) {
            const char *path = argc > 1 ? argv[1] : "/";
            if (chdir(path) < 0) {
                cprintf("cd: %s: %s\r\n", path, strerror(errno));
            }
        } else if (strcmp(argv[0], "ls") == 0) {
            cmd_ls(argc > 1 ? argv[1] : ".");
        } else if (strcmp(argv[0], "cat") == 0) {
            if (argc < 2) {
                cprintf("usage: cat <file>\r\n");
            } else {
                cmd_cat(argv[1]);
            }
        } else if (strcmp(argv[0], "stat") == 0) {
            if (argc < 2) {
                cprintf("usage: stat <path>\r\n");
            } else {
                cmd_stat(argv[1]);
            }
        } else if (strcmp(argv[0], "mounts") == 0) {
            cmd_mounts();
        } else if (strcmp(argv[0], "mountsystem") == 0) {
            bool read_only = true;

            if (argc > 1 && strcmp(argv[1], "rw") == 0) {
                read_only = false;
            }
            cmd_mountsystem(read_only);
        } else if (strcmp(argv[0], "prepareandroid") == 0) {
            cmd_prepareandroid();
        } else if (strcmp(argv[0], "inputinfo") == 0) {
            cmd_inputinfo(argv, argc);
        } else if (strcmp(argv[0], "drminfo") == 0) {
            cmd_drminfo(argv, argc);
        } else if (strcmp(argv[0], "fbinfo") == 0) {
            cmd_fbinfo(argv, argc);
        } else if (strcmp(argv[0], "kmsprobe") == 0) {
            cmd_kmsprobe();
        } else if (strcmp(argv[0], "kmssolid") == 0) {
            cmd_kmssolid(argv, argc);
        } else if (strcmp(argv[0], "kmsframe") == 0) {
            cmd_kmsframe();
        } else if (strcmp(argv[0], "statusscreen") == 0) {
            cmd_statusscreen();
        } else if (strcmp(argv[0], "statushud") == 0 ||
                   strcmp(argv[0], "redraw") == 0) {
            cmd_statushud();
        } else if (strcmp(argv[0], "testpattern") == 0) {
            cmd_statusscreen();
        } else if (strcmp(argv[0], "clear") == 0) {
            cmd_clear_display();
        } else if (strcmp(argv[0], "inputcaps") == 0) {
            cmd_inputcaps(argv, argc);
        } else if (strcmp(argv[0], "readinput") == 0) {
            cmd_readinput(argv, argc);
        } else if (strcmp(argv[0], "waitkey") == 0) {
            cmd_waitkey(argv, argc);
        } else if (strcmp(argv[0], "blindmenu") == 0 ||
                   strcmp(argv[0], "menu") == 0) {
            cmd_blindmenu();
        } else if (strcmp(argv[0], "mkdir") == 0) {
            if (argc < 2) {
                cprintf("usage: mkdir <dir>\r\n");
            } else if (mkdir(argv[1], 0755) < 0 && errno != EEXIST) {
                cprintf("mkdir: %s: %s\r\n", argv[1], strerror(errno));
            }
        } else if (strcmp(argv[0], "mknodc") == 0) {
            unsigned int major_num;
            unsigned int minor_num;

            if (argc < 4) {
                cprintf("usage: mknodc <path> <major> <minor>\r\n");
            } else if (sscanf(argv[2], "%u", &major_num) != 1 ||
                       sscanf(argv[3], "%u", &minor_num) != 1) {
                cprintf("mknodc: invalid major/minor\r\n");
            } else if (ensure_char_node(argv[1], major_num, minor_num) < 0) {
                cprintf("mknodc: %s: %s\r\n", argv[1], strerror(errno));
            }
        } else if (strcmp(argv[0], "mknodb") == 0) {
            unsigned int major_num;
            unsigned int minor_num;

            if (argc < 4) {
                cprintf("usage: mknodb <path> <major> <minor>\r\n");
            } else if (sscanf(argv[2], "%u", &major_num) != 1 ||
                       sscanf(argv[3], "%u", &minor_num) != 1) {
                cprintf("mknodb: invalid major/minor\r\n");
            } else if (mknod(argv[1], S_IFBLK | 0600,
                             makedev(major_num, minor_num)) < 0 && errno != EEXIST) {
                cprintf("mknodb: %s: %s\r\n", argv[1], strerror(errno));
            }
        } else if (strcmp(argv[0], "mountfs") == 0) {
            unsigned long flags = 0;

            if (argc < 4) {
                cprintf("usage: mountfs <src> <dst> <type> [ro]\r\n");
            } else {
                if (argc > 4 && strcmp(argv[4], "ro") == 0) {
                    flags |= MS_RDONLY;
                }
                if (mount(argv[1], argv[2], argv[3], flags, NULL) < 0) {
                    cprintf("mountfs: %s\r\n", strerror(errno));
                }
            }
        } else if (strcmp(argv[0], "umount") == 0) {
            if (argc < 2) {
                cprintf("usage: umount <path>\r\n");
            } else if (umount(argv[1]) < 0) {
                cprintf("umount: %s: %s\r\n", argv[1], strerror(errno));
            }
        } else if (strcmp(argv[0], "echo") == 0) {
            cmd_echo(argv, argc);
        } else if (strcmp(argv[0], "writefile") == 0) {
            cmd_writefile(argv, argc);
        } else if (strcmp(argv[0], "run") == 0) {
            cmd_run(argv, argc);
        } else if (strcmp(argv[0], "runandroid") == 0) {
            cmd_runandroid(argv, argc);
        } else if (strcmp(argv[0], "startadbd") == 0) {
            cmd_startadbd();
```

stage3/linux_init/init_v30.c (L3230 to 3235)
  Note: Immediately attaches `/dev/ttyGS0` as console and enters `shell_loop()` with no authentication step.
```
    if (attach_console() == 0) {
        mark_step("4_console_attached_v30\n");
        cprintf("\r\n%s\r\n", INIT_BANNER);
        cprintf("USB ACM serial console ready.\r\n");
        shell_loop();
    }
```

# Attack-path analysis
Final: medium | Decider: model_decided | Matrix severity: medium | Policy adjusted: ignore
## Rationale
Kept at medium: impact is high (unauthenticated root shell primitives), but probability is moderated by required physical USB access and deployment precondition of this custom init workflow. Evidence shows direct exploit path in code and validation PoC for root command execution primitive, so this is not a false positive.
## Likelihood
medium - Exploitation is straightforward once physical access and vulnerable boot image are present, but those preconditions materially limit opportunistic abuse.
## Impact
high - Successful access yields root-level command execution and full integrity/confidentiality/availability impact on the device image/runtime.
## Assumptions
- init_v30.c is compiled and deployed as the device /init in a flashed boot image
- Attacker can obtain physical USB access during this boot stage
- Device is in the project’s rooted/patched baseline workflow
- Physical USB connection to target phone
- Booting image that uses stage3/linux_init/init_v30.c logic
- Early boot reaches setup_acm_gadget + attach_console path
## Path
USB cable -> ACM gadget (UDC bind) -> /dev/ttyGS0 console -> shell_loop() (no auth) -> run/execve,mount,mknod,startadbd(root)
## Path evidence
- `stage3/linux_init/init_v30.c:2226-2258` - Automatically creates USB ACM gadget and binds UDC, exposing serial interface.
- `stage3/linux_init/init_v30.c:2261-2268` - Console is attached to /dev/ttyGS0.
- `stage3/linux_init/init_v30.c:3230-3234` - Immediately enters shell_loop() after attach with no auth/pairing/challenge.
- `stage3/linux_init/init_v30.c:2807-2834` - cmd_run executes attacker-supplied path via execve.
- `stage3/linux_init/init_v30.c:3035-3164` - Dispatcher exposes dangerous commands to any console user (writefile/mknod/mountfs/run/runandroid/startadbd).
- `stage3/linux_init/init_v30.c:2962-2966` - startadbd launches with root seclabel.
- `README.md:3-5` - Repo is a rooted native-Linux boot workspace, indicating this is runtime boot-chain code in project context.
- `docs/overview/PROGRESS_LOG.md:95-106` - Project workflow explicitly uses USB ACM serial mini-shell path and boot artifacts.
## Narrative
The commit introduces an early-boot USB ACM console that is automatically enabled and bound, then attached and dropped directly into an interactive shell without any authentication. The shell exposes direct root-impact primitives, including arbitrary execve and filesystem/device mutation. Validation evidence also reports executable PoC behavior confirming root command execution primitive. This is a real vulnerability when this init is deployed, but exploitability is constrained by physical USB access and custom-boot preconditions, aligning with medium severity.
## Controls
- Physical access requirement (USB cable to device)
- Requires booting custom/rooted experiment image
- No in-code authentication/authorization on shell entry
## Blindspots
- Static-only review cannot prove how widely init_v30 is deployed across actual flashed images.
- No live device state verification (OEM lock/KG/physical protections) in this stage.
- No cloud/service manifests; exposure is hardware-local rather than networked.
