#!/bin/env python

import json
import urllib
import urllib2
import warnings

# eeDomus Python API. From http://doc.eedomus.com/en/index.php/API_eedomus

class eeError(Exception):
	"""Exception raised for API errors
	   
	   Attributes:
	   	errFrame: full frame from the API
	   	errCode: Error code
		errMsg: description of the error

	   Documentation:
	   	http://doc.eedomus.com/en/index.php/API_eedomus#Error_codes
	
	"""
	def __init__(self,errFrame, errCode=None, errMsg=None):
		if errFrame is None:
			self.errCode = errCode
			self.description = errMsg
		else:
			self.errCode = errFrame[u'error_code']
			self.description = errFrame[u'error_msg']
	
	def __str__(self):
		return "Error %s: %s"%(str(self.errCode),str(self.description))

class eeDevice:
	"""Class describing a typical device, as returned by the getPeriphList API method.
	
	   The user experience is enriched by methods calling the API in the background, so that the 
	   periphID doesn't have to be passed explicitely.
	"""
	def __init__(self, periph_id,parent_periph_id,name,room_id,room_name,usage_id,usage_name,creation_date):
		self.periph_id = periph_id
		self.parent_periph_id = parent_periph_id
		self.name = name
		self.room_id = room_id
		self.room_name = room_name
		self.usage_id = usage_id
		self.usage_name = usage_name
		self.creation_date = creation_date

	def __unicode__(self):
		myString = "Device #%s (parent: device #%s)\n"%(self.periph_id,self.parent_periph_id)
		myString+= "Name: %s\n"%self.name
		myString+= "Room: %s (#%s)\n"%(self.room_name,self.room_id)
		myString+= "Usage: %s (#%s)\n"%(self.usage_name,self.usage_id)
		myString+= "Created on %s"%self.creation_date
		return myString

	def __str__(self):
		    return unicode(self).encode('utf-8')

	def setAPI(self,api):
		self.api = api

	def lastValue(self):
		if not hasattr(self,"lastValue_"):
			data = self.api.getCaracteristics(self.periph_id)
			self.lastValue_ = data[u"last_value"]
			self.lastValueChange_ = data[u"last_value_change"]
		return self.lastValue_

	def lastValueChange(self):
		if not hasattr(self,"lastValueChange_"):
			data = self.api.getCaracteristics(self.periph_id)
			self.lastValue_ = data[u"last_value"]
			self.lastValueChange_ = data[u"last_value_change"]
		return self.lastValueChange_

	def setValue(self,value, value_date=None, mode="", update_only=False):
		return self.api.setPeriphValue(self.periph_id, value, value_date, mode, update_only)

	def refresh(self):
		del self.lastValue_
		del self.lastValueChange_
		
def eeDevice_decoder(obj):
	"""Decoder to create a device from the json dict returned by the API"""
	if u"periph_id" in obj:
		return eeDevice(obj[u"periph_id"], obj[u"parent_periph_id"], obj[u"name"], obj[u"room_id"], 
				obj[u"room_name"], obj[u"usage_id"], obj[u"usage_name"], obj[u"creation_date"])
	return obj

def findDevice(thelist,periph_id=None,parent_periph_id=None,name=None,room_id=None,room_name=None,usage_id=None,usage_name=None,creation_date=None):
	"""Utility to filter a list of devices"""
	devices = thelist[:]
	if periph_id is not None:
		devices = filter(lambda item: item.periph_id == periph_id, devices)
	if parent_periph_id is not None:
		devices = filter(lambda item: item.parent_periph_id == parent_periph_id, devices)
	if name is not None:
		devices = filter(lambda item: item.name == name, devices)
	if room_id is not None:
		devices = filter(lambda item: item.room_id == room_id, devices)
	if room_name is not None:
		devices = filter(lambda item: item.room_name == room_name, devices)
	if usage_id is not None:
		devices = filter(lambda item: item.usage_id == usage_id, devices)
	if usage_name is not None:
		devices = filter(lambda item: item.usage_name == usage_name, devices)
	if creation_date is not None:
		devices = filter(lambda item: item.creation_date == creation_date, devices)
	return devices

