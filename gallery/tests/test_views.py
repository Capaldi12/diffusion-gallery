from io import BytesIO
import tempfile
import shutil

from django.test import TestCase, override_settings
from django.shortcuts import reverse
from django.http import HttpResponseRedirect
from django.core.files import File

import PIL.Image
import modelqueue

from ..models import DiffusionModel, Prompt, Image, Task


# Temporary media root
TEST_MEDIA_ROOT = tempfile.mkdtemp()


def tearDownModule():
    shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)


class IndexTestCase(TestCase):
    def test_page_accessibility(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)


class GenerateTestCase(TestCase):
    def test_page_accessibility(self):
        response = self.client.get(reverse('generate'))
        self.assertEqual(response.status_code, 302)

    def test_redirect_location(self):
        response = self.client.get(reverse('generate'))

        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response.url, reverse('prompt_list'))


class PromptCreateViewTestCase(TestCase):
    def setUp(self):
        self.model = DiffusionModel.objects.create(
            name='test_model_1', available=True)

        self.post_data = {
            'name': 'test_prompt',
            'text': 'prompt_text',
            'model': self.model.pk,
            'width': '512',
            'height': '512',
            'steps': '50',
            'seed': '',
        }

    def test_page_accessibility(self):
        response = self.client.get(reverse('prompt_create'))
        self.assertEqual(response.status_code, 200)

    def test_post_request(self):
        response = self.client.post(reverse('prompt_create'), self.post_data)

        self.assertEqual(response.status_code, 302)

        prompt = Prompt.objects.last()

        self.assertEqual(response.url, prompt.get_absolute_url())

        self.assertEqual(prompt.model, self.model)


class PromptListViewTestCase(TestCase):
    def test_page_accessibility(self):
        response = self.client.get(reverse('prompt_list'))
        self.assertEqual(response.status_code, 200)


class PromptDetailViewTestCase(TestCase):
    def setUp(self):
        model = DiffusionModel.objects.create(
            name='test_model_1', available=True)
        prompt = Prompt.objects.create(
            name='test_prompt', text='test_prompt', model=model)

        self.prompt_url = prompt.get_absolute_url()

    def test_page_accessibility(self):
        response = self.client.get(self.prompt_url)
        self.assertEqual(response.status_code, 200)

    def test_not_exists(self):
        response = self.client.get(reverse('prompt', args=[42]))
        self.assertEqual(response.status_code, 404)


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class ImageDetailViewTestCase(TestCase):
    def setUp(self):
        model = DiffusionModel.objects.create(
            name='test_model_1', available=True)
        prompt = Prompt.objects.create(
            name='test_prompt', text='test_prompt', model=model)

        pil_image = PIL.Image.new('RGB', (32, 32))
        blob = BytesIO()
        pil_image.save(blob, 'PNG')

        image = Image(name='test_image', prompt=prompt)
        image.image.save('test_image.png', File(blob))

        self.image_url = image.get_absolute_url()

    def test_page_accessibility(self):
        response = self.client.get(self.image_url)
        self.assertEqual(response.status_code, 200)

    def test_not_exists(self):
        response = self.client.get(reverse('image', args=[42]))
        self.assertEqual(response.status_code, 404)


class CreateTaskTestCase(TestCase):
    def setUp(self):
        model = DiffusionModel.objects.create(
            name='test_model_1', available=True)
        prompt = Prompt.objects.create(
            name='test_prompt', text='test_prompt', model=model)

        self.post_data = {
            'prompt_id': prompt.pk,
            'count': 5,
        }

        self.prompt_id = prompt.pk

    def test_post_request(self):
        response = self.client.post(
            reverse('task_create'),
            self.post_data,
            HTTP_REFERER=reverse('prompt', args=[self.prompt_id])
        )

        self.assertEqual(response.status_code, 302)

        task_count = Task.objects.count()

        self.assertEqual(task_count, 5)

        last_task = Task.objects.last()
        last_prompt = Prompt.objects.last()

        self.assertEqual(last_task.prompt, last_prompt)
        self.assertEqual(last_task.task_status.state.name, 'waiting')
