from ax_agent_core.demo import build_demo_agent


def main() -> None:
    agent = build_demo_agent()
    session_id = "demo"
    prompts = [
        "tool:math {\"expression\": \"5 * (3 + 2)\"}",
        "tool:http_get {\"url\": \"https://example.com/status\"}",
        "tool:json_formatter {\"payload\": {\"service\": \"api\", \"status\": \"ok\"}}",
        "Summarize current system state.",
    ]
    for prompt in prompts:
        response = agent.runtime.handle(prompt, session_id=session_id)
        print(f"User: {prompt}")
        print(f"Assistant: {response.content}")
        if response.tool_result and response.tool_result.output is not None:
            print(f"Tool Output: {response.tool_result.output}")
        print("-")


if __name__ == "__main__":
    main()
