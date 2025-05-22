#!/usr/bin/env python3

#
#
# Switches on the keyboard illumination with a customisable brightness (--brightness).
# Switches the keyboard backlighting off if no mouse or keyboard inputs have been made
# after a configurable period of time (--timeout).
# The effects for turning off the keyboard illumination (kids all like it) can be disabled by (--noeffect)
#
#
import asyncio
import time
import logging
import signal
from evdev import InputDevice, ecodes, list_devices
import argparse
import os
import sys
import random as rnd

# Logging-configuration
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(funcName)s - %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)


class KeyboardLighting:

    def __init__(self, default_brightness, default_hex_colour, no_effect=False):

        self.classpath = "/sys/class/leds"
        self.keys = self._init_key_paths()
        self.brightness_path = {
            i: os.path.join(p, "brightness") for i, p in self.keys.items()
        }
        self.max_brightness_cache = self._cache_max_brightness()
        self.multi_intensity_path = {
            i: os.path.join(p, "multi_intensity") for i, p in self.keys.items()
        }

        self._init_handles()

        self.default_colour = self.hex_to_rgb(default_hex_colour)
        self.colour_cache = self._save_keyboard_multi_intensity()
        self.default_brightness = default_brightness
        self.last_brightness = default_brightness

        self.no_effect = no_effect

        self.off_actions = {
            1: self.off1,
            2: self.off2,
            3: self.off3,
            4: self.off4,
            5: self.off5,
            6: self.off6,
            7: self.off7,
            8: self.off,
        }

    def _init_key_paths(self):

        #
        # There is no such thing as 'rgb:kbd_backlight_0'
        # User keyindex 126 to access the lightbar
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

    def _init_handles(self):

        self.brightness_handles = {}
        self.colour_handles = {}

        for key in self.keys:
            try:
                self.brightness_handles[key] = open(
                    os.path.join(self.keys[key], "brightness"), "r+"
                )
                self.colour_handles[key] = open(
                    os.path.join(self.keys[key], "multi_intensity"), "r+"
                )
            except Exception as e:
                logger.error(f"Fehler beim Öffnen der Handles für Key {key}: {str(e)}")

    def _cache_max_brightness(self):
        return {
            key: int(open(os.path.join(path, "max_brightness")).read().strip())
            for key, path in self.keys.items()
        }

    def _save_keyboard_multi_intensity(self):
        cache = {}
        for key in self.keys:
            try:
                logging.debug(f"save key{key} colour {self.get_colour(key)}")
                cache[key] = self.get_colour(key)
            except Exception as e:
                logger.error(f"Error caching colour for key {key}: {str(e)}")
                cache[key] = 0
        return cache

    def save_keyboard_colours(self):
        self.colour_cache = self._save_keyboard_multi_intensity()

    def restore_keyboard_colours(self):
        for key, c in self.colour_cache.items():
            if c == (0, 0, 0):
                c = self.default_colour
            try:
                # logger.debug(f"restore_keyboard_colors({key}, {c})")
                self.set_colour(key, c)
            except Exception as e:
                logger.error(f"Error restoring colour for key {key}: {str(e)}")

    def set_default_keyboard_colours(self):
        for key in self.keys:
            c = self.colour_cache[key]
            try:
                logger.debug(f"default_keyboard_colors({key}, {self.default_colour})")
                self.set_colour(key, self.default_colour)
            except Exception as e:
                logger.error(f"Error restoreing colour for key {key}: {str(e)}")

    def set_leds_on(self):
        if self.last_brightness < 2:
            self.last_brightness = self.default_brightness
            self.set_brightness(0, self.last_brightness)
            self.set_default_keyboard_colours()
        else:
            self.set_brightness(0, self.last_brightness)

    def off1(self):
        _ = [range(64, -1, -1), range(0, 64)]
        for i in _[rnd.randint(0, len(_) - 1)]:
            self.set_colour(i, (0, 0, 0))
            self.set_colour(126 - i, (0, 0, 0))

    def off2(self):
        cols = [(255, 0, 0), (0, 255, 0), (255, 0, 255)]
        _ = [range(64, -1, -1), range(0, 64)]
        rnd.shuffle(cols)
        for c in cols:
            for i in _[rnd.randint(0, len(_) - 1)]:
                self.set_colour(i, c)
                self.set_colour(126 - i, c)

        for i in _[rnd.randint(0, len(_) - 1)]:
            self.set_colour(i, (0, 0, 0))
            self.set_colour(126 - i, (0, 0, 0))

    def off3(self):
        _ = [range(126, -1, -1), range(0, 126, 1)]
        for i in _[rnd.randint(0, len(_) - 1)]:
            self.set_colour(i, (0, 0, 0))
        self.set_brightness(0, 0)

    def off4(self):
        _ = list(range(0, 126, 1))
        rnd.shuffle(_)

        for i in _:
            self.set_colour(i, (0, 0, 0))
        self.set_brightness(0, 0)

    def off5(self):
        _ = list(range(0, 126, 1))
        rnd.shuffle(_)

        for i in _:
            for c in [(255, 0, 0)]:
                self.set_colour(i, (255, 0, 0))
        self.set_brightness(0, 0)

    def off6(self):
        _ = list(range(0, 126, 1))
        rnd.shuffle(_)

        for i in _:
            for c in [(255, 255, 0), (255, 0, 0), (0, 0, 0)]:
                self.set_colour(i, c)

        self.set_brightness(0, 0)

    def off7(self):
        for i in range(self.get_brightness(0), self.max_brightness_cache[0]):
            self.set_brightness(0, i)
            # time.sleep(0.01)
        for i in range(self.max_brightness_cache[0], -1, -1):
            self.set_brightness(0, i)

    def off(self):
        self.set_brightness(0, 0)

    def set_leds_off(self):
        self.last_brightness = self.get_brightness(0)
        self.save_keyboard_colours()
        if self.no_effect:
            self.off()
        else:
            off_effect = self.off_actions.get(
                rnd.randint(1, len(self.off_actions)), self.off
            )
            off_effect()

        self.set_brightness(0, 0)
        self.restore_keyboard_colours()

    def get_brightness(self, key_index):

        if key_index not in self.brightness_handles:
            return 0
        try:
            self.brightness_handles[key_index].seek(0)
            return int(self.brightness_handles[key_index].read().strip())
        except Exception as e:
            logger.error(f"Error getting brightness: {str(e)}")
            return 0

    def set_brightness(self, key_index, brightness):
        if key_index not in self.brightness_handles:
            return
        try:
            safe_brightness = min(brightness, self.max_brightness_cache[key_index])
            self.brightness_handles[key_index].seek(0)
            self.brightness_handles[key_index].write(str(safe_brightness))
            self.brightness_handles[key_index].flush()
        except Exception as e:
            logger.error(f"Error setting brightness: {str(e)}")

    def get_colour(self, key_index):

        if key_index not in self.colour_handles:
            return (0, 0, 0)
        try:
            self.colour_handles[key_index].seek(0)
            multicol = self.colour_handles[key_index].readline()
            return tuple([int(x) for x in multicol.strip().split()])
        except Exception as e:
            logger.error(f"Error getting colour: {str(e)}")
            return (0, 0, 0)

    def get_cached_colour(self, key_idx):
        return self.colour_cache[key_idx]

    def set_colour(self, key_index, rgb):
        if key_index not in self.colour_handles:
            return
        try:
            self.colour_handles[key_index].seek(0)
            self.colour_handles[key_index].write(f"{rgb[0]} {rgb[1]} {rgb[2]}")
            self.colour_handles[key_index].flush()
        except Exception as e:
            logger.error(f"Error setting colour: {str(e)}")

    def set_hexcolor(self, key_idx, hex_colour):
        rgb = self.hex_to_rgb(hex_colour)
        try:
            pfad = os.path.join(self.keys[key_idx], "multi_intensity")
            with open(pfad, "w") as f:
                f.write(f"{rgb[0]} {rgb[1]} {rgb[2]}")
        except Exception as e:
            logger.error(f"Error setting color: {str(e)}")

    def config_key(self, key_idx, brightness, rgb):
        self.set_brightness(key_idx, brightness)
        self.set_colour(key_idx, rgb)

    def hex_to_rgb(self, hex_color):

        s = str(hex_color).lstrip("#").upper()
        if len(s) != 6:
            raise ValueError(
                f"Hex colour code must have the format '#rrggbb' or 'rrggbb': '{hex_color}'"
            )
        if not set(s) <= set("0123456789ABCDEF"):
            raise ValueError(f"Invalid characters in hex colour code:'{hex_color}'")

        return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


