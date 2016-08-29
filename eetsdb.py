import socket
import string
import unicodedata as ud
import sys
from unidecode import unidecode
from datetime import datetime
from itertools import tee, izip

from opentsdbclient.client import RESTOpenTSDBClient as OpenTSDBClient
from opentsdbclient.opentsdberrors import OpenTSDBError
from opentsdbclient.opentsdbobjects import OpenTSDBTimeSeries, OpenTSDBMeasurement
from opentsdbclient.opentsdbquery import OpenTSDBtsuidSubQuery, OpenTSDBQuery

from recipes import cureValues

#TODO: put units in metadata

# this dictionnary maps eeDevices to openTSDB metrics
#TODO: this could be in a json file.
eetsdbMapping = {
    258506 : "memory.free",
    258507 : "disk.free",
    258508 : "communication.errors",
    268580 : "state",
    350073 : "state",
    268177 : "temperature",
    268223 : "temperature",
    268224 : "humidity",
    271760 : "wind.speed",
    271761 : "rainfall",
    271762 : "visibility",
    271766 : "pressure",
    271992 : "index",
    268234 : "state",
    268237 : "state",
    268238 : "temperature",
    342898 : "state",
    342899 : "temperature",
    343296 : "state",
    343297 : "temperature",
    268218 : "temperature",
    268219 : "CO2",
    268220 : "humidity",
    268221 : "pressure",
    268222 : "noise.level",
    268267 : "noise.level",
    268359 : "light",
    268360 : "appliance",
    268361 : "appliance",
    268362 : "appliance",
    268363 : "appliance",
    268364 : "appliance",
    268365 : "power.consumption",
    268366 : "power.consumption",
    268367 : "power.consumption",
    268368 : "power.consumption",
    268369 : "power.consumption",
    268370 : "power.consumption",
    325388 : "light",
    325389 : "power.consumption",
    348904 : "light",
    271741 : "appliance",
    271742 : "power.consumption",
    271747 : "movement",
    271748 : "temperature",
    271749 : "luminosity",
    271773 : "state",
    273229 : "state",
    349023 : "appliance",
    349024 : "power.consumption",
    345835 : "power.consumption",
    349001 : "gas.consumption",
        }

#TODO: this could be in a json file.
#When working with time series, it is actually recommended to rather submit data as the integral (i.e. a monotinically increasing counter).
#OpenTSDB can then "differentiate" this using the rate function.
eedbintegration = {
    258506 : (False,0,0),
    258507 : (False,0,0),
    258508 : (True,1,1), # communication errors
    268580 : (False,0,0),
    350073 : (False,0,0),
    268177 : (False,0,0),
    268223 : (False,0,0),
    268224 : (False,0,0),
    271760 : (False,0,0),
    271761 : (False,0,0),
    271762 : (False,0,0),
    271766 : (False,0,0),
    271992 : (False,0,0),
    268234 : (False,0,0),
    268237 : (False,0,0),
    268238 : (False,0,0),
    342898 : (False,0,0),
    342899 : (False,0,0),
    343296 : (False,0,0),
    343297 : (False,0,0),
    268218 : (False,0,0),
    268219 : (False,0,0),
    268220 : (False,0,0),
    268221 : (False,0,0),
    268222 : (False,0,0),
    268267 : (False,0,0),
    268359 : (False,0,0),
    268360 : (False,0,0),
    268361 : (False,0,0),
    268362 : (False,0,0),
    268363 : (False,0,0),
    268364 : (False,0,0),
    268365 : (True,None,3600000.), #(watt*s -> kWh)
    268366 : (True,None,3600000.), #(watt*s -> kWh)
    268367 : (True,None,3600000.), #(watt*s -> kWh)
    268368 : (True,None,3600000.), #(watt*s -> kWh)
    268369 : (True,None,3600000.), #(watt*s -> kWh)
    268370 : (True,None,3600000.), #(watt*s -> kWh)
    325388 : (False,0,0),
    325389 : (True,None,3600000.), #(watt*s -> kWh)
    348904 : (False,0,0),
    271741 : (False,0,0),
    271742 : (True,None,3600000.), #(watt*s -> kWh)
    271747 : (False,0,0),
    271748 : (False,0,0),
    271749 : (False,0,0),
    271773 : (False,0,0),
    273229 : (False,0,0),
    349023 : (False,0,0),
    349024 : (True,None,3600000.), #(watt*s -> kWh)
    345835 : (True,None,3600000.), #(watt*s -> kWh)
    349001 : (True,900,3600.) #(m3 -> /h*s -> m3)  WILL NEED A TIME-DEPENDENT FIX, MOST PROBABLY (AD HOC) 3600000 for early values
	}

#TODO: this could be in a json file.
eetsdbvalues = {
        "off": 0,
        "desactivee": 0,
        "ok": 0,
        "ferme": 0,
        "aucun mouvement": 0,
        "non joignable": 0,
        "--": 0,
	"intimite":0,
        "on": 1,
	"activee": 1,
	"alarme": 1,
	"ouvert": 1,
	"detection mouvement": 1,
	"mouvement": 1,
	"joignable": 1,
	"normal": 1,
        "alerte": 2,
	"vibration": 2
	}

eetsdbrecipes = {
        349001 : "fix_gazreading"
        }

