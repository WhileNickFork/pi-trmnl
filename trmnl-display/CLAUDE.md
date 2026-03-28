# TRMNL Display - Claude Code Setup Guide

This document provides everything Claude Code needs to set up, build, test, debug, and maintain the TRMNL display project on a Raspberry Pi Zero W with a **Pimoroni Inky Impression Spectra 13.3"** e-ink display (1600x1200, 6-color Spectra 6).

## Remote Execution via SSH

All commands that need to run on the Pi (building, testing, running the application, installing packages, etc.) **must be executed via SSH**. Do not attempt to run Pi-targeted commands locally.

**SSH connection details** are stored in `ssh-instructions.txt` at the project root. Use `sshpass` to connect:
```bash
sshpass -p '<password>' ssh -o StrictHostKeyChecking=no <username>@<ip-address> '<command>'
```

**Project directory on the Pi:** `~/Documents/trmnl/pi-trmnl`

All code, build scripts, and runtime files live in this directory on the Pi.

## Keeping Code in Sync with Git

The Pi has its own clone of the repository at `~/Documents/trmnl/pi-trmnl`. After making code changes locally and committing/pushing them, **always pull the latest changes on the Pi** before building or running:
```bash
sshpass -p '<password>' ssh <username>@<ip-address> 'cd ~/Documents/trmnl/pi-trmnl && git pull'
```

Workflow:
1. Edit code locally in this repository
2. Commit and push changes to the remote
3. SSH into the Pi and `git pull` in `~/Documents/trmnl/pi-trmnl`
4. Build and/or run on the Pi via SSH

Never edit files directly on the Pi — always go through git so local and remote stay in sync.

## Commit Guidelines

When committing, describe only what changed or what the code does. Do not mention who made the changes — do not cite yourself, Anthropic, the user, or anyone else. Stick strictly to the substance of the changes.

## Project Overview

A Go application that polls the TRMNL API for images and renders them on an e-ink display. The 13.3" Spectra display is driven via a Python script (`show_image.py`) using Pimoroni's official `inky` library, because the C-based `bb_epaper` library does not support this panel.

**Data flow:**
```
Go app -> TRMNL API (GET /api/display) -> downloads image -> calls show_image.py -> Pimoroni inky library -> SPI -> display
```

## Architecture

```
trmnl-display.go          # Main Go application (polling loop, API, config)
show_image.py             # Python display driver for 13.3" Inky Impression Spectra
build.sh                  # Build script (deps, compilation, config generation)
raspberry_pi/
  trmnl.desktop           # Desktop launcher (optional)
  trmnl.svg               # App icon (optional)
```

**Config files (on Pi, created by build.sh or first run):**
```
~/.config/trmnl/config.json       # API key, device_id, base_url
~/.config/trmnl/show_img.json     # Display adapter, dimensions, panel type
```

---

## Hardware Setup

### Display: Pimoroni Inky Impression Spectra 13.3" (PIM774)
- Resolution: 1600 x 1200 pixels (4:3 aspect ratio)
- Color: 6-color Spectra 6 (black, white, red, green, blue, yellow)
- Interface: SPI + I2C (for EEPROM auto-detection)
- Refresh time: ~12-25 seconds per full update

### Host: Raspberry Pi Zero W
- 512MB RAM, single-core ARM11
- Known SPI signal quality issues with large displays
- If SPI timeouts occur, add to `/boot/firmware/config.txt`:
  ```
  dtoverlay=spi0-0cs,clockfreq=2000000
  ```

### Required interfaces (must be enabled):
```bash
sudo raspi-config nonint do_spi 0    # Enable SPI
sudo raspi-config nonint do_i2c 0    # Enable I2C
```

### Verify hardware:
```bash
ls /dev/spidev*          # Should show /dev/spidev0.0 and /dev/spidev0.1
i2cdetect -y 1           # Should detect Inky EEPROM on I2C bus
```

