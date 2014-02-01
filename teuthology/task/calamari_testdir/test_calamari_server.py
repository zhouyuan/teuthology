#!/usr/bin/env python

import argparse
import datetime
import sys
import json
import uuid
import unittest
from http_client import AuthenticatedHttpClient

global client

class RestTest(unittest.TestCase):
    'Base class for all tests here; get class\'s data'

    def setUp(self):
        method = getattr(self, 'method', 'GET')
        self.response = get_object(method, self.uri)

    def tearDown(self):
        self.response = None

class TestUserMe(RestTest):

    def __init__(self, test_name):
        self.uri = 'user/me'
        super(self.__class__, self).__init__(test_name)

    def test_me(self):
        self.assertEqual(self.response['username'], 'admin')

class TestCluster(RestTest):

    def __init__(self, test_name):
        self.uri = 'cluster'
        super(self.__class__, self).__init__(test_name)

    def test_id(self):
        self.assertEqual(self.response[0]['id'], 1)

    def test_times(self):
        for t in (
            self.response[0]['cluster_update_time'],
            self.response[0]['cluster_update_attempt_time'],
        ):
            self.assertTrue(is_datetime(t))

    def test_api_base_url(self):
        api_base_url = self.response[0]['api_base_url']
        self.assertTrue(api_base_url.startswith('http'))
        self.assertIn('api/v0.1', api_base_url)

class TestHealth(RestTest):

    def __init__(self, test_name):
        self.uri = 'cluster/1/health'
        super(self.__class__, self).__init__(test_name)

    def test_cluster(self):
        self.assertEqual(self.response['cluster'], 1)

    def test_times(self):
        for t in (
            self.response['cluster_update_time'],
            self.response['added'],
        ):
            self.assertTrue(is_datetime(t))

    def test_report_and_overall_status(self):
        self.assertIn('report', self.response)
        self.assertIn('overall_status', self.response['report'])

class TestHealthCounters(RestTest):

    def __init__(self, test_name):
        self.uri = 'cluster/1/health_counters'
        super(self.__class__, self).__init__(test_name)

    def test_cluster(self):
        self.assertEqual(self.response['cluster'], 1)

    def test_time(self):
        self.assertTrue(is_datetime(self.response['cluster_update_time']))

    def test_existence(self):
        for section in ('pg', 'mon', 'osd'):
            for counter in ('warn', 'critical', 'ok'):
                count = self.response[section][counter]['count']
                self.assertIsInstance(count, int)
        self.assertIsInstance(self.response['pool']['total'], int)

    def test_mds_sum(self):
        count = self.response['mds']
        self.assertEqual(
            count['up_not_in'] + count['not_up_not_in'] + count['up_in'],
            count['total']
        )

class TestSpace(RestTest):

    def __init__(self, test_name):
        self.uri = 'cluster/1/space'
        super(self.__class__, self).__init__(test_name)

    def test_cluster(self):
        self.assertEqual(self.response['cluster'], 1)

    def test_times(self):
        for t in (
            self.response['cluster_update_time'],
            self.response['added'],
        ):
            self.assertTrue(is_datetime(t))

    def test_space(self):
        for size in ('free_bytes', 'used_bytes', 'capacity_bytes'):
            self.assertIsInstance(self.response['space'][size], int)
            self.assertGreater(self.response['space'][size], 0)

    def test_report(self):
        for size in ('total_used', 'total_space', 'total_avail'):
            self.assertIsInstance(self.response['report'][size], int)
            self.assertGreater(self.response['report'][size], 0)

class TestOSD(RestTest):
    def __init__(self, test_name):
        self.uri = 'cluster/1/osd'
        super(self.__class__, self).__init__(test_name)

    def test_cluster(self):
        self.assertEqual(self.response['cluster'], 1)

    def test_times(self):
        for t in (
            self.response['cluster_update_time'],
            self.response['added'],
        ):
            self.assertTrue(is_datetime(t))

    def test_number_of_osds(self):
        self.assertEqual(len(self.response['osds']), 2)

    def test_osd_uuid(self):
        for o in self.response['osds']:
            uuidobj = uuid.UUID(o['uuid'])
            self.assertEqual(str(uuidobj), o['uuid'])

    def test_osd_pools(self):
        for o in self.response['osds']:
            self.assertIsInstance(o['pools'], list)
            self.assertIsInstance(o['pools'][0], basestring)

    def test_osd_up_in(self):
        for o in self.response['osds']:
            for flag in ('up', 'in'):
                self.assertIn(o[flag], (0, 1))

    def test_osd_0(self):
        osd0 = get_object('GET', 'cluster/1/osd/0')['osd']
        for field in osd0.keys():
            if not field.startswith('cluster_update_time'):
                self.assertEqual(self.response['osds'][0][field], osd0[field])

class TestPool(RestTest):
    def __init__(self, test_name):
        self.uri = 'cluster/1/pool'
        super(self.__class__, self).__init__(test_name)

    def test_cluster(self):
        for p in self.response:
            self.assertEqual(p['cluster'], 1)

    def test_fields_are_ints(self):
        for p in self.response:
            for field in ('id', 'used_objects', 'used_bytes'):
                self.assertIsInstance(p[field], int)

    def test_name_is_str(self):
        for p in self.response:
            self.assertIsInstance(p['name'], basestring)

    def test_pool_0(self):
        poolid = self.response[0]['id']
        pool = get_object('GET', 'cluster/1/pool/{id}'.format(id=poolid))
        self.assertEqual(self.response[0], pool)

class TestServer(RestTest):

    def __init__(self, test_name):
        self.uri = 'cluster/1/server'
        super(self.__class__, self).__init__(test_name)

    def test_ipaddr(self):
        for s in self.response:
            octets = s['addr'].split('.')
            self.assertEqual(len(octets), 4)
            for octetstr in octets:
                octet = int(octetstr)
                self.assertIsInstance(octet, int)
                self.assertGreaterEqual(octet, 0)
                self.assertLessEqual(octet, 255)

    def test_hostname_name_strings(self):
        for s in self.response:
            for field in ('name', 'hostname'):
                self.assertIsInstance(s[field], basestring)

    def test_services(self):
        for s in self.response:
            self.assertIsInstance(s['services'], list)
            for service in s['services']:
                self.assertIn(service['type'], ('osd', 'mon', 'mds'))

#
# Utility functions
#

DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'

def is_datetime(t):
    datetime.datetime.strptime(t, DATETIME_FORMAT)
    return True

def get_object(method, url):
    'Return Python object decoded from JSON response to method/url'
    return client.request(method, url).json()

def parse_args():
    p = argparse.ArgumentParser('Test Calamari server')
    p.add_argument(
        '-u', '--uri',
        required=True,
        help='URI of REST server to test'
    )
    return p.parse_known_args()

if __name__ == '__main__':
    cmdargs, unittest_args = parse_args()
    uri = cmdargs.uri
    if not uri.endswith('/'):
        uri += '/'
    if not uri.endswith('api/v1/'):
        uri += 'api/v1/'
    client = AuthenticatedHttpClient(uri, 'admin', 'admin')
    client.login()

    sys.argv = [sys.argv[0]]
    sys.argv.extend(unittest_args)
    unittest.main()
