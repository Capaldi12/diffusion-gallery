from django.shortcuts import render

from .utils import Router
from .models import Image


route = Router()


@route('', name='index')
def index(request):
    images = Image.objects.all().order_by('-created_at')

    return render(request, 'index.html', {'images': images})
