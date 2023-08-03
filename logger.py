from syslog import LOG_EMERG, LOG_ALERT, LOG_CRIT, LOG_ERR, LOG_WARNING, LOG_NOTICE, LOG_INFO, LOG_DEBUG
from syslog import syslog
import sys

class logger:
    """Simple class to send logs to syslog and/or to the console
       Priority levels (high to low):
       LOG_EMERG, LOG_ALERT, LOG_CRIT, LOG_ERR, LOG_WARNING, LOG_NOTICE, LOG_INFO, LOG_DEBUG.
    """
    def __init__(self,console=True,syslog=False,threshold=LOG_INFO):
        self.console = console
        self.syslog = syslog
        self.threshold = threshold

        self.names = { 
                      LOG_EMERG   : "EMERGENCY", 
                      LOG_ALERT   : "ALERT", 
                      LOG_CRIT    : "CRITICAL", 
                      LOG_ERR     : "ERROR", 
                      LOG_WARNING : "WARNING", 
                      LOG_NOTICE  : "NOTICE", 
                      LOG_INFO    : "INFO", 
                      LOG_DEBUG   : "DEBUG"
                }

    def log(self,priority,message):
        assert(priority in self.names)
        if priority>self.threshold:
            return
        if self.console:
            if priority in [LOG_EMERG,LOG_ALERT,LOG_CRIT,LOG_ERR]:
                print(f"{self.names[priority]}: {message}", file=sys.stderr)
            else:
                print(f"{self.names[priority]}: {message}")
        if self.syslog:
            syslog(priority,message)

