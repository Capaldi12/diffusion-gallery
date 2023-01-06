"""Background process to run diffusion tasks."""
import time

from django.core.management.base import BaseCommand

import modelqueue

from ...DiffusionWorker import DiffusionWorker
from ...models import Task


class Command(BaseCommand):
    """Background process to run diffusion tasks."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.worker = DiffusionWorker()  # TODO configs

    def handle(self, *args, **options):
        while True:
            task = modelqueue.run(
                Task.objects.all(),
                'status',
                self.process_task
            )

            if task is None:
                print('No tasks. Sleeping')
                time.sleep(5)

    def process_task(self, task: Task):
        prompt = task.prompt

        image = self.worker.generate(prompt)

        # TODO save image

