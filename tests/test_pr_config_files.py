"""
Tests for PR config-file changes:
  - .github/workflows/docker.yml   (action version bumps)
  - .github/workflows/publish-mcp.yml  (new workflow)
  - .gitignore                     (new ignore rules)
  - README.md                      (tool count 19, tool table, links)
  - server.json                    (version field required by publish workflow)
"""
import json
import os
import re

import pytest
import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_yaml(rel_path: str) -> dict:
    with open(os.path.join(REPO_ROOT, rel_path)) as fh:
        return yaml.safe_load(fh)


def _read(rel_path: str) -> str:
    with open(os.path.join(REPO_ROOT, rel_path)) as fh:
        return fh.read()


def _gitignore_lines() -> list[str]:
    return _read(".gitignore").splitlines()


# ---------------------------------------------------------------------------
# docker.yml – action version bumps (Node-24 compatible releases)
# ---------------------------------------------------------------------------

class TestDockerWorkflow:
    @pytest.fixture(scope="class")
    def workflow(self):
        return _load_yaml(".github/workflows/docker.yml")

    def _step_uses(self, workflow: dict, name: str) -> str:
        steps = workflow["jobs"]["docker"]["steps"]
        for s in steps:
            if s.get("name") == name:
                return s["uses"]
        raise KeyError(f"Step not found: {name!r}")

    def test_checkout_version_is_v5(self, workflow):
        assert self._step_uses(workflow, "Checkout") == "actions/checkout@v5"

    def test_setup_buildx_version_is_v4(self, workflow):
        assert self._step_uses(workflow, "Set up Docker Buildx") == "docker/setup-buildx-action@v4"

    def test_login_version_is_v4(self, workflow):
        assert self._step_uses(workflow, "Login to Docker Hub") == "docker/login-action@v4"

    def test_build_push_version_is_v7(self, workflow):
        assert self._step_uses(workflow, "Build and push") == "docker/build-push-action@v7"

    def test_triggers_on_main_branch(self, workflow):
        # PyYAML parses the YAML 'on:' key as Python boolean True
        branches = workflow[True]["push"]["branches"]
        assert "main" in branches

    def test_triggers_on_version_tags(self, workflow):
        tags = workflow[True]["push"]["tags"]
        assert any(t.startswith("v") for t in tags), "Expected a v* tag trigger"

    def test_workflow_dispatch_enabled(self, workflow):
        assert "workflow_dispatch" in workflow[True]

    def test_image_name_is_correct(self, workflow):
        steps = workflow["jobs"]["docker"]["steps"]
        meta_step = next(s for s in steps if s.get("name") == "Extract metadata")
        assert meta_step["with"]["images"] == "hrco/xbridge-mcp"

    def test_docker_hub_secret_names(self, workflow):
        """Secrets used must match documented names DOCKERHUB_USERNAME / DOCKERHUB_TOKEN."""
        login_step = next(
            s for s in workflow["jobs"]["docker"]["steps"]
            if s.get("name") == "Login to Docker Hub"
        )
        assert "DOCKERHUB_USERNAME" in login_step["with"]["username"]
        assert "DOCKERHUB_TOKEN" in login_step["with"]["password"]

    def test_cache_uses_gha(self, workflow):
        build_step = next(
            s for s in workflow["jobs"]["docker"]["steps"]
            if s.get("name") == "Build and push"
        )
        assert "gha" in build_step["with"]["cache-from"]
        assert "gha" in build_step["with"]["cache-to"]

    def test_no_deprecated_v3_actions(self, workflow):
        """None of the previously used v3 action versions should remain."""
        steps = workflow["jobs"]["docker"]["steps"]
        for step in steps:
            uses = step.get("uses", "")
            assert not uses.endswith("@v3"), f"Deprecated v3 action still in use: {uses}"

    def test_no_deprecated_v6_build_push(self, workflow):
        """docker/build-push-action@v6 was replaced by v7 in this PR."""
        steps = workflow["jobs"]["docker"]["steps"]
        for step in steps:
            uses = step.get("uses", "")
            assert uses != "docker/build-push-action@v6", "build-push-action@v6 still present"


# ---------------------------------------------------------------------------
# publish-mcp.yml – new workflow
# ---------------------------------------------------------------------------

