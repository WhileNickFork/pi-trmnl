# TRMNL Display

A lightweight Linux application that fetches images from the [TRMNL](https://usetrmnl.com) API and renders them on e-paper and framebuffer displays. Built in Go with a Python display driver for Pimoroni Inky Impression panels.

Forked from [usetrmnl/trmnl-display](https://github.com/usetrmnl/trmnl-display) with added support for the **Pimoroni Inky Impression Spectra 13.3"** (1600x1200, 6-color Spectra 6) on a Raspberry Pi Zero W.

## Supported Displays

| # | Display | Resolution | Adapter |
|---|---------|-----------|---------|
| 1 | Framebuffer (HDMI/LCD) | 800x480 | `framebuffer` |
| 2 | Waveshare e-paper HAT | 800x480 | `waveshare_2` |
| 3 | Pimoroni Inky Impression Spectra 7.3" | 800x480 | `pimoroni` |
| 4 | Pimoroni Inky Impression Spectra 13.3" | 1600x1200 | `pimoroni_py` |

Options 1-3 use the [bb_epaper](https://github.com/bitbank2/bb_epaper) C library. Option 4 uses a Python driver (`show_image.py`) with Pimoroni's [inky](https://github.com/pimoroni/inky) library, since bb_epaper does not support this panel.

## Architecture

```
trmnl-display.go          # Main Go application (polling loop, API client, config)
show_image.py             # Python display driver for 13.3" Inky Impression Spectra
build.sh                  # Build script (installs deps, compiles, generates config)
raspberry_pi/
  trmnl.desktop           # Desktop launcher (optional)
  trmnl.svg               # App icon (optional)
```

**Data flow:**
```
Go binary -> TRMNL API (GET /api/display) -> downloads image
  -> show_image.py (Python/inky) or show_img (C/bb_epaper) -> SPI -> e-ink display
```

## Requirements

- Linux SBC (Raspberry Pi Zero W, Pi 3/4, Orange Pi, etc.)
- Go 1.24+
- Python 3.7+ (for 13.3" Pimoroni display)
- E-paper display with SPI connection, or framebuffer display
- Internet connection
- TRMNL account with a registered BYOD device

## Installation

### Quick Install (build.sh)

```bash
git clone https://github.com/WhileNickFork/pi-trmnl.git
cd pi-trmnl/trmnl-display
./build.sh
```

Select your display type when prompted (option **4** for the 13.3" Pimoroni). The script handles package installation, library compilation, and config generation.

### Manual Install (13.3" Pimoroni Inky Impression)

If you prefer to set things up step by step, or need to debug the build process:

#### 1. System packages

```bash
sudo apt update
sudo apt install -y git gpiod libgpiod-dev golang-go python3 python3-pip python3-pil i2c-tools
```

Verify Go version (need 1.24+):
```bash
go version
```

#### 2. Enable SPI and I2C

```bash
sudo raspi-config nonint do_spi 0
sudo raspi-config nonint do_i2c 0
```

Verify after enabling (reboot if needed):
```bash
ls /dev/spidev*          # Should show /dev/spidev0.0 and /dev/spidev0.1
i2cdetect -y 1           # Should show a device at address 0x50 (Inky EEPROM)
```

#### 3. Python dependencies

```bash
pip3 install --break-system-packages inky
```

Verify:
```bash
python3 -c "from inky.auto import auto; d = auto(ask_user=False); print(d.resolution)"
# Should print: (1600, 1200)
```

#### 4. Clone and build C libraries

Even though the 13.3" display uses the Python driver at runtime, the build script compiles these and they are needed for display options 1-3:

```bash
mkdir -p ~/Projects && cd ~/Projects
git clone https://github.com/bitbank2/bb_epaper
git clone https://github.com/bitbank2/PNGdec
git clone https://github.com/bitbank2/JPEGDEC

cd PNGdec/linux && make && cd ../..
cd JPEGDEC/linux && make && cd ../..
cd bb_epaper/rpi && make && cd examples/show_img && make && cd ../../../..
```

#### 5. Create display config

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

#### 6. Build the Go binary

```bash
cd /path/to/pi-trmnl/trmnl-display
go build -o trmnl-display ./trmnl-display.go
```

## TRMNL BYOD Device Registration

Before the application can fetch images, your device must be registered with TRMNL.

### 1. Get your MAC address

```bash
cat /sys/class/net/wlan0/address
```

**Important:** The MAC address must be **UPPERCASE** when registering with TRMNL. For example, if your MAC is `b8:27:eb:a0:12:24`, register it as `B8:27:EB:A0:12:24`. The API is case-sensitive and will return "Device not found" with a lowercase MAC.

### 2. Register the device

1. Go to [trmnl.com/claim-a-device](https://trmnl.com/claim-a-device)
2. Enter your uppercase MAC address
3. Select **Inky Impression 13.3 - 1600x1200** as the device hardware model

### 3. Call the setup endpoint

The device must check in via `api/setup` to receive its API key:

```bash
curl -s \
  -H "ID: YOUR_UPPERCASE_MAC" \
  -H "Content-Type: application/json" \
  https://trmnl.app/api/setup
```

A successful response looks like:
```json
{
  "status": 200,
  "api_key": "your-api-key-here",
  "friendly_id": "XXXXXX",
  "image_url": "https://trmnl.com/images/system_screens/setup_logo/inky_impression_13_3.png"
}
```

### 4. Create the API config

Use the `api_key` from the setup response:

```bash
cat > ~/.config/trmnl/config.json << EOF
{
  "api_key": "YOUR_API_KEY_FROM_SETUP",
  "base_url": "https://trmnl.app",
  "device_id": "YOUR_UPPERCASE_MAC"
}
EOF
chmod 600 ~/.config/trmnl/config.json
```

### 5. Configure the color palette

For full 6-color Spectra output on the 13.3" display:
1. Go to your device settings at [usetrmnl.com](https://usetrmnl.com)
2. Set the color palette to **`color-spectra6`**

## Usage

Run the application:

```bash
./trmnl-display
```

Verbose output (default):
```
Checking system environment...
Using base URL: https://trmnl.app
Display: 1600x1200, adapter: pimoroni_py
Displayed: /tmp/trmnl-display.../plugin-...
EPD update completed
```

To skip to the next playlist item, press `Enter`.

### Command-line flags

| Flag | Description |
|------|-------------|
| `-d` | Dark mode (invert image pixels) |
| `-v` | Show version and exit |
| `-verbose` | Enable verbose output (default: true) |
| `-q` | Quiet mode |
| `-base-url URL` | Override API base URL |

### Environment variable overrides

```bash
TRMNL_API_KEY="..."          # Overrides config.json api_key
TRMNL_DEVICE_ID="AA:BB:..."  # Overrides config.json device_id
TRMNL_BASE_URL="https://..." # Overrides config.json base_url
XDG_CONFIG_HOME="/custom"    # Changes config dir from ~/.config
```

## Running in the Background

```bash
nohup ./trmnl-display > ~/.config/trmnl/logfile.log 2>&1 &
```

### Auto-start on Boot

Add a crontab entry so the display starts automatically after a reboot:

```bash
crontab -e
```

Add this line (adjust the path to your installation):

```bash
@reboot sleep 15 && nohup /home/$(whoami)/Documents/trmnl/pi-trmnl/trmnl-display/trmnl-display > /home/$(whoami)/.config/trmnl/logfile.log 2>&1 &
```

The `sleep 15` ensures the network is ready before the application makes its first API request.

Verify it works:

```bash
sudo reboot
```

After reboot, check the log:

```bash
cat ~/.config/trmnl/logfile.log
```

## Configuration

Configuration files are stored in `~/.config/trmnl/`:

| File | Purpose | Permissions |
|------|---------|-------------|
| `config.json` | API key, device ID, base URL | `600` (contains API key) |
| `show_img.json` | Display adapter, dimensions, panel type | `644` |

## Testing Individual Components

### Test the Python display driver

```bash
# Generate a test image
python3 -c "
from PIL import Image
img = Image.new('RGB', (1600, 1200), (255, 0, 0))
img.save('/tmp/red_test.png')
"

# Display it
python3 show_image.py --file /tmp/red_test.png --saturation 0.5
```

### Test API connectivity

```bash
curl -s \
  -H "access-token: YOUR_API_KEY" \
  -H "WIDTH: 1600" \
  -H "HEIGHT: 1200" \
  https://trmnl.app/api/display | python3 -m json.tool
```

### Test display auto-detection

```bash
python3 -c "
from inky.auto import auto
inky = auto(ask_user=False, verbose=True)
print(f'Resolution: {inky.resolution}')
print(f'Color: {inky.colour}')
"
```

## Troubleshooting

### "Device not found" from API
- Verify your MAC address is **UPPERCASE** in both `config.json` and on the TRMNL portal
- Call `api/setup` with your MAC to check registration status
- Contact support@trmnl.com if `api/setup` says "MAC not registered"

### "unsupported protocol scheme" error
- This means the API returned an empty `image_url` — usually caused by the "Device not found" issue above

### "show_image.py failed; ensure inky library is installed"
- Run: `pip3 install --break-system-packages inky`

### "Error initializing display" / "No EEPROM detected"
- Check physical display connection to GPIO header
- Verify I2C: `i2cdetect -y 1` should show device at `0x50`
- Verify SPI: `ls /dev/spidev*` should show devices
- Enable interfaces: `sudo raspi-config nonint do_spi 0 && sudo raspi-config nonint do_i2c 0`
- Reboot after enabling

### "Timeout waiting for busy signal"
- Common on Pi Zero W due to SPI signal quality
- Add to `/boot/firmware/config.txt`: `dtoverlay=spi0-0cs,clockfreq=2000000`
- Reboot

### Go version too old
- Need 1.24+. Check with `go version`
- On Pi OS Bookworm: `sudo apt install golang-go` gets 1.24.x

## Hardware Details

### Pimoroni Inky Impression Spectra 13.3" (PIM774)
- Resolution: 1600 x 1200 pixels (4:3 aspect ratio)
- Color: 6-color Spectra 6 (black, white, red, green, blue, yellow)
- Interface: SPI + I2C (EEPROM auto-detection)
- Refresh time: ~12-25 seconds per full update

### Raspberry Pi Zero W
- 512MB RAM, single-core ARM11
- Go build times are slow (~2-3 minutes) due to limited CPU
- If SPI issues occur, reduce clock frequency (see Troubleshooting)

## License

TRMNL Display is licensed under the MIT License. See [LICENSE](./LICENSE) for details.
