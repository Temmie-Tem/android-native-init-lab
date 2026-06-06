# Secrets

Place local-only env files and credentials here. Use `0600` permissions. Never
copy secrets into logs, archives, manifests, public summaries, or commits.

The Wi-Fi connect runner checks `workspace/private/secrets/a90-wifi-test.env`
before the legacy `tmp/wifi/.wifi-test.env` path. Supported lines use
`KEY=value` or `export KEY=value` syntax.
