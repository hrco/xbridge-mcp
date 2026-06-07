"""
Tests for SessionManager — CRUD, persistence, conversation history, disk reload.
Uses tmp_path to isolate each test from the real .grok_sessions/ directory.
"""
import json
import pytest
from pathlib import Path

from xbridge_mcp.session_manager import SessionManager


@pytest.fixture
def sm(tmp_path) -> SessionManager:
    """Fresh SessionManager backed by a throw-away temp directory."""
    return SessionManager(storage_dir=str(tmp_path / "sessions"))


# ---------------------------------------------------------------------------
# Session creation
# ---------------------------------------------------------------------------

class TestSessionCreate:
    def test_returns_uuid_string(self, sm):
        sid = sm.create_session()
        assert isinstance(sid, str)
        assert len(sid) == 36

    def test_session_stored_in_memory(self, sm):
        sid = sm.create_session()
        assert sm.get_session(sid) is not None

    def test_conversation_history_starts_empty(self, sm):
        sid = sm.create_session()
        assert sm.get_session(sid)["conversation_history"] == []

    def test_tool_chain_history_starts_empty(self, sm):
        sid = sm.create_session()
        assert sm.get_session(sid)["tool_chain_history"] == []

    def test_session_id_recorded_in_session_data(self, sm):
        sid = sm.create_session()
        assert sm.get_session(sid)["session_id"] == sid

    def test_custom_name_stored(self, sm):
        sid = sm.create_session(name="Project Alpha")
        assert sm.get_session(sid)["name"] == "Project Alpha"

    def test_default_name_includes_id_prefix(self, sm):
        sid = sm.create_session()
        name = sm.get_session(sid)["name"]
        assert sid[:8] in name

    def test_custom_metadata_stored(self, sm):
        sid = sm.create_session(metadata={"env": "test", "version": "2.1"})
        meta = sm.get_session(sid)["metadata"]
        assert meta["env"] == "test"
        assert meta["version"] == "2.1"

    def test_timestamps_present(self, sm):
        sid = sm.create_session()
        session = sm.get_session(sid)
        assert "created_at" in session
        assert "updated_at" in session

    def test_persists_json_file_to_disk(self, sm):
        sid = sm.create_session(name="Persist Me")
        session_file = Path(sm.storage_dir) / f"{sid}.json"
        assert session_file.exists()

    def test_disk_file_contains_session_id(self, sm):
        sid = sm.create_session()
        session_file = Path(sm.storage_dir) / f"{sid}.json"
        data = json.loads(session_file.read_text())
        assert data["session_id"] == sid

    def test_multiple_sessions_get_unique_ids(self, sm):
        ids = {sm.create_session() for _ in range(5)}
        assert len(ids) == 5


# ---------------------------------------------------------------------------
# Session retrieval
# ---------------------------------------------------------------------------

class TestSessionGet:
    def test_returns_none_for_unknown_id(self, sm):
        assert sm.get_session("does-not-exist") is None

    def test_returns_correct_session(self, sm):
        sid = sm.create_session(name="Find Me")
        session = sm.get_session(sid)
        assert session["name"] == "Find Me"


# ---------------------------------------------------------------------------
# Session listing
# ---------------------------------------------------------------------------

class TestSessionList:
    def test_empty_when_no_sessions(self, sm):
        assert sm.list_sessions() == []

    def test_lists_all_sessions(self, sm):
        sm.create_session(name="A")
        sm.create_session(name="B")
        sessions = sm.list_sessions()
        assert len(sessions) == 2
        names = {s["name"] for s in sessions}
        assert names == {"A", "B"}

    def test_list_entry_has_required_keys(self, sm):
        sm.create_session()
        entry = sm.list_sessions()[0]
        for key in ("session_id", "name", "created_at", "updated_at", "message_count"):
            assert key in entry

    def test_message_count_reflects_history(self, sm):
        sid = sm.create_session()
        sm.add_message(sid, "user", "hello")
        sm.add_message(sid, "assistant", "hi")
        entry = next(s for s in sm.list_sessions() if s["session_id"] == sid)
        assert entry["message_count"] == 2


# ---------------------------------------------------------------------------
# Session deletion
# ---------------------------------------------------------------------------

class TestSessionDelete:
    def test_removes_from_memory(self, sm):
        sid = sm.create_session()
        sm.delete_session(sid)
        assert sm.get_session(sid) is None

    def test_removes_json_file(self, sm):
        sid = sm.create_session()
        session_file = Path(sm.storage_dir) / f"{sid}.json"
        assert session_file.exists()
        sm.delete_session(sid)
        assert not session_file.exists()

    def test_delete_nonexistent_does_not_raise(self, sm):
        sm.delete_session("nonexistent-id")  # must not raise

    def test_other_sessions_unaffected(self, sm):
        sid_a = sm.create_session(name="Keep")
        sid_b = sm.create_session(name="Delete")
        sm.delete_session(sid_b)
        assert sm.get_session(sid_a) is not None


# ---------------------------------------------------------------------------
# Message management
# ---------------------------------------------------------------------------

