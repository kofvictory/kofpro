import json

from art_p0.fakes import FakeAssistantMessage, FakeToolCall
from art_p0.trajectory import TrajectoryStore, to_jsonable


def test_to_jsonable_handles_fake_messages():
    msg = FakeAssistantMessage(tool_calls=[FakeToolCall(name="x")], content="")
    data = to_jsonable(msg)
    assert data["tool_calls"][0]["name"] == "x"


def test_trajectory_store_round_trip(tmp_path):
    store = TrajectoryStore(tmp_path)
    path = store.write("r1", {"messages": [FakeAssistantMessage(content="hi")]})
    loaded = json.loads(path.read_text())
    assert loaded["messages"][0]["content"] == "hi"
