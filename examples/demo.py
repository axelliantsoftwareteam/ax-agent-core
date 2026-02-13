from __future__ import annotations

from ax_agent_core.demo import build_demo_agent, default_scripted_prompts


def main() -> None:
    agent = build_demo_agent("examples/config.json")
    session_id = "examples-demo"

    for prompt in default_scripted_prompts():
        response = agent.runtime.handle(prompt, session_id=session_id)
        print(f"User: {prompt}")
        print(f"Assistant: {response.content}")
        if response.tool_result and response.tool_result.output is not None:
            print(f"Tool Output: {response.tool_result.output}")
        print("-")

    print("MCP health:", agent.mcp_bridge.health())


if __name__ == "__main__":
    main()
