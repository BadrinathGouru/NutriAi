# app2.py — Streamlit UI for NutriAi
# All AI calls → GeminiService | All DB calls → UserRepository / MealRepository

import logging
import os
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv
from PIL import Image
from supabase import create_client, Client

from services.gemini_service import GeminiService
from services.health_calculator import HealthCalculator
from services.meal_repository import MealRepository
from services.user_repository import UserRepository

# ── Setup ─────────────────────────────────────────────────────────────────────
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")
logger = logging.getLogger(__name__)

# ── Page config — MUST be the first Streamlit command in the script ───────────
st.set_page_config(page_title="NutriAi", page_icon="🥘", layout="wide")

# ── Clients — cached so they are created only once, not on every page refresh ──
@st.cache_resource
def get_services():
    """
    @st.cache_resource runs this function exactly once and reuses the result.
    Without it, Streamlit recreates Supabase and Gemini clients on every click.
    """
    _supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    return GeminiService(), UserRepository(_supabase), MealRepository(_supabase)

gemini, user_repo, meal_repo = get_services()
st.markdown("<h1 style='text-align: center;'>🥘 NutriAi - AI Meal Analyzer</h1>",
            unsafe_allow_html=True)

# ── Session state defaults ────────────────────────────────────────────────────
if "user_data" not in st.session_state:
    st.session_state.user_data = {
        "logged_in": False, "name": "", "username": "", "gender": "",
        "age": 0, "height_cm": 0, "weight_kg": 0, "goal": "",
        "activity_level": 1.2, "tdee": 0.0, "user_id": None
    }

if "messages" not in st.session_state:
    st.session_state.messages = []   # list of {"role": ..., "content": ...}

if "page" not in st.session_state:
    st.session_state.page = "login"

# ── Activity multipliers ──────────────────────────────────────────────────────
ACTIVITY_MAP = {
    "Sedentary (little or no exercise)":                        1.2,
    "Lightly Active (light exercise/sports 1-3 days/week)":     1.375,
    "Moderately Active (moderate exercise/sports 3-5 days/week)": 1.55,
    "Very Active (hard exercise/sports 6-7 days/week)":         1.725,
    "Super Active (very hard exercise/sports & physical job)":  1.9,
}


