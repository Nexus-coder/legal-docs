import re
import zipfile
from copy import deepcopy
from html import escape
from io import BytesIO
from typing import Any
from xml.sax.saxutils import escape as xml_escape

from fastapi import HTTPException, status

ALLOWED_NODES = {
    "doc",
    "paragraph",
    "text",
    "heading",
    "bulletList",
    "orderedList",
    "listItem",
    "blockquote",
    "horizontalRule",
    "hardBreak",
}
ALLOWED_MARKS = {"bold", "italic", "strike", "code", "citationRef"}
ALLOWED_NODE_ATTRS = {
    "heading": {"level"},
    "orderedList": {"start", "type"},
    "bulletList": {"type"},
}
ALLOWED_MARK_ATTRS = {
    "citationRef": {"evidenceId", "label"},
}
SCRIPT_LIKE = re.compile(r"<\s*/?\s*script\b|javascript:|on[a-z]+\s*=", re.IGNORECASE)


def text_to_editor_json(text: str) -> dict[str, Any]:
    paragraphs = []
    for block in (text or "").replace("\r\n", "\n").split("\n\n"):
        lines = [line for line in block.split("\n") if line.strip()]
        if not lines:
            continue
        paragraphs.append(
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "\n".join(lines)}],
            }
        )
    return {"type": "doc", "content": paragraphs or [{"type": "paragraph"}]}


def validate_editor_json(editor_json: Any, allowed_evidence_ids: set[int]) -> dict[str, Any]:
    if not isinstance(editor_json, dict):
        raise _invalid_editor_json("Editor document must be a JSON object.")
    normalized = deepcopy(editor_json)
    _validate_node(normalized, allowed_evidence_ids, is_root=True)
    return normalized


def editor_json_to_plain_text(editor_json: dict[str, Any]) -> str:
    lines = _node_to_lines(editor_json)
    return "\n".join(lines).strip()


def editor_json_to_preview_html(editor_json: dict[str, Any]) -> str:
    return f'<div class="export-preview">{_node_to_html(editor_json)}</div>'


def editor_json_to_docx(editor_json: dict[str, Any]) -> bytes:
    paragraphs = _paragraph_texts(editor_json)
    body = "".join(_docx_paragraph(paragraph) for paragraph in paragraphs)
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}<w:sectPr/></w:body></w:document>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/></Relationships>'
    )
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("word/document.xml", document_xml)
    return buffer.getvalue()


def _validate_node(node: dict[str, Any], allowed_evidence_ids: set[int], *, is_root: bool = False) -> None:
    node_type = node.get("type")
    if node_type not in ALLOWED_NODES:
        raise _invalid_editor_json(f"Unsupported editor node: {node_type}")
    if is_root and node_type != "doc":
        raise _invalid_editor_json("Editor document root must be a doc node.")
    if not isinstance(node.get("attrs", {}), dict):
        raise _invalid_editor_json("Editor node attrs must be an object.")
    allowed_attrs = ALLOWED_NODE_ATTRS.get(node_type, set())
    for attr in node.get("attrs", {}):
        if attr not in allowed_attrs:
            raise _invalid_editor_json(f"Unsupported {node_type} attr: {attr}")
    if node_type == "heading":
        level = node.get("attrs", {}).get("level", 1)
        if level not in {1, 2, 3}:
            raise _invalid_editor_json("Only heading levels 1-3 are allowed.")
    if node_type == "text":
        text = node.get("text", "")
        if not isinstance(text, str):
            raise _invalid_editor_json("Text nodes must contain string text.")
        if SCRIPT_LIKE.search(text):
            raise _invalid_editor_json("Script-like content is not allowed.")
    elif "text" in node:
        raise _invalid_editor_json("Only text nodes may contain text.")
    marks = node.get("marks", [])
    if marks is None:
        marks = []
    if not isinstance(marks, list):
        raise _invalid_editor_json("Editor marks must be a list.")
    for mark in marks:
        _validate_mark(mark, allowed_evidence_ids)
    content = node.get("content", [])
    if content is None:
        content = []
    if not isinstance(content, list):
        raise _invalid_editor_json("Editor node content must be a list.")
    if node_type == "text" and content:
        raise _invalid_editor_json("Text nodes cannot have child content.")
    for child in content:
        if not isinstance(child, dict):
            raise _invalid_editor_json("Editor child nodes must be objects.")
        _validate_node(child, allowed_evidence_ids)


