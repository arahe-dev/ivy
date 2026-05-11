from __future__ import annotations

from pathlib import Path

from scripts.ingest_external_corpus import ingest_file


def test_ingest_file_uses_existing_text_for_line_offsets(tmp_path: Path) -> None:
    root = tmp_path / "source"
    root.mkdir()
    path = root / "notes.md"
    path.write_text(
        "# First\n\n"
        "This first section has enough words to be included in the generated corpus item.\n\n"
        "# Second\n\n"
        "This second section also has enough words to be included in the generated corpus item.\n",
        encoding="utf-8",
    )

    items = ingest_file(root_index=0, root=root, path=path, source_name="source", max_chars=3600)

    assert len(items) == 2
    assert items[0]["provenance"]["line_start"] == 1
    assert items[1]["provenance"]["line_start"] == 5
