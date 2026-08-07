# Privacy

The default mock/simulator path makes no network request. SQLite stores reminders, mood/hydration entries, and appointment notes at `DATABASE_PATH` (default `data/baymax.sqlite3`). No raw audio or transcript history is persisted. Ollama is opt-in and must remain on localhost/private LAN; data sent to it is governed by the local installation.

Export with `baymax-companion --export-data export.json`. Delete rows with `baymax-companion --delete-data`; securely delete exports/backups separately. Filesystem users with access to the database can read it, so use OS permissions and encrypted storage. No API keys belong in source or `.env.example`.
