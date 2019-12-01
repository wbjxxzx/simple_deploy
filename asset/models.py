# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

# Create your models here.

class Asset(models.Model):
    hostname = models.CharField(max_length=64)
    ip = models.CharField(max_length=15)
