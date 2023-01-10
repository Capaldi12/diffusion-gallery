"""Background process to run diffusion tasks."""
import time
from io import BytesIO
from datetime import timedelta
import logging

from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files import File

import modelqueue

from ...DiffusionWorker import DiffusionWorker
from ...models import Task, Image


ONE_DAY = timedelta(days=1)


class Command(BaseCommand):
    """Background process to run diffusion tasks."""

    worker: DiffusionWorker

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.logger = logging.getLogger('diffuse')

    def handle(self, *args, **options):
        """Run background worker."""

        self.logger.debug('Running \'diffuse\' command')

        self.worker = DiffusionWorker(settings.MODELS_CONFIG_PATH)

        try:
            self.logger.debug('Starting processing loop')

            while True:
                task = modelqueue.run(
                    Task.objects.all(), 'status', self.process_task,
                    timeout=ONE_DAY,  # One hour might be too short
                )

                if task is None:
                    self.logger.debug('No task. Sleeping...')

                    time.sleep(5)

        except KeyboardInterrupt:
            self.logger.debug('Shutting down')
            pass

    def process_task(self, task: Task):
        """Process image generation task."""

        self.logger.debug(f'Processing task {task}')
        prompt = task.prompt

        # TODO: Exception handling
        images, seed = self.worker.generate(prompt)

        for i, image_ in enumerate(images):
            # Write image to in-memory buffer
            blob = BytesIO()
            image_.save(blob, 'PNG')

            name = f'{prompt.name}_{seed}_{i}'

            # Create database record and save image to storage
            image = Image(name=name, prompt=prompt)
            image.image.save(f'{name}.png', File(blob))

            self.logger.info(f'Saved to {image.image.name}')

        self.logger.debug(f'Saved {len(images)} images')
        self.logger.debug(f'Finished task {task}')

