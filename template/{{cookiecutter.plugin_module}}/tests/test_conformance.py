from earthaccess_plugin_spec.testing import Fixtures, run_conformance

from {{ cookiecutter.plugin_module }} import {{ cookiecutter.plugin_class }}


def test_conformance():
    # Replace Fixtures and options once the backend fake is in place.
    run_conformance({{ cookiecutter.plugin_class }}, fixtures=Fixtures(options={}))
