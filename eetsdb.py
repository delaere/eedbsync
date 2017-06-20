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

#TODO: find a way to "chain" time series
# this is: when a device replaces another, in the integration mode, one should "take the last value and continue". Sometimes, a scale factor has to be applied.
# alternatively, one could have "virtual periph_ids", or a way to say: that periph_id is to be translated as the old one. The recipe for scale factors could be in the existing fix_measurement mechanism.
# we could generalize the tracking of changes in the TS name... or not.

# options
import yaml
with open("config.yml", 'r') as ymlfile:
    cfg = yaml.load(ymlfile)

eetsdbMapping = cfg["eetsdbMapping"] #this dictionnary maps eeDevices to openTSDB metrics
eedbintegration = cfg["eedbintegration"] # When working with time series, it is actually recommended to rather submit data as the integral (i.e. a monotinically increasing counter).
eetsdbvalues = cfg["eetsdbvalues"] # non-numeirc eedomus values and their translation
eetsdbrecipes = cfg["eetsdbrecipes"] #recipes to be used to correct some readings.
from recipes import cureValues

# small utility
def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return izip(a, b)

# main class
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
        if len(measurements)>0:
            print "Inserting %d measurements for the following timeseries:"%len(measurements)
            print timeseries.getMap(full=False).__str__()
        self.insertHistory(measurements)
        self.addAnnotation(timeseries)

    def registerTS(self, timeseries):
        try:
            res = self.client_.search("LOOKUP",metric=timeseries.metric, tags=timeseries.tags)
        except OpenTSDBError:
            timeseries.assign_uid(self.client_)

    def insertHistory(self, measurements):
        return self.client_.put_measurements(measurements, summary=True, compress=True)

# TS METADATA:
# self.displayName = kwargs.get("displayName",'') # TODO: put most recent name in metadata
# self.units = kwargs.get("units",'') #TODO: put units in metadata. Should come from the yaml cfg
# self.custom = kwargs["custom"] if kwargs.get("custom",None) is not None else {} # TODO: other: creation_date,usage_name

    def mkTimeseries(self,device):
        try:
            lookup = self.client_.search("LOOKUP",tags={"periph_id":str(device.periph_id)})
            if lookup["totalResults"]==0: # create if needed
                metric = eetsdbMapping[int(device.periph_id)]
                tags = { "periph_id":str(device.periph_id), 
                         "room":self.cureString(device.room_name),
                         "name":self.cureString(device.name)}
                return OpenTSDBTimeSeries(metric,tags)
            elif lookup["totalResults"]==1: # take existing one if possible
                return OpenTSDBTimeSeries(tsuid=lookup["results"][0]["tsuid"]).loadFrom(self.client_)
            else: # abort in case of ambiguity
                raise RuntimeError("More than one time series with tsuid = %s"%str(device.periph_id),lookup)
        except OpenTSDBError:
                metric = eetsdbMapping[int(device.periph_id)]
                tags = { "periph_id":str(device.periph_id), 
                         "room":self.cureString(device.room_name),
                         "name":self.cureString(device.name)}
                return OpenTSDBTimeSeries(metric,tags)

    def mkMeasurements(self,timeseries,history):
        # history is a vector of pairs (measurement,timestamp)
        history = self.cureValues(timeseries,history)
        if eedbintegration[int(timeseries.tags["periph_id"])][0]:
            conversionFactor=eedbintegration[int(timeseries.tags["periph_id"])][2]
            samplingPeriod=eedbintegration[int(timeseries.tags["periph_id"])][1]
            last= self.getLastValue(timeseries)
            return [OpenTSDBMeasurement(timeseries, int(timestamp.strftime("%s")),value) for (value,timestamp) in self.cummulative(history, conversionFactor, samplingPeriod, last)]
        else:
            return [OpenTSDBMeasurement(timeseries, int(timestamp.strftime("%s")),value) for (value,timestamp) in history]

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
    	for i,((d0,t0),(d1,t1)) in enumerate(pairwise(data)):
    		if last is None:
    			last = 0
                        output.append((0,t0))
                else:
                    #TODO: fix this: have to add one entry for the first measurement. 
                    # for that, one needs last, d0, t0, but also the time of the last measurement 
                    pass
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

