# Program to control the leds and LCD of the techtile rpi
# To be run as a service

import time
import os
import sys
import subprocess
import threading
from multiprocessing import Queue
import RPi.GPIO as GPIO
from threading import Timer, Thread
import atexit

from board import SCL, SDA
import busio
#from PIL import Image, ImageDraw, ImageFont
#import adafruit_ssd1306

from buttons import Buttons
from proximity_sensor import ProximitySensor
from leds import LEDs
from screen import Screen
from statistics import Statistics

BUTTON_LEFT_GPIO = 5
BUTTON_RIGHT_GPIO = 6
PROXIMITY_INT_GPIO = 26
LEDS_GPIO = 18
NUMBER_OF_LEDS = 5

buttons = Buttons({"left": BUTTON_LEFT_GPIO, "right": BUTTON_RIGHT_GPIO})
proximity_sensor = ProximitySensor(PROXIMITY_INT_GPIO)
leds = LEDs(LEDS_GPIO, 5)
screen = Screen()
statistics = Statistics()

def scroll_left():
    screen.button_scroll_page(-1, 60)
    screen.sleep(55)
    leds.backlight()
    leds.resume(55)

def scroll_right():
    screen.button_scroll_page(1, 60)
    screen.sleep(55)
    leds.backlight()
    leds.resume(55)

def turn_on():
    screen.wake()
    leds.backlight()

def turn_off():
    screen.sleep(20)
    leds.resume(20)

def exit_handler():
    screen.sleep(0)
    leds.resume(0)

def shutdown():
    screen.sleep(0)
    leds.resume(0)
    subprocess.call(['shutdown', '-h', 'now'], shell=False)

if __name__ == '__main__':
    GPIO.setmode(GPIO.BCM)
    buttons.register_callback("left", "short", scroll_left)
    buttons.register_callback("right", "short", scroll_right)
    buttons.register_callback("left", "medium", scroll_left)
    buttons.register_callback("right", "medium", scroll_right)

    buttons.register_callback("right", "multiple_long", shutdown)
    buttons.register_callback("right", "multiple_extra_long", shutdown)

    proximity_sensor.register_callback("closing", turn_on)
    proximity_sensor.register_callback("away", turn_off)
    
    leds.sync_effect_on("time", 60)
    leds.start_heartbeat()

    screen.register_statistics(statistics)

    atexit.register(exit_handler)

    while True:
        time.sleep(1)
        # Almost everything happens in callbacks, we just need to check the cpu for the high cpu led effect
        if not leds.backlight_on and not screen.awake:
            if statistics.get("cpu") > 50:
                leds.start_bounce()
            elif statistics.get("cpu") < 40:
                leds.start_heartbeat()

    
