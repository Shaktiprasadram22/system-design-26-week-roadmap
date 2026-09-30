from pathlib import Path
import csv
import html
import json
import re
import zipfile

import markdown
from pypdf import PdfReader
from weasyprint import HTML


ROOT = Path(__file__).resolve().parent
CHAPTERS = ROOT / "chapters"
CHAPTER_NAMES = [
    "01-foundations.md",
    "02-core-system-design.md",
    "03-reliability-security-and-lld.md",
    "04-cloud-and-infrastructure.md",
    "05-ai-fundamentals-and-rag.md",
    "06-agents-and-ai-production.md",
]


def github_slug(value: str, separator: str) -> str:
    """Match GitHub heading IDs for the headings used in these documents."""
    stripped = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"\s", separator, stripped)

STYLE = """
@page {
  size: A4;
  margin: 19mm 18mm 20mm;
  @bottom-left {
    content: "System design · 26 weeks · 89 topics";
    font-family: "DejaVu Sans", sans-serif;
    font-size: 8pt;
    color: #626b78;
  }
  @bottom-right {
    content: counter(page);
    font-family: "DejaVu Sans", sans-serif;
    font-size: 8pt;
    color: #626b78;
  }
}
* { box-sizing: border-box; }
html { color: #182332; background: white; }
body {
  font-family: "DejaVu Sans", sans-serif;
  font-size: 9.6pt;
  line-height: 1.5;
  max-width: 850px;
  margin: 0 auto;
}
h1, h2, h3 { line-height: 1.25; color: #122b45; }
h1 { font-size: 25pt; margin: 0 0 15pt; letter-spacing: -0.4pt; }
h2 { font-size: 16pt; margin: 24pt 0 12pt; }
h3 { font-size: 12pt; margin: 19pt 0 9pt; }
h1, h2, h3 { break-after: avoid; }
p { margin: 0 0 10pt; orphans: 3; widows: 3; }
a { color: #175b92; text-decoration: none; overflow-wrap: anywhere; }
strong { color: #132b44; }
code { font-family: "DejaVu Sans Mono", monospace; font-size: 8.4pt; }
p code, td code { overflow-wrap: anywhere; }
pre {
  font-size: 8.3pt;
  line-height: 1.45;
  background: #f0f4f7;
  border-left: 3pt solid #7895ac;
  padding: 12pt;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  break-inside: avoid;
}
table { border-collapse: collapse; width: 100%; margin: 12pt 0 18pt; }
thead { display: table-header-group; }
th, td {
  text-align: left;
  vertical-align: top;
  font-size: 8.5pt;
  line-height: 1.45;
  padding: 7pt;
  border-bottom: 0.5pt solid #d5dce4;
  overflow-wrap: anywhere;
}
th { background: #eaf0f5; color: #122b45; white-space: nowrap; }
tr { break-inside: avoid; }
li { margin: 0 0 4pt; }
ul { margin: 10pt 0 15pt; padding-left: 18pt; }
.toc { font-size: 9.2pt; }
.toc ul { list-style: none; padding-left: 0; }
.toc li { margin-bottom: 5pt; }
@media print {
  h2[id^="phase-"] { break-before: page; }
  h2[id^="worked-production-"] { break-before: page; }
  h2[id="documented-production-case-studies"] { break-before: page; }
}
@media screen {
  body { padding: 45px 24px 80px; font-size: 16px; }
  h1 { font-size: 38px; }
  h2 { font-size: 27px; }
  h3 { font-size: 21px; }
  table { display: block; overflow-x: auto; }
  th, td { font-size: 14px; min-width: 65px; }
  pre { overflow-x: auto; }
}
"""


