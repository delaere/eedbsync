#!/bin/env python

import MySQLdb as mdb
import sys
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
	return datetime.strptime(execution_date[0],"%Y-%m-%d %H:%M:%S")
	 
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
	# TODO: create a value table
	# I see two options: one big table, or one table per device (dynamically created)
	# the second option allows to have the proper type for the values. But is it needed? 
	# how do we retrieve the value type automatically?
	#   -> can try to convert to a float
	#   -> if it works, checks for a . in the string to decide between int and float
	#   -> create a table whose name is periph_id_history with 3 fields: id (autoincr), value(int/float/unicode),  datetime(unique)

def insertHistory(cursor,dev,history):
	pass
	# check that the table exists
	# loop on history and insert 

def registerSync(cursor,time):
	pass

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
	for dev in devices:
		history = dev.getHistory(None,end_date) if dev.periph_id in newDevices else dev.getHistory(begin_date,end_date)
		insertHistory(cursor, dev, history)
	
	# register the sync operation
	registerSync(cursor, end_date)

	# commit and close
	con.commit()
	con.close()

