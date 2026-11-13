import os
import json
import logging

import google.generativeai as genai

logger = logging.getLogger(__name__)

# Default model — overridden by GEMINI_MODEL in .env
DEFAULT_MODEL = "gemini-1.5-flash"


class GeminiService:
    """Single place for all Gemini model calls and prompt templates."""

    def __init__(self):
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        model_name = os.getenv("GEMINI_MODEL", DEFAULT_MODEL)

        # Regular model for text responses
        self.model = genai.GenerativeModel(model_name)

        # JSON model — forces Gemini to return valid JSON every time
        self.json_model = genai.GenerativeModel(
            model_name,
            generation_config={"response_mime_type": "application/json"}
        )

    def analyze_meal(self, image_parts: list, user_profile: dict, prep_prompt: str = "") -> dict:
        """
        Analyze a meal image and return structured nutrition data as a dict.
        Uses JSON mode so we never need fragile regex parsing.
        """
        prep_note = f"Meal Preparation: {prep_prompt}" if prep_prompt else ""
        prompt = f"""
        User Profile:
        Name: {user_profile['name']}
        Health Goal: {user_profile['goal']}
        Daily Calorie Needs: {user_profile['tdee']:.0f} kcal
        {prep_note}

        You are an expert nutritionist. Analyze the food items in the image.
        Return ONLY a JSON object with this exact structure:
        {{
            "items": [
                {{"name": "Food Item Name", "calories": 123}}
            ],
            "total_calories": 456,
            "carbs_pct": 50,
            "protein_pct": 25,
            "fat_pct": 25,
            "recommendation": "Your food is healthy/not healthy because ...",
            "goal_feedback": "Based on your goal to {user_profile['goal']}, this meal ..."
        }}
        """
        response = self.json_model.generate_content([prompt, image_parts[0]])
        return json.loads(response.text)

    def generate_meal_plan(self, user_profile: dict, diet_preferences: str) -> str:
        """Generate a 7-day personalized meal plan as plain text."""
        prompt = f"""
        Generate a detailed 7-day personalized meal plan for a person with the goal to '{user_profile['goal']}'.
        Their daily calorie need is approximately {user_profile['tdee']:.0f} kcal.
        Food preferences: {diet_preferences}.
        Include breakfast, lunch, dinner, and snacks for each day.
        Add a grocery list at the end.
        """
        response = self.model.generate_content(prompt)
        return response.text

    def chat(self, user_profile: dict, question: str) -> str:
        """Answer a nutrition question personalised to the user's profile."""
        prompt = f"""
        User Profile:
        Name: {user_profile['name']}, Age: {user_profile['age']}, Gender: {user_profile['gender']}
        Height: {user_profile['height_cm']} cm, Weight: {user_profile['weight_kg']} kg
        Goal: {user_profile['goal']}, Daily Calorie Needs: {user_profile['tdee']:.0f} kcal

        Act as a friendly, personalised nutritionist and answer this question:
        {question}
        """
        response = self.model.generate_content(prompt)
        return response.text
