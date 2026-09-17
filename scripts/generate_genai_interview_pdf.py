from pathlib import Path
import textwrap


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "genai_interview_qa.md"
OUTPUT = ROOT / "docs" / "genai_interview_qa.pdf"


def escape_pdf_text(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )


def wrap_text(text: str, width: int) -> list[str]:
    if not text.strip():
        return [""]
    return textwrap.wrap(text, width=width, break_long_words=False) or [""]


def markdown_to_lines(markdown: str) -> list[tuple[str, str]]:
    lines: list[tuple[str, str]] = []
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line:
            lines.append(("blank", ""))
        elif line.startswith("# "):
            lines.append(("title", line[2:].strip()))
        elif line.startswith("## "):
            lines.append(("section", line[3:].strip()))
        elif line.startswith("Answer:"):
            lines.append(("answer", line))
        elif line[0].isdigit() and ". " in line[:5]:
            lines.append(("question", line))
        else:
            lines.append(("body", line))
    return lines


def paginate(items: list[tuple[str, str]]) -> list[list[tuple[str, str]]]:
    pages: list[list[tuple[str, str]]] = []
    page: list[tuple[str, str]] = []
    y = 760

    def line_height(style: str) -> int:
        return {
            "title": 22,
            "section": 18,
            "question": 13,
            "answer": 12,
            "body": 12,
            "blank": 8,
        }.get(style, 12)

    for style, text in items:
        width = 58 if style in {"title", "section"} else 86
        wrapped = wrap_text(text, width)
        needed = line_height(style) * len(wrapped) + (8 if style == "section" else 2)
        if y - needed < 60 and page:
            pages.append(page)
            page = []
            y = 760
        page.append((style, text))
        y -= needed

    if page:
        pages.append(page)
    return pages


def build_page_stream(page_items: list[tuple[str, str]], page_number: int) -> str:
    commands = ["BT"]
    y = 760

    for style, text in page_items:
        if style == "blank":
            y -= 8
            continue

        font = "F1"
        size = 10
        leading = 12
        width = 86
        x = 50

        if style == "title":
            font, size, leading, width = "F2", 18, 22, 58
        elif style == "section":
            font, size, leading, width = "F2", 14, 18, 62
            y -= 6
        elif style == "question":
            font, size, leading, width = "F2", 10, 13, 86
        elif style == "answer":
            font, size, leading, width = "F1", 10, 12, 86

        commands.append(f"/{font} {size} Tf")
        for wrapped in wrap_text(text, width):
            commands.append(f"1 0 0 1 {x} {y} Tm ({escape_pdf_text(wrapped)}) Tj")
            y -= leading
        y -= 2

    commands.append("/F1 9 Tf")
    commands.append(
        f"1 0 0 1 50 35 Tm ({escape_pdf_text('BHRMS GenAI Interview Q&A - Page ' + str(page_number))}) Tj"
    )
    commands.append("ET")
    return "\n".join(commands)


def make_pdf(pages: list[list[tuple[str, str]]]) -> bytes:
    objects: list[bytes] = []

    def add(obj: str | bytes) -> int:
        if isinstance(obj, str):
            obj = obj.encode("latin-1", errors="replace")
        objects.append(obj)
        return len(objects)

    catalog_id = add("PLACEHOLDER")
    pages_id = add("PLACEHOLDER")
    font_regular_id = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    font_bold_id = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")

    page_ids: list[int] = []
    for index, page in enumerate(pages, start=1):
        stream = build_page_stream(page, index).encode("latin-1", errors="replace")
        content_id = add(
            b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream"
        )
        page_id = add(
            f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_regular_id} 0 R /F2 {font_bold_id} 0 R >> >> "
            f"/Contents {content_id} 0 R >>"
        )
        page_ids.append(page_id)

    objects[catalog_id - 1] = f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode("latin-1")
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[pages_id - 1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("latin-1")

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for obj_id, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{obj_id} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_pos = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)


def main() -> None:
    markdown = SOURCE.read_text(encoding="utf-8")
    items = markdown_to_lines(markdown)
    pages = paginate(items)
    OUTPUT.write_bytes(make_pdf(pages))
    print(f"Generated {OUTPUT} with {len(pages)} pages")


if __name__ == "__main__":
    main()