class TestPublishMcpWorkflow:
    @pytest.fixture(scope="class")
    def workflow(self):
        return _load_yaml(".github/workflows/publish-mcp.yml")

    def test_workflow_name(self, workflow):
        assert "MCP" in workflow["name"] or "mcp" in workflow["name"].lower()

    def test_triggers_only_on_version_tags(self, workflow):
        # PyYAML parses the YAML 'on:' key as Python boolean True
        tags = workflow[True]["push"]["tags"]
        assert len(tags) == 1
        assert tags[0] == "v*"

    def test_workflow_dispatch_enabled(self, workflow):
        assert "workflow_dispatch" in workflow[True]

    def test_no_branch_trigger(self, workflow):
        """publish-mcp should NOT trigger on branch pushes, only tags."""
        push_trigger = workflow[True].get("push", {})
        assert "branches" not in push_trigger

    def test_id_token_write_permission(self, workflow):
        perms = workflow["jobs"]["publish"]["permissions"]
        assert perms["id-token"] == "write"

    def test_contents_read_permission(self, workflow):
        perms = workflow["jobs"]["publish"]["permissions"]
        assert perms["contents"] == "read"

    def test_checkout_action_version(self, workflow):
        steps = workflow["jobs"]["publish"]["steps"]
        checkout = next(s for s in steps if s.get("name") == "Checkout")
        assert checkout["uses"] == "actions/checkout@v5"

    def test_mcp_publisher_install_step_exists(self, workflow):
        steps = workflow["jobs"]["publish"]["steps"]
        names = [s.get("name", "") for s in steps]
        assert any("mcp-publisher" in n.lower() or "install" in n.lower() for n in names)

    def test_version_set_step_reads_github_ref(self, workflow):
        """Version extraction must strip 'refs/tags/v' prefix from GITHUB_REF."""
        steps = workflow["jobs"]["publish"]["steps"]
        version_step = next(s for s in steps if "version" in s.get("name", "").lower())
        run_script = version_step["run"]
        assert "GITHUB_REF" in run_script
        assert "refs/tags/v" in run_script

    def test_version_step_updates_server_json(self, workflow):
        steps = workflow["jobs"]["publish"]["steps"]
        version_step = next(s for s in steps if "version" in s.get("name", "").lower())
        run_script = version_step["run"]
        assert "server.json" in run_script
        assert "jq" in run_script

    def test_auth_step_uses_github_oidc(self, workflow):
        steps = workflow["jobs"]["publish"]["steps"]
        auth_step = next(s for s in steps if "auth" in s.get("name", "").lower())
        assert "github-oidc" in auth_step["run"]

    def test_publish_step_exists(self, workflow):
        steps = workflow["jobs"]["publish"]["steps"]
        pub_step = next(s for s in steps if "publish" in s.get("name", "").lower())
        assert "mcp-publisher" in pub_step["run"]
        assert "publish" in pub_step["run"]

    def test_runs_on_ubuntu_latest(self, workflow):
        assert workflow["jobs"]["publish"]["runs-on"] == "ubuntu-latest"

    def test_step_count(self, workflow):
        """Workflow should have exactly 5 steps: checkout, install, version, auth, publish."""
        steps = workflow["jobs"]["publish"]["steps"]
        assert len(steps) == 5


# ---------------------------------------------------------------------------
# .gitignore – pattern changes
# ---------------------------------------------------------------------------

class TestGitignorePatterns:
    """Test the semantic behaviour of changed .gitignore lines."""

    @pytest.fixture(scope="class")
    def lines(self):
        return _gitignore_lines()

    def test_claude_agents_dir_ignored(self, lines):
        assert ".claude/agents/" in lines

    def test_github_wildcard_pattern_present(self, lines):
        """'.github/*' should be present (replaced the old '.github/' entry)."""
        assert ".github/*" in lines

    def test_github_workflows_negation_present(self, lines):
        """'!.github/workflows/' must appear to keep workflows tracked."""
        assert "!.github/workflows/" in lines

    def test_negation_appears_after_wildcard(self, lines):
        """.github/workflows/ negation must come after .github/* rule."""
        wildcard_idx = lines.index(".github/*")
        negation_idx = lines.index("!.github/workflows/")
        assert negation_idx > wildcard_idx

    def test_old_github_dir_pattern_removed(self, lines):
        """The old bare '.github/' pattern (without wildcard) must not appear."""
        # The old pattern was exactly '.github/' — after the PR it is '.github/*'
        assert ".github/" not in lines

    def test_no_duplicate_claude_agents_entry(self, lines):
        assert lines.count(".claude/agents/") == 1

    def test_no_duplicate_github_wildcard(self, lines):
        assert lines.count(".github/*") == 1

    def test_internal_settings_still_ignored(self, lines):
        """Pre-existing private-config lines must remain intact."""
        assert ".claude/settings.local.json" in lines
        assert ".claude/settings.json" in lines

    def test_claude_md_still_ignored(self, lines):
        assert "CLAUDE.md" in lines


