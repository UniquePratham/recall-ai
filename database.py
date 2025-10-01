from pymongo import MongoClient
from dotenv import load_dotenv
import os
from datetime import datetime

from config import config

load_dotenv()


def get_db_connection():
    client = MongoClient(os.getenv("MONGODB_URI"))
    return client[os.getenv("DB_NAME")]


async def is_user_activated(user_id=None, username=None):
    db = get_db_connection()
    query = {}
    if user_id:
        query["user_id"] = user_id
    elif username:
        query["username"] = username
    else:
        return False
    user = db.users.find_one(query)
    return user and user.get("is_activated", False)


def _normalize(key: str) -> str:
    return (key or "").strip().upper()


async def activate_user(user_id, username, license_key):
    db = get_db_connection()
    try:
        normalized_input = _normalize(license_key)

        # First priority: environment-configured license key (private instance)
        env_license = _normalize(config.app.license_key)
        owner_id = config.app.owner_telegram_id

        if env_license:
            if normalized_input != env_license:
                return False, "Invalid license key."

            if owner_id and user_id != owner_id:
                return False, "This license key is reserved for the owner only."

            db.users.update_one(
                {"user_id": user_id},
                {"$set": {
                    "username": username,
                    "is_activated": True,
                    "activated_at": datetime.now(),
                    "license_key": normalized_input,
                    "activation_source": "env"
                }},
                upsert=True
            )

            # Optionally ensure the license_keys collection reflects this license for traceability
            db.license_keys.update_one(
                {"key": env_license},
                {"$set": {
                    "key": env_license,
                    "is_used": True,
                    "used_by": user_id,
                    "username": username,
                    "used_at": datetime.now(),
                    "source": "env"
                }},
                upsert=True
            )

            return True, "Your account has been successfully activated!"

        # Fallback: legacy database-managed license keys
        key_doc = db.license_keys.find_one({"key": normalized_input})
        if not key_doc:
            return False, "Invalid license key."
        if key_doc.get("is_used", False):
            # If the key is used by the same user, allow reactivation
            if key_doc.get("used_by") == user_id:
                db.users.update_one(
                    {"user_id": user_id},
                    {"$set": {
                        "username": username,
                        "is_activated": True,
                        "activated_at": datetime.now(),
                        "license_key": normalized_input,
                        "activation_source": "db"
                    }}
                )
                return True, "Your account has been reactivated!"
            else:
                return False, "This license key is already in use."

        # Mark license key as used
        db.license_keys.update_one(
            {"key": normalized_input},
            {"$set": {"is_used": True, "used_by": user_id,
                      "username": username, "used_at": datetime.now(), "source": "db"}}
        )

        # Activate user
        db.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "username": username,
                "is_activated": True,
                "activated_at": datetime.now(),
                "license_key": normalized_input,
                "activation_source": "db"
            }},
            upsert=True
        )

        return True, "Your account has been successfully activated!"
    except Exception as e:
        return False, f"Activation failed: {str(e)}"
