#!/usr/bin/env python3

# Switches on the keyboard illumination with a customisable brightness (--brightness).
# Switches the keyboard backlighting off if no mouse or keyboard inputs have been made
# after a configurable period of time (--timeout).

import asyncio
import time
import logging
import signal
from evdev import InputDevice, ecodes, list_devices
import argparse
import os
import sys

# Logging-configuration
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


class KeyboardLighting:

    def __init__(self):
        self.classpath = "/sys/class/leds"
        self.keys = self._init_key_paths()
        self.brightness_path = {
            i: os.path.join(p, "brightness") for i, p in self.keys.items()
        }
        self.max_brightness_cache = self._cache_max_brightness()
        self.multi_intensity_path = {
            i: os.path.join(p, "multi_intensity") for i, p in self.keys.items()
        }

    def _init_key_paths(self):

        # There is no such thing as 'rgb:kbd_backlight_0'
        # Use keyindex 126 to access the lightbar
        
        keys = {
            0: os.path.join(self.classpath, "rgb:kbd_backlight"),
            126: os.path.join(self.classpath, "rgb:lightbar"),
        }
        keys.update(
            {
                i: os.path.join(self.classpath, f"rgb:kbd_backlight_{i}")
                for i in range(1, 126)
            }
        )
        return keys

    def _cache_max_brightness(self):
        cache = {}
        for key in self.keys:
            try:
                with open(os.path.join(self.keys[key], "max_brightness"), "r") as f:
                    cache[key] = int(f.read().strip())
            except Exception as e:
                logger.error(f"Error caching max brightness for key {key}: {str(e)}")
                cache[key] = 0
        return cache

    def get_brightness(self, key_index):
        try:
            with open(self.brightness_path[key_index], "r") as f:
                return int(f.read().strip())
        except Exception as e:
            logger.error(f"Error reading brightness: {str(e)}")
            return 0

    def set_brightness(self, key_index, brightness):
        try:
            safe_brightness = min(brightness, self.max_brightness_cache[key_index])
            with open(self.brightness_path[key_index], "w") as f:
                f.write(str(safe_brightness))
        except Exception as e:
            logger.error(f"Error setting brightness: {str(e)}")

    def set_color(self, key_idx, rgb):
        try:
            pfad = os.path.join(self.keys[key_idx], "multi_intensity")
            with open(pfad, "w") as f:
                f.write(f"{rgb[0]} {rgb[1]} {rgb[2]}")
        except Exception as e:
            logger.error(f"Error setting color: {str(e)}")
    
    def config_key(self, key_idx, brightness, rgb):
        self.set_brightness(key_idx, brightness)
        self.set_color(key_idx, rgb)

    @staticmethod
    def _hex_to_rgb(hex_color):
        s = str(hex_color).lstrip("#").upper()
        if len(s) != 6:
            raise ValueError(
                f"Hex colour code must have the format '#rrggbb' or 'rrggbb': '{hex_color}'"
            )
        if not set(s) <= set("0123456789ABCDEF"):
            raise ValueError(f"Invalid characters in hex colour code:'{hex_color}'")

        return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


class DeviceMonitor:
    def __init__(self, keyboard, timeout, brightness):
        self.keyboard = keyboard
        self.timeout = timeout
        self.brightness = brightness
        self.last_event_time = time.time()
        self.led_is_off = False
        self.last_brightness = brightness
        self.active_tasks = []

    async def _handle_device(self, device):
        try:
            async for event in device.async_read_loop():
                self.last_event_time = time.time()
                if self.led_is_off:
                    self._activate_leds()
        except OSError as e:
            logger.error(f"Device error {device.path}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")

    def _activate_leds(self):
        if self.last_brightness <= 1:
            self.last_brightness = self.brightness
        self.keyboard.set_brightness(0, self.last_brightness)
        self.led_is_off = False
        logger.debug("LEDs activated due to activity")

    def _deactivate_leds(self):
        self.last_brightness = self.keyboard.get_brightness(0)
        self.keyboard.set_brightness(0, 0)
        self.led_is_off = True
        logger.debug("LEDs deactivated due to inactivity")

    async def _inactivity_check(self):
        while True:
            await asyncio.sleep(1)
            if (
                time.time() - self.last_event_time > self.timeout
                and not self.led_is_off
            ):
                self._deactivate_leds()

    async def start_monitoring(self, devices):
        self.active_tasks = [
            asyncio.create_task(self._handle_device(dev)) for dev in devices
        ]
        await self._inactivity_check()


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Advanced Keyboard Lighting Controller",
        epilog="Example: sudo ./lightctl.py --brightness 10 --timeout 30",
    )
    parser.add_argument(
        "-b", "--brightness", type=int, default=6, help="Initial brightness (0-255)"
    )
    parser.add_argument(
        "-t", "--timeout", type=int, default=300, help="Inactivity timeout in seconds"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug output"
    )
    return parser.parse_args()


async def event_loop(keyboard, timeout, brightness):
    devices = [InputDevice(path) for path in list_devices()]
    input_devices = [
        dev
        for dev in devices
        if ecodes.EV_KEY in dev.capabilities() or ecodes.EV_REL in dev.capabilities()
    ]

    logger.debug(
        f"{len(input_devices)} Input devices found{os.linesep}{os.linesep.join(str(_) for _ in input_devices)}"
    )
    if not input_devices:
        logger.error("No suitable input devices found")
        return

    monitor = DeviceMonitor(keyboard, timeout, brightness)
    await monitor.start_monitoring(input_devices)


def main():
    args = parse_arguments()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    if os.geteuid() != 0:
        logger.error("Root privileges required")
        sys.exit(1)

    keyboard = KeyboardLighting()

    # Signalhandler für sauberen Exit
    def signal_handler(sig, frame):
        keyboard.set_brightness(0, args.brightness)
        logger.info("Restored brightness and exited")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        keyboard.set_brightness(0, args.brightness)
        asyncio.run(event_loop(keyboard, args.timeout, args.brightness))
    except KeyboardInterrupt:
        signal_handler(None, None)
    except Exception as e:
        logger.error(f"Critical error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
