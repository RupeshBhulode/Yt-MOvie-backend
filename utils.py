# utils.py
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json

# -------------------------------------------
# 🔥 FIREBASE INITIALIZATION
# -------------------------------------------
firebase_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")

if not firebase_admin._apps:
    if firebase_json:
        cred_dict = json.loads(firebase_json)
        cred = credentials.Certificate(cred_dict)
    else:
        cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# -------------------------------------------
# 🎬 MOVIE CATEGORIES
# -------------------------------------------
CATEGORIES = [
    "Hindi Action",
    "Hindi Comedy",
    "Hindi Family",
    "Hindi Horror",
    "Hindi Suspense Thriller",
    "Hindi Animated"
]
