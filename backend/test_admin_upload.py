"""Regression tests: admin upload/delete must not expose 'request' as a query param.

Previously ``request=None`` (no type annotation) in the FastAPI handler made
FastAPI treat ``request`` as a string query parameter, producing
``POST /api/v1/admin/documents/upload?request=...`` in /openapi.json and a
``AttributeError: 'str' object has no attribute 'client'`` at runtime.

These are static OpenAPI-contract tests (no database / network), so they run
fast and deterministically, and fail if the bug is ever reintroduced.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.main import app


def _get_openapi_operations():
    schema = app.openapi()
    paths = schema["paths"]
    return {
        "upload": paths["/api/v1/admin/documents/upload"]["post"],
        "delete": paths["/api/v1/admin/documents/{document_id}"]["delete"],
    }


def test_upload_has_no_request_query_param():
    ops = _get_openapi_operations()
    params = ops["upload"].get("parameters", [])
    names = {p.get("name") for p in params}
    assert "request" not in names, f"'request' leaked as a query parameter: {sorted(names)}"


def test_delete_has_no_request_query_param():
    ops = _get_openapi_operations()
    params = ops["delete"].get("parameters", [])
    names = {p.get("name") for p in params}
    assert "request" not in names, f"'request' leaked as a query parameter: {sorted(names)}"


def test_upload_declares_multipart_file_body():
    schema = app.openapi()
    op = schema["paths"]["/api/v1/admin/documents/upload"]["post"]
    body = op.get("requestBody", {})
    assert body, "upload operation must declare a request body"
    content = body.get("content", {})
    assert "multipart/form-data" in content, f"upload body must be multipart/form-data: {list(content)}"
    body_schema = content["multipart/form-data"].get("schema", {})
    # Resolve $ref if used (FastAPI emits a generated component ref).
    ref = body_schema.get("$ref")
    if ref:
        comp_name = ref.rsplit("/", 1)[-1]
        body_schema = schema["components"]["schemas"].get(comp_name, {})
    props = body_schema.get("properties", {}).get("file", {})
    is_binary = (
        props.get("type") == "string"
        and (
            props.get("format") == "binary"
            or props.get("contentMediaType") == "application/octet-stream"
        )
    )
    assert is_binary, f"file property missing/malformed: {props}"
    required = body_schema.get("required", [])
    assert "file" in required, f"file must be required; got {required}"


def test_upload_operation_still_secured():
    # Security (BearerAuth) must remain declared on the upload operation.
    ops = _get_openapi_operations()
    sec = ops["upload"].get("security")
    assert sec == [{"BearerAuth": []}], f"upload security missing: {sec}"