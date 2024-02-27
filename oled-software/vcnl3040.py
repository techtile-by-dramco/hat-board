import time

VCNL3040_DEV_ADDRESS = 0x60

# - REGISTERS
CMD_CONFIG1                 = 0x03
CMD_CONFIG3                 = 0x04
CMD_CANCELLATION            = 0x05
CMD_THRESHOLD_LOW           = 0x06
CMD_THRESHOLD_HIGH          = 0x07
CMD_OUTPUT_DATA             = 0x08
CMD_INT_FLAG                = 0x0B
CMD_DEVICE_ID               = 0x0C

# - VALUES AND MASKS
SLEEP                       = 0x01

PS_ENABLE_MASK              = 0xFFFE
PS_ENABLE_POS               = 0

# --- LED current settings
LED_CURRENT_50mA            = 0x00
LED_CURRENT_75mA            = 0x01
LED_CURRENT_120mA           = 0x02
LED_CURRENT_140mA           = 0x03
LED_CURRENT_160mA           = 0x04
LED_CURRENT_180mA           = 0x05
LED_CURRENT_200mA           = 0x07
LED_CURRENT_MASK            = 0xF8FF
LED_CURRENT_POS             = 8

# --- Duty cycle for sensors LED
PS_DUTY_40                  = 0x00
PS_DUTY_80                  = 0x01
PS_DUTY_160                 = 0x02
PS_DUTY_320                 = 0x03
PS_DUTY_MASK                = 0xFF3F
PS_DUTY_POS                 = 6

# --- Measurement integration time 1T0 - IT = 1 -  125us (application note page 5 )
PS_IT_1T0                   = 0x00
PS_IT_1T5                   = 0x01
PS_IT_2T0                   = 0x02
PS_IT_2T5                   = 0x03
PS_IT_3T0                   = 0x04
PS_IT_3T5                   = 0x05
PS_IT_4T0                   = 0x06
PS_IT_8T0                   = 0x07
PS_IT_MASK                  = 0xFFF1
PS_IT_POS                   = 1

# --- Resolution settings
PS_RES_12                   = 0
PS_RES_12                   = 1
PS_RES_MASK                 = 0xF7FF
PS_RES_POS                  = 11

# --- Interupt persistance setting - how many consecutive measruements
# --- have to be made in interupt range to trigger interupt (datasheet page 11)
PS_PERS_1                   = 0x00
PS_PERS_2                   = 0x01
PS_PERS_3                   = 0x02
PS_PERS_4                   = 0x03
PS_PERS_MASK                = 0xFFCF
PS_PERS_POS                 = 4

# --- Interupt modes
PS_INT_DISABLED             = 0x00
PS_INT_CLOSING              = 0x01
PS_INT_AWAY                 = 0x02
PS_INT_CLOSING_AWAY         = 0x03
PS_INT_MASK                 = 0xFCFF
PS_INT_POS                  = 8

PS_INT_PROXIMITY_MODE_MASK  = 0xBFFF
PS_INT_PROXIMITY_MODE_VAL   = 0x01 << 14

PS_INT_NORMAL_MODE_MASK     = 0xBFFF
PS_INT_NORMAL_MODE_VAL      = 0x00 << 14

PS_FORCED_MODE_MASK         = 0xFFF7
PS_FORCED_MODE_POS          = 3
PS_FORCED_TRIGGER_MASK      = 0xFFFB
PS_FORCED_TRIGGER_POS       = 2

PS_SUNLIGHT_IMMUNITY_MASK   = 0xFFFE
PS_SUNLIGHT_IMMUNITY_POS    = 0

