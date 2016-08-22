#!/bin/env python

import MySQLdb as mdb
import sys
import time
from datetime import datetime
from eedomus import eeError,eeDevice,findDevice,eeDomusAPI
from eetsdb import eeTSDB,eetsdbMapping
from credentials import api_user,api_secret

def getAPI():
    # the API entry point
    #api = eeDomusAPI(api_user,api_secret,"192.168.1.13")
    api = eeDomusAPI(api_user,api_secret)
    if api.authTest()==1:
        print "Authentification OK"
    else:
	raise eeError(None,1,"Authentification Error")
    return api

class eeLocalDb:
	def __init__(self, host='localhost', user='eedomus', password='eedomus', database='eedb'):
	    self.con = mdb.connect(host, user, password, database)
	    self.cur = self.con.cursor()
	    self.cur.execute("SELECT VERSION()")
	    ver = self.cur.fetchone()
	    print "Database version : %s " % ver

	def getDbCursor(self):
	    return self.cur

	def getLastSync(self):
	    self.cur.execute("SELECT MAX(job_id) as MaximumID FROM syncjobs;")
	    maximumID = self.cur.fetchone()
	    if maximumID[0] is None:
		# first sync
		return None
	    else:
		self.cur.execute("SELECT execution_date FROM syncjobs where job_id = %s;",maximumID)
		execution_date = self.cur.fetchone()
		return execution_date[0]
	 
	def hasUsage(self,usage_id):
		self.cur.execute("SELECT COUNT(*) AS CNT FROM devusage WHERE usage_id = %s;",(usage_id,))
		return self.cur.fetchone()[0]==1

	def hasRoom(self,room_id):
		self.cur.execute("SELECT COUNT(*) AS CNT FROM room WHERE room_id = %s;",(room_id,))
		return self.cur.fetchone()[0]==1

	def hasDevice(self,device):
		self.cur.execute("SELECT COUNT(*) AS CNT FROM device WHERE periph_id = %s;",(device.periph_id,))
		return self.cur.fetchone()[0]==1

	def addUsage(self,usage_id,usage_name):
		print "add",usage_id,usage_name
		self.cur.execute("INSERT INTO devusage (usage_id,usage_name) VALUES(%s,%s)",(usage_id,usage_name))

	def addRoom(self,room_id,room_name):
		print "add",room_id,room_name
		self.cur.execute("INSERT INTO room (room_id,room_name) VALUES(%s,%s)",(room_id,room_name))

	def addDevice(self,device):
		print "add",device.periph_id,device.name
		values = (device.periph_id,device.parent_periph_id,device.name,device.room_id,device.usage_id,device.creation_date.strftime("%Y-%m-%d %H:%M:%S"))
                if str(values[1]) is '': # avoids a Warning: Incorrect integer value: '' for column 'parent_periph_id' at row 1"
                    values = (device.periph_id,0,device.name,device.room_id,device.usage_id,device.creation_date.strftime("%Y-%m-%d %H:%M:%S"))
		self.cur.execute("INSERT INTO device(periph_id,parent_periph_id,name,room_id,usage_id,creation_date) VALUES(%s,%s,%s,%s,%s,%s)", values)

	def insertHistory(self,dev,history):
		print "Inserting", len(history), "values for", dev.name
		for measurement in history:
			add_measurement = ("INSERT INTO periph_history "
			                   "(periph_id,measurement,timestamp) "
		                           "VALUES (%s,%s,%s)")
			data = (dev.periph_id,measurement[0],measurement[1].strftime("%Y-%m-%d %H:%M:%S"))
			self.cur.execute(add_measurement, data)

	def registerSync(self,time):
		self.cur.execute("INSERT INTO syncjobs (execution_date) VALUES (\'%s\')"%time.strftime("%Y-%m-%d %H:%M:%S"))

	def commitAndClose(self):
		self.con.commit()
		self.con.close()

def isInTSDB(dev):
    # check that the metric is in eetsdbMapping
    return dev.periph_id in eetsdbMapping

def doSync():
	# first fill the device table
	api = getAPI()
	devices = api.getPeriphList()
	localDb = eeLocalDb('localhost','eedomus','eedomus','eedb')
        eetsdb  = eeTSDB('localhost',4242)
	lastSync = localDb.getLastSync()
	newDevices = []
	for dev in devices:
		if not localDb.hasUsage(dev.usage_id): localDb.addUsage(dev.usage_id, dev.usage_name)
		if not localDb.hasRoom(dev.room_id): localDb.addRoom(dev.room_id,dev.room_name)
		if not localDb.hasDevice(dev):
			localDb.addDevice(dev)
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
		localDb.insertHistory(dev, history)
                #TODO: check this: seems that migrate is not called...
                if isInTSDB(dev):
                    eetsdb.migrate(device=dev,history=history)
	
	# register the sync operation
	localDb.registerSync(end_date)

	# commit and close
	localDb.commitAndClose()

if __name__ == "__main__":
	doSync()