# ══════════════════════════════════════════════════════════════════════════════
# LOGIN PAGE
# ══════════════════════════════════════════════════════════════════════════════
def login_page():
    st.title("NutriAi Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username and password:
            try:
                user = user_repo.verify_login(username, password)
                if user:
                    st.session_state.user_data.update({
                        "logged_in":      True,
                        "username":       username,
                        "name":           user["name"],
                        "age":            user["age"],
                        "gender":         user["gender"],
                        "height_cm":      user["height_cm"],
                        "weight_kg":      user["weight_kg"],
                        "goal":           user["goal"],
                        "activity_level": user["activity_level"],
                        "tdee":           user["tdee"],
                        "user_id":        user["id"],
                    })
                    # Load this user's chat history from Supabase
                    st.session_state.messages = meal_repo.get_chat_history(user["id"])
                    st.success("Login successful!")
                    st.session_state.page = "main"
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
            except Exception as e:
                logger.error("Login error: %s", e)
                st.error("Something went wrong during login. Please try again.")
        else:
            st.warning("Please enter both username and password.")

    if st.button("Go to Signup"):
        st.session_state.page = "signup"
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# SIGNUP PAGE
# ══════════════════════════════════════════════════════════════════════════════
def signup_page():
    st.title("NutriAi Signup")
    name     = st.text_input("Name")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    age      = st.number_input("Age", min_value=1, max_value=120, value=25)
    gender   = st.selectbox("Gender", ["Male", "Female"])
    height   = st.number_input("Height (in cm)", min_value=50, max_value=250, value=170)
    weight   = st.number_input("Weight (in kg)", min_value=20, max_value=300, value=70)
    goal     = st.selectbox("Health Goal", ["Lose Weight", "Maintain Weight", "Gain Muscle"])
    activity_label = st.selectbox("Activity Level", list(ACTIVITY_MAP.keys()))

    if st.button("Signup"):
        if name and username and password:
            try:
                activity_level = ACTIVITY_MAP[activity_label]
                bmr  = HealthCalculator.calculate_bmr(weight, height, age, gender)
                tdee = HealthCalculator.calculate_tdee(bmr, activity_level)

                result = user_repo.create_user({
                    "name": name, "username": username,
                    "age": age, "gender": gender,
                    "height_cm": height, "weight_kg": weight,
                    "goal": goal, "activity_level": activity_level, "tdee": tdee
                }, password)

                if result:
                    st.success("Signup successful! Please login.")
                    st.session_state.page = "login"
                    st.rerun()
                else:
                    st.error("Signup failed. Try a different username.")
            except Exception as e:
                logger.error("Signup error: %s", e)
                st.error("Signup failed. The username may already be taken.")
        else:
            st.warning("Please fill in all fields.")

    if st.button("Go to Login"):
        st.session_state.page = "login"
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN APP (shown after login)
# ══════════════════════════════════════════════════════════════════════════════
def main_app():
    user = st.session_state.user_data

    # ── Sidebar ───────────────────────────────────────────────────────────────
    st.sidebar.title(f"Hello, {user['name']}!")
    with st.sidebar.expander("Your Health Stats"):
        bmi = HealthCalculator.calculate_bmi(user["weight_kg"], user["height_cm"])
        st.metric("Your BMI", f"{bmi:.2f}")
        st.metric("Daily Calorie Needs", f"{user['tdee']:.0f} kcal")

    # Logout button — clears all session state and returns to login
    if st.sidebar.button("🚪 Logout"):
        st.session_state.clear()
        st.rerun()

    analyze_tab, plan_tab, chat_tab, history_tab = st.tabs(
        ["📊 Analyze Meal", "📋 Personalized Meal Plan", "🗣️ Ask NutriAi", "📜 Meal History"]
    )

    # ── TAB 1: Analyze Meal ───────────────────────────────────────────────────
    with analyze_tab:
        col1, col2 = st.columns([2, 1])
        with col1:
            uploaded_file  = st.file_uploader("📤 Upload your meal photo...",
                                               type=["jpg", "jpeg", "png"])
            meal_consumed  = st.text_input("What meal did you consume?")
            prep_prompt    = st.text_input("How was your meal prepared? (e.g., grilled, fried, steamed)")
            analyze_clicked = st.button("🍽️ Analyze My Meal")

        with col2:
            if uploaded_file:
                st.image(Image.open(uploaded_file), caption="📸 Uploaded Meal", width=300)

        if uploaded_file and analyze_clicked:
            with st.spinner("🔍 Analyzing your meal..."):
                try:
                    image_bytes = uploaded_file.getvalue()
                    image_parts = [{"mime_type": uploaded_file.type, "data": image_bytes}]

                    # Gemini returns structured JSON — no regex needed
                    result = gemini.analyze_meal(image_parts, user, prep_prompt)

                    # Display results
                    st.subheader("🧠 Nutritional Analysis")

                    st.markdown("### 🍱 Food Items")
                    for item in result.get("items", []):
                        st.markdown(f"- **{item['name']}** — {item['calories']} kcal")

                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Total Calories",  f"{result.get('total_calories', 'N/A')} kcal")
                    c2.metric("Carbs",           f"{result.get('carbs_pct', 'N/A')}%")
                    c3.metric("Protein",         f"{result.get('protein_pct', 'N/A')}%")
                    c4.metric("Fat",             f"{result.get('fat_pct', 'N/A')}%")

                    st.info(result.get("recommendation", ""))
                    st.success(result.get("goal_feedback", ""))

                    # ── Calorie Warning ───────────────────────────────────────
                    total_cal = result.get("total_calories", 0)
                    try:
                        pct = float(total_cal) / user["tdee"] * 100
                        st.progress(min(float(total_cal) / user["tdee"], 1.0),
                                    text=f"This meal is **{pct:.0f}%** of your daily calorie needs")
                        if pct > 50:
                            st.warning(
                                f"⚠️ This single meal uses {pct:.0f}% of your daily calories "
                                f"({user['tdee']:.0f} kcal). Consider a lighter next meal!"
                            )
                    except (ValueError, TypeError):
                        pass

                    # Save to Supabase
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    filename  = f"{user['username']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
                    image_url = meal_repo.upload_image(filename, image_bytes)
                    meal_repo.save_meal(
                        user["user_id"], timestamp, image_url,
                        str(result), meal_consumed,
                        result.get("total_calories", "N/A")
                    )
                except Exception as e:
                    logger.error("Meal analysis error: %s", e)
                    st.error("Failed to analyse the meal. Please try again.")

    # ── TAB 2: Meal Plan ──────────────────────────────────────────────────────
    with plan_tab:
        st.subheader("🍽️ Generate a Personalized Meal Plan")
        diet_preferences = st.text_input(
            f"Hello {user['name']}, enter your food preferences (e.g., vegetarian, low-carb):"
        )

        if st.button("Generate Meal Plan"):
            with st.spinner("Creating your personalised meal plan..."):
                try:
                    plan = gemini.generate_meal_plan(user, diet_preferences)
                    st.subheader("Your 7-Day Personalized Meal Plan:")
                    st.write(plan)
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    meal_repo.save_diet_plan(user["user_id"], plan, timestamp)
                    st.download_button("Download Meal Plan 📄", data=plan,
                                       file_name="personalized_meal_plan.txt",
                                       mime="text/plain")
                except Exception as e:
                    logger.error("Meal plan generation error: %s", e)
                    st.error("Failed to generate meal plan. Please try again.")

        if st.button("View Last Generated Meal Plan"):
            try:
                last_plan = meal_repo.get_last_diet_plan(user["user_id"])
                if last_plan:
                    st.subheader("Last Generated Meal Plan:")
                    st.write(last_plan)
                else:
                    st.info("No meal plan found. Generate one first!")
            except Exception as e:
                logger.error("Fetch meal plan error: %s", e)
                st.error("Failed to load meal plan.")

    # ── TAB 3: Chat ───────────────────────────────────────────────────────────
    with chat_tab:
        st.subheader("🗣️ Ask NutriAi")

        # Show previous messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Input (text_input + button — chat_input is not allowed inside st.tabs)
        user_question = st.text_input("What would you like to know about nutrition?",
                                      key="chat_input_box")
        if st.button("Send 💬") and user_question:
            try:
                # Show user message
                with st.chat_message("user"):
                    st.markdown(user_question)
                st.session_state.messages.append({"role": "user", "content": user_question})

                # Get AI response
                response_text = gemini.chat(user, user_question)
                with st.chat_message("assistant"):
                    st.write(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})

                # Save both messages to Supabase
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                meal_repo.save_chat_message(user["user_id"], "user",      user_question,  timestamp)
                meal_repo.save_chat_message(user["user_id"], "assistant", response_text, timestamp)

            except Exception as e:
                logger.error("Chat error: %s", e)
                st.error("Failed to get a response. Please try again.")

    # ── TAB 4: Meal History ───────────────────────────────────────────────────
    with history_tab:
        st.subheader("📜 Your Meal History")

        try:
            meals = meal_repo.get_meal_history(user["user_id"], limit=10)

            if not meals:
                st.info("No meals logged yet. Analyse a meal to see it here!")
            else:
                # ── Recent meals table ────────────────────────────────────────
                for meal in meals:
                    with st.expander(
                        f"🍽️ {meal.get('meal_consumed') or 'Meal'} — "
                        f"{meal.get('calories', 'N/A')} kcal  |  {meal.get('timestamp','')[:10]}"
                    ):
                        col_img, col_info = st.columns([1, 2])
                        with col_img:
                            if meal.get("image_url"):
                                st.image(meal["image_url"], width=200)
                        with col_info:
                            st.markdown(f"**Date:** {meal.get('timestamp','')[:10]}")
                            st.markdown(f"**Meal:** {meal.get('meal_consumed', 'N/A')}")
                            st.markdown(f"**Calories:** {meal.get('calories', 'N/A')} kcal")

                # ── Calorie Trend Chart ───────────────────────────────────────
                st.markdown("---")
                st.subheader("📈 Calorie Trend (Last 7 Days)")
                trend = meal_repo.get_calorie_trend(user["user_id"], days=7)

                if trend:
                    # st.bar_chart expects a dict {label: value}
                    st.bar_chart(trend)
                    st.caption("Total calories consumed per day across all logged meals.")
                else:
                    st.info("Log at least one meal to see your calorie trend.")

        except Exception as e:
            logger.error("Meal history error: %s", e)
            st.error("Failed to load meal history. Please try again.")


# ══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.page == "login":
    login_page()
elif st.session_state.page == "signup":
    signup_page()
elif st.session_state.user_data["logged_in"]:
    main_app()
