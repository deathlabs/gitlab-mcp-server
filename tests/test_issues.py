# Standard library imports.
import json
import sys
import unittest
from os import environ
from pathlib import Path
from unittest.mock import patch

# Third party imports.
import httpx
from agentmesh.governance import GovernanceDenied
from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError

# Local imports.
sys.path.insert(
    0, str(Path(__file__).resolve().parents[1] / "mcp-server/gitlab_mcp_server")
)
from main import apply_policy, get_policy
from tools import TOOLS, tools


class IssueTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(
            environ,
            {
                "GITLAB_URL": "https://gitlab.example/team",
                "GITLAB_TOKEN": "secret-token",
            },
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.requests = []

    def client(self, request):
        self.requests.append(request)
        return httpx.Response(
            204 if request.method == "DELETE" else 200, json={"iid": 7}
        )

    def run_tool(self, fn, *args, **kwargs):
        client_type = httpx.Client
        with patch.object(
            tools.httpx,
            "Client",
            side_effect=lambda **options: client_type(
                transport=httpx.MockTransport(self.client), **options
            ),
        ):
            return apply_policy(fn, get_policy(), "gitlab_mcp_server")(*args, **kwargs)

    def test_crud_endpoints_and_fields(self):
        self.run_tool(
            tools.create_issue,
            "group/project",
            "Title",
            description="Body",
            labels=["bug"],
            assignee_ids=[4],
        )
        self.run_tool(tools.fetch_issue, 42, 7)
        self.run_tool(
            tools.update_issue,
            "group/project",
            7,
            description="",
            labels=[],
            assignee_ids=[],
            state_event="close",
        )
        deleted = self.run_tool(tools.delete_issue, 42, 7)
        self.assertTrue(deleted["deleted"])
        self.assertEqual(
            [r.method for r in self.requests], ["POST", "GET", "PUT", "DELETE"]
        )
        self.assertEqual(
            self.requests[0].url.raw_path,
            b"/team/api/v4/projects/group%2Fproject/issues",
        )
        self.assertEqual(self.requests[1].url.path, "/team/api/v4/projects/42/issues/7")
        self.assertEqual(
            json.loads(self.requests[0].content),
            {
                "title": "Title",
                "description": "Body",
                "labels": "bug",
                "assignee_ids": [4],
            },
        )
        self.assertEqual(
            json.loads(self.requests[2].content),
            {
                "description": "",
                "labels": "",
                "assignee_ids": [0],
                "state_event": "close",
            },
        )
        self.assertEqual(self.requests[0].headers["PRIVATE-TOKEN"], "secret-token")
        self.assertEqual(self.requests[0].extensions["timeout"]["read"], 30.0)

    def test_validation_before_http(self):
        for project, iid in [
            ("", 1),
            (0, 1),
            ("group/../project", 1),
            ("project", 0),
            ("project", True),
            ("project", None),
        ]:
            with self.subTest(project=project, iid=iid), self.assertRaises(ValueError):
                self.run_tool(tools.fetch_issue, project, iid)
        with self.assertRaises(ValueError):
            self.run_tool(tools.update_issue, 1, 2)
        self.assertEqual(self.requests, [])

    def test_policy_blocks_before_http_and_action_cannot_be_spoofed(self):
        def unknown(project_id):
            return tools.fetch_issue(project_id, 1)

        with self.assertRaises(GovernanceDenied):
            self.run_tool(unknown, 1)
        denied_policy = get_policy().replace("action: allow", "action: deny")
        with self.assertRaises(GovernanceDenied):
            apply_policy(tools.delete_issue, denied_policy, "gitlab_mcp_server")(
                project_id=1, issue_iid=2
            )
        with self.assertRaises(TypeError):
            self.run_tool(tools.fetch_issue, 1, 2, action={"type": "delete_issue"})
        self.assertEqual(self.requests, [])

    def test_errors_do_not_expose_token_or_response(self):
        for status in (401, 403, 404, 429, 500, 302):
            self.client = lambda request, status=status: httpx.Response(
                status, text="secret-token server details"
            )
            with self.assertRaises(RuntimeError) as caught:
                self.run_tool(tools.fetch_issue, 1, 2)
            self.assertIn(str(status), str(caught.exception))
            self.assertNotIn("secret-token", str(caught.exception))

        def timeout(request):
            raise httpx.ReadTimeout("secret-token", request=request)

        self.client = timeout
        with self.assertRaisesRegex(RuntimeError, "failed to reach"):
            self.run_tool(tools.fetch_issue, 1, 2)

    def test_configuration(self):
        with (
            patch.dict(environ, {"GITLAB_TOKEN": ""}),
            self.assertRaisesRegex(ValueError, "GITLAB_TOKEN"),
        ):
            tools.get_configuration()
        with (
            patch.dict(environ, {"GITLAB_URL": "https://user:secret@example.com"}),
            self.assertRaisesRegex(ValueError, "GITLAB_URL"),
        ):
            tools.get_configuration()


class DiscoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_mcp_registers_four_tools_without_action_parameter(self):
        server = FastMCP("test")
        for tool in TOOLS:
            server.add_tool(apply_policy(tool, get_policy(), "gitlab_mcp_server"))
        async with Client(server, timeout=10) as client:
            exposed = await client.list_tools()
        self.assertEqual(
            {tool.name for tool in exposed},
            {"create_issue", "fetch_issue", "update_issue", "delete_issue"},
        )
        for tool in exposed:
            self.assertNotIn("action", tool.input_schema["properties"])

    async def test_mcp_calls_issue_tool_and_denies_before_http(self):
        requests = []

        def respond(request):
            requests.append(request)
            return httpx.Response(200, json={"iid": 7, "title": "Example"})

        client_type = httpx.Client
        server = FastMCP("test")
        server.add_tool(
            apply_policy(tools.fetch_issue, get_policy(), "gitlab_mcp_server")
        )
        denied_policy = get_policy().replace("action: allow", "action: deny")
        server.add_tool(
            apply_policy(tools.delete_issue, denied_policy, "gitlab_mcp_server")
        )
        with (
            patch.dict(
                environ,
                {"GITLAB_URL": "https://gitlab.example", "GITLAB_TOKEN": "test-token"},
            ),
            patch.object(
                tools.httpx,
                "Client",
                side_effect=lambda **options: client_type(
                    transport=httpx.MockTransport(respond), **options
                ),
            ),
        ):
            async with Client(server, timeout=10) as client:
                result = await client.call_tool(
                    "fetch_issue", {"project_id": "group/project", "issue_iid": 7}
                )
                self.assertEqual(result.data["iid"], 7)
                with self.assertRaisesRegex(ToolError, "denied"):
                    await client.call_tool(
                        "delete_issue", {"project_id": 42, "issue_iid": 7}
                    )
        self.assertEqual(len(requests), 1)
        self.assertEqual(
            requests[0].url.raw_path, b"/api/v4/projects/group%2Fproject/issues/7"
        )


if __name__ == "__main__":
    unittest.main()
