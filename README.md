#mage-report

A quick Python hack to get the reports I needed out of Magento's SOAP API. One
cool thing it does is pretty reliably calculate PST and GST (we're in Manitoba,
Canada so we need that), which isn't really supposed to be possible over the
SOAP API. (It does this by basically duplicating Magento's tax logic, which is
an ugly approach but really the only option in this case)

##Requirements

- python2 (may work in 3 as well, not tested)
- `pip install terminaltables progress python-magento pytz` (you could do this
  in a virtualenv to avoid cluttering up your system)

##Installation

Not at this point. Just run it in the directory it comes in.

##Usage

`./mage-report <cmd> <year> <month>`

`cmd` can be `tables`, `invoices`, and `days`

- `tables` prints out a pretty ANSI table for each day of sales, with rows for
  each invoice and a total row for the day.
- `invoices` prints a CSV representation of each invoice (id, customer, date,
  total)
- `days` prints a CSV representation of each day of the month, including days
  with no sales (day, total pre-tax, total PST, total GST, total with tax)
