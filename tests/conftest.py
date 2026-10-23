import pytest

from when2ask.environment import Environment
from when2ask.runner import run_episode
from when2ask.task import PrivateTaskSpec


@pytest.fixture
def env():
    with Environment(seed=0) as world:
        yield world


@pytest.fixture(scope="session")
def ask_episode(tmp_path_factory):
    return run_episode("ask", output_dir=tmp_path_factory.mktemp("ask"), quiet=True)


@pytest.fixture(scope="session")
def noask_episode(tmp_path_factory):
    return run_episode("noask", output_dir=tmp_path_factory.mktemp("noask"), quiet=True)


@pytest.fixture(scope="session")
def matched_noask_episode(tmp_path_factory):
    return run_episode("noask", output_dir=tmp_path_factory.mktemp("matched_noask"), quiet=True,
                       private_spec=PrivateTaskSpec(block_choice="yellow_block"))