---

## Initial Setup (Fresh Pi)

Run these steps in order. The build.sh script handles most of this, but here's the manual breakdown if you need to debug or re-run steps individually.

### 1. System packages

```bash
sudo apt update
sudo apt install -y git gpiod libgpiod-dev golang-go python3 python3-pip python3-pil
```

Go 1.24+ is required. Check with `go version`. On Raspberry Pi OS Bookworm, the default golang-go package may be older. If so:
```bash
# Check version
go version
# If < 1.24, install from snap or download from go.dev
sudo snap install go --classic
```

### 2. Python dependencies

```bash
pip3 install inky
```

Verify:
```bash
python3 -c "from inky.auto import auto; print('inky OK')"
python3 -c "from PIL import Image; print('PIL OK')"
```

Note: On some Pi OS versions, you may need `--break-system-packages` flag or use a venv:
```bash
pip3 install --break-system-packages inky
# OR
python3 -m venv ~/.venv/trmnl
source ~/.venv/trmnl/bin/activate
pip install inky pillow
```

If using a venv, update the Go code's exec.Command to use the venv's python3 path, or activate the venv before running trmnl-display.

### 3. Clone and build C libraries (needed for options 1-3, but build.sh does this for all options)

```bash
mkdir -p ~/Projects
cd ~/Projects
git clone https://github.com/bitbank2/bb_epaper
git clone https://github.com/bitbank2/PNGdec
git clone https://github.com/bitbank2/JPEGDEC

cd PNGdec/linux && make && cd ../..
cd JPEGDEC/linux && make && cd ../..
cd bb_epaper/rpi && make && cd examples/show_img && make && cd ../../../..
```

