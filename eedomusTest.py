#!/bin/env python

from eedomus import eeDevice,findDevice,eeDomusAPI
from credentials import api_user,api_secret

api = eeDomusAPI(api_user,api_secret,"192.168.1.13")
devs = api.getPeriphList()
dev = findDevice(devs,room_name="Salon")[4]
print dev
print "Value:", dev.lastValue()

