#!/bin/env python

import MySQLdb as mdb
from datetime import datetime
from dateutil.relativedelta import relativedelta
from eedomus import eeDevice
		
class eeDbAPI:
	"""Main interface to the eeDomus API cloned db.
	"""
	def __init__(self, host='localhost', user='eedomus', password='eedomus', database='eedb'):
		self.con = mdb.connect(host, user, password, database, use_unicode=True)
		self.cur = self.con.cursor()
		self.cur.execute("SELECT VERSION()")
		ver = self.cur.fetchone()
		print(("Database version : %s " % ver))

	# Test authentification parameters:
	def authTest(self):
		# in case of auth issue, there is an exception in __init__
		return True

	# Get basic caracteristics from a user peripheral:
	def getCaracteristics(self,periph_id):
		self.cur.execute("SELECT measurement,timestamp FROM periph_history WHERE periph_id=%s ORDER BY id DESC LIMIT 1;",(periph_id,))
		(measurement,timestamp) = self.cur.fetchone()
		self.cur.execute("SELECT name FROM device WHERE periph_id=%s",(periph_id,))
		name = self.cur.fetchone()[0]
		caracs = { "name":name, "last_value":measurement, "last_value_change":timestamp }
		return caracs

	# Get periph list attached to your user account:
	def getPeriphList(self):
		self.cur.execute('select * from deviceview;')
		plist = []
		for (periph_id,parent_periph_id,name,room_id,room_name,usage_id,usage_name,creation_date) in self.cur:
			eedev = eeDevice(periph_id,parent_periph_id,name,room_id,room_name,usage_id,usage_name,creation_date)
			eedev.setAPI(self)
			plist.append(eedev)
		return plist

	#Get values history from a user peripheral:
	def getPeriphHistory(self,periph_id, start_date=None, end_date=None):
		start = (start_date if start_date is not None else (datetime.now()-relativedelta(years=1))).strftime("%Y-%m-%d %H:%M:%S")
		end   = (end_date if end_date is not None else datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
		self.cur.execute("SELECT measurement,timestamp FROM periph_history WHERE periph_id=%s AND timestamp between %s and %s ORDER BY timestamp DESC;",(periph_id,start,end))
		hist = []
		return self.cur.fetchall()

	#Set a value for a user peripheral. 
	def setPeriphValue(self,periph_id, value, value_date=None, mode="", update_only=False):
		raise NotImplementedError("cannot run setPeriphValue on the cloned local db")

	def setPeriphMacro(self,macro):
		raise NotImplementedError("cannot run setPeriphMacro on the cloned local db")