For option 4 (13.3" Pimoroni), `show_img` is NOT used at runtime (Python driver replaces it), but build.sh still compiles it. This is fine.

### 4. Enable SPI and I2C

```bash
sudo raspi-config nonint do_spi 0
sudo raspi-config nonint do_i2c 0
```

A reboot may be required after enabling these.

### 5. Create display config

```bash
mkdir -p ~/.config/trmnl
cat > ~/.config/trmnl/show_img.json << 'EOF'
{
        "adapter": "pimoroni_py",
        "stretch": "aspectfill",
        "panel_1bit": "INKY_SPECTRA_1600x1200",
        "panel_2bit": "INKY_SPECTRA_1600x1200",
        "width": 1600,
        "height": 1200
}
EOF
```

### 6. Build the Go binary

```bash
cd /path/to/trmnl-display
go build -o trmnl-display ./trmnl-display.go
```

### 7. Create API config

```bash
cat > ~/.config/trmnl/config.json << EOF
{
  "api_key": "YOUR_TRMNL_API_KEY_HERE",
  "base_url": "https://trmnl.app"
}
EOF
chmod 600 ~/.config/trmnl/config.json
```

For BYOS servers, use `device_id` (MAC address) instead of `api_key` and set `base_url` to your server.

### 8. Run

```bash
./trmnl-display
```

Or use the build script (does steps 1-6 automatically, prompts for display type):
```bash
./build.sh    # Select option 4 for 13.3" Pimoroni
```

---

## Automated Setup (build.sh)

The simplest path: run `./build.sh` and select option **4** when prompted. It handles everything except the API key (prompted on first run of `./trmnl-display`).

---

## Running and Testing

### Run in foreground (verbose):
```bash
./trmnl-display -verbose
```

Expected output:
```
Checking system environment...
Using base URL: https://trmnl.app
Display: 1600x1200, adapter: pimoroni_py
Displayed: /tmp/trmnl-display.../plugin-...
EPD update completed
```

### Run in background:
```bash
nohup ./trmnl-display > ~/.config/trmnl/logfile.log 2>&1 &
```

### Auto-start on boot:
```bash
crontab -e
# Add:
@reboot sleep 15 && nohup /path/to/trmnl-display > ~/.config/trmnl/logfile.log 2>&1 &
```

### Command-line flags:
| Flag | Description |
|------|-------------|
| `-d` | Dark mode (invert pixels) |
| `-v` | Show version and exit |
| `-verbose` | Enable verbose output (default: true) |
| `-q` | Quiet mode |
| `-base-url URL` | Override API base URL |

### Environment variable overrides:
```bash
TRMNL_API_KEY="..."          # Overrides config.json api_key
TRMNL_DEVICE_ID="AA:BB:..."  # Overrides config.json device_id
TRMNL_BASE_URL="https://..." # Overrides config.json base_url
XDG_CONFIG_HOME="/custom"    # Changes config dir from ~/.config
```

---

## Testing Individual Components

### Test API connectivity:
```bash
curl -s -H "access-token: YOUR_API_KEY" \
     -H "WIDTH: 1600" \
     -H "HEIGHT: 1200" \
     https://trmnl.app/api/display | python3 -m json.tool
```

Expected: JSON with `image_url`, `filename`, `refresh_rate`.

### Test image download:
```bash
# Use the image_url from the API response
curl -o /tmp/test_image.jpg "IMAGE_URL_FROM_API"
file /tmp/test_image.jpg
```

### Test Python display driver directly:
```bash
# With a real image:
python3 show_image.py --file /tmp/test_image.jpg --saturation 0.5

# Test dark mode:
python3 show_image.py --file /tmp/test_image.jpg --invert true

# Test with different saturation (higher = more vivid colors):
python3 show_image.py --file /tmp/test_image.jpg --saturation 0.8
```

### Test Inky library detection:
```bash
python3 -c "
from inky.auto import auto
inky = auto(ask_user=False, verbose=True)
print(f'Resolution: {inky.resolution}')
print(f'Color: {inky.colour}')
"
```

Expected: `Resolution: (1600, 1200)`

### Test with a generated solid color image:
```bash
python3 -c "
from PIL import Image
img = Image.new('RGB', (1600, 1200), (255, 0, 0))  # solid red
img.save('/tmp/red_test.png')
"
python3 show_image.py --file /tmp/red_test.png --saturation 0.5
```

---

## Key Code Paths

### API Request (trmnl-display.go)

The `processNextImage()` function (line ~204):
1. Builds GET request to `{base_url}/api/display`
2. Sends headers: `access-token`, `WIDTH`, `HEIGHT`, `FW_VERSION`, `battery-voltage`, `rssi`
3. Parses JSON response: `image_url`, `filename`, `refresh_rate`
4. Downloads image to `/tmp/trmnl-display*/`
5. Calls `displayImage()`

### Display Routing (trmnl-display.go)

The `displayImage()` function (line ~342):
- If `adapter == "pimoroni_py"`: calls `python3 show_image.py --file ... --invert ... --mode ... --saturation 0.5`
- Otherwise: calls `show_img file=... invert=... mode=...` (C binary from bb_epaper)

### Python Driver (show_image.py)

1. Initializes display via `inky.auto.auto()` (EEPROM detection)
2. Opens image with PIL
3. Converts to RGB if needed (handles palette, grayscale, RGBA)
4. Aspect-fill resizes to display resolution (1600x1200)
5. Optionally inverts for dark mode
6. Calls `inky.set_image(image, saturation=...)` then `inky.show()`

### Config Loading (trmnl-display.go)

- `loadConfig()`: reads `~/.config/trmnl/config.json` -> API key, device ID, base URL
- `loadDisplayConfig()`: reads `~/.config/trmnl/show_img.json` -> adapter type, dimensions
- Defaults: width=800, height=480 if not specified (backward compatibility)

---

## Troubleshooting

### "show_image.py failed; ensure inky library is installed"
- Check: `pip3 list | grep inky`
- Fix: `pip3 install inky` (or `pip3 install --break-system-packages inky`)

### "Error initializing display" / "No EEPROM detected"
- Check physical connection of display to GPIO header
- Verify I2C: `i2cdetect -y 1` should show a device
- Verify SPI: `ls /dev/spidev*` should show devices
- Enable interfaces: `sudo raspi-config nonint do_spi 0 && sudo raspi-config nonint do_i2c 0`
- Reboot after enabling

### "Timeout waiting for busy signal"
- Common on Pi Zero W due to SPI signal degradation
- Add to `/boot/firmware/config.txt`: `dtoverlay=spi0-0cs,clockfreq=2000000`
- Reboot

### API returns 404
- Verify base URL: `cat ~/.config/trmnl/config.json`
- Test: `curl -H "access-token: KEY" https://trmnl.app/api/display`

### "go: command not found" or Go version too old
- `go version` to check (need 1.24+)
- On Pi OS Bookworm: `sudo apt install golang-go` or `sudo snap install go --classic`

### Images look wrong / low quality
- The TRMNL API needs to know your display size. Check that `WIDTH` and `HEIGHT` headers are being sent (run with `-verbose`).
- In the TRMNL web portal, set the device's color palette to `color-spectra6` for full 6-color output.
- Adjust saturation: edit the `"0.5"` value in `displayImage()` in trmnl-display.go (range 0.0-1.0, higher = more vivid).

### Display shows nothing / no update
- Check verbose output: `./trmnl-display -verbose`
- Check that `/tmp/trmnl-display*/` contains downloaded images
- Try running show_image.py manually with a test image
- Check dmesg for SPI errors: `dmesg | tail -30`

### Python venv issues
- If `pip3 install inky` fails with "externally-managed-environment", use:
  ```bash
  pip3 install --break-system-packages inky
  ```
  Or create a venv and modify the exec.Command in Go to use it.

---

## TRMNL Color Palette Setup

For full 6-color Spectra output, configure the palette in the TRMNL web portal:
1. Go to your device settings at https://usetrmnl.com
2. Set the color palette to **`color-spectra6`**
3. This tells the server to render content using the 6 Spectra colors
4. The `saturation` parameter in show_image.py controls dithering aggressiveness

Available palettes: `bw`, `gray-4`, `gray-16`, `gray-256`, `color-3bwr`, `color-3bwy`, `color-4bwry`, `color-spectra6`, `color-6a`, `color-7a`, `color-12bit`, `color-24bit`

---

## File Permissions

```bash
chmod +x build.sh
chmod +x show_image.py
chmod 600 ~/.config/trmnl/config.json    # Contains API key
chmod 644 ~/.config/trmnl/show_img.json
```

---

## Quick Validation Checklist

Run these checks to confirm the environment is properly set up:

```bash
# 1. Go compiler
go version                        # Should be 1.24+

# 2. Python + dependencies
python3 --version                 # Should be 3.7+
python3 -c "import inky; print('inky', inky.__version__)"
python3 -c "from PIL import Image; print('PIL OK')"

# 3. Hardware interfaces
ls /dev/spidev*                   # Should list SPI devices
i2cdetect -y 1                    # Should detect EEPROM

# 4. Config files
cat ~/.config/trmnl/show_img.json # adapter should be "pimoroni_py", width 1600, height 1200
cat ~/.config/trmnl/config.json   # Should have api_key or device_id

# 5. Display detection
python3 -c "from inky.auto import auto; d = auto(ask_user=False); print(d.resolution)"
# Should print: (1600, 1200)

# 6. Binary exists
ls -la trmnl-display              # Should be executable
file trmnl-display                # Should show ARM executable

# 7. API connectivity
curl -s -o /dev/null -w "%{http_code}" -H "access-token: $(python3 -c 'import json; print(json.load(open("'$HOME'/.config/trmnl/config.json"))["api_key"])')" https://trmnl.app/api/display
# Should print: 200
```
