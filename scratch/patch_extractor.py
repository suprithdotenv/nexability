path = r"D:\sap\nexability\backend\app\automated_pipeline\extractor.py"
with open(path, "r", encoding="utf-8") as f:
    code = f.read()

target = '''def _extract_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
        full_text = "\\n\\n".join(p for p in pages if p.strip())
        if full_text.strip():
            return full_text
    except Exception:
        pass

    raw = data.decode("latin-1", errors="ignore")
    matches = re.findall(r"BT\\s*(.*?)\\s*ET", raw, flags=re.DOTALL)
    blocks: list[str] = []
    for m in matches:
        clean = re.sub(r"\\\\\\((.*?)\\\\\\)", r"\\1", m)
        clean = re.sub(r"\\\\[0-9]+", "", clean).replace("\\\\n", " ").strip()
        if clean:
            blocks.append(clean)
    if not blocks:
        try:
            decoded = data.decode("utf-8")
            if decoded.strip():
                return decoded
        except Exception:
            pass
        return raw.strip()
    return "\\n".join(blocks)'''

replacement = '''def _extract_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
        full_text = "\\n\\n".join(p for p in pages if p.strip())
        if full_text.strip():
            return full_text.replace("\\x00", "")
    except Exception:
        pass

    raw = data.decode("latin-1", errors="ignore")
    matches = re.findall(r"BT\\s*(.*?)\\s*ET", raw, flags=re.DOTALL)
    blocks: list[str] = []
    for m in matches:
        clean = re.sub(r"\\\\\\((.*?)\\\\\\)", r"\\1", m)
        clean = re.sub(r"\\\\[0-9]+", "", clean).replace("\\\\n", " ").strip()
        if clean:
            blocks.append(clean)
    if not blocks:
        try:
            decoded = data.decode("utf-8")
            if decoded.strip() and not decoded.startswith("%PDF"):
                return decoded.replace("\\x00", "")
        except Exception:
            pass
        return ""
    return "\\n".join(blocks).replace("\\x00", "")'''

if target in code:
    code = code.replace(target, replacement, 1)
    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(code)
    print("Patched extractor.py successfully")
else:
    print("Target not found, trying normalized search")
    idx = code.find("def _extract_pdf")
    if idx != -1:
        print("Found def _extract_pdf at", idx)
