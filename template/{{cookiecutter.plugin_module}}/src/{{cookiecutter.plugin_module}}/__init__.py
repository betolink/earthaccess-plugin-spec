"""{{ cookiecutter.distribution_name }}."""

from __future__ import annotations

from .plugin import {{ cookiecutter.plugin_class }}
{% if cookiecutter.remote == 'yes' %}from .job import {{ cookiecutter.plugin_class }}Job

__all__ = ["{{ cookiecutter.plugin_class }}", "{{ cookiecutter.plugin_class }}Job"]
{% else %}
__all__ = ["{{ cookiecutter.plugin_class }}"]
{% endif %}
