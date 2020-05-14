from eetsdb import eeTSDB, eetsdbMapping
from eedb import eeDbAPI
from opentsdbclient.client import RESTOpenTSDBClient
from opentsdbclient.opentsdbquery import OpenTSDBtsuidSubQuery, OpenTSDBQuery
from opentsdbclient.opentsdberrors import OpenTSDBError

from datetime import datetime
from dateutil.relativedelta import relativedelta

from optparse import OptionParser

import pprint
import time

def migrate(replace=False,yearsback=10,dryrun=False):
    api = eeDbAPI()
    devices = api.getPeriphList()
    eetsdb  = eeTSDB('localhost',4242)
    client = RESTOpenTSDBClient("localhost",4242)
    for dev in devices:
        # check that the metric is in eetsdbMapping
        if not dev.periph_id in eetsdbMapping:
            print(("Skipping", dev.periph_id, dev.name, dev.room_name, dev.usage_name))
            continue
        # check if the TS is there already. If yes, look for the last point and continue from there
        ts = eetsdb.mkTimeseries(dev)
        if not dryrun: eetsdb.registerTS(ts)
        begin = datetime.now()-relativedelta(years=yearsback)
        try:
            res = client.search("LOOKUP",metric=ts.metric, tags=ts.tags)
            if res["totalResults"]>1 :
                print("Time series:")
                pprint.pprint(ts.getMap())
                print("Search result:")
                pprint.pprint(res)
                raise RuntimeError("The timeseries is ambiguous. This should not happen.")
            elif res["totalResults"]==1:
                tsuid = res["results"][0]["tsuid"]
                sq = OpenTSDBtsuidSubQuery("sum",[tsuid])
                if replace:
                    query = OpenTSDBQuery([sq],"%dy-ago"%yearsback,delete=True)
                    if not dryrun: answer = client.query(query)
                    begin = datetime.now()-relativedelta(years=yearsback)
                    time.sleep(5)
                else:
                    query = OpenTSDBQuery([sq],"%dy-ago"%yearsback)
                    answer = client.query(query)
                    if len(answer)>0:
                        last = max([ int(k) for k in list(answer[0]["dps"].keys()) ])
                        begin = datetime.fromtimestamp(last+1)
            # migrate that dev
            print(("migrating",dev.periph_id, dev.name, dev.room_name, dev.usage_name, "from", begin))
            if not dryrun: eetsdb.migrate(device=dev,start_date=begin, end_date=None)
        except OpenTSDBError as e:
            print(("Exception while processing",dev.periph_id, dev.name, dev.room_name, dev.usage_name,"Skipping."))
            raise

class MyOptionParser: 
    def __init__(self):
        usage  = "Usage: %prog [options]"
        self.parser = OptionParser(usage=usage)
        self.parser.add_option("-r","--replace", action="store_true", 
                               dest="replace", default=False,
             help="replace existing values")
        self.parser.add_option("-y","--yearsback", action="store", type="int",
                               dest="yearsback", default=10,
             help="years back in history")
        self.parser.add_option("-d","--dry", action="store_true",
                               dest="dryrun", default=False,
             help="dry run (do not touch the database)")

    def get_opt(self):
        """
        Returns parse list of options
        """
        opts, args = self.parser.parse_args()
        return opts

if __name__ == "__main__":
    # get the options
    optmgr = MyOptionParser()
    opts = optmgr.get_opt()
    migrate(**opts.__dict__)

