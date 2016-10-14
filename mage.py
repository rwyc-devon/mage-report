#!/usr/bin/python
from datetime import datetime, timedelta
import pytz
from magento import MagentoAPI
from invoice import Invoice
import progress.bar
import sys
import re
class Mage:
    def __init__(self, host, port, user, key, pst, gst, timezone):
        self.api=MagentoAPI(host, port, user, key)
        self.pst=pst
        self.gst=gst
        self.tz=timezone
        self.invoices={}
        self.creditmemos={}
        self.orders={}
    def __dateRange(self, start, end):
        """
        Return a date range dict with timezone conversion

        The returned dict has two keys: "from" and "to", which are converted to
        GMT.
        """
        gmt=pytz.timezone("GMT")
        return {
                "from": self.tz.localize(start).astimezone(gmt).strftime("%Y-%m-%d %H:%M:%S"),
                "to":   self.tz.localize(end).astimezone(gmt).strftime("%Y-%m-%d %H:%M:%S")
                }
    def getInvoicesByDate(self, start, end, showProgress=True):
        """
        Return a list of Invoice objects for the specified time period
        
        The Invoice objects will correspond to Invoices as well as Creditmemos
        in the given time period

        Keyword arguments:
        start        -- start of the time period
        end          -- end of the time period
        showProgress -- whether or not to display a progress bar (default True)
        """
        out=[]
        if(showProgress):
            sys.stderr.write("Downloading Invoice List...\n")
            sys.stderr.flush()
        invoices=self.getInvoiceList(start, end)
        creditmemos=self.getCreditmemoList(start, end)
        if(showProgress):
            bar=progress.bar.IncrementalBar("Loading Invoices... (%(eta)ds)", max=len(invoices)+len(creditmemos));
        for i in invoices:
            out.append(self.getInvoice(i))
            bar.next() if(showProgress) else False
        for i in creditmemos:
            out.append(self.getCreditmemo(i))
            bar.next() if(showProgress) else False
        bar.finish() if(showProgress) else False
        return out
    def getInvoices(self, invoices, showProgress=True):
        """
        Return a list of Invoice objects, given a list of Invoice IDs

        Keyword arguments:
        invoices     -- a List of Invoice IDs
        showProgress -- whether or not to display a progress bar (default True)
        """
        out=[]
        if(showProgress):
            bar=progress.bar.IncrementalBar("Loading Invoices... (%(eta)ds)", max=len(invoices));
        for i in invoices:
            matches=re.match(r'^([+-]?)(1\d{8})$', i).groups()
            if(matches):
                if(matches[0] == "-"):
                    out.append(self.getCreditmemo(matches[1]))
                else:
                    out.append(self.getInvoice(matches[1]))
            bar.next() if(showProgress) else False
        bar.finish() if(showProgress) else False
        return out
    def getInvoiceList(self, start, end):
        """Return a list of Invoice IncrementIDs within the specified date range"""
        return [i["increment_id"] for i in self.api.sales_order_invoice.list({"created_at": self.__dateRange(start, end)})]
    def getCreditmemoList(self, start, end):
        """Return a list of Creditmemo IncrementIDs within the specified date range"""
        return [i["increment_id"] for i in self.api.sales_order_creditmemo.list({"created_at": self.__dateRange(start, end)})]
    def getInvoice(self, incrementId):
        """
        Return an Invoice object for the specified Invoice IncrementID
        
        The Invoices are cached, so the cost of calling repeatedly on the same
        IncrementID is minimal.
        """
        if(incrementId in self.invoices):
            return self.invoices[incrementId]
        self.invoices[incrementId]=Invoice(self.api.sales_order_invoice.info(incrementId), pst=self.pst, gst=self.gst, mage=self, refund=False)
        return self.invoices[incrementId]
    
    def getCreditmemo(self, incrementId):
        """
        Return an Invoice object for the specified Creditmemo IncrementID
        
        The Invoices are cached, so the cost of calling repeatedly on the same
        IncrementID is minimal.
        """
        if(incrementId in self.creditmemos):
            return self.creditMemos[incrementId]
        self.creditmemos[incrementId]=Invoice(self.api.sales_order_creditmemo.info(incrementId), pst=self.pst, gst=self.gst, mage=self, refund=True)
        return self.creditmemos[incrementId]
    
    def getOrder(self, incrementId):
        """Return a dictionary of data describing the specified Order IncrementID"""
        if(incrementId in self.orders):
            return self.orders[incrementId]
        self.orders[incrementId]=self.api.sales_order.info(incrementId)
        return self.orders[incrementId]
