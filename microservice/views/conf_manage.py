#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#

import re
import yaml
import json
from microservice.models import *
from django.views import generic
from django.http import JsonResponse
from django.db.models import Count, ObjectDoesNotExist, Max, Q
from django.core.paginator import Paginator
from django.utils.timezone import localtime, utc, now
from io import BytesIO
from ConfigParser import RawConfigParser


def style_adapter(_type, content):
    if _type in ('conf', 'ini'):
        f = BytesIO(content.encode('utf-8'))
        try:
            cf = RawConfigParser()
            cf.readfp(f)
        except Exception:
            raise ValueError('文件格式不正确')
    elif _type == 'json':
        try:
            cf = json.loads(content)
        except:
            raise ValueError('文件格式不正确')
    elif _type == 'yml':
        f = BytesIO(content.encode('utf-8'))
        try:
            cf = yaml.load(f)
        except Exception:
            raise ValueError('文件格式不正确')

    return cf

def validate_conf(name, _type, content):
    # 校验内容格式  返回原始内容 和 conf 对象
    errors = ''
    if not name:
        errors = '配置文件名称不能为空'
        return False, errors, None

    if not name.endswith(_type):
        errors = '文件名称必须以 .{} 结尾'.format(_type)
        return False, errors, None

    if not content or not content.strip():
        errors = '配置文件内容不能为空'
        return False, errors, None

    try:
        cf = style_adapter(_type, content)
    except ValueError:
        errors = "文件[{}]格式不正确".format(name)
        return False, errors, None

    return True, content, cf


class ContentValidatorApi(generic.View):
    """
    配置文件内容校验
    """

    def post(self, request):
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        _type = data.get('type', 'conf').strip()
        path = data.get('path', '/home/').strip()
        # 不做任何修改 返回页面的原始内容
        content = data.get('content', '')

        is_valid, err, _ = validate_conf(name, _type, content)
        if not is_valid:
            return JsonResponse({'msg': err}, status=417)
        return JsonResponse({})


class ConfRevisionPageView(generic.DetailView):
    """
    配置文件管理页面视图
    """
    template_name = 'microservice/conf.html'
    model = MicroService
    pk_url_kwarg = 'service_id'


class ConfRevisionApi(generic.View):
    """
    配置文件操作 获取列表、添加
    修改配置内容时创建一个新的修订号  也是发送到该视图
    """

    def get(self, request, service_id):
        query = request.GET
        page = query.get('page', 1)
        limit = query.get('limit', 20)

        try:
            service = MicroService.objects.get(pk=service_id)
        except MicroService.DoesNotExist:
            return JsonResponse({'msg': '资源不存在'}, status=404)

        # select_related 使用 inner join 关联外键 并缓存 再次访问时就不用查询  用于sql优化
        revisions = ConfRevision.objects.filter(service=service)\
            .select_related('created_by')\
            .annotate(num_insts=Count('microserviceinstance'))

        paginator = Paginator(revisions, limit)
        pdata = paginator.page(page)

        data = [{
            'id': item.id,
            'name': service.name,
            'revision': item.revision,
            'description': item.description,
            'is_default': item.is_default,
            'created_by': item.created_by.username,
            'num_insts': item.num_insts,
            'created': localtime(item.created).strftime('%Y-%m-%d %H:%M:%S %Z'),
        } for item in pdata]

        return JsonResponse({
            'data': data,
            'total': paginator.count
        })

    def post(self, request, service_id):
        try:
            service = MicroService.objects.get(id=service_id)
        except MicroService.DoesNotExist:
            return JsonResponse({'msg': '关联的服务不存在'}, status=404)

        data = json.loads(request.body)
        files = data.get('files', [])
        description = data.get('description', '')
        name_set = set()
        details = []
        for file in files:
            name = file.get('name', '').strip()
            if name in name_set:
                return JsonResponse({'msg': '文件名重复'}, status=409)

            name_set.add(name)
            _type = file.get('type', 'conf').strip()
            path = file.get('path', '/home/').strip()
            raw_content = file.get('content', '')
            # 校验文件内容 返回错误或 cf 对象
            is_valid, raw_or_err, cf_obj = validate_conf(name, _type, raw_content)
            if not is_valid:
                return JsonResponse({'msg': raw_or_err}, status=417)

            details.append({
                'name': name,
                'type': _type,
                'path': path,
                'content': raw_or_err, # 原始 conf 内容
                'created_by': request.user
            })

        revision_info = ConfRevision.objects.filter(service=service).aggregate(max_revision=Max('revision'))
        max_revision = revision_info['max_revision']
        max_revision = 0 if not max_revision else max_revision

        d = {
            'service': service,
            'revision': max_revision + 1,
            'created_by': request.user,
            'description': description,
        }

        revi = ConfRevision.objects.create(**d)
        for conf in details:
            tmp = conf.copy()
            tmp['rev'] = revi
            ConfDetail.objects.create(**tmp)

        return JsonResponse({})


class ConfRevisionDeleteApi(generic.View):
    """
    删除一个配置修订号 和与之关联的文件
    """
    def delete(self, request, service_id, pk):

        try:
            revision = ConfRevision.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return JsonResponse({'msg': '资源不存在'}, status=404)

        if revision.microserviceinstance_set.count():
            return JsonResponse({'msg': '当前配置有关联的实例，不能删除'}, status=417)

        ConfDetail.objects.filter(rev=revision).delete()
        revision.delete()

        return JsonResponse({})


