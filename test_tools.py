"""
test_tools.py — sanity-check every tool BEFORE handing them to an LLM.

Same idea as the reference repo's "2-import-tools.py": call each function
directly in plain Python and print what it returns. If a tool is broken
here, it'll be much harder to debug once an LLM starts calling it.
"""

from build_tools import get_document, search_documents, list_document_types, propose_type_update

print("Document types in DB:")
print(list_document_types())

print("\nSearch for 'late delivery penalty':")
for hit in search_documents("late delivery penalty", top_k=3):
    print(f"  [{hit['type']}] (sim={hit['similarity']}) {hit['matched_excerpt'][:80]}...")

print("\nFetch document id=1:")
print(get_document(1))

print("\nPropose reclassifying doc 1 as 'invoice':")
print(propose_type_update(1, "invoice"))