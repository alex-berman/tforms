import GeoIP
import os
from gps import GPS

class IpLocator:
    def __init__(self):
        self._geo_ip = GeoIP.open("%s/GeoLiteCity.dat" % os.path.dirname(__file__),
                                  GeoIP.GEOIP_STANDARD)
        self._gps = GPS()

    def locate(self, addr):
        gir = self._geo_ip.record_by_addr(addr)
        if gir:
            x = self._gps.x(gir['longitude'])
            y = self._gps.y(gir['latitude'])
            return x, y
