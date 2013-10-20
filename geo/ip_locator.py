# -*- coding: utf-8 -*-

import GeoIP
import os
from gps import GPS

DB_EXTENSION = {
    "81.234.35.": {
        "longitude": 11.9667,
        "latitude": 57.7167,
        "city": u"Göteborg"
        },
    "37.250.35.": {
        "longitude": 18.05,
        "latitude": 59.3333,
        "city": u"Stockholm"
        },
    "83.185.62.": {
        "longitude": 18.05,
        "latitude": 59.3333,
        "city": u"Stockholm"
        },
    "93.182.133.": {
        "longitude": 13.1833,
        "latitude": 55.7,
        "city": u"Lund"
        },
    "83.190.165.": {
        "longitude": 17.92,
        "latitude": 59.45,
        "city": u"Kista"
        },
    "193.14.105.": {
        "longitude": 17.92,
        "latitude": 59.45,
        "city": u"Kista"
        },
    "193.14.26.": {
        "longitude": 17.92,
        "latitude": 59.45,
        "city": u"Kista"
        },
    "82.182.78.": {
        "longitude": 20.25,
        "latitude": 63.83,
        "city": u"Umeå"
        },
    "46.246.123.": {
        "longitude": 18.05,
        "latitude": 59.3333,
        "city": u"Stockholm"
        },
    "193.91.189.": {
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
            else:
                extension_record = self._look_up_in_db_extension(addr)
                if extension_record:
                    return self._location_tuple_from_record(extension_record)
                else:
                    return self._location_tuple_from_record(record)
        else:
            print "WARNING: unknown location IP %s" % addr

    def _look_up_in_db_extension(self, addr):
        addr_without_last_part = self._strip_last_addr_part(addr)
        try:
            return DB_EXTENSION[addr_without_last_part]
        except KeyError:
            return None

    def _strip_last_addr_part(self, addr):
        return ".".join(addr.split(".")[0:3]) + "."

    def _location_tuple_from_record(self, record, coding=None):
        x = self._gps.x(record['longitude'])
        y = self._gps.y(record['latitude'])
        place_name = record['city']
        if place_name and coding:
            place_name = place_name.decode(coding)
        return x, y, place_name
