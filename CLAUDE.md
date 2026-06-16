# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Set up virtual environment and install all dependencies
make install

# Install GUI-specific dependencies after base install (if needed separately)
make install-gui

# Run the GUI application
make run-gui

# Run the CLI
./venv/bin/python download-aura-photos.py <frame-name>

# Serve rotating images/videos over HTTP (default port 8124)
./venv/bin/python image_server.py images [--port 9000]

# Run the linter (prospector)
make lint

# Build macOS .app bundle
make build-mac

# Clean build artifacts
make clean-build
```

The Makefile uses pyenv: `PYTHON_VERSION=${default_python_version}`. Ensure pyenv is configured with a default Python version.

**Windows** uses `build_windows.ps1` — see README for PowerShell commands.

## Architecture

This project has three entry points. Two share the `aura/` library; the third is independent:

- **`download-aura-photos.py`** — CLI entry point. Reads credentials from `~/etc/aura/credentials.ini` (INI format with `[login]` and per-frame sections).
- **`aura_gui.py`** — PyQt6 GUI entry point. Persists settings via `QSettings` (no config file needed).
- **`image_server.py`** — standalone stdlib HTTP server (no `aura/` dependency) that serves the *already-downloaded* media directory. It does not touch the Aura API. See "Image Server" below.

### `aura/` package

- **`core.py`** — All Aura API logic. `create_session()` authenticates against `api.pushd.com` and returns a `requests.Session` with auth headers. `download_photos_from_aura()` is the main download function, shared by both the CLI and GUI; it accepts optional `progress_callback` and `cancel_check` callables so the GUI can hook in without coupling.
- **`config.py`** — INI config parsing used only by the CLI.
- **`exceptions.py`** — Exception hierarchy rooted at `AuraError`.

### `aura/gui/`

- **`main_window.py`** — `MainWindow` (QMainWindow) + `FrameDialog` (QDialog). Frame list and credentials are saved/restored with `QSettings("AuraDownloader", "AuraFrameDownloader")`.
- **`download_worker.py`** — `DownloadWorker(QThread)` runs `download_photos_from_aura()` on a background thread and emits Qt signals (`progress_updated`, `status_changed`, `download_complete`, `error_occurred`) back to the main window.

### Image Server (`image_server.py`)

Stdlib-only HTTP server that rotates through media in a local directory. Rotation is deterministic, not stateful: `pick_for_bucket()` seeds `random` with `floor(now / interval)`, so every client requesting within the same `n`-second window sees the same item without any server-side scheduling. Endpoints:

- `/rotate?n=<sec>` — serves a single rotating **image** (no video); for HA's Generic Camera integration.
- `/page?n=<sec>[&audio=1]` — self-contained HTML page that rotates **images and videos** client-side, polling `/current`; for Wallpanel's `iframe+`.
- `/current?n=<sec>` — JSON `{type, url}` for the current bucket's item.
- `/file/<name>` — serves a single file; rejects path traversal (no `/`, `\`, or leading `.`).

### Scheduled downloads

`scripts/run_download.sh` wraps the CLI for cron: edit `FRAME`/`CONFIG`/`LOG_FILE` at the top, then schedule it. It appends a dated block to `logs/aura-downloads.log` and filters out `already downloaded` lines to keep the log signal-heavy.

### PyInstaller

`aura_gui.spec` controls the macOS `.app` and Windows `.exe` builds. Icons live in `aura/gui/resources/` (`.svg`, `.icns`, `.ico`).

## API Notes

The Aura API is at `api.pushd.com/v5`. Authentication requires posting to `/login.json` with a payload that includes `app_identifier: "com.pushd.Framelord"`. The response provides `X-User-Id` and `X-Token-Auth` headers used for all subsequent requests.

Per-asset download URL depends on media type (see `download_photos_from_aura` in `core.py`): **videos** carry a signed `video_url` pointing at the real MP4 and are saved with a `.mp4` extension; **photos** are built from `imgproxy.pushd.com/{user_id}/{file_name}`. Filenames are `{taken_at, ':'→'-'}_{id}{ext}`, and existing files are skipped so runs are resumable. The API throttles downloads; `core.py` sleeps 2s between items and 10s on error.
