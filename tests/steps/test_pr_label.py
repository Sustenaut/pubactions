"""Steps for the pr-label action: its step run as GitHub runs a composite
step, with its inputs in the environment its `env` gives, the event in a
file, and a stand-in curl on PATH that answers GitHub's API for the
repository o/r from files, failing as `curl -f` does where there is none."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import yaml
from pytest_bdd import parsers, scenarios, then, when

scenarios("pr-label.feature")

ACTION = Path(__file__).resolve().parents[2] / "actions" / "pr-label"
INPUT = re.compile(r"^\$\{\{ inputs\.([\w-]+) \}\}$")

# Answers .../repos/o/r/<what> with api/<what>, its slashes made dashes.
CURL = r"""#!/usr/bin/env bash
url="${*: -1}"
file="$API_DIR/$(sed -E 's#.*/repos/o/r/##; s#/#-#g' <<< "$url")"
[[ -f "$file" ]] || { echo "curl: (22) 404 $url" >&2; exit 22; }
cat "$file"
"""
API = {
    "commits-abc123-pulls": [{"merged_at": "2026-10-30T07:00:00Z", "labels": [{"name": "Refresh Cache"}]}],
    "commits-def456-pulls": [{"merged_at": "2026-10-30T07:00:00Z", "labels": [{"name": "docs"}]},
                             {"merged_at": None, "labels": [{"name": "refresh cache"}]}],
    "pulls-15": {"labels": [{"name": "refresh cache"}]},
}


def _action():
    return yaml.safe_load((ACTION / "action.yml").read_text())


def _event(how):
    """The event file's body, and the pushed commit, for a scenario's words."""
    if m := re.fullmatch(r'whose pull request carries (?:"(.*)"|no label)', how):
        names = re.findall(r'"([^"]*)"', how)
        return {"pull_request": {"labels": [{"name": n} for n in names]}}, "abc123"
    if m := re.fullmatch(r'for the queue branch "(.*)"', how):
        return {"merge_group": {"head_ref": f"refs/heads/{m[1]}"}}, "abc123"
    if m := re.fullmatch(r'of the commit "(.*)"', how):
        return {}, m[1]
    assert how == "with no pull request", how
    return {}, "abc123"


@when(parsers.re(r'pr-label looks for "(?P<label>[^"]+)" on an? (?P<event>\w+) run, (?P<how>.+)$'),
      target_fixture="ran")
def looks(tmp_path, label, event, how):
    body, sha = _event(how)
    bin_dir, api = tmp_path / "bin", tmp_path / "api"
    bin_dir.mkdir()
    api.mkdir()
    (bin_dir / "curl").write_text(CURL)
    (bin_dir / "curl").chmod(0o755)
    for name, answer in API.items():
        (api / name).write_text(json.dumps(answer))
    (tmp_path / "event.json").write_text(json.dumps(body))
    out = tmp_path / "out"
    out.write_text("")
    action = _action()
    inputs = {key: str(spec.get("default", "")) for key, spec in action["inputs"].items()}
    inputs.update(label=label, token="t")
    (step,) = action["runs"]["steps"]
    env = {key: inputs[INPUT.match(value)[1]] for key, value in step["env"].items()}
    done = subprocess.run(
        ["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", step["run"]],
        capture_output=True, text=True, check=False, cwd=tmp_path,
        env={**os.environ, **env, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
             "GITHUB_ACTION_PATH": str(ACTION), "GITHUB_OUTPUT": str(out), "API_DIR": str(api),
             "GITHUB_REPOSITORY": "o/r", "GITHUB_SHA": sha, "GITHUB_EVENT_NAME": event,
             "GITHUB_EVENT_PATH": str(tmp_path / "event.json")})
    return {"code": done.returncode, "stdout": done.stdout, "stderr": done.stderr,
            "output": out.read_text().splitlines()}


@then(parsers.re(r"the step (?P<how>passed|failed)$"))
def step_result(ran, how):
    assert (ran["code"] == 0) == (how == "passed"), ran


@then(parsers.parse("it wrote present={present}"))
def wrote(ran, present):
    assert ran["output"] == [f"present={present}"], ran


@then("it wrote nothing")
def wrote_nothing(ran):
    assert ran["output"] == [], ran


@when("I read the pr-label action", target_fixture="action")
def read_action():
    return _action()


@then(parsers.re(r'its "(?P<name>[\w-]+)" input defaults to "(?P<value>[^"]*)"$'))
def input_default(action, name, value):
    assert action["inputs"][name].get("default") == value, action["inputs"][name]


@then("its step takes its inputs from its environment alone")
def inputs_by_env(action):
    (step,) = action["runs"]["steps"]
    assert "${{" not in step["run"], step["run"]
    assert all(INPUT.match(value) for value in step["env"].values()), step["env"]
