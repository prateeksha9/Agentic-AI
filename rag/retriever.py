from pathlib import Path
from sentence_transformers import SentenceTransformer, util

class SimpleRetriever:
    def __init__(self, kb_path="rag/knowledge_base"):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.docs = {}
        for f in Path(kb_path).glob("*.txt"):
            text = f.read_text().strip()
            if text:
                self.docs[f.stem] = text
        if not self.docs:
            print("[red] Warning: No knowledge base files found. Add .txt files in rag/knowledge_base[/red]")

    def retrieve(self, query, top_k=2):
        if not self.docs:
            return [("default", "No KB available.")]
        all_texts, app_names = zip(*self.docs.items())
        embeddings = self.model.encode(list(all_texts), convert_to_tensor=True)
        query_emb = self.model.encode(query, convert_to_tensor=True)
        scores = util.cos_sim(query_emb, embeddings)[0]
        top_idx = scores.argsort(descending=True)[:top_k]
        return [(app_names[i], all_texts[i]) for i in top_idx]
