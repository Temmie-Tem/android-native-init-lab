"""Static tests for Wi-Fi supplicant config ENOSPC fallback."""

from __future__ import annotations

import unittest
from pathlib import Path


SOURCE = Path("workspace/public/src/native-init/a90_wificfg.c")


class NativeWifiCacheEnospcFallbackSourceTests(unittest.TestCase):
    def test_supplicant_config_enospc_fallback_is_bounded(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("wificfg_storage_pressure_rc", source)
        self.assertIn("rc == -ENOSPC || rc == -EDQUOT", source)
        self.assertIn("wificfg_write_supplicant_text_inplace", source)
        self.assertIn("wificfg_write_supplicant_text_storage_fallback", source)
        self.assertIn("WIFICFG_ENOSPC_INPLACE_FALLBACK_MARKER", source)
        self.assertIn("wifi-config-enospc-inplace-fallback", source)
        self.assertIn("wifi_config_cache_fallback=", source)
        self.assertIn("O_WRONLY | O_TRUNC | O_CLOEXEC | O_NOFOLLOW", source)
        self.assertIn("fstat(fd, &st) < 0 || !S_ISREG(st.st_mode)", source)
        self.assertIn("fchmod(fd, 0600)", source)
        self.assertIn("write_all_checked(fd, text, text_len)", source)
        self.assertIn("*bytes_out = text_len", source)
        self.assertIn("wificfg_secure_zero(text, sizeof(text))", source)

    def test_fallback_does_not_delete_broad_cache_paths(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        fallback = source[source.index("static int wificfg_write_supplicant_text_inplace"):
                          source.index("static int wificfg_write_supplicant_text(")]

        self.assertNotIn("unlink(", fallback)
        self.assertNotIn("rmdir(", fallback)
        self.assertNotIn("/cache/boot", fallback)
        self.assertNotIn("/cache/a90-runtime", fallback)
        self.assertNotIn("/mnt/sdext/a90/secrets", fallback)


if __name__ == "__main__":
    unittest.main()
