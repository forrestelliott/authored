#!/usr/bin/env python3
"""Generate the synthetic evidence folder used by the evals.

Everything here is fictional sample data: a student ("Maya Okafor") writing a
history essay across two weeks. The Word files carry realistic internal metadata
(editing time, revision count, editing-session IDs, one tracked change and a
comment) and the files' modified times are set to match the story, so the
scripts have something to read. This is test data only.

Usage: python3 make_fixtures.py <output-folder>
"""

import os
import sys
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.sax.saxutils import escape

TZ = timezone(timedelta(hours=-7))

OUTLINE = """Broad Street essay outline
Thesis: Snow's map mattered less than the argument he built around it.
1. 1854 Soho, miasma theory, what people believed
2. Snow's earlier work (1849 pamphlet), why he suspected water
3. The pump handle, what actually happened (outbreak already declining)
4. Whitehead and the index case, local knowledge
5. Why the Board of Health rejected it at first
6. What changed later: Bazalgette, 1866, Farr
Sources: Johnson Ghost Map ch 4-6, Snow 1855 2nd ed, Brody et al 2000 Lancet, Vinten-Johansen book
Question for Dr Reyes: can I use the Ghost Map as a main source or only as secondary?"""

P_INTRO = ("Most people who know one thing about the 1854 cholera outbreak in Soho know about the map. "
           "John Snow marked each death with a small black bar, the bars clustered around the pump on Broad Street, "
           "and the handle was removed. It is a satisfying story and it is mostly true, but I think it puts the weight "
           "in the wrong place. The map did not persuade anyone in 1854. What eventually persuaded people was the "
           "argument Snow built around it, and the slow work of other people who kept testing that argument after the "
           "outbreak was over.")
P_INTRO_V1 = ("Most people who know about the 1854 cholera outbreak in Soho know about the map. John Snow marked each "
              "death with a black bar, the bars clustered around the Broad Street pump, and the handle was removed. "
              "This essay will argue that the map was important but that it was not the whole story.")
P_PUMP_V1 = ("Snow persuaded the local Board of Guardians to remove the pump handle on 8 September. This is usually "
             "told as the moment the outbreak ended.")
P_BOARD_V1 = ("The General Board of Health rejected Snow's conclusion. They thought the air around the pump was the real "
              "cause.")
P_MIASMA = ("In 1854 the dominant explanation for cholera was miasma, the idea that disease travelled through bad air "
            "rising from filth and decay. This was not a stupid theory. Cholera really was worse in crowded, dirty "
            "places, and cleaning up those places often helped. The trouble was that miasma explained everything and "
            "so predicted nothing in particular. Snow had already argued in his 1849 pamphlet that cholera was "
            "swallowed rather than breathed, because it attacked the gut first, but he had no way to show it.")
P_PUMP = ("The pump handle story is where the popular version gets shaky. Snow persuaded the local Board of Guardians "
          "to remove the handle on 8 September, but deaths had already been falling for several days, partly because "
          "so many residents had fled. Snow admitted this himself in the second edition of his book. Removing the "
          "handle may have prevented a second wave, but it did not end the outbreak in the dramatic way the story "
          "suggests.")
P_WHITEHEAD = ("The person who did the most to confirm Snow's theory started out trying to disprove it. Henry Whitehead "
               "was the curate of St Luke's, and he knew the neighbourhood house by house. He expected his own "
               "investigation to show that the pump was innocent. Instead he found the likely index case: a baby at "
               "40 Broad Street whose nappies had been rinsed in a cesspool only a few feet from the well. Whitehead's "
               "local knowledge filled the gap Snow could not fill from outside. Snow had a pattern. Whitehead had "
               "the route the water took.")
P_BOARD = ("Even so, the General Board of Health rejected Snow's conclusion in its report on the outbreak. The committee "
           "accepted that many victims had drunk from the pump but argued that the air around it was the real cause. "
           "Reading the report now, what stands out is not that they ignored the evidence but that they fitted it "
           "into the theory they already had. That is uncomfortable, because it is what most of us do most of the time.")
P_LATER = ("The argument won slowly. William Farr, who had supported miasma, changed his mind after the 1866 outbreak "
           "in east London, where he traced deaths to one water company that had drawn unfiltered water. By then "
           "Joseph Bazalgette's sewers were being built, mostly for reasons of smell rather than germs, and they "
           "helped anyway. Snow died in 1858 and did not see any of this.")
P_CONCL = ("So the map deserves its place, but as the start of an argument rather than the end of one. Snow's real "
           "contribution was to insist that a theory should predict where disease would appear, and to keep collecting "
           "cases that could prove him wrong. Whitehead's contribution was to take that challenge seriously. The lesson "
           "I take from Broad Street is less about maps than about being willing to be checked.")

NOTES = """Whitehead notes (Ghost Map ch 5 + Vinten-Johansen), typed up Sep 12

- Henry Whitehead, curate of St Luke's, knew the neighbourhood house by house
- started out trying to DISPROVE Snow, expected his investigation to show the pump was innocent
- found the likely index case: a baby at 40 Broad Street whose nappies had been rinsed in a cesspool only a few feet from the well
- baby = Frances Lewis? check Johnson p.196
- his local knowledge filled the gap Snow could not fill from outside
- Snow had a pattern. Whitehead had the route the water took.  <- use this line
- W. pamphlet 1855, 'The Cholera in Berwick Street'
- ask Dr Reyes: ok to use Ghost Map as main secondary source?"""

