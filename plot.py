#!/bin/env python
# -*- coding: utf8 -*-

from eedomus import findDevice
from eedb import eeDbAPI
import ROOT
from datetime import datetime
from dateutil.relativedelta import relativedelta


def graphFromHistory(history):
    time = ROOT.TDatime()
    graph = ROOT.TGraph()
    for i,(to,do) in enumerate(history):
        time.Set(do.strftime("%Y-%m-%d %H:%M:%S"))
        graph.SetPoint(i,time.Convert(),ROOT.Double(float(to)))
    return graph

api = eeDbAPI()
devs = api.getPeriphList()
temps = findDevice(devs,usage_name=u"Température")
outside = temps[0].getHistory()
inside = temps[3].getHistory()

c1 = ROOT.TCanvas()
gr = graphFromHistory(outside)
gr.Draw()

c2 = ROOT.TCanvas()
gr2 = graphFromHistory(inside)
gr2.Draw()
