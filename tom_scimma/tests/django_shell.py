#!/usr/bin/env python
# django_shell.py

import django
from django.core.management import call_command
from boot_django import boot_django, APP_NAME

boot_django()
call_command('shell_plus')
