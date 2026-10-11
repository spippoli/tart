# Releases are cut by semantic-release on demand, and a breaking change means Operator action

TART has one version for the whole platform: a `vX.Y.Z` tag on the repository, the same number in `backend/pyproject.toml`, `frontend/package.json`, and both images. The maintainer starts a manual release workflow on `main`, by convention when an implementation wave of the delivery plan is complete. semantic-release computes the next version from the Conventional Commits since the last tag, and writes the release notes. The images are built and pushed before the tag, so an announced release always has its images. A commit is marked breaking (`!` or a `BREAKING CHANGE:` footer) only when an Operator must act on upgrade, and its footer is that action, written for the Operator. The footer thereby becomes the release notes' "Operator actions" section, and SemVer majors mean exactly what the Operations spec says they mean. We chose this because the spec reserves majors for Operator action, and a volunteer Operator reads the release feed. Automating the bump and the notes removes manual error. Keeping the release moment a human decision keeps the feed free of a release per merged pull request.

## Decisions

- **Trigger**: `workflow_dispatch` on `main` only, pinned to the commit it starts from, under a `concurrency` group so two releases never run at once. If `main` moves during the run, semantic-release publishes nothing and the run is started again. CI on pull requests and on `main` is unchanged.
- **Bump rules** (Conventional Commits, `conventionalcommits` preset):
  - `fix`, `perf`, and `build(deps)` (base-image digest and dependency updates) give a patch;
  - `feat` gives a minor;
  - `!` or `BREAKING CHANGE:` gives a major, and is used only for Operator action: a `config_version` bump, a manual step, a PostgreSQL major upgrade.
  - An internal incompatibility, such as a change to the HTTP API between `frontend` and `api`, is not breaking: both halves always ship together under one version.
- **Before the launch**: versions stay at `0.x`. A one-time `v0.0.0` tag on the first commit of the pipeline makes the first release `0.1.0`. While the major is `0`, a breaking commit gives a minor. The maintainer cuts `1.0.0` deliberately at the first Instance's launch, with a breaking commit whose footer points to the Operator documentation.
- **Versions in project files**: the files in the repository stay at `0.0.0`. The release job writes the version into both project files in its own workspace, without committing, and builds the images from that workspace. `main` never receives a bot commit, so no branch-protection bypass is needed and there is no `CHANGELOG.md`. The GitHub Releases are the changelog.
- **Order of steps**:
  1. `semantic-release --dry-run` computes the next version;
  2. the `api` and `frontend` images are built and pushed;
  3. `semantic-release` creates the tag, the GitHub Release, and its notes.

  A failure before step 3 leaves at most unannounced images, and the workflow is run again.
- **Release notes**: a custom template for the release-notes generator.
  - `## Operator actions` comes first and is always present: it lists the breaking footers, or states that only `tart upgrade <version>` is needed.
  - Features and fixes follow, linked to their commits and pull requests.
  - A CVE rebuild (Operations spec) is a patch release with no breaking footer, so its notes say exactly that.
- **Images**: `ghcr.io/spippoli/tart-api` and `ghcr.io/spippoli/tart-frontend`, tagged with the exact version (`0.3.0`, no `v`) and nothing else: no `latest`, and no floating `0.3` or `0` that would bypass `tart upgrade`. Each image carries the OCI labels `version`, `revision`, `source`, and `licenses`. Images are multi-architecture (`linux/amd64` and `linux/arm64`), built on native GitHub runners and joined into one manifest; the `arm64` image gets a start-up smoke test on `/api/health`.
- **Operator files**: `deploy/compose.yaml` is the production file: images only, `${TART_VERSION:?}`, no `build:`. Development adds `deploy/compose.dev.yaml` (builds from source, Mailpit profile). Each GitHub Release attaches, as separate files, `compose.yaml`, `Caddyfile`, `.env.example`, and, once it exists, the `tart` host wrapper.
- **Commit hygiene**: commitlint (`@commitlint/config-conventional`) checks every commit of a pull request. The types allowed are `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`, `build`, `perf`, `revert`, and `style`. The `main` ruleset requires the `backend`, `frontend`, `images`, and `commitlint` checks, with no bypass actors.
- **Tooling**: semantic-release and its plugins are pinned in their own `release/` package. They are MIT-licensed CI tools that are not distributed with TART (ADR 0011).

## Considered Options

- **Independent versions for backend and frontend**: rejected; the Operator pins one `TART_VERSION` and reads one set of release notes, and compatible pairs would have to be tracked.
- **Standard breaking-change semantics**: every technical incompatibility would become a major that needs no Operator action, turning the spec's "read majors carefully" into noise. A dedicated `OPERATOR-ACTION:` footer would work, but adds a non-standard convention to remember.
- **A release on every merge to `main`**: dozens of releases during the MVP, each one in the Operators' feed.
- **A release commit on `main` (`@semantic-release/git`)**: keeps the files in the repository current, but is a direct commit to `main` and needs a ruleset bypass. **A release pull request (release-please)** keeps GitHub Flow intact, but is a different tool's model.
- **Images built after the tag**, inside semantic-release or in a tag-triggered workflow: a failed build leaves an announced release without images.
- **Starting at `1.0.0`, or prereleases (`1.0.0-wave.N`)**: the first declares an incomplete platform stable; the second contradicts the single stable channel.

## Consequences

- Commit messages are release inputs. A mistyped type drops a change from the notes, and a forgotten breaking footer ships a minor that needs Operator action. commitlint guards the syntax; the meaning of a breaking footer is a review point.
- A CVE rebuild needs a releasable commit: the Renovate or Dependabot base-image update is committed as `build(deps): …`, and the maintainer starts the release workflow outside the wave rhythm.
- The repository's project files never show the released version; the tag and the images do.
- This amends the Operations spec: "On a SemVer tag, build and publish" becomes "build and publish, then tag".
