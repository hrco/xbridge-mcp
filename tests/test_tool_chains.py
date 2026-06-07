"""
Tests for ToolChain, ChainStep, and ChainBuilder.
Validates sequential execution, context resolution, error-stopping, and builder patterns.
"""
import pytest
from unittest.mock import AsyncMock

from xbridge_mcp.tool_chains import ChainBuilder, ChainStep, ToolChain


# ---------------------------------------------------------------------------
# ToolChain core execution
# ---------------------------------------------------------------------------

class TestToolChainExecute:

    async def test_single_step_executes_and_returns_result(self):
        chain = ToolChain("single")
        fn = AsyncMock(return_value="result_a")
        chain.add_step("step_a", fn, {"key": "val"})

        result = await chain.execute()

        fn.assert_called_once_with(key="val")
        assert result["success"] is True
        assert result["steps_executed"] == 1
        assert result["final_result"] == "result_a"

    async def test_multiple_steps_execute_in_order(self):
        chain = ToolChain("multi")
        call_log = []

        async def step_a(**kwargs):
            call_log.append("a")
            return "a_out"

        async def step_b(**kwargs):
            call_log.append("b")
            return "b_out"

        chain.add_step("a", step_a, {})
        chain.add_step("b", step_b, {})

        result = await chain.execute()

        assert call_log == ["a", "b"]
        assert result["steps_executed"] == 2
        assert result["final_result"] == "b_out"

    async def test_stops_on_first_error_and_marks_failure(self):
        chain = ToolChain("fail")
        never_called = AsyncMock(return_value="nope")

        async def boom(**kwargs):
            raise RuntimeError("kaboom")

        chain.add_step("fail_step", boom, {})
        chain.add_step("unreachable", never_called, {})

        result = await chain.execute()

        assert result["success"] is False
        assert result["steps_executed"] == 0
        never_called.assert_not_called()
        assert "kaboom" in result["step_results"][0]["error"]

    async def test_empty_chain_returns_zero_steps(self):
        chain = ToolChain("empty")
        result = await chain.execute()

        assert result["steps_executed"] == 0
        assert result["steps_total"] == 0
        assert result["final_result"] is None
        assert result["success"] is True

    async def test_step_results_list_populated(self):
        chain = ToolChain("steps")
        chain.add_step("s1", AsyncMock(return_value="out1"), {})
        chain.add_step("s2", AsyncMock(return_value="out2"), {})

        result = await chain.execute()

        assert len(result["step_results"]) == 2
        assert result["step_results"][0]["step_name"] == "s1"
        assert result["step_results"][1]["step_name"] == "s2"
        assert all(s["success"] for s in result["step_results"])

    async def test_partial_failure_records_both_success_and_error(self):
        chain = ToolChain("partial")
        chain.add_step("ok", AsyncMock(return_value="ok_out"), {})

        async def fail(**kwargs):
            raise ValueError("bad")

        chain.add_step("fail", fail, {})

        result = await chain.execute()

        assert result["success"] is False
        assert result["step_results"][0]["success"] is True
        assert result["step_results"][1]["success"] is False


# ---------------------------------------------------------------------------
# Context / placeholder resolution
# ---------------------------------------------------------------------------

class TestContextResolution:

    async def test_last_result_placeholder_resolved(self):
        chain = ToolChain("ctx")
        chain.add_step("produce", AsyncMock(return_value="produced_value"), {})

        captured = {}

        async def consume(**kwargs):
            captured["data"] = kwargs.get("data")
            return "done"

        chain.add_step("consume", consume, {"data": "{last_result}"})
        await chain.execute()

        assert captured["data"] == "produced_value"

    async def test_step_n_result_placeholder_resolved(self):
        chain = ToolChain("indexed")
        chain.add_step("first", AsyncMock(return_value="first_val"), {})

        captured = {}

        async def second(**kwargs):
            captured["ref"] = kwargs.get("ref")
            return "second_val"

        chain.add_step("second", second, {"ref": "{step_0_result}"})
        await chain.execute()

        assert captured["ref"] == "first_val"

    async def test_unknown_placeholder_passes_through_unchanged(self):
        chain = ToolChain("passthrough")
        captured = {}

        async def step(**kwargs):
            captured["v"] = kwargs.get("v")
            return "done"

        chain.add_step("step", step, {"v": "{unknown_key}"})
        await chain.execute()

        assert captured["v"] == "{unknown_key}"

    async def test_non_placeholder_string_passes_through(self):
        chain = ToolChain("literal")
        captured = {}

        async def step(**kwargs):
            captured["v"] = kwargs.get("v")
            return "done"

        chain.add_step("step", step, {"v": "literal_value"})
        await chain.execute()

        assert captured["v"] == "literal_value"

    async def test_non_string_args_pass_through(self):
        chain = ToolChain("typed")
        captured = {}

        async def step(**kwargs):
            captured.update(kwargs)
            return "done"

        chain.add_step("step", step, {"count": 42, "flag": True, "items": [1, 2]})
        await chain.execute()

        assert captured["count"] == 42
        assert captured["flag"] is True
        assert captured["items"] == [1, 2]


