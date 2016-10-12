#!/usr/bin/python
from __future__ import print_function
from datetime import datetime, timedelta
import pytz
from terminaltables import SingleTable
from decimal import *
import json
import os
import os.path
import sys
import re
from mage import Mage
from invoice import Invoice, Item

def config():
    home=os.getenv("HOME")
    home="/dev/null" if home is None else home #/dev/null ought to make it fail
    xdg=os.getenv("XDG_CONFIG_HOME")
    xdg=home+"/.config" if xdg is None else xdg
    configFiles=[
        xdg+"/magento-client/config.json",
        "/etc/magento-client/config.json"
    ]
    for f in configFiles:
        if(os.path.isfile(f)):
            with open(f, "r") as fh:
                return json.loads(fh.read())
    return {}
config=config()
localTZ=pytz.timezone(config["timezone"])
gmt=pytz.timezone("GMT")
pst=Decimal(config["taxes"]["PST"])
gst=Decimal(config["taxes"]["GST"])
mage=None

def groupInvoicesBy(invoices, attr="localDateStr"):
    out={}
    for i in invoices:
        key=getattr(i, attr)
        if(not key in out):
            out[key]=InvoiceGroup()
        out[key].addInvoice(i)
    return out

class InvoiceGroup:
    def __init__(self, invoices=[]):
        self.subtotal=0
        self.pst=0
        self.gst=0
        self.total=0
        self.invoices=[]
        for i in invoices:
            self.addInvoice(i)

    def addInvoice(self, invoice):
        self.subtotal += invoice.preTax
        self.pst      += invoice.pst
        self.gst      += invoice.gst
        self.total    += invoice.total
        self.invoices.append(invoice)

    def table(self, title):
        table=[["ID", "Time", "Subtotal", "PST", "GST", "Total", "Customer"]]
        for i in self.invoices:
            table.append([
                i.id,
                i.localTimeStr,
                round(i.preTax, 2),
                round(i.pst,    2),
                round(i.gst,    2),
                round(i.total,  2),
                i.customer
                ])
        table.append([
            "Total",
            "",
            round(self.subtotal, 2),
            round(self.pst,      2),
            round(self.gst,      2),
            round(self.total,    2)
            ])
        return SingleTable(table, title).table

def printInvoiceTables(invoices):
    for (date, invoices) in sorted(groupInvoicesBy(invoices).items()):
        print(invoices.table(date))

def printInvoicesCSV(invoices):
    print('"id", "customer", "date", "total"')
    for invoice in sorted(invoices, key=lambda i:i.localDT):
        print('"{0}","{1}","{2}",{3}'.format(invoice.id, invoice.customer, invoice.localDateStr, invoice.total))

def printDaysCSV(invoices):
    invs=groupInvoicesBy(invoices, "dayOfMonth")
    print('"day", "subtotal", "pst", "gst", "total"')
    for i in xrange(1,31):
        if(i in invs):
            inv=invs[i]
            print('"{0}", "{1}", "{2}", "{3}", "{4}"'.format(i, round(inv.subtotal, 2), round(inv.pst, 2), round(inv.gst, 2), round(inv.total)))
        else:
            print('"{0}", "", "", "", ""'.format(i))

def usage():
    print("Usage: {0} <cmd> <year> <month>".format(sys.argv[0]))
    print('cmd can be "tables", "invoices", or "days"')

if(len(sys.argv)>3):
    month= int(sys.argv[3])
    cmd=sys.argv[1]
    year=int(sys.argv[2])
    sys.stderr.write("Connecting to Magento...\n")
    sys.stderr.flush()
    mage=Mage(host=config["api"]["host"], port=80, user=config["api"]["user"], key=config["api"]["key"], pst=pst, gst=gst, timezone=localTZ)
    invoices=mage.getInvoices(
            datetime(year, month, 1, 0,0,0),
            datetime(
                year if month<12 else year+1,
                ((month)%12)+1,
                1, 0,0,0
                )
            )
    cmds={"tables": printInvoiceTables, "invoices": printInvoicesCSV, "days": printDaysCSV}
    if(cmd in cmds):
        cmds[cmd](invoices)
    else:
        usage()
else:
    usage()
#printDaysCSV(invoices)
