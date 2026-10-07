# Standard library imports.
from asyncio import run, sleep
from os import getenv

# Third party imports.
from fastmcp import Client

# Constants.
SERVER = "GitLab MCP Server MCP Server"
URL = getenv("MCP_URL", "http://localhost:8003/mcp")
HEALTH_ATTEMPTS = 5
HEALTH_RETRY_DELAY = 1
GREEN = "\033[32m"
RESET = "\033[0m"


async def main() -> None:

    # Wait for the MCP server to become available.
    for attempt in range(1, HEALTH_ATTEMPTS + 1):
        try:
            async with Client(URL) as client:
                await client.list_tools()
            break
        except Exception as error:
            if attempt == HEALTH_ATTEMPTS:
                raise RuntimeError(f"The {SERVER} is not up.") from error
            await sleep(HEALTH_RETRY_DELAY)

    async with Client(URL) as client:
        expected_tools = {"create_issue", "fetch_issue", "update_issue", "delete_issue"}
        exposed_tools = {tool.name for tool in await client.list_tools()}
        assert exposed_tools == expected_tools, f"Unexpected tools: {exposed_tools}"
        print(
            f" {GREEN}✔{RESET} The {SERVER} exposes: {', '.join(sorted(exposed_tools))}"
        )

    print(f"[+] The {SERVER} is up-up")


if __name__ == "__main__":
    run(main())
