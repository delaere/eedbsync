# set of ad hoc methods to correct inputs

class cureValues:
    def __init__(self):
        pass

    @staticmethod
    def fix_gazreading(reading):
        # for some time, readings were in dm3. Now fixed: returns m3
        if reading >50:
            return reading/1000.
        else:
            return reading

    @staticmethod
    def fix_indoorTemperature(reading):
        # sometimes drops to zero or negative
        if reading<1e-3:
            return None
        else:
            return reading
