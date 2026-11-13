import logging

logger = logging.getLogger(__name__)


class MealRepository:
    """All Supabase calls related to meals, diet plans, and chat history."""

    def __init__(self, supabase_client):
        self.db = supabase_client

    # ── Meal images ───────────────────────────────────────────────────────────
    def upload_image(self, filename: str, image_bytes: bytes) -> str:
        """Upload image to Supabase storage and return its public URL."""
        self.db.storage.from_("meal-images").upload(filename, image_bytes)
        return self.db.storage.from_("meal-images").get_public_url(filename)

    # ── Meal history ──────────────────────────────────────────────────────────
    def save_meal(self, user_id, timestamp: str, image_url: str,
                  summary: str, meal_consumed: str, calories):
        """Save one meal analysis result."""
        self.db.table("meal_history").insert({
            "user_id": user_id,
            "timestamp": timestamp,
            "image_url": image_url,
            "summary": summary,
            "meal_consumed": meal_consumed,
            "calories": str(calories)
        }).execute()

    # ── Diet plans ────────────────────────────────────────────────────────────
    def save_diet_plan(self, user_id, plan: str, timestamp: str):
        """Save a generated 7-day meal plan."""
        self.db.table("diet_plans").insert({
            "user_id": user_id,
            "plan": plan,
            "timestamp": timestamp
        }).execute()

    def get_last_diet_plan(self, user_id) -> str | None:
        """Return the most recent diet plan text for a user, or None."""
        result = (
            self.db.table("diet_plans")
            .select("plan")
            .eq("user_id", user_id)
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0]["plan"] if result.data else None

    # ── Chat history ──────────────────────────────────────────────────────────
    def save_chat_message(self, user_id, role: str, content: str, timestamp: str):
        """Persist a single chat message (role = 'user' or 'assistant')."""
        self.db.table("chat_history").insert({
            "user_id": user_id,
            "role": role,
            "content": content,
            "timestamp": timestamp
        }).execute()

    def get_chat_history(self, user_id, limit: int = 20) -> list:
        """Load the most recent chat messages for a user (oldest first)."""
        result = (
            self.db.table("chat_history")
            .select("role", "content")
            .eq("user_id", user_id)
            .order("timestamp", desc=False)
            .limit(limit)
            .execute()
        )
        return result.data if result.data else []

    # ── Meal history display ──────────────────────────────────────────────────
    def get_meal_history(self, user_id, limit: int = 10) -> list:
        """Return the most recent meals for display in the History tab."""
        result = (
            self.db.table("meal_history")
            .select("timestamp", "meal_consumed", "calories", "image_url")
            .eq("user_id", user_id)
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data if result.data else []

    def get_calorie_trend(self, user_id, days: int = 7) -> dict:
        """
        Return a dict of {date_string: total_calories} for the last `days` days.
        Used to draw the calorie trend chart.
        """
        result = (
            self.db.table("meal_history")
            .select("timestamp", "calories")
            .eq("user_id", user_id)
            .order("timestamp", desc=False)
            .execute()
        )
        trend: dict = {}
        for row in (result.data or []):
            date = row["timestamp"][:10]          # "YYYY-MM-DD"
            try:
                cal = float(row["calories"])
            except (ValueError, TypeError):
                cal = 0.0
            trend[date] = trend.get(date, 0.0) + cal

        # Keep only last `days` dates
        sorted_dates = sorted(trend.keys())[-days:]
        return {d: trend[d] for d in sorted_dates}
