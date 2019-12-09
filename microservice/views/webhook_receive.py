#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from microservice.models import MicroServiceVersion, BuildStatus
from django.http import HttpResponse
from django.views import generic

"""
pipeline 返回结果部分
 'object_attributes': {
   'before_sha': '0000000000000000000000000000000000000000',
   'created_at': '2019-12-09 08:53:34 UTC',
   'detailed_status': 'passed', # pending running passed failed
   'duration': 69,
   'finished_at': '2019-12-09 08:54:56 UTC',
   'id': 123,
   'ref': 'master',
   'sha': 'ad02bfded9fed8a1ae478bc088378827c485cf94',
   'stages': ['prepare', 'build', 'deploy'],
   'status': 'success', # pending running success failed
   'tag': False,
   'variables': [
                 {'key': 'VERSION_ID', 'value': '3'},
                 {'key': 'SERVICE_ID', 'value': '2'},
                 {'key': 'SERVICE_NAME', 'value': 'A'},
                 {'key': 'USERNAME', 'value': 'zhangsan'}
               ],
    },
 """
class GitWebhookReceiver(generic.View):
    def post(self, request):
        data = json.loads(request.body)
        object_attributes = data.get('object_attributes', {})
        task_id = object_attributes.get('id')
        return self._git_build_result(task_id, object_attributes)

    def _git_build_result(self, task_id, object_attributes):
        status = object_attributes.get('status', '')
        if status in ('pending', 'running', 'canceled'):
            return HttpResponse('')

        elif status in ('failed', 'success'):
            version_id = ''
            service_name = ''
            for item in object_attributes.get('variables', []):
                if item.get('key') == 'VERSION_ID':
                    version_id = item.get('value')
                if item.get('key') == 'SERVICE_NAME':
                    service_name = item.get('value')

            if status in ('failed', ):
                if version_id:
                    MicroServiceVersion.objects.filter(pk=version_id).update(status=BuildStatus.failed.value)
            else: # status == 'success' and detailed_status == 'passed':
                if version_id:
                    MicroServiceVersion.objects.filter(pk=version_id).update(
                        status=BuildStatus.success.value,
                        file_path='{}/{}'.format(service_name, task_id)
                    )
        return HttpResponse('')