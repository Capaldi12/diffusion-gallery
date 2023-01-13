from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .utils import Router
from .models import Image, Prompt, Task

route = Router()


@route('', name='index')
def index(request):
    images = Image.objects.all().order_by('-created_at')

    return render(request, 'gallery/index.html', {'images': images})


@route('generate', name='generate')
class PromptCreateView(CreateView):
    model = Prompt
    fields = ['name', 'text', 'model', 'width', 'height', 'steps', 'seed']
    success_url = reverse_lazy('index')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Don't display `generate` button
        context['no_button'] = True

        return context

    def form_valid(self, form):
        response = super().form_valid(form)

        # Create task for the prompt
        # TODO: multiple tasks per prompt
        Task.objects.create(prompt=self.object)

        return response
