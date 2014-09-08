from __future__ import unicode_literals
import re

import balanced

from rentmybike.models.users import User

from tests import email_generator, SystemTestCase
from psycopg2.tests.testutils import unittest


email_generator = email_generator()


class TestMerchantFlow(SystemTestCase):

    def test_anonymous_listing(self):
        email_address = 'krusty@balancedpayments.com'
        payload = self._guest_listing_payload(email_address)
        resp = self.client.post('/list', data=payload)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/list/1/complete', resp.data)

        # check locally
        user = User.query.filter(
            User.email_address == email_address).one()
        # NOTE: guest passwords currently disabled
        self.assertIsNone(user.password_hash)
#        self.assertTrue(user.check_password('ab'))

        # check in balanced
        account = user.balanced_account
        self.assertTrue('merchant' in account.roles)
        self.assertEqual(account.email_address, email_address)

    def test_authenticated_listing(self, email_address=None):
        email_address = email_address or 'bob@balancedpayments.com'
        self._create_user(email_address)
        payload = self._listing_payload()
        user = User.query.filter(User.email_address == email_address).one()
        resp = self.client.post('/list', data=payload)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/list/1/complete', resp.data)

        # check in balanced
        user = User.query.filter(
            User.email_address == email_address).one()
        account = user.balanced_account
        self.assertTrue('merchant' in account.roles)
        self.assertEqual(account.email_address, email_address)

    def test_anonymous_listing_with_bank_account(self):
        email_address = email_generator.next()
        payload = self._guest_listing_payload(email_address)
        bank_account = balanced.BankAccount(name='Myata Marketplace',
            account_number=321174851, bank_code=321174851
        ).save()
        payload['bank_account_uri'] = bank_account.uri
        resp = self.client.post('/list', data=payload)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/list/1/complete', resp.data)

        # check locally
        user = User.query.filter(
            User.email_address == email_address).one()
        # NOTE: guest passwords currently disabled
        self.assertIsNone(user.password_hash)
#        self.assertTrue(user.check_password('ab'))

        # check in balanced
        account = user.balanced_account
        self.assertTrue('merchant' in account.roles)
        self.assertEqual(account.email_address, email_address)
        self.assertTrue(
            [ba for ba in account.bank_accounts if bank_account.id in ba.uri]
        )

    def test_authenticated_listing_with_bank_account(self, email_address=None):
        email_address = email_address or email_generator.next()
        self._create_user(email_address)
        payload = self._listing_payload()
        bank_account = balanced.BankAccount(name='Bob Saget',
            account_number=321174851, bank_code=321174851
        ).save()
        payload['bank_account_uri'] = bank_account.uri
        user = User.query.filter(User.email_address == email_address).one()
        resp = self.client.post('/list', data=payload)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/list/1/complete', resp.data)

        # check in balanced
        user = User.query.filter(
            User.email_address == email_address).one()
        account = user.balanced_account
        self.assertTrue('merchant' in account.roles)
        self.assertEqual(account.email_address, email_address)
        self.assertTrue(
            [ba for ba in account.bank_accounts if bank_account.id in ba.uri]
        )

    def test_authenticated_listing_repeat_kyc(self):
        email_address = 'repeat@balancedpayments.com'
        self.test_authenticated_listing(email_address)
        data = {
            '_csrf_token': self.get_csrf_token(),
            }
        user = User.query.filter(User.email_address == email_address).one()
        resp = self.client.post('/list', data=data)
        self.assertEqual(resp.status_code, 302)
        self.assertIsNotNone(re.search(r'/list/\d+/confirm', resp.data))
        data = {
            '_csrf_token': self.get_csrf_token(),
            }
        user = User.query.filter(User.email_address == email_address).one()
        resp = self.client.post('/list', data=data)
        self.assertEqual(resp.status_code, 302)
        self.assertIsNotNone(re.search(r'/list/\d+/confirm', resp.data))

    def test_anonymous_listing_with_existing_merchant_account(self):
        email_address = email_generator.next()
        ogaccount = balanced.Marketplace.my_marketplace.create_merchant(
            **self._merchant_payload(email_address))
        payload = self._guest_listing_payload(email_address)
        resp = self.client.post('/list', data=payload)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/list/1/complete', resp.data)

        # check locally
        user = User.query.filter(
            User.email_address == email_address).one()
        # NOTE: guest passwords currently disabled
        self.assertIsNone(user.password_hash)
#        self.assertTrue(user.check_password('ab'))

        # check in balanced
        account = user.balanced_account
        self.assertTrue('merchant' in account.roles)
        self.assertEqual(account.email_address, email_address)
        self.assertEqual(ogaccount.uri, account.uri)

    def test_anonymous_listing_with_existing_buyer_account(self):
        email_address = email_generator.next()
        card = balanced.Card(
            card_number='4111111111111111',
            expiration_month=12,
            expiration_year=2020,
            security_code=123
        ).save()
        ogaccount = balanced.Marketplace.my_marketplace.create_buyer(
            email_address, card.uri,
        )

        payload = self._guest_listing_payload(email_address)
        resp = self.client.post('/list', data=payload)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/list/1/complete', resp.data)

        # check locally
        user = User.query.filter(
            User.email_address == email_address).one()
        # NOTE: guest passwords currently disabled
        self.assertIsNone(user.password_hash)
#        self.assertTrue(user.check_password('ab'))

        # check in balanced
        account = user.balanced_account
        self.assertTrue('merchant' in account.roles)
        self.assertTrue('buyer' in account.roles)
        self.assertEqual(account.email_address, email_address)
        self.assertEqual(ogaccount.uri, account.uri)
