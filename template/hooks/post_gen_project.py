"""Cookiecutter post-generation hook."""

from __future__ import annotations

import os

remote = "{{ cookiecutter.remote }}" == "yes"
job_module = os.path.join("src", "{{ cookiecutter.plugin_module }}", "job.py")

if not remote and os.path.exists(job_module):
    os.remove(job_module)
