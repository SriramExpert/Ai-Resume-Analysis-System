
import os
import sys

# Ensure we can import from src
sys.path.append(os.getcwd())

from src.utils.vector_db import VectorDBHandler

print("Starting raw test...")
vdb = VectorDBHandler()
print("Initialized.")
results = vdb.query("test query", n_results=1)
print("Success!")
print(results)
