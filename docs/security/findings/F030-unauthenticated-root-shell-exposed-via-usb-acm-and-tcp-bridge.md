# F030. Unauthenticated root shell exposed via USB ACM and TCP bridge

## Metadata

| field | value |
|---|---|
| finding_id | `7f3b6c5b0d6c819192f7f3869ce48b04` |
| finding_url | https://chatgpt.com/codex/cloud/security/findings/7f3b6c5b0d6c819192f7f3869ce48b04 |
| severity | `informational` |
| status | `new` |
| detected_at | `2026-04-27T23:44:27.918637Z` |
| committed_at | `2026-04-23 23:20:31 +0900` |
| commit_hash | `c5983844a4293e5ad3be364792426fd4e679eca0` |
| relevant_paths | `stage3/linux_init/init_v8.c | scripts/revalidation/serial_tcp_bridge.py` |
| has_patch | `false` |

## CSV Description

New native init variants (e.g., init_v8.c) automatically configure a USB ACM gadget, attach /dev/ttyGS0 as console, and enter an interactive command loop as PID 1/root. The shell accepts dangerous commands such as run/runandroid (arbitrary execve), mountfs, mknodb, reboot, and startadbd, but implements no authentication or authorization before command execution. In the same commit, serial_tcp_bridge.py opens a TCP listener and forwards client bytes directly to the serial shell, also with no authentication checks. If this experimental boot image is flashed and the bridge is run (README even suggests sudo usage), any local user able to connect to 127.0.0.1:<port> can control the root shell on the connected device, with full confidentiality/integrity/availability impact on that device.

## Codex Cloud Detail

Unauthenticated root shell exposed via USB ACM and TCP bridge
Link: https://chatgpt.com/codex/cloud/security/findings/7f3b6c5b0d6c819192f7f3869ce48b04?repo=https%3A%2F%2Fgithub.com%2FTemmie-Tem%2FA90_5G_rooting&sev=&page=2
Criticality: informational (attack path: ignore)
Status: new

# Metadata
Repo: Temmie-Tem/A90_5G_rooting
Commit: c598384
Author: shs02140@gmail.com
Created: 2026. 4. 28. 오전 8:44:27
Assignee: Unassigned
Signals: Security, Validated, Attack-path

# Summary
Security bug introduced: unauthenticated privileged command interface (USB ACM root shell) plus unauthenticated TCP-to-serial forwarding, effectively creating a backdoor control channel.
New native init variants (e.g., init_v8.c) automatically configure a USB ACM gadget, attach /dev/ttyGS0 as console, and enter an interactive command loop as PID 1/root. The shell accepts dangerous commands such as run/runandroid (arbitrary execve), mountfs, mknodb, reboot, and startadbd, but implements no authentication or authorization before command execution. In the same commit, serial_tcp_bridge.py opens a TCP listener and forwards client bytes directly to the serial shell, also with no authentication checks. If this experimental boot image is flashed and the bridge is run (README even suggests sudo usage), any local user able to connect to 127.0.0.1:<port> can control the root shell on the connected device, with full confidentiality/integrity/availability impact on that device.

