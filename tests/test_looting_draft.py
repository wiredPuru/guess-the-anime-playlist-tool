"""Shared record shop, first-come draft claims, and normal-playback handoff."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from _app_scripts.file.web_server import looting_draft, web_host_actions, web_server
from core.game_state import state


@pytest.fixture
def pool():
    return [(f"Anime {i}", {"OP": [f"{i}-OP1.webm"]}) for i in range(30)]


def _events(client, name):
    return [next(iter(item["args"]), None)
            for item in client.get_received() if item["name"] == name]


@pytest.mark.parametrize(
    ("library_size", "picks", "bin_sizes"),
    [(250, 2, [67, 67, 66]), (31, 2, [11, 10, 10]), (300, 70, [70, 70, 70])],
)
def test_shop_stocks_about_200_choices_and_scales_to_the_library_and_draft(library_size, picks, bin_sizes):
    pool = [(f"Anime {i}", {"OP": [f"{i}-OP1.webm"]}) for i in range(library_size)]
    roster = {"a": "Alice", "b": "Bob"}
    draft = looting_draft.LootingDraft(roster, picks, 60, pool)
    shop = draft.view("a", roster)
    assert [len(cards) for cards in shop["bins"]] == bin_sizes
    assert len({title for title, _ in draft.cards}) == sum(bin_sizes)


def test_shop_keeps_inspections_and_claims_private(monkeypatch, pool):
    for name, value in {
        "_app": None, "_socketio": None, "_looting_draft": None,
        "_looting_tokens": {}, "_connected_players": {},
        "_host_sids": set(), "_player_meta": {}, "_host_password": "test",
    }.items():
        monkeypatch.setattr(web_server, name, value)
    web_server._build_app()
    host = web_server._socketio.test_client(web_server._app)
    host.emit("claim_host", {"password": "test"})

    def connect(name, key):
        client = web_server._socketio.test_client(web_server._app)
        client.emit("set_name", {"name": name, "looting_token": key * 32})
        return client

    a = connect("Alice", "a")
    b = connect("Bob", "b")
    draft_id = web_server.start_looting(next(iter(web_server._host_sids)), 1, 60, lambda: pool)
    for player in (a, b):
        view = _events(player, "looting_state")[-1]
        assert len(view["bins"]) == 3 and view["players"] == 2
        assert view["inspected"] is None
        assert all(card["title"] is None for bin_cards in view["bins"] for card in bin_cards)

    def pick(client, action, target):
        client.emit("looting_pick", {"id": draft_id, "action": action, "target": target})

    pick(a, "claim", len(pool))
    assert _events(a, "looting_error")[-1]["message"] == "That pick is no longer available to you."
    pick(a, "inspect", 0)
    assert _events(b, "looting_state") == []
    pick(b, "inspect", 0)
    for player in (a, b):
        view = _events(player, "looting_state")[-1]
        sleeve = view["bins"][0][0]
        assert view["inspected"] == 0
        assert sleeve["title"] and not sleeve["taken"]

    simultaneous = Barrier(2)

    def race(client):
        simultaneous.wait(timeout=3)
        pick(client, "claim", 0)

    with ThreadPoolExecutor(2) as workers:
        contenders = [workers.submit(race, player) for player in (a, b)]
        for contender in contenders:
            contender.result(timeout=5)
    draft = web_server._looting_draft
    winner, loser = (a, b) if draft.owners[0] == "a" * 32 else (b, a)
    events = {item["name"]: item["args"] for item in loser.get_received()}
    assert events["looting_error"][-1]["message"] == "Someone already claimed that anime."
    loser_view = events["looting_state"][-1]
    assert loser_view["bins"][0][0] == {"id": 0, "title": None, "taken": True}
    assert loser_view["picks"] == []

    pick(loser, "inspect", 1)
    assert _events(loser, "looting_state")[-1]["bins"][0][0] == {"id": 0, "title": None, "taken": False}

    pick(winner, "inspect", 1)
    pick(winner, "claim", 1)
    assert _events(winner, "looting_error")[-1]["message"] == "Release a pick to make room."
    assert _events(loser, "looting_state") == []

    pick(loser, "inspect", 0)
    assert _events(loser, "looting_state")[-1]["bins"][0][0]["title"] is None
    pick(winner, "release", 0)
    assert _events(loser, "looting_state")[-1]["bins"][0][0]["title"] == draft.cards[0][0]
    pick(loser, "claim", 0)
    assert 0 in draft.owners

    name, key = ("Alice", "a") if loser is a else ("Bob", "b")
    loser.disconnect()
    rejoined = connect(name, key)
    assert _events(rejoined, "looting_state")[-1]["picks"][0]["id"] == 0

    draft.deadline -= 70
    pick(winner, "claim", 1)
    assert _events(winner, "looting_error")[-1]["message"] == "The draft has closed."
    entries = web_server.finish_looting(draft_id)
    filenames = {entry["filename"] for entry in entries}
    assert len(filenames) == 2
    assert filenames <= {tracks["OP"][0] for _, tracks in draft.cards}
    assert all(entry["looting_effect"] in ("blur", "pixelize") for entry in entries)
    assert [(entry["filename"], entry["looted_by"]) for entry in entries if entry["looted_by"]] == [
        (draft.cards[0][1]["OP"][0], name)
    ]
    assert _events(rejoined, "looting_credit") == []
    monkeypatch.setattr(web_server, "_looting_credit", None)
    web_server.push_looting_credit(name)
    assert _events(rejoined, "looting_credit") == [{"name": name}]
    web_server.push_looting_credit(None)
    assert _events(rejoined, "looting_credit") == [{"name": None}]
    host_view = _events(host, "looting_state")[-1]
    assert host_view["autoFilled"] == 1 and "picks" not in host_view


def test_theme_type_is_weighted_before_choosing_track(monkeypatch):
    draft = looting_draft.LootingDraft({"p": "Player"}, 1, 60, [
        ("Anime", {"OP": ["op1", "op2"], "ED": ["ed"]}),
    ])

    def choose_type(kinds, weights):
        assert list(zip(kinds, weights)) == [("OP", 60), ("ED", 30)]
        return ["ED"]

    monkeypatch.setattr(looting_draft.random, "choices", choose_type)
    assert draft.finish()[0]["filename"] == "ed"


def test_click_can_claim_before_hover_preview_arrives(pool):
    draft = looting_draft.LootingDraft({"a": "Alice", "b": "Bob"}, 1, 60, pool)
    draft.change("a", "claim", 3)
    draft.change("a", "inspect", 3)
    assert draft.view("a", draft.roster)["picks"] == [{"id": 3, "title": draft.cards[3][0]}]
    assert not draft.view("b", draft.roster)["bins"][0][1]["taken"]
    with pytest.raises(ValueError, match="already claimed"):
        draft.change("b", "claim", 3)


def test_drafted_set_queues_without_replacing_fixed_playback(monkeypatch):
    monkeypatch.setattr(state.lightning, "fixed_lightning_queue", {"name": "Other set"})
    monkeypatch.setattr(state.lightning, "fixed_lightning_round_playlist_data", None)
    monkeypatch.setattr(web_server, "finish_looting", lambda _id: ["op1.webm"])
    queued, closed = [], []
    monkeypatch.setattr(web_server, "close_looting", lambda *args: closed.append(args))
    monkeypatch.setattr(web_host_actions.transport, "queue_looting_songs", queued.append)
    web_host_actions._queue_looting_if_available("draft", "host")
    assert queued == [["op1.webm"]]
    assert closed[0][0] == "draft"
    assert state.lightning.fixed_lightning_queue == {"name": "Other set"}
