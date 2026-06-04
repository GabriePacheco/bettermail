import os
from dotenv import load_dotenv

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from app.security import hash_email, normalize_email


load_dotenv()


def init_firebase():
    if firebase_admin._apps:
        return

    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    if credentials_path:
        credentials_path = credentials_path.strip().strip('"')

    if credentials_path and os.path.exists(credentials_path):
        print(f"Firebase usando credenciales locales: {credentials_path}")
        cred = credentials.Certificate(credentials_path)
        firebase_admin.initialize_app(cred)
    else:
        print("Firebase usando credenciales automáticas de Google Cloud")
        firebase_admin.initialize_app()


def get_db():
    init_firebase()
    return firestore.client()


def get_user_ref(email: str):
    db = get_db()
    email_hash = hash_email(email)
    return db.collection("mailbox_users").document(email_hash)


def get_or_create_mailbox_user(user, trial_limit: int):
    ref = get_user_ref(user.email)
    snapshot = ref.get()

    normalized_email = normalize_email(user.email)

    if snapshot.exists:
        data = snapshot.to_dict() or {}

        ref.update({
            "lastSeenAt": SERVER_TIMESTAMP,
            "displayName": user.display_name,
            "accountType": user.account_type,
            "timeZone": user.time_zone,
        })

        return ref, data

    data = {
        "email": normalized_email,
        "displayName": user.display_name,
        "accountType": user.account_type,
        "timeZone": user.time_zone,
        "status": "trial",
        "trialLimit": trial_limit,
        "trialUsed": 0,
        "preferredTone": "profesional",
        "createdAt": SERVER_TIMESTAMP,
        "firstSeenAt": SERVER_TIMESTAMP,
        "lastSeenAt": SERVER_TIMESTAMP,
    }

    ref.set(data)

    return ref, {
        "email": normalized_email,
        "displayName": user.display_name,
        "accountType": user.account_type,
        "timeZone": user.time_zone,
        "status": "trial",
        "trialLimit": trial_limit,
        "trialUsed": 0,
        "preferredTone": "profesional",
    }


def register_usage(email: str, payload: dict):
    db = get_db()

    db.collection("usage_logs").add({
        **payload,
        "emailHash": hash_email(email),
        "createdAt": SERVER_TIMESTAMP,
    })