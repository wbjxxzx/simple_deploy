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

]

urlpatterns = pages + apis