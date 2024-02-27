import time
import os
import sys
import subprocess
import threading
from multiprocessing import Queue
import RPi.GPIO as GPIO
from threading import Timer

buttons = None

def button_callback(gpio):
    global buttons
    buttons.callback(gpio)

# Buttons classes and functions
class Button:
    def __init__(self, name, gpio, btns):
        self.name = name
        self.gpio = gpio
        self.pressed = False
        self.released = True
        self.press_time = -1.0
        self.press_duration = 0
        self.number_of_presses = 0
        
        self.buttons = btns

        # Now set them up in hardware
        GPIO.setup(gpio, GPIO.IN)
        GPIO.add_event_detect(gpio, GPIO.BOTH, callback=button_callback, bouncetime=10)

    def press(self):
        self.pressed = True
        self.released = False
        self.press_time = time.time()
        self.press_duration = 0

    def release(self):
        self.pressed = False
        self.released = True
        self.press_duration = time.time() - self.press_time
        self.press_time = -1.0

        if self.press_duration < 0.5:
            self.number_of_presses += 1
        else:
            self.number_of_presses = 1

        self.buttons.start_timer_evaluate_callback()

    def callback(self):
        if self.pressed and GPIO.input(self.gpio):
            self.release()
        elif self.released and not GPIO.input(self.gpio):
            self.press()

    def short(self):
        return self.press_duration <= 0.5

    def medium(self):
        return self.press_duration <= 1

    def long(self):
        return self.press_duration <= 2

    def extra_long(self):
        return self.press_duration > 2

    def reset(self):
        self.number_of_presses = 0
        self.press_duration = 0

    def evaluate_callback(self):
        if self.number_of_presses == 1:
            if self.short():
                self.execute_callback("short")
            elif self.medium():
                self.execute_callback("medium")
            elif self.long():
                self.execute_callback("long")
            elif self.extra_long():
                self.execute_callback("extra_long")

        # Multiple press
        if self.number_of_presses == 2:
            self.execute_callback("twice")
        elif self.number_of_presses == 3: 
            self.execute_callback("trice")

        self.reset()

    def register_callback(self, action, function, args, kwargs):
        setattr(self, action + "_callback", function)
        setattr(self, action + "_args", args)
        setattr(self, action + "_kwargs", kwargs)

    def execute_callback(self, action):
        if hasattr(self, action+"_callback"):
            f = getattr(self, action + "_callback")
            if getattr(self, action + "_args") is not None and getattr(self, action + "_kwargs") is not None: 
                f(*getattr(self, action + "_args"), **getattr(self, action + "_kwargs"))
            elif getattr(self, action + "_args") is not None: 
                f(*getattr(self, action + "_args"))
            elif getattr(self, action + "_kwargs") is not None: 
                f(**getattr(self, action + "_kwargs"))
            else:
                f()
            
class Buttons:
    def __init__(self, btns):
        global buttons

        buttons = self
        
        self.list = []
        for btn, gpio in btns.items():
            setattr(self, btn, Button(btn, gpio, self))
            self.list.append(getattr(self, btn)) 
            # These point to eachother, so one object with two names

        self.action_timer = None

    def get(self, gpio):
        return next((btn for btn in self.list if btn.gpio == gpio), None)

    def callback(self, gpio):
        self.get(gpio).callback()

    def start_timer_evaluate_callback(self):
        if self.action_timer is not None:
            self.action_timer.cancel()

        self.action_timer = Timer(0.25, self.evaluate_callback)
        self.action_timer.start()
        
    def evaluate_callback(self):
        pressed = [btn for btn in self.list if btn.number_of_presses >= 1]
        durations = [btn.press_duration for btn in self.list if btn.number_of_presses >= 1]
        number_of_presses = [btn.number_of_presses for btn in self.list if btn.number_of_presses >= 1]
        if len(pressed) > 1:
            if max(durations) <= 0.5:
                self.execute_callback("multiple_short")
            elif max(durations) <= 1:
                self.execute_callback("multiple_medium")
            elif max(durations) <= 2:
                self.execute_callback("multiple_long")
            elif max(durations) > 2:
                self.execute_callback("multiple_extra_long")

            if max(number_of_presses) == 2:
                self.execute_callback("multiple_twice")
            elif max(number_of_presses) == 3: 
                self.execute_callback("multiple_trice")

            # Event has been handled, reset it 
            for btn in pressed:
                btn.reset()
        elif len(pressed) == 1:
            pressed[0].evaluate_callback()

        # Reset timer and button states
        self.action_timer = None

    def register_callback(self, btn, action, function, *args, **kwargs):
        if not action.startswith("multiple"):
            getattr(self, btn).register_callback(action, function, args, kwargs)
        else:
            setattr(self, action + "_callback", function)
            setattr(self, action + "_args", args)
            setattr(self, action + "_kwargs", kwargs)

    def execute_callback(self, action):
        if hasattr(self, action+"_callback"):
            f = getattr(self, action + "_callback")
            if getattr(self, action + "_args") is not None and getattr(self, action + "_kwargs") is not None: 
                f(*getattr(self, action + "_args"), **getattr(self, action + "_kwargs"))
            elif getattr(self, action + "_args") is not None: 
                f(*getattr(self, action + "_args"))
            elif getattr(self, action + "_kwargs") is not None: 
                f(**getattr(self, action + "_kwargs"))
            else:
                f()