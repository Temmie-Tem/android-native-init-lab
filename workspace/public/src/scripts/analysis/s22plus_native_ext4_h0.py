#!/usr/bin/env python3
"""Build and qualify the fixed ARM64 ext4 helper; no device access or live grant."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "workspace/public/src/scripts/revalidation"))
import s22plus_native_ext4_profile_v1 as profile
import s22plus_native_gpt_source_v1 as predecessor
from s22plus_native_records_v3 import _identity, pin, private_path, publish, read, require, verify

NATIVE = ROOT / "workspace/public/src/native-init"
UPSTREAM_URL = "https://www.kernel.org/pub/linux/kernel/people/tytso/e2fsprogs/v1.47.2/e2fsprogs-1.47.2.tar.xz"
UPSTREAM_SHA256 = "08242e64ca0e8194d9c1caad49762b19209a06318199b63ce74ae4ef2d74e63c"
ARCHIVE_MAXIMUM = 16 * 1024 * 1024
CONFIGURE = (
    "--host=aarch64-linux-gnu", "--build=x86_64-linux-gnu",
    "--enable-libuuid", "--enable-libblkid", "--disable-nls",
    "--disable-elf-shlibs", "--disable-uuidd", "--disable-fsck",
    "--disable-e2initrd-helper", "--disable-fuse2fs", "--without-libarchive",
    "--disable-backtrace", "--without-crond-dir", "--without-systemd-unit-dir",
)
CONFIGURE_ENV = dict(CC="aarch64-linux-gnu-gcc", AR="aarch64-linux-gnu-ar",
                     RANLIB="aarch64-linux-gnu-ranlib", CFLAGS="-Os -fno-ident",
                     LDFLAGS="-static", PKG_CONFIG="false", SOURCE_DATE_EPOCH="1735689600")
SOURCE_FILES = (
    Path(__file__), Path(profile.__file__),
    NATIVE / "s22plus_native_ext4_v1.c", NATIVE / "s22plus_native_ext4_core_v1.h",
    NATIVE / "s22plus_fyg8_max77705_result_parser.inc.c",
)


def build_tools(archive, directory):
    """Build from the pinned upstream archive, with a recorded fixed toolchain."""
    archive = private_path(ROOT, archive)
    upstream = pin(archive, maximum=ARCHIVE_MAXIMUM)
    require(upstream["sha256"] == UPSTREAM_SHA256, "e2fsprogs source archive differs")
    directory = private_path(ROOT, directory, exists=False)
    require(not directory.exists(), "fresh e2fsprogs output required")
    tools = [shutil.which(name) for name in
             ("aarch64-linux-gnu-gcc", "aarch64-linux-gnu-ar", "aarch64-linux-gnu-ranlib",
              "aarch64-linux-gnu-as", "aarch64-linux-gnu-ld", "make")]
    require(all(tools), "formatter build toolchain is incomplete")
    compiler = tools[0]
    for library in ("libc.a", "libm.a", "libpthread.a", "libgcc.a", "libgcc_eh.a",
                    "crt1.o", "crti.o", "crtn.o", "crtbeginT.o", "crtend.o"):
        value = subprocess.check_output([compiler, "-print-file-name=" + library], text=True).strip()
        require(value != library and Path(value).is_file(), "ARM64 link input unavailable: " + library)
        tools.append(value)
    cc1 = subprocess.check_output([compiler, "-print-prog-name=cc1"], text=True).strip()
    require(Path(cc1).is_file(), "ARM64 cc1 unavailable")
    tools.append(cc1)
    toolchain = [compiler_identity(path) for path in tools]
    directory.mkdir(mode=0o700, parents=True)
    producer_snapshot = directory / "producer-source.py"
    producer_snapshot.write_bytes(Path(__file__).read_bytes()); producer_snapshot.chmod(0o400)
    with tarfile.open(archive) as source:
        members = source.getmembers()
        require(all(member.name == "e2fsprogs-1.47.2" or
                    member.name.startswith("e2fsprogs-1.47.2/") for member in members),
                "source archive root differs")
        source.extractall(directory, filter="data")
    source_directory = directory / "e2fsprogs-1.47.2"
    build = directory / "build"; build.mkdir(mode=0o700)
    env = dict(PATH="/usr/bin:/bin", LC_ALL="C", **CONFIGURE_ENV)
    commands = [
        ("configure", [str(source_directory / "configure"), *CONFIGURE]),
        ("libraries", ["make", "-j2", "libs"]),
        ("formatter", ["make", "-C", "misc", "-j2", "mke2fs.static"]),
        ("checker", ["make", "-C", "e2fsck", "-j2", "e2fsck.static"]),
    ]
    request = publish(directory / "build-request.json", dict(
        upstream=upstream, environment=env, commands=commands, toolchain=toolchain,
        producer=pin(producer_snapshot), device_effects=0))
    for label, argv in commands:
        run(argv, cwd=build, env=env, stdout=directory / (label + ".log"))
    require([compiler_identity(path) for path in tools] == toolchain,
            "formatter toolchain changed during build")
    require(pin(archive, maximum=ARCHIVE_MAXIMUM) == upstream, "formatter archive changed during build")
    formatter = tool_identity(build / "misc/mke2fs.static")
    checker = tool_identity(build / "e2fsck/e2fsck.static")
    value = dict(schema="s22plus-native-ext4-tools-h0-v1", upstream=upstream,
                 request=request, formatter=formatter, checker=checker,
                 generated_config=pin(build / "lib/config.h"),
                 logs=[pin(directory / (label + ".log")) for label, _ in commands],
                 device_effects=0, live_authorized=False)
    return publish(directory / "result.json", value)


def verify_tools(receipt):
    value = read(verify(receipt)); request = read(verify(value["request"]))
    require(value["schema"] == "s22plus-native-ext4-tools-h0-v1" and
            value["upstream"] == request["upstream"] and
            value["upstream"]["sha256"] == UPSTREAM_SHA256 and
            value["device_effects"] == 0 and value["live_authorized"] is False,
            "formatter source/build provenance differs")
    verify(value["upstream"], maximum=ARCHIVE_MAXIMUM); verify(value["generated_config"])
    verify(request["producer"])
    require(Path(request["producer"]["path"]) == Path(value["request"]["path"]).parent / "producer-source.py",
            "formatter producer snapshot belongs elsewhere")
    require(request["environment"] == dict(PATH="/usr/bin:/bin", LC_ALL="C", **CONFIGURE_ENV),
            "formatter build environment differs")
    commands = request["commands"]
    source = Path(value["request"]["path"]).parent / "e2fsprogs-1.47.2/configure"
    require(commands == [["configure", [str(source), *CONFIGURE]],
                         ["libraries", ["make", "-j2", "libs"]],
                         ["formatter", ["make", "-C", "misc", "-j2", "mke2fs.static"]],
                         ["checker", ["make", "-C", "e2fsck", "-j2", "e2fsck.static"]]],
            "formatter build commands differ")
    for row in value["logs"]: verify(row)
    for key in ("formatter", "checker"):
        verify(value[key]); require(tool_identity(value[key]["path"]) == value[key], "tool ELF pin differs")
    return value


def qualify_tools(receipt, directory):
    """Actual ARM64 formatter/checker over one disposable exact-size regular file.

    Synthetic scratch data is placed in a private temporary directory on the
    host's tmpfs; permanent evidence and all payloads remain workspace/private.
    No existing file or host block device can be selected as a format target.
    """
    tools = verify_tools(receipt)
    directory = private_path(ROOT, directory, exists=False)
    require(not directory.exists(), "fresh formatter qualification required")
    directory.mkdir(mode=0o700, parents=True)
    config = directory / "mke2fs.conf"; config.write_bytes(profile.CONFIG); config.chmod(0o400)
    fixture_uuid = "11111111-2222-4333-8444-555555555555"
    with tempfile.TemporaryDirectory(prefix="s22-ext4-geometry-", dir="/tmp") as scratch:
        scratch = Path(scratch)
        require(shutil.disk_usage(scratch).free > 2300 * 1024 * 1024,
                "insufficient disposable geometry-fixture capacity")
        image = scratch / "native.img"
        with image.open("xb") as file:
            file.truncate(profile.SIZE_BYTES)
        started = time.monotonic()
        argv = ["qemu-aarch64", *profile.formatter_argv(tools["formatter"]["path"], str(image), fixture_uuid)]
        run(argv, cwd=directory, env=dict(PATH="/usr/bin:/bin", LC_ALL="C", MKE2FS_CONFIG=str(config)),
            stdout=directory / "format.stdout", stderr=directory / "format.stderr", timeout=180)
        format_seconds = time.monotonic() - started
        require(not (directory / "format.stdout").read_bytes() and
                not (directory / "format.stderr").read_bytes(), "formatter diagnostics differ")
        with image.open("rb") as file:
            file.seek(1024); superblock = file.read(1024)
        value = profile.superblock(superblock, fixture_uuid)
        (directory / "superblock.bin").write_bytes(superblock)
        started = time.monotonic()
        run(["qemu-aarch64", tools["checker"]["path"], "-fn", image], cwd=directory,
            env=dict(PATH="/usr/bin:/bin", LC_ALL="C"),
            stdout=directory / "check.stdout", stderr=directory / "check.stderr", timeout=180)
        check_seconds = time.monotonic() - started
        require((directory / "check.stderr").read_bytes() == profile.CHECKER_STDERR,
                "checker diagnostic version differs")
        with image.open("rb") as file:
            file.seek(1024); require(file.read(1024) == superblock, "read-only checker changed superblock")
            file.seek(profile.SIZE_BYTES - profile.BLOCK_SIZE); tail = file.read(profile.BLOCK_SIZE)
        require(len(tail) == profile.BLOCK_SIZE and image.stat().st_size == profile.SIZE_BYTES,
                "large filesystem offsets or size differ")
        value.update(schema="s22plus-native-ext4-tools-qualification-h0-v1", tools=receipt,
                     configuration=pin(config), fixture_size=image.stat().st_size,
                     fixture_allocated=image.stat().st_blocks * 512,
                     last_block_sha256=hashlib.sha256(tail).hexdigest(),
                     format_seconds=format_seconds, check_seconds=check_seconds,
                     formatter_exit=0, checker_exit=0, mounted=False,
                     target_kernel_mount_proved=False, device_effects=0)
    value.update(fixture_removed=True, superblock=pin(directory / "superblock.bin"),
                 logs=[pin(directory / name) if (directory / name).stat().st_size else
                       dict(path=str(directory / name), size=0, sha256=hashlib.sha256(b"").hexdigest())
                       for name in ("format.stdout", "format.stderr", "check.stdout", "check.stderr")])
    return publish(directory / "result.json", value)


def run(argv, *, cwd, stdout, stderr=None, timeout=300, env=None):
    with Path(stdout).open("xb") as out:
        if stderr is None:
            result = subprocess.run([str(a) for a in argv], cwd=cwd, env=env,
                                    stdout=out, stderr=subprocess.STDOUT, timeout=timeout)
        else:
            with Path(stderr).open("xb") as err:
                result = subprocess.run([str(a) for a in argv], cwd=cwd, env=env,
                                        stdout=out, stderr=err, timeout=timeout)
    require(result.returncode == 0, "H0 producer failed: " + Path(stdout).name)


def tool_identity(path):
    path = private_path(ROOT, path)
    description = subprocess.check_output(["file", "-b", path], text=True).strip()
    headers = subprocess.check_output(["aarch64-linux-gnu-readelf", "-W", "-l", path])
    require("ARM aarch64" in description and "statically linked" in description
            and b"INTERP" not in headers, "filesystem tool is not a static ARM64 ELF")
    return pin(path)


def compiler_identity(path):
    """Distribution tool binaries can have legitimate root-owned hard links."""
    path = Path(path).resolve(strict=True)
    before = path.stat()
    require(stat.S_ISREG(before.st_mode) and before.st_uid == 0 and
            not before.st_mode & 0o022 and 0 < before.st_size < 64 * 1024 * 1024,
            "host compiler metadata differs")
    raw = path.read_bytes()
    require(_identity(before) == _identity(path.stat()) and len(raw) == before.st_size,
            "host compiler changed during read")
    return dict(path=str(path), size=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def kernel_configuration(path):
    path = private_path(ROOT, path)
    raw = path.read_bytes()
    start = raw.find(b"IKCFG_ST")
    end = raw.find(b"IKCFG_ED", start + 8)
    require(start >= 0 and end > start, "selected Image has no bounded IKCONFIG")
    config = gzip.decompress(raw[start + 8:end]).decode("ascii")
    keys = ("CONFIG_EXT4_FS", "CONFIG_EXT4_FS_POSIX_ACL", "CONFIG_EXT4_FS_SECURITY",
            "CONFIG_JBD2", "CONFIG_FS_MBCACHE", "CONFIG_TMPFS", "CONFIG_NAMESPACES",
            "CONFIG_DEVTMPFS", "CONFIG_PID_NS", "CONFIG_USER_NS")
    facts = {}
    for key in keys:
        matches = re.findall(r"^" + re.escape(key) + r"=(.+)$", config, re.M)
        disabled = "# " + key + " is not set" in config.splitlines()
        require(len(matches) + int(disabled) == 1, "ambiguous kernel option: " + key)
        facts[key] = matches[0] if matches else "n"
    require(all(facts[key] == "y" for key in keys[:7]), "required ext4 runtime is absent")
    return dict(image=pin(path, maximum=128 * 1024 * 1024),
                config_sha256=hashlib.sha256(config.encode()).hexdigest(), facts=facts)


def verify_qualification(receipt, tools):
    value = read(verify(receipt))
    require(value["schema"] == "s22plus-native-ext4-tools-qualification-h0-v1" and
            value["tools"] == tools and value["fixture_size"] == profile.SIZE_BYTES and
            value["formatter_exit"] == value["checker_exit"] == value["device_effects"] == 0 and
            value["fixture_removed"] is True and value["mounted"] is False and
            value["target_kernel_mount_proved"] is False,
            "exact-geometry formatter qualification differs")
    verify(value["configuration"]); verify(value["superblock"])
    require(Path(value["configuration"]["path"]).read_bytes() == profile.CONFIG,
            "qualified formatter configuration changed")
    profile.superblock(Path(value["superblock"]["path"]).read_bytes(),
                       "11111111-2222-4333-8444-555555555555")
    for row in value["logs"]:
        if row["size"]:
            verify(row)
        else:
            path = private_path(ROOT, row["path"])
            st = path.lstat()
            require(stat.S_ISREG(st.st_mode) and st.st_nlink == 1 and st.st_size == 0 and
                    row["sha256"] == hashlib.sha256(b"").hexdigest(),
                    "qualified empty tool output differs")
    return value


def create_binding(directory, *, tools, qualification, kernel, fs_uuid=None):
    directory = private_path(ROOT, directory, exists=False)
    require(not directory.exists(), "fresh filesystem binding directory required")
    layout, vectors = predecessor.proposal_inputs()
    require(layout["layout"]["native_size_bytes"] == profile.SIZE_BYTES,
            "filesystem extent differs from the preserved Android32 layout")
    fs_uuid = str(uuid.uuid4()) if fs_uuid is None else fs_uuid
    require(str(uuid.UUID(fs_uuid)) == fs_uuid, "filesystem UUID is not canonical")
    built = verify_tools(tools)
    verify_qualification(qualification, tools)
    directory.mkdir(mode=0o700, parents=True)
    config = directory / "mke2fs.conf"
    config.write_bytes(profile.CONFIG); config.chmod(0o400)
    gpt = directory / "expected-gpt.bin"
    gpt.write_bytes(vectors["proposed"]); gpt.chmod(0o400)
    value = dict(schema="s22plus-native-ext4-binding-h0-v1", active=False,
                 layout_proposal=predecessor.PROPOSAL, expected_gpt=pin(gpt),
                 filesystem_uuid=fs_uuid, block_size=profile.BLOCK_SIZE,
                 block_count=profile.BLOCK_COUNT, size_bytes=profile.SIZE_BYTES,
                 features=list(profile.FEATURES), witness_sha256=profile.WITNESS_SHA256,
                 tools=tools, qualification=qualification,
                 formatter=built["formatter"], checker=built["checker"],
                 configuration=pin(config), kernel=kernel_configuration(kernel),
                 formatter_source=dict(url=UPSTREAM_URL, sha256=UPSTREAM_SHA256),
                 source_inputs=[pin(path) for path in SOURCE_FILES], device_effects=0)
    return publish(directory / "binding.json", value)


def seal(binding, run_id, *, initialize):
    require(re.fullmatch(r"[0-9a-f]{32}", run_id) is not None and type(initialize) is bool,
            "invalid compiled native role")
    value = read(verify(binding))
    require(value["schema"] == "s22plus-native-ext4-binding-h0-v1" and value["active"] is False,
            "filesystem binding is not the declared H0 schema")
    built = verify_tools(value["tools"])
    verify_qualification(value["qualification"], value["tools"])
    require(all(value[key] == built[key] for key in ("formatter", "checker")),
            "filesystem tools do not join the qualified producer")
    for key in ("formatter", "checker", "configuration", "expected_gpt", "layout_proposal"):
        verify(value[key])
    require(Path(value["configuration"]["path"]).read_bytes() == profile.CONFIG and
            (value["block_count"], value["block_size"], value["size_bytes"], value["features"],
             value["witness_sha256"]) ==
            (profile.BLOCK_COUNT, profile.BLOCK_SIZE, profile.SIZE_BYTES, list(profile.FEATURES),
             profile.WITNESS_SHA256), "filesystem declaration changed")
    original, vectors = predecessor.proposal_inputs()
    require(value["layout_proposal"] == predecessor.PROPOSAL and
            Path(value["expected_gpt"]["path"]).read_bytes() == vectors["proposed"],
            "filesystem GPT does not join the exact Android32 proposal")
    rows = ["/* Private, generated target seal. Never commit this file. */",
            "#define FS1_ALLOW_FORMAT " + str(int(initialize)),
            'static const char fs1_run_id[]="' + run_id + '";',
            'static const char fs1_uuid_text[]="' + value["filesystem_uuid"] + '";']

    def array(name, raw):
        rows.append("static const uint8_t " + name + "[" + str(len(raw)) + "]={" +
                    ",".join(map(str, raw)) + "};")

    array("fs1_uuid", uuid.UUID(value["filesystem_uuid"]).bytes)
    array("fs1_sealed_gpt", vectors["proposed"])
    for name, key in (("formatter", "formatter"), ("checker", "checker"), ("config", "configuration")):
        rows.append("static const uint64_t fs1_" + name + "_size=" + str(value[key]["size"]) + "ULL;")
        array("fs1_" + name + "_sha256", bytes.fromhex(value[key]["sha256"]))
    return ("\n".join(rows) + "\n").encode()


def build_helper(binding, output, run_id, *, initialize):
    sources = [pin(path) for path in SOURCE_FILES]
    output = private_path(ROOT, output, exists=False)
    require(not output.exists(), "fresh filesystem helper output required")
    output.mkdir(mode=0o700, parents=True)
    (output / "s22plus_native_ext4_seal_v1.h").write_bytes(seal(binding, run_id, initialize=initialize))
    flags = ["-std=c11", "-static", "-Os", "-fno-ident", "-Wall", "-Wextra", "-Werror",
             "-Wno-unused-function", "-I", output, "-I", NATIVE]
    compiler = shutil.which("aarch64-linux-gnu-gcc")
    require(compiler is not None, "ARM64 compiler unavailable")
    compiler_pin = compiler_identity(compiler)
    for side in ("a", "b"):
        run([compiler, *flags, NATIVE / "s22plus_native_ext4_v1.c", "-o", output / ("helper-" + side)],
            cwd=ROOT, stdout=output / ("compile-" + side + ".log"), timeout=60)
    require((output / "helper-a").read_bytes() == (output / "helper-b").read_bytes(),
            "filesystem helper A/B differs")
    value = dict(schema="s22plus-native-ext4-helper-h0-v1", binding=binding,
                 run_id_hex=run_id, initialize=initialize, helper=tool_identity(output / "helper-a"),
                 ab_identical=True, source_inputs=sources,
                 compiler=compiler_pin, device_effects=0, live_authorized=False)
    require(compiler_identity(compiler) == compiler_pin, "compiler changed during helper build")
    require([pin(path) for path in SOURCE_FILES] == sources, "filesystem sources changed during helper build")
    return publish(output / "result.json", value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binding", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--initialize-role", action="store_true")
    args = parser.parse_args()
    print(json.dumps(build_helper(pin(private_path(ROOT, args.binding)), args.output,
                                  args.run_id, initialize=args.initialize_role), sort_keys=True))


if __name__ == "__main__":
    main()
