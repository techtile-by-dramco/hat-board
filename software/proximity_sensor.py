import RPi.GPIO as GPIO
from vcnl3040 import VCNL3040

def proximity_callback(gpio):
    proximity_sensor.callback()

proximity_sensor = None

class ProximitySensor:
    def __init__(self, gpio):
        global proximity_sensor
        proximity_sensor = self

        self.vcnl = VCNL3040()

        GPIO.setup(gpio, GPIO.IN)
        GPIO.add_event_detect(gpio, GPIO.BOTH, callback=proximity_callback, bouncetime=10)

        self.vcnl.set_LED_current(180)
        self.vcnl.set_duty_cycle(80)
        self.vcnl.set_integration_time(8)
        self.vcnl.set_resolution(16)
        self.vcnl.set_forced_mode(False)
        
        self.vcnl.enable_interrupt_proximity_mode()
        self.vcnl.set_interrupt_mode("closing_and_away")
        
        self.vcnl.set_persistence(4)
        self.vcnl.start()

        self.calibrate()
        self.proximity = False

    def calibrate(self, low_threshold=None, delta=4):
        if low_threshold is None:
            reading = self.vcnl.get_data()
            self.vcnl.set_low_threshold(reading)
            self.vcnl.set_high_threshold(reading + delta)
        else:
            self.vcnl.set_low_threshold(low_threshold)
            self.vcnl.set_high_threshold(low_threshold + delta)


    def register_callback(self, action, function, *args, **kwargs):
        setattr(self, action + "_callback", function)
        setattr(self, action + "_args", args)
        setattr(self, action + "_kwargs", kwargs)

    def callback(self):
        if self.vcnl.get_data() < 3:
            self.proximity = False
        else:
            self.proximity = True

        self.evaluate_callback()

    def evaluate_callback(self):
        if self.proximity == True:
            self.execute_callback("closing")
        else:
            self.execute_callback("away")

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