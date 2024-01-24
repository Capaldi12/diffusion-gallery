import json

from django.db import DatabaseError
from django.http import JsonResponse
from django.urls import reverse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST

from .models import Image, Prompt, DiffusionModel
from .utils import Router

route = Router()


def success(data=None, **kwargs):
    if data:
        kwargs['data'] = data

    return JsonResponse({
        'status': 'success',
        **kwargs
    })


def fail(code, message):
    return JsonResponse({
        'status': 'fail',
        'data': {
            'code': code,
            'message': str(message)
        }
    })


@route('', name='api_root')
def api_root(request):
    return success(
        links={
            'prompts': reverse('prompt_list'),
            'images': reverse('image_list'),
            'models': reverse('model_list'),
        },
    )


@route('images/', name='image_list')
@route('images/<int:image_id>/', name='image_details')
@route('prompts/<int:prompt_id>/images/', name='prompt_images')
class ImageView(View):
    def get(self, request, prompt_id=None, image_id=None):
        if image_id:
            return self.get_image(image_id)
        else:
            return self.get_list(prompt_id)

    def get_list(self, prompt_id=None):
        if prompt_id:
            data = Image.objects.filter(prompt_id=prompt_id)
        else:
            data = Image.objects.all()

        return success({
            'images': [
                {
                    'name': image.name,
                    'src': image.image.url,
                    'url': reverse('image_details', args=[image.id]),
                }
                for image in data
            ],
        })

    def get_image(self, image_id):
        image = Image.objects.filter(id=image_id).first()

        if image is None:
            return fail(404, 'Image does not exist')

        return success({
            'image': {
                'name': image.name,
                'description': image.description,
                'src': image.image.url,
                'prompt': reverse('prompt_details', args=[image.prompt_id]),
                'created_at': image.created_at,
            },
        })


@route('prompts/', name='prompt_list')
@route('prompts/<int:prompt_id>/', name='prompt_details')
@route('models/<int:model_id>/prompts/', name='model_prompts')
@method_decorator(csrf_exempt, name='dispatch')  # No CSRF protection
class PromptView(View):
    def get(self, request, model_id=None, prompt_id=None):
        if prompt_id:
            return self.get_prompt(prompt_id)
        else:
            return self.get_list(model_id)

    def get_list(self, model_id=None):
        if model_id:
            data = Prompt.objects.filter(model_id=model_id)
        else:
            data = Prompt.objects.all()

        return success({
            'prompts': [
                {
                    'name': prompt.name,
                    'text': prompt.text,
                    'url': reverse('prompt_details', args=[prompt.id]),
                }
                for prompt in data
            ],
        })

    def get_prompt(self, prompt_id):
        prompt = Prompt.objects.filter(id=prompt_id).first()

        if prompt is None:
            return fail(404, 'Prompt does not exist')

        return success({
            'prompt':  {
                'name': prompt.name,
                'text': prompt.text,
                'model': prompt.model.name,
                'width': prompt.width,
                'height': prompt.height,
                'steps': prompt.steps,
                'seed': prompt.seed,
                'images': reverse('prompt_images', args=[prompt.id]),
                'generate': reverse('generate', args=[prompt.id]),
            },
        })

    allowed_keys = {
        'name', 'text', 'model', 'width', 'height', 'steps', 'seed',
    }

    required_keys = {
        'name', 'text', 'model'
    }

    def post(self, request):
        data: dict = json.loads(request.body)

        keys = set(data.keys())

        # TODO use validation library
        if keys - self.allowed_keys:
            return fail(
                400,
                f'Invalid keys: ' + ', '.join(keys - self.allowed_keys),
            )

        if self.required_keys - keys:
            return fail(
                400,
                f'Missing keys: ' + ', '.join(self.required_keys - keys),
            )

        try:
            model = DiffusionModel.objects.get(name=data['model'])
        except DatabaseError:
            return fail(404, 'Specified model does not exist')

        data['model'] = model

        try:
            prompt = Prompt.objects.create(**data)
        except DatabaseError as e:
            return fail(400, e)

        return success({
            # Other fields?
            'url': reverse('prompt_details', args=[prompt.id]),
        })


@route('prompts/<int:prompt_id>/generate/', name='generate')
@route('prompts/<int:prompt_id>/generate/<int:count>/', name='generate_many')
@csrf_exempt
@require_POST
def generate(request, prompt_id, count=1):
    try:
        prompt = Prompt.objects.get(id=prompt_id)
    except DatabaseError:
        return fail(404, 'Specified prompt does not exist')

    prompt.create_task(count)

    return success()


@route('models/', name='model_list')
@route('models/<int:model_id>/', name='model_details')
def models(request, model_id=None):
    if model_id:
        model = DiffusionModel.objects.filter(id=model_id).first()

        if model is None:
            return fail(404, 'Model not found')

        return success({
            'model': {
                'name': model.name,
                'available': model.available,
                'download_url': model.url,
                'prompts': reverse('model_prompts', args=[model.id])
            }
        })

    models_ = DiffusionModel.objects.all()

    return success({
        'models': [
            {
                'name': model.name,
                'available': model.available,
                'url': reverse('model_details', args=[model.id])
            }
            for model in models_
        ],
    })
