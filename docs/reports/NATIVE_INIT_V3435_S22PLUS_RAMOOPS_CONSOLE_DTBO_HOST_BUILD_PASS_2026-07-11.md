# V3435 S22+ Ramoops Console/Dmesg DTBO Host Build Pass

## Verdict

`HOST_BUILD_PASS_NO_LIVE`.

V3435 found why the prior ramoops attempts could not produce console or dmesg
records: the exact FYG8 node assigned its entire 2 MiB region to pmsg and had no
`console-size` or `record-size`. The new host-only candidate preserves the
allocation and adds real console/dmesg partitions.

No device contact, reboot, flash, partition write, or live authorization
occurred.

## Result

Candidate layout:

```text
pmsg      1 MiB
console   512 KiB
dmesg     512 KiB total
record    256 KiB x 2
```

Candidate identity:

```text
raw DTBO       3c4d38a9d4833bab648cd36c3c0c78a2bfed35ca80dc4532b5e877cbaa8fa281
LZ4            4202edca2a0d06ab691c492151b5f4228b1bd28eace06b1a72c36e35cac7c84b
AP.tar         839296660e6834e9e39bb207dbd676748c4dc2340fad1e96995d3f7e57d25ab9
AP.tar.md5     622ac0259eb61a7c9ef71eff44d4ea8bb3edbc6a90c3f2b237be7fdf88cb0264
```

The AP contains exactly one member, `dtbo.img.lz4`. A stock-DTBO-only rollback
AP is staged in the same private output tree.

## Container Proof

- Target overlays: DT table entries 9 and 10.
- Vendor roots checked: all four exact FYG8 vendor DTBs.
- Application matrix: 8/8 PASS.
- Target semantic diff: only status, pmsg-size, console-size, record-size.
- Non-target DT entries: byte-identical.
- DT entry sizes/offsets and table header: unchanged.
- Raw image size: unchanged at 8 MiB.
- Samsung 512-byte signer trailer: byte-identical.
- AVB metadata/footer region: byte-identical.
- Stock AVB descriptor digest: intentionally no longer matches the modified payload.
- Odin archive parse gate: candidate and rollback both reached the expected
  invalid-device boundary after archive recognition.

The no-growth construction is achieved by suffix-compacting each patched FDT
string table, reclaiming 140 bytes, and padding each blob back to its exact
stock size. This avoids shifting any Samsung or AVB trailer.

## Validation

```text
py_compile                                    PASS
V3435 focused tests                          11/11 PASS
V3426-V3435 regression tests               135/135 PASS (56.993 s)
vendor-DTB/overlay application matrix         8/8 PASS
candidate and rollback Odin AP member gate    PASS
device actions                                  0
```

## Next Gate

The next useful live unit is an Android-side positive control under a new
DTBO-only exception and a separate one-shot intentional-panic exception. It
must prove the backend live before panic and recover a run-bound marker after
reset. Direct-PID1 is not the first live target.

V3435 does not create those exceptions or authorize that run.
