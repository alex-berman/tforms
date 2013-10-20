# -*- coding: utf-8 -*-

import unittest
from ip_locator import IpLocator

class IpLocatorTest(unittest.TestCase):
    def setUp(self):
        self.ip_locator = IpLocator()

    def test_locate_using_GeoIP(self):
        addr = '94.1.203.100'
        expected_result = (0.49111111097865634, 0.18916666242811417, u'Edinburgh')
        self.assertEqual(expected_result, self.ip_locator.locate(addr))

    def test_locate_using_db_extension(self):
        addr = '81.234.35.62'
        expected_result = (0.5332408333333334, 0.17935166666666666, u'Göteborg')
        self.assertEqual(expected_result, self.ip_locator.locate(addr))
