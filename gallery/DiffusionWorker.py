"""Responsible for managing and running stable diffusion model."""
from .models import Prompt


class DiffusionWorker:
    """Responsible for managing and running stable diffusion model."""

    def __init__(self):
        ...

        # TODO argument for config file?
        # TODO implement reading configuration and instantiating models

    def generate(self, prompt: Prompt):
        """Generate image(s) for given prompt"""

        # TODO implement this
