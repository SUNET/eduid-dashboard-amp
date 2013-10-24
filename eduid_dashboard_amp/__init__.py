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

    if 'norEduPersonNIN' in attributes_set:
        # The 'norEduPersonNIN' is a list of items like
        #   [{u'active': False,
        #     u'norEduPersonNIN': u'123456781234',
        #     u'verified': False}, ...]
        #
        # only return verified NINs, and only the NINs themselves
        old_nins = attributes_set['norEduPersonNIN']
        new_nins = [this['norEduPersonNIN'] for this in old_nins if this.get('verified') is True]
        attributes_set['norEduPersonNIN'] = new_nins

    attributes['$set'] = attributes_set

    return attributes
