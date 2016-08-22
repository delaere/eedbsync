from eetsdb import eeTSDB, eetsdbMapping
from eedb import eeDbAPI
from opentsdbclient.client import RESTOpenTSDBClient
from opentsdbclient.opentsdbquery import OpenTSDBtsuidSubQuery, OpenTSDBQuery
from opentsdbclient.opentsdberrors import OpenTSDBError

from datetime import datetime
from dateutil.relativedelta import relativedelta

import pprint

#TODO add a funtion to submit integrated consumptions (electricity & gas) rather than instant values.
#When working with time series, it is actually recommended to rather submit data as the integral (i.e. a monotinically increasing counter). µ
#OpenTSDB can then "differentiate" this using the rate function.

# look into the ROOT code to do this properly.
# might also add a hook to fix the normalization issue in eedomus (time-dependent scale factor)

def migrate(replace=False,yearsback=10):
    api = eeDbAPI()
    devices = api.getPeriphList()
    eetsdb  = eeTSDB('localhost',4242)
    client = RESTOpenTSDBClient("localhost",4242)
    for dev in devices:
        # check that the metric is in eetsdbMapping
        if not dev.periph_id in eetsdbMapping:
            print "Skipping", dev.periph_id, dev.name, dev.room_name, dev.usage_name
            continue
        # check if the TS is there already. If yes, look for the last point and continue from there
        ts = eetsdb.mkTimeseries(dev)
        begin = datetime.now()-relativedelta(years=yearsback)
        try:
            res = client.search("LOOKUP",metric=ts.metric, tags=ts.tags)
            if res["totalResults"]>1 :
                print "Time series:"
                pprint.pprint(ts.getMap())
                print "Search result:"
                pprint.pprint(res)
                raise RuntimeError("The timeseries is ambiguous. This should not happen.")
            elif res["totalResults"]==1:
                tsuid = res["results"][0]["tsuid"]
                sq = OpenTSDBtsuidSubQuery("sum",[tsuid])
                if replace:
                    query = OpenTSDBQuery([sq],"%dy-ago"%yearsback,delete=True)
                    answer = client.query(query)
                    begin = datetime.now()-relativedelta(years=yearsback)
                else:
                    query = OpenTSDBQuery([sq],"%dy-ago"%yearsback)
                    answer = client.query(query)
                    if len(answer)>0:
                        last = max([ int(k) for k in answer[0]["dps"].keys() ])
                        begin = datetime.fromtimestamp(last+1)
                    else:
                        print "unexpected answer to query... potential issue here..."
                        print answer
            # migrate that dev
            print "migrating",dev.periph_id, dev.name, dev.room_name, dev.usage_name, "from", begin
            eetsdb.migrate(device=dev,start_date=begin, end_date=None)
        except OpenTSDBError:
            print "Exception while processing",dev.periph_id, dev.name, dev.room_name, dev.usage_name,"Skipping."