class DeviceMonitor:
    def __init__(self, keyboard, timeout, default_brightness, default_colour):
        self.keyboard = keyboard
        self.timeout = timeout
        self.default_brightness = default_brightness
        self.default_colour = default_colour
        self.last_event_time = time.time()
        self.led_is_off = False
        self.last_brightness = default_brightness
        self.active_tasks = []

    async def _handle_device(self, device):
        try:
            async for event in device.async_read_loop():
                #
                # An event fom the monitored devices has arrived
                #
                self.last_event_time = time.time()
                if self.led_is_off:
                    self._activate_leds()
        except OSError as e:
            logger.error(f"Device error {device.path}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")

    def _activate_leds(self):
        # set default brightness as minimal brightness
        self.keyboard.set_leds_on()
        self.led_is_off = False
        logger.debug("LEDs activated due to activity")

    def _deactivate_leds(self):
        self.keyboard.set_leds_off()
        self.led_is_off = True
        logger.debug("LEDs deactivated due to inactivity")

    async def _inactivity_check(self):
        while True:
            await asyncio.sleep(1)

            # due to short circuit eval. in python it should be faster to check the boolean first.
            if (
                not self.led_is_off
                and time.time() - self.last_event_time > self.timeout
            ):
                self._deactivate_leds()

    async def start_monitoring(self, devices):
        self.active_tasks = [
            asyncio.create_task(self._handle_device(dev)) for dev in devices
        ]
        await self._inactivity_check()


