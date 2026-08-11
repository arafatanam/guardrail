import json
import os
import requests
from supabase import create_client

supabase = create_client(os.getenv("SUPABASE_URL"),
                         os.getenv("SUPABASE_SERVICE_ROLE_KEY"))

with open("../test_cases/seed_cases.json") as f:
    cases = json.load(f)

for case in cases:
    supabase.table("test_cases").insert(case).execute()
print("Seeded 10 test cases")
