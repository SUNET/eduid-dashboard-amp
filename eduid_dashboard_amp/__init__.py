from eduid_userdb.exceptions import UserDoesNotExist


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


def attribute_fetcher(db, user_id):
    attributes = {}

    user = db.profiles.find_one({'_id': user_id})
    if user is None:
        raise UserDoesNotExist("No user matching _id='%s'" % user_id)

    # white list of valid attributes for security reasons
    attributes_set = {}
    attributes_unset = {}
    for attr in WHITELIST_SET_ATTRS:
        value = value_filter(attr, user.get(attr, None))
        if value:
            attributes_set[attr] = value
        elif attr in WHITELIST_UNSET_ATTRS:
            attributes_unset[attr] = value

    attributes['$set'] = attributes_set
    if attributes_unset:
        attributes['$unset'] = attributes_unset

    return attributes
