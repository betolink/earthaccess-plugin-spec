"""{{ cookiecutter.plugin_class }}: {{ cookiecutter.description }}."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from earthaccess_plugin_spec import PluginBase


class {{ cookiecutter.plugin_class }}(PluginBase):
    name = "{{ cookiecutter.plugin_name }}"
    auth = "{{ cookiecutter.auth }}"
    output = "{{ cookiecutter.output }}"
{% if cookiecutter.needs.strip() %}    needs = frozenset({"{{ cookiecutter.needs.split(',') | map('trim') | join('", "') }}"})
{% endif %}
    @dataclass
    class Options:
        # TODO: declare the options this plugin accepts.
        pass

    def _request(self, results: Any, options: Options) -> Any:
        # Import the backend inside the method so plugin discovery stays cheap.
        # import {{ cookiecutter.backend_package }}

        def work() -> Any:
            # TODO: call the backend and return the {{ cookiecutter.output }} output.
            raise NotImplementedError("implement {{ cookiecutter.plugin_class }}._request")

        return self.job(work)
