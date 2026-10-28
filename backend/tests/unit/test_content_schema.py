import pytest

from app.content_loader.schema import ContentError, read_track_directory
from tests.content_helpers import activity, unit, write_track


def test_valid_track_is_read_in_order(tmp_path):
    directory = write_track(
        tmp_path,
        units=[unit("second", 2), unit("first", 1, activities=[activity("a"), activity("b")])],
    )
    content = read_track_directory(directory)
    assert content.track.slug == "sample"
    assert {u.slug: u.position for u in content.units} == {"first": 1, "second": 2}
    first = next(u for u in content.units if u.slug == "first")
    assert [a.slug for a in first.activities] == ["a", "b"]


@pytest.mark.parametrize(
    ("units", "message"),
    [
        ([unit("same", 1), unit("same", 2)], "duplicate unit slug"),
        ([unit("one", 1), unit("two", 1)], "duplicate unit position"),
        ([unit(activities=[activity("x"), activity("x")])], "duplicate activity slug"),
        ([unit(activities=[])], "activities"),
        ([unit(slug="Bad Slug")], "slug"),
        ([unit(position=0)], "position"),
        ([unit(activities=[activity(kind="podcast")])], "kind"),
        ([unit(activities=[activity(body_md=None)])], "url or body_md"),
        ([unit(activities=[activity(kind="external", body_md="x")])], "need a url"),
        ([unit(activities=[activity(url="javascript:alert(1)")])], "http"),
        ([unit(activities=[activity(url="ftp://example.com/x")])], "http"),
        ([unit(unexpected="field")], "unexpected"),
        ([unit(status="retired")], "status"),
        ([unit(activities=[activity(body_md="값에는 **자료형(type)**이 있다")])], "bold"),
    ],
)
def test_invalid_content_is_rejected_with_file_name(tmp_path, units, message):
    directory = write_track(tmp_path, units=units)
    with pytest.raises(ContentError) as excinfo:
        read_track_directory(directory)
    assert message in str(excinfo.value)
    assert "sample" in str(excinfo.value)


def test_missing_track_file_is_rejected(tmp_path):
    with pytest.raises(ContentError, match="missing track.yaml"):
        read_track_directory(tmp_path)


def test_invalid_yaml_is_rejected(tmp_path):
    directory = write_track(tmp_path, units=[unit()])
    (directory / "units" / "99-broken.yaml").write_text("slug: [unclosed", "utf-8")
    with pytest.raises(ContentError, match="invalid YAML"):
        read_track_directory(directory)


def test_bold_followed_by_korean_after_a_letter_is_fine(tmp_path):
    directory = write_track(
        tmp_path,
        units=[unit(activities=[activity(body_md="**대입**이라고 하고 **자료형**(type)")])],
    )
    assert read_track_directory(directory).units[0].activities[0].body_md.startswith("**대입**")
