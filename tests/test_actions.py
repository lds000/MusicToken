from musictoken.actions import ActionRunner
from musictoken.events import EventBus
from musictoken.players.mock import MockPlayer
from musictoken.registry import ChipRegistry


def make_runner(tmp_path):
    bus = EventBus()
    reg = ChipRegistry(tmp_path / "c.db")
    player = MockPlayer()
    runner = ActionRunner(reg, player, bus)
    return runner, reg, player, bus


def test_unknown_chip_publishes_scan(tmp_path):
    runner, _reg, _player, bus = make_runner(tmp_path)
    runner.handle_scan("DEADBEEF")
    last = bus.last("scan")
    assert last is not None
    assert last.payload["uid"] == "DEADBEEF"
    assert last.payload["known"] is False


def test_spotify_chip_drives_player(tmp_path):
    runner, reg, player, bus = make_runner(tmp_path)
    reg.upsert(uid="A", label="EAGLES", genre="rock",
               action_type="spotify",
               payload={"uri": "spotify:track:abc", "title": "Hotel California"})
    runner.handle_scan("A")
    np = player.now_playing()
    assert np is not None
    assert np["title"] == "Hotel California"
    assert bus.last("now_playing").payload["title"] == "Hotel California"


def test_command_skip(tmp_path):
    runner, reg, _player, bus = make_runner(tmp_path)
    reg.upsert(uid="S", action_type="command", payload={"command": "skip"})
    runner.handle_scan("S")
    cmd = bus.last("command")
    assert cmd is not None
    assert cmd.payload["command"] == "skip"


def test_mood_picks_random_chip(tmp_path):
    runner, reg, player, _bus = make_runner(tmp_path)
    reg.upsert(uid="C1", label="A", genre="chill", action_type="spotify",
               payload={"uri": "spotify:track:1"})
    reg.upsert(uid="C2", label="B", genre="chill", action_type="spotify",
               payload={"uri": "spotify:track:2"})
    reg.upsert(uid="M",  label="MOOD CHILL", action_type="mood",
               payload={"mood": "chill"})
    runner.handle_scan("M")
    np = player.now_playing()
    assert np is not None
    assert np["uri"] in {"spotify:track:1", "spotify:track:2"}