# ---------------------------------------------------------------------------
# README.md – content changes
# ---------------------------------------------------------------------------

class TestReadmeContent:
    @pytest.fixture(scope="class")
    def readme(self):
        return _read("README.md")

    # --- tool count ---

    def test_headline_tool_count_is_19(self, readme):
        """Section heading must say 19, not 20."""
        assert "Available Tools (19)" in readme

    def test_headline_does_not_say_20(self, readme):
        assert "Available Tools (20)" not in readme

    def test_bullet_tool_count_is_19(self, readme):
        """The feature-list bullet must advertise 19 tools."""
        assert "19 tools" in readme

    def test_bullet_does_not_say_20_tools(self, readme):
        assert "20 tools" not in readme

    # --- all 19 tools present in table ---

    @pytest.mark.parametrize("tool_name", [
        "grok-chat",
        "grok-web-search",
        "grok-x-search",
        "grok-session-create",
        "grok-session-chat",
        "grok-session-get",
        "grok-session-list",
        "grok-session-delete",
        "grok-chain-search-summarize",
        "grok-chain-research",
        "grok-chain-debug",
        "grok-image-generate",
        "grok-image-edit",
        "grok-image-models",
        "grok-video-generate",
        "grok-docs-list",
        "grok-docs-get",
        "grok-docs-search",
        "grok-models",
    ])
    def test_tool_present_in_readme(self, readme, tool_name):
        assert tool_name in readme, f"Tool {tool_name!r} not found in README"

    # --- links ---

    def test_product_site_link_present(self, readme):
        assert "https://xbridgemcp.com" in readme

    def test_github_link_present(self, readme):
        assert "https://github.com/hrco/xbridge-mcp" in readme

    def test_docker_hub_link_present(self, readme):
        assert "https://hub.docker.com/r/hrco/xbridge-mcp" in readme

    # --- Pro tier note (new in this PR) ---

    def test_pro_tier_mentioned(self, readme):
        assert "Pro" in readme

    def test_self_host_free_forever_note(self, readme):
        assert "free forever" in readme.lower() or "Self-host is free" in readme

    # --- no telemetry claim still present ---

    def test_no_telemetry_claim_present(self, readme):
        assert "No telemetry" in readme

    # --- BYOK claim still present ---

    def test_byok_claim_present(self, readme):
        assert "BYOK" in readme or "your own API key" in readme.lower()


# ---------------------------------------------------------------------------
# server.json – version field required by publish-mcp.yml
# ---------------------------------------------------------------------------

class TestServerJson:
    @pytest.fixture(scope="class")
    def server_json(self):
        with open(os.path.join(REPO_ROOT, "server.json")) as fh:
            return json.load(fh)

    def test_version_field_exists(self, server_json):
        """publish-mcp.yml updates server.json via jq '.version = $v'; field must exist."""
        assert "version" in server_json

    def test_version_is_string(self, server_json):
        assert isinstance(server_json["version"], str)

    def test_version_matches_semver(self, server_json):
        pattern = re.compile(r"^\d+\.\d+\.\d+")
        assert pattern.match(server_json["version"]), (
            f"version {server_json['version']!r} does not look like semver"
        )

    def test_name_field_exists(self, server_json):
        assert "name" in server_json

    def test_schema_field_exists(self, server_json):
        assert "$schema" in server_json

    def test_oci_package_present(self, server_json):
        """publish-mcp.yml publishes to MCP Registry; OCI package must be declared."""
        oci = [p for p in server_json["packages"] if p["registryType"] == "oci"]
        assert oci, "No OCI package entry in server.json"

    def test_oci_identifier_matches_docker_workflow_image(self, server_json):
        """Docker workflow builds hrco/xbridge-mcp; server.json OCI id must match."""
        oci = next(p for p in server_json["packages"] if p["registryType"] == "oci")
        assert "hrco/xbridge-mcp" in oci["identifier"]
