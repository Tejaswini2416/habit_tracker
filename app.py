import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date, timedelta

# ===============================
# PAGE CONFIG (Mobile-first)
# ===============================
st.set_page_config(
    page_title="Habit Tracker",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ===============================
# THEME + TILE STYLES
# ===============================
st.markdown("""
<style>
body { background:#2b2b2b; color:white; }

.yellow-bar {
    background:#f5c518;
    padding:10px;
    font-size:20px;
    font-weight:bold;
    color:black;
    text-align:center;
}

.card {
    background:#3a3a3a;
    padding:12px;
    border-radius:10px;
    text-align:center;
}

.tile {
    width:20px;
    height:20px;
    border-radius:4px;
    border:2px solid #555;
    margin:auto;
}

.tile-empty { background:#2b2b2b; }
.tile-done  { background:#f5c518; border-color:#f5c518; }
.tile-miss  { background:#7c3aed; border-color:#7c3aed; }

.center { display:flex; justify-content:center; }

@media (max-width: 768px) {
    .tile { width:18px; height:18px; }
}
</style>
""", unsafe_allow_html=True)

# ===============================
# HEADER
# ===============================
st.markdown('<div class="yellow-bar">🌱 Habit Tracker</div>', unsafe_allow_html=True)

# ===============================
# DATABASE (SQLite3 – stable)
# ===============================
conn = sqlite3.connect("habits.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS habits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS logs (
    habit_id INTEGER,
    log_date TEXT,
    status INTEGER,
    UNIQUE(habit_id, log_date)
)
""")
conn.commit()

# ===============================
# SIDEBAR NAVIGATION (KEY FIXED)
# ===============================
menu = st.sidebar.radio(
    "Menu",
    ["Dashboard", "Add Habit", "Manage Habits"],
    key="sidebar_menu"
)

# ===============================
# ADD HABIT
# ===============================
if menu == "Add Habit":
    st.subheader("➕ Add Habit")

    habit = st.text_input("Habit name", key="add_habit_input")

    if st.button("Add Habit", key="add_habit_btn"):
        if habit.strip():
            cursor.execute(
                "INSERT OR IGNORE INTO habits (name) VALUES (?)",
                (habit.strip(),)
            )
            conn.commit()
            st.success("Habit added!")
        else:
            st.warning("Habit name cannot be empty")

# ===============================
# MANAGE HABITS (EDIT / DELETE)
# ===============================
if menu == "Manage Habits":
    st.subheader("✏️ Edit / 🗑 Delete Habits")

    habits = cursor.execute("SELECT id, name FROM habits").fetchall()
    if not habits:
        st.info("No habits available")
        st.stop()

    habit_map = {name: hid for hid, name in habits}
    selected = st.selectbox(
        "Select habit",
        habit_map.keys(),
        key="manage_select"
    )
    hid = habit_map[selected]

    new_name = st.text_input(
        "Edit habit name",
        value=selected,
        key="edit_name_input"
    )

    col1, col2 = st.columns(2)
    if col1.button("Update", key="update_habit_btn"):
        if new_name.strip():
            cursor.execute(
                "UPDATE habits SET name=? WHERE id=?",
                (new_name.strip(), hid)
            )
            conn.commit()
            st.success("Habit updated")
            st.rerun()

    if col2.button("Delete", key="delete_habit_btn"):
        cursor.execute("DELETE FROM logs WHERE habit_id=?", (hid,))
        cursor.execute("DELETE FROM habits WHERE id=?", (hid,))
        conn.commit()
        st.warning("Habit deleted")
        st.rerun()

# ===============================
# DASHBOARD (DEFAULT)
# ===============================
if menu == "Dashboard":

    # ---------- WEEK NAVIGATION ----------
    if "week_offset" not in st.session_state:
        st.session_state.week_offset = 0

    nav_l, nav_c, nav_r = st.columns([1, 4, 1])

    if nav_l.button("⬅️", key="week_prev"):
        st.session_state.week_offset -= 1
        st.rerun()

    if nav_r.button("➡️", key="week_next"):
        st.session_state.week_offset += 1
        st.rerun()

    base_day = date.today() + timedelta(weeks=st.session_state.week_offset)
    start_week = base_day - timedelta(days=base_day.weekday())
    dates = [start_week + timedelta(days=i) for i in range(7)]

    nav_c.markdown(
        f"### {dates[0].strftime('%d %b')} – {dates[-1].strftime('%d %b')}"
    )

    # ---------- LOAD HABITS ----------
    habits = cursor.execute("SELECT id, name FROM habits").fetchall()
    if not habits:
        st.info("Add habits to start tracking 👈")
        st.stop()

    # ---------- PERFORMANCE CARDS ----------
    stats = cursor.execute("SELECT status FROM logs").fetchall()
    total = len(stats)
    done = sum(1 for s in stats if s[0] == 1)
    percent = round((done / total) * 100, 2) if total else 0

    c1, c2, c3 = st.columns(3)
    c1.markdown('<div class="card">Today<br><b>-</b></div>', unsafe_allow_html=True)
    c2.markdown('<div class="card">This Week<br><b>-</b></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="card">Overall<br><b>{percent}%</b></div>', unsafe_allow_html=True)

    # ---------- HABIT GRID ----------
    st.markdown("### Habit Calendar")

    header = st.columns([2] + [1]*7)
    header[0].markdown("**Habit**")
    for i, d in enumerate(dates):
        header[i+1].markdown(d.strftime("%a<br>%d"), unsafe_allow_html=True)

    for hid, name in habits:
        row = st.columns([2] + [1]*7)
        row[0].write(name)

        for i, d in enumerate(dates):
            cursor.execute("""
                SELECT status FROM logs
                WHERE habit_id=? AND log_date=?
            """, (hid, str(d)))
            res = cursor.fetchone()
            status = res[0] if res else 0

            css = (
                "tile-empty" if status == 0
                else "tile-done" if status == 1
                else "tile-miss"
            )

            clicked = row[i+1].button(
                " ",
                key=f"tile_{hid}_{d}"
            )

            row[i+1].markdown(
                f"<div class='center'><div class='tile {css}'></div></div>",
                unsafe_allow_html=True
            )

            if clicked:
                new_status = 1 if status == 0 else 2 if status == 1 else 0

                if new_status == 0:
                    cursor.execute(
                        "DELETE FROM logs WHERE habit_id=? AND log_date=?",
                        (hid, str(d))
                    )
                else:
                    cursor.execute("""
                        INSERT OR REPLACE INTO logs (habit_id, log_date, status)
                        VALUES (?, ?, ?)
                    """, (hid, str(d), new_status))
                conn.commit()
                st.rerun()

    # ---------- WEEKLY CHART (FIXED – NO DEPRECATION) ----------
    st.markdown("### Weekly Performance")

    df = pd.DataFrame(
        cursor.execute("SELECT log_date, status FROM logs").fetchall(),
        columns=["date", "status"]
    )

    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])

        weekly = (
            df[df["status"] == 1]
            .groupby(df["date"].dt.isocalendar().week)["status"]
            .count()
        )

        fig, ax = plt.subplots()
        ax.bar(weekly.index.astype(str), weekly.values, color="#f5c518")
        ax.set_ylabel("Completed")
        ax.set_xlabel("Week")
        st.pyplot(fig)

# ===============================
# FOOTER
# ===============================
st.markdown("---")
st.caption("📱 Mobile-friendly • Streamlit + SQLite3 • Habit Tracker")
