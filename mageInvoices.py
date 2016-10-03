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

def groupInvoicesByDate(invoices):
    out={}
    for i in invoices:
        if(not i.localDateStr in out):
            out[i.localDateStr]=[]
        out[i.localDateStr].append(i)
    return out

def invoiceTable(title, invoices):
    table=[["ID", "Time", "Subtotal", "PST", "GST", "Total"]]
    subtotal=0
    pst=0
    gst=0
    total=0
    for i in invoices:
        table.append([
            i.id,
            i.localTimeStr,
            round(i.preTax, 2),
            round(i.pst, 2),
            round(i.gst, 2),
            round(i.total, 2)
            ])
        subtotal+=i.preTax
        pst+=i.pst
        gst+=i.gst
        total+=i.total
    table.append([
        "Total",
        "",
        round(subtotal, 2),
        round(pst, 2),
        round(gst, 2),
        round(total, 2)
        ])
    return SingleTable(table, title).table

if(len(sys.argv)>2):
    month= int(sys.argv[2])
if(len(sys.argv)>1):
    year=int(sys.argv[1])
    sys.stderr.write("Connecting to Magento...\n")
    sys.stderr.flush()
    mage=Mage(host=config["api"]["host"], port=80, user=config["api"]["user"], key=config["api"]["key"], pst=pst, gst=gst, timezone=localTZ)
    invoices=mage.getInvoices(
            datetime(year, month, 1, 0,0,0),
            datetime(
                year if month<12 else year+1,
                (month+1)%12,
                1, 0,0,0
                )
            )
    for (date, invoices) in sorted(groupInvoicesByDate(invoices).items()):
        print(invoiceTable(date, invoices))
