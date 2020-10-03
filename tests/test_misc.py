import pytest
from dlclabel import misc


@pytest.mark.parametrize(
    "input, expected",
    [
        [[4, 3, 3, 2, 1, 5, 1, 5], [4, 3, 2, 1, 5]],
        [["d", "b", "a", "a", "b", "c"], ["d", "b", "a", "c"]],
        [["ad", "aa", "aa", "ad", "ab", "ab"], ["ad", "aa", "ab"]],
    ],
)
def test_unsorted_unique(input, expected):
    assert list(misc.unsorted_unique(input)) == expected


def test_encode_categories():
    cat = ["b", "b", "c", "c", "a"]
    inds, map_ = misc.encode_categories(cat, return_map=True)
    assert list(inds) == [0, 0, 1, 1, 2]
    assert map_ == {"b": 0, "c": 1, "a": 2}


@pytest.mark.parametrize("is_multi", [False, True])
def test_dlc_header(is_multi):
    config = {
        "multianimalproject": is_multi,
        "scorer": "user",
        "individuals": ["ind1", "ind2"],
        "bodyparts": ["a", "b"],
        "multianimalbodyparts": ["a", "b"],
        "uniquebodyparts": ["c"],
    }
    header = misc.DLCHeader.from_config(config)
    assert header.scorer == config["scorer"]
    assert header.coords == ["x", "y"]
    if is_multi:
        assert header.individuals == config["individuals"] + ["single"]
        assert (
            header.bodyparts
            == config["multianimalbodyparts"] + config["uniquebodyparts"]
        )
    else:
        assert header.individuals == [""]
        assert header.bodyparts == config["bodyparts"]


def test_cycle_enum():
    cycle_enum = misc.CycleEnum("Item", ["ITEM1", "ITEM2", "ITEM3"])
    assert cycle_enum("item1") is cycle_enum.ITEM1
    assert cycle_enum(cycle_enum.ITEM1) is cycle_enum.ITEM1
    assert next(cycle_enum) is cycle_enum.ITEM1
    assert next(cycle_enum) is cycle_enum.ITEM2
    assert next(cycle_enum) is cycle_enum.ITEM3
    assert next(cycle_enum) is cycle_enum.ITEM1
