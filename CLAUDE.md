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

This project has two entry points that share a common `aura/` library:

- **`download-aura-photos.py`** — CLI entry point. Reads credentials from `~/etc/aura/credentials.ini` (INI format with `[login]` and per-frame sections).
- **`aura_gui.py`** — PyQt6 GUI entry point. Persists settings via `QSettings` (no config file needed).

### `aura/` package

- **`core.py`** — All Aura API logic. `create_session()` authenticates against `api.pushd.com` and returns a `requests.Session` with auth headers. `download_photos_from_aura()` is the main download function, shared by both the CLI and GUI; it accepts optional `progress_callback` and `cancel_check` callables so the GUI can hook in without coupling.
- **`config.py`** — INI config parsing used only by the CLI.
- **`exceptions.py`** — Exception hierarchy rooted at `AuraError`.

### `aura/gui/`

- **`main_window.py`** — `MainWindow` (QMainWindow) + `FrameDialog` (QDialog). Frame list and credentials are saved/restored with `QSettings("AuraDownloader", "AuraFrameDownloader")`.
- **`download_worker.py`** — `DownloadWorker(QThread)` runs `download_photos_from_aura()` on a background thread and emits Qt signals (`progress_updated`, `status_changed`, `download_complete`, `error_occurred`) back to the main window.

### PyInstaller

`aura_gui.spec` controls the macOS `.app` and Windows `.exe` builds. Icons live in `aura/gui/resources/` (`.svg`, `.icns`, `.ico`).

## API Notes

The Aura API is at `api.pushd.com/v5`. Authentication requires posting to `/login.json` with a payload that includes `app_identifier: "com.pushd.Framelord"`. The response provides `X-User-Id` and `X-Token-Auth` headers used for all subsequent requests. Photo files are fetched from `imgproxy.pushd.com/{user_id}/{file_name}`. The API throttles downloads; `core.py` sleeps 2s between photos and 10s on error.
