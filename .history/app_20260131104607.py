import streamlit as st
import pandas as pd
import json
import calendar
from datetime import datetime, date
from pathlib import Path

DATA_FILE = "data.json"


def load_data():
    if Path(DATA_FILE).exists():
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


st.set_page_config(page_title="Diet Tracker", layout="wide")
st.title("Diet & Weight Tracker")

data = load_data()

# --- Calendar for current month ---
today = date.today()
year, month = today.year, today.month
month_name = calendar.month_name[month]

st.subheader(f"{month_name} {year}")

cal = calendar.Calendar(firstweekday=6)  # Sunday start
weeks = cal.monthdayscalendar(year, month)

# Render calendar as a grid of buttons
selected_date = st.session_state.get("selected_date", today.isoformat())

cols = st.columns(7)
for i, day_name in enumerate(["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]):
    cols[i].markdown(f"**{day_name}**")

for week in weeks:
    cols = st.columns(7)
    for i, day in enumerate(week):
        if day == 0:
            cols[i].write("")
        else:
            d = date(year, month, day).isoformat()
            has_data = d in data
            label = f"✅ {day}" if has_data else str(day)
            if cols[i].button(label, key=f"day_{day}", use_container_width=True):
                st.session_state["selected_date"] = d

selected_date = st.session_state.get("selected_date", today.isoformat())
entry = data.get(selected_date, {})

st.divider()
st.subheader(f"Entry for {selected_date}")

# --- 1. Carbs ---
carb_success = st.radio(
    "Kept carbs ≤ 20g?",
    ["Yes", "No"],
    index=0 if entry.get("carbs_ok", True) else 1,
    horizontal=True,
    key="carbs_radio",
)
if carb_success == "Yes":
    st.success("Success")
else:
    st.error("Fail")

# --- 2. Weight ---
weight = st.number_input(
    "Weight (lbs)",
    min_value=50.0,
    max_value=500.0,
    value=float(entry.get("weight", 200.0)),
    step=0.1,
    format="%.1f",
    key="weight_input",
)

# --- 3. Alcohol ---
had_drinks = st.radio(
    "Any alcoholic drinks today?",
    ["Yes", "No"],
    index=0 if entry.get("drinks", 0) > 0 else 1,
    horizontal=True,
    key="drinks_radio",
)
if had_drinks == "Yes":
    num_drinks = st.number_input(
        "# of drinks",
        min_value=1,
        max_value=50,
        value=max(1, int(entry.get("drinks", 1))),
        step=1,
        key="drinks_input",
    )
else:
    num_drinks = 0

# --- Save ---
if st.button("Save Entry", type="primary", use_container_width=True):
    data[selected_date] = {
        "carbs_ok": carb_success == "Yes",
        "weight": weight,
        "drinks": num_drinks,
    }
    save_data(data)
    st.success(f"Saved entry for {selected_date}!")
    st.rerun()

# --- Trend Charts ---
if data:
    st.divider()
    st.subheader("Trends")

    df = pd.DataFrame(
        [
            {
                "date": k,
                "weight": v["weight"],
                "drinks": v["drinks"],
                "carbs_ok": v["carbs_ok"],
            }
            for k, v in sorted(data.items())
        ]
    )
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Weight (lbs)**")
        import altair as alt
        chart = alt.Chart(df.reset_index()).mark_line(point=True).encode(
            x="date:T",
            y=alt.Y("weight:Q", scale=alt.Scale(domainMin=160)),
        )
        st.altair_chart(chart, use_container_width=True)

    with col2:
        st.markdown("**Alcoholic Drinks**")
        st.bar_chart(df["drinks"])

    with col3:
        st.markdown("**Carbs ≤ 20g Streak**")
        carb_data = df["carbs_ok"].astype(int)
        st.bar_chart(carb_data)
