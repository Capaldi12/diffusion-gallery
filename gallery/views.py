from django.shortcuts import render

from .util import Router


route = Router()


@route('', name='index')
def index(request):
    return render(request, 'index.html')
