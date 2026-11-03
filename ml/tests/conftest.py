import os

# Unit tests stay offline even when a developer's .env selects E5.
os.environ["EMBEDDING_MODEL"] = "placeholder"
