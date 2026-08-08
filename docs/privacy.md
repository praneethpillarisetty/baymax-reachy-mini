# Privacy

The default mock/simulator path makes no network request. SQLite stores reminders, mood/hydration entries, and appointment notes at `DATABASE_PATH` (default `data/baymax.sqlite3`). No raw audio or transcript history is persisted. Ollama is opt-in and must remain on localhost/private LAN; data sent to it is governed by the local installation.

Export with `baymax data export --output export.json`. Delete rows with `baymax data delete --yes`; securely delete exports/backups separately. Filesystem users with access to the database can read it, so use OS permissions and encrypted storage. No API keys belong in source or `.env.example`.

The model dashboard is localhost-only and returns redacted capability/configuration data. Downloads
require explicit confirmation and go only to the card's reviewed source; candidate cards remain
blocked while unverified. Installation manifests contain public model metadata and artifact hashes,
never credentials, prompts, recordings, or tokens. Models are not removed automatically.
