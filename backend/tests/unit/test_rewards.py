import pytest

from app.services.rewards import level_info
from tests.conftest import make_settings


@pytest.mark.parametrize(
    ("total", "level", "into", "next_needed"),
    [
        (0, 1, 0, 100),
        (99, 1, 99, 100),
        (100, 2, 0, 150),  # first completed unit levels up right away
        (249, 2, 149, 150),
        (250, 3, 0, 200),
        (449, 3, 199, 200),
        (450, 4, 0, 250),
        (2700, 10, 0, 550),
    ],
)
def test_level_curve_grows_by_a_fixed_step(total, level, into, next_needed):
    info = level_info(total, make_settings())
    assert (info.level, info.xp_into_level, info.xp_for_next_level) == (level, into, next_needed)
    assert info.total_xp == total


def test_level_curve_is_configurable():
    settings = make_settings(level_base_xp=200, level_step_xp=0)
    assert level_info(600, settings).level == 4  # flat 200 per level
