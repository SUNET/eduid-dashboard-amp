import bson
from freezegun import freeze_time
from datetime import datetime, date

from eduid_userdb.exceptions import UserDoesNotExist, UserHasUnknownData
from eduid_userdb.testing import MongoTestCase
from eduid_userdb.dashboard import DashboardUser
from eduid_dashboard_amp import attribute_fetcher, plugin_init
from eduid_am.celery import celery, get_attribute_manager


TEST_DB_NAME = 'eduid_dashboard_test'


class AttributeFetcherOldToNewUsersTests(MongoTestCase):

    def setUp(self):
        super(AttributeFetcherOldToNewUsersTests, self).setUp(celery, get_attribute_manager)
        self.plugin_context = plugin_init(celery.conf)

        for userdoc in self.amdb._get_all_docs():
            dashboard_user = DashboardUser(data = userdoc)
            self.plugin_context.dashboard_userdb.save(dashboard_user, check_sync=False)

        self.maxDiff = None

    def test_invalid_user(self):
        with self.assertRaises(UserDoesNotExist):
            attribute_fetcher(self.plugin_context, bson.ObjectId('0' * 24))

    def test_existing_user(self):
        _data = {
            'eduPersonPrincipalName': 'test-test',
            'mail': 'john@example.com',
            'mailAliases': [{
                'email': 'john@example.com',
                'verified': True,
                'added_timestamp': datetime.now()
            }],
            'mobile': [{
                'verified': True,
                'mobile': '+46700011336',
                'primary': True,
            }],
            'passwords': [{
                'id': bson.ObjectId('112345678901234567890123'),
                'salt': '$NDNv1H1$9c810d852430b62a9a7c6159d5d64c41c3831846f81b6799b54e1e8922f11545$32$32$',
            }],
        }
        user = DashboardUser(data = _data)
        self.plugin_context.dashboard_userdb.save(user)

        fetched_attributes = attribute_fetcher(self.plugin_context, user.user_id)
        expected_attributes = {
            '$set': {
                'mailAliases': [{
                    'email': 'john@example.com',
                    'verified': True,
                    'primary': True,
                    'created_ts': fetched_attributes['$set']['mailAliases'][0]['created_ts']
                }],
                'passwords': [{
                    'id': bson.ObjectId('112345678901234567890123'),
                    'salt': u'$NDNv1H1$9c810d852430b62a9a7c6159d5d64c41c3831846f81b6799b54e1e8922f11545$32$32$',
                }],
                'phone': [{
                    'verified': True,
                    'number': '+46700011336',
                    'primary': True,
                }],
            },
            '$unset': {
                'norEduPersonNIN': None,
                'nins': [],
                'mail': None,
                'mobile': None,
                'sn': None,
                'terminated': False
            }
        }
        self.assertDictEqual(fetched_attributes, expected_attributes)

    def test_malicious_attributes(self):
        _data = {
            'eduPersonPrincipalName': 'test-test',
            'mail': 'john@example.com',
            'mailAliases': [{
                'email': 'john@example.com',
                'verified': True,
            }],
            'mobile': [{
                'verified': True,
                'mobile': '+46700011336'
            }],
            'malicious': 'hacker',
            'passwords': [{
                'id': bson.ObjectId('112345678901234567890123'),
                'salt': '$NDNv1H1$9c810d852430b62a9a7c6159d5d64c41c3831846f81b6799b54e1e8922f11545$32$32$',
            }],
        }
        # Write bad entry into database
        user_id = self.plugin_context.dashboard_userdb._coll.insert(_data)

        with self.assertRaises(UserHasUnknownData):
            attribute_fetcher(self.plugin_context, user_id)

    def test_fillup_attributes(self):
        _data = {
            'eduPersonPrincipalName': 'test-test',
            'mail': 'john@example.com',
            'displayName': 'John',
            'mailAliases': [{
                'email': 'john@example.com',
                'verified': True,
            }],
            'mobile': [{
                'verified': True,
                'mobile': '+46700011336'
            }],
            'passwords': [{
                'id': bson.ObjectId('112345678901234567890123'),
                'salt': '$NDNv1H1$9c810d852430b62a9a7c6159d5d64c41c3831846f81b6799b54e1e8922f11545$32$32$',
            }],
        }

        user = DashboardUser(data = _data)
        self.plugin_context.dashboard_userdb.save(user)

        self.assertDictEqual(
            attribute_fetcher(self.plugin_context, user.user_id),
            {
                '$set': {
                    'mailAliases': [{
                        'email': 'john@example.com',
                        'verified': True,
                        'primary': True
                    }],
                    'displayName': 'John',
                    'passwords': [{
                        'id': bson.ObjectId('112345678901234567890123'),
                        'salt': '$NDNv1H1$9c810d852430b62a9a7c6159d5d64c41c3831846f81b6799b54e1e8922f11545$32$32$',
                    }],
                    'phone': [{
                        'verified': True,
                        'number': '+46700011336',
                        'primary': True
                    }],
                },
                '$unset': {
                    'norEduPersonNIN': None,
                    'nins': [],
                    'mail': None,
                    'mobile': None,
                    'sn': None,
                    'terminated': False
                }
            }
        )

        _data['displayName'] = 'John2'
        user = DashboardUser(data = _data)
        self.plugin_context.dashboard_userdb.save(user)

        self.assertEqual(
            attribute_fetcher(self.plugin_context,
                              user.user_id)['$set']['displayName'],
            'John2',
        )

    def test_append_attributes(self):
        self.maxDiff = None
        _data = {
            'eduPersonPrincipalName': 'test-test',
            'mail': 'john@example.com',
            'mailAliases': [{
                'email': 'john@example.com',
                'verified': True,
            }],
            'mobile': [{
                'verified': True,
                'mobile': '+46700011336',
                'primary': True
            }],
            'passwords': [{
                'id': bson.ObjectId('1' * 24),
                'salt': '456',
            }]
        }
        user = DashboardUser(data = _data)
        self.plugin_context.dashboard_userdb.save(user)

        actual_update = attribute_fetcher(self.plugin_context, user.user_id)
        expected_update = {
            '$set': {
                'mailAliases': [{
                    'email': 'john@example.com',
                    'verified': True,
                    'primary': True
                }],
                'phone': [{
                    'number': '+46700011336',
                    'verified': True,
                    'primary': True
                }],
                'passwords': [{
                    'id': bson.ObjectId('1' * 24),
                    'salt': u'456',
                }]
            },
            '$unset': {
                'norEduPersonNIN': None,
                'nins': [],
                'mail': None,
                'mobile': None,
                'sn': None,
                'terminated': False
            }
        }
        self.assertDictEqual(
            actual_update,
            expected_update
        )

        actual_update = attribute_fetcher(self.plugin_context, user.user_id)
        expected_update = {
            '$set': {
                'mailAliases': [{
                    'email': 'john@example.com',
                    'verified': True,
                    'primary': True
                }],
                'phone': [{
                    'number': '+46700011336',
                    'verified': True,
                    'primary': True
                }],
                'passwords': [{
                    'id': bson.ObjectId('1' * 24),
                    'salt': u'456',
                }]
            },
            '$unset': {
                'norEduPersonNIN': None,
                'nins': [],
                'mail': None,
                'mobile': None,
                'sn': None,
                'terminated': False
            }
        }
        # Don't repeat the password
        self.assertDictEqual(
            actual_update,
            expected_update
        )

        # Adding a new password
        _data['passwords'].append(
                {
                    'id': bson.ObjectId('2' * 24),
                    'salt': '456',
                }
        )
        user = DashboardUser(data = _data)
        self.plugin_context.dashboard_userdb.save(user)

        actual_update = attribute_fetcher(self.plugin_context, user.user_id)
        expected_update = {
            '$set': {
                'mailAliases': [{
                    'email': 'john@example.com',
                    'verified': True,
                    'primary': True
                }],
                'phone': [{
                    'number': '+46700011336',
                    'verified': True,
                    'primary': True
                }],
                'passwords': [{
                    'id': bson.ObjectId('1' * 24),
                    'salt': u'456',
                }, {
                    'id': bson.ObjectId('2' * 24),
                    'salt': u'456',
                }]
            },
            '$unset': {
                'norEduPersonNIN': None,
                'nins': [],
                'mail': None,
                'mobile': None,
                'sn': None,
                'terminated': False
            }
        }

        self.assertDictEqual(
            actual_update,
            expected_update
        )

    def test_NIN_normalization(self):
        _data = {
            'eduPersonPrincipalName': 'test-test',
            'mail': 'john@example.com',
            'mailAliases': [{
                'email': 'john@example.com',
                'verified': True,
            }],
            'mobile': [{
                'verified': True,
                'mobile': '+46700011336',
                'primary': True
            }],
            'norEduPersonNIN': [u'123456781235'],
            'passwords': [{
                'id': bson.ObjectId('112345678901234567890123'),
                'salt': '$NDNv1H1$9c810d852430b62a9a7c6159d5d64c41c3831846f81b6799b54e1e8922f11545$32$32$',
            }],
        }
        user = DashboardUser(data = _data)
        self.plugin_context.dashboard_userdb.save(user)
        # Test that the verified NIN is returned in a list
        attributes = attribute_fetcher(self.plugin_context, user.user_id)
        self.assertDictEqual(
            attributes,
            {
                '$set': {
                    'mailAliases': [{'email': 'john@example.com', 'verified': True, 'primary': True}],
                    'phone': [{'verified': True, 'number': '+46700011336', 'primary': True}],
                    'nins': [{'verified': True, 'number': '123456781235', 'primary': True}],
                    'passwords': [{
                        'id': bson.ObjectId('112345678901234567890123'),
                        'salt': u'$NDNv1H1$9c810d852430b62a9a7c6159d5d64c41c3831846f81b6799b54e1e8922f11545$32$32$',
                    }],
                },
                '$unset': {
                    'mail': None,
                    'mobile': None,
                    'norEduPersonNIN': None,
                    'sn': None,
                    'terminated': False
                }

            }
        )

    def test_NIN_unset(self):
        _data = {
            'eduPersonPrincipalName': 'test-test',
            'mail': 'test@example.com',
            'mailAliases': [{
                'email': 'test@example.com',
                'verified': True,
            }],
            'mobile': [{
                'verified': True,
                'mobile': '+46700011336',
                'primary': True
            }],
            'norEduPersonNIN': [],
            'passwords': [{
                'id': bson.ObjectId('112345678901234567890123'),
                'salt': '$NDNv1H1$9c810d852430b62a9a7c6159d5d64c41c3831846f81b6799b54e1e8922f11545$32$32$',
            }],
        }
        user = DashboardUser(data = _data)
        self.plugin_context.dashboard_userdb.save(user)
        # Test that a blank norEduPersonNIN is unset
        attributes = attribute_fetcher(self.plugin_context, user.user_id)
        self.assertDictEqual(
            attributes,
            {
                '$set': {
                    'mailAliases': [{'email': 'test@example.com', 'verified': True, 'primary': True}],
                    'phone': [{
                        'verified': True,
                        'number': '+46700011336',
                        'primary': True
                    }],
                    'passwords': [{
                        'id': bson.ObjectId('112345678901234567890123'),
                        'salt': u'$NDNv1H1$9c810d852430b62a9a7c6159d5d64c41c3831846f81b6799b54e1e8922f11545$32$32$',
                    }],
                    },
                '$unset': {
                    'norEduPersonNIN': None,
                    'nins': [],
                    'mobile': None,
                    'sn': None,
                    'mail': None,
                    'terminated': False
                }
            }
        )

    def test_mobile_unset(self):
        _data = {
            'eduPersonPrincipalName': 'test-test',
            'mail': 'test@example.com',
            'mailAliases': [{
                'email': 'test@example.com',
                'verified': True,
            }],
            'mobile': [],
            'norEduPersonNIN': [u'123456781235'],
            'passwords': [{
                'id': bson.ObjectId('112345678901234567890123'),
                'salt': '$NDNv1H1$9c810d852430b62a9a7c6159d5d64c41c3831846f81b6799b54e1e8922f11545$32$32$',
            }],
        }
        user = DashboardUser(data=_data)
        self.plugin_context.dashboard_userdb.save(user)
        # Test that a blank norEduPersonNIN is unset
        attributes = attribute_fetcher(self.plugin_context, user.user_id)
        self.assertDictEqual(
            attributes,
            {
                '$set': {
                    'mailAliases': [{'email': 'test@example.com', 'verified': True, 'primary': True}],
                    'passwords': [{
                        'id': bson.ObjectId('112345678901234567890123'),
                        'salt': '$NDNv1H1$9c810d852430b62a9a7c6159d5d64c41c3831846f81b6799b54e1e8922f11545$32$32$',
                    }],
                    'nins': [{'number': '123456781235', 'verified': True, 'primary': True}],
                },
                '$unset': {
                    'norEduPersonNIN': None,
                    'mobile': None,
                    'phone': None,
                    'sn': None,
                    'mail': None,
                    'terminated': False
                }
            }
        )

    @freeze_time(date.today())
    def test_terminated_set(self):
        now = datetime.now(tz=bson.tz_util.FixedOffset(0, 'UTC'))
        _data = {
            'eduPersonPrincipalName': 'test-test',
            'mail': 'test@example.com',
            'mailAliases': [{
                'email': 'test@example.com',
                'verified': True,
            }],
            'mobile': [],
            'norEduPersonNIN': [u'123456781235'],
            'passwords': [{
                'id': bson.ObjectId('112345678901234567890123'),
                'salt': '$NDNv1H1$9c810d852430b62a9a7c6159d5d64c41c3831846f81b6799b54e1e8922f11545$32$32$',
            }],
            'terminated': True,
        }
        user = DashboardUser(data=_data)
        self.plugin_context.dashboard_userdb.save(user)
        attributes = attribute_fetcher(self.plugin_context, user.user_id)
        self.assertDictEqual(
            attributes,
            {
                '$set': {
                    'mailAliases': [{'email': 'test@example.com', 'verified': True, 'primary': True}],
                    'passwords': [{
                        'id': bson.ObjectId('112345678901234567890123'),
                        'salt': '$NDNv1H1$9c810d852430b62a9a7c6159d5d64c41c3831846f81b6799b54e1e8922f11545$32$32$',
                    }],
                    'nins': [{'number': '123456781235', 'verified': True, 'primary': True}],
                    'terminated': now
                },
                '$unset': {
                    'norEduPersonNIN': None,
                    'mobile': None,
                    'phone': None,
                    'sn': None,
                    'mail': None,
                }
            }
        )

    def test_terminated_unset(self):
        _data = {
            'eduPersonPrincipalName': 'test-test',
            'mail': 'test@example.com',
            'mailAliases': [{
                'email': 'test@example.com',
                'verified': True,
            }],
            'mobile': [],
            'norEduPersonNIN': [u'123456781235'],
            'passwords': [{
                'id': bson.ObjectId('112345678901234567890123'),
                'salt': '$NDNv1H1$9c810d852430b62a9a7c6159d5d64c41c3831846f81b6799b54e1e8922f11545$32$32$',
            }],
            'terminated': datetime.now(tz=bson.tz_util.FixedOffset(0, 'UTC')),
        }
        user = DashboardUser(data=_data)
        self.plugin_context.dashboard_userdb.save(user)
        user.terminated = False
        self.plugin_context.dashboard_userdb.save(user)
        attributes = attribute_fetcher(self.plugin_context, user.user_id)
        self.assertDictEqual(
            attributes,
            {
                '$set': {
                    'mailAliases': [{'email': 'test@example.com', 'verified': True, 'primary': True}],
                    'passwords': [{
                        'id': bson.ObjectId('112345678901234567890123'),
                        'salt': u'$NDNv1H1$9c810d852430b62a9a7c6159d5d64c41c3831846f81b6799b54e1e8922f11545$32$32$',
                    }],
                    'nins': [{'number': '123456781235', 'verified': True, 'primary': True}],
                },
                '$unset': {
                    'norEduPersonNIN': None,
                    'mobile': None,
                    'phone': None,
                    'sn': None,
                    'mail': None,
                    'terminated': False
                }
            }
        )


