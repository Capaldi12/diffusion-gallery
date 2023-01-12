__all__ = ['DiffusionModel', 'Prompt', 'Task', 'Image']

from django.db import models
from django.conf import settings
from django.core.validators import \
    MinValueValidator as Min, \
    MaxValueValidator as Max, \
    StepValueValidator as Step

# https://grantjenks.com/docs/modelqueue/
import modelqueue


class DiffusionModel(models.Model):
    """Stable diffusion model."""

    # Unique model name for identification
    name = models.CharField(max_length=100, unique=True,
                            help_text='Unique model name')

    # URL model can be downloaded from
    url = models.URLField(help_text='URL where you can download the model')

    # Path model is stored in
    filepath = models.FilePathField(
        path=settings.GALLERY_MODEL_ROOT, recursive=True,
        blank=True, null=True, default=None,
        help_text='Path to the model checkpoint file')

    # Whether model is available to use (filepath is set and file is present)
    available = models.BooleanField(
        default=False, help_text='Whether the model can be used')

    def __str__(self):
        return self.name


class Prompt(models.Model):
    """Diffusion prompt for image generation."""

    # Name of the prompt
    name = models.CharField(
        max_length=100, db_index=True,
        help_text='Name of the prompt (Does not need to be unique)'
    )

    # Timestamp of prompt creation
    created_at = models.DateTimeField(auto_now_add=True)

    # --- Image parameters ---

    width = models.PositiveIntegerField(
        default=512, validators=[Min(64), Max(4096), Step(64)],
        help_text='Width of the image in pixels (must be divisible by 8)'
    )   # Width

    height = models.PositiveIntegerField(
        default=512, validators=[Min(64), Max(4096), Step(64)],
        help_text='Height of the image in pixels (must be divisible by 8)'
    )     # Height

    # --- Model parameters ---

    # Model to generate with
    model = models.ForeignKey(DiffusionModel, on_delete=models.PROTECT,
                              help_text='Model to generate with')

    # --- Diffusion parameters ---

    # Text prompt used to generate image
    text = models.TextField(
        max_length=1000,
        help_text='Description of the image to generate')  # prompt

    # Number of diffusion steps
    steps = models.PositiveIntegerField(
        default=50, validators=[Min(1), Max(1000)],
        help_text='Number of diffusion steps. More steps - better results'
    )  # ddim_steps

    # Random number generator seed
    # TODO validate seed is empty string or can be cast to number
    #   or hash the string if it can not instead
    seed = models.CharField(
        max_length=16, help_text='Random number generator seed. '
                                 'Numbers are used as is. Strings are hashed. '
                                 'Leave blank for random seed')  # seed

    # Sampling algorithm
    sampler = models.CharField(max_length=16, choices=[
        ('euler', 'Euler'),
        ('heun', 'Heun'),
        ('lms', 'LMS'),
        ('plms', 'PLMS'),
        ('ddim', 'DDIM'),
        ('dpm2', 'DPM2'),
        ('euler_a', 'Euler Ancestral'),
        ('dpm2_a', 'DPM2 Ancestral'),

    ], default='euler', help_text='Sampling algorithm')  # sampler

    # Number of samples in operation (images generated simultaneously)
    #   Perhaps should be calculated based on picture size and VRAM available
    batch_size = models.PositiveIntegerField(
        default=1, validators=[Min(1), Max(100)],
        help_text='Number of images to generate simultaneously')  # batch_size

    # How much image fits the prompt
    scale = models.FloatField(
        default=7.5, validators=[Min(0), Max(50), Step(0.1)],
        help_text='How much image looks like prompt')   # scale

    # Amount of noise added during sampling
    eta = models.FloatField(
        default=0.01, validators=[Min(0), Max(1), Step(0.01)],
        help_text='Amount of noise added during sampling')  # ddim_eta

    # --- Possible parameters ---

    # Number of images to generate
    #   can be implemented through multiple tasks in queue instead
    n_iter = 1

    # Batch size of the UNet
    #   Takes up a lot of extra RAM for very
    #   little improvement in inference time
    #   Might as well be set to constant
    unet_bs = 1

    # Device to run model on
    #   Probably should be set by server config
    device = 'cuda'

    # Precision mode for float calculations
    #   Mixed precision might not be available for some devices (which results
    #   in all-green images being generated). Should either be set through
    #   config or enabled/disabled through config
    full_precision = True

    # Increase generation speed for the cost of extra VRAM usage
    #   Also dependent on the device used and available resources
    #   might be better to set from settings or keep disabled
    turbo = False

    @property
    def size(self):
        return f'{self.width}x{self.height}'

    def __str__(self):
        return self.name


class Image(models.Model):
    """Image generated by diffusion model."""

    # Image display name
    name = models.CharField(max_length=100, db_index=True,
                            help_text='Image display name')

    # Image description
    description = models.TextField(max_length=1000)

    # Image file
    image = models.ImageField(upload_to='images/generated/')

    # Prompt this image was generated for
    prompt = models.ForeignKey(Prompt, on_delete=models.PROTECT,
                               help_text='Prompt image was generated for')

    # Timestamp of image creation
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def prompt_text(self):
        return self.prompt.text

    def __str__(self):
        return self.name


class Task(models.Model):
    """Task for image generation."""

    # Prompt to generate for
    prompt = models.ForeignKey(Prompt, on_delete=models.CASCADE)

    # Current task status
    status = modelqueue.StatusField(
        db_index=True, default=modelqueue.Status.waiting)

    # Timestamps of creation and last update
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def task_status(self):
        """Convert status into Status instance"""
        return modelqueue.Status(self.status)

    @property
    def prompt_text(self):
        return self.prompt.text

    def __str__(self):
        return f'Task for `{self.prompt}`'
