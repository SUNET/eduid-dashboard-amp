from eduid_am.exceptions import UserDoesNotExist


def attribute_fetcher(db, user_id):
    attributes = {}

    user = db.registered.find_one({'_id': user_id})
    if user is None:
        raise UserDoesNotExist("No user matching _id='%s'" % user_id)

    else:
        # white list of valid attributes for security reasons
        for attr in ('email', 'date', 'verified'):
            value = user.get(attr, None)
            if value is not None:
                attributes[attr] = value

        # This values must overwrite existent values
        for attr in ('screen_name', 'last_name', 'first_name', 'passwords'):
            value = user.get(attr, None)
            if value is not None:
                attributes[attr] = value

    return attributes
