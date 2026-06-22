from datetime import datetime, timedelta, timezone

from app.firebase_service import get_db


def _number(value, cast=float):
    try:
        return cast(value or 0)
    except (TypeError, ValueError):
        return cast(0)


def get_openai_cost_summary(days: int = 30):
    db = get_db()
    today = datetime.now(timezone.utc).date()
    daily = []

    for offset in range(days - 1, -1, -1):
        day = (today - timedelta(days=offset)).isoformat()
        snapshot = db.collection("operational_metrics").document(f"openai_{day}").get()
        data = snapshot.to_dict() if snapshot.exists else {}
        daily.append(
            {
                "date": day,
                "requests": _number(data.get("requests"), int),
                "promptTokens": _number(data.get("promptTokens"), int),
                "cachedPromptTokens": _number(data.get("cachedPromptTokens"), int),
                "completionTokens": _number(data.get("completionTokens"), int),
                "totalTokens": _number(data.get("totalTokens"), int),
                "estimatedCostUsd": round(
                    _number(data.get("estimatedCostUsd")), 6
                ),
                "model": data.get("model"),
                "pricingLabel": data.get("pricingLabel"),
            }
        )

    return {
        "days": days,
        "requests": sum(item["requests"] for item in daily),
        "promptTokens": sum(item["promptTokens"] for item in daily),
        "cachedPromptTokens": sum(item["cachedPromptTokens"] for item in daily),
        "completionTokens": sum(item["completionTokens"] for item in daily),
        "totalTokens": sum(item["totalTokens"] for item in daily),
        "estimatedCostUsd": round(
            sum(item["estimatedCostUsd"] for item in daily), 6
        ),
        "daily": daily,
    }
