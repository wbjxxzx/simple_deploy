#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#

from django.conf.urls import url

from microservice import views

urlpatterns = [
    url(r'^service/$', views.ServicePageView.as_view()),
]

apis = [
    url(r'^api/microservice/$', views.ServiceApi.as_view(), name='api_microservice'),
    # url(r'microservice/(?P<pk>[0-9]+)/$', views.ServiceManageApi.as_view(), name='api_microservice_manage'),

]

urlpatterns += apis