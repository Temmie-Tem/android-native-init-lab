"""Execute the four stock g0q HAL proxy entry points to their Parcel boundaries.

The Android framework imports below are an in-memory recorder. No Android
service manager, Binder driver, USB transport or socket is available here.
"""
from hashlib import sha256
from io import BytesIO
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE, UC_PROT_READ, UC_PROT_EXEC
from unicorn import arm64_const as reg

HAL_SHA256 = "8bbf25ee2ea747edf4c165d6b5856f499dae1a0e1b80bcec415cb11a673070c2"
METHODS = {"open": "8BpHwdiag4openE", "write": "8BpHwdiag5writeE",
           "callback": "16BpHwdiagcallback9send_dataE", "close": "8BpHwdiag5closeE"}
STUBS = 0x100000
HEAP = 0x200000
SELF, MEMORY, HANDLE, BACKING = (HEAP + i for i in (256, 512, 768, 1024))
CALLBACK = HEAP + 2048
IPC = b"vendor.qti.diaghal@1.0::Idiag"
WORD = struct.Struct("<Q")


def check(condition, message):
    if not condition:
        raise ValueError(message)


class StockProxy:
    def __init__(self, path):
        raw = path.read_bytes()
        check(sha256(raw).hexdigest() == HAL_SHA256, "unexpected HAL ELF")
        elf = ELFFile(BytesIO(raw))
        self.cpu = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        self.cpu.mem_map(0, 0x24000)
        for seg in elf.iter_segments():
            if seg["p_type"] == "PT_LOAD":
                self.cpu.mem_write(seg["p_vaddr"], seg.data())
        self.cpu.mem_map(STUBS, 0x1000)
        self.cpu.mem_map(HEAP, 0x20000)
        symbols = elf.get_section_by_name(".dynsym")
        self.entry = {}
        for method, fragment in METHODS.items():
            value, = (s["st_value"] for s in symbols.iter_symbols() if fragment in s.name)
            self.entry[method] = value
        # These two GLOB_DAT slots are from the pinned ELF's Android packed
        # relocations. RELR needs no adjustment at bias zero.
        for slot, descriptor in ((0x22688, 0x23b80), (0x226b0, 0x23b88)):
            self.cpu.mem_write(slot, WORD.pack(descriptor))
        self.imports = {}
        for i, rel in enumerate(elf.get_section_by_name(".rela.plt").iter_relocations()):
            symbol = symbols.get_symbol(rel["r_info_sym"])
            address = symbol["st_value"]
            if not address:
                address = STUBS + i * 4
                self.imports[address] = symbol.name
                self.cpu.mem_write(address, bytes.fromhex("c0035fd6"))  # ret
            self.cpu.mem_write(rel["r_offset"], WORD.pack(address))
        self.cpu.mem_protect(0, 0xe000, UC_PROT_READ)
        self.cpu.mem_protect(0xe000, 0x12000, UC_PROT_READ | UC_PROT_EXEC)
        self.cpu.mem_protect(STUBS, 0x1000, UC_PROT_READ | UC_PROT_EXEC)
        self.cpu.hook_add(UC_HOOK_CODE, self._framework_call, begin=STUBS, end=STUBS+0xfff)

    def _framework_call(self, cpu, address, size, user):
        name = self.imports[address]
        a, b, c, d = [cpu.reg_read(reg.UC_ARM64_REG_X0 + n) for n in range(4)]
        if name == "atrace_get_enabled_tags" or "ParcelC1Ev" in name:
            pass
        elif "writeInterfaceToken" in name:
            token = bytes(cpu.mem_read(b, 48)).split(b"\0", 1)[0]
            expected = IPC + (b"callback" if self.method == "callback" else b"")
            check(token == expected, "interface mismatch")
            self.parcel = a
            self.events.append("interface")
        elif "getOrCreateCachedBinder" in name:
            check(self.method == "open" and a == CALLBACK, "unexpected callback")
            cpu.mem_write(cpu.reg_read(reg.UC_ARM64_REG_X8), WORD.pack(HANDLE))
        elif "writeStrongBinder" in name:
            check(a == self.parcel and cpu.mem_read(b, 8) == WORD.pack(HANDLE), "callback reference")
            self.events.append("callback_ref")
            cpu.emu_stop()
        elif "writeBuffer" in name:
            check(a == self.parcel and b == MEMORY and c == 40, "hidl_memory argument")
            self.mem_object = bytes(cpu.mem_read(b, c))
            cpu.mem_write(d, WORD.pack(1))
            self.events.append("memory")
        elif "writeEmbeddedToParcel" in name:
            check((a, b, c, d) == (MEMORY, self.parcel, 1, 0), "embedded memory reference")
            self.events.append("embedded")
        elif "writeUint32" in name:
            check(a == self.parcel and self.mem_object is not None, "unbound length")
            handle, _, length = struct.unpack_from("<QQQ", self.mem_object)
            check(handle == HANDLE and length == b and b <= 320, "memory size or handle")
            # The test allocator alone maps this opaque native handle to its
            # backing. Consume only the object and byte count passed by the HAL.
            self.delivered = bytes(cpu.mem_read(BACKING, b))
            self.events.append("length")
        elif "IInterface8asBinder" in name:
            check(a == SELF + 8, "unexpected receiver")
            self.events.append("binder_lookup")
            cpu.emu_stop()
        else:
            raise ValueError(f"unmodelled Android framework import: {name}")
        cpu.reg_write(reg.UC_ARM64_REG_X0, 0)

    def call(self, method, body=b""):
        check(method in METHODS and len(body) <= 320, "unsupported fixture call")
        self.method, self.events, self.delivered = method, [], None
        self.mem_object, self.parcel = None, None
        self.cpu.mem_write(BACKING, body or b"\0")
        memory = struct.pack("<QQQ16x", HANDLE, 0, len(body))
        self.cpu.mem_write(MEMORY, WORD.pack(CALLBACK) if method == "open" else memory)
        self.cpu.reg_write(reg.UC_ARM64_REG_X0, SELF)
        self.cpu.reg_write(reg.UC_ARM64_REG_X1, MEMORY)
        self.cpu.reg_write(reg.UC_ARM64_REG_X2, len(body))
        self.cpu.reg_write(reg.UC_ARM64_REG_X8, HEAP + 2240)
        self.cpu.reg_write(reg.UC_ARM64_REG_TPIDR_EL0, HEAP)
        self.cpu.reg_write(reg.UC_ARM64_REG_SP, HEAP + 0x1f000)
        self.cpu.emu_start(self.entry[method], 0, count=1000)
        sequence = {"open": ["interface", "callback_ref"], "close": ["interface", "binder_lookup"]}
        expected = sequence.get(method, ["interface", "memory", "embedded", "length", "binder_lookup"])
        check(self.events == expected, f"incomplete {method} marshalling: {self.events}")
        return self.delivered


