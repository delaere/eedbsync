import io
import json
import urllib.request, urllib.parse, urllib.error
import warnings
from datetime import datetime
import time
import pytz

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
                        self.errCode = errFrame['error_code']
                        self.description = errFrame['error_msg']
        
        def __str__(self):
                return "Error %s: %s"%(str(self.errCode),str(self.description))

class eeDevice:
        """Class describing a typical device, as returned by the getPeriphList API method.
        
           The user experience is enriched by methods calling the API in the background, so that the 
           periphID doesn't have to be passed explicitely.
        """
        def __init__(self, periph_id,parent_periph_id,name,room_id,room_name,usage_id,usage_name,creation_date):
                self.periph_id = periph_id
                self.parent_periph_id = parent_periph_id if parent_periph_id != '' else 0
                self.name = name
                self.room_id = room_id
                self.room_name = room_name
                self.usage_id = usage_id
                self.usage_name = usage_name
                self.creation_date = creation_date

        def __str__(self):
                myString = "Device #%s (parent: device #%s)\n"%(self.periph_id,self.parent_periph_id)
                myString+= "Name: %s\n"%self.name
                myString+= "Room: %s (#%s)\n"%(self.room_name,self.room_id)
                myString+= "Usage: %s (#%s)\n"%(self.usage_name,self.usage_id)
                myString+= "Created on %s"%self.creation_date.strftime("%Y-%m-%d %H:%M:%S")
                return myString

        def __bytes__(self):
                    return str(self).encode('utf-8')

        def setAPI(self,api):
                self.api = api

        def lastValue(self):
                if not hasattr(self,"lastValue_"):
                        data = self.api.getCaracteristics(self.periph_id)
                        if data['name']!=self.name:
                                raise Exception('Name inconsistency: %s vs %s'%(data['name'],self.name))
                        self.lastValue_ = data["last_value"]
                        self.lastValueChange_ = data["last_value_change"]
                return self.lastValue_

        def lastValueChange(self):
                if not hasattr(self,"lastValueChange_"):
                        data = self.api.getCaracteristics(self.periph_id)
                        if data['name']!=self.name:
                                raise Exception('Name inconsistency: %s vs %s'%(data['name'],self.name))
                        self.lastValue_ = data["last_value"]
                        self.lastValueChange_ = data["last_value_change"]
                return self.lastValueChange_

        def setValue(self,value, value_date=None, mode="", update_only=False):
                if value_date is not None:
                        date_string = value_date.strftime("%Y-%m-%d %H:%M:%S")
                else :
                        date_string = None
                return self.api.setPeriphValue(self.periph_id, value, date_string, mode, update_only)

        def getHistory(self,start_date=None, end_date=None):
                return self.api.getPeriphHistory(self.periph_id,start_date,end_date)

        def refresh(self):
                del self.lastValue_
                del self.lastValueChange_
                
def eeDevice_decoder(obj, tz='Europe/Brussels'): # TODO: define TZ from yaml (through lambda) lambda obj: eeDevice_decoder(obj,self.tz)
        """Decoder to create a device from the json dict returned by the API"""
        # the time zone to be used for the creation of data points
        mytz = pytz.timezone(tz) if tz is not None else pytz.utc
        if 'last_value_change' in obj:
                return { 'name':obj['name'],
                         'last_value':obj['last_value'],
                         'last_value_change': mytz.localize(datetime.strptime(obj['last_value_change'],"%Y-%m-%d %H:%M:%S")) }
        elif "periph_id" in obj:
                return eeDevice(obj["periph_id"], obj["parent_periph_id"], obj["name"], obj["room_id"], 
                                obj["room_name"], obj["usage_id"], obj["usage_name"], mytz.localize(datetime.strptime(obj["creation_date"],"%Y-%m-%d %H:%M:%S")))
        elif 'history' in obj:
                result = []
                for item in obj['history']:
                        try:
                                timestamp = mytz.localize(datetime.strptime(item[1],"%Y-%m-%d %H:%M:%S"))
                        except ValueError as e:
                                warnings.warn("Warning: %s"%e,UserWarning)
                        else:
                                result += [ (item[0], timestamp ) ]
                return result
        return obj


def findDevice(thelist,periph_id=None,parent_periph_id=None,name=None,room_id=None,room_name=None,usage_id=None,usage_name=None,creation_date=None):
        """Utility to filter a list of devices"""
        devices = thelist[:]
        if periph_id is not None:
                devices = [item for item in devices if item.periph_id == periph_id]
        if parent_periph_id is not None:
                devices = [item for item in devices if item.parent_periph_id == parent_periph_id]
        if name is not None:
                devices = [item for item in devices if item.name == name]
        if room_id is not None:
                devices = [item for item in devices if item.room_id == room_id]
        if room_name is not None:
                devices = [item for item in devices if item.room_name == room_name]
        if usage_id is not None:
                devices = [item for item in devices if item.usage_id == usage_id]
        if usage_name is not None:
                devices = [item for item in devices if item.usage_name == usage_name]
        if creation_date is not None:
                devices = [item for item in devices if item.creation_date == creation_date]
        return devices

