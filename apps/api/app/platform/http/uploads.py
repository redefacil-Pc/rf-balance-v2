from fastapi import UploadFile


async def read_upload_limited(upload: UploadFile, *, max_bytes: int) -> bytes:
    """Lê no máximo o limite mais um byte, sem carregar um corpo arbitrário na memória."""
    content = await upload.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise ValueError("upload-too-large")
    return content


def matches_declared_content_type(content_type: str, content: bytes) -> bool:
    signatures = {
        "application/pdf": (b"%PDF-",),
        "image/jpeg": (b"\xff\xd8\xff",),
        "image/png": (b"\x89PNG\r\n\x1a\n",),
    }
    return any(content.startswith(signature) for signature in signatures.get(content_type, ()))
