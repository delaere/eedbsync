#!/bin/env python
# -*- coding: utf8 -*-

from eedomus import findDevice
from eedb import eeDbAPI
import ROOT
from datetime import datetime
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

#TODO: add a method for averaging over some time (1h, 1d, etc.)

#TODO: add a cleaning method for the history: drop zero values, etc.

