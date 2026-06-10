#!/usr/bin/env python3
"""Focused regression tests for Codex security Unit A guardrails."""

from __future__ import annotations

import importlib
import io
import os
import pathlib
import tempfile
import unittest
from contextlib import redirect_stdout


class UnitASecurityRegression(unittest.TestCase):
    def test_bridge_repair_dirs_rejects_private_symlink(self) -> None:
        bridge = importlib.import_module("a90_bridge")
        original_rels = bridge.PRIVATE_REPAIR_RELS
        try:
            with tempfile.TemporaryDirectory(prefix="a90-bridge-repair-test-") as temp_dir:
                root = pathlib.Path(temp_dir)
                outside = root / "outside"
                outside.mkdir()
                private_link = root / "workspace" / "private"
                private_link.parent.mkdir(parents=True)
                private_link.symlink_to(outside, target_is_directory=True)
                bridge.PRIVATE_REPAIR_RELS = ("workspace/private/logs/bridge",)

                class Args:
                    user = None
                    json = True

                with redirect_stdout(io.StringIO()):
                    rc = bridge.command_repair_dirs(Args(), root)
                self.assertEqual(rc, 1)
        finally:
            bridge.PRIVATE_REPAIR_RELS = original_rels

    def test_a90ctl_does_not_retry_unsafe_busy_response(self) -> None:
        a90ctl = importlib.import_module("a90ctl")
        calls: list[str] = []
        original_exchange = a90ctl.bridge_exchange
        try:
            def fake_exchange(*args: object, **kwargs: object) -> str:
                calls.append("call")
                return a90ctl.BRIDGE_BUSY_TEXT

            a90ctl.bridge_exchange = fake_exchange
            with self.assertRaisesRegex(RuntimeError, "not retrying"):
                a90ctl.run_cmdv1_command(
                    "127.0.0.1",
                    54321,
                    1.0,
                    ["run", "/cache/bin/toybox", "true"],
                )
            self.assertEqual(calls, ["call"])
        finally:
            a90ctl.bridge_exchange = original_exchange

    def test_ncm_candidates_require_samsung_product_id(self) -> None:
        ncm = importlib.import_module("a90_ncm_transport")
        base = {
            "driver": ncm.A90_USB_NCM_DRIVER,
            "usb_vendor": ncm.A90_USB_VENDOR_ID,
            "link_local": "fe80::1",
            "ifname": "enx1",
        }
        wrong_product = dict(base, usb_product="ffff")
        right_product = dict(base, usb_product=ncm.A90_USB_PRODUCT_ID)
        self.assertEqual(ncm.host_ncm_candidates([wrong_product], require_link_local=True), [])
        self.assertEqual(ncm.host_ncm_candidates([right_product], require_link_local=True), [right_product])

    def test_ncm_host_repair_is_opt_in(self) -> None:
        ncm = importlib.import_module("a90_ncm_transport")
        old_env = os.environ.pop(ncm.NCM_REPAIR_HOST_NET_ENV, None)
        try:
            session = ncm.FastTransferSession(None, [], run_step=lambda *args, **kwargs: {})
            self.assertFalse(session.repair_host_net)
        finally:
            if old_env is not None:
                os.environ[ncm.NCM_REPAIR_HOST_NET_ENV] = old_env

    def test_ncm_listener_bind_tuple_is_not_wildcard(self) -> None:
        ncm = importlib.import_module("a90_ncm_transport")

        localhost_tuple = ncm.scoped_ipv6_bind_tuple("::1", "missing0", 12345)
        linklocal_tuple = ncm.scoped_ipv6_bind_tuple("fe80::1", "lo", 0)

        self.assertEqual(localhost_tuple, ("::1", 12345, 0, 0))
        self.assertNotEqual(localhost_tuple[0], "::")
        self.assertEqual(linklocal_tuple[0], "fe80::1")
        self.assertGreater(linklocal_tuple[3], 0)


if __name__ == "__main__":
    unittest.main()
