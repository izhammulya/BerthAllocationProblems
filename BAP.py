import streamlit as st
import pulp
import pandas as pd
import matplotlib.pyplot as plt
import random

st.set_page_config(page_title="Berth Allocation Problem", layout="wide")

st.title("⚓ Berth Allocation Problem with Vessel Variations")
st.markdown("Define vessels, berths, and run the optimization interactively.")

# -----------------------------
# Sidebar Inputs
# -----------------------------
st.sidebar.header("Simulation Parameters")

n_vessels = st.sidebar.number_input("Number of Vessels", 1, 10, 4)
n_berths = st.sidebar.number_input("Number of Berths", 1, 10, 3)

st.sidebar.markdown("---")
st.sidebar.header("Generate Random Example (optional)")
randomize = st.sidebar.checkbox("Generate Random Data")

# -----------------------------
# Input Tables
# -----------------------------
if randomize:
    vessel_data = pd.DataFrame({
        "Vessel": [f"V{i+1}" for i in range(n_vessels)],
        "ArrivalTime": [random.randint(0, 5) for _ in range(n_vessels)],
        "HandlingTime": [random.randint(2, 5) for _ in range(n_vessels)],
        "Type": random.choices(["Container", "Bulk", "Tanker"], k=n_vessels)
    })
    berth_data = pd.DataFrame({
        "Berth": [f"B{i+1}" for i in range(n_berths)],
        "OpenTime": [0 for _ in range(n_berths)],
        "CloseTime": [15 for _ in range(n_berths)],
        "AllowedTypes": [",".join(random.sample(["Container", "Bulk", "Tanker"], random.randint(2,3))) for _ in range(n_berths)],
        "X": [i*10 for i in range(n_berths)],
        "Y": [0 for _ in range(n_berths)]
    })
else:
    st.subheader("🛳️ Vessel Data")
    vessel_data = st.data_editor(pd.DataFrame({
        "Vessel": [f"V{i+1}" for i in range(n_vessels)],
        "ArrivalTime": [0]*n_vessels,
        "HandlingTime": [0]*n_vessels,
        "Type": ["Container"]*n_vessels
    }), key="vessel_editor")

    st.subheader("🏗️ Berth Data")
    berth_data = st.data_editor(pd.DataFrame({
        "Berth": [f"B{i+1}" for i in range(n_berths)],
        "OpenTime": [0]*n_berths,
        "CloseTime": [15]*n_berths,
        "AllowedTypes": ["Container,Bulk,Tanker"]*n_berths,
        "X": [i*10 for i in range(n_berths)],
        "Y": [0]*n_berths
    }), key="berth_editor")

# -----------------------------
# Solve Optimization
# -----------------------------
if st.button("🚀 Solve Berth Allocation"):
    vessels = vessel_data["Vessel"].tolist()
    berths = berth_data["Berth"].tolist()

    arrival_time = dict(zip(vessel_data["Vessel"], vessel_data["ArrivalTime"]))
    handling_time = dict(zip(vessel_data["Vessel"], vessel_data["HandlingTime"]))
    vessel_type = dict(zip(vessel_data["Vessel"], vessel_data["Type"]))

    berth_open = dict(zip(berth_data["Berth"], berth_data["OpenTime"]))
    berth_close = dict(zip(berth_data["Berth"], berth_data["CloseTime"]))
    berth_coord = dict(zip(berth_data["Berth"], zip(berth_data["X"], berth_data["Y"])))

    compatible_berth = {
        b: berth_data.loc[i, "AllowedTypes"].split(",") for i, b in enumerate(berths)
    }

    # Model
    model = pulp.LpProblem("Berth_Allocation_Problem", pulp.LpMinimize)
    x = pulp.LpVariable.dicts("Assign", [(v, b) for v in vessels for b in berths], cat='Binary')
    start_time = pulp.LpVariable.dicts("StartTime", vessels, lowBound=0)

    # Objective: minimize total departure time
    model += pulp.lpSum([start_time[v] + handling_time[v] for v in vessels])

    # Constraints
    for v in vessels:
        model += pulp.lpSum([x[(v, b)] for b in berths]) == 1

    for v in vessels:
        for b in berths:
            if vessel_type[v] not in compatible_berth[b]:
                model += x[(v, b)] == 0

    for v in vessels:
        model += start_time[v] >= arrival_time[v]

    M = 1e5
    for b in berths:
        for v1 in vessels:
            for v2 in vessels:
                if v1 != v2:
                    model += start_time[v1] + handling_time[v1] <= start_time[v2] + M * (1 - x[(v1, b)] + 1 - x[(v2, b)])
                    model += start_time[v2] + handling_time[v2] <= start_time[v1] + M * (1 - x[(v1, b)] + 1 - x[(v2, b)])

    for v in vessels:
        for b in berths:
            model += start_time[v] >= berth_open[b] - (1 - x[(v, b)]) * 1e6
            model += start_time[v] + handling_time[v] <= berth_close[b] + (1 - x[(v, b)]) * 1e6

    model.solve(pulp.PULP_CBC_CMD(msg=0))

    # -----------------------------
    # Output Results
    # -----------------------------
    st.success(f"Optimization completed! Status: {pulp.LpStatus[model.status]}")

    results = []
    for v in vessels:
        for b in berths:
            if pulp.value(x[(v, b)]) > 0.5:
                results.append({
                    "Vessel": v,
                    "Berth": b,
                    "Start": pulp.value(start_time[v]),
                    "Finish": pulp.value(start_time[v]) + handling_time[v],
                    "Type": vessel_type[v]
                })

    df_result = pd.DataFrame(results)
    st.subheader("📊 Allocation Results")
    st.dataframe(df_result)

    # -----------------------------
    # Cartesian Visualization
    # -----------------------------
    st.subheader("🧭 Berth Layout Simulation (Cartesian View)")

    fig, ax = plt.subplots(figsize=(10, 4))

    # Plot berths
    for b, (x_coord, y_coord) in berth_coord.items():
        ax.plot(x_coord, y_coord, "s", markersize=12, label=f"{b}")
        ax.text(x_coord, y_coord - 0.5, b, ha='center', va='top', fontsize=9, color='blue')

    colors = {"Container": "orange", "Bulk": "green", "Tanker": "red"}

    # Plot vessels near their assigned berth
    for _, row in df_result.iterrows():
        bx, by = berth_coord[row["Berth"]]
        ax.plot(bx, by + 1, "o", color=colors[row["Type"]])
        ax.text(bx, by + 1.2, f"{row['Vessel']} ({row['Start']:.1f}-{row['Finish']:.1f})",
                ha='center', fontsize=8, color=colors[row["Type"]])

    ax.set_xlabel("X (Berth position)")
    ax.set_ylabel("Y (Dock line)")
    ax.set_title("Vessel Assignments on Cartesian Coordinate System")
    ax.grid(True)
    st.pyplot(fig)
