# Aura Frame Downloader

Bulk download photos from your Aura digital picture frame (auraframes.com). Aura provides no easy way to bulk download photos, so this tool lets you download all your photos at once. Since Aura stores photos on their servers, no physical access to the frame is needed.

---

## Download & Install (Easiest)

### macOS (Apple Silicon)

1. **Download** the latest release: [Aura-Downloader-macOS-arm64.zip](https://github.com/meub/aura-frame-downloader/releases/latest)

2. **Unzip** and drag `Aura Downloader.app` to your Applications folder

3. **First launch** - Right-click the app and select "Open" (required once since the app isn't signed by Apple)
   - If you see "app is damaged", run this in Terminal:
     ```bash
     xattr -cr "/Applications/Aura Downloader.app"
     ```

4. **Use the app:**
   - Enter your Aura email and password
   - Click "Add Frame" and enter your frame details (see [Getting your Frame ID](#getting-your-frame-id) below)
   - Select a download folder
   - Click "Start Download"

Your credentials and frame settings are saved automatically for next time.

### Windows

1. **Download** the latest release: [Aura-Downloader-Windows.zip](https://github.com/meub/aura-frame-downloader/releases/latest)

2. **Unzip** and run `Aura Downloader.exe`
   - Windows may show a SmartScreen warning since the app isn't signed
   - Click "More info" then "Run anyway"

3. **Use the app:**
   - Enter your Aura email and password
   - Click "Add Frame" and enter your frame details (see [Getting your Frame ID](#getting-your-frame-id) below)
   - Select a download folder
   - Click "Start Download"

Your credentials and frame settings are saved automatically for next time.

---

## Getting your Frame ID

1. Go to https://app.auraframes.com and log in
2. Click on the Frame name
3. Click on "View Photos" underneath the frame
4. Grab the ID from the URL: `https://app.auraframes.com/frame/<FRAME ID HERE>`

---

## Command Line Usage

If you prefer the command line or are on Windows/Linux:

### Setup

1. Install Python 3 and the requests module:
   ```bash
   pip install requests
   ```

2. Create a configuration file at:
   - **Windows:** `%USERPROFILE%/etc/aura/credentials.ini`
   - **Mac/Linux:** `$HOME/etc/aura/credentials.ini`

   Example config:
   ```ini
   [login]
   email = myemail@gmail.com
   password = mypassword

   [myframe]
   file_path = ./images
   frame_id = abf53be3-b73d-4de3-98cd-cfd289bd82df

   [anotherframe]
   file_path = ./images-another-frame
   frame_id = b69ddd8d-bcad-483f-adf4-e15ff9a48c47
   ```

### Commands

```bash
# Download photos from a frame
python download-aura-photos.py myframe

# Show photo count only
python download-aura-photos.py --count myframe

# Organize by year folders
python download-aura-photos.py --years myframe

# Use alternate config file
python download-aura-photos.py --config /path/to/config.ini myframe
```

### Options

| Option | Description |
|--------|-------------|
| `--config PATH` | Use alternate configuration file |
| `--count` | Show photo count and exit |
| `--years` | Organize photos into year subfolders |
| `--debug` | Enable debug logging |

---

## Notes

- **Throttling:** The Aura API may throttle downloads. The script automatically waits between downloads, but you may need to restart it for large collections.

- **Resume support:** Already-downloaded photos are skipped, so you can safely restart the script.

- **Filename format:** `2012-04-15-03-15-04.000_B9A0E367-FA8D-4157-A090-7EE33F603312.jpeg`
  - Based on `taken_at` timestamp + unique `id` + original extension

- **Duplicates:** The same photo uploaded by different people will be downloaded separately. Consider running a duplicate finder afterward.

---

## Scheduled Runs (Ubuntu/Linux)

### Setup

1. Set up the venv on your machine (see [Development](#development) below)

2. Edit `scripts/run_download.sh` and set:
   - `FRAME` — your frame name from `credentials.ini`
   - `LOG_FILE` — where to write the log (default: `~/aura-downloads.log`)

3. Make the script executable:
   ```bash
   chmod +x scripts/run_download.sh
   ```

4. Add a cron entry to run it nightly (`crontab -e`):
   ```cron
   0 2 * * * /absolute/path/to/aura-frame-downloader/scripts/run_download.sh
   ```

### Log format

Each run appends a block to the log file:

```
=== 2025-10-15T02:00:01+00:00  frame=myframe ===
02:00:01 [INFO]: Using credentials file '/home/user/etc/aura/credentials.ini'
02:00:03 [INFO]: Login successful
02:00:04 [INFO]: Found 247 photos
02:00:04 [INFO]: Starting download process
02:00:08 [INFO]: 245: Downloading 2025-10-14-18-22-01.000_F9C3...jpeg
02:01:09 [INFO]: Downloaded 3 photos (244 skipped)
=== done (exit 0) ===
```

### Log rotation (optional)

To prevent the log from growing unboundedly, create `/etc/logrotate.d/aura-downloads`:

```
/home/youruser/aura-frame-downloader/logs/aura-downloads.log {
    weekly
    rotate 8
    compress
    missingok
    notifempty
}
```

---

## Image Server

`image_server.py` serves rotating images and videos from a local directory over HTTP. Each item is held for a configurable number of seconds before rotating to the next.

### Usage

```bash
# Serve media from the ./images directory on the default port (8124)
./venv/bin/python image_server.py images

# Use a custom port
./venv/bin/python image_server.py images --port 9000
```

### Endpoints

| Endpoint | Description |
|----------|-------------|
| `/rotate?n=<seconds>` | Returns a single rotating image (no videos). Suitable for HA's [Generic Camera](https://www.home-assistant.io/integrations/generic/) integration. |
| `/page?n=<seconds>[&audio=1]` | Returns a self-contained HTML page that rotates through both images and videos client-side. Use with [Wallpanel](https://j-a-n.github.io/lovelace-wallpanel/)'s `iframe+` prefix. |

The `n` parameter controls how long each item is shown. All requests within the same `n`-second window get the same item. Defaults to 15 seconds.

**Audio** (`/page` only): Videos are muted by default. Pass `audio=1` to enable sound. Note that browsers may block autoplay-with-sound until you interact with the page.

**Wallpanel example:**

```yaml
image_url: iframe+http://192.168.5.50:8124/page?n=30
```

### Run automatically on Ubuntu (systemd)

Create `/etc/systemd/system/aura-image-server.service`:

```ini
[Unit]
Description=Aura Image Server
After=network.target

[Service]
User=<your-username>
WorkingDirectory=/home/<your-username>/aura-frame-downloader
ExecStart=/home/<your-username>/aura-frame-downloader/venv/bin/python image_server.py images
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Then enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable aura-image-server
sudo systemctl start aura-image-server
```

The server will start automatically on reboot. Check its status with:

```bash
sudo systemctl status aura-image-server
```

---

## Development

### macOS/Linux

```bash
# Install virtual environment with dependencies
make install

# Run the GUI
make run-gui

# Build macOS app
make build-mac

# Run linter
make lint
```

See `make help` for all available commands.

### Windows (PowerShell)

```powershell
# Full build (install + build)
.\build_windows.ps1 -All

# Or step by step:
.\build_windows.ps1 -Install    # Create venv and install dependencies
.\build_windows.ps1 -Build      # Build the executable
.\build_windows.ps1 -Run        # Run GUI from source
.\build_windows.ps1 -Clean      # Remove build artifacts
```

The built executable will be at `dist\Aura Downloader.exe`.
