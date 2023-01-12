from django.contrib import admin

import modelqueue

from .models import *


@admin.register(DiffusionModel)
class DiffusionModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'url', 'filepath', 'available']
    list_filter = ['available']


@admin.register(Prompt)
class PromptAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'text', 'size', 'model', 'steps', 'sampler'
    ]
    list_filter = ['model__name']


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ['name', 'prompt_text', 'image']


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    actions = [*modelqueue.admin_actions('status')]
    list_display = ['__str__', 'prompt_text', 'task_status']
    list_filter = [modelqueue.admin_list_filter('status')]

    def get_changeform_initial_data(self, request):
        # TODO make custom widget https://stackoverflow.com/a/37676970
        return {'status': int(modelqueue.Status.waiting())}
