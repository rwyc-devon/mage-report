#!/usr/bin/python
from datetime import datetime, timedelta
import pytz
from decimal import *
class Invoice:
    def __init__(self, data, pst, gst, mage, refund=False):
        """
        Create a new Invoice Object

        Keyword arguments:
        data   -- the dict returned by the Magento API for an Invoice or Creditmemo
        pst    -- the PST rate
        gst    -- the GST rate
        mage   -- a Mage instance, used to look up additional information needed to calculate taxes
        refund -- whether this is a refund (creditmemo), in which case all the amounts are negated
        """
        #get order (needed for customer info and, bizarrely, tax info (province)
        order         = mage.getOrder(data["order_increment_id"])
        #set date
        gmt           = pytz.timezone("GMT")
        self.date     = gmt.localize(datetime.strptime(data["created_at"], "%Y-%m-%d %H:%M:%S"))
        self.tz       = mage.tz
        #Pretty basic fields
        discount = Decimal(data["base_discount_amount"] or 0)
        self.subtotal = Decimal(data["base_subtotal"])
        self.shipping = Decimal(data["base_shipping_amount"])
        self.preTax   = self.subtotal+self.shipping+discount
        self.tax      = Decimal(data["base_tax_amount"])
        self.total    = Decimal(data["base_grand_total"])
        self.id       = data["increment_id"]
        #if pre-tax total is 0, then this is an "adjustment".
        if(self.preTax==0):
            self.subtotal=self.total
            self.preTax=self.total
        #set customer name
        self.customer=""
        if "customer_firstname" in order and "customer_lastname" in order:
            self.customer= \
                (order["customer_firstname"] or "") + \
                " " + \
                (order["customer_lastname"] or "") \
        #calculate PST
        self.pst      = Decimal(0)
        if(order["shipping_address"] and order["shipping_address"]["region"] == "Manitoba"):
            for i in data["items"]:
                self.pst+=Item(i, pst=pst, gst=gst).pst
        #calculate GST
        self.gst      = self.tax - self.pst
        #negate everything if this is a refund
        if(refund):
            self.negate()
    def __cmp__(self, other):
        return cmp(self.date, other.date)

    def negate(self):
        """Negate all the money amounts (for example if this is a refund"""
        self.subtotal   = self.subtotal.copy_negate()
        self.shipping   = self.shipping.copy_negate()
        self.preTax     = self.preTax.copy_negate()
        self.tax        = self.tax.copy_negate()
        self.pst        = self.pst.copy_negate()
        self.gst        = self.gst.copy_negate()
        self.total      = self.total.copy_negate()
    
    @property
    def localDT(self):
        """Return a DateTime for this invoice, converted to local time"""
        return self.date.astimezone(self.tz)

    @property
    def localDateStr(self):
        """
        Return the date string for this invoice, converted to local time
        
        The format will be YYYY-MM-DD, as all dates should
        """
        return self.date.astimezone(self.tz).strftime("%Y-%m-%d")

    @property
    def localTimeStr(self):
        """
        Return the time string for this invoice, converted to local time
        
        The format will be HH:MM:SS.
        """
        return self.date.astimezone(self.tz).strftime("%H:%M:%S")

    @property
    def dayOfMonth(self):
        """
        Return an integer representing the day of month for this invoice
        """
        return self.localDT.day

class Item:
    def __init__(self, data, pst, gst):
        self.tax=Decimal(data["base_tax_amount"] or 0)
        self.total=Decimal(data["base_row_total"] or 0)
        self.pstRate=Decimal(pst)
        self.gstRate=Decimal(gst)

    @property
    def pst(self):
        if(
                self.tax and
                self.total and
                round(self.tax / self.total * 100) == self.pstRate + self.gstRate
                ):
            return self.tax * (self.pstRate / (self.pstRate + self.gstRate))
        else:
            return Decimal(0)

    @property
    def gst(self):
        return self.tax-self.pst()