class eeDomusAPI:
        """Main interface to the eeDomus API.
           The API is created with the user and secret, and will use the local URL by default (except to get the history).
        """
        def __init__(self, api_user, api_secret, localIP=None, tz=None):
                self.api_user = api_user
                self.api_secret = api_secret
                self.localURLget = None if localIP is None else  "http://%s/api/get?"%localIP
                self.cloudURLget = "http://api.eedomus.com/get?"
                self.localURLset = None if localIP is None else  "http://%s/api/set?"%localIP
                self.cloudURLset = "http://api.eedomus.com/set?"

                if localIP is not None :
                        self.baseURLget = self.localURLget
                        self.baseURLset = self.localURLset
                else:
                        self.baseURLget = self.cloudURLget
                        self.baseURLset = self.cloudURLset 

                self.values   = { "api_user":api_user, "api_secret":api_secret}
                self.tz = tz
                self.eeDevice_decoder = lambda obj : eeDevice_decoder(obj,self.tz)

        # Test authentification parameters:
        def authTest(self):
                vals = self.values.copy()
                vals["action"]="auth.test"
                args = urllib.parse.urlencode(vals)
                u = urllib.request.urlopen(self.baseURLget+args)
                f = io.TextIOWrapper(u, encoding = "latin-1")
                data = json.load(f)
                #data = json.load(urllib.request.urlopen(self.baseURLget+args), encoding = "latin-1")
                return int(data['success'])

        # Get basic caracteristics from a user peripheral:
        def getCaracteristics(self,periph_id):
                vals = self.values.copy()
                vals["action"]="periph.caract"
                vals["periph_id"]=periph_id
                args = urllib.parse.urlencode(vals)
                u = urllib.request.urlopen(self.baseURLget+args)
                f = io.TextIOWrapper(u, encoding = "latin-1")
                data = json.load(f,object_hook=self.eeDevice_decoder)
                if int(data['success']):
                        return data['body']
                else:
                        raise eeError(data["body"])

        # Get periph list attached to your user account:
        def getPeriphList(self):
                vals = self.values.copy()
                vals["action"]="periph.list"
                args = urllib.parse.urlencode(vals)
                u = urllib.request.urlopen(self.baseURLget+args)
                f = io.TextIOWrapper(u, encoding = "latin-1")
                data = json.load(f,object_hook=self.eeDevice_decoder)
                if int(data['success']):
                        for device in data['body']:
                                device.setAPI(self)
                        return data['body']
                else:
                        raise eeError(data["body"])

        #Get values history from a user peripheral:
        def getPeriphHistory(self,periph_id, start_date=None, end_date=None, prepend=[]):
                vals = self.values.copy()
                vals["action"]="periph.history"
                vals["periph_id"]=periph_id
                if not start_date is None: vals["start_date"]=start_date.strftime("%Y-%m-%d %H:%M:%S")
                if not end_date is None: vals["end_date"]=end_date.strftime("%Y-%m-%d %H:%M:%S")
                print(f'{"None" if start_date is None else start_date.strftime("%Y-%m-%d %H:%M:%S")} - {"None" if end_date is None else end_date.strftime("%Y-%m-%d %H:%M:%S")}')
                args = urllib.parse.urlencode(vals)
                u = urllib.request.urlopen(self.cloudURLget+args)
                f = io.TextIOWrapper(u, encoding = "latin-1")
                data = json.load(f,object_hook=self.eeDevice_decoder)
                if not int(data['success']):
                    raise eeError(data["body"])
                if 'history_overflow' in data:
                    time.sleep(1)
                    return self.getPeriphHistory(periph_id,start_date=start_date,end_date=data['body'][-1][1],prepend=prepend+data['body'])
                else:
                    return prepend+data['body']

        #Set a value for a user peripheral. 
        #The peripheral could be a sensor (the value is stored in his history) or a actuator (the peripheral is asked to change for the new value)
        def setPeriphValue(self,periph_id, value, value_date=None, mode="", update_only=False):
                vals = self.values.copy()
                vals["action"]="periph.value"
                vals["periph_id"]=periph_id
                vals["value"]=value
                if not value_date is None: vals["value_date"]=value_date.strftime("%Y-%m-%d %H:%M:%S")
                if mode=="mobile": vals["mode"]="mobile"
                if update_only: vals["update_only"]=1
                args = urllib.parse.urlencode(vals)
                u = urllib.request.urlopen(self.baseURLget+args)
                f = io.TextIOWrapper(u, encoding = "latin-1")
                data = json.load(f)
                #data = json.load(urllib.request.urlopen(self.baseURLset+args), encoding = "latin-1")
                if int(data['success']):
                        return data['body']['result']
                else:
                        raise eeError(data["body"])

        #Activate a macro on a user peripheral.
        def setPeriphMacro(self,macro):
                vals = self.values.copy()
                vals["action"]="periph.macro"
                vals["macro"]=macro
                args = urllib.parse.urlencode(vals)
                u = urllib.request.urlopen(self.baseURLget+args)
                f = io.TextIOWrapper(u, encoding = "latin-1")
                data = json.load(f)
                #data = json.load(urllib.request.urlopen(self.baseURLset+args), encoding = "latin-1")
                if int(data['success']):
                        return data['body']['result']
                else:
                        raise eeError(data["body"])
