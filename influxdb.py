"""
Created on Wed Jul 26 15:04:54 2023

@author: delaere
"""

import yaml

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS, PointSettings
from influxdb_client.client.exceptions import InfluxDBError

# Influxdb2 python API. 
# From https://influxdb-client.readthedocs.io/en/stable/index.html
# and  https://influxdb-python.readthedocs.io/en/latest/index.html

def is_float(string):
    if string.replace(".", "", 1).isnumeric():
        return True
    else:
        return False

def converted(string):
    return float(string) if is_float(string) else string

def are_float(points):
    """ determine is the points are float or not """
    thetypes = [is_float(p) for p,_ in points ]
    # we accept the list as floats if more than 50% are.
    if len(thetypes)>0 and thetypes.count(True)/len(thetypes) > 0.5:
        return True
    else:
        return False

class Influxdb:
    """ Simple interface to the influxdb API, for basic operations """
    
    def __init__(self,configfile="config.yml"):
        self.client ,self.point_settings, self.bucket, self.org = self._getClient(configfile)

    def toInfluxData(self,device,points):
        """ converts a series of measurements to the format required to 
            write to InfluxDB v2 """
            
        # output
        output = []
            
        # tags
        periph_id = device.periph_id
        parent_periph_id = device.parent_periph_id
        name = device.name
        room_name = device.room_name
        # measurement
        usage_name = device.usage_name
        
        are_f = are_float(points)
        
        print(f"Saving {usage_name},name={name} as {'float' if are_f else 'string'}")
        for (value,timestamp) in points:
            if are_f:
                if is_float(value):
                    p = Point(usage_name).tag("periph_id", periph_id) \
                    .tag("parent",parent_periph_id) \
                    .tag("name",name) \
                    .tag("room",room_name) \
                    .field("value", float(value)).time(timestamp)
            else:
                    p = Point(usage_name).tag("periph_id", periph_id) \
                    .tag("parent",parent_periph_id) \
                    .tag("name",name) \
                    .tag("room",room_name) \
                    .field("string", value).time(timestamp)
            output.append(p)
        return output

    def _getClient(self,configfile="config.yml"):
        """ Returns the Influxdb client """
        with open(configfile, 'r') as ymlfile:
            cfg = yaml.load(ymlfile, Loader=yaml.FullLoader)
        url = cfg["url"]
        token = cfg["token"]
        org = cfg["org"]
        bucket = cfg["bucket"]
        tags = cfg["tags"]
        
        point_settings = PointSettings(**tags)
        
        client = InfluxDBClient(url=url, token=token, org=org, timeout=60_000)
        return (client,point_settings,bucket,org)

    def writeInflux(self,data):
        """ Uses the Influx write API to write data to the db """
        try:
            write_api = self.client.write_api(write_options=SYNCHRONOUS,point_settings=self.point_settings)
            write_api.write(self.bucket, self.org, data)
        except InfluxDBError as e:
            print(e)
        
    def getLastEntry(self,device):
        """ Finds the last entry already in the database """
        usage_name = device.usage_name
        periph_id = device.periph_id
        query=f'from(bucket: "{self.bucket}") |> range(start: 1970-01-01T00:00:00Z) |> filter(fn: (r) => r["_measurement"] == "{usage_name}")  |> filter(fn: (r) => r["periph_id"] == "{periph_id}") |> last()'
        result = self.client.query_api().query(org=self.org, query=query)
        for table in result:
            for record in table.records:
                return record.get_time()
