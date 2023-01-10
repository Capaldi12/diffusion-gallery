"""Responsible for managing and running stable diffusion model."""
import logging
from typing import Union, List, Tuple
from pathlib import Path

from contextlib import nullcontext
import random
import time

from omegaconf import OmegaConf

import numpy as np
import torch
import pytorch_lightning as pl
from einops import rearrange
from PIL import Image

import transformers
transformers.logging.set_verbosity_error()

from ldm.util import instantiate_from_config
from optimizedSD import ddpm
from optimizedSD.optimUtils import split_weighted_subprompts

from .models import Prompt, DiffusionModel


class DiffusionWorker:
    """Responsible for managing and running stable diffusion model."""

    # Models that do the work
    UNet: ddpm.UNet
    FirstStage: ddpm.FirstStage
    CondStage: ddpm.CondStage

    def __init__(self, config_file: Union[str, Path]):
        self.logger = logging.getLogger('diffuse')
        self.config = OmegaConf.load(config_file)

        self.model_name = None

    def generate(self, prompt: Prompt) -> Tuple[List[Image.Image], int]:
        """Generate image(s) for given prompt."""

        self.logger.info(f'Generating images for {prompt}')

        self._check_model(prompt.model)

        # This might be put into prompt as well
        channels = 4   # latent channels
        f = 8   # downsampling factor

        device = prompt.device

        # Set parameters for models that need them
        self.UNet.unet_bs = prompt.unet_bs
        self.UNet.turbo = prompt.turbo
        self.UNet.cdevice = device

        self.CondStage.cond_stage_model.device = device

        # Set seed for everything
        seed = prompt.seed

        if seed == "":
            seed = random.randint(0, 1_000_000)
            self.logger.debug(f'No seed provided. Using {seed}')

        try:
            seed = int(seed)
        except ValueError:
            seed = hash(seed)

        pl.seed_everything(seed)

        # Handle precision
        if device != 'cpu' and prompt.full_precision is False:
            self.UNet.half()
            self.FirstStage.half()
            self.CondStage.half()

            precision_scope = torch.autocast

        else:
            precision_scope = nullcontext

        prompts = prompt.batch_size * [prompt.text]

        images = []

        with torch.no_grad():  # no gradient calculations
            with precision_scope('cuda'):
                self.logger.debug('Running CondStage')

                self.CondStage.to(device)

                # Unconditional conditioning (aka empty prompt)
                uc = None

                if prompt.scale != 1.:
                    uc = self.CondStage.get_learned_conditioning(
                        prompt.batch_size * [""])

                # Handling weighted prompts
                sub_prompts, weights = split_weighted_subprompts(prompts[0])

                if len(sub_prompts) > 1:
                    c = torch.zeros_like(uc)
                    total_weight = sum(weights)

                    for sp, w in zip(sub_prompts, weights):
                        c = torch.add(
                            c, self.CondStage.get_learned_conditioning(sp),
                            alpha=w/total_weight
                        )
                else:
                    c = self.CondStage.get_learned_conditioning(prompts)

                shape = [prompt.batch_size, channels,
                         prompt.height // f, prompt.width // f]

                # Move everything back to the cpu and wait for memory to clear
                if device != 'cpu':
                    self.logger.debug('Freeing memory')

                    # TODO Do we really need to divide here ?
                    mem = torch.cuda.memory_allocated() / 1e6
                    self.CondStage.to('cpu')

                    while torch.cuda.memory_allocated() / 1e6 >= mem:
                        time.sleep(1)

                self.logger.debug('Sampling')

                # Now do the sampling
                samples = self.UNet.sample(
                    S=prompt.steps,
                    conditioning=c,
                    seed=seed,
                    shape=shape,
                    verbose=False,
                    unconditional_guidance_scale=prompt.scale,
                    unconditional_conditioning=uc,
                    eta=prompt.eta,
                    x_T=None,   # start_code
                    sampler=prompt.sampler
                )

                self.logger.debug('Running FirstStage')

                # Decode images from output data
                self.FirstStage.to(device)

                for sample in samples:
                    sample_ = self.FirstStage.decode_first_stage(
                        sample.unsqueeze(0))
                    sample_ = torch.clamp((sample_ + 1.) / 2., min=0., max=1.)
                    sample_ = 255. * rearrange(sample_[0].cpu().numpy(),
                                               'c h w -> h w c')

                    images.append(Image.fromarray(sample_.astype(np.uint8)))

                # Free memory once again
                if device != 'cpu':
                    self.logger.debug('Freeing memory')

                    mem = torch.cuda.memory_allocated() / 1e6
                    self.FirstStage.to('cpu')

                    while torch.cuda.memory_allocated() / 1e6 >= mem:
                        time.sleep(1)

        self.logger.debug('Finished generating images')
        return images, seed

    def _check_model(self, model: DiffusionModel):
        """Check if model is the same as loaded and load it if not."""

        if self.model_name != model.name:
            self.logger.debug(f'Switching model to {model.name}')
            self._load_model(model)

    def _load_model(self, model: DiffusionModel):
        """Load specified model."""

        ckpt = model.filepath

        # Check if model can be loaded
        if not model.available or ckpt is None or not Path(ckpt).exists():
            raise ValueError(f'Model {model.name} is not available')

        self.logger.info(f'Loading {model.name} ({ckpt})')

        # Load checkpoint from ckpt file
        checkpoint = torch.load(ckpt, map_location='cpu')

        if 'global_step' in checkpoint:
            self.logger.debug(f'Global Step: {checkpoint["global_step"]}')

        sd = checkpoint['state_dict']

        self._split_model(sd)

        self.logger.debug('Instantiating models')

        # Instantiate models and load state from state dict
        self.UNet = instantiate_from_config(self.config.modelUNet)
        self.UNet.load_state_dict(sd, strict=False)
        self.UNet.eval()

        self.FirstStage = instantiate_from_config(self.config.modelFirstStage)
        self.FirstStage.load_state_dict(sd, strict=False)
        self.FirstStage.eval()

        self.CondStage = instantiate_from_config(self.config.modelCondStage)
        self.CondStage.load_state_dict(sd, strict=False)
        self.CondStage.eval()

        self.model_name = model.name
        self.logger.debug(f'Finished loading {model.name}')

    @staticmethod
    def _split_model(sd: dict):
        """
        Split model parameters into 2 models.

        Why? No idea.
        """
        # optimizedSD/txt2img_gradio.py:47-62

        li, lo = [], []

        for key in sd:
            first, *sp = key.split(".")
            if first == "model":
                if "input_blocks" in sp or "middle_block" in sp or \
                        "time_embed" in sp:
                    li.append(key)
                else:
                    lo.append(key)

        for key in li:
            sd["model1." + key[6:]] = sd.pop(key)

        for key in lo:
            sd["model2." + key[6:]] = sd.pop(key)
