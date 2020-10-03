import pytest


@pytest.fixture()
def config():
    return {
        "scorer": "user",
        "individuals": ["ind1", "ind2"],
        "bodyparts": ["a", "b"],
        "multianimalbodyparts": ["a", "b"],
        "uniquebodyparts": ["c"],
    }
