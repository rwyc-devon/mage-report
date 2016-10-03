#!/usr/bin/python
from datetime import datetime, timedelta
import pytz
from magento import MagentoAPI
from terminaltables import SingleTable
from decimal import *
import progress.bar
import progress.spinner
import json
import os
import os.path
import sys
import re

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
def invoices(fromDate, toDate, showprogress=True):
    out=[]
    print("Getting Invoice List...") if(showprogress) else False
    invoices=mage.sales_order_invoice.list(
        {
            "created_at": {
                "from": fromDate.strftime("%Y-%m-%d %H:%M:%S"),
                "to": toDate.strftime("%Y-%m-%d %H:%M:%S")
            }
        }
    )
    creditmemos=mage.sales_order_creditmemo.list(
        {
            "created_at": {
                "from": fromDate.strftime("%Y-%m-%d %H:%M:%S"),
                "to": toDate.strftime("%Y-%m-%d %H:%M:%S")
            }
        }
    )
    if(showprogress):
        bar=progress.bar.IncrementalBar("Fetching Invoices... (%(eta)ds)", max=len(invoices)+len(creditmemos));
    for i in invoices:
        invoice=getInvoice(i["increment_id"])
        processInvoice(invoice)
        out.append(invoice)
        bar.next() if(showprogress) else False
    for c in creditmemos:
        creditmemo=getCreditmemo(c["increment_id"])
        processCreditmemo(creditmemo)
        out.append(creditmemo)
        bar.next() if(showprogress) else False
    bar.finish() if(showprogress) else False
    return out

def getInvoices(year, month, day=None):
    year=int(year)
    month=int(month)
    day=int(day) if (day is not None) else 0
    if(day):
        return invoices(datetime(year, month, day, 0,0,0, tzinfo=localTZ), datetime(year, month, day+1, 0,0,0, tzinfo=localTZ).astimezone(gmt))
    else:
        return invoices(datetime(year, month, 1, 0,0,0, tzinfo=localTZ), datetime(year if month<12 else year+1, (month+1)%12, 1, 0,0,0, tzinfo=localTZ).astimezone(gmt))

def processInvoice(invoice):
    addTaxFields(invoice)
    addDateFields(invoice)
    return invoice

def processCreditmemo(creditmemo):
    processInvoice(creditmemo)
    creditmemo["tax"]=0-Decimal(creditmemo["tax"])
    creditmemo["pst"]=0-Decimal(creditmemo["pst"])
    creditmemo["gst"]=0-Decimal(creditmemo["gst"])
    creditmemo["subtotal"]=0-Decimal(creditmemo["subtotal"])
    creditmemo["grand_total"]=0-Decimal(creditmemo["grand_total"])
    creditmemo["shipping_amount"]=0-Decimal(creditmemo["shipping_amount"])
    return creditmemo

def addDateFields(invoice):
    invoice["date"]=gmt.localize(datetime.strptime(invoice["created_at"], "%Y-%m-%d %H:%M:%S"))
    return invoice

def addTaxFields(invoice):
    invoice["order"]=getOrder(invoice["order_increment_id"])
    invoice["tax"]=Decimal(invoice["base_tax_amount"])
    invoice["pst"]=invoicePST(invoice)
    invoice["gst"]=invoice["tax"] - invoice["pst"]
    return invoice

def getCreditmemo(incrementId, cache={}):
    if(incrementId in cache):
        return cache[incrementId]
    cache[incrementId]=mage.sales_order_creditmemo.info(incrementId)
    return cache[incrementId]

def getInvoice(incrementId, cache={}):
    if(incrementId in cache):
        return cache[incrementId]
    cache[incrementId]=mage.sales_order_invoice.info(incrementId)
    return cache[incrementId]

def getOrder(incrementId, cache={}):
    if(incrementId in cache):
        return cache[incrementId]
    cache[incrementId]=mage.sales_order.info(incrementId)
    return cache[incrementId]

def invoiceHasPST(invoice):
    address=getOrder(invoice["order_increment_id"])["shipping_address"]
    if(address == []):
	return False
    return address["region"] == "Manitoba"

def itemHasPST(item):
    rate=0
    if(item["base_tax_amount"] and item["base_row_total"] and Decimal(item["base_row_total"])):
        rate=round(Decimal(item["base_tax_amount"]) / Decimal(item["base_row_total"]), 2)
    return round(rate*100) == pst + gst

def invoicePST(invoice):
    if(not invoiceHasPST(invoice)):
        return 0
    result=0
    for item in invoice["items"]:
        if(itemHasPST(item)):
            result+=Decimal(round(Decimal(item["base_tax_amount"])*(pst/(pst+gst)), 2))
    return result

def dateTotals(invoices):
    sumkeys=["base_subtotal", "base_shipping_amount", "base_grand_total", "gst", "pst", "tax"]
    out={}
    for i in invoices:
        d=i["date"].astimezone(localTZ).strftime("%Y-%m-%d")
        if(not d in out):
            out[d]={k:0 for k in sumkeys}
        out[d]={k: out[d][k]+Decimal(i[k]) for k in sumkeys}
    return out

def monthSummary(year, month, day=None):
    table=[["Date", "Subtotal", "PST", "GST", "Total"]]
    for (date, i) in sorted(dateTotals(getInvoices(year,month, day)).items()):
        subtotal=Decimal(i["base_subtotal"])+Decimal(i["base_shipping_amount"])
        tax=i["tax"]
        table.append([
            date,
            subtotal,
            round(i["pst"],2),
            round(i["gst"],2),
            i["base_grand_total"]
        ])
    return SingleTable(table).table

def monthInvoiceDetails(year, month, day=None):
    table=[["ID", "Date", "Subtotal", "PST", "GST", "Total"]]
    for i in getInvoices(year, month, day):
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

def filterFields(invoice):
    fields=["pst", "grand_total"]
    return {k:invoice[k] for k in fields}

if(len(sys.argv)>2):
    month= int(sys.argv[2])
day=None
if(len(sys.argv)>3):
    day= int(sys.argv[3])
if(len(sys.argv)>1):
    year=int(sys.argv[1])
    print("Connecting to Magento...")
    mage=MagentoAPI(config["api"]["host"], 80, config["api"]["user"], config["api"]["key"])
    print monthSummary(year, month, day)
    print monthInvoiceDetails(year, month, day)

