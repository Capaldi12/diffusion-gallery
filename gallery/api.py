from django.http import JsonResponse

from .utils import Router

route = Router()


@route('test')
def the_test(request):
    return JsonResponse({'ok': True})
