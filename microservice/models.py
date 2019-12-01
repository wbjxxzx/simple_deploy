# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.conf import settings

# Create your models here.

class MicroService(models.Model):
    LANGUAGE_TYPE = (
        ('cpp', 'cpp'),
        ('go', 'go'),
        ('python', 'python'),
        ('other', 'other')
    )

    name = models.CharField(u'服务名称', max_length=64)
    language = models.CharField(u'语言类型', max_length=16, choices=LANGUAGE_TYPE)
    build_orig = models.CharField(u'构建来源', max_length=16, default='git')
    build_url = models.CharField(u'构建地址', max_length=128)
    description = models.CharField(max_length=256, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='created_by', on_delete=models.DO_NOTHING)
    updated = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='updated_by', on_delete=models.DO_NOTHING)

    class Meta:
        db_table = 'micro_service'
        unique_together = (('name', ), )
        ordering = ['-created']

from enum import Enum, unique
@unique
class BuildStatus(Enum):
    pending = 0
    building = 1
    success = 2
    timeout = 3
    failed = 4
    duplicate = 5


class MicroServiceVersion(models.Model):
    BUILD_STATUS = tuple([(v.value, k) for k, v in BuildStatus.__members__.items()])

    microservice = models.ForeignKey(MicroService, on_delete=models.DO_NOTHING)
    version = models.CharField(u'版本', max_length=48)
    description = models.CharField(max_length=128, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING)
    status = models.PositiveSmallIntegerField(choices=BUILD_STATUS, default=1)
    file_path = models.FilePathField(u'程序包存放路径', max_length=128, null=True, blank=True)
    ref = models.CharField(u'构建分支', max_length=64, default='master')

    class Meta:
        db_table = 'micro_service_version'
        unique_together = (('microservice', 'version'), )


@unique
class InstanceStatus(Enum):
    running = 0
    installing = 1
    upgrading = 2
    reverting = 3
    deleting = 4
    install_failed = 11
    upgrade_failed = 12
    revert_failed = 13
    delete_failed = 14


from asset.models import Asset
class MicroServiceInstance(models.Model):
    STATUS = tuple([(v.value, k) for k, v in InstanceStatus.__members__.items()])

    microservice = models.ForeignKey(MicroService, on_delete=models.DO_NOTHING)
    version = models.ForeignKey(MicroServiceVersion, on_delete=models.DO_NOTHING)
    host = models.ForeignKey(Asset, on_delete=models.DO_NOTHING)
    port = models.IntegerField(u'端口号', null=True, blank=True)
    tag = models.CharField(u'标签', max_length=64, null=True, blank=True)
    weight = models.PositiveSmallIntegerField(u'权重', default=100)
    description = models.CharField(max_length=128, null=True, blank=True)
    updated = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING)
    status = models.PositiveSmallIntegerField(u'实例状态', choices=STATUS, default=0)
    locked = models.BooleanField(u'操作锁定', default=False)
    is_maintain = models.BooleanField(u'是否维护中', default=False) # 保留

    class Meta:
        db_table = 'micro_service_instance'
        ordering = ['-updated']