# Validation
## Rubric
- [x] Confirm commit path exposes USB ACM control channel and auto-enters shell (`init_v8.c:225-257`, `1008-1023`).
- [x] Confirm shell includes dangerous privileged commands and arbitrary exec (`init_v8.c:660-687`, `864-983`).
- [x] Confirm no authentication/authorization checks before command dispatch (no auth gate in `shell_loop`, `init_v8.c:864-983`).
- [x] Confirm TCP bridge has no client auth and blindly forwards bytes (`serial_tcp_bridge.py:51-57`, `126-138`, `187-213`).
- [x] Reproduce practical exploitability with bounded PoC (unauthenticated localhost TCP client injects `run /bin/id` bytes and receives serial reply).
## Report
I validated the finding as a real authz/authn logic vulnerability (not a memory-corruption crash). Evidence: (1) `init_v8.c` auto-enables ACM gadget and binds UDC in `setup_acm_gadget()` (`stage3/linux_init/init_v8.c:225-257`), then waits for `/dev/ttyGS0`, attaches it as stdio, and immediately enters `shell_loop()` (`stage3/linux_init/init_v8.c:1008-1023`). (2) The shell dispatcher exposes privileged operations with no auth gate: `run`, `runandroid`, `mountfs`, `mknodb`, `startadbd`, `reboot`, etc. (`stage3/linux_init/init_v8.c:864-983`), and `cmd_run` does direct `execve(argv[1], ...)` (`stage3/linux_init/init_v8.c:660-687`). (3) The bridge opens a TCP listener (`scripts/revalidation/serial_tcp_bridge.py:51-57`), accepts any client without authentication (`...:126-138`), and forwards client bytes directly to serial (`...:187-213`). (4) Runtime PoC: `python3 validation_poc/poc_serial_bridge_unauth.py` produced `PASS: unauthenticated TCP client could inject shell command bytes`, with `serial_received: run /bin/id` and `client_received: uid=0(root) gid=0(root)`, proving unauthenticated localhost TCP injection into the serial command channel. (5) README explicitly documents usage as a quick gate (`scripts/revalidation/README.md:35-42` with `sudo ...serial_tcp_bridge.py` and `nc 127.0.0.1 54321`). Per required method order, I also attempted crash/ASan/valgrind/debugger on `init_v8.c`: debug build succeeded, direct run timed out (`EXIT:124`), ASan run timed out (`EXIT:124`), valgrind unavailable (`command not found`), LLDB non-interactive backtrace captured (artifacts logs).

# Evidence
scripts/revalidation/serial_tcp_bridge.py (L126 to 138)
  Note: Accepts client connections without authentication/authorization.
```
    def accept_client(self) -> None:
        conn, addr = self.server.accept()
        conn.setblocking(False)

        if self.client is not None:
            self.log(f"rejecting extra client from {addr[0]}:{addr[1]}")
            conn.close()
            return

        self.client = conn
        self.client_addr = addr
        self.selector.register(conn, selectors.EVENT_READ, "client")
        self.log(f"client connected: {addr[0]}:{addr[1]}")
```

scripts/revalidation/serial_tcp_bridge.py (L187 to 213)
  Note: Blindly forwards client input to serial endpoint, granting command channel access.
```
    def forward_client(self) -> None:
        assert self.client is not None

        try:
            data = self.client.recv(8192)
        except OSError as exc:
            self.log(f"client read failed: {exc}")
            self.close_client()
            return

        if not data:
            self.close_client()
            return

        if self.capture_fp is not None:
            self.capture_fp.write(b"\n--- tcp->serial ---\n")
            self.capture_fp.write(data)

        if self.serial_fd is None:
            return

        try:
            os.write(self.serial_fd, data)
        except OSError as exc:
            self.log(f"serial write failed: {exc}")
            self.close_serial()
```

scripts/revalidation/serial_tcp_bridge.py (L51 to 57)
  Note: Starts TCP listener for bridge access.
```
    def _open_server(self) -> socket.socket:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.args.host, self.args.port))
        server.listen(1)
        server.setblocking(False)
        self.log(f"tcp listener ready on {self.args.host}:{self.args.port}")
```

stage3/linux_init/init_v8.c (L225 to 257)
  Note: Sets up and enables USB ACM gadget (UDC bind), exposing a serial control channel.
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

stage3/linux_init/init_v8.c (L660 to 687)
  Note: Implements run command that executes arbitrary binaries via execve as root/PID1 context.
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

stage3/linux_init/init_v8.c (L864 to 983)
  Note: Main shell command dispatcher with sensitive operations (mount, mknod, run, startadbd, reboot) and no authentication gate.