def render_document(name: str, title: str, source: str) -> dict:
    converter = markdown.Markdown(
        extensions=["tables", "fenced_code", "toc", "sane_lists"],
        extension_configs={"toc": {"toc_depth": "2-2", "slugify": github_slug}},
    )
    body = converter.convert(source)
    page = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{html.escape(title)}</title><style>{STYLE}</style>"
        f"</head><body><main>{body}</main></body></html>"
    )
    html_path = ROOT / f"{name}.html"
    pdf_path = ROOT / f"{name}.pdf"
    html_path.write_text(page, encoding="utf-8")
    HTML(string=page, base_url=str(ROOT)).write_pdf(pdf_path)
    reader = PdfReader(pdf_path)
    extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
    expected_topics = re.findall(r"^### (\d+)\.", source, re.M)
    pdf_topics = [number for number in expected_topics
                  if re.search(r"(?m)^\s*" + number + r"\.\s+", extracted)]
    assert pdf_topics == expected_topics
    report = {
        "document": name,
        "words": len(source.split()),
        "pages": len(reader.pages),
        "bytes": pdf_path.stat().st_size,
        "extracted_numbered_headings": len(pdf_topics),
        "empty_pages": [i + 1 for i, p in enumerate(reader.pages) if not (p.extract_text() or "").strip()],
    }
    (ROOT / f"{name}.pdf-text.txt").write_text(extracted, encoding="utf-8")
    return report


roadmap = (ROOT / "roadmap.md").read_text()
chapters = "\n\n".join(
    (CHAPTERS / name).read_text()
    for name in CHAPTER_NAMES
)
walkthroughs = (CHAPTERS / "07-production-walkthroughs-and-case-studies.md").read_text()
intro = """# System design: the complete production learning guide

**26 weeks · 89 topics · 89 production scenarios · 89 exercises**

This guide expands every topic from the inspected website into an explanation, a realistic production scenario, and a hands-on verification exercise. It includes a proposed weekly roadmap, two connected production walkthroughs, and six documented company case studies. Scenarios and numerical lab targets are illustrative; company case studies cite primary evidence.

Begin with the roadmap, then read the numbered topics assigned to your current week. Use the production walkthroughs to connect individual concepts into a complete system.

"""
roadmap_body = roadmap.split("\n", 1)[1].lstrip()
combined_body = roadmap_body + "\n\n" + chapters + "\n\n" + walkthroughs
headings = re.findall(r"^## (.+)$", combined_body, re.M)
contents = "## Contents\n\n" + "\n".join(
    f"- [{heading}](#{github_slug(heading, '-')})" for heading in headings
) + "\n\n"
guide = intro + contents + combined_body
(ROOT / "complete-guide.md").write_text(guide, encoding="utf-8")

curriculum = json.loads((ROOT / "curriculum.json").read_text())
if not (ROOT / "topic-tracker.csv").exists():
    with (ROOT / "topic-tracker.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(["Topic", "Phase", "Source weeks", "Subject", "Status", "Evidence / notes"])
        number = 0
        for phase in curriculum:
            for section in phase["sections"]:
                for topic in section["topics"]:
                    number += 1
                    writer.writerow([number, phase["title"], phase["weeks"], topic["name"], "Not started", ""])

results = [
    render_document("roadmap", "26-week system design roadmap", roadmap),
    render_document("complete-guide", "Complete system design production learning guide", guide),
]

assert len(re.findall(r"^### \d+\.", guide, re.M)) == 89
assert guide.count("**Production scenario.**") == 89
assert guide.count("**Build and verify.**") == 89
assert not any(result["empty_pages"] for result in results)
(ROOT / "build-report.json").write_text(json.dumps(results, indent=2))

reader_files = [
    "README.md", "roadmap.pdf", "complete-guide.pdf", "roadmap.md",
    "complete-guide.md", "roadmap.html", "complete-guide.html",
    "topic-tracker.csv", "curriculum.json", "build_documents.py", "requirements.txt",
] + [f"chapters/{name}" for name in CHAPTER_NAMES] + [
    "chapters/07-production-walkthroughs-and-case-studies.md"
]
with zipfile.ZipFile(ROOT / "system-design-learning-package.zip", "w",
                     compression=zipfile.ZIP_DEFLATED) as archive:
    for name in reader_files:
        archive.write(ROOT / name, arcname=name)

print(json.dumps(results, indent=2))
