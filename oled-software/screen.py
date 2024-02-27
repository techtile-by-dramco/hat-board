
import time
import os
import sys
import subprocess
import threading
import numbers
from multiprocessing import Queue
import RPi.GPIO as GPIO
from threading import Timer, Thread

from board import SCL, SDA
import busio
from PIL import Image, ImageDraw, ImageFont, ImageChops
from ssd1306 import SSD1306_128_64

class Screen:
    def __init__(self):
        self.pages = ["identification", "usage"]
        self.active_page = 0
        self.scroll_timer = None
        self.sleep_timer = None
        self.sleep_timeout = 20
        self.statistics = None
        self.awake = False

        self.display = SSD1306_128_64(rst=None)
        self.display.begin()

        # Clear display.
        self.display.set_contrast(255)
        self.display.dim(False)

        self.width = self.display.width
        self.height = self.display.height
        self.image = Image.new('1', (self.width, self.height))

        # Get drawing object to draw on image.
        self.draw = ImageDraw.Draw(self.image)

        self.top = 0
        self.bottom = self.height-1
        
        self.cursor_x = 0
        self.cursor_y = 0

        # Load default font.
        #font = ImageFont.load_default()
        self.font_small = ImageFont.truetype('OpenSans-SemiBold.ttf', 9)
        self.font_medium = ImageFont.truetype('OpenSans-SemiBold.ttf', 11)
        self.font_large = ImageFont.truetype('OpenSans-ExtraBold.ttf', 13)

        self.clear()
        
    def clear(self, write = True, for_sleep = False):
        self.display.clear()
        # Draw a black filled box to clear the image.
        self.draw.rectangle((0, 0, self.width, self.height), outline=0, fill=0)
        if write:
            self.display.display()
        self.cursor_y = 0
        self.cursor_x = 0
        if for_sleep:
            if self.scroll_timer is not None:
                self.scroll_timer.cancel()
            self.awake = False

    def show(self):
        self.display.image(self.image)
        show_thread = Thread(target=self.display.display)
        show_thread.start()

    def draw_paging_dots(self, number_of_dots, active_dot):
        single_dot_width = 7
        middle = self.width/2
        dots_width = number_of_dots * single_dot_width
        for i in range(number_of_dots):
            fill = 0
            if i == active_dot:
                fill = 255
            self.draw.ellipse((middle - dots_width/2 + i*single_dot_width + single_dot_width/2, self.bottom-3, middle - dots_width/2 + i*single_dot_width + single_dot_width/2 + 3, self.bottom), outline=255, fill=fill)

    def draw_rounded_rectangle(self, xy, radius, fill=None, outline=None):
        # Draw the rounded rectangle
        x1, y1, x2, y2 = xy
        if fill:
            self.draw.rectangle([(x1, y1 + radius), (x2, y2 - radius)], fill=fill, outline=outline)
            self.draw.rectangle([(x1 + radius, y1), (x2 - radius, y2)], fill=fill, outline=outline)
            self.draw.ellipse([(x1, y1), (x1 + radius * 2, y1 + radius * 2)], fill=fill, outline=outline)
            self.draw.ellipse([(x2 - radius * 2, y2 - radius * 2), (x2, y2)], fill=fill, outline=outline)
            self.draw.ellipse([(x1, y2 - radius * 2), (x1 + radius * 2, y2)], fill=fill, outline=outline)
            self.draw.ellipse([(x2 - radius * 2, y1), (x2, y1 + radius * 2)], fill=fill, outline=outline)
        else:
            self.draw.line([(x1 + radius, y1), (x2 - radius, y1)], fill=outline)
            self.draw.line([(x1 + radius, y2), (x2 - radius, y2)], fill=outline)
            self.draw.line([(x1, y1 + radius), (x1, y2 - radius)], fill=outline)
            self.draw.line([(x2, y1 + radius), (x2, y2 - radius)], fill=outline)
            self.draw.arc((x1, y1, x1 + radius*2, y1 + radius*2), 180, 270, fill=outline)
            self.draw.arc((x2 - radius*2, y2 - radius*2, x2, y2), 0, 90, fill=outline)
            self.draw.arc((x1, y2 - radius*2, x1 + radius*2, y2), 90, 180, fill=outline)
            self.draw.arc((x2 - radius*2, y1, x2, y1 + radius*2), 270, 360, fill=outline)

    def draw_pill_text(self, align, text, font=None, fill=None, outline=None, margin_top=0):
        if font is None:
            font = self.font_medium
        text_width, text_height = self.draw.textsize(text, font=font)

        y = self.cursor_y + margin_top

        x = 3
        if align == "center":
            x = self.width/2 - (text_width+12)/2
        elif align == "right":
            x = self.width - (text_width+12)

        self.draw_rounded_rectangle((x, y, x+text_width+12, y+text_height+text_height/3), (text_height+text_height/3)/2, fill, outline)

        fill_text = 255
        if fill is not None and fill > 0:
            fill_text = 0
        self.draw.text((x+7, y+text_height/5), text,  font=font, fill=fill_text)

        self.cursor_y = y + y+text_height+text_height/3

    def draw_text(self, align, text, font=None, fill=None, outline=None, margin_top=0):
        if font is None:
            font = self.font_medium
        text_width, text_height = self.draw.textsize(text, font=font)

        x = 3
        if align == "center":
            x = self.width/2 - (text_width)/2
        elif align == "right":
            x = self.width - (text_width)

        y = self.cursor_y + margin_top
        self.draw.text((x, y), text, font=font, fill=fill, outline=outline)
        self.cursor_y = y + text_height

    def draw_bar(self, text, value, max_value, unit, font=None, line=True, margin_top=0):
        if font is None:
            font = self.font_medium

        percentage = value/max_value*100
        if unit == "%":
            value_string = f"{value:.1f}/{max_value:.1f} {unit}"
        else:
            value_string = f"{value:.1f}/{max_value:.1f} {unit} ({percentage:.0f}%)"
        text_width, text_height = self.draw.textsize(text, font=font)
        value_width, value_height = self.draw.textsize(value_string, font=font)
        self.draw.text((self.cursor_x+2, self.cursor_y), text, font=font, fill=255, outline=0)
        self.draw.text((self.width-value_width-2, self.cursor_y), value_string, font=font, fill=255, outline=0)
        if line:
            self.draw.line([(0, max(text_height, value_height) + self.cursor_y + 4), (self.width, max(text_height, value_height) + self.cursor_y + 4)], fill=255)

        graphs = Image.new('1', (self.width, self.height))
        draw_graphs = ImageDraw.Draw(graphs)
        draw_graphs.rectangle([(0, self.cursor_y), (percentage/100*self.width, self.cursor_y + max(text_height, value_height) + 2)], fill=255, outline=255)
        graphs = ImageChops.logical_xor(self.image, graphs)

        self.image.paste(graphs, (0,0))
        self.cursor_y = max(text_height, value_height) + self.cursor_y + 6

    def draw_page(self, page):
        if isinstance(page, numbers.Number):
            page = self.pages[page]

        self.clear(False)

        if self.statistics is not None:
            if page == "identification":
                self.draw_paging_dots(len(self.pages), 0)
                self.draw.rectangle([(0, 0), (self.width, self.height/2-5)], fill=255, outline=255)
                self.draw_text("center", self.statistics.get("hostname"), font=self.font_large, fill=0, margin_top=self.height/4-12)
                self.draw_text("center", self.statistics.get("ip"), font=self.font_small, fill=255, margin_top=self.height/4+4)
            elif page == "usage":
                self.draw_paging_dots(len(self.pages), 1)
                self.draw_bar("CPU", self.statistics.get("cpu"), 100, "%", font=self.font_medium,)
                self.draw_bar("RAM", self.statistics.get("ram")/1024, self.statistics.get("ram_max")/1024, "GB", font=self.font_medium,)
                self.draw_bar("DISK", self.statistics.get("disk"), self.statistics.get("disk_max"), "GB", font=self.font_medium, line=False)
                
    def start_scroll_page(self, timeout = 10):
        self.draw_page(self.active_page)
        self.show()
        self.scroll_timer = Timer(timeout, self.loop_scroll_page, [timeout])
        self.scroll_timer.start()

    def loop_scroll_page(self, timeout = 10):
        self.scroll_page(1)
        self.scroll_timer = Timer(timeout, self.loop_scroll_page, [timeout])
        self.scroll_timer.start()

    def scroll_page(self, direction):
        self.active_page = (self.active_page + 1) % len(self.pages)
        self.draw_page(self.active_page)
        self.show()

    def button_scroll_page(self, direction, timeout):
        self.awake = True
        self.scroll_page(direction)
        if self.scroll_timer is not None:
        	self.scroll_timer.cancel()
        if self.sleep_timer is not None:
            self.sleep_timer.cancel()

    def cancel_scroll_page(self):
        if self.scroll_timer is not None:
            self.scroll_timer.cancel()

    def register_statistics(self, statistics):
        self.statistics = statistics

    def sleep(self, timeout=20):
        self.sleep_timeout = timeout

        if self.awake:
            if self.sleep_timer is not None:
                self.sleep_timer.cancel()
            self.sleep_timer = Timer(self.sleep_timeout, self.clear, [True, True])
            self.sleep_timer.start()


    def wake(self):
        if not self.awake:
            self.awake = True
            self.start_scroll_page()