# ---------------------------------------------------------------------------
# ChainStep dataclass
# ---------------------------------------------------------------------------

class TestChainStep:
    def test_defaults_result_and_error_to_none(self):
        async def fn(**kwargs): ...
        step = ChainStep(name="s", tool_function=fn, arguments={})
        assert step.result is None
        assert step.error is None

    def test_stores_name_and_arguments(self):
        async def fn(**kwargs): ...
        step = ChainStep(name="my_step", tool_function=fn, arguments={"q": "test"})
        assert step.name == "my_step"
        assert step.arguments == {"q": "test"}


# ---------------------------------------------------------------------------
# ChainBuilder.search_and_summarize
# ---------------------------------------------------------------------------

class TestChainBuilderSearchAndSummarize:

    def test_produces_two_step_chain(self):
        chain = ChainBuilder.search_and_summarize(
            search_tool=AsyncMock(),
            chat_tool=AsyncMock(),
            search_query="anything",
        )
        assert len(chain.steps) == 2

    def test_first_step_is_search(self):
        chain = ChainBuilder.search_and_summarize(
            search_tool=AsyncMock(),
            chat_tool=AsyncMock(),
            search_query="test",
        )
        assert "search" in chain.steps[0].name

    def test_second_step_is_summarize(self):
        chain = ChainBuilder.search_and_summarize(
            search_tool=AsyncMock(),
            chat_tool=AsyncMock(),
            search_query="test",
        )
        assert chain.steps[1].name == "summarize"

    async def test_executes_search_with_correct_query(self):
        search_mock = AsyncMock(return_value="results")
        chat_mock = AsyncMock(return_value="summary")

        chain = ChainBuilder.search_and_summarize(
            search_tool=search_mock,
            chat_tool=chat_mock,
            search_query="xBridge MCP",
        )
        await chain.execute()

        search_mock.assert_called_once()
        assert search_mock.call_args[1]["query"] == "xBridge MCP"

    async def test_summary_message_contains_search_results(self):
        search_mock = AsyncMock(return_value="<raw_search_output>")
        captured = {}

        async def chat(**kwargs):
            captured["message"] = kwargs.get("message", "")
            return "summary"

        chain = ChainBuilder.search_and_summarize(
            search_tool=search_mock,
            chat_tool=chat,
            search_query="test",
        )
        result = await chain.execute()

        assert result["success"] is True
        assert "<raw_search_output>" in captured["message"]

    async def test_custom_summary_instructions_used(self):
        search_mock = AsyncMock(return_value="data")
        captured = {}

        async def chat(**kwargs):
            captured["message"] = kwargs.get("message", "")
            return "done"

        chain = ChainBuilder.search_and_summarize(
            search_tool=search_mock,
            chat_tool=chat,
            search_query="test",
            summary_instructions="Give me 10 bullet points",
        )
        await chain.execute()

        assert "Give me 10 bullet points" in captured["message"]

    def test_x_search_type_used_in_chain_name(self):
        chain = ChainBuilder.search_and_summarize(
            search_tool=AsyncMock(),
            chat_tool=AsyncMock(),
            search_query="test",
            search_type="x",
        )
        assert "x" in chain.name


# ---------------------------------------------------------------------------
# ChainBuilder.multi_source_research
# ---------------------------------------------------------------------------

