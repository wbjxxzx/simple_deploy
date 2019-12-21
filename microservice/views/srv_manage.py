# -*- coding: utf-8 -*-
from django.shortcuts import render

# Create your views here.

from django.views import generic
from django.http import JsonResponse
from django.core.paginator import Paginator
from microservice.models import *
from django.utils.timezone import localtime, utc, now
from django.db.models import Count, ObjectDoesNotExist, Q
import time
import requests
import re


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
            'created': localtime(item.created).strftime('%Y-%m-%d %H:%M:%S %Z'),
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
        query = request.GET
        version_id = query.get('version_id')
        locked = query.get('locked')

        try:
            service = MicroService.objects.get(pk=service_id)
        except MicroService.DoesNotExist:
            return JsonResponse({'msg': '资源不存在'}, status=404)

        insts = MicroServiceInstance.objects.filter(microservice=service)
        if version_id:
            insts = insts.filter(version_id=version_id)

        insts = insts.select_related('version').select_related('host').select_related('updated_by')

        if locked is not None:
            lck = False if locked in ('0', 'false') else True
            insts = insts.filter(locked=lck)

        data = [{
            'id': item.id,
            'name': service.name,
            'language': service.language,
            'version': item.version.version,
            'host': ':'.join((item.host.hostname, item.host.ip)),
            'host_id': item.host_id,
            'port': item.port,
            'tag': item.tag,
            'weight': item.weight,
            'description': item.description,
            'status': item.status,
            'status_str': item.get_status_display(),
            'is_maintain': item.is_maintain,
            'updated_by': item.updated_by.username,
            'updated': localtime(item.updated).strftime('%Y-%m-%d %H:%M:%S %Z'),
        } for item in insts]

        return JsonResponse({
            'data': data,
            'count': insts.count(),
            'code': 0,
        })


class VersionDeployPageView(generic.DetailView):
    template_name = 'microservice/version_deploy.html'
    model = MicroServiceVersion


class VersionDeployActionApi(generic.View):
    def get(self, request, service_id, action, pk):
        if action not in ('upgrade', 'revert'):
            return JsonResponse({'msg': '仅支持 upgrade/revert', 'code': -1}, status=417)

        cur_id = int(pk)
        versions = MicroServiceVersion.objects.filter(
            microservice_id=service_id,
            status=BuildStatus.success.value
        ).order_by('-id')

        data = [{
            'id': item.id,
            'version': item.version,
            'enable': item.id > cur_id if action == 'upgrade' else cur_id > item.id,
        } for item in versions]

        return JsonResponse({
            'data': data,
            'count': versions.count(),
            'code': 0,
        })

    def post(self, request, service_id, action, pk):
        params = request.POST
        q = {}
        q['dest_version'] = params.get('dest_version', '')
        q['host'] = params.get('host', '')

        if not q['dest_version']:
            return JsonResponse({'msg': '版本号不能为空'}, status=417)

        if not q['host']:
            return JsonResponse({'msg': '主机不能为空'}, status=417)
        else:
            if q['host'] != 'all' and (not re.match(r'[0-9,]', q['host'])):
                return JsonResponse({'msg': '主机参数错误，请传入 all 或以逗号分隔的id值'}, status=417)

        # 先获取服务
        try:
            service = MicroService.objects.get(pk=service_id)
            insts = MicroServiceInstance.objects.select_related('host').select_related('version').filter(version__id=pk)
            dest_ver = MicroServiceVersion.objects.filter(microservice=service).get(pk=q['dest_version'])
        except ObjectDoesNotExist:
            return JsonResponse({'msg': '资源不存在'}, status=404)

        db_idset = req_idset = set([x.host_id for x in insts])
        if q['host'] != 'all':
            req_idset = set([int(x) for x in q['host'].split(',') if x])
        # 如果传入的主机id在 db 中不存在
        if req_idset - db_idset:
            return JsonResponse({'msg': '请发送正确的主机id'}, status=404)

        # 只更新db中存在 且未锁定 的主机id
        idset = db_idset & req_idset

        st = InstanceStatus.upgrading.value if action == 'upgrade' else InstanceStatus.reverting.value
        for inst in insts:
            if inst.host_id in idset and not inst.locked:
                d = {
                    'updated_by': request.user,
                    'updated': now(),
                    'status': st,
                    'locked': True,
                }
                print d
                MicroServiceInstance.objects.filter(pk=inst.id).update(**d)

        # TODO 发起任务

        return JsonResponse({})


class AvailableHostApi(generic.View):
    """
    获取当前服务所有可用主机列表  未部署服务的设置 enalbe: true
    """

    def get(self, request, service_id):
        deployed = MicroServiceInstance.objects.filter(microservice_id=service_id)
        deployed_id_set = set([v.host_id for v in deployed])

        data = [{
            'id': item.id,
            'ip': item.ip,
            'hostname': item.hostname,
            'enable': False if item.id in deployed_id_set else True
        } for item in Asset.objects.all()]

        return JsonResponse({
            'data': data,
            'count': len(data),
            'code': 0,
        })


class VersionInstallApi(generic.View):

    def post(self, request, service_id, pk):
        comma_host_ids = request.POST.get('host', '').strip()

        if not comma_host_ids:
            return JsonResponse({'msg': '主机不能为空'}, status=417)
        elif not re.match(r'[0-9,]', comma_host_ids):
            return JsonResponse({'msg': '请发送正确的主机id'}, status=417)

        try:
            service = MicroService.objects.get(pk=service_id)
            version = MicroServiceVersion.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return JsonResponse({'msg': '资源不存在'}, status=417)

        deployed_insts = MicroServiceInstance.objects.filter(microservice_id=service_id)
        idset = set([int(x) for x in comma_host_ids.split(',') if x])
        deployed_hosts = [x for x in deployed_insts if x.host_id in idset]

        if deployed_hosts:
            return JsonResponse({'msg': '主机{}已部署相关服务'.format(
                ','.join(x.host.ip for x in deployed_hosts)
            )}, status=417)

        q = Q()
        q.connector = 'OR'
        for _id in idset:
            q.children.append(('id', _id))
        hosts = Asset.objects.filter(q)

        if hosts.count() != len(idset):
            return JsonResponse({'msg': '请发送正确的主机id'}, status=417)

        installing_insts = []
        for host in hosts:
            d = {
                'microservice_id': service.id,
                'version_id': version.id,
                'host_id': host.id,
                'description': '{} instance'.format(service.name),
                'status': InstanceStatus.installing.value,
                'locked': True,
                'updated_by': request.user,
            }
            inst = MicroServiceInstance.objects.create(**d)
            installing_insts.append(inst.id)

        # TODO 发起任务

        return JsonResponse({})