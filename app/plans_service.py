from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from app.firebase_service import get_db


DEFAULT_PLANS = [
    {
        "id": "pro_monthly",
        "name": "BetterMail Pro",
        "price": 4.99,
        "currency": "USD",
        "monthlyLimit": 300,
        "active": True,
    }
]


def list_plans():
    db = get_db()
    plans_ref = db.collection("plans")

    for plan in DEFAULT_PLANS:
        plans_ref.document(plan["id"]).set({
            **plan,
            "updatedAt": SERVER_TIMESTAMP,
        }, merge=True)

    snapshots = plans_ref.where("active", "==", True).stream()
    plans = []

    for snapshot in snapshots:
        data = snapshot.to_dict() or {}
        plans.append({
            "id": data.get("id", snapshot.id),
            "name": data.get("name", ""),
            "price": float(data.get("price", 0)),
            "currency": data.get("currency", "USD"),
            "monthlyLimit": int(data.get("monthlyLimit", 0)),
            "active": bool(data.get("active", False)),
        })

    return plans


def get_plan(plan_id: str):
    db = get_db()
    snapshot = db.collection("plans").document(plan_id).get()

    if snapshot.exists:
        data = snapshot.to_dict() or {}

        if data.get("active"):
            return {
                "id": data.get("id", snapshot.id),
                "name": data.get("name", ""),
                "price": float(data.get("price", 0)),
                "currency": data.get("currency", "USD"),
                "monthlyLimit": int(data.get("monthlyLimit", 0)),
                "active": bool(data.get("active", False)),
            }

    for plan in list_plans():
        if plan["id"] == plan_id and plan["active"]:
            return plan

    return None