class TestChainBuilderMultiSourceResearch:

    def test_produces_three_step_chain(self):
        chain = ChainBuilder.multi_source_research(
            web_search_tool=AsyncMock(),
            x_search_tool=AsyncMock(),
            chat_tool=AsyncMock(),
            topic="MCP",
        )
        assert len(chain.steps) == 3

    async def test_all_three_steps_execute(self):
        web_mock = AsyncMock(return_value="web_results")
        x_mock = AsyncMock(return_value="x_results")
        chat_mock = AsyncMock(return_value="report")

        chain = ChainBuilder.multi_source_research(
            web_search_tool=web_mock,
            x_search_tool=x_mock,
            chat_tool=chat_mock,
            topic="AI agents",
        )
        result = await chain.execute()

        assert result["success"] is True
        assert result["steps_executed"] == 3
        web_mock.assert_called_once()
        x_mock.assert_called_once()
        chat_mock.assert_called_once()

    async def test_synthesis_receives_both_search_results(self):
        web_mock = AsyncMock(return_value="WEB_DATA")
        x_mock = AsyncMock(return_value="X_DATA")
        captured = {}

        async def chat(**kwargs):
            captured["message"] = kwargs.get("message", "")
            return "report"

        chain = ChainBuilder.multi_source_research(
            web_search_tool=web_mock,
            x_search_tool=x_mock,
            chat_tool=chat,
            topic="test_topic",
        )
        await chain.execute()

        assert "WEB_DATA" in captured["message"]
        assert "X_DATA" in captured["message"]

    async def test_topic_in_web_search_query(self):
        web_mock = AsyncMock(return_value="results")
        captured_web = {}

        async def web_search(**kwargs):
            captured_web["query"] = kwargs.get("query", "")
            return "results"

        chain = ChainBuilder.multi_source_research(
            web_search_tool=web_search,
            x_search_tool=AsyncMock(return_value="x"),
            chat_tool=AsyncMock(return_value="r"),
            topic="quantum_computing",
        )
        await chain.execute()

        assert "quantum_computing" in captured_web["query"]


# ---------------------------------------------------------------------------
# ChainBuilder.debug_workflow
# ---------------------------------------------------------------------------

class TestChainBuilderDebugWorkflow:

    def test_produces_two_step_chain(self):
        chain = ChainBuilder.debug_workflow(
            x_search_tool=AsyncMock(),
            chat_tool=AsyncMock(),
            error_message="AttributeError: 'NoneType'",
        )
        assert len(chain.steps) == 2

    async def test_error_message_in_x_search_query(self):
        captured = {}

        async def x_search(**kwargs):
            captured["query"] = kwargs.get("query", "")
            return "issues"

        chain = ChainBuilder.debug_workflow(
            x_search_tool=x_search,
            chat_tool=AsyncMock(return_value="fix"),
            error_message="ImportError: no module named foo",
        )
        await chain.execute()

        assert "ImportError: no module named foo" in captured["query"]

    async def test_tech_stack_included_in_search_query(self):
        captured = {}

        async def x_search(**kwargs):
            captured["query"] = kwargs.get("query", "")
            return "issues"

        chain = ChainBuilder.debug_workflow(
            x_search_tool=x_search,
            chat_tool=AsyncMock(return_value="fix"),
            error_message="KeyError: 'id'",
            tech_stack="Python FastAPI",
        )
        await chain.execute()

        assert "Python FastAPI" in captured["query"]

    async def test_fix_step_receives_error_and_x_results(self):
        captured = {}

        async def chat(**kwargs):
            captured["message"] = kwargs.get("message", "")
            captured["system_prompt"] = kwargs.get("system_prompt", "")
            return "fix"

        chain = ChainBuilder.debug_workflow(
            x_search_tool=AsyncMock(return_value="X_ISSUES"),
            chat_tool=chat,
            error_message="TypeError: unexpected kwarg",
            tech_stack="Go",
        )
        await chain.execute()

        assert "TypeError: unexpected kwarg" in captured["message"]
        assert "X_ISSUES" in captured["message"]
        assert "Go" in captured["message"]

    async def test_fix_step_has_debugging_system_prompt(self):
        captured = {}

        async def chat(**kwargs):
            captured["system_prompt"] = kwargs.get("system_prompt", "")
            return "fix"

        chain = ChainBuilder.debug_workflow(
            x_search_tool=AsyncMock(return_value="issues"),
            chat_tool=chat,
            error_message="error",
        )
        await chain.execute()

        assert captured["system_prompt"]  # non-empty
        assert "debug" in captured["system_prompt"].lower()

    async def test_both_steps_execute_successfully(self):
        chain = ChainBuilder.debug_workflow(
            x_search_tool=AsyncMock(return_value="found issues"),
            chat_tool=AsyncMock(return_value="here is the fix"),
            error_message="SyntaxError",
        )
        result = await chain.execute()

        assert result["success"] is True
        assert result["steps_executed"] == 2