class TestAddMessage:
    def test_appends_message_to_history(self, sm):
        sid = sm.create_session()
        sm.add_message(sid, "user", "Hello")
        history = sm.get_conversation_history(sid, format_for_api=False)
        assert len(history) == 1
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello"

    def test_multiple_messages_ordered(self, sm):
        sid = sm.create_session()
        sm.add_message(sid, "user", "First")
        sm.add_message(sid, "assistant", "Second")
        history = sm.get_conversation_history(sid, format_for_api=False)
        assert history[0]["content"] == "First"
        assert history[1]["content"] == "Second"

    def test_message_has_timestamp(self, sm):
        sid = sm.create_session()
        sm.add_message(sid, "user", "hi")
        msg = sm.get_conversation_history(sid, format_for_api=False)[0]
        assert "timestamp" in msg

    def test_custom_metadata_stored_on_message(self, sm):
        sid = sm.create_session()
        sm.add_message(sid, "user", "hi", metadata={"model": "grok-4"})
        msg = sm.get_conversation_history(sid, format_for_api=False)[0]
        assert msg["metadata"]["model"] == "grok-4"

    def test_raises_for_nonexistent_session(self, sm):
        with pytest.raises(ValueError, match="not found"):
            sm.add_message("bad-id", "user", "oops")

    def test_message_persisted_to_disk(self, sm):
        sid = sm.create_session()
        sm.add_message(sid, "user", "Persist me")
        data = json.loads((Path(sm.storage_dir) / f"{sid}.json").read_text())
        assert data["conversation_history"][0]["content"] == "Persist me"


# ---------------------------------------------------------------------------
# Conversation history retrieval
# ---------------------------------------------------------------------------

class TestGetConversationHistory:
    def test_api_format_strips_metadata_and_timestamp(self, sm):
        sid = sm.create_session()
        sm.add_message(sid, "user", "Hi", metadata={"model": "grok-4"})
        history = sm.get_conversation_history(sid, format_for_api=True)
        assert history == [{"role": "user", "content": "Hi"}]

    def test_full_format_includes_metadata(self, sm):
        sid = sm.create_session()
        sm.add_message(sid, "user", "Hi", metadata={"model": "grok-4"})
        history = sm.get_conversation_history(sid, format_for_api=False)
        assert "metadata" in history[0]

    def test_limit_returns_most_recent_messages(self, sm):
        sid = sm.create_session()
        for i in range(5):
            sm.add_message(sid, "user", f"msg {i}")
        history = sm.get_conversation_history(sid, limit=3, format_for_api=True)
        assert len(history) == 3
        assert history[-1]["content"] == "msg 4"

    def test_no_limit_returns_all(self, sm):
        sid = sm.create_session()
        for i in range(5):
            sm.add_message(sid, "user", f"msg {i}")
        assert len(sm.get_conversation_history(sid)) == 5

    def test_raises_for_nonexistent_session(self, sm):
        with pytest.raises(ValueError, match="not found"):
            sm.get_conversation_history("bad-id")


# ---------------------------------------------------------------------------
# Persistence across reload
# ---------------------------------------------------------------------------

class TestPersistenceOnReload:
    def test_sessions_survive_new_instance(self, tmp_path):
        storage = str(tmp_path / "sessions")
        sm1 = SessionManager(storage_dir=storage)
        sid = sm1.create_session(name="Survivor")
        sm1.add_message(sid, "user", "remember me")

        sm2 = SessionManager(storage_dir=storage)
        session = sm2.get_session(sid)
        assert session is not None
        assert session["name"] == "Survivor"

    def test_conversation_history_survives_reload(self, tmp_path):
        storage = str(tmp_path / "sessions")
        sm1 = SessionManager(storage_dir=storage)
        sid = sm1.create_session()
        sm1.add_message(sid, "user", "reload test")

        sm2 = SessionManager(storage_dir=storage)
        history = sm2.get_conversation_history(sid, format_for_api=False)
        assert history[0]["content"] == "reload test"

    def test_multiple_sessions_all_reload(self, tmp_path):
        storage = str(tmp_path / "sessions")
        sm1 = SessionManager(storage_dir=storage)
        ids = [sm1.create_session(name=f"S{i}") for i in range(3)]

        sm2 = SessionManager(storage_dir=storage)
        for sid in ids:
            assert sm2.get_session(sid) is not None


# ---------------------------------------------------------------------------
# Clear conversation
# ---------------------------------------------------------------------------

class TestClearConversation:
    def test_clears_conversation_history(self, sm):
        sid = sm.create_session()
        sm.add_message(sid, "user", "hi")
        sm.clear_conversation(sid)
        assert sm.get_conversation_history(sid) == []

    def test_clears_tool_chain_history(self, sm):
        sid = sm.create_session()
        sm.add_tool_chain_step(sid, "step", "grok-chat", {}, "result")
        sm.clear_conversation(sid)
        assert sm.get_session(sid)["tool_chain_history"] == []

    def test_session_still_exists_after_clear(self, sm):
        sid = sm.create_session()
        sm.add_message(sid, "user", "hi")
        sm.clear_conversation(sid)
        assert sm.get_session(sid) is not None

    def test_clear_nonexistent_is_noop(self, sm):
        sm.clear_conversation("nonexistent-id")  # must not raise


# ---------------------------------------------------------------------------
# Tool chain step recording
# ---------------------------------------------------------------------------

class TestAddToolChainStep:
    def test_records_step_in_tool_chain_history(self, sm):
        sid = sm.create_session()
        sm.add_tool_chain_step(
            sid,
            step_name="search",
            tool_name="grok-web-search",
            arguments={"query": "test"},
            result="some results",
        )
        session = sm.get_session(sid)
        assert len(session["tool_chain_history"]) == 1
        step = session["tool_chain_history"][0]
        assert step["step_name"] == "search"
        assert step["tool_name"] == "grok-web-search"

    def test_result_truncated_to_1000_chars(self, sm):
        sid = sm.create_session()
        long_result = "x" * 5000
        sm.add_tool_chain_step(sid, "s", "tool", {}, long_result)
        step = sm.get_session(sid)["tool_chain_history"][0]
        assert len(step["result"]) <= 1000

    def test_raises_for_nonexistent_session(self, sm):
        with pytest.raises(ValueError, match="not found"):
            sm.add_tool_chain_step("bad-id", "s", "tool", {}, "r")
