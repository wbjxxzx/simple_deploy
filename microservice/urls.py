#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#

from django.conf.urls import url

from microservice import views

pages = [
    url(r'home', views.ServicePageView.as_view()),
    url(r'^service/(?P<service_id>[0-9]+)/versions/$',
        views.ServiceVersionPageView.as_view(),
        name='page_service_versions'),

    url(r'^service/versions/(?P<pk>[0-9]+)/(?P<action>[a-z]+)/$',
        views.VersionDeployPageView.as_view(),
        name='page_version_deploy'),

    url(r'^service/(?P<service_id>[0-9]+)/confs/$',
        views.ConfRevisionPageView.as_view(),
        name='page_conflist'),

    url(r'^service/(?P<service_id>[0-9]+)/confs/(?P<pk>[0-9]+)/$',
        views.ConfRevisionDetailPageView.as_view(),
        name='page_conf_detail'),

    url(r'^service/(?P<service_id>[0-9]+)/confs/diff/$',
        views.ConfDiffPageView.as_view(),
        name='page_conf_diff'),
]

apis = [
    url(r'^api/microservice/$', views.ServiceApi.as_view(), name='api_microservice'),
    url(r'^api/microservice/(?P<pk>[0-9]+)/$', views.ServiceManageApi.as_view(), name='api_microservice_manage'),
    url(r'^api/microservice/(?P<service_id>[0-9]+)/versions/$', views.ServiceVersionApi.as_view(), name='api_microservice_versions'),

    # 构建版本任务接收
    url(r'^microservice/task/receive/webhook/$', views.GitWebhookReceiver.as_view()),

    # 发布
    url(r'^api/microservice/(?P<service_id>[0-9]+)/inst/$', views.InstanceApi.as_view(), name='api_microservice_inst'),
    url(r'^api/microservice/(?P<service_id>[0-9]+)/deploy/(?P<action>[a-z]+)/version/(?P<pk>[0-9]+)/$',
        views.VersionDeployActionApi.as_view(),
        name='api_microservice_version_deploy_action'),
    url(r'^api/microservice/(?P<service_id>[0-9]+)/hosts/$',
        views.AvailableHostApi.as_view(),
        name='api_available_hosts'),
    url(r'^api/microservice/(?P<service_id>[0-9]+)/install/version/(?P<pk>[0-9]+)/$',
        views.VersionInstallApi.as_view(),
        name='api_microservice_version_install'),

    # 配置文件管理
    url(r'^api/microservice/(?P<service_id>[0-9]+)/confs/$',
        views.ConfRevisionApi.as_view(),
        name='api_microservice_confs'),

    url(r'^api/microservice/(?P<service_id>[0-9]+)/confs/delete/(?P<pk>[0-9]+)/$',
        views.ConfRevisionDeleteApi.as_view(),
        name='api_microservice_conf_delete'),

    url(r'^api/microservice/(?P<service_id>[0-9]+)/confs/desc/(?P<pk>[0-9]+)/$',
        views.ConfRevisionUpdateDescApi.as_view(),
        name='api_microservice_conf_desc'),

    url(r'^api/microservice/(?P<service_id>[0-9]+)/confs/(?P<pk>[0-9]+)/$',
        views.ConfRevisionDetailApi.as_view(),
        name='api_microservice_conf_detail'),

    url(r'^api/microservice/conf/validate/$',
        views.ContentValidatorApi.as_view(),
        name='api_microservice_conf_validate'),

    url(r'^api/microservice/(?P<service_id>[0-9]+)/conf/setdefault/$',
        views.ConfRevisionSetDefaultApi.as_view(),
        name='api_microservice_conf_set_default'),

    url(r'^api/microservice/(?P<service_id>[0-9]+)/conf/relateinsts/(?P<pk>[0-9]+)/$',
        views.ConfRevisionRelateInstsApi.as_view(),
        name='api_microservice_conf_related'),

    url(r'^api/microservice/(?P<service_id>[0-9]+)/conf/activeall/$',
        views.ConfRevisionActiveAllApi.as_view(),
        name='api_microservice_conf_active_all'),

    url(r'^api/microservice/(?P<service_id>[0-9]+)/confdiff/$',
        views.ConfDiffApi.as_view(),
        name='api_microservice_conf_diff'),
]

urlpatterns = pages + apis