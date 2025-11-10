from rag.retriever import SimpleRetriever

retriever = SimpleRetriever()
query = "add backpack to cart in sauce demo app"

results = retriever.retrieve(query)
print("\n🔍 Query:", query)
print("📚 Top retrieved contexts:\n")

for i, (name, text) in enumerate(results, start=1):
    print(f"{i}. {name}")
