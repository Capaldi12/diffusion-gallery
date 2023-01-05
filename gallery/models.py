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
    name = models.CharField(max_length=100, unique=True)

    # URL model can be downloaded from
    url = models.URLField()

    # Path model is stored in
    filepath = models.FilePathField(
        path=settings.GALLERY_MODEL_ROOT, recursive=True,
        blank=True, null=True, default=None)

    # Whether model is available to use (filepath is set and file is present)
    available = models.BooleanField(default=False)


class Prompt(models.Model):
    """Diffusion prompt for image generation."""

    # Name of the prompt
    name = models.CharField(max_length=100, db_index=True)

    # Timestamp of prompt creation
    created_at = models.DateTimeField(auto_now_add=True)

    # --- Image parameters ---

    width = models.PositiveIntegerField(
        default=512, validators=[Min(64), Max(4096), Step(64)])     # Width
    height = models.PositiveIntegerField(
        default=512, validators=[Min(64), Max(4096), Step(64)])     # Height

    # --- Model parameters ---

    # Model to generate with
    model = models.ForeignKey(DiffusionModel, on_delete=models.PROTECT)

    # --- Diffusion parameters ---

    # Text prompt used to generate image
    text = models.TextField(max_length=1000)  # prompt

    # Number of diffusion steps
    steps = models.PositiveIntegerField(
        default=50, validators=[Min(1), Max(1000)])     # ddim_steps

    # Random number generator seed
    # TODO validate seed is empty string or can be cast to number
    seed = models.CharField(max_length=16)  # seed

    # Sampling algorithm
    sampler = models.CharField(choices=[
        'ddim', 'plms', 'heun', 'euler', 'euler_a', 'dpm2', 'dpm2_a', 'lms'
    ], default='plms')    # sampler

    # Number of samples in operation (images generated simultaneously)
    #   Perhaps should be calculated based on picture size and VRAM available
    batch_size = models.PositiveIntegerField(
        default=1, validators=[Min(1), Max(100)])   # batch_size

    # How much image fits the prompt
    scale = models.FloatField(
        default=7.5, validators=[Min(0), Max(50), Step(0.1)])   # scale

    # Amount of noise added during sampling
    eta = models.FloatField(
        default=0.01, validators=[Min(0), Max(1), Step(0.01)])  # ddim_eta

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


class Image(models.Model):
    """Image generated by diffusion model."""

    # Image display name
    name = models.CharField(max_length=100, db_index=True)

    # Image description
    description = models.TextField(max_length=1000)

    # Image file
    image = models.ImageField(upload_to='images/generated/')

    # Prompt this image was generated for
    prompt = models.ForeignKey(Prompt, on_delete=models.PROTECT)

    # Timestamp of image creation
    created_at = models.DateTimeField(auto_now_add=True)


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
