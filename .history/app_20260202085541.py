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

# --- Calendar month navigation ---
today = date.today()
if "cal_year" not in st.session_state:
    st.session_state["cal_year"] = today.year
if "cal_month" not in st.session_state:
    st.session_state["cal_month"] = today.month

nav_left, nav_center, nav_right = st.columns([1, 3, 1])
with nav_left:
    if st.button("◀ Prev"):
        if st.session_state["cal_month"] == 1:
            st.session_state["cal_month"] = 12
            st.session_state["cal_year"] -= 1
        else:
            st.session_state["cal_month"] -= 1
        st.rerun()
with nav_right:
    if st.button("Next ▶"):
        if st.session_state["cal_month"] == 12:
            st.session_state["cal_month"] = 1
            st.session_state["cal_year"] += 1
        else:
            st.session_state["cal_month"] += 1
        st.rerun()

year = st.session_state["cal_year"]
month = st.session_state["cal_month"]
month_name = calendar.month_name[month]

with nav_center:
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

# --- Export / Import ---
st.divider()
exp_col, imp_col, reset_col = st.columns(3)

with exp_col:
    if data:
        most_recent = max(data.keys())
        st.download_button(
            "Download Data (JSON)",
            data=json.dumps(data, indent=2),
            file_name=f"diet_tracker_thru_{most_recent}.json",
            mime="application/json",
        )

with imp_col:
    uploaded = st.file_uploader("Upload Data (JSON)", type=["json"], key="json_uploader")
    if uploaded is not None and not st.session_state.get("imported"):
        try:
            imported = json.load(uploaded)
            data.update(imported)
            save_data(data)
            st.session_state["imported"] = True
            st.success(f"Imported {len(imported)} entries!")
            st.rerun()
        except Exception as e:
            st.error(f"Invalid JSON file: {e}")
    if uploaded is None:
        st.session_state["imported"] = False

with reset_col:
    if data:
        if st.button("Reset All Data", type="secondary"):
            st.session_state["confirm_reset"] = True
        if st.session_state.get("confirm_reset"):
            st.warning("This will delete all entries. Are you sure?")
            if st.button("Yes, reset", type="primary"):
                save_data({})
                st.session_state["confirm_reset"] = False
                st.rerun()
            if st.button("Cancel"):
                st.session_state["confirm_reset"] = False
                st.rerun()

# --- Trend Charts ---
if data:
    st.divider()
    st.subheader("Trends")
    chart_range = st.radio("Show:", ["Current Month", "All Time"], horizontal=True, key="chart_range")

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
    if chart_range == "Current Month":
        df = df[(df["date"].dt.year == year) & (df["date"].dt.month == month)]
    df = df.set_index("date")

    if df.empty:
        st.info("No data for this period.")
    else:

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**Weight (lbs)**")
            target_weight = st.number_input("Target Weight (lbs)", min_value=50.0, max_value=500.0, value=180.0, step=0.5, format="%.1f", key="target_weight")
            import altair as alt
            weight_df = df.reset_index()
            line = alt.Chart(weight_df).mark_line(point=True).encode(
                x="date:T",
                y=alt.Y("weight:Q", scale=alt.Scale(domainMin=160)),
            )
            target_rule = alt.Chart(pd.DataFrame({"weight": [target_weight]})).mark_rule(color="blue", strokeDash=[4, 4]).encode(
                y="weight:Q",
            )
            mid_date = weight_df["date"].iloc[len(weight_df) // 2]
            target_label = alt.Chart(pd.DataFrame({"date": [mid_date], "weight": [target_weight], "label": ["Target Weight"]})).mark_text(
                align="center", dy=-10, color="blue", fontWeight="bold"
            ).encode(
                x="date:T",
                y="weight:Q",
                text="label:N",
            )
            st.altair_chart(line + target_rule + target_label, use_container_width=True)

        with col2:
            st.markdown("**Alcoholic Drinks**")
            drinks_df = df.reset_index()
            drinks_df["drink_level"] = drinks_df["drinks"].apply(
                lambda d: "green" if d == 0 else ("orange" if d <= 2 else "red")
            )
            drinks_chart = alt.Chart(drinks_df).mark_point(size=80, filled=True).encode(
                x="date:T",
                y=alt.Y("drinks:Q", title="drinks", scale=alt.Scale(domain=[0, 5])),
                color=alt.Color("drink_level:N", scale=alt.Scale(
                    domain=["green", "orange", "red"],
                    range=["green", "orange", "red"],
                ), legend=None),
            )
            st.altair_chart(drinks_chart, use_container_width=True)

        with col3:
            st.markdown("**Carbs ≤ 20g**")
            carb_df = df.reset_index()[["date", "carbs_ok"]].copy()
            carb_df["y"] = 0.5
            carb_df["status"] = carb_df["carbs_ok"].map({True: "green", False: "red"})
            carb_chart = alt.Chart(carb_df).mark_point(size=80, filled=True).encode(
                x="date:T",
                y=alt.Y("y:Q", scale=alt.Scale(domain=[0, 1]), axis=None),
                color=alt.Color("status:N", scale=alt.Scale(
                    domain=["green", "red"],
                    range=["green", "red"],
                ), legend=None),
            )
            st.altair_chart(carb_chart, use_container_width=True)
