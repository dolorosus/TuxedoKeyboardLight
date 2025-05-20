# Keyboard lighting control for Tuxedo Stellaris Gen. 6 (and maybe others) 

## Switches the keyboard lighting on with a certain brightness and switches it off again after an adjustable period of inactivity.

## Why this little script?
Because by default the keyboard lighting is only switched off when the screen saver appears. This time span was too long for me personally.
The minimum brightness was also too bright for me personally.
This script also accepts brightness values less than 10 (20%)


## Other Hardware
Adaptation to other hardware that also follows the sysfs standard for keyboard illumination should be feasible without any problems.

## Features

- Turns on backlight when mouse/keyboard activity is detected
- Automatic shutoff after configurable inactivity period
- Customizable RGB colors and brightness levels
- Persistent system service with automatic restart
- Logging to `/var/log/keyboardlight-idle.log`
- If the backlight brightness is set to 0 (keyboard illumination is turned off),
  the default settings are used

## Requirements

- Linux with sysfs LED support
- Python 3.7+
- systemd init system
- Root privileges for installation

## Installation

1. **Clone the repository**
```
git clone https://github.com/yourusername/keyboardlight-idle.git
cd keyboardlight-idle
```

2. **Build and install executable**
```
bash ./install.sh
```

3. **Verify service status**
```
systemctl status keyboardlight-idle
```

## Configuration

Edit the service file to modify startup parameters:
```
sudo nano /etc/systemd/system/keyboardlight-idle.service
```

**Recommended parameters:**
```
ExecStart=/usr/local/bin/keyboardlight-idle \
  --brightness 4 \      # 0-50 intensity
  --timeout 20 \        # Seconds until keybaordlight is turned off
  --colour "#0000ff"    # Default blue
```

## Service Management

| Command | Description |
|---------|-------------|
| `sudo systemctl start keyboardlight-idle` | Start service |
| `sudo systemctl stop keyboardlight-idle` | Stop service |
| `sudo systemctl enable keyboardlight-idle` | Enable autostart |
| `sudo journalctl -u keyboardlight-idle` | View logs |

## Build Details

The installation script:
- Creates isolated Python virtual environment
- Installs PyInstaller and dependencies
- Builds single-file executable
- Deploys to `/usr/local/bin`
- Configures logging rotation

## Notes

- To set the default colour, just turn the keyboardlight off. After reaching the timeout, the keyboard will be initialized with the setting from --brightness and --colour 
- Requires compatible RGB keyboard with sysfs interface
- Debug using `journalctl -u keyboardlight-idle -f`
- Uninstall by removing:
  - `/usr/local/bin/keyboardlight-idle`
  - `/etc/systemd/system/keyboardlight-idle.service`

If you're using Plasma, you can define keyboard shortcuts for controlling the keyboard illumination brightness e.g. meta+F1 and meta+F2.

## License

CC BY-NC/CC BY-NC-SA

