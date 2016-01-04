#!/bin/env python

import MySQLdb as mdb
import sys
import time
from datetime import datetime
from eedomus import eeError,eeDevice,findDevice,eeDomusAPI
from credentials import api_user,api_secret

def getAPI():
    # the API entry point
    api = eeDomusAPI(api_user,api_secret,"192.168.1.13")
    if api.authTest()==1:
        print "Authentification OK"
    else:
	raise eeError(None,1,"Authentification Error")
    return api

#TODO: all these methods would fit in a class.
#this would simplify the interface (no need to expose the connection & cursor)
#and would allow to combine some steps naturally

def getDbCursor():
    # host, user, password, db
    con = mdb.connect('localhost', 'eedomus', 'eedomus', 'eedb');
    cur = con.cursor()
    cur.execute("SELECT VERSION()")
    ver = cur.fetchone()
    print "Database version : %s " % ver
    return (con,cur)

def getLastSync(cursor):
    cursor.execute("SELECT MAX(job_id) as MaximumID FROM syncjobs;")
    maximumID = cursor.fetchone()
    if maximumID[0] is None:
	# first sync
	return None
    else:
	cursor.execute("SELECT execution_date FROM syncjobs where job_id = %s;",maximumID)
	execution_date = cursor.fetchone()
	return execution_date[0]
	 
def hasUsage(cursor,usage_id):
	cursor.execute("SELECT COUNT(*) AS CNT FROM devusage WHERE usage_id = %s;",(usage_id,))
	return cursor.fetchone()[0]==1

def hasRoom(cursor,room_id):
	cursor.execute("SELECT COUNT(*) AS CNT FROM room WHERE room_id = %s;",(room_id,))
	return cursor.fetchone()[0]==1

def hasDevice(cursor,device):
	cursor.execute("SELECT COUNT(*) AS CNT FROM device WHERE periph_id = %s;",(device.periph_id,))
	return cursor.fetchone()[0]==1

def addUsage(cursor,usage_id,usage_name):
	print "add",usage_id,usage_name
	cursor.execute("INSERT INTO devusage (usage_id,usage_name) VALUES(%s,%s)",(usage_id,usage_name))

def addRoom(cursor,room_id,room_name):
	print "add",room_id,room_name
	cursor.execute("INSERT INTO room (room_id,room_name) VALUES(%s,%s)",(room_id,room_name))

def addDevice(cursor,device):
	print "add",device.periph_id,device.name
	values = (device.periph_id,device.parent_periph_id,device.name,device.room_id,device.usage_id,device.creation_date.strftime("%Y-%m-%d %H:%M:%S"))
	cursor.execute("INSERT INTO device(periph_id,parent_periph_id,name,room_id,usage_id,creation_date) VALUES(%s,%s,%s,%s,%s,%s)", values)

def insertHistory(cursor,dev,history):
	print "Inserting", len(history), "values for", dev.name
	for measurement in history:
		add_measurement = ("INSERT INTO periph_history "
		                   "(periph_id,measurement,timestamp) "
	                           "VALUES (%s,%s,%s)")
		data = (dev.periph_id,measurement[0],measurement[1].strftime("%Y-%m-%d %H:%M:%S"))
		cursor.execute(add_measurement, data)

def registerSync(cursor,time):
	cursor.execute("INSERT INTO syncjobs (execution_date) VALUES (\'%s\')"%time.strftime("%Y-%m-%d %H:%M:%S"))

def doSync():
	# first fill the device table
	api = getAPI()
	devices = api.getPeriphList()
	(con,cursor) = getDbCursor()
	lastSync = getLastSync(cursor)
	newDevices = []
	for dev in devices:
		if not hasUsage(cursor,dev.usage_id): addUsage(cursor,dev.usage_id, dev.usage_name)
		if not hasRoom(cursor,dev.room_id): addRoom(cursor,dev.room_id,dev.room_name)
		if not hasDevice(cursor,dev): 
			addDevice(cursor,dev)
			newDevices.append(dev.periph_id)
	
	# now, run on devices and update history
	# we set the end to be sure that it is the same for all devices
	end_date = datetime.now()
	begin_date = lastSync
	print "Syncing from %s to %s."%(begin_date.strftime("%Y-%m-%d %H:%M:%S"),end_date.strftime("%Y-%m-%d %H:%M:%S"))
	for dev in devices:
		time.sleep(1)
		print "Downloading history for", dev.name
		history = dev.getHistory(None,end_date) if dev.periph_id in newDevices else dev.getHistory(begin_date,end_date)
		insertHistory(cursor, dev, history)
	
	# register the sync operation
	registerSync(cursor, end_date)

	# commit and close
	con.commit()
	con.close()

if __name__ == "__main__":
	doSync()
