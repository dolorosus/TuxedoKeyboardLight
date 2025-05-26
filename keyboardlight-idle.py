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

class KeyboardLight:

    def __init__(self, def_brightness, def_hex_colour, no_effect=False):

        self.classpath = "/sys/class/leds"
        self.keys = self._init_key_paths()
        self.brightness_path = {
            i: os.path.join(p, "brightness") for i, p in self.keys.items()
        }
        self.max_brightness_cache = self._cache_max_brightness(self.keys)
        self.multi_intensity_path = {
            i: os.path.join(p, "multi_intensity") for i, p in self.keys.items()
        }

        self.brightness_hdls, self.colour_hdls = self._init_handles(self.keys)

        self.knam2num = self._keynames()

        self.def_colour = self.hex_to_rgb(def_hex_colour)
        self.colour_cache = self._save_keyboard_multi_intensity()
        self.def_brightness = def_brightness
        self.last_brightness = def_brightness

        self.no_effect = no_effect

        self.off_effects = {
            1: self.off1,
            2: self.off2,
            3: self.off3,
            4: self.off4,
            5: self.off5,
            6: self.off6,
            7: self.off7,
            8: self.off8,
            9: self.off9,
            10: self.off10,
            11: self.off_generic,
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

    @staticmethod
    def _keynames():
        kl5 = {
            "esc": 105,
            "f1": 106,
            "f2": 107,
            "f3": 108,
            "f4": 109,
            "f5": 110,
            "f6": 111,
            "f7": 112,
            "f8": 113,
            "f9": 114,
            "f10": 115,
            "f11": 116,
            "f12": 117,
            "print": 118,
            "insert": 119,
            "delete": 120,
            "pos1": 121,
            "end": 122,
            "scr_up": 123,
            "scr_down": 124,
        }
        kl4 = {
            "circ": 84,
            "1": 85,
            "2": 86,
            "3": 87,
            "4": 88,
            "5": 89,
            "6": 90,
            "7": 91,
            "8": 92,
            "9": 93,
            "0": 94,
            "sz": 95,
            "eque": 96,
            "BS": 98,
            "numpad_num": 99,
            "numpad_slash": 100,
            "numpad_mult": 101,
            "numpad_minus": 102,
        }
        kl3 = {
            "tab": 63,
            "q": 65,
            "w": 66,
            "e": 67,
            "r": 68,
            "t": 69,
            "z": 70,
            "u": 71,
            "i": 72,
            "o": 73,
            "p": 74,
            "ü": 75,
            "+": 76,
            "enter": 77,
            "keypad_4": 78,
            "keypad_5": 79,
            "keypad_6": 80,
            "keypad_+": 81,
        }
        kl2 = {
            "shift_lock": 42,
            "a": 44,
            "y": 45,
            "d": 46,
            "f": 47,
            "g": 48,
            "h": 49,
            "nj": 50,
            "k": 51,
            "l": 52,
            "ö": 53,
            "ä": 54,
            "#": 55,
            "keypad_4": 57,
            "keypad_5": 58,
            "keypad_6": 59,
        }
        kl1 = {
            "lshift": 22,
            "lt": 23,
            "y": 24,
            "x": 25,
            "c": 26,
            "v": 27,
            "b": 28,
            "n": 29,
            "m": 30,
            ",": 31,
            ".": 32,
            "-": 33,
            "rshift": 35,
            "keypad_1": 36,
            "keypad_2": 37,
            "keypad_3": 38,
            "keypad_enter": 39,
        }
        kl0 = {
            "lstrg": 0,
            "fn": 2,
            "tux": 3,
            "lalt": 4,
            "space": 7,
            "altgr": 10,
            "rstrg": 12,
            "cup": 14,
            "cdown": 18,
            "cright": 15,
            "cleft": 13,
            "keypad_0": 16,
            "keypad_colon": 17,
        }
        k = {}
        k.update(kl0)
        k.update(kl1)
        k.update(kl2)
        k.update(kl3)
        k.update(kl4)
        k.update(kl5)
        return k

    @staticmethod
    def _init_handles(keys):

        brightness_hdl = {}
        colour_hdl = {}

        for key in keys:
            try:
                brightness_hdl[key] = open(os.path.join(keys[key], "brightness"), "r+")
                colour_hdl[key] = open(os.path.join(keys[key], "multi_intensity"), "r+")
            except Exception as e:
                logger.error(f"Error openening handle for key {key}: {str(e)}")

        return brightness_hdl, colour_hdl

    @staticmethod
    def _cache_max_brightness(keys):
        return {
            key: int(open(os.path.join(path, "max_brightness")).read().strip())
            for key, path in keys.items()
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
                c = self.def_colour
            try:
                # logger.debug(f"restore_keyboard_colors({key}, {c})")
                self.set_colour(key, c)
            except Exception as e:
                logger.error(f"Error restoring colour for key {key}: {str(e)}")

    def set_default_keyboard_colours(self):
        for key in self.keys:
            c = self.colour_cache[key]
            try:
                logger.debug(f"default_keyboard_colors({key}, {self.def_colour})")
                self.set_colour(key, self.def_colour)
            except Exception as e:
                logger.error(f"Error restoreing colour for key {key}: {str(e)}")

    def set_leds_on(self):
        if self.last_brightness < 2:
            self.last_brightness = self.def_brightness
            self.set_default_keyboard_colours()
            self.set_brightness(0, self.last_brightness)
        else:
            self.set_brightness(0, self.last_brightness)

    """All effects are highly adapted to the Stellaris keyboard and won't work correct on other systems"""

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
        _ = list(self.knam2num.values())
        rnd.shuffle(_)

        for i in _:
            self.set_colour(i, (0, 0, 0))
        self.set_brightness(0, 0)

    def off5(self):
        _ = list(self.knam2num.values())
        rnd.shuffle(_)

        for i in _:
            for c in [(255, 0, 0), (255, 255, 0)]:
                self.set_colour(i, c)
            self.set_brightness(0, 0)

    def off6(self):
        _ = list(self.knam2num.values())
        rnd.shuffle(_)

        for i in _:
            for c in [(255, 255, 0), (255, 0, 0), (0, 0, 0)]:
                self.set_colour(i, c)

        self.set_brightness(0, 0)

    def off7(self):
        for i in range(self.get_brightness(0), self.max_brightness_cache[0]):
            self.set_brightness(0, i)

        for i in range(self.max_brightness_cache[0], -1, -1):
            self.set_brightness(0, i)

    def off8(self):
        k = [
            range(0, 20),
            range(20, 40),
            range(40, 60),
            range(62, 82),
            range(83, 103),
            range(105, 125),
        ]
        colours = [(0, 0, 0)]
        for c in colours:
            for i in [range(0, 20), range(19, -1, -1)][rnd.randrange(2)]:
                for j in range(0, 6):
                    self.set_colour(k[j][i], c)

    def off9(self):
        k = [
            range(0, 20),
            range(20, 40),
            range(40, 60),
            range(62, 82),
            range(83, 103),
            range(105, 125),
        ]
        colours = [(0, 0, 0)]

        for c in colours:
            for i in range(0, 20):
                self.set_colour(k[0][i], c)
                self.set_colour(k[1][19 - i], c)
                self.set_colour(k[2][i], c)
                self.set_colour(k[3][19 - i], c)
                self.set_colour(k[4][i], c)
                self.set_colour(k[5][19 - i], c)

    def off10(self):
        k = [
            range(0, 20),
            range(20, 40),
            range(40, 60),
            range(62, 82),
            range(83, 103),
            range(105, 125),
        ]
        colours = [(255, 128, 0)]
        for c in colours:
            for i in range(0, 20):
                self.set_colour(k[0][i], c)
                self.set_colour(k[1][19 - i], c)
                self.set_colour(k[2][i], c)
                self.set_colour(k[3][19 - i], c)
                self.set_colour(k[4][i], c)
                self.set_colour(k[5][19 - i], c)

                self.set_colour(k[0][i], (0, 0, 0))
                self.set_colour(k[1][19 - i], (0, 0, 0))
                self.set_colour(k[2][i], (0, 0, 0))
                self.set_colour(k[3][19 - i], (0, 0, 0))
                self.set_colour(k[4][i], (0, 0, 0))
                self.set_colour(k[5][19 - i], (0, 0, 0))

    """ off generic """

    def off_generic(self):
        self.set_brightness(0, 0)

    def set_leds_off(self):
        """Saves the current keyboard colours
        turn keyboardlight off with random effect
        set brightness to 0
        restores colours
        """
        self.last_brightness = self.get_brightness(0)
        self.save_keyboard_colours()
        if self.no_effect:
            self.off_generic()
        else:
            self.off_effects.get(
                rnd.randint(1, len(self.off_effects)), self.off_generic
            )()

        self.set_brightness(0, 0)
        self.restore_keyboard_colours()

    def get_brightness(self, key_idx):

        if key_idx not in self.brightness_hdls:
            return 0
        try:
            self.brightness_hdls[key_idx].seek(0)
            return int(self.brightness_hdls[key_idx].read().strip())
        except Exception as e:
            logger.error(f"Error getting brightness: {str(e)}")
            return 0

    def get_colour(self, key_idx):

        if key_idx not in self.colour_hdls:
            return (0, 0, 0)
        try:
            self.colour_hdls[key_idx].seek(0)
            multicol = self.colour_hdls[key_idx].readline()
            return tuple([int(x) for x in multicol.strip().split()])
        except Exception as e:
            logger.error(f"Error getting colour: {str(e)}")
            return (0, 0, 0)
        
    def set_brightness(self, key_idx, brightness):
        if key_idx not in self.brightness_hdls:
            return
        try:
            safe_brightness = min(brightness, self.max_brightness_cache[key_idx])
            self.brightness_hdls[key_idx].write(str(safe_brightness))
            self.brightness_hdls[key_idx].flush()
        except Exception as e:
            logger.error(f"Error setting brightness: {str(e)}")

    def set_colour(self, key_idx, rgb):
        if key_idx not in self.colour_hdls:
            return
        try:
            # self.colour_hdls[key_index].seek(0)
            self.colour_hdls[key_idx].write(f"{rgb[0]} {rgb[1]} {rgb[2]}")
            self.colour_hdls[key_idx].flush()
        except Exception as e:
            logger.error(f"Error setting colour: {str(e)}")
    
    def config_key(self, key_idx, brightness, rgb):
        self.set_brightness(key_idx, brightness)
        self.set_colour(key_idx, rgb)

    def set_hexcolor(self, key_idx, hex_colour):
        rgb = self.hex_to_rgb(hex_colour)
        self.set_colour(key_idx, (f"{rgb[0]} {rgb[1]} {rgb[2]}"))

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

    keyboard = KeyboardLight(args.brightness, args.hexcolour, args.noeffect)
    colour = keyboard.hex_to_rgb(args.hexcolour)

    # Signalhandler for clean Exit
    def signal_handler(sig, frame):

        keyboard.set_brightness(0, args.brightness)
        logger.info("Restored brightness and exited")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        #keyboard.set_brightness(0, args.brightness)
        asyncio.run(event_loop(keyboard, args.timeout, args.brightness, colour))
    except KeyboardInterrupt:
        signal_handler(None, None)
    except Exception as e:
        logger.error(f"Critical error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
