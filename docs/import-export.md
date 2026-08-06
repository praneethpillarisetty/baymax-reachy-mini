# Import, export and migration

`baymax export --output profile.zip` writes versioned manifest, non-secret settings and TOML model profiles. Add `--include-reminders` only with explicit consent. `baymax import --input profile.zip` validates format/version and archive paths before copying profiles; it prints settings for review rather than silently overwriting active configuration.

Personal database export is separate: `baymax data export --output data.json`. Destructive deletion requires `baymax data delete --yes`. Secrets, keys, passwords, private tokens, raw audio, models and logs are never included by default.