def _validate_mark(mark: Any, allowed_evidence_ids: set[int]) -> None:
    if not isinstance(mark, dict):
        raise _invalid_editor_json("Editor marks must be objects.")
    mark_type = mark.get("type")
    if mark_type not in ALLOWED_MARKS:
        raise _invalid_editor_json(f"Unsupported editor mark: {mark_type}")
    attrs = mark.get("attrs", {})
    if attrs is None:
        attrs = {}
    if not isinstance(attrs, dict):
        raise _invalid_editor_json("Editor mark attrs must be an object.")
    allowed_attrs = ALLOWED_MARK_ATTRS.get(mark_type, set())
    for attr in attrs:
        if attr not in allowed_attrs:
            raise _invalid_editor_json(f"Unsupported {mark_type} attr: {attr}")
    if mark_type != "citationRef":
        return
    evidence_id = attrs.get("evidenceId")
    if not isinstance(evidence_id, int) or evidence_id not in allowed_evidence_ids:
        raise _invalid_editor_json("Citation anchors must reference evidence on this matter.")
    label = attrs.get("label")
    if label is not None and (not isinstance(label, str) or SCRIPT_LIKE.search(label)):
        raise _invalid_editor_json("Citation anchor labels must be safe text.")


def _node_to_lines(node: dict[str, Any]) -> list[str]:
    node_type = node.get("type")
    if node_type == "text":
        return [node.get("text", "")]
    if node_type == "hardBreak":
        return ["\n"]
    content = node.get("content") or []
    if node_type in {"paragraph", "heading", "blockquote", "listItem"}:
        return ["".join("".join(_node_to_lines(child)) for child in content)]
    if node_type in {"bulletList", "orderedList"}:
        lines = []
        for index, child in enumerate(content, start=1):
            prefix = "- " if node_type == "bulletList" else f"{index}. "
            child_text = "\n".join(_node_to_lines(child)).strip()
            if child_text:
                lines.append(f"{prefix}{child_text}")
        return lines
    if node_type == "horizontalRule":
        return ["---"]
    lines = []
    for child in content:
        for line in _node_to_lines(child):
            if line.strip() or lines and lines[-1].strip():
                lines.append(line)
    return lines


def _node_to_html(node: dict[str, Any]) -> str:
    node_type = node.get("type")
    content = "".join(_node_to_html(child) for child in node.get("content") or [])
    if node_type == "doc":
        return content
    if node_type == "paragraph":
        return f"<p>{content}</p>"
    if node_type == "heading":
        level = node.get("attrs", {}).get("level", 1)
        return f"<h{level}>{content}</h{level}>"
    if node_type == "blockquote":
        return f"<blockquote>{content}</blockquote>"
    if node_type == "bulletList":
        return f"<ul>{content}</ul>"
    if node_type == "orderedList":
        return f"<ol>{content}</ol>"
    if node_type == "listItem":
        return f"<li>{content}</li>"
    if node_type == "horizontalRule":
        return "<hr />"
    if node_type == "hardBreak":
        return "<br />"
    if node_type != "text":
        return ""
    text = escape(node.get("text", ""))
    for mark in node.get("marks") or []:
        mark_type = mark.get("type")
        if mark_type == "bold":
            text = f"<strong>{text}</strong>"
        elif mark_type == "italic":
            text = f"<em>{text}</em>"
        elif mark_type == "strike":
            text = f"<s>{text}</s>"
        elif mark_type == "code":
            text = f"<code>{text}</code>"
        elif mark_type == "citationRef":
            evidence_id = mark.get("attrs", {}).get("evidenceId")
            text = f'<span data-citation-evidence-id="{evidence_id}" class="citation-ref">{text}</span>'
    return text


def _paragraph_texts(editor_json: dict[str, Any]) -> list[str]:
    text = editor_json_to_plain_text(editor_json)
    return [line for line in text.splitlines() if line.strip()] or [""]


def _docx_paragraph(text: str) -> str:
    escaped = xml_escape(text, {'"': "&quot;"})
    return f"<w:p><w:r><w:t>{escaped}</w:t></w:r></w:p>"


def _invalid_editor_json(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=message)
