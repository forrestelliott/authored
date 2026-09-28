# Where writing-process evidence lives

Work through the tools the writer actually used. For each, capture the evidence **before** anyone edits the document again. Product menus change; if a step below does not match what the writer sees, search the product's current help pages.

## Contents

- Cloud writing tools: Google Docs, Microsoft Word / OneDrive / SharePoint, Apple Pages / iCloud, Notion
- Desktop and local tools: Word (local files), Scrivener, Obsidian and Markdown folders, git
- School and work systems: LMS drafts, email and messaging
- Offline and research evidence: paper notes, reference managers, library records, browser history
- Voice baseline: earlier writing samples
- What to do with each item

## Cloud writing tools

**Google Docs.** Usually the richest source.
- File → Version history → See version history. Expand every grouped version (the arrow beside each entry) so all timestamps are visible. Screenshot the list showing dates, then open several versions spread across the timeline and screenshot each, showing the document growing.
- Name key versions (outline, first full draft, final) so they are easy to show in a meeting.
- Draftback, a Chrome extension, replays a Google Doc's full keystroke-level revision history as a video and produces statistics about when writing happened. It only works on docs the writer can edit. If they use it, save the replay link or a screen recording.
- Google Docs downloads (.docx, .pdf) do not include version history, and the download's file dates reflect the download time, not the writing. Capture the history itself.

**Microsoft Word with OneDrive or SharePoint.**
- In Word: File → Info → Version History, or in OneDrive on the web: right-click the file → Version history. Screenshot the list and download earlier versions. Downloaded versions keep their internal document metadata.
- Retention depends on the organization's settings, so capture it promptly.

**Apple Pages / iCloud.** File → Revert To → Browse All Versions shows saved versions over time. Screenshot the timeline and export earlier versions as separate files.

**Notion.** Page ••• menu → Page history. The period covered depends on the workspace plan. Screenshot entries across the writing period.

## Desktop and local tools

**Word (local .docx files).** A .docx file carries internal metadata: created and modified dates, total editing time in minutes, revision count, and editing-session IDs (called rsids) that Word adds each time the document is edited in a new session. Tracked changes carry their own dates. `scripts/timeline.py` reads all of these. Earlier copies may exist in email attachments, USB drives, backup folders, Time Machine or Windows File History ("Previous versions").

**Scrivener.** Snapshots (Documents → Snapshots) preserve dated versions of each section. Project backups (zip files in the backup folder) are dated copies of the whole project.

**Obsidian and plain Markdown folders.** File timestamps, any sync service's version history (Obsidian Sync, Dropbox, iCloud), and the daily notes or outline files written alongside the piece.

**git.** If the writer drafted in a repository, commit history is strong evidence: dated, sequential and hard to fake convincingly. Pass `--git <repo>` to `scripts/timeline.py`.

## School and work systems

**LMS drafts and submissions.** Canvas, Moodle, Blackboard, Brightspace and Google Classroom often keep earlier submissions, draft uploads, discussion posts and instructor feedback with timestamps. Screenshot or download them.

**Email and messaging.** Messages to classmates, tutors, editors, colleagues or friends about the piece while it was being written: questions about the topic, drafts sent for feedback, complaints about a difficult section. Third-party, time-stamped records like these carry a lot of weight.

**Feedback on drafts.** Writing-center appointments, tutor notes, peer-review forms, editor comments. The reviewer can often verify these independently.

## Offline and research evidence

**Paper.** Photograph handwritten notes, outlines, mind maps and printed drafts with markup. Include a page with a visible date if one exists. Keep the originals.

**Reference managers.** Zotero, Mendeley, EndNote and Paperpile record when each source was added. Export the library or screenshot the "date added" column.

**Library records.** Loan history, interlibrary requests and database download history.

**Browser history.** Visits to sources during the research period. Export only the relevant date range and entries, and remove anything unrelated or private before sharing.

**Saved PDFs and highlights.** Annotated sources with modification dates show engagement with the material.

## Voice baseline

Earlier writing by the same person shows that the flagged style is simply how they write. The strongest samples:
- predate November 2022, when ChatGPT launched;
- were written in supervised settings (timed exams, in-class essays, handwritten work);
- are similar in genre to the flagged piece.

If the writer's style is formal, plain, formulaic or shaped by learning English as an additional language, these samples also illustrate why a detector might misread it. Point this out neutrally rather than arguing it.

## What to do with each item

1. Put copies of files in one folder. Leave the originals where they are and do not re-save them.
2. Save screenshots with descriptive filenames that include the date shown in the image, for example `2025-10-02_gdocs-version-history.png`.
3. Run `scripts/snapshot.py` on the folder to hash and archive everything.
4. Note anything that cannot be copied (a paper notebook, an LMS page) in a short list with where it is and who can verify it.