class eeDomusAPI:
	"""Main interface to the eeDomus API.
	   I is created with the user and secret, and will use the local URL by default (except to get the history).
	"""
	def __init__(self, api_user, api_secret, local=True):
		self.api_user = api_user
		self.api_secret = api_secret
		#TODO: local URL should be an option
		self.localURLget = "http://192.168.1.13/api/get?"
		self.cloudURLget = "http://api.eedomus.com/get?"
		self.localURLset = "http://192.168.1.13/api/set?"
		self.cloudURLset = "http://api.eedomus.com/set?"

		if local is True:
			self.baseURLget = self.localURLget
			self.baseURLset = self.localURLset
		else:
			self.baseURLget = self.cloudURLget
			self.baseURLset = self.cloudURLset 

		self.values   = { "api_user":api_user, "api_secret":api_secret}

	# Test authentification parameters:
	def authTest(self):
		vals = self.values.copy()
		vals["action"]="auth.test"
		args = urllib.urlencode(vals)
		data = json.load(urllib2.urlopen(self.baseURLget+args), encoding = "latin-1")
		if int(data[u'success']):
			return data[u'body']
		else:
			raise eeError(data[u"body"])

	# Get basic caracteristics from a user peripheral:
	def getCaracteristics(self,periph_id):
		vals = self.values.copy()
		vals["action"]="periph.caract"
		vals["periph_id"]=periph_id
		args = urllib.urlencode(vals)
		data = json.load(urllib2.urlopen(self.baseURLget+args), encoding = "latin-1")
		if int(data[u'success']):
			return data[u'body']
		else:
			raise eeError(data[u"body"])

	# Get periph list attached to your user account:
	def getPeriphList(self):
		vals = self.values.copy()
		vals["action"]="periph.list"
		args = urllib.urlencode(vals)
		data = json.load(urllib2.urlopen(self.baseURLget+args), encoding = "latin-1", object_hook=eeDevice_decoder)
		if int(data[u'success']):
			for device in data[u'body']:
				device.setAPI(self)
			return data[u'body']
		else:
			raise eeError(data[u"body"])

	#Get values history from a user peripheral:
	def getPeriphHistory(self,periph_id, start_date=None, end_date=None):
		vals = self.values.copy()
		vals["action"]="periph.history"
		vals["periph_id"]=periph_id
		if not start_date is None: vals["start_date"]=start_date
		if not end_date is None: vals["end_date"]=end_date
		args = urllib.urlencode(vals)
		data = json.load(urllib2.urlopen(self.cloudURLget+args), encoding = "latin-1")
		if int(data[u'success']):
			if u'history_overflow' in data:
				#TODO: in that case, split and restart (recursively)
				warnings.warn("Warning. Overflow: History is limited to 10K",UserWarning)
			else:
				return data[u'body'][u'history']
		else:
			raise eeError(data[u"body"])

	#Set a value for a user peripheral. 
	#The peripheral could be a sensor (the value is stored in his history) or a actuator (the peripheral is asked to change for the new value)
	def setPeriphValue(self,periph_id, value, value_date=None, mode="", update_only=False):
		vals = self.values.copy()
		vals["action"]="periph.value"
		vals["periph_id"]=periph_id
		vals["value"]=value
		if not value_date is None: vals["value_date"]=value_date
		if mode=="mobile": vals["mode"]="mobile"
		if update_only: vals["update_only"]=1
		args = urllib.urlencode(vals)
		data = json.load(urllib2.urlopen(self.baseURLset+args), encoding = "latin-1")
		if int(data[u'success']):
			return data[u'body'][u'result']
		else:
			raise eeError(data[u"body"])

	#Activate a macro on a user peripheral.
	def setPeriphMacro(self,macro):
		vals = self.values.copy()
		vals["action"]="periph.macro"
		vals["macro"]=macro
		args = urllib.urlencode(vals)
		data = json.load(urllib2.urlopen(self.baseURLset+args), encoding = "latin-1")
		if int(data[u'success']):
			return data[u'body'][u'result']
		else:
			raise eeError(data[u"body"])

#TODO script d'importation de la db
# - get list of periphs -> devices, rooms, usages, (macros???)
# - load history if not in db (from beginning of time till last downloas)
# - for all devices, refresh by loading the history

# then, the webserver will run and access the db via a php script returning data in json format.
# we should also consider the possibility to attack the db with ROOT

# the initial idea of the webserver is to present a selection of graphs. 
# in a second stage, I will see how to be more generic
