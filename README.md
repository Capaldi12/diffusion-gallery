<h1 align="center">Diffusion Gallery</h1>

This repo is an extension to @basujindal [Optimized Stable Diffusion](https://github.com/basujindal/stable-diffusion), adding gallery web interface to simplify model usage.
Interface allows to create prompts for SD and add tasks to generate them to the generation queue. Generation queue persists between app launches and interrupted tasks will restart after the program is up again.

Generated images can then be viewed in the gallery interface.
Each image keeps track of its prompt and each prompt is saved in the system and can be reused later.

<h1 align="center">Installation</h1>

All gallery files are located in the [gallery](gallery) folder, so if you have already cloned the original repository you can just download and copy this folder into the original instead of cloning the entire repo. 

You can also clone this repo and follow the same installation steps as the original (mainly creating the conda environment and placing the weights at the specified location).

In addition to conda requirements, you may need to install following libraries:

```shell
pip install django modelqueue
```

<h1 align="center">Usage</h1>

This project consists of two parts: daemon that runs Stable Diffusion model and Django server hosting web interface. Both of them need to run for the app to be usable, but they can also be used separately, if you only need one of the functions.

Daemon is registered as Django app and can be started as such:

```shell
python manage.py diffuse
```

Running only daemon will allow it to process generation queue, generating and saving images. However, web interface will be inaccessible, unless server is running as well.

Server, being classical Django app, can be started as follows:

```shell
python manage.py runserver
```

Running only server will allow you to view images and prompts, create new prompts and add tasks to the generation queue. However, the queue will not be processed unless daemon is running as well.

To run daemon and server simultaneously, use aforementioned commands in two separate command prompts or use command like `start` in windows command prompt or its unix equivalent to run them both in the same session.

Don't forget to activate virtual environment before running.
