#!/bin/env python
# -*- coding: utf8 -*-

from datetime import datetime, timedelta, date
from itertools import tee, izip
from enum import Enum
import ROOT
import operator


class eeHistory:
    def __init__(self,data, binned = False, cummulative = False):
  	self.data_ = sorted(data,key=operator.itemgetter(1), reverse=True)
	self.binned_ = binned
	self.cummulative_ = cummulative

    def data(self):
        return self.data_

    def dico(self):
        tmp = [(key,value) for (value,key) in self.data_]
	return dict(tmp)

    @staticmethod
    def pairwise(iterable):
        "s -> (s0,s1), (s1,s2), (s2, s3), ..."
        a, b = tee(iterable)
        next(b, None)
        return izip(a, b)

    def cleanData(self, minimum = -float('Inf'), maximum = float('Inf'), exclude=[]):
        """ Method to clean the data... quite trivial """
        self.data_ = [(value, time) for (value, time) in self.data_ if value>=minimum and value<=maximum and value not in exclude ]

    def binData(self, period = timedelta(minutes=15)):
        """ Method to bin unbinned data. """
      
        # it should not be used on already binned or cumulative data.
        if self.binned or self.cummulative: return
        
        output = [ (0,self.data_[-1][1]), ]
    
        for ((d0,time0),(d1,time1)) in pairwise(self.data_[::-1]):
          lasttime = output[-1][1]
          nexttime = lasttime + period
          d0 = float(d0)
    
          # this should never happen with sorted data
          assert(time0>=lasttime)
    
          # fill the full intervals
          while time1 > nexttime:
            duration = (nexttime - lasttime).total_seconds() if time0<lasttime else (nexttime-time0).total_seconds()
            output[-1] = (output[-1][0] +d0*duration/period.total_seconds(),output[-1][1])
            output.append((0,nexttime)) 
            lasttime = output[-1][1]
            nexttime = lasttime + period
    
          # the last bit
          duration = (time1-lasttime).total_seconds() if time0<lasttime else (time1-time0).total_seconds()
          output[-1] = (output[-1][0] +d0*duration/period.total_seconds(), output[-1][1])
        
	# replace the data with the new series
        self.data_ = output[:-1]
	self.binned_ = True

    class timeGranularity(Enum):
        year = 1
        month = 2
        day = 3
        hour = 4
    
    class rebinMode(Enum):
        normal = 1
        minimum = 2
        maximum = 3

    def rebin(self, granularity, mode = rebinMode.normal):
	""" rebin binned data so coarser predetermined intervals """

        # this is the best way to rebin data that are already integrated on a fixed period, like gaz consumption or degrees-jours
        # but it doesn't work when the data points are instant measurements like electricity
        # for these, first use the binHistory method above
	assert (self.binned_ and not self.cummulative_)
	assert isinstance(granularity,eeHistory.timeGranularity)
	assert isinstance(mode,eeHistory.rebinMode)
    	output = {}
    	for (entry, timestamp) in self.data_:
    		if granularity==eeHistory.timeGranularity.hour:
    			time = datetime(timestamp.year, timestamp.month, timestamp.day, timestamp.hour, 0, 0)
    		else:
    			time = date(timestamp.year, timestamp.month if granularity!=eeHistory.timeGranularity.year else 0, timestamp.day if granularity==eeHistory.timeGranularity.day else 0)
    		if not time in output:
    			output[time] = float(entry)
    		else:
    			if mode == eeHistory.rebinMode.normal:
    				output[time] += float(entry)
    			elif mode == eeHistory.rebinMode.minimum:
    				output[time] = min(float(entry),output[time])
    			elif mode == eeHistory.rebinMode.maximum:
    				output[time] = max(float(entry),output[time])
	self.data_ = sorted([(value,time) for time, value in output.iteritems()],key=operator.itemgetter(1), reverse=True)

    def histogram(self,name="histo",title="histo", binLabel="%B %Y"):
        """ make an histogram """
        h = ROOT.TH1F(name,title,len(self.data_),0,len(self.data_))
	for i,(value,date) in enumerate(self.data_[::-1]):
            h.SetBinContent(i+1,value)
            h.GetXaxis().SetBinLabel(i+1,date.strftime(binLabel))
        return h

    def graph(self):
        """ make a graph """
        time = ROOT.TDatime()
        graph = ROOT.TGraph()
        for i,(to,do) in enumerate(self.data_):
            time.Set(do.strftime("%Y-%m-%d %H:%M:%S"))
            graph.SetPoint(i,time.Convert(),ROOT.Double(float(to)))
        return graph

################################################################################