class VCNL3040(object):
    def __init__(self, address=VCNL3040_DEV_ADDRESS, i2c=None, **kwargs):
        if i2c is None:
            import Adafruit_GPIO.I2C as I2C
            i2c = I2C
        self._device = i2c.get_i2c_device(address, **kwargs)

        self.forced = False

    # ---- Low level write command -----
    def write(self, command, value):
        return self._device.write16(command, value)

    # ---- Low level read command -----
    def read(self, command):
        return self._device.readU16(command)

    # ---- Higher level commands ----
    def is_connected(self):
        return self.read(CMD_DEVICE_ID) == 0x186

    def start(self):
        _current_setting = self.read(CMD_CONFIG1)
        _current_setting = _current_setting & PS_ENABLE_MASK
        _current_setting = _current_setting | (0 << PS_ENABLE_POS)

        self.write(CMD_CONFIG1, _current_setting)

    def stop(self):
        _current_setting = self.read(CMD_CONFIG1)
        _current_setting = _current_setting & PS_ENABLE_MASK
        _current_setting = _current_setting | (1 << PS_ENABLE_POS)

        self.write(CMD_CONFIG1, _current_setting)

    def sleep(self):
        _current_setting = self.read(CMD_CONFIG1)
        _current_setting = _current_setting | SLEEP
        self.write(_current_setting)

    def get_interrupt_flag(self):
        _current_value = self.read(CMD_INT_FLAG)
        return _current_value >> 8

    def get_data(self):
        if self.forced:
            _current_setting = self.read(CMD_CONFIG3)
            _current_setting = _current_setting & PS_FORCED_TRIGGER_MASK
            _current_setting = _current_setting | (1 << PS_FORCED_TRIGGER_POS)
            self.write(CMD_CONFIG3, _current_setting)
            
        return self.read(CMD_OUTPUT_DATA)

    def set_forced_mode(self, forced):
        _current_setting = self.read(CMD_CONFIG3)
        _current_setting = _current_setting & PS_FORCED_MODE_MASK
        _current_setting = _current_setting | (int(forced) << PS_FORCED_MODE_POS)
        
        self.write(CMD_CONFIG3, _current_setting)

        self.forced = forced

    def set_sunlight_cancellation(self, si):
        _current_setting = self.read(CMD_CONFIG3)
        _current_setting = _current_setting & PS_SUNLIGHT_IMMUNITY_MASK
        _current_setting = _current_setting | (int(si) << PS_SUNLIGHT_IMMUNITY_POS)
        print(hex(_current_setting))
        self.write(CMD_CONFIG3, _current_setting)


    def set_LED_current(self, current):
        _current_value = LED_CURRENT_50mA
        if current == 50:
            _current_value = LED_CURRENT_50mA
        elif current == 75:
            _current_value = LED_CURRENT_75mA
        elif current == 120:
            _current_value = LED_CURRENT_120mA
        elif current == 140:
            _current_value = LED_CURRENT_140mA
        elif current == 160:
            _current_value = LED_CURRENT_160mA
        elif current == 180:
            _current_value = LED_CURRENT_180mA
        else:
            raise ValueError('Current setting can only be 50 mA, 75 mA, 120 mA, 140 mA, 160 mA, or 180 mA.')

        _current_setting = self.read(CMD_CONFIG3)
        _current_setting = _current_setting & LED_CURRENT_MASK
        _current_setting = _current_setting | (_current_value << LED_CURRENT_POS)

        self.write(CMD_CONFIG3, _current_setting)

    def set_duty_cycle(self, duty_cycle):
        _current_value = PS_DUTY_40
        if duty_cycle == 40:
            _current_value = PS_DUTY_40
        elif duty_cycle == 80:
            _current_value = PS_DUTY_80
        elif duty_cycle == 160:
            _current_value = PS_DUTY_160
        elif duty_cycle == 320:
            _current_value = PS_DUTY_320
        else:
            raise ValueError('Duty cycle setting can only be 40, 80, 160, or 320. Herin is the duty cycle ratio 1/X.') 

        _current_setting = self.read(CMD_CONFIG1)
        _current_setting = _current_setting & PS_DUTY_MASK
        _current_setting = _current_setting | (_current_value << PS_DUTY_POS)

        self.write(CMD_CONFIG1, _current_setting)

    def set_integration_time(self, time):
        _current_value = PS_IT_1T0
        if time == 1:
            _current_value = PS_IT_1T0
        elif time == 1.5:
            _current_value = PS_IT_1T5
        elif time == 2:
            _current_value = PS_IT_2T0
        elif time == 2.5:
            _current_value = PS_IT_2T5
        elif time == 3:
            _current_value = PS_IT_3T0
        elif time == 3.5:
            _current_value = PS_IT_3T5
        elif time == 4:
            _current_value = PS_IT_4T0
        elif time == 8:
            _current_value = PS_IT_8T0
        else:
            raise ValueError('Integration time setting can only be 1T, 1.5T, 2T, 2.5T, 3T, 3.5T, 4T, or 8T. See application note p5.')

        _current_setting = self.read(CMD_CONFIG1)
        _current_setting = _current_setting & PS_IT_MASK
        _current_setting = _current_setting | (_current_value << PS_IT_POS)

        self.write(CMD_CONFIG1, _current_setting)

    def set_resolution(self, resolution):
        _current_value = 0
        if resolution == 12:
            _current_value = 0
        elif resolution == 16:
            _current_value = 1
        else:
            raise ValueError('Resolution setting can only be 12 or 16 bit.')

        _current_setting = self.read(CMD_CONFIG1)
        _current_setting = _current_setting & PS_RES_MASK
        _current_setting = _current_setting | (_current_value << PS_RES_POS)

        self.write(CMD_CONFIG1, _current_setting)

    def set_interrupt_mode(self, mode):
        _current_value = PS_INT_DISABLED
        if mode == "disabled":
            _current_value = PS_INT_DISABLED
        elif mode == "closing":
            _current_value = PS_INT_CLOSING
        elif mode == "away":
            _current_value = PS_INT_AWAY
        elif mode == "closing_and_away":
            _current_value = PS_INT_CLOSING_AWAY
        else:
            raise ValueError('Interrupt mode setting can only be "disabled", "closing", "away", or "closing_and_away".')

        _current_setting = self.read(CMD_CONFIG1)
        _current_setting = _current_setting & PS_INT_MASK
        _current_setting = _current_setting | (_current_value << PS_INT_POS)

        self.write(CMD_CONFIG1, _current_setting)

    def enable_interrupt_proximity_mode(self):
        _current_setting = self.read(CMD_CONFIG3)
        _current_setting = _current_setting & PS_INT_PROXIMITY_MODE_MASK
        _current_setting = _current_setting | PS_INT_PROXIMITY_MODE_VAL

        self.write(CMD_CONFIG3, _current_setting)

    def enable_interrupt_normal_mode(self):
        _current_setting = self.read(CMD_CONFIG3)
        _current_setting = _current_setting & PS_INT_NORMAL_MODE_MASK
        _current_setting = _current_setting | PS_INT_NORMAL_MODE_VAL

        self.write(CMD_CONFIG3, _current_setting)

    def set_persistence(self, persistence):
        _current_value = PS_PERS_1
        if persistence == 1:
            _current_value = PS_PERS_1
        elif persistence == 2:
            _current_value = PS_PERS_2
        elif persistence == 3:
            _current_value = PS_PERS_3
        elif persistence == 4:
            _current_value = PS_PERS_4
        else:
            raise ValueError('Persistence setting can only be 1, 2, 3, or 4.')

        _current_setting = self.read(CMD_CONFIG1)
        _current_setting = _current_setting & PS_PERS_MASK
        _current_setting = _current_setting | (_current_value << PS_PERS_POS)

        self.write(CMD_CONFIG1, _current_setting)

    def set_low_threshold(self, threshold):
        self.write(CMD_THRESHOLD_LOW, threshold)

    def set_high_threshold(self, threshold):
        self.write(CMD_THRESHOLD_HIGH, threshold)