def parse_arguments():
    def hex_color_type(value):
        s = str(value).lstrip("#").upper()
        if len(s) != 6:
            raise ValueError(
                f"Hex colour code must have the format '#rrggbb' or 'rrggbb': '{value}'"
            )
        if not set(s) <= set("0123456789ABCDEF"):
            raise ValueError(f"Invalid characters in hex colour code:'{value}'")
        return value

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
        "-c",
        "--colour",
        type=hex_color_type,
        dest="hexcolour",
        default="#0000FF",
        help="Colour (#rrggbb)",
    )
    parser.add_argument(
        "-n",
        "--noeffect",
        dest="noeffect",
        action="store_true",
        help="Disable effects for turning lights off",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug output"
    )
    return parser.parse_args()


async def event_loop(keyboard, timeout, brightness, colour):
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

    monitor = DeviceMonitor(keyboard, timeout, brightness, colour)
    await monitor.start_monitoring(input_devices)


def main():
    args = parse_arguments()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    if os.geteuid() != 0:
        logger.error("Root privileges required")
        sys.exit(1)

    keyboard = KeyboardLighting(args.brightness, args.hexcolour, args.noeffect)
    colour = keyboard.hex_to_rgb(args.hexcolour)

    # Signalhandler for clean Exit
    def signal_handler(sig, frame):
        keyboard.set_brightness(0, args.brightness)
        logger.info("Restored brightness and exited")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        keyboard.set_brightness(0, args.brightness)
        asyncio.run(event_loop(keyboard, args.timeout, args.brightness, colour))
    except KeyboardInterrupt:
        signal_handler(None, None)
    except Exception as e:
        logger.error(f"Critical error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
