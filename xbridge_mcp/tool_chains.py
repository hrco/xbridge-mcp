#!/usr/bin/env python3
"""
Tool Chaining for xBridge MCP

Provides composable tool chains for complex multi-step workflows.
Examples: web search → summarize, X search → analyze → generate report
"""

from typing import Any, Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass
import json


@dataclass
class ChainStep:
    """Represents a single step in a tool chain."""
    name: str
    tool_function: Callable[..., Awaitable[Any]]
    arguments: Dict[str, Any]
    result: Optional[Any] = None
    error: Optional[str] = None


class ToolChain:
    """Manages execution of chained tool operations."""

    def __init__(self, name: str):
        """
        Initialize tool chain.

        Args:
            name: Name of the chain for identification
        """
        self.name = name
        self.steps: List[ChainStep] = []
        self.context: Dict[str, Any] = {}

    def add_step(self,
                 step_name: str,
                 tool_function: Callable[..., Awaitable[Any]],
                 arguments: Dict[str, Any]):
        """
        Add a step to the chain.

        Args:
            step_name: Human-readable name for this step
            tool_function: Async function to execute
            arguments: Arguments to pass to the function
        """
        step = ChainStep(
            name=step_name,
            tool_function=tool_function,
            arguments=arguments,
        )
        self.steps.append(step)

    async def execute(self) -> Dict[str, Any]:
        """
        Execute all steps in the chain sequentially.

        Returns:
            Dictionary with chain execution results
        """
        results = {
            "chain_name": self.name,
            "steps_executed": 0,
            "steps_total": len(self.steps),
            "success": True,
            "step_results": [],
            "final_result": None,
        }

        for i, step in enumerate(self.steps):
            try:
                # Execute step with current context available
                step_args = self._prepare_arguments(step.arguments, self.context)
                step.result = await step.tool_function(**step_args)

                # Update context with result (accessible in next steps)
                self.context[f"step_{i}_result"] = step.result
                self.context["last_result"] = step.result

                results["step_results"].append({
                    "step_name": step.name,
                    "success": True,
                    "result": step.result,
                })
                results["steps_executed"] += 1

            except Exception as e:
                step.error = str(e)
                results["success"] = False
                results["step_results"].append({
                    "step_name": step.name,
                    "success": False,
                    "error": str(e),
                })
                # Stop execution on error
                break

        # Set final result to last successful step result
        if results["steps_executed"] > 0:
            results["final_result"] = self.context.get("last_result")

        return results

    def _prepare_arguments(self,
                          template_args: Dict[str, Any],
                          context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare arguments by resolving context references.

        Supports special syntax:
        - "{last_result}": Replace with result from previous step
        - "{step_0_result}": Replace with result from specific step

        Args:
            template_args: Argument template with possible placeholders
            context: Current chain context

        Returns:
            Resolved arguments
        """
        resolved = {}
        for key, value in template_args.items():
            if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
                # Extract context key
                context_key = value[1:-1]
                resolved[key] = context.get(context_key, value)
            else:
                resolved[key] = value
        return resolved


# =============================================================================
# Pre-built Chain Builders
# =============================================================================

class ChainBuilder:
    """Helper to build common tool chain patterns."""

    @staticmethod
    def search_and_summarize(
        search_tool: Callable,
        chat_tool: Callable,
        search_query: str,
        search_type: str = "web",
        model: str = "grok-4-1-fast",
        summary_instructions: str = "Summarize the key findings in 3-5 bullet points",
    ) -> ToolChain:
        """
        Create a chain that searches and then summarizes results.

        Args:
            search_tool: Web or X search tool function
            chat_tool: Chat tool function
            search_query: Query to search for
            search_type: "web" or "x"
            model: Model to use
            summary_instructions: How to summarize

        Returns:
            Configured ToolChain
        """
        chain = ToolChain(name=f"{search_type}_search_and_summarize")

        # Step 1: Search
        chain.add_step(
            step_name=f"{search_type}_search",
            tool_function=search_tool,
            arguments={"query": search_query, "model": model}
        )

        # Step 2: Summarize results
        chain.add_step(
            step_name="summarize",
            tool_function=chat_tool,
            arguments={
                "message": f"{summary_instructions}\n\nSearch results:\n{{last_result}}",
                "model": model,
            }
        )

        return chain

    @staticmethod
    def multi_source_research(
        web_search_tool: Callable,
        x_search_tool: Callable,
        chat_tool: Callable,
        topic: str,
        model: str = "grok-4-1-fast",
    ) -> ToolChain:
        """
        Create a chain that researches a topic from web + X, then synthesizes.

        Args:
            web_search_tool: Web search tool function
            x_search_tool: X search tool function
            chat_tool: Chat tool function
            topic: Research topic
            model: Model to use

        Returns:
            Configured ToolChain
        """
        chain = ToolChain(name="multi_source_research")

        # Step 1: Web search
        chain.add_step(
            step_name="web_research",
            tool_function=web_search_tool,
            arguments={"query": f"Latest information about {topic}", "model": model}
        )

        # Step 2: X search
        chain.add_step(
            step_name="x_research",
            tool_function=x_search_tool,
            arguments={"query": f"Discussions about {topic}", "model": model}
        )

        # Step 3: Synthesize findings
        chain.add_step(
            step_name="synthesize",
            tool_function=chat_tool,
            arguments={
                "message": (
                    f"Based on web and X research about '{topic}', "
                    "create a comprehensive report with:\n"
                    "1. Key findings from web sources\n"
                    "2. Social media sentiment and discussions\n"
                    "3. Notable insights or trends\n"
                    "4. Summary conclusion\n\n"
                    "Web results: {step_0_result}\n\n"
                    "X results: {step_1_result}"
                ),
                "model": model,
            }
        )

        return chain

    @staticmethod
    def debug_workflow(
        x_search_tool: Callable,
        chat_tool: Callable,
        error_message: str,
        tech_stack: Optional[str] = None,
        model: str = "grok-4",
    ) -> ToolChain:
        """
        Create a chain for debugging: search X for similar issues → generate fix.

        Args:
            x_search_tool: X search tool function
            chat_tool: Chat tool function
            error_message: The error message to debug
            tech_stack: Optional technology context
            model: Model to use (grok-4 for better reasoning)

        Returns:
            Configured ToolChain
        """
        chain = ToolChain(name="debug_workflow")

        # Step 1: Search X for similar issues
        search_query = error_message
        if tech_stack:
            search_query = f"{tech_stack} {error_message}"

        chain.add_step(
            step_name="search_similar_issues",
            tool_function=x_search_tool,
            arguments={
                "query": f"{search_query} solution OR fix OR solved",
                "model": model,
            }
        )

        # Step 2: Generate fix based on findings
        chain.add_step(
            step_name="generate_fix",
            tool_function=chat_tool,
            arguments={
                "message": (
                    f"Error: {error_message}\n"
                    + (f"Tech stack: {tech_stack}\n" if tech_stack else "")
                    + "\nBased on these X discussions:\n{last_result}\n\n"
                    "Please provide:\n"
                    "1. Root cause analysis\n"
                    "2. Step-by-step fix\n"
                    "3. Code examples if applicable\n"
                    "4. Prevention tips"
                ),
                "model": model,
                "system_prompt": "You are an expert debugging assistant.",
            }
        )

        return chain
