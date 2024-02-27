import os
import sys
import subprocess
import time

class Statistics:
    def __init__(self):
        self.commands = {
            "ip": "hostname -I | cut -d' ' -f1",
            "hostname": "cat /etc/hostname",
            "cpu": "cut -f 1 -d \" \" /proc/loadavg",
            "ram": "free -m | awk 'NR==2{printf \"%s\", $3}'",
            "ram_max": "free -m | awk 'NR==2{printf \"%s\", $2}'",
            "disk": "df -h | awk '$NF==\"/\"{printf \"%d\", $3}'",
            "disk_max": "df -h | awk '$NF==\"/\"{printf \"%d\", $2}'",
            "temperature": "vcgencmd measure_temp" 
        }

        self.values = {}
        self.last_update = 0

        self.update()

        
    def update(self):
        if time.time() - self.last_update >= 10:
            for key, command in self.commands.items():
                self.values[key] = subprocess.check_output(command, shell=True).decode("utf-8")

            if "temperature" in self.values:
                self.values["temperature"] = self.values["temperature"].replace("temp=","").replace("'C","").strip()

            for key, value in self.values.items():
                try:
                    self.values[key] = float(self.values[key])
                except ValueError:
                    self.values[key] = self.values[key].strip()
                    
            self.last_update = time.time()

    def get(self, key):
        self.update()
        if key in self.values:
            return self.values[key]
        else:
            return None

