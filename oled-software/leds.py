import time
import board
import neopixel
from adafruit_blinka.microcontroller.bcm283x.pin import Pin
from itertools import groupby
from threading import Thread, Timer
import math

class LEDs:
    def __init__(self, gpio, number_of_leds, brightness=0.5, auto_write=False):
        self.number_of_leds = number_of_leds
        self.current_colors = []
        self.current_colors = [(0,0,0)]*self.number_of_leds
        self.resume_colors = []
        self.resume_effect = False

        p = Pin(gpio)
        self.pixels = neopixel.NeoPixel(p, number_of_leds, brightness=brightness)

        self.fade_time = 0.5
        self.fade_steps = 50

        self.direction = 1
        # Define the current index of the bouncing LED
        self.current_index = 0

        self.effect_thread = None
        self.effect_running = False
        self.effect_timer = None
        self.effect = ""
        self.effect_args = []
        self.effect_sync_method = None
        self.effect_sync_value = 0

        self.backlight_on = False

        self.bounce_color = (255,100,0)
        self.heartbeat_color = (100,100,50)
        self.backlight_color = (200,200,50)

        self.show()
        
    def fill(self, color):
        self.current_colors = [color]*self.number_of_leds
        self.show()

    def fill_fade(self, color):
        new_colors = [color]*self.number_of_leds
        self.fade_to(new_colors)

    def pause(self):
        if self.effect_running:
            self.resume_effect = True
        self.stop_effect()
        self.resume_colors = self.current_colors.copy()

    def backlight(self, target_color=None):
        if target_color is None:
            target_color = self.backlight_color

        if not self.backlight_on:
            self.pause()
            backlight_thread = Thread(target=self.fill_fade, args=(target_color, ))
            backlight_thread.start()
            self.backlight_on = True

    def resume(self, timeout=0):
        if timeout > 0:
            if self.effect_timer is not None:
                self.effect_timer.cancel()
            self.effect_timer = Timer(timeout, self.resume, [0])
            self.effect_timer.start()
        else:
            self.backlight_on = False
            if self.resume_effect: 
                self.fill_fade((0,0,0))
                if self.effect == "bounce":
                    self.start_bounce(*self.effect_args)
                elif self.effect == "heartbeat":
                    self.start_heartbeat(*self.effect_args)
            else:
                self.fade_to(self.resume_colors)

    def clear(self):
        self.current_colors = [(0,0,0)]*self.number_of_leds
        self.show()

    def show(self):
        for i in range(0, self.number_of_leds):
            self.pixels[i] = self.current_colors[i]
        self.pixels.show()

    def gamma_correct(self, led_val):
        factor = 2.8
        max_val = (1 << 8) - 1.0
        corrected = pow(led_val / max_val, factor) * max_val
        return int(min(255, max(0, corrected)))

    def fade_to(self, target_colors, fade_time=None, fade_steps=None, allow_effect_break=False):
        if fade_time is None:
            fade_time = self.fade_time
        if fade_steps is None:
        	fade_steps = self.fade_steps

        # Calculate the step size for each color component for each LED
        step_sizes = []
        for i, target_color in enumerate(target_colors):
            # Extract RGB values from the current color of the specified LED
            r1, g1, b1 = self.current_colors[i]

            # Extract RGB values from the target color
            r2, g2, b2 = target_color

            # Calculate the step size for each color component
            step_r = (r2 - r1) / fade_steps
            step_g = (g2 - g1) / fade_steps
            step_b = (b2 - b1) / fade_steps

            step_sizes.append((step_r, step_g, step_b))

        # Initialize variables for the current colors
        current_rs = [r1 for r1, _, _ in self.current_colors]
        current_gs = [g1 for _, g1, _ in self.current_colors]
        current_bs = [b1 for _, _, b1 in self.current_colors]

        # Fade all LEDs to the target colors
        for _ in range(fade_steps):
            for i, target_color in enumerate(target_colors):
                # Extract RGB values from the current color of the specified LED
                current_r = current_rs[i]
                current_g = current_gs[i]
                current_b = current_bs[i]

                # Extract RGB values from the target color
                r2, g2, b2 = target_color

                # Calculate the new RGB values based on the step sizes
                current_rs[i] = max(0, min(255, int(current_r + step_sizes[i][0])))
                current_gs[i] = max(0, min(255, int(current_g + step_sizes[i][1])))
                current_bs[i] = max(0, min(255, int(current_b + step_sizes[i][2])))

                self.current_colors[i] = (current_rs[i], current_gs[i], current_bs[i])
                self.pixels[i] = (self.gamma_correct(current_rs[i]), self.gamma_correct(current_gs[i]), self.gamma_correct(current_bs[i]))

            self.pixels.show()

            if allow_effect_break and not self.effect_running:
                break
            else:
                time.sleep(fade_time/fade_steps)

        # Rounding errors apart, this should be the target color, save it in the current_colors


    def bounce(self, target_color, fade_time=0.01, fade_steps=10):
        new_colors = self.current_colors.copy()
        
        new_colors[max(0, min(self.number_of_leds-1, self.current_index - 2))] = (0,0,0)
        new_colors[max(0, min(self.number_of_leds-1, self.current_index + 2))] = (0,0,0)

        half_brightness_color = tuple(int(0.5 * c) for c in target_color)
        new_colors[max(0, min(self.number_of_leds-1, self.current_index - 1))] = half_brightness_color
        new_colors[max(0, min(self.number_of_leds-1, self.current_index + 1))] = half_brightness_color

        new_colors[self.current_index] = target_color

        self.fade_to(new_colors,0.01,10, allow_effect_break=True)

 		# Update the index of the bouncing LED based on the direction
        self.current_index += self.direction

        
        # Check if the LED has reached the end of the strip
        if self.current_index == 0 or self.current_index == len(self.current_colors) - 1:
            # Change the direction of the bouncing LED
            self.direction *= -1

    def loop_bounce(self, target_color=(255,255,0), delay=0, fade_time=0.01, fade_steps=10):
        self.effect_running = True
        while self.effect_running:
            self.bounce(target_color, fade_time, fade_steps)
            start = time.time()
            while time.time() - start < delay and self.effect_running:
                time.sleep(0.01)

    def start_bounce(self, target_color=None, delay=0, fade_time=0.01, fade_steps=10):
        if target_color is None:
            target_color = self.bounce_color
        self.effect_thread = Thread(target=self.loop_bounce, args=(target_color,delay, fade_time, fade_steps))
        self.effect_thread.start()
        self.effect = "bounce"
        self.effect_args = [target_color, delay, fade_time, fade_steps]

    def stop_effect(self):
        self.effect_running = False

    def heartbeat(self, target_color, on_delay=0.3, fade_time=2, fade_steps=50):
        # Make sure we can immediately stop this effect (because we're rejoining threads when canceling)
        new_colors = [target_color]*self.number_of_leds
        if self.effect_running:
            self.fade_to(new_colors, fade_time, fade_steps, allow_effect_break=True)
        start = time.time()
        while time.time() - start < on_delay and self.effect_running:
            time.sleep(0.01)
        new_colors = [(0,0,0)]*self.number_of_leds
        if self.effect_running:
            self.fade_to(new_colors, fade_time, fade_steps, allow_effect_break=True)

    def loop_heartbeat(self, target_color, on_delay=0.3, off_delay=10, fade_time=2, fade_steps=50):
        self.effect_running = True
        last_heartbeat = 0
        while self.effect_running:
            if self.effect_sync_method is None or self.effect_sync_method == "":
                if time.time() - last_heartbeat > off_delay:
                    self.heartbeat(target_color, on_delay, fade_time, fade_steps)
                    last_heartbeat = time.time()
                else:
                    time.sleep(0.1)
            elif self.effect_sync_method == "time" and self.effect_sync_value > 0:
                if int(time.time() % self.effect_sync_value) == 0:
                    self.heartbeat(target_color, on_delay, fade_time, fade_steps)
                    last_heartbeat = time.time()
                else:
                    time.sleep(0.1)

    def start_heartbeat(self, target_color=None, on_delay=0.3, off_delay=10, fade_time=2, fade_steps=50):
        if target_color is None:
            target_color = self.heartbeat_color
        self.effect_thread = Thread(target=self.loop_heartbeat, args=(target_color, on_delay, off_delay, fade_time, fade_steps))
        self.effect_thread.start()
        self.effect = "heartbeat"
        self.effect_args = [target_color, on_delay, off_delay, fade_time, fade_steps]
        

    def sync_effect_on(self, sync_method, sync_value):
        self.effect_sync_method = sync_method
        self.effect_sync_value = sync_value
