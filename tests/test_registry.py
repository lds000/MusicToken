from musictoken.registry import ChipRegistry


def test_upsert_and_get(tmp_path):
    db = tmp_path / "chips.db"
    reg = ChipRegistry(db)

    chip = reg.upsert(
        uid="04A2",
        label="EAGLES / HOTEL CALIFORNIA",
        genre="rock",
        action_type="spotify",
        payload={"uri": "spotify:track:abc"},
    )
    assert chip.uid == "04A2"
    assert chip.label.startswith("EAGLES")
    assert chip.payload == {"uri": "spotify:track:abc"}

    fetched = reg.get("04A2")
    assert fetched is not None
    assert fetched.action_type == "spotify"

    reg.mark_scanned("04A2")
    assert reg.get("04A2").scan_count == 1


def test_by_genre_and_delete(tmp_path):
    reg = ChipRegistry(tmp_path / "c.db")
    reg.upsert(uid="A", label="x", genre="rock", action_type="spotify",
               payload={"uri": "spotify:track:1"})
    reg.upsert(uid="B", label="y", genre="chill", action_type="spotify",
               payload={"uri": "spotify:track:2"})
    assert {c.uid for c in reg.by_genre("rock")} == {"A"}
    assert reg.delete("A") is True
    assert reg.get("A") is None
    assert reg.delete("A") is False


def test_unknown_action(tmp_path):
    reg = ChipRegistry(tmp_path / "c.db")
    chip = reg.upsert(uid="Z", action_type="command", payload={"command": "skip"})
    assert chip.action_type == "command"
    assert chip.payload == {"command": "skip"}
