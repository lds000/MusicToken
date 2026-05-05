from musictoken.ai.mock import MockProvider
from musictoken.ai.suggester import Suggester
from musictoken.registry import ChipRegistry


def test_suggest_chips_returns_validated_items(tmp_path):
    reg = ChipRegistry(tmp_path / "c.db")
    sug = Suggester(MockProvider(), reg)
    out = sug.suggest_chips("late-night driving", count=4)
    assert 1 <= len(out) <= 4
    for s in out:
        assert s["label"]
        assert s["action_type"] in {"spotify", "radio", "url"}
        if s["action_type"] == "spotify":
            assert s["payload"]["uri"].startswith("spotify:")


def test_pick_wild_returns_chip_or_none(tmp_path):
    reg = ChipRegistry(tmp_path / "c.db")
    sug = Suggester(MockProvider(), reg)
    assert sug.pick_wild() is None
    reg.upsert(uid="X", label="A", genre="rock", action_type="spotify",
               payload={"uri": "spotify:track:abc"})
    pick = sug.pick_wild(context="evening")
    assert pick is not None
    assert pick.uid == "X"


def test_autofill_returns_label_and_genre(tmp_path):
    reg = ChipRegistry(tmp_path / "c.db")
    sug = Suggester(MockProvider(), reg)
    out = sug.autofill({"uri": "spotify:album:123"}, action_type="spotify")
    assert "label" in out
    assert "genre" in out
