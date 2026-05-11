"""Full-dataset export helpers using only stdlib dependencies."""
from __future__ import annotations

import csv
import html
import io
import json
import zipfile
from typing import Any, Iterable, List
from urllib.parse import quote


def _neutralize(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    return f"'{text}" if text.startswith(("=", "+", "-", "@")) else text


def records_to_csv(records: List[dict[str, Any]]) -> bytes:
    output = io.StringIO()
    columns = list(records[0].keys()) if records else []
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
    if columns:
        writer.writeheader()
        for record in records:
            writer.writerow({column: _neutralize(record.get(column)) for column in columns})
    return output.getvalue().encode("utf-8")


def records_to_csv_chunks(records: List[dict[str, Any]]) -> Iterable[bytes]:
    columns = list(records[0].keys()) if records else []
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
    if columns:
        writer.writeheader()
        yield output.getvalue().encode("utf-8")
        output.seek(0)
        output.truncate(0)
        for record in records:
            writer.writerow({column: _neutralize(record.get(column)) for column in columns})
            yield output.getvalue().encode("utf-8")
            output.seek(0)
            output.truncate(0)


def safe_export_filename(name: str, extension: str) -> str:
    cleaned = "".join(
        char if char.isalnum() or char in {"-", "_", "."} else "-"
        for char in (name or "sheet")
        if char not in {"\r", "\n", '"', "'", "\\", "/", ";"}
    ).strip("-._")
    if not cleaned:
        cleaned = "sheet"
    return f"{cleaned[:80]}-export.{extension}"


def content_disposition(filename: str) -> str:
    return f'attachment; filename="{filename}"; filename*=UTF-8\'\'{quote(filename)}'


def _xlsx_column_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _sheet_xml(records: List[dict[str, Any]]) -> str:
    columns = list(records[0].keys()) if records else []
    rows = [columns] + [[record.get(column) for column in columns] for record in records]
    xml_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row, start=1):
            coordinate = f"{_xlsx_column_name(column_index)}{row_index}"
            text = html.escape(_neutralize(value))
            cells.append(
                f'<c r="{coordinate}" t="inlineStr"><is><t>{text}</t></is></c>'
            )
        xml_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(xml_rows)}</sheetData></worksheet>'
    )


def records_to_xlsx(records: List[dict[str, Any]]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as workbook:
        workbook.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            "</Types>",
        )
        workbook.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>",
        )
        workbook.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Data" sheetId="1" r:id="rId1"/></sheets></workbook>',
        )
        workbook.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            "</Relationships>",
        )
        workbook.writestr("xl/worksheets/sheet1.xml", _sheet_xml(records))
    return buffer.getvalue()


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def records_to_pdf(
    title: str,
    records: List[dict[str, Any]],
    metadata: dict[str, Any],
) -> bytes:
    preview = records[:25]
    lines = [
        title,
        "",
        f"Rows exported: {len(records)}",
        f"Schema: {json.dumps(metadata.get('schema'), default=str)[:500]}",
        f"Filters: {json.dumps(metadata.get('filters', []), default=str)[:300]}",
    ]
    if metadata.get("comments") is not None:
        lines.append(f"Comments: {json.dumps(metadata.get('comments'), default=str)[:700]}")
    if metadata.get("charts") is not None:
        lines.append(f"Charts: {json.dumps(metadata.get('charts'), default=str)[:700]}")
    lines.append("")
    if preview:
        columns = list(preview[0].keys())
        lines.append(" | ".join(columns))
        for record in preview:
            lines.append(" | ".join(str(record.get(column, ""))[:24] for column in columns))
    else:
        lines.append("No rows matched this export.")

    content_lines = ["BT", "/F1 10 Tf", "50 780 Td", "14 TL"]
    for line in lines[:48]:
        content_lines.append(f"({_pdf_escape(line)}) Tj")
        content_lines.append("T*")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("utf-8")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]

    output = io.BytesIO()
    output.write(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(output.tell())
        output.write(f"{index} 0 obj\n".encode("ascii"))
        output.write(obj)
        output.write(b"\nendobj\n")
    xref = output.tell()
    output.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.write(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.write(
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii")
    )
    return output.getvalue()
