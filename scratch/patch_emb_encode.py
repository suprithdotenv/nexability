"""Fix encode in ml/nexability_ml/embeddings.py to handle SimpleEmbeddingModel properly."""
filepath = r'D:\sap\nexability\ml\nexability_ml\embeddings.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_code = '''        model = self._load_model()
        try:
            encoded = model.encode(
                [prefix + text for text in values],
                normalize_embeddings=True,
                convert_to_numpy=True,
            )
            rows = encoded.tolist() if hasattr(encoded, "tolist") else encoded
            vectors = [[float(value) for value in row] for row in rows]
        except Exception:
            raise RuntimeError(
                f"Embedding failed for configured model '{self.model_name}'."
            ) from None'''

new_code = '''        model = self._load_model()
        try:
            if isinstance(model, SimpleEmbeddingModel):
                return model.encode(values, prefix=prefix)
            encoded = model.encode(
                [prefix + text for text in values],
                normalize_embeddings=True,
                convert_to_numpy=True,
            )
            rows = encoded.tolist() if hasattr(encoded, "tolist") else encoded
            vectors = [[float(value) for value in row] for row in rows]
        except Exception:
            raise RuntimeError(
                f"Embedding failed for configured model '{self.model_name}'."
            ) from None'''

if old_code in content:
    content = content.replace(old_code, new_code)
    print("Replaced encode in embeddings.py")
else:
    print("WARNING: Could not find target in embeddings.py")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated embeddings.py successfully")