class AttributeFetcherNewToNewUsersTests(MongoTestCase):

    def setUp(self):
        super(AttributeFetcherNewToNewUsersTests, self).setUp(celery, get_attribute_manager)
        self.plugin_context = plugin_init(celery.conf)

        for userdoc in self.amdb._get_all_docs():
            dashboard_user = DashboardUser(data = userdoc)
            self.plugin_context.dashboard_userdb.save(dashboard_user, check_sync=False)

        self.maxDiff = None

    def test_invalid_user(self):
        with self.assertRaises(UserDoesNotExist):
            attribute_fetcher(self.plugin_context, bson.ObjectId('0' * 24))

    def test_existing_user(self):
        now = datetime.now(tz=bson.tz_util.FixedOffset(0, 'UTC'))
        _data = {
            'eduPersonPrincipalName': 'test-test',
            'mailAliases': [{
                'email': 'john@example.com',
                'verified': True,
                'primary': True,
                'created_ts': now
            }],
            'phone': [{
                'verified': True,
                'number': '+46700011336',
                'primary': True
            }],
            'passwords': [{
                'id': bson.ObjectId('112345678901234567890123'),
                'salt': '$NDNv1H1$9c810d852430b62a9a7c6159d5d64c41c3831846f81b6799b54e1e8922f11545$32$32$',
            }],
        }
        user = DashboardUser(data = _data)
        self.plugin_context.dashboard_userdb.save(user)

        fetched_attributes = attribute_fetcher(self.plugin_context, user.user_id)
        expected_attributes = {
            '$set': {
                'mailAliases': [{
                    'email': 'john@example.com',
                    'verified': True,
                    'primary': True,
                    'created_ts': fetched_attributes['$set']['mailAliases'][0]['created_ts']
                }],
                'passwords': [{
                    'id': bson.ObjectId('112345678901234567890123'),
                    'salt': u'$NDNv1H1$9c810d852430b62a9a7c6159d5d64c41c3831846f81b6799b54e1e8922f11545$32$32$',
                }],
                'phone': [{
                    'verified': True,
                    'number': '+46700011336',
                    'primary': True
                }],
            },
            '$unset': {
                'mail': None,
                'norEduPersonNIN': None,
                'nins': [],
                'mobile': None,
                'sn': None,
                'terminated': False
            }
        }
        self.assertDictEqual(fetched_attributes, expected_attributes)

    def test_malicious_attributes(self):
        _data = {
            'eduPersonPrincipalName': 'test-test',
            'mailAliases': [{
                'email': 'john@example.com',
                'verified': True,
                'primary': True
            }],
            'mobile': [{
                'verified': True,
                'mobile': '+46700011336',
                'primary': True
            }],
            'malicious': 'hacker',
            'passwords': [{
                'id': bson.ObjectId('112345678901234567890123'),
                'salt': '$NDNv1H1$9c810d852430b62a9a7c6159d5d64c41c3831846f81b6799b54e1e8922f11545$32$32$',
            }],
        }
        # Write bad entry into database
        user_id = self.plugin_context.dashboard_userdb._coll.insert(_data)

        with self.assertRaises(UserHasUnknownData):
            attribute_fetcher(self.plugin_context, user_id)

    def test_fillup_attributes(self):
        _data = {
            'eduPersonPrincipalName': 'test-test',
            'displayName': 'John',
            'mailAliases': [{
                'email': 'john@example.com',
                'verified': True,
                'primary': True
            }],
            'mobile': [{
                'verified': True,
                'mobile': '+46700011336',
                'primary': True
            }],
            'passwords': [{
                'id': bson.ObjectId('112345678901234567890123'),
                'salt': '$NDNv1H1$9c810d852430b62a9a7c6159d5d64c41c3831846f81b6799b54e1e8922f11545$32$32$',
            }],
        }

        user = DashboardUser(data = _data)
        self.plugin_context.dashboard_userdb.save(user)

        self.assertDictEqual(
            attribute_fetcher(self.plugin_context, user.user_id),
            {
                '$set': {
                    'mailAliases': [{
                        'email': 'john@example.com',
                        'verified': True,
                        'primary': True
                    }],
                    'displayName': 'John',
                    'passwords': [{
                        'id': bson.ObjectId('112345678901234567890123'),
                        'salt': u'$NDNv1H1$9c810d852430b62a9a7c6159d5d64c41c3831846f81b6799b54e1e8922f11545$32$32$',
                    }],
                    'phone': [{
                        'verified': True,
                        'number': '+46700011336',
                        'primary': True
                    }],
                },
                '$unset': {
                    'norEduPersonNIN': None,
                    'nins': [],
                    'mail': None,
                    'mobile': None,
                    'sn': None,
                    'terminated': False
                }
            }
        )

        _data['displayName'] = 'John2'
        user = DashboardUser(data = _data)
        self.plugin_context.dashboard_userdb.save(user)

        self.assertEqual(
            attribute_fetcher(self.plugin_context,
                              user.user_id)['$set']['displayName'],
            'John2',
        )

    def test_append_attributes(self):
        self.maxDiff = None
        _data = {
            'eduPersonPrincipalName': 'test-test',
            'mailAliases': [{
                'email': 'john@example.com',
                'verified': True,
                'primary': True
            }],
            'phone': [{
                'verified': True,
                'number': '+46700011336',
                'primary': True
            }],
            'passwords': [{
                'id': bson.ObjectId('1' * 24),
                'salt': '456',
            }]
        }
        user = DashboardUser(data = _data)
        self.plugin_context.dashboard_userdb.save(user)

        actual_update = attribute_fetcher(self.plugin_context, user.user_id)
        expected_update = {
            '$set': {
                'mailAliases': [{
                    'email': 'john@example.com',
                    'verified': True,
                    'primary': True
                }],
                'phone': [{
                    'verified': True,
                    'number': '+46700011336',
                    'primary': True
                }],
                'passwords': [{
                    'id': bson.ObjectId('1' * 24),
                    'salt': u'456',
                }]
            },
            '$unset': {
                'norEduPersonNIN': None,
                'nins': [],
                'mail': None,
                'mobile': None,
                'sn': None,
                'terminated': False
            }
        }
        self.assertDictEqual(
            actual_update,
            expected_update
        )

        actual_update = attribute_fetcher(self.plugin_context, user.user_id)
        expected_update = {
            '$set': {
                'mailAliases': [{
                    'email': 'john@example.com',
                    'verified': True,
                    'primary': True
                }],
                'phone': [{
                    'verified': True,
                    'number': '+46700011336',
                    'primary': True
                }],
                'passwords': [{
                    'id': bson.ObjectId('1' * 24),
                    'salt': u'456',
                }]
            },
            '$unset': {
                'norEduPersonNIN': None,
                'nins': [],
                'mail': None,
                'mobile': None,
                'sn': None,
                'terminated': False
            }
        }
        # Don't repeat the password
        self.assertDictEqual(
            actual_update,
            expected_update
        )

        # Adding a new password
        _data['passwords'].append(
                {
                    'id': bson.ObjectId('2' * 24),
                    'salt': '456',
                }
        )
        user = DashboardUser(data = _data)
        self.plugin_context.dashboard_userdb.save(user)

        actual_update = attribute_fetcher(self.plugin_context, user.user_id)
        expected_update = {
            '$set': {
                'mailAliases': [{
                    'email': 'john@example.com',
                    'verified': True,
                    'primary': True
                }],
                'phone': [{
                    'verified': True,
                    'number': '+46700011336',
                    'primary': True
                }],
                'passwords': [{
                    'id': bson.ObjectId('1' * 24),
                    'salt': u'456',
                }, {
                    'id': bson.ObjectId('2' * 24),
                    'salt': u'456',
                }]
            },
            '$unset': {
                'norEduPersonNIN': None,
                'nins': [],
                'mail': None,
                'mobile': None,
                'sn': None,
                'terminated': False
            }
        }

        self.assertDictEqual(
            actual_update,
            expected_update
        )

    def test_NIN_normalization(self):
        _data = {
            'eduPersonPrincipalName': 'test-test',
            'mailAliases': [{
                'email': 'john@example.com',
                'verified': True,
                'primary': True
            }],
            'phone': [{
                'verified': True,
                'number': '+46700011336',
                'primary': True
            }],
            'nins': [{'number': '123456781235', 'verified': True, 'primary': True}],
            'passwords': [{
                'id': bson.ObjectId('112345678901234567890123'),
                'salt': '$NDNv1H1$9c810d852430b62a9a7c6159d5d64c41c3831846f81b6799b54e1e8922f11545$32$32$',
            }],
        }
        user = DashboardUser(data = _data)
        self.plugin_context.dashboard_userdb.save(user)
        # Test that the verified NIN is returned in a list
        attributes = attribute_fetcher(self.plugin_context, user.user_id)
        self.assertDictEqual(
            attributes,
            {
                '$set': {
                    'mailAliases': [{'email': 'john@example.com', 'verified': True, 'primary': True}],
                    'phone': [{'verified': True, 'number': '+46700011336', 'primary': True}],
                    'nins': [{'number': '123456781235', 'verified': True, 'primary': True}],
                    'passwords': [{
                        'id': bson.ObjectId('112345678901234567890123'),
                        'salt': u'$NDNv1H1$9c810d852430b62a9a7c6159d5d64c41c3831846f81b6799b54e1e8922f11545$32$32$',
                    }],
                },
                '$unset': {
                    'norEduPersonNIN': None,
                    'mobile': None,
                    'sn': None,
                    'mail': None,
                    'terminated': False
                }

            }
        )

    def test_NIN_unset(self):
        _data = {
            'eduPersonPrincipalName': 'test-test',
            'mailAliases': [{
                'email': 'test@example.com',
                'verified': True,
                'primary': True
            }],
            'mobile': [{
                'verified': True,
                'mobile': '+46700011336',
                'primary': True
            }],
            'nins': [],
            'passwords': [{
                'id': bson.ObjectId('112345678901234567890123'),
                'salt': '$NDNv1H1$9c810d852430b62a9a7c6159d5d64c41c3831846f81b6799b54e1e8922f11545$32$32$',
            }],
        }
        user = DashboardUser(data = _data)
        self.plugin_context.dashboard_userdb.save(user)
        # Test that a blank norEduPersonNIN is unset
        attributes = attribute_fetcher(self.plugin_context, user.user_id)
        self.assertDictEqual(
            attributes,
            {
                '$set': {
                    'mailAliases': [{'email': 'test@example.com', 'verified': True,  'primary': True}],
                    'phone': [{
                        'verified': True,
                        'number': '+46700011336',
                        'primary': True
                    }],
                    'passwords': [{
                        'id': bson.ObjectId('112345678901234567890123'),
                        'salt': '$NDNv1H1$9c810d852430b62a9a7c6159d5d64c41c3831846f81b6799b54e1e8922f11545$32$32$',
                    }],
                    },
                '$unset': {
                    'norEduPersonNIN': None,
                    'nins': [],
                    'mail': None,
                    'mobile': None,
                    'sn': None,
                    'terminated': False
                }
            }
        )

    def test_mobile_unset(self):
        _data = {
            'eduPersonPrincipalName': 'test-test',
            'mailAliases': [{
                'email': 'test@example.com',
                'verified': True,
                'primary': True
            }],
            'mobile': [],
            'nins': [{'number': '123456781235', 'verified': True, 'primary': True}],
            'passwords': [{
                'id': bson.ObjectId('112345678901234567890123'),
                'salt': '$NDNv1H1$9c810d852430b62a9a7c6159d5d64c41c3831846f81b6799b54e1e8922f11545$32$32$',
            }],
        }
        user = DashboardUser(data=_data)
        self.plugin_context.dashboard_userdb.save(user)
        # Test that a blank norEduPersonNIN is unset
        attributes = attribute_fetcher(self.plugin_context, user.user_id)
        self.assertDictEqual(
            attributes,
            {
                '$set': {
                    'mailAliases': [{'email': 'test@example.com', 'verified': True, 'primary': True}],
                    'passwords': [{
                        'id': bson.ObjectId('112345678901234567890123'),
                        'salt': '$NDNv1H1$9c810d852430b62a9a7c6159d5d64c41c3831846f81b6799b54e1e8922f11545$32$32$',
                    }],
                    'nins': [{'number': '123456781235', 'verified': True, 'primary': True}],
                },
                '$unset': {
                    'norEduPersonNIN': None,
                    'mail': None,
                    'mobile': None,
                    'phone': None,
                    'sn': None,
                    'terminated': False
                }
            }
        )

    @freeze_time(date.today())
    def test_terminated_set(self):
        now = datetime.now(tz=bson.tz_util.FixedOffset(0, 'UTC'))
        _data = {
            'eduPersonPrincipalName': 'test-test',
            'mailAliases': [{
                'email': 'test@example.com',
                'verified': True,
                'primary': True
            }],
            'phone': [],
            'nins': [{'number': '123456781235', 'verified': True, 'primary': True}],
            'passwords': [{
                'id': bson.ObjectId('112345678901234567890123'),
                'salt': '$NDNv1H1$9c810d852430b62a9a7c6159d5d64c41c3831846f81b6799b54e1e8922f11545$32$32$',
            }],
            'terminated': True,
        }
        user = DashboardUser(data=_data)
        self.plugin_context.dashboard_userdb.save(user)
        attributes = attribute_fetcher(self.plugin_context, user.user_id)
        self.assertDictEqual(
            attributes,
            {
                '$set': {
                    'mailAliases': [{'email': 'test@example.com', 'verified': True, 'primary': True}],
                    'passwords': [{
                        'id': bson.ObjectId('112345678901234567890123'),
                        'salt': u'$NDNv1H1$9c810d852430b62a9a7c6159d5d64c41c3831846f81b6799b54e1e8922f11545$32$32$',
                    }],
                    'nins': [{'number': '123456781235', 'verified': True, 'primary': True}],
                    'terminated': now
                },
                '$unset': {
                    'norEduPersonNIN': None,
                    'mail': None,
                    'mobile': None,
                    'phone': None,
                    'sn': None,
                }
            }
        )

    def test_terminated_unset(self):
        _data = {
            'eduPersonPrincipalName': 'test-test',
            'mailAliases': [{
                'email': 'test@example.com',
                'verified': True,
                'primary': True
            }],
            'mobile': [],
            'nins': [{'number': '123456781235', 'verified': True, 'primary': True}],
            'passwords': [{
                'id': bson.ObjectId('112345678901234567890123'),
                'salt': '$NDNv1H1$9c810d852430b62a9a7c6159d5d64c41c3831846f81b6799b54e1e8922f11545$32$32$',
            }],
            'terminated': datetime.now(tz=bson.tz_util.FixedOffset(0, 'UTC')),
        }
        user = DashboardUser(data=_data)
        self.plugin_context.dashboard_userdb.save(user)
        user.terminated = False
        self.plugin_context.dashboard_userdb.save(user)
        attributes = attribute_fetcher(self.plugin_context, user.user_id)
        self.assertDictEqual(
            attributes,
            {
                '$set': {
                    'mailAliases': [{'email': 'test@example.com', 'verified': True, 'primary': True}],
                    'passwords': [{
                        'id': bson.ObjectId('112345678901234567890123'),
                        'salt': '$NDNv1H1$9c810d852430b62a9a7c6159d5d64c41c3831846f81b6799b54e1e8922f11545$32$32$',
                    }],
                    'nins': [{'number': '123456781235', 'verified': True, 'primary': True}],
                },
                '$unset': {
                    'norEduPersonNIN': None,
                    'mail': None,
                    'mobile': None,
                    'phone': None,
                    'sn': None,
                    'terminated': False
                }
            }
        )
