"""
BailBridge — Database Configuration (Consolidated)
"""
import firebase_admin
from firebase_admin import credentials, firestore
from config import settings

_db = None

def get_db():
    global _db
    if _db is None:
        if settings.prod_mode:
            # Real Firebase
            cred = credentials.Certificate(settings.firebase_service_account)
            firebase_admin.initialize_app(cred)
            _db = firestore.client()
            print("[Firebase] OK: Connected to Production Firestore.")
        else:
            # Mock Firestore for Dev
            from mockfirestore import MockFirestore
            _db = MockFirestore()
            print("[Firebase] [Test] Using Mock Firestore.")
    return _db
