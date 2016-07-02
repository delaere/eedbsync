import tempfile
import gzip
import subprocess
from opentsdbclient import client as opentsdbclient


# this dictionnary maps eeDevices to openTSDB metrics

eetsdbMapping = {
    12345 : "temperature",
    12346 : "humidity"
        }

# class that prepares a time series from a device

class eeTimeSeries:
    def __init__(metric=None, tags={}, device=None, history=None):
        if device is None:
            self.metric = metric
            self.tags = tags
        else:
            self.metric = eetsdbMapping[device.periph_id]
            self.tags = { "periph_id":device.periph_id, 
                          "parent_periph_id":device.parent_periph_id,
                          "room":device.room_name,
                          "name":device.name,
                          "usage":device.usage_name}
        self.history = []
        if history is not None:
            self.setHistory(history)

    def setHistory(self, history):
        if history is not None:
            self.history = [] #TODO fill and convert the timestamp. Format: pairs (timestamp, data)
        else:
            self.history = []

# specialized client that feeds in one datapoint

class eeTSDB:
    def __init__(self,host,port):
        self.host_ = host
        self.port_ = port
        self.client_ = opentsdbclient.get_client((self.host_, self.port_), protocol='rest')
        #TODO for this we should use the /api/search, to be added to the client
        for dataid,metric in eetsdbMapping.iteritems():
            if len(self.client_.search(metric=metric))==0:
                self.mkMetric(metric)

    def mkMetric(self, metric):
        # use the external tool to declare the metric
        return subprocess.call(["tsdb", "mkmetric", metric], stdout=-1, stderr=-1)
        #TODO: this could be done via the API (tbc)

    def insertHistory(self, timeseries, batch=False):
        if batch:
            self.batchMigration(timeseries)
        else:
            self.restMigration(timeseries)

    def restMigration(self, timeseries):
        for (value,time) in timeseries.history:
            self.client_.put_meter({"metric":timeseries.metric, "timestamp":timestamp, "value":value, "tags":timeseries.tags})
            #TODO: change the synthax of the client to sth more pythonic.

    def batchMigration(self,timeseries):
        tmpfile = self.prepareBatchFile(timeseries)
        self.insert(tmpfile.name)
        tmpfile.close()

    def prepareBatchFile(self, timeseries):
        # create a file for batch upload
        tmpf = tempfile.NamedTemporaryFile()
        with gzip.GzipFile(fileobj=tmpf) as f:
            for (value,timestamp) in timeseries.history:
                f.write("%s %d %f %S"%(timeseries.metric,timestamp,value,timeseries.tags))
        return tmpf

    def insert(self, filename):
        # insert the file into openTSDB using the provided tool
        return subprocess.call(["tsdb", "import", filename], stdout=-1, stderr=-1)

