# pubactions

Composite GitHub Actions that Sustenaut's workflows share, released apart
from [pubrules](https://github.com/Sustenaut/pubrules) so a workflow can pin
them on their own:

| Action | What it does |
| --- | --- |
| [`actions/retry`](actions/retry/action.yml) | Runs a bash script up to a number of times (3), warning and waiting (15 s) after each failed try but the last. |
| [`actions/apt-install`](actions/apt-install/action.yml) | Installs apt packages, with the package lists and `.deb` files kept in the Actions cache, so a run on the same runner image fetches nothing. |
| [`actions/terraform-init`](actions/terraform-init/action.yml) | `terraform init`, tried through retry's loop, then once from a provider mirror when its `mirror` input names one. |
| [`actions/pr-label`](actions/pr-label/action.yml) | Whether the pull request a run is for carries a label (`refresh cache` by default). |

pubrules' `actions/cache`, which reads a repository's `pubrules.json`, stays
in pubrules.

## Using an action

Pin the commit of a release tag, with the version in a comment:

    - name: Set up, tried three times (a release download can time out)
      uses: Sustenaut/pubactions/actions/retry@<commit> # vX.Y.Z
      with: { run: make venv }

The commit is the release tag's
(`git ls-remote https://github.com/Sustenaut/pubactions refs/tags/vX.Y.Z^{}`).
Each `action.yml` says what its inputs are, and shows a step that uses it.

An action's inputs reach its script through the step's environment, never
in the script's text, so whatever an input holds runs as given. apt-install
and terraform-init call retry's script beside them, so they are used from
the same commit as it.

### terraform-init's mirror

terraform-init reads no file of the repository it runs in. A provider
mirror is the caller's to give, as the `mirror` input (a Terraform network
mirror's base URL); empty, the default, means no mirror try. A repository
whose `pubrules.json` names one can pass it on:

    - id: mirror
      run: echo "url=$(jq -r '.mirror.terraform // empty' pubrules.json)" >> "$GITHUB_OUTPUT"
    - uses: Sustenaut/pubactions/actions/terraform-init@<commit> # vX.Y.Z
      with: { dir: infra, args: -backend=false -input=false, mirror: '${{ steps.mirror.outputs.url }}' }

The lock's hashes still check every archive the mirror gives.

## Developing

    make venv        # the hash-locked environment (tests/requirements.lock)
    make check       # ./pubrules sync --check, shellcheck and the Gherkin suite

The suite (`tests/features`, `tests/steps`) runs each action's steps as
GitHub runs a composite step, with its inputs in the environment and
stand-ins for what it calls (apt-get, sudo, terraform, curl, sleep). CI
(`.github/workflows/ci.yml`) also runs every action by local path
(`uses: ./actions/retry`), so a change is tried on a real runner before a
release carries it.

CI is written by hand and calls none of pubrules' reusable workflows:
pubrules pins these actions, so a call back into pubrules would make the
two repositories' pins a cycle. Third-party actions are pinned by commit.

## Releasing

[pubrel](https://github.com/Sustenaut/pubrel) releases pubactions; there is
no package to publish beyond the tag. A pull request that changes
`actions/` records the change:

    pubrel add fixed "terraform-init: ..."

and `pubrel prepare` cuts the release pull request. Once it merges, main's
CI tags `vX.Y.Z`.

## License

Apache-2.0: see [LICENSE](LICENSE).
