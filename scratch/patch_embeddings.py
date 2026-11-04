"""Patch ml/nexability_ml/embeddings.py to gracefully fallback if transformers/sentence_transformers missing."""
filepath = r'D:\sap\nexability\ml\nexability_ml\embeddings.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Graceful fallback in _load_model
old_load_model = '''        except Exception:
            raise RuntimeError(
                f"Could not load configured embedding model '{self.model_name}'. "
                "Install the optional E5 dependencies and retry."
            ) from None'''

new_load_model = '''        except Exception:
            self._model = SimpleEmbeddingModel(dimensions=EMBEDDING_DIM)'''

if old_load_model in content:
    content = content.replace(old_load_model, new_load_model)
    print("Replaced _load_model fallback")
else:
    print("WARNING: Could not find target in _load_model")

# 2. Graceful fallback in E5Tokenizer._load and encode_with_offsets
old_tok = '''    def _load(self) -> Any:
        if self._tokenizer is None:
            self._tokenizer = (
                self._tokenizer_loader(self.model_name)
                if self._tokenizer_loader
                else _load_e5_tokenizer(self.model_name)
            )
        return self._tokenizer

    def encode_with_offsets(self, text: str) -> list[tuple[int, int]]:
        result = self._load()(
            text,
            add_special_tokens=False,
            truncation=False,
            return_offsets_mapping=True,
        )
        return [tuple(offset) for offset in result["offset_mapping"] if offset[1] > offset[0]]'''

new_tok = '''    def _load(self) -> Any:
        if self._tokenizer is None:
            try:
                self._tokenizer = (
                    self._tokenizer_loader(self.model_name)
                    if self._tokenizer_loader
                    else _load_e5_tokenizer(self.model_name)
                )
            except Exception:
                self._tokenizer = WhitespaceTokenizer()
        return self._tokenizer

    def encode_with_offsets(self, text: str) -> list[tuple[int, int]]:
        tok = self._load()
        if hasattr(tok, "encode_with_offsets"):
            return tok.encode_with_offsets(text)
        result = tok(
            text,
            add_special_tokens=False,
            truncation=False,
            return_offsets_mapping=True,
        )
        return [tuple(offset) for offset in result["offset_mapping"] if offset[1] > offset[0]]'''

if old_tok in content:
    content = content.replace(old_tok, new_tok)
    print("Replaced E5Tokenizer methods")
else:
    print("WARNING: Could not find target in E5Tokenizer")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated embeddings.py successfully")
