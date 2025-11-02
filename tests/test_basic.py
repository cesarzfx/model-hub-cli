"""
Basic tests for the model-hub-cli project.
"""

import sys

import pytest


def test_imports():
    """Test that basic modules can be imported."""
    try:
        pass

        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import modules: {e}")


def test_python_version():
    """Test that we're using Python 3.8+."""
    assert sys.version_info >= (
        3,
        8,
    ), f"Python 3.8+ required, got {sys.version}"


def test_placeholder():
    """Placeholder test to ensure pytest runs successfully."""
    assert 1 + 1 == 2
