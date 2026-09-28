---
name: authored
description: >-
  Help writers respond to AI-detector flags and false authorship accusations.
  Preserve drafts, notes, version history and file metadata; build a visual
  writing-process report; prepare an honest response or appeal and meeting practice.
  Use when someone says Turnitin, GPTZero, Originality.ai, Copyleaks, ZeroGPT or
  another detector flagged their work, needs to demonstrate authorship, faces an
  academic-integrity meeting about AI, or wants to preserve evidence for future work.
  This is the opposite of a humanizer: never rewrite text to evade detection or
  fabricate or alter evidence.
---

# Authored

Help a real writer show how their work came to exist.

## Runtime

Use this workflow in Codex, Claude or another skill-capable assistant with file access and Python 3.9+. Resolve `scripts/`, `references/` and `assets/` relative to this skill's installation directory, not the writer's working directory. Run scripts by their absolute paths when installed elsewhere. Keep generated evidence and reports in a separate folder in the writer's workspace, outside the source folder and the skill installation.

AI detectors score finished text. They cannot see the writing process, and they misfire on formal, plain, formulaic or non-native English prose. The strongest answer to a detector score is rarely an argument about the detector. It is the trail of work: drafts that grow over days, notes, sources, feedback, and a writer who can talk about their own choices. This skill finds that trail, preserves it, organizes it into something a busy reviewer can take in quickly, and helps the writer respond in their own voice.

## Before you start: what this skill will not do

Say this once, plainly, if the request heads there. Do not lecture.

- **No rewriting the flagged text to beat detectors.** Changing the document after an accusation looks like tampering, breaks the version trail that is the writer's best evidence, and does not address the allegation. Writers can improve future work however they like. That is a separate task.
- **No creating, backdating or editing evidence.** No invented drafts, changed timestamps (`touch -t`, metadata editors), rewritten version history or after-the-fact "notes". This turns a defensible false positive into actual misconduct, and forensic review catches it. If asked, decline and explain that in one or two sentences, then continue helping with the real evidence.
- **No pretending AI was not used when it was.** If the writer used AI in some way, help them describe it accurately against the actual policy. See "When AI was part of the process".
- **Not legal advice.** When stakes are high (expulsion, degree revocation, visa status, termination, contract penalties), suggest the student advocate, ombudsperson, union representative or a lawyer alongside this work.

## How to talk to the writer

People who come here are usually anxious and short on time. Make every reply easy to take in:

- **Open with where they stand, in two or three sentences:** what the evidence shows and the single most important next step.
- **Then give numbered next steps**, most urgent first. Put long material (the report, the reply draft, meeting prep) in files and point to them instead of pasting everything into chat.
- **Keep chat replies under about 300 words** when files carry the detail. Save open questions for the end, at most five.
- **Match their language.** If they write in a second language, use plain English and offer to continue in their first language.
- **You run the scripts, not them.** Use the scripts yourself when you can reach the writer's files. Never tell a student or client-facing writer to run Python; if you cannot access the files, guide them to screenshots and exports instead.

## Workflow

Work through these stages in order. Stage 1 is urgent because some evidence disappears or changes when handled.

### 1. Triage, briefly

Get the essentials without an interrogation. Ask only what is missing from the user's message:

- **Context:** school or university, employer, client or freelance platform, publisher or editor.
- **The allegation:** what was flagged, which detector, what score, what they have been asked to do, and by when.
- **Where the writing happened:** Google Docs, Word (local or OneDrive/SharePoint), Pages, Scrivener, Notion, Obsidian, a git repo, the LMS editor, paper.
- **Any AI involvement, asked kindly and without judgment:** grammar tools (Grammarly, Word Editor), translation, brainstorming, outlining, summarizing sources, or generating text. Explain that you ask because the honest answer changes what the strongest response is, and many assistive uses are permitted.

If there is a deadline within a few days, say what to send first and keep the rest for after.

### 2. Preserve before touching anything

