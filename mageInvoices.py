#!/usr/bin/python
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
    home="" if home is None else home
    configFiles=[
        home+"/.config/magento-client/config.json",
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

def getInvoices(year, month, day=None):
    year=int(year)
    month=int(month)
    day=int(day) if (day is not None) else 0
    start=datetime(year, month, 1, 0,0,0)
    end=datetime(year if month<12 else year+1, (month+1)%12, 1, 0,0,0)
    return mage.getInvoices(start, end)

def dateTotals(invoices):
    sumkeys=["subtotal", "shipping", "preTax", "pst", "gst", "total"]
    out={}
    for i in invoices:
        d=i.localDateStr
        if(not d in out):
            out[d]={k:0 for k in sumkeys}
        out[d]={k: out[d][k] + getattr(i, k) for k in sumkeys}
    return out

def monthSummary(year, month):
    table=[["Date", "Subtotal", "PST", "GST", "Total"]]
    for (date, i) in sorted(dateTotals(getInvoices(year,month)).items()):
        table.append([
            date,
            i["subtotal"],
            round(i["pst"],   2),
            round(i["gst"],   2),
            round(i["total"], 2)
        ])
    return SingleTable(table).table

def monthInvoiceDetails(year, month):
    table=[["ID", "Date", "Subtotal", "PST", "GST", "Total"]]
    for i in getInvoices(year, month):
        subtotal=Decimal(i["base_subtotal"])+Decimal(i["base_shipping_amount"])
        tax=i["tax"]
        table.append([
            i["increment_id"],
            i["date"].astimezone(localTZ).strftime("%Y-%m-%d"),
            subtotal,
            round(i["pst"],2),
            round(i["gst"],2),
            i["base_grand_total"]
        ])
    return SingleTable(table).table

if(len(sys.argv)>2):
    month= int(sys.argv[2])
if(len(sys.argv)>1):
    year=int(sys.argv[1])
    print("Connecting to Magento...")
    mage=Mage(host=config["api"]["host"], port=80, user=config["api"]["user"], key=config["api"]["key"], pst=pst, gst=gst, timezone=localTZ)
    print monthSummary(year, month)
    print monthInvoiceDetails(year, month)