class ConfRevisionUpdateDescApi(generic.View):
    """
    由于每次对配置文件的修改都会产生一个新的修订号, 这里做一个单独的接口来修改描述
    """
    def post(self, request, service_id, pk):
        description = request.POST.get('description', '').strip()
        if not description:
            return JsonResponse({'msg': '请输入描述'}, status=417)

        d = {
            'description': description,
        }
        ConfRevision.objects.filter(pk=pk).update(**d)
        return JsonResponse({})



class ConfRevisionDetailPageView(generic.DetailView):
    """
    配置文件详细页面视图
    """
    template_name = 'microservice/confdetail.html'
    model = MicroService
    pk_url_kwarg = 'service_id'


class ConfRevisionDetailApi(ConfRevisionApi):
    """
    配置文件详情  继承 post 方法
    """

    def get(self, request, service_id, pk):
        try:
            rev = ConfRevision.objects.get(pk=pk)
        except ConfRevision.DoesNotExist:
            return JsonResponse({'msg': '资源不存在'}, status=404)

        files = []
        for conf in rev.confdetail_set.all():
            files.append({
                'title': conf.name,
                'type': conf.type,
                'content': conf.content,
            })

        return JsonResponse({
            'items': files,
            'description': rev.description
        })



class ConfRevisionSetDefaultApi(generic.View):
    """
    设置为默认配置
    """
    def post(self, request, service_id):
        revision = request.POST.get('revision')
        if not revision:
            return JsonResponse({'msg': '请提交正确的修订号'}, status=417)

        try:
            svcobj = MicroService.objects.get(id=service_id)
        except MicroService.DoesNotExist:
            return JsonResponse({'msg': '数据错误: 关联的服务不存在'}, status=404)

        ConfRevision.objects.filter(service=svcobj, is_default=True).update(is_default=False)
        ConfRevision.objects.filter(service=svcobj, revision=revision).update(is_default=True)

        return JsonResponse({})


class ConfRevisionActiveAllApi(generic.View):
    """
    应用某个配置文件版本到所有实例
    """

    def post(self, request, service_id):
        revision = request.POST.get('revision')
        if not revision:
            return JsonResponse({'msg': '请提交正确的修订号'}, status=417)

        try:
            svcobj = MicroService.objects.get(id=service_id)
            revobj = ConfRevision.objects.get(service=svcobj, revision=revision)
            insts = MicroServiceInstance.objects.filter(microservice=svcobj)
        except ObjectDoesNotExist:
            return JsonResponse({'msg': '数据错误: 关联的服务不存在'}, status=404)

        insts.update(conf_revision=revobj)

        return JsonResponse({})



class ConfRevisionRelateInstsApi(generic.View):
    """
    关联配置到多个实例
    """
    def post(self, request, service_id, pk):
        comma_inst_ids = request.POST.get('ids', '')

        try:
            revobj = ConfRevision.objects.get(pk=pk)
        except ConfRevision.DoesNotExist:
            return JsonResponse({'msg': '请提交正确的修订号'}, status=417)

        try:
            svcobj = MicroService.objects.get(id=service_id)
        except MicroService.DoesNotExist:
            return JsonResponse({'msg': '关联的服务不存在'}, status=404)

        if not re.match(r'[0-9,]', comma_inst_ids):
            return JsonResponse({'msg': '主机参数错误, 请传入逗号分隔的实例id值'}, status=417)

        # 该服务的全部实例
        insts = MicroServiceInstance.objects.filter(microservice=svcobj).select_related('host')
        idset = set([int(x) for x in comma_inst_ids.split(',') if x])
        relate_insts = []
        for inst in insts:
            # 在关联列表且当前修订号不等于传入的修订号
            if inst.id in idset and inst.conf_revision_id != pk:
                relate_insts.append(inst)

        if not relate_insts:
            return JsonResponse({})

        # 查找关联的实例并更新
        for inst in relate_insts:
            MicroServiceInstance.objects.filter(pk=inst.id).update(conf_revision_id=pk)

        return JsonResponse({})


class ConfDiffPageView(generic.DetailView):
    """
    配置文件对比页面视图
    """
    template_name = 'microservice/confdiff.html'
    model = MicroService
    pk_url_kwarg = 'service_id'


class ConfDiffApi(generic.View):
    """
    配置文件对比
    """

    def get(self, request, service_id):
        query = request.GET
        commastr = query.get('revision', '').strip()

        try:
            service = MicroService.objects.get(pk=service_id)
        except MicroService.DoesNotExist:
            return JsonResponse({'msg': '资源不存在'}, status=404)

        q = Q()
        q.connector = 'OR'

        for revision in commastr.split(','):
            q.children.append(('revision', revision))

        # 小版本在前
        revisions = ConfRevision.objects.filter(service=service).filter(q).order_by('revision')
        if revisions.count() != 2:
            return JsonResponse({'msg': '数据异常'}, status=417)

        data = []
        for rev in revisions:
            files = []
            for conf in ConfDetail.objects.filter(rev=rev):
                files.append({
                    'title': conf.name,
                    'content': conf.content
                })
            data.append({
                'revision': rev.revision,
                'items': files
            })

        return JsonResponse({
            'data': data
        })
