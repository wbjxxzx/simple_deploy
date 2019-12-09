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
]

apis = [
    url(r'^api/microservice/$', views.ServiceApi.as_view(), name='api_microservice'),
    url(r'^api/microservice/(?P<pk>[0-9]+)/$', views.ServiceManageApi.as_view(), name='api_microservice_manage'),
    url(r'^api/microservice/(?P<service_id>[0-9]+)/versions/$', views.ServiceVersionApi.as_view(), name='api_microservice_versions'),

]

urlpatterns = pages + apis