import urllib.request

import pybullet
import pytest


@pytest.fixture(autouse=True)
def no_network_or_physics(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError('Contract tests do not call models or run physics')
    monkeypatch.setattr(urllib.request, 'urlopen', blocked)
    monkeypatch.setattr(pybullet, 'connect', blocked)
