#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A file for logging from Phidget 5105-2 to csv
"""

__author__ = "Dave Lindley"


from Phidget22.Devices.TemperatureSensor import *
import time
from datetime import datetime
import csv
from Phidget22Python.send_twilio import send_twilio


log_file = "phidget_log.csv"


def ms_since_epoch():
    """
    This is used to calculate seconds in ms since 1.1.1970, which is the way HighCharts expects to recieve datetime.
    :return: Milliseconds since January 1, 1970.
    """
    return int((datetime.utcnow() - datetime(1970, 1, 1)).total_seconds() * 1000)


def onAttachHandler(self):
    """
    This needs to be done as a 'monkey patched' event handler - not sure why.
    this gets passed into the Phidget class, and is treated as Phidget.onAttachHandler at runtime.
    Some settings can be changed here
    """
    self.setDataInterval(30000)
    self.setTemperatureChangeTrigger(0.0)


def calculate_doneness(readings_per_minute=2):
    """
    For calculating the "chews" of a cook
    :param readings_per_minute: should be 60000/self.setDataInterval
    :return:
    """
    with open(log_file, 'r') as f:
        time_temp_list = [tuple(line) for line in csv.reader(f)]

    total_doneness = 0
    for record in time_temp_list:
        total_doneness += (
            0.00000000000000007048 * ((float(record[0])*9/5 + 32) ** 7.29007299056)
        ) / readings_per_minute

    return total_doneness, time_temp_list



def log_to_csv(self, temperature):
    """
    This function is used as a mixin for the Phidget class - i.e. it will be used inside that class at runtime.
    :param self: parent object
    :param temperature: temp float which gets passed in by parent
    :return:
    """
    # temperature = temperature * 9 / 5 + 32
    time = ms_since_epoch()

    print(f"temperature {time}---> {temperature}")

    with open(log_file, "a+") as output_file:
        writer = csv.writer(output_file)
        writer.writerow([temperature, time])

    doneness, time_temp_list = calculate_doneness()
    print(f'doneness is {doneness}')

    # to send a text every 10 minutes.
    if len(time_temp_list)%20 == 0:
        # maybe put some twilio logic here
        try:
            send_twilio(doneness)
        except Exception as e:
            print(e)


def configure_phidget(serial=542_616, hub=0, channel=0):
    """
    :param serial: Serial Number as int
    :param hub: Is this connected to a hub? 1:Yes, 0:No
    :param channel: Channel 0 is Thermocouple. 1 is Board.
    :return: configured phidget
    """
    ch = TemperatureSensor()
    ch.setDeviceSerialNumber(serial)
    ch.setHubPort(hub)
    ch.setChannel(channel)
    ch.setOnAttachHandler(onAttachHandler)
    return ch


if __name__ == "__main__":
    BrisklessPhidget = configure_phidget()

    # set the log to firebase mixin to run on every temp change
    BrisklessPhidget.setOnTemperatureChangeHandler(log_to_csv)
    print("logging added")
    # launch temperature reading from Phidget
    BrisklessPhidget.openWaitForAttachment(10000)

    while True:
        time.sleep(10)