class StockRouter:
    """Check the stock service's write mapping boundary and entire close method."""
    def __init__(self, path):
        import lzma
        raw = path.read_bytes()
        check(sha256(raw).hexdigest() == "9e0d03f2fb35fd4ff7f621bdf3e6bb3403de0560a26ed85f873189ac6a33c8d4",
              "unexpected router ELF")
        elf = ELFFile(BytesIO(raw))
        debug = lzma.decompress(elf.get_section_by_name(".gnu_debugdata").data())
        symbols = ELFFile(BytesIO(debug)).get_section_by_name(".symtab")
        self.methods = {}
        for method, fragment in (("write", "11diagService5writeE"), ("close", "11diagService5closeE")):
            s, = [s for s in symbols.iter_symbols() if fragment in s.name]
            self.methods[method] = s["st_value"], s["st_size"]
        self.cpu = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        self.cpu.mem_map(0, 0x33000)
        for seg in elf.iter_segments():
            if seg["p_type"] == "PT_LOAD" and seg["p_vaddr"] < 0x33000:
                self.cpu.mem_write(seg["p_vaddr"], seg.data())
        self.cpu.mem_protect(0, 0x33000, UC_PROT_READ | UC_PROT_EXEC)
        self.cpu.mem_map(HEAP, 0x20000)
        # The three PLT entries are the pinned router's default-handle and
        # string constructors, then mapMemory. No router instruction is patched.
        for address in (0x324c0, 0x324d8, 0x32718):
            self.cpu.hook_add(UC_HOOK_CODE, self._import, begin=address, end=address)

    def _import(self, cpu, address, size, user):
        if address == 0x32718:
            check(cpu.reg_read(reg.UC_ARM64_REG_X0) == MEMORY, "router mapped another object")
            handle, _, length = struct.unpack("<QQQ", bytes(cpu.mem_read(MEMORY, 24)))
            check(handle == HANDLE and length == self.size, "router memory identity")
            self.mapped = bytes(cpu.mem_read(BACKING, length))
            cpu.emu_stop()
        else:
            cpu.reg_write(reg.UC_ARM64_REG_PC, cpu.reg_read(reg.UC_ARM64_REG_LR))

    def map_write(self, body):
        self.mapped, self.size = None, len(body)
        check(0 < self.size <= 320, "router fixture size")
        self.cpu.mem_write(MEMORY, struct.pack("<QQQ16x", HANDLE, 0, self.size))
        self.cpu.mem_write(BACKING, body)
        self.cpu.reg_write(reg.UC_ARM64_REG_X0, SELF)
        self.cpu.reg_write(reg.UC_ARM64_REG_X1, MEMORY)
        self.cpu.reg_write(reg.UC_ARM64_REG_X2, self.size)
        self.cpu.reg_write(reg.UC_ARM64_REG_X8, HEAP + 2240)
        self.cpu.reg_write(reg.UC_ARM64_REG_TPIDR_EL0, HEAP)
        self.cpu.reg_write(reg.UC_ARM64_REG_SP, HEAP + 0x1f000)
        self.cpu.emu_start(self.methods["write"][0], 0, count=100)
        check(self.mapped is not None, "stock service did not request memory mapping")
        return self.mapped

    def close(self):
        entry, size = self.methods["close"]
        check(size == 24, "unexpected router close size")
        # Execute with only code and result storage mapped. Any access to the
        # receiver, a registration table, TLS or a callee would fail this check.
        cpu = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        page = entry & ~4095
        cpu.mem_map(page, 4096)
        cpu.mem_write(entry, bytes(self.cpu.mem_read(entry, size)))
        cpu.mem_protect(page, 4096, UC_PROT_READ | UC_PROT_EXEC)
        cpu.mem_map(HEAP, 4096)
        cpu.mem_write(HEAP, b"\xa5" * 40)
        cpu.reg_write(reg.UC_ARM64_REG_X0, HEAP + 8192)
        cpu.reg_write(reg.UC_ARM64_REG_X8, HEAP)
        cpu.reg_write(reg.UC_ARM64_REG_LR, entry + size)
        cpu.emu_start(entry, entry + size, count=6)
        result = bytes(cpu.mem_read(HEAP, 40))
        check(cpu.reg_read(reg.UC_ARM64_REG_PC) == entry + size and
              result == bytes(33) + b"\xa5" * 3 + bytes(4), "unexpected close result")
