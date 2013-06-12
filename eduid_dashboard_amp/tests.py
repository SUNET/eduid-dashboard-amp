import datetime

import bson

from eduid_am.exceptions import UserDoesNotExist
from eduid_am.tests import MongoTestCase
from eduid_dashboard_amp import attribute_fetcher


TEST_DB_NAME = 'eduid_dashboard_test'


class AttributeFetcherTests(MongoTestCase):

    def test_invalid_user(self):
        self.assertRaises(UserDoesNotExist, attribute_fetcher, self.conn['test'],
                          bson.ObjectId('000000000000000000000000'))

    def test_existing_user(self):
        user_id = self.conn['test'].profiles.insert({
            'email': 'john@example.com',
            'date': datetime.datetime(2013, 4, 1, 10, 10, 20),
            'verified': True,
        })
        self.assertEqual(
            attribute_fetcher(self.conn['test'], user_id),
            {'email': 'john@example.com',
             'date': datetime.datetime(2013, 4, 1, 10, 10, 20, 0),
             'verified': True}
        )

    def test_malicious_attributes(self):
        user_id = self.conn['test'].profiles.insert({
            'email': 'john@example.com',
            'date': datetime.datetime(2013, 4, 1, 10, 10, 20),
            'verified': True,
            'malicious': 'hacker',
        })
        # Malicious attributes are not returned
        self.assertEqual(
            attribute_fetcher(self.conn['test'], user_id),
            {'email': 'john@example.com',
             'date': datetime.datetime(2013, 4, 1, 10, 10, 20, 0),
             'verified': True}
        )

    def test_fillup_attributes(self):
        user_id = self.conn['test'].profiles.insert({
            'email': 'john@example.com',
            'screen_name': 'John',
            'date': datetime.datetime(2013, 4, 1, 10, 10, 20),
            'verified': True,
        })
        self.assertEqual(
            attribute_fetcher(self.conn['test'], user_id),
            {'email': 'john@example.com',
             'screen_name': 'John',
             'date': datetime.datetime(2013, 4, 1, 10, 10, 20, 0),
             'verified': True}
        )

        self.conn['test'].profiles.update({
            'email': 'john@example.com',
        }, {
            '$set': {
                'screen_name': 'John2',
            }
        })

        self.assertEqual(
            attribute_fetcher(self.conn['test'], user_id)['screen_name'],
            'John2',
        )

    def test_append_attributes(self):
        user_id = self.conn['test'].profiles.insert({
            'email': 'john@example.com',
            'date': datetime.datetime(2013, 4, 1, 10, 10, 20),
            'verified': True,
            'passwords': [{
                'id': '123',
                'salt': '456',
            }]
        })
        self.assertEqual(
            attribute_fetcher(self.conn['test'], user_id),
            {'email': 'john@example.com',
             'date': datetime.datetime(2013, 4, 1, 10, 10, 20, 0),
             'verified': True,
             'passwords': [{
                 'id': u'123',
                 'salt': u'456',
             }]}
        )

        # Don't repeat the password
        self.assertEqual(
            attribute_fetcher(self.conn['test'], user_id),
            {'email': 'john@example.com',
             'date': datetime.datetime(2013, 4, 1, 10, 10, 20, 0),
             'verified': True,
             'passwords': [{
                 'id': u'123',
                 'salt': u'456',
             }]}
        )

        # Adding a new password
        self.conn['test'].profiles.update({
            'email': 'john@example.com',
        }, {
            '$push': {
                'passwords': {
                    'id': '123a',
                    'salt': '456',
                }
            }
        })

        self.assertEqual(
            attribute_fetcher(self.conn['test'], user_id),
            {'email': 'john@example.com',
             'date': datetime.datetime(2013, 4, 1, 10, 10, 20, 0),
             'verified': True,
             'passwords': [{
                 'id': u'123',
                 'salt': u'456',
             }, {
                 'id': u'123a',
                 'salt': u'456',
             }]}
        )
