from eduid_am.exceptions import UserDoesNotExist


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


def attribute_fetcher(db, user_id):
    attributes = {}

    user = db.profiles.find_one({'_id': user_id})
    if user is None:
        raise UserDoesNotExist("No user matching _id='%s'" % user_id)

    # white list of valid attributes for security reasons
    attributes_set = {}
    for attr in WHITELIST_SET_ATTRS:
        value = user.get(attr, None)
        if value is not None:
            attributes_set[attr] = value

    attributes['$set'] = attributes_set

    return attributes
