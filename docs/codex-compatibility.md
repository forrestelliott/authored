# Codex compatibility

Authored uses the same `SKILL.md`, Python scripts and references in Codex and Claude. No separate Codex implementation or plugin is required for local skill use.

## Installation

Clone the repository into `~/.agents/skills/authored` for user-wide access, or `.agents/skills/authored` inside a project for project-only access. In Codex CLI or the IDE extension, use `/skills` or `$authored` to select it. Restart Codex if it does not appear. These locations and invocation methods follow the [official OpenAI skill documentation](https://learn.chatgpt.com/docs/build-skills).

The assistant needs access to the writing files and Python 3.9+. Script paths resolve relative to the installed skill; evidence and reports belong in a separate output folder in the user's workspace. File access and execution remain subject to the host's permissions.

## Checks performed

Checked on September 27, 2026, on macOS:

- **Metadata:** the skill validator accepted the frontmatter and description.
- **Codex discovery:** `codex-cli 0.155.0-alpha.16.3`, through its local app server's `skills/list` method, discovered `authored` from a temporary project's `.agents/skills/authored/SKILL.md`. It reported repository scope, `enabled: true`, and no skill errors. The user's installed skills were not changed.
- **Python scripts:** all seven regression tests passed on Python 3.9.6 and 3.11.3. They cover snapshot collisions, output containment, source preservation, archive hashes, empty drafts, partial wording overlap, and the sample report workflow.
- **Separate Codex agent smoke test:** an isolated agent was given the installed skill, the fictional Maya files and a realistic request to prepare for an instructor meeting. It generated a five-file snapshot, timeline, draft comparison, HTML report, draft summary, reply outline and meeting practice. Scripts ran successfully from outside the skill directory. Independent checks confirmed all archive hashes and unchanged input contents. The response distinguished wording overlap from proven origin, raised the unexplained final addition, and kept the first-person summary marked as a draft for review. No messages were sent.

Discovery and the behavioral smoke test were separate checks. This was not a full interactive CLI or desktop UI test, and the generated HTML was checked for content without a visual browser review during this run. Only the local-files behavioral scenario was exercised; the cloud-history and partial-AI-use scenarios remain untested in Codex.

The agent also corrected two labels in its generated HTML: “separate editing sessions” became recorded session IDs, and “added in one piece” became text appearing between saved drafts. The underlying metadata and saved drafts do not establish distinct human work sessions or a single paste event. The subsequent report redesign incorporated these corrections into the shared generator: it now describes recorded editing-session markers and additions since the previous draft.

## Rechecking a release

1. Copy the skill into a temporary project's `.agents/skills/authored` folder and copy the fictional files from `evals/fixtures/maya-broad-street` into a separate `writing` folder.
2. Start Codex in that project and check that Authored appears in `/skills`.
3. Invoke `$authored` with the first scenario in `evals/evals.json`, replacing its evidence path with `./writing`. Keep generated output separate from both input files and the installed skill.
4. Check the actual artifacts against the scenario assertions, independently verify archive hashes, and compare input files before and after the run.
5. Run `python3 -m unittest discover -s tests -v` from the Authored repository.

These checks do not establish automatic skill selection reliability, performance on every evidence format, or compatibility with every Codex version, cloud environment or operating system. Behavioral scenarios require human review; passing the Python tests alone does not establish assistant behavior.