DRAFTS = [
    # name, paragraphs, created, saved, minutes, revision, sessions, tracked, comment
    ("essay_draft1.docx", [P_INTRO_V1, P_MIASMA, P_PUMP_V1],
     datetime(2026, 9, 10, 19, 12, tzinfo=TZ), datetime(2026, 9, 11, 22, 40, tzinfo=TZ), 186, 9, 4, False, False),
    ("essay_draft2.docx", [P_INTRO_V1, P_MIASMA, P_PUMP, P_WHITEHEAD, P_BOARD_V1],
     datetime(2026, 9, 10, 19, 12, tzinfo=TZ), datetime(2026, 9, 16, 17, 2, tzinfo=TZ), 402, 21, 9, False, True),
    ("essay_final.docx", [P_INTRO, P_MIASMA, P_PUMP, P_WHITEHEAD, P_BOARD, P_LATER, P_CONCL],
     datetime(2026, 9, 10, 19, 12, tzinfo=TZ), datetime(2026, 9, 20, 21, 18, tzinfo=TZ), 611, 34, 14, True, False),
]


def z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def docx(path: Path, paras, created, saved, minutes, revision, sessions, tracked, comment) -> None:
    W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    body = []
    for i, p in enumerate(paras):
        if tracked and i == 2:
            body.append(
                f'<w:p><w:r><w:t xml:space="preserve">{escape(p)} </w:t></w:r>'
                f'<w:ins w:id="1" w:author="Maya Okafor" w:date="{z(saved - timedelta(hours=2))}"><w:r><w:t>'
                "The handle was put back within weeks, once the immediate panic was over.</w:t></w:r></w:ins>"
                f'<w:del w:id="2" w:author="Maya Okafor" w:date="{z(saved - timedelta(hours=2))}"><w:r><w:delText>'
                "Everyone agreed it was a turning point.</w:delText></w:r></w:del></w:p>")
        else:
            body.append(f'<w:p><w:r><w:t xml:space="preserve">{escape(p)}</w:t></w:r></w:p>')
    document = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {W}><w:body>{"".join(body)}</w:body></w:document>'
    rsids = "".join(f'<w:rsid w:val="00{0xA1B200 + i * 7919:06X}"/>' for i in range(sessions))
    settings = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:settings {W}><w:rsids><w:rsidRoot w:val="00A1B200"/>{rsids}</w:rsids></w:settings>'
    words = sum(len(p.split()) for p in paras) + (13 - 6 if tracked else 0)  # tracked insertion (13) replaces deletion (6)
    core = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        '<dc:title>Broad Street essay</dc:title><dc:creator>Maya Okafor</dc:creator>'
        f'<cp:lastModifiedBy>Maya Okafor</cp:lastModifiedBy><cp:revision>{revision}</cp:revision>'
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{z(created)}</dcterms:created>'
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{z(saved)}</dcterms:modified></cp:coreProperties>')
    app = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
        f'<Application>Microsoft Office Word</Application><TotalTime>{minutes}</TotalTime><Words>{words}</Words></Properties>')
    ctypes = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
        '<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>'
        '<Override PartName="/word/webSettings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.webSettings+xml"/>'
        '<Override PartName="/word/fontTable.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.fontTable+xml"/>'
        '<Override PartName="/word/comments.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"/>'
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
        '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
        '</Types>')
    if not comment:
        ctypes = ctypes.replace('<Override PartName="/word/comments.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"/>', "")
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        '</Relationships>')
    styles = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles {W}><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:sz w:val="24"/></w:rPr></w:rPrDefault></w:docDefaults><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style></w:styles>'
    fonts = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:fonts {W}><w:font w:name="Calibri"/><w:font w:name="Times New Roman"/></w:fonts>'
    web = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:webSettings {W}/>'
    doc_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
                '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>'
                '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/webSettings" Target="webSettings.xml"/>'
                '<Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/fontTable" Target="fontTable.xml"/>'
                + ('<Relationship Id="rId5" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments" Target="comments.xml"/>' if comment else "")
                + '</Relationships>')

    def put(zf, name, data):
        # Word writes every package part with the fixed DOS date 1980-01-01, not the save time.
        zi = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
        zi.compress_type = zipfile.ZIP_DEFLATED
        zf.writestr(zi, data)

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        put(zf, "[Content_Types].xml", ctypes)
        put(zf, "_rels/.rels", rels)
        put(zf, "word/document.xml", document)
        put(zf, "word/_rels/document.xml.rels", doc_rels)
        put(zf, "word/styles.xml", styles)
        put(zf, "word/settings.xml", settings)
        put(zf, "word/webSettings.xml", web)
        put(zf, "word/fontTable.xml", fonts)
        put(zf, "docProps/core.xml", core)
        put(zf, "docProps/app.xml", app)
        if comment:
            put(zf, "word/comments.xml",
                        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:comments {W}>'
                        f'<w:comment w:id="0" w:author="Jordan Lee (Writing Center)" w:date="{z(datetime(2026, 9, 16, 15, 30, tzinfo=TZ))}">'
                        '<w:p><w:r><w:t>Strong paragraph. Could you say more about why the Board rejected it?</w:t></w:r></w:p>'
                        '</w:comment></w:comments>')
    os.utime(path, (saved.timestamp(), saved.timestamp()))


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "fixtures/maya-broad-street")
    out.mkdir(parents=True, exist_ok=True)
    outline = out / "outline.txt"
    outline.write_text(OUTLINE + "\n")
    t = datetime(2026, 9, 8, 16, 45, tzinfo=TZ).timestamp()
    os.utime(outline, (t, t))
    notes = out / "notes_whitehead.txt"
    notes.write_text(NOTES + "\n")
    t = datetime(2026, 9, 13, 21, 3, tzinfo=TZ).timestamp()
    os.utime(notes, (t, t))
    for d in DRAFTS:
        docx(out / d[0], *d[1:])
    print(f"Wrote sample evidence to {out}")


if __name__ == "__main__":
    main()
