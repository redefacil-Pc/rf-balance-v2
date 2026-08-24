from urllib.parse import quote


def content_disposition(file_name: str, *, inline: bool = False) -> str:
    disposition = "inline" if inline else "attachment"
    cleaned = file_name.replace("\r", "").replace("\n", "").strip() or "arquivo"
    ascii_fallback = "".join(
        character if character.isascii() and (character.isalnum() or character in ".-_ ") else "_"
        for character in cleaned
    ).strip() or "arquivo"
    encoded = quote(cleaned, safe="")
    return f'{disposition}; filename="{ascii_fallback}"; filename*=UTF-8\'\'{encoded}'
