from django.contrib import admin

from .models import ExpertRequest, RequestData, Decision

admin.site.register(Decision)
admin.site.register(ExpertRequest)
admin.site.register(RequestData)
