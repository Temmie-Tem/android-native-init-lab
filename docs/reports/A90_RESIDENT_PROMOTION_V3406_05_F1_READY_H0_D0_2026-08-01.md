# A90 V3406-05 resident promotion F1 readiness

## Result

Fresh private run `a90-v3406-debian-display-f1-20260801-05` is ready for one
fresh exact F1 approval. Preparation itself granted no live authority and did
not stage a rootfs, transfer a boot image, flash, or reboot.

The previous `-04` preparation stopped host-only. The first stop was a new
review report created with group-write permission; the second exposed a stale
transitive guard-helper size constant. No live action occurred. Its partially
published private files are preserved as failed preparation evidence and are
not reusable. Commit `e73a72a6` binds the actual 51402-byte helper size and a
direct filesystem-size regression assertion; independent review returned GO.

## Fresh inputs and connected D0

The `-05` materializer created a new-inode 2 GiB keyed ext4 rootfs from the
reviewed clean A/B image, generated a single-run observer key, passed read-only
`e2fsck`, and proved the required runtime paths absent in the image.

One exact connected A90 D0 then proved:

- exact V2321 version/build;
- selftest `fail=0`;
- pstore `entries=0`; and
- the run-derived final path, fixed work path, and run stage path all absent.

The D0 sent bounded read-only framed commands only. Device writes, payload
transfer, flash, and reboot were all false. The separately connected S22+
received no command.

## Immutable live binding

- resident manifest SHA256: `58e2a0a401c2493df610a29fde9e583564f90a6e07e7cb597464dc8f54e2de9b`
- approval binding SHA256: `33afdf2a8a8d085a3c62bebf4c89d8d31d722739807730566837974a1ca4213d`
- orchestrator SHA256: `aa0677077ddf82ed559a2b703e599ee05c3fa77f7023260d193c01c462b25b20`
- resident runner SHA256: `0e18d50ee059419b273f7af9d3735e8ac8c5ee49c825973f3c36f1adcc7a13c8`
- keyed rootfs SHA256: `25450c341bb1ff1281dfe5f805516e697d268f79abfc5f25fb41f7411f025f31`
- candidate boot SHA256: `3d3e66535654a62f83c5772caba27624acc160911307190de458154acaefdabb`
- exact rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`

The production resident inspector reports `contract_issues=[]`, exact
resident-promotion mode, and fresh operator approval required. The private
approval receipt exists but has `f1_authorized=false` and
`live_authorized=false`.

## Next gate

The only next gate is the operator echoing the exact prepared F1 token. That
token authorizes one boot-only candidate attempt and its mandatory exact
rollback. Until then there is no A90 F1 authority. The consumed `-03` token and
candidate remain non-reusable.
