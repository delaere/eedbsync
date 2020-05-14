#!/bin/env python

from eedomus import findDevice
from eedb import eeDbAPI

# the API entry point
api = eeDbAPI()

if api.authTest()==1:
	print("Authentification OK")
else:
	print("Authentification Error")

# get the list of devices
devs = api.getPeriphList()

# pick one for the next operations
dev = findDevice(devs,room_name="Salon")[4]

# print infos on that device
print(dev)

# get value and last change
print("Value:", dev.lastValue(), end=' ')
print(", last changed on", dev.lastValueChange())

# get the history and print some information
history = dev.getHistory()
print("History size: ", len(history))
print("First entry: ",history[0])
print("Last entry:", history[-1])


