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
import logger as log
import urllib3
from datetime import timedelta

onesec = timedelta(seconds=1)

def getAPI(configfile="config.yml"):
    # load config
    with open(configfile, 'r') as ymlfile:
        cfg = yaml.load(ymlfile, Loader=yaml.FullLoader)
    api_user = cfg.get("api_user",None)
    api_secret = cfg.get("api_secret",None)
    local_api = cfg.get("local_api",None)
    use_cloud = cfg.get("use_cloud_api",None)
    timezone = cfg.get("timezone",None)
    if use_cloud : 
        local_api = None
    
    # the logger
    logger = getLogger(configfile)

    # the API entry point
    api = eedomus.eeDomusAPI(api_user,api_secret,local_api,tz=timezone,logger=logger)

    #check connection
    if api.authTest()==1:
        logger.log(log.LOG_INFO,"Authentification OK")
    else:
        raise eedomus.eeError(None,1,"Authentification Error")
    return api

def getLogger(configfile="config.yml"):
    # names
    names = {
            "EMERGENCY": log.LOG_EMERG, 
            "ALERT": log.LOG_ALERT,
            "CRITICAL": log.LOG_CRIT,
            "ERROR": log.LOG_ERR,
            "WARNING": log.LOG_WARNING,
            "NOTICE": log.LOG_NOTICE,
            "INFO": log.LOG_INFO,
            "DEBUG": log.LOG_DEBUG
            }
    # load config
    with open(configfile, 'r') as ymlfile:
        cfg = yaml.load(ymlfile, Loader=yaml.FullLoader)
    console=cfg.get("consoleOutput",True)
    syslog =cfg.get("syslogOutput",False)
    threshold=names[cfg.get("logThreshold","INFO")]
    return log.logger(console,syslog,threshold)

def main():

    # handle options
    argParser = argparse.ArgumentParser(
            prog="migrate.py",
            description="migrates data from eedomus to influxdb v2",
            epilog="use at your own risk")
    argParser.add_argument("-c", "--config", help="config file", default="config.yml")
    argParser.add_argument("-d", "--dry", help="don't write to influxdb",action='store_true')
    argParser.add_argument("-a", "--all", help="Force migration of all data",action='store_true')
    args = argParser.parse_args()
    configfile = args.config
    dryrun = args.dry
    forceall = args.all

    # the logger
    logger = getLogger(configfile)

    # the eedomus API
    try:
        api = getAPI(configfile)
    except:
        logger.log(log.LOG_ERR,"Unable to connect to the eedomus API")
        return
    
    # get the list of devices
    devices = api.getPeriphList()
    
    # the Influxdb API
    try:
        influxdb = Influxdb(configfile,logger)
    except:
        logger.log(log.LOG_ERR,"Unable to connect to the influxdb API")
        return

    # loop on devices and migrate data to influxdb
    for device in devices:
        try: 
            start_date = influxdb.getLastEntry(device)+onesec if not forceall else None
        except urllib3.exceptions.NewConnectionError as e:
            logger.log(log.LOG_ERR,f"Unable to connect to the influxdb API: {e}")
            return
        if start_date is None:
            logger.log(log.LOG_INFO,f"Migrating {device.name}")
        else:
            logger.log(log.LOG_INFO,f"Migrating {device.name} from {start_date}")
        # load the history
        points = device.getHistory(start_date=start_date)
        # use the influxdb API
        if not dryrun:
            influxdb.writeInflux(influxdb.toInfluxData(device,points))
        else:
            data = influxdb.toInfluxData(device,points)
            logger.log(log.LOG_INFO,f"Dry run. Not saving {len(data)} data points.")
            if len(data):
                logger.log(log.LOG_DEBUG,str(data[0]))
        time.sleep(1)

if __name__ == "__main__":
        main()
