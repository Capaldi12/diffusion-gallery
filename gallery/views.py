from django.shortcuts import render

from .utils import Router


route = Router()


@route('', name='index')
def index(request):
    return render(request, 'index.html')
