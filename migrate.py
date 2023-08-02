#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jul 26 15:57:47 2023

@author: Christophe Delaere
"""

import eedomus
from influxdb import Influxdb
import yaml
import time
import argparse

def getAPI(configfile="config.yml"):
    # load config
    with open(configfile, 'r') as ymlfile:
        cfg = yaml.load(ymlfile, Loader=yaml.FullLoader)
    api_user = cfg["api_user"]
    api_secret = cfg["api_secret"]
    local_api = cfg["local_api"]
    use_cloud = cfg["use_cloud_api"]
    if use_cloud : 
        local_api = None
    
    # the API entry point
    api = eedomus.eeDomusAPI(api_user,api_secret,local_api)

    #check connection
    if api.authTest()==1:
        print("Authentification OK")
    else:
        raise eedomus.eeError(None,1,"Authentification Error")
    return api

def main():

    # handle options
    argParser = argparse.ArgumentParser(
            prog="migrate.py",
            description="migrates data from eedomus to influxdb v2",
            epilog="use at your own risk")
    argParser.add_argument("-c", "--config", help="config file", default="config.yml")
    argParser.add_argument("-d", "--dry", help="don't write to influxdb",action='store_true')
    args = argParser.parse_args()
    configfile = args.config
    dryrun = args.dry

    # the eedomus API
    api = getAPI(configfile)
    
    # get the list of devices
    devices = api.getPeriphList()
    
    # the Influxdb API
    influxdb = Influxdb(configfile)
    
    # loop on devices and migrate data to influxdb
    for device in devices:
        start_date = influxdb.getLastEntry(device)
        if start_date is None: 
            print(f"Migrating {device.name}")
        else:
            print(f"Migrating {device.name} from {start_date}")
        # load the history
        points = device.getHistory(start_date=start_date)
        # use the influxdb API
        if not dryrun:
            influxdb.writeInflux(influxdb.toInfluxData(device,points))
        else:
            data = influxdb.toInfluxData(device,points)
            print(f"Dry run. Not saving {len(data)} data points.")
            if len(data):
                print(data[0])
        time.sleep(1)

if __name__ == "__main__":
        main()
