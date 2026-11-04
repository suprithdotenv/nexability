filepath = r'D:\sap\nexability\backend\app\api\v1\endpoints\employers.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

target = 'process_job_document(doc_record.id, db=db, content=content)'
replacement = 'process_job_document(doc_record.id, db=db, content=content)\n            db.refresh(doc_record)'

if target in content:
    content = content.replace(target, replacement, 1)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Successfully added db.refresh(doc_record) to employers.py")
else:
    print("Could not find target in employers.py")
