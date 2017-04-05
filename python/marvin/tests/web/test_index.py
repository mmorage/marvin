# !usr/bin/env python2
# -*- coding: utf-8 -*-
#
# Licensed under a 3-clause BSD license.
#
# @Author: Brian Cherinka
# @Date:   2017-02-12 20:46:42
# @Last modified by:   Brian Cherinka
# @Last Modified time: 2017-04-02 20:11:35

from __future__ import print_function, division, absolute_import
from marvin.tests.web import MarvinWebTester, MarvinFrontEnd
from marvin import config, marvindb
from flask import session, url_for
import unittest
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys


class TestIndexFront(MarvinFrontEnd):

    def setUp(self):
        super(TestIndexFront, self).setUp()

    def test_stuff(self):
        self.assertIn('Marvin', self.driver.title)

    def test_image(self):
        self.driver.find_element_by_id("image_link").click()
        time.sleep(1)
        self.assertIn('random', self.driver.current_url)

    def test_search(self):
        self.driver.find_element_by_id("search_link").click()
        time.sleep(1)
        self.assertIn('Search', self.driver.title)
        self.assertIn('search', self.driver.current_url)
        results = self.driver.find_elements(By.ID, "search_results")
        self.assertFalse(results)
        self.driver.find_element_by_id("searchbox").send_keys('nsa.z < 0.1')
        self.driver.find_element_by_id("searchbox").send_keys(Keys.RETURN)
        results = self.driver.find_elements(By.ID, "search_results")
        self.assertTrue(results)
        table = self.driver.find_elements(By.ID, "searchtablediv")
        self.assertTrue(table)


class TestIndexPage(MarvinWebTester):

    render_templates = False

    def setUp(self):
        super(TestIndexPage, self).setUp()
        self.blue = 'index_page'
        config.setRelease('MPL-5')
        self.release = config.release

    def test_assert_index_template_used(self):
        url = self.get_url('Marvin:index')
        self._load_page('get', url)
        self.assertEqual('', self.data)
        self.assert_template_used('index.html')


class TestDb(TestIndexPage):

    def test_db_works(self):
        url = self.get_url('Marvin:database')
        self._load_page('get', url, params={'release': self.release})
        data = {'plate': 7443}
        self._assert_webjson_success(data)

    def test_db_post_fails(self):
        url = self.get_url('Marvin:database')
        self._load_page('post', url, params={'release': self.release})
        self.assert405(self.response, 'allowed method should be get')


class TestSelectMPL(TestIndexPage):

    def _select_mpl(self, release, drpver, dapver):
        url = self.get_url('selectmpl')
        self._load_page('post', url, params={'release': release})
        data = {'current_release': release, 'current_drpver': drpver, 'current_dapver': dapver}
        self._assert_webjson_success(data)
        self._release_in_session(data)

    def test_select_mpl5(self):
        self._select_mpl('MPL-5', 'v2_0_1', '2.0.2')

    def test_select_mpl4(self):
        self._select_mpl('MPL-4', 'v1_5_1', '1.1.1')

    def test_select_mpl2(self):
        self._select_mpl('MPL-2', 'v1_2_0', None)

    def _release_in_session(self, data):
        with self.client as c:
            with c.session_transaction() as sess:
                sess['release'] = data['current_release']
                sess['drpver'] = data['current_drpver']
                sess['dapver'] = data['current_dapver']


class TestGetGalIdList(TestIndexPage):

    def test_getgalid_success(self):
        url = self.get_url('getgalidlist')
        self._load_page('post', url, params={'release': self.release})
        data = ['8485', '8485-1901', '7443', '7443-12701', '1-209232', '12-98126']
        self.assert200(self.response, message='response status should be 200 for ok')
        self.assertListIn(data, self.json)

    def test_getgalid_fail(self):
        marvindb.datadb = None
        url = self.get_url('getgalidlist')
        self._load_page('post', url, params={'release': self.release})
        data = ['']
        self.assert200(self.response, message='response status should be 200 for ok')
        self.assertListEqual(data, self.json)


class TestGalIdSelect(TestIndexPage):

    def _get_galid(self, name, galid, redirect_url):
        data = {'galid': galid, 'release': self.release}
        url = self.get_url('galidselect')
        self._load_page('get', url, params=data)
        self.assert_redirects(self.response, redirect_url, 'page should be redirected to {0} page'.format(name))

    def test_get_plate(self):
        self._get_galid('plate', self.plate, url_for('plate_page.Plate:get', plateid=self.plate))

    def test_get_plateifu(self):
        self._get_galid('galaxy', self.plateifu, url_for('galaxy_page.Galaxy:get', galid=self.plateifu))

    def test_get_mangaid(self):
        self._get_galid('galaxy', self.mangaid, url_for('galaxy_page.Galaxy:get', galid=self.mangaid))

    def test_get_none(self):
        self._get_galid('main', 'galname', url_for('index_page.Marvin:index'))


class TestLogin(TestIndexPage):

    @unittest.SkipTest
    def test_login_success(self):
        data = {'username': 'sdss', 'password': 'password', 'release': self.release}
        exp = {'ready': True, 'status': 1, 'message': 'Logged in as sdss. ', 'membername': 'SDSS User'}
        self._login(data, exp)

    def test_no_input(self):
        data = {'username': '', 'password': '', 'release': self.release}
        exp = {'ready': False, 'status': -1, 'message': ''}
        self._login(data, exp)

    def test_wrong_password(self):
        data = {'username': 'sdss', 'password': 'password', 'release': self.release}
        exp = {'ready': False, 'status': 0, 'message': 'Failed login for sdss. Please retry.', 'membername': 'Unknown user'}
        self._login(data, exp)

    def test_wrong_username(self):
        data = {'username': 'bac29', 'password': 'password', 'release': self.release}
        exp = {'ready': False, 'status': 0, 'message': 'Failed login for bac29. Username unrecognized.', 'membername': 'Unknown user'}
        self._login(data, exp)

    def _login(self, data, exp):
        url = self.get_url('login')
        self._load_page('post', url, params=data)
        self.assert200(self.response, 'response status should be 200 for ok')
        self.assertEqual(exp['status'], self.response.json['result']['status'])
        self.assertEqual(exp['message'], self.response.json['result']['message'])
        if 'membername' in exp:
            self.assertEqual(exp['membername'], self.response.json['result']['membername'])

if __name__ == '__main__':
    verbosity = 2
    unittest.main(verbosity=verbosity)