```
static void shell_loop(void) {
    char line[512];

    cmd_help();

    while (1) {
        char *argv[32];
        int argc;

        print_prompt();
        if (read_line(line, sizeof(line)) < 0) {
            cprintf("read: %s\r\n", strerror(errno));
            sleep(1);
            continue;
        }

        argc = split_args(line, argv, 32);
        if (argc == 0) {
            continue;
        }

        if (strcmp(argv[0], "help") == 0) {
            cmd_help();
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
        } else if (strcmp(argv[0], "mkdir") == 0) {
            if (argc < 2) {
                cprintf("usage: mkdir <dir>\r\n");
            } else if (mkdir(argv[1], 0755) < 0 && errno != EEXIST) {
                cprintf("mkdir: %s: %s\r\n", argv[1], strerror(errno));
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
        } else if (strcmp(argv[0], "run") == 0) {
            cmd_run(argv, argc);
        } else if (strcmp(argv[0], "runandroid") == 0) {
            cmd_runandroid(argv, argc);
        } else if (strcmp(argv[0], "startadbd") == 0) {
            cmd_startadbd();
        } else if (strcmp(argv[0], "stopadbd") == 0) {
            cmd_stopadbd();
        } else if (strcmp(argv[0], "sync") == 0) {
            sync();
            cprintf("synced\r\n");
        } else if (strcmp(argv[0], "reboot") == 0) {
            sync();
            reboot(RB_AUTOBOOT);
            wf("/proc/sysrq-trigger", "b");
        } else if (strcmp(argv[0], "recovery") == 0) {
            cmd_recovery();
        } else if (strcmp(argv[0], "poweroff") == 0) {
            sync();
            reboot(RB_POWER_OFF);
        } else {
            cprintf("unknown command: %s\r\n", argv[0]);
        }
```

# Attack-path analysis
Final: ignore | Decider: model_decided | Matrix severity: medium | Policy adjusted: ignore
## Rationale
The vulnerability is technically real and PoC-backed, with high per-device impact. However, probability in project context is constrained by non-default, operator-driven lab setup and a localhost-only bridge in explicitly experimental tooling. The repository positions these components as revalidation/development helpers, not production-facing services; therefore this should be tracked as unsafe debug design in a lab workflow rather than a high-severity product security defect.
## Likelihood
medium - Exploitation is straightforward once bridge is running, but requires local host access plus operator-enabled experimental setup (flashed image + running bridge).
## Impact
high - If preconditions are met, attacker can execute arbitrary commands as root/PID1 on connected device, allowing full integrity, confidentiality, and availability compromise of that device.
## Assumptions
- A boot image containing stage3/linux_init/init_v8.c is actually flashed and booted on the target device.
- The operator runs scripts/revalidation/serial_tcp_bridge.py while the device is connected over USB ACM.
- An attacker has local user-level access on the same host and can connect to 127.0.0.1:54321.
- Flashed experimental init image
- USB ACM gadget exposed by init_v8
- Bridge process running on host
- Local host access to localhost TCP port
## Path
n1(local user) -> n2(localhost TCP bridge) -> n3(USB ACM ttyGS0) -> n4(PID1/root shell)
## Path evidence
- `stage3/linux_init/init_v8.c:225-257` - Automatically configures and enables USB ACM gadget (creates command channel).
- `stage3/linux_init/init_v8.c:998-1023` - Main path enables gadget, waits for ttyGS0, attaches console, enters shell_loop.
- `stage3/linux_init/init_v8.c:864-983` - Command dispatcher exposes sensitive operations with no auth gate.
- `stage3/linux_init/init_v8.c:660-687` - run command executes arbitrary path via execve.
- `scripts/revalidation/serial_tcp_bridge.py:17-18` - Default listener is localhost:54321.
- `scripts/revalidation/serial_tcp_bridge.py:51-57` - Opens TCP listener.
- `scripts/revalidation/serial_tcp_bridge.py:126-138` - Accepts client with no authentication/authorization.
- `scripts/revalidation/serial_tcp_bridge.py:187-213` - Blindly forwards client bytes to serial endpoint.
- `scripts/revalidation/README.md:20-23` - Describes bridge as minimal quick-development gate exposing USB ACM shell over localhost.
- `README.md:1-5` - Repository is framed as a personal native Linux rechallenge workspace (experimental context).
## Narrative
Static evidence confirms a real authz/authn gap: init_v8 configures USB ACM, attaches /dev/ttyGS0, and enters shell_loop with privileged commands and no authentication; serial_tcp_bridge.py then opens a localhost TCP port and forwards client bytes directly to that shell without auth checks. Validation artifacts include an executable PoC showing unauthenticated command injection resulting in uid=0 on the device. However, repository context indicates this is experimental local lab tooling rather than an exposed production service.
## Controls
- Default bind to 127.0.0.1
- Single-client limit in bridge
- No authentication/authorization controls on shell or bridge
## Blindspots
- Static-only review cannot confirm how often init_v8 or bridge are used outside lab workflows.
- No formal threat model file defines whether hostile co-tenants on the host are in scope.
- No deployment manifests/services found to establish production exposure.
