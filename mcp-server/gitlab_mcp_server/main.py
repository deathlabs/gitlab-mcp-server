# Standard library imports.
from collections.abc import Callable
from functools import wraps
from inspect import signature
from os import environ
from pathlib import Path
from typing import Any

# Third party imports.
from agentmesh.governance import govern
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

# Local imports.
from tools import TOOLS
from tools.tools import get_configuration, validate_target

POLICY_FILE_PATH = str(Path(__file__).with_name("policy.yaml"))


def get_policy(file_path: str = POLICY_FILE_PATH) -> str:
    """Read the policy from the provided file path.

    Returns:
        The policy as a string.
    """
    with open(file=file_path, encoding="UTF-8", mode="r") as policy_file:
        return policy_file.read()


def apply_policy(
    fn: Callable[..., Any], policy: str, agent_id: str
) -> Callable[..., Any]:
    """Return a policy-protected version of a function.

    Args:
        fn: The function to protect.
        policy: The policy to enforce.
        agent_id: The agent identifier to use when evaluating the policy.

    Returns:
        A function that checks the policy before calling `fn`.
    """

    # Create a callable that evaluates the policy before invoking the function.
    def invoke(action: dict[str, str], **kwargs: Any) -> Any:
        return fn(**kwargs)

    governor = govern(fn=invoke, policy=policy, agent_id=agent_id)
    tool_signature = signature(fn)

    # Restore the function's signature so it can be registered as a tool.
    @wraps(fn)
    def protected_function(*args, **kwargs):
        bound = tool_signature.bind(*args, **kwargs)
        bound.apply_defaults()
        validate_target(bound.arguments["project_id"], bound.arguments.get("issue_iid"))
        return governor(action={"type": fn.__name__}, **bound.arguments)

    return protected_function


def main() -> None:
    """Start the MCP server."""

    # Check if the FASTMCP_PORT environment variable is set.
    if "FASTMCP_PORT" not in environ:
        raise RuntimeError("The FASTMCP_PORT environment variable is not set.")

    # Get the FASTMCP_PORT environment variable.
    fastmcp_port = int(environ["FASTMCP_PORT"])

    get_configuration()

    # Init an MCP server.
    mcp = FastMCP(name="gitlab_mcp_server")

    # Read the policy file.
    policy = get_policy()

    # Register tools with the MCP server.
    for tool in TOOLS:
        tool_with_policy_applied = apply_policy(
            tool,
            policy=policy,
            agent_id="gitlab_mcp_server",
        )
        mcp.add_tool(tool_with_policy_applied)

    @mcp.custom_route("/api/v1/health", methods=["GET"])
    async def health(request: Request) -> JSONResponse:
        """Respond to health checks.

        Returns:
            A JSON-based response that indicates the service is running.
        """
        return JSONResponse(content={"status": "ok"})

    # Start the MCP server.
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=fastmcp_port,
    )


if __name__ == "__main__":
    main()
