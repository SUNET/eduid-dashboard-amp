from eduid_userdb.exceptions import UserDoesNotExist
from eduid_userdb.dashboard import DashboardUserDB

WHITELIST_SET_ATTRS = (
    'givenName',
    'sn',
    'displayName',
    'photo',
    'preferredLanguage',
    'mail',
    'date',  # last modification

    # TODO: Arrays must use put or pop, not set, but need more deep refacts
    'norEduPersonNIN',
    'eduPersonEntitlement',
    'mobile',
    'mailAliases',
    'postalAddress',
    'passwords',
)

WHITELIST_UNSET_ATTRS = (
    'mail',
    'norEduPersonNIN',
    'mailAliases',
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


def plugin_init(db_uri, am_conf):
    """
    Create a private context for this plugin.

    Whatever is returned by this function will get passed to attribute_fetcher() as
    the `context' argument.

    @param db_uri: Database URI from the Attribute Manager.
    @am_conf: Attribute Manager configuration data.

    @type db_uri: str or unicode
    @type am_conf: dict
    """
    return DashboardAMPContext(db_uri)


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

    user = context.dashboard_userdb.get_user_by_id(user_id)
    if user is None:
        raise UserDoesNotExist("No user matching _id='%s'" % user_id)

    user_dict = user.to_dict(old_userdb_format=True)

    # white list of valid attributes for security reasons
    attributes_set = {}
    attributes_unset = {}
    for attr in WHITELIST_SET_ATTRS:
        value = value_filter(attr, user_dict.get(attr, None))
        if value:
            attributes_set[attr] = value
        elif attr in WHITELIST_UNSET_ATTRS:
            attributes_unset[attr] = value

    attributes['$set'] = attributes_set
    if attributes_unset:
        attributes['$unset'] = attributes_unset

    return attributes
