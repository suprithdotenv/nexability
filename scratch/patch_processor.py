path = r"D:\sap\nexability\backend\app\automated_pipeline\processor.py"
with open(path, "r", encoding="utf-8") as f:
    code = f.read()

code = code.replace('chunk_text=c["chunk_text"],', 'chunk_text=str(c["chunk_text"]).replace("\\x00", ""),')
with open(path, "w", encoding="utf-8", newline="\r\n") as f:
    f.write(code)
print("Sanitized chunk_text in processor.py")
