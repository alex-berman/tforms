# -*- coding: utf-8 -*-

import GeoIP
import os
from gps import GPS

DB_EXTENSION = {
    "81.234.35.62": {
        "longitude": 11.9667,
        "latitude": 57.7167,
        "city": u"Göteborg"
        },
    "37.250.35.48": {
        "longitude": 18.05,
        "latitude": 59.3333,
        "city": u"Stockholm"
        },
    "83.185.62.143": {
        "longitude": 18.05,
        "latitude": 59.3333,
        "city": u"Stockholm"
        },
    "93.182.133.11": {
        "longitude": 13.1833,
        "latitude": 55.7,
        "city": u"Lund"
        },
    "83.190.165.146": {
        "longitude": 17.92,
        "latitude": 59.45,
        "city": u"Kista"
        },
    "82.182.78.82": {
        "longitude": 20.25,
        "latitude": 63.83,
        "city": u"Umeå"
        },
    "46.246.123.125": {
        "longitude": 18.05,
        "latitude": 59.3333,
        "city": u"Stockholm"
        },
    "193.91.189.8": {
        "longitude": 10.63,
        "latitude": 59.9,
        "city": u"Fornebu"
        },
    }

class IpLocator:
    def __init__(self):
        self._geo_ip = GeoIP.open("%s/GeoLiteCity.dat" % os.path.dirname(__file__),
                                  GeoIP.GEOIP_STANDARD)
        self._gps = GPS()

    def locate(self, addr):
        record = self._geo_ip.record_by_addr(addr)
        if record:
            if record['city']:
                return self._location_tuple_from_record(record, coding="unicode_escape")
            elif addr in DB_EXTENSION:
                return self._location_tuple_from_record(DB_EXTENSION[addr])
            else:
                print "WARNING: unknown city for IP %s (GeoIP reports coordinates %r, %r)" % (
                    addr, record['longitude'], record['latitude'])
                return record
        else:
            print "WARNING: unknown location IP %s" % addr

    def _location_tuple_from_record(self, record, coding=None):
        x = self._gps.x(record['longitude'])
        y = self._gps.y(record['latitude'])
        place_name = record['city']
        if place_name and coding:
            place_name = place_name.decode(coding)
        return x, y, place_name
