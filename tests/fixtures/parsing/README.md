# Phase 05 parser samples

Binary samples are generated deterministically at test time by
`tests/fakes/parsing.py`. No user upload, model weight, extracted RAGFlow asset,
or third-party document is committed here.

The recipes produce one small TXT, Markdown, HTML, DOCX, PPTX, XLSX, PDF, and
PNG input. Tests must keep payloads synthetic, non-sensitive, and small enough
for normal Git and CI use.
