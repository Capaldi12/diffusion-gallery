from django.shortcuts import render, reverse, redirect
from django.views.generic import CreateView, DetailView, ListView
from django.views.decorators.http import require_http_methods
from django.contrib import messages

from .utils import Router
from .models import Image, Prompt, Task

route = Router()

# TODO separate views into files per model


@route('', name='index')
def index(request):
    images = Image.objects.all()

    return render(request, 'gallery/index.html',
                  {'images': images, 'generate_button': True})


@route('generate', name='generate')
def generate(request):
    return redirect(reverse('prompt_list'))


@route('prompt/create', name='prompt_create')
class PromptCreateView(CreateView):
    model = Prompt
    fields = ['name', 'text', 'model', 'width', 'height', 'steps', 'seed']


@route('prompt/<pk>', name='prompt')
class PromptDetailView(DetailView):
    model = Prompt
    context_object_name = 'prompt'


@route('prompt', name='prompt_list')
class PromptListView(ListView):
    model = Prompt
    context_object_name = 'prompts'


@route('task/create', name='task_create')
@require_http_methods(['POST'])
def create_task(request):
    prompt_id = request.POST.get('prompt_id')
    count = int(request.POST.get('count'))

    prompt = Prompt.objects.get(id=prompt_id)
    prompt.create_task(count)

    messages.info(request, 'Success!')
    return redirect(request.META['HTTP_REFERER'])
