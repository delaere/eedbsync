import socket
import string
import unicodedata as ud
from datetime import datetime

from opentsdbclient.client import RESTOpenTSDBClient as OpenTSDBClient
from opentsdbclient.opentsdberrors import OpenTSDBError
from opentsdbclient.opentsdbobjects import OpenTSDBTimeSeries, OpenTSDBMeasurement


# this dictionnary maps eeDevices to openTSDB metrics

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
    268361 : "applicance",
    268362 : "applicance",
    268363 : "applicance",
    268364 : "applicance",
    268365 : "power.consumption",
    268366 : "power.consumption",
    268367 : "power.consumption",
    268368 : "power.consumption",
    268369 : "power.consumption",
    268370 : "power.consumption",
    325388 : "light",
    325389 : "power.consumption",
    348904 : "light",
    271741 : "applicance",
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

class eeTSDB:
    """Simple utility to migrate the history from eedb to eetsdb"""

    def __init__(self,host,port):
        self.host_ = host
        self.port_ = port
        self.client_ = OpenTSDBClient(self.host_, self.port_)

    def migrate(self,device,start_date=None, end_date=None, history = None):
        """Main method: give device and time range to migrate to openTSDB"""
        timeseries = self.mkTimeseries(device)
        self.registerTS(timeseries)
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
        metric = eetsdbMapping[device.periph_id]
        tags = { "periph_id":str(device.periph_id), 
                 "room":self.cureString(device.room_name),
                 "name":self.cureString(device.name)}
        return OpenTSDBTimeSeries(metric,tags)

    def mkMeasurements(self,timeseries,history):
        # history is a vector of pairs (measurement,timestamp)
        try:
            return [OpenTSDBMeasurement(timeseries, int(timestamp.strftime("%s")), self.translateValue(value)) for (value,timestamp) in history]
        except:
            print("Unable to create valid measurements.")
            if len(history)>0: print "Example:",history[0]
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

# can we do better? We are stuck since eedomus never sends the raw value and doesn't give access to the dict.
    def translateValue(self,value):
        if value in ["On", "ON", u'Activ\xe9e', "Alarme", "Ouvert", "Mouvement", "Joignable"]: return 1
        if value in ["Off","OFF", u'D\xc3\xa9sactiv\xc3\xa9e', "OK", u'Ferm\xe9', "Aucun mouvement", "Non joignable", "--"]: return 0
        if value in ["Alerte", "Vibration"]: return 2
        try:
            return float(''.join([c for c in value if c in "-0123456789."]))
        except:
            print value,"cannot be translated"
            return 0