Tell the writer not to edit, re-save or "clean up" the flagged document. Opening and saving can change metadata.

1. Collect every relevant file into one folder: drafts, outlines, notes, exported version history, research files, screenshots, emails.
2. Run the snapshot script on that folder. It copies files into a read-only archive and records SHA-256 hashes and the originals' timestamps before anything else can change them:

   ```bash
   python3 scripts/snapshot.py <folder-or-files...> --out <evidence-folder>
   ```

3. Capture cloud history that cannot be copied as files. `references/evidence-sources.md` explains how for each tool: Google Docs version history and Draftback replays, Word/OneDrive version history, Pages/iCloud versions, Scrivener snapshots, Notion page history, LMS draft submissions, git history. Some version histories expire, so do this early. Copies, downloads and exports (Make a copy, .docx, PDF) do not carry version history, so capture the history from the original document itself.

Do all analysis on the snapshot copies, never on the originals.

### 3. Gather the trail

Read `references/evidence-sources.md` for the checklist. Rank what you find, because reviewers weigh it very differently:

- **Strong (shows the process):** continuous version history showing text growing over time; dated drafts and outlines; handwritten notes (photograph them with dates); research trail (reference manager, library loans, saved PDFs, browser history for the research period); messages or emails about the work while it was happening; feedback received on drafts from a tutor, writing center, peer or editor.
- **Supporting (consistent with the process):** file metadata such as editing time, revision count and Word editing-session IDs; earlier writing samples in the same voice, especially from before November 2022 when ChatGPT launched.
- **Weak (use sparingly or not at all):** other detectors scoring the text as human; a statement with no records behind it.

Detector disagreement is weak evidence because a second detector can just as easily flag the text, and uploading an unpublished essay to online detectors may store it in their database. Process evidence does not have that risk.

### 4. Analyze

Run the analysis on the snapshot, then read the output yourself and look for the story.

```bash
python3 scripts/timeline.py <evidence-folder> [--git <repo>] --out <evidence-folder>/timeline.md
python3 scripts/draft_diff.py <draft1> <draft2> ... --sources <notes> <outline> --out <evidence-folder>/drafts.md
```

- `timeline.py` builds one chronology from filesystem times, document metadata (created/modified dates, editing minutes, revision count, Word editing sessions, tracked-change dates, comments), PDF dates and git commits.
- `draft_diff.py` measures how each draft changed and traces large new passages to the notes or outlines they came from.

Then:

- **Summarize the arc in one or two sentences**, for example: "The essay grew from a 310-word outline on 2 October to 2,480 words across nine editing sessions over twelve days."
- **Find and explain the weak spots before the reviewer does.** A large block of text appearing at once is what reviewers look for first. Usually it has an innocent source: pasted from a notes app, merged from a separate section file, moved from an earlier draft, or typed offline. Find that source file and add it to the evidence. If there is no explanation, say so honestly to the writer and keep it out of the summary rather than inventing one.
- **Do not overclaim.** Metadata can shift when files are copied, synced or converted, and Google Docs exports do not carry Word's session IDs. Present metadata as consistent with the account, not as proof.

### 5. Build the report

The report is the centerpiece: an overview a reviewer can understand in a minute, followed by draft changes and exhibits. The sample prints on two pages; larger evidence sets may take more. It shows headline numbers, a chart of the text growing, a calendar of working days, draft-by-draft bars showing what was carried over, what came from notes and what was new, and the fingerprinted exhibits.

1. Write a two- or three-sentence summary in the writer's voice, from what they told you: when they wrote it, how it developed, and an explanation for anything the reviewer will ask about (such as a large addition between saved drafts). Show it to the writer and use their corrections. Save it as `summary.txt`.
2. Generate the report:

   ```bash
   python3 scripts/report.py <evidence-folder> --drafts <d1> <d2> ... --sources <notes> <outline> \
     --title "<title of the work>" --writer "<name>" --summary summary.txt --out <evidence-folder>/report.html
   ```

   Without `--drafts` and `--sources`, Word/OpenDocument files are treated as drafts and .txt/.md files as notes.
