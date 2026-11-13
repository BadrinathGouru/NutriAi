class HealthCalculator:
    """Pure calculation helpers — no Supabase, no Gemini, easy to unit-test."""

    @staticmethod
    def calculate_bmr(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
        """Mifflin-St Jeor equation for Basal Metabolic Rate."""
        base = (10 * weight_kg) + (6.25 * height_cm) - (5 * age)
        return base + 5 if gender == "Male" else base - 161

    @staticmethod
    def calculate_tdee(bmr: float, activity_level: float) -> float:
        """Total Daily Energy Expenditure = BMR × activity multiplier."""
        return bmr * activity_level

    @staticmethod
    def calculate_bmi(weight_kg: float, height_cm: float) -> float:
        """Body Mass Index = weight(kg) / height(m)²."""
        height_m = height_cm / 100
        return weight_kg / (height_m ** 2)