def cummulative(inputgraph, conversionFactor = 3600000., samplingPeriod = None):
	""" Integrates the input to return a cummulative distribution.
	    By default, it uses the trapeze integration rule.
	    If samplingPeriod is set, each point is taken independently over that time.
	    The default conversion factor works for both electricity (watt*s -> kWh) and gaz (dm3/h*s -> m3)
	"""
	output = ROOT.TGraph()
	timevector = inputgraph.GetX()
	valuesvector = inputgraph.GetY()
	data = []
	last = None
	for i in range(inputgraph.GetN()-1,0,-1):
		data.append((timevector[i],valuesvector[i]))
	for i,((t0,d0),(t1,d1)) in enumerate(eeHistory.pairwise(data)):
		if last is None:
			last = 0
			output.SetPoint(i,t0,0)
		if samplingPeriod is None:
			last += (((d0+d1)/2.)*(t1-t0))/conversionFactor
		else:
			last += d0*samplingPeriod/conversionFactor
		output.SetPoint(i+1,t1,last)
	return output

################################################################################

def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return izip(a, b)

def degreeJours(t_ext, t_ref = 15, t_max = 15):
  """compute the degree-jours per day"""

  dataStart = t_ext[-1][1].replace(hour=0, minute=0, second=0, microsecond=0) 
  date(t_ext[-1][1].year, t_ext[-1][1].month, t_ext[-1][1].day)
  period = timedelta(days=1)
  output = [ (0,dataStart),  ]

  for ((d0,time0),(d1,time1)) in pairwise(t_ext[::-1]):
    lasttime = output[-1][1]
    nexttime = lasttime + period
    d0 = float(d0)
    d1 = float(d1)

    # fill the "full days"
    while time1 > nexttime:
      duration = (nexttime - lasttime).total_seconds() if time0<lasttime else (nexttime-time0).total_seconds()
      if d1<t_max:
          output[-1] = (output[-1][0] + (t_ref-d1)*duration/period.total_seconds(),output[-1][1])

      output.append((0,nexttime)) 
      lasttime = output[-1][1]
      nexttime = lasttime + period

    # the last bit
    duration = (time1-lasttime).total_seconds() if time0<lasttime else (time1-time0).total_seconds()
    if  d1<t_max:
	 output[-1] = (output[-1][0] + (t_ref-d1)*duration/period.total_seconds(),output[-1][1])
  
  return output[:-1]

################################################################################
################################################################################

from eedomus import findDevice
from eedb import eeDbAPI

# login
api = eeDbAPI()
devs = api.getPeriphList()

# temperatures
c1 = ROOT.TCanvas()
graphs = []
temps = findDevice(devs,usage_name=u"Température")
for temp in temps:
    history = eeHistory(temp.getHistory())
    gr = history.graph()
    gr.SetLineColor(30+len(graphs))
    gr.SetLineWidth(3)
    if len(graphs):
    	gr.Draw("same")
    else:
    	gr.Draw()
    graphs.append(gr)

# conso électricité
c3 =  ROOT.TCanvas()
c3.Divide(2,2)
c3.cd(1)
cgraphs = []
consos = findDevice(devs,usage_name=u"Consomètre")
for conso in consos:
    history = eeHistory(conso.getHistory())
    gr = history.graph()
    gr.SetLineColor(30+len(graphs))
    gr.SetLineWidth(3)
    cgraphs.append(gr)
first = True
for gr in sorted(cgraphs, key=lambda g:-g.GetHistogram().GetMaximum()) :
	if first:
		gr.Draw()
		first = False
		gr0 = gr
	else:
		gr.Draw("same")
    
c3.cd(2)
igraphs = []
gr0.Draw()
c3.cd(3)
gr0 = cummulative(gr0)
igraphs.append(gr0)
gr0.Draw()
#ajouter histogramme de conso par semaine et par mois

# conso gaz
# http://www.energieplus-lesite.be/index.php?id=10016
gaz = eeHistory(findDevice(devs,usage_name=u"Compteur de gaz")[0].getHistory(), binned = True)
gazcanvas =  ROOT.TCanvas()
gazcanvas.Divide(2,2)
gazcanvas.cd(2)
gazgr = gaz.graph()
gazgrc = cummulative(gazgr, 3600000, 900)
gazgrc.Draw()
gazcanvas.cd(1)
gaz.rebin(eeHistory.timeGranularity.day)
gazh = gaz.histogram(name="gaz",title="Consommation gaz",binLabel="%d %B %Y")
gazh.Scale(1/4000.)
gazh.Draw()
gazcanvas.cd(3)
dj = eeHistory(degreeJours(temps[1].getHistory()))
djg = dj.graph()
djg.Draw()
gazcanvas.cd(4)
performance = ROOT.TGraph()
i = 0
for degree,timestamp in dj.data():
	day = date(timestamp.year, timestamp.month, timestamp.day)
	if day in gaz.dico():
		performance.SetPoint(i,degree,gaz.dico()[day]/4000.)
		i+=1
performance.SetMarkerStyle(ROOT.kFullCircle)
performance.Draw("AP")
performance.Fit("pol1")
#TODO repeter par semaine et par mois
