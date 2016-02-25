#!/bin/env python
# -*- coding: utf8 -*-

from eedomus import findDevice
from eedb import eeDbAPI
import ROOT
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from itertools import tee, izip
def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return izip(a, b)

def cummulative(inputgraph):
	output = ROOT.TGraph()
	timevector = inputgraph.GetX()
	valuesvector = inputgraph.GetY()
	data = []
	last = None
	for i in range(inputgraph.GetN()-1,0,-1):
		data.append((timevector[i],valuesvector[i]))
	for i,((t0,d0),(t1,d1)) in enumerate(pairwise(data)):
		if last is None:
			last = d0
			output.SetPoint(i,t0,0)
		last += (((d0+d1)/2.)*(t1-t0))/3600000. # watt * seconds -> kWh
		output.SetPoint(i+1,t1,last)
	return output

def graphFromHistory(history):
    time = ROOT.TDatime()
    graph = ROOT.TGraph()
    for i,(to,do) in enumerate(history):
        time.Set(do.strftime("%Y-%m-%d %H:%M:%S"))
        graph.SetPoint(i,time.Convert(),ROOT.Double(float(to)))
    return graph

# login
api = eeDbAPI()
devs = api.getPeriphList()

# temperatures
c1 = ROOT.TCanvas()
graphs = []
temps = findDevice(devs,usage_name=u"Température")
for temp in temps:
    history = temp.getHistory()
    gr = graphFromHistory(history)
    gr.SetLineColor(30+len(graphs))
    gr.SetLineWidth(3)
    if len(graphs):
    	gr.Draw("same")
    else:
    	gr.Draw()
    graphs.append(gr)

# consommations
c2 =  ROOT.TCanvas()
cgraphs = []
consos = findDevice(devs,usage_name=u"Consomètre")
for conso in consos:
    history = conso.getHistory()
    gr = graphFromHistory(history)
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
    

# just the total reading. Instant + integral
igraphs = []
c3 =  ROOT.TCanvas()
gr0.Draw()
c4 = ROOT.TCanvas()
gr0 = cummulative(gr0)
igraphs.append(gr0)
gr0.Draw()

# method to rebin data.
# it doesn't work for cumulative data.
#TODO: add mode for min/max
def rebin(data, period):

  output = [ (0,data[-1][1]),  ]

  for ((d0,time0),(d1,time1)) in pairwise(data[::-1]):
    lasttime = output[-1][1]
    nexttime = lasttime + period
    d0 = float(d0)
    d1 = float(d1)

    # if the previous data point is before this interval, add a correction to the previous interval
    # this should never happen...
    if time0 < lasttime:
      print "WARNING: I should never come here..."
      duration = (lasttime-time0).total_seconds()
      output[-2] = (output[-2][0] + d1*duration/period.total_seconds(), output[-2][1])
    else:
      lasttime = time0

    # fill the "full intervals
    while time1 > nexttime:
      duration = (nexttime - lasttime).total_seconds()
      output[-1] = (output[-1][0] +d1*duration/period.total_seconds(),output[-1][1])
      output.append((0,nexttime)) 
      lasttime = output[-1][1]
      nexttime = lasttime + period

    # the last bit
    duration = (time1-lasttime).total_seconds()
    output[-1] = (output[-1][0] +d1*duration/period.total_seconds(), output[-1][1])
  
  return output[:-1]

def perHour(data):
	return rebin(data,timedelta(0,3600))

def perDay(data):
	return rebin(data,timedelta(1))

def perWeek(data):
	return rebin(data,timedelta(7))

def perMonth(data):
	return rebin(data,timedelta(30))

#TODO: add a cleaning method for the history: drop zero values, etc.