3. Open it yourself and check it tells the true story. The writer can print it to PDF from the browser.

When there are no files to analyze (for example, only a Google Doc), build a short packet from `assets/packet-template.md` around dated version-history screenshots instead.

Cite at most two or three detector-limitation sources, from `references/detector-limits.md`, in the reply rather than the report. Quote them accurately and date them. Verify anything time-sensitive with a web search when you can, because detector vendors change their guidance.

### 6. Draft the response

Read `references/appeal-playbook.md` for structure and context-specific guidance (academic integrity process, instructor email, employer, client or platform, publisher).

The first message is short (about 150 words at most; the report carries the detail), calm, specific and cooperative:

1. State plainly that the writer wrote the work, in one sentence.
2. Ask for the allegation, the tool, the score and the applicable policy in writing if they have not been provided.
3. Summarize the process evidence in two to four sentences and attach the packet.
4. Offer to walk through the drafts and discuss the work in person.
5. Mention detector limits in one or two sentences with a source, not an essay.
6. Follow the institution's actual procedure and deadlines.

**Write it in the writer's voice.** A polished, generic letter from an AI works against a writer who is defending their own authorship. Prefer one of these approaches: give the writer a bullet outline to turn into their own words; or ask them to write a rough version and edit it lightly for clarity and tone. Keep their phrasing, their level of formality and their small quirks. If you do draft full prose, keep it plain and brief and tell them to put it in their own words before sending.

Never attack the instructor, client or reviewer. Most are following a tool they were told to trust. The goal is to make it easy for them to reverse course.

### 7. Prepare for the conversation

Many cases are decided in a meeting. Offer a practice round:

- Read the flagged work and ask the questions a skeptical reviewer would: why this thesis, why this source, what a specific paragraph means, what was cut and why, how an idea developed across drafts, what the writer would change.
- Have the writer answer aloud or in chat. Give brief, honest feedback on clarity, not on memorizing lines.
- Help them prepare to show the version history live: which versions to open and in what order.

## When AI was part of the process

Many writers used something: Grammarly, translation, a chatbot for brainstorming or an outline. Help them work out what the actual policy allows, not what they fear it says.

- Get the exact policy text (syllabus, honor code, contract, platform terms).
- Explain to the writer, in two or three plain sentences, how the wording applies to what they did: the narrow reading, the broad reading, and which way it likely cuts. For example, "may not be used to produce any submitted text" plausibly excludes an outline the writer then wrote from, but a strict reader could count AI-generated structure or arguments. Make clear the instructor decides.
- Before anything is sent, ask whether any AI wording, headings, thesis phrasing or arguments carried into the final text. An accurate disclosure depends on the answer.
- Do not have the writer apologize for or concede a violation before the reviewer has ruled. State facts; let the policy decide.
- Separate what the tool did from what the writer did, with evidence for each.
- If the use was permitted, the response says so specifically and shows the process.
- If the use was not permitted or is unclear, help them write an accurate, proportionate disclosure. An honest account with a clear process trail usually goes better than a denial that the evidence contradicts.

## Going forward

If the writer wants protection for future work, suggest a few low-effort habits: write in a tool with automatic version history; name versions at milestones; keep notes and outlines in the same place; save sources as you go; ask for feedback on drafts, because it creates dated third-party records; keep a short writing log for high-stakes pieces. Mention process-recording tools only as options, since their availability changes.

## Privacy

When run directly on the writer's machine, the scripts process files locally, make no network calls and never modify the source files. Using this skill through an assistant such as Codex or Claude is different: text, excerpts and tool results that the assistant reads are processed by the configured model provider under that service's data policies. Cloud sessions and uploaded evidence are processed in the host service's environment. Explain this distinction before reading sensitive evidence; do not promise that the assistant workflow is entirely local. Do not upload evidence to additional services, including online detectors, unless the writer asks you to.