def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return izip(a, b)

class eeTSDB:
    """Simple utility to migrate the history from eedb to eetsdb"""

    def __init__(self,host,port):
        self.host_ = host
        self.port_ = port
        self.client_ = OpenTSDBClient(self.host_, self.port_)

    def migrate(self,device,start_date=None, end_date=None, history = None, lastValue=None): 
        """Main method: give device and time range to migrate to openTSDB"""
        self.debugId = device.periph_id
        timeseries = self.mkTimeseries(device)
        self.registerTS(timeseries)
        timeseries.loadFrom(self.client_)
        if history is None:
            history = device.getHistory(start_date, end_date)
        measurements = self.mkMeasurements(timeseries,history)
        self.insertHistory(measurements)
        self.addAnnotation(timeseries)

    def registerTS(self, timeseries):
        try:
            res = self.client_.search("LOOKUP",metric=timeseries.metric, tags=timeseries.tags)
        except OpenTSDBError:
            timeseries.assign_uid(self.client_)

    def insertHistory(self, measurements):
        return self.client_.put_measurements(measurements, summary=True, compress=True)

    def mkTimeseries(self,device):
        metric = eetsdbMapping[int(device.periph_id)]
        tags = { "periph_id":str(device.periph_id), 
                 "room":self.cureString(device.room_name),
                 "name":self.cureString(device.name)}
        return OpenTSDBTimeSeries(metric,tags)

    def mkMeasurements(self,timeseries,history):
        # history is a vector of pairs (measurement,timestamp)
        history = self.cureValues(timeseries,history)
        try:
            if eedbintegration[int(timeseries.tags["periph_id"])][0]:
                conversionFactor=eedbintegration[int(timeseries.tags["periph_id"])][2]
                samplingPeriod=eedbintegration[int(timeseries.tags["periph_id"])][1]
                last= self.getLastValue(timeseries)
                return [OpenTSDBMeasurement(timeseries, int(timestamp.strftime("%s")),value) for (value,timestamp) in self.cummulative(history, conversionFactor, samplingPeriod, last)]
            else:
                return [OpenTSDBMeasurement(timeseries, int(timestamp.strftime("%s")),value) for (value,timestamp) in history]
        except :
            print("Unable to create valid measurements.")
            print sys.exc_info()[0]
            return []

    def addAnnotation(self,timeseries, isGlobal=False):
        timeseries.loadFrom(self.client_)
        tsuid = timeseries.metadata.tsuid
        description = "Migrated from eedb"
        custom={"host":socket.gethostname()}
        self.client_.set_annotation(int(datetime.now().strftime("%s")), tsuid=tsuid, description=description, custom=custom)

    def cureString(self,thestring):
	asciichars = string.ascii_letters + "0123456789-_./"
        return ''.join([c for c in thestring.replace(" ","_").replace("[","_").replace("]","_") if c in asciichars or ud.category(unicode(c)) in ['Ll', 'Lu']])

    def cureValues(self,timeseries,history):
        recipeName = eetsdbrecipes.get(int(timeseries.tags["periph_id"]), None)
        recipe = getattr(cureValues, recipeName) if recipeName is not None else lambda x:x
        return [(recipe(self.translateValue(value)),timestamp) for (value,timestamp) in history]

    def translateValue(self,value):
	if unidecode(value).lower() in eetsdbvalues: return eetsdbvalues[unidecode(value).lower()]
        try:
            return float(''.join([c for c in value if c in "-0123456789."]))
        except:
            print value,"cannot be translated"
            return 0

    def cummulative(self,inputHistory, conversionFactor = 3600000., samplingPeriod = None, last = None, integrationMode="trapeze"):
    	""" Integrates the input to return a cummulative distribution.
    	    By default, it uses the trapeze integration rule.
    	    If samplingPeriod is set, each point is taken independently over that time.
    	    The default conversion factor works for both electricity (watt*s -> kWh) and gaz (dm3/h*s -> m3)
    	"""
        data = sorted(inputHistory, key=lambda entry:entry[1])
        output = []
    	for i,((ud0,t0),(ud1,t1)) in enumerate(pairwise(data)):
                d0 = self.translateValue(ud0)
                d1 = self.translateValue(ud1)
    		if last is None:
    			last = 0
                        output.append((0,t0))
    		if samplingPeriod is None:
                        if integrationMode=="trapeze":
        			last += (((d0+d1)/2.)*(t1-t0).total_seconds())/conversionFactor # good approximation for continuous functions
                        else:
                                last += d0*(t1-t0).total_seconds()/conversionFactor # best when the series "updates on changes"
    		else:
    			last += d0*samplingPeriod/conversionFactor # when measurements are defined on a fixed interval and are not continuous
                output.append((last,t1))
    	return output

    def getLastValue(self,timeseries):
        # issue with query last, so do it by hand with some large backsearch. Heavy...
        sq = OpenTSDBtsuidSubQuery("sum",[timeseries.metadata.tsuid])
        query = OpenTSDBQuery([sq],"1y-ago")
        answer = self.client_.query(query)
        if len(answer)>0:
            if len(answer[0]["dps"].keys()) >0:
                last = max([ int(k) for k in answer[0]["dps"].keys()  ])
                return answer[0]["dps"][str(last)]
            else:
                print answer
        else:
            return None

