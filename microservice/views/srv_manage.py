# -*- coding: utf-8 -*-
from django.shortcuts import render

# Create your views here.

from django.views import generic
from django.http import JsonResponse
from django.core.paginator import Paginator
from microservice.models import *
from django.utils.timezone import localtime, utc, now
from django.db.models import Count
import time
import requests

class ServicePageView(generic.ListView):
    template_name = 'microservice/service.html'

    def get_queryset(self):
        pass


class ServiceApi(generic.View):
    def get(self, request):
        query = request.GET
        page = int(query.get('page', 1))
        limit = int(query.get('limit', 20))

        services = MicroService.objects.select_related('updated_by')
        paginator = Paginator(services, limit)
        pdata = paginator.page(page)

        data = [{
            'id': item.id,
            'name': item.name,
            'description': item.description,
            'language': item.language,
            'build_orig': item.build_orig,
            'build_url': item.build_url,
            'updated_by': item.updated_by.username,
            'updated': localtime(item.updated).strftime('%Y-%m-%d %H:%M:%S %Z'),
        } for item in pdata]

        return JsonResponse({
            'data': data,
            'count': services.count(),
            'code': 0,
        })

    def post(self, request):
        d = {}
        d['name'] = request.POST.get('name', '')
        d['language'] = request.POST.get('language', 'cpp')
        d['description'] = request.POST.get('description', '')
        d['build_orig'] = request.POST.get('build_orig', 'git')
        d['build_url'] = request.POST.get('build_url', '')

        if not d['name'] or not d['build_url']:
            return JsonResponse({'msg': '必填项不能为空'}, status=417)

        try:
            MicroService.objects.get(name=d['name'])
        except MicroService.DoesNotExist:
            d['created_by'] = request.user
            d['updated_by'] = request.user
            MicroService.objects.create(**d)
            return JsonResponse({}, status=201)
        else:
            return JsonResponse({'msg': '该服务已存在'}, status=409)


class ServiceManageApi(generic.View):
    def post(self, request, pk):
        params = request.POST
        d = {}
        d['description'] = params.get('description', '')
        d['language'] = params.get('language', '')
        d['build_url'] = params.get('build_url', '')
        d['updated_by'] = request.user
        d['updated'] = now()

        try:
            MicroService.objects.filter(pk=pk).update(**d)
        except MicroService.DoesNotExist:
            return JsonResponse({'msg': '资源不存在'}, status=404)
        return JsonResponse({})

    def delete(self, request, pk):
        svcs = MicroService.objects.annotate(num_versions=Count('microserviceversion')).filter(pk=pk)
        if not svcs:
            return JsonResponse({'msg': '资源不存在'}, status=404)
        if len(svcs) > 1:
            return JsonResponse({'msg': '数据错误'}, status=417)
        if svcs[0].num_versions != 0:
            return JsonResponse({'msg': '该服务有关联的版本, 不允许删除'}, status=417)
        svcs.delete()
        return JsonResponse({})


class ServiceVersionPageView(generic.DetailView):
    template_name = 'microservice/version.html'
    model = MicroService
    pk_url_kwarg = 'service_id'


class ServiceVersionApi(generic.View):
    def get(self, request, service_id):
        query = request.GET
        page = int(query.get('page', 1))
        limit = int(query.get('limit', 20))

        try:
            service = MicroService.objects.get(pk=service_id)
        except MicroService.DoesNotExist:
            return JsonResponse({'msg': '资源不存在'}, status=404)

        versions = MicroServiceVersion.objects.filter(microservice=service)
        paginator = Paginator(versions, limit)
        pdata = paginator.page(page)
        data = [{
            'id': item.id,
            'name': item.microservice.name,
            'language': item.microservice.language,
            'description': item.description,
            'version': item.version,
            'status': item.get_status_display(),
            'created_by': item.created_by.username,
            'created': item.created,
        } for item in pdata]

        return JsonResponse({
            'data': data,
            'count': versions.count(),
            'code': 0,
        })

    def post(self, request, service_id):
        ref = request.POST.get('branch', 'master').strip()
        desc = request.POST.get('description', '').strip()
        try:
            service = MicroService.objects.get(pk=service_id)
        except MicroService.DoesNotExist:
            return JsonResponse({'msg': '资源不存在'}, status=404)

        version = MicroServiceVersion.objects.create(
            microservice=service,
            version='building-' + str(time.time()),
            created_by=request.user,
            description=desc,
            ref=ref
        )

        build_params = {
            'variables[SERVICE_ID]': service.id,
            'variables[VERSION_ID]': version.id,
            'variables[SERVICE_NAME]': service.name,
            'variables[USERNAME]': request.user.username,
        }
        try:
            r = requests.post(service.build_url, data=build_params, timeout=10)
        except requests.exceptions.Timeout:
            return JsonResponse({'msg': '调用git 超时'}, status=417)

        if r.status_code >= 200 and r.status_code < 300:
            rdata = r.json()
            return JsonResponse(rdata, status=200)
        return JsonResponse({'msg': '创建任务失败{}'.format(r.content)})


class InstanceApi(generic.View):
    def get(self, request, service_id):
        pass


class VersionDeployPageView(generic.DetailView):
    template_name = 'microservice/version_deploy.html'
    model = MicroServiceVersion


class VersionDeployActionApi(generic.View):
    def get(self, request, service_id, action, pk):
        pass

    def post(self, request, service_id, action, pk):
        pass