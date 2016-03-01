from eduid_userdb.exceptions import UserDoesNotExist
from eduid_userdb.dashboard import DashboardUserDB
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

WHITELIST_SET_ATTRS = (
    'givenName',
    'surname',
    'displayName',
    'preferredLanguage',
    'mail',

    # TODO: Arrays must use put or pop, not set, but need more deep refacts
    'norEduPersonNIN',
    'eduPersonEntitlement',
    'phone_numbers',
    'mailAliases',
    'passwords',
    'letter_proofing_data',
    'terminated',
)

WHITELIST_UNSET_ATTRS = (
    'mail',
    'norEduPersonNIN',
    'mailAliases',
    'phone_numbers',
)


def value_filter(attr, value):
    if value:
        # Check it we need to filter values for this attribute
        #if attr == 'norEduPersonNIN':
        #   value = filter_nin(value)
        pass
    return value


def filter_nin(value):
    """
    :param value: dict
    :return: list

    This function will compile a users verified NINs to a list of strings.
    """
    result = []
    for item in value:
        verified = item.get('verfied', False)
        if verified and type(verified) == bool:  # Be sure that it's not something else that evaluates as True in Python
            result.append(item['nin'])
    return result


class DashboardAMPContext(object):
    """
    Private data for this AM plugin.
    """

    def __init__(self, db_uri):
        self.dashboard_userdb = DashboardUserDB(db_uri)


def plugin_init(am_conf):
    """
    Create a private context for this plugin.

    Whatever is returned by this function will get passed to attribute_fetcher() as
    the `context' argument.

    :am_conf: Attribute Manager configuration data.

    :type am_conf: dict

    :rtype: DashboardAMPContext
    """
    return DashboardAMPContext(am_conf['MONGO_URI'])


def attribute_fetcher(context, user_id):
    """
    Read a user from the Dashboard private userdb and return an update
    dict to let the Attribute Manager update the use in the central
    eduid user database.

    :param context: Plugin context, see plugin_init above.
    :param user_id: Unique identifier

    :type context: DashboardAMPContext
    :type user_id: ObjectId

    :return: update dict
    :rtype: dict
    """

    attributes = {}
    logger.debug('Trying to get user with _id: {} from {}.'.format(user_id, context.dashboard_userdb))
    user = context.dashboard_userdb.get_user_by_id(user_id)
    logger.debug('User: {} found.'.format(user))
    user_dict = user.to_dict(old_userdb_format=False)

    # white list of valid attributes for security reasons
    attributes_set = {}
    attributes_unset = {}
    for attr in WHITELIST_SET_ATTRS:
        value = value_filter(attr, user_dict.get(attr, None))
        if value:
            attributes_set[attr] = value
        elif attr in WHITELIST_UNSET_ATTRS:
            attributes_unset[attr] = value

    logger.debug('Will set attributes: {}'.format(attributes_set))
    logger.debug('Will remove attributes: {}'.format(attributes_unset))

    attributes['$set'] = attributes_set
    if attributes_unset:
        attributes['$unset'] = attributes_unset

    return attributes
