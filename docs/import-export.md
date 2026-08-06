# Import, export and migration

`baymax export --output profile.zip` writes format version 2 with SHA-256 checksums, recursively redacted app settings, personality/system prompt, deterministic safety metadata, and TOML model profiles. Add `--include-reminders` only with explicit consent. `baymax import --input profile.zip --settings-output imported-settings.json` validates size, format, schema, checksums and archive paths before copying profiles and writing settings for review. Add `--import-reminders` only to insert validated reminder definitions into the selected local database. Version 1 archives are migrated in memory; unknown future versions fail closed.

Personal database export is separate: `baymax data export --output data.json`. Destructive deletion requires `baymax data delete --yes`. Secrets, keys, passwords, private tokens, raw audio, models and logs are never included by default.
