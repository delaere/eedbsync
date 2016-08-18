import tempfile
import gzip
import subprocess
from opentsdbclient.client import RESTOpenTSDBClient as OpenTSDBClient
from opentsdbclient.opentsdberrors import OpenTSDBError
from opentsdbclient.opentsdbobjects import OpenTSDBTimeSeries


# this dictionnary maps eeDevices to openTSDB metrics

eetsdbMapping = {
    12345 : "temperature",
    12346 : "humidity"
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
            history = device.getHistory(self,start_date, end_date)
        measurements = self.mkMeasurements(timeseries,history)
        self.insertHistory(measurements)

    def registerTS(self, timeseries):
        try:
            res = self.client_.search("LOOKUP",metric=timeseries.metric, tags=timeseries.tags)
        except opentsdberrors.OpenTSDBError:
            timeseries.assign_uid(self.client_)

    def insertHistory(self, measurements):
        return self.client.put_measurements(measurements, summary=True, compress=True)

    def mkTimeseries(self,device):
        metric = eetsdbMapping[device.periph_id]
        tags = { "periph_id":device.periph_id, 
                 "parent_periph_id":device.parent_periph_id,
                 "room":device.room_name,
                 "name":device.name,
                 "usage":device.usage_name}
        return OpenTSDBTimeSeries(metric,tags)

    def mkMeasurements(self,timeseries,history):
        # history is a vector of pairs (measurement,timestamp)
        return [OpenTSDBMeasurement(timeseries, timestamp, value) for (value,timestamp) in history]

