#!/usr/bin/env python

import sys

try:

    # required now to setup the environment
    import django
    django.setup()

    from django.contrib.auth.models import User
    if User.objects.count() == 0:
        admin = User.objects.create_superuser('admin', 'aaron@cimolini.com', 'qwerasdf')
        admin.save()

except:
    pass

sys.exit()
