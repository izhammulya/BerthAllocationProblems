import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import random
from pulp import LpProblem, LpVariable, LpMinimize, lpSum, LpStatus, value

# -----------------------------
# Optimization Model
# -----------------------------
def berth_allocation_optimization(vessels, berth_length):
    model = LpProblem("Berth_Allocation", LpMinimize)

    start = {v["name"]: LpVariable(f"start_{v['name']}", lowBound=0, upBound=berth_length) for v in vessels}
    delay = {v["name"]: LpVariable(f"delay_{v['name']}", lowBound=0) for v in vessels}

    # Objective: minimize total delay
    model += lpSum(delay[v["name"]] for v in vessels)

    for i, vi in enumerate(vessels):
        li = vi["length"]
        eta_i = int(vi["eta"].split(":")[0])  # hour-based ETA
        model += start[vi["name"]] + li <= berth_length, f"WithinBerth_{vi['name']}"
        model += delay[vi["name"]] >= start[vi["name"]] - eta_i * 10

        for j, vj in enumerate(vessels):
            if i >= j:
                continue
            lj = vj["length"]
            M = berth_length * 2
            y_ij = LpVariable(f"y_{vi['name']}_{vj['name']}", cat="Binary")
            model += start[vi["name"]] + li <= start[vj["name"]] + M * (1 - y_ij)
            model += start[vj["name"]] + lj <= start[vi["name"]] + M * y_ij

    model.solve()

    if LpStatus[model.status] != "Optimal":
        st.warning("⚠️ Optimization did not find an optimal solution.")
        return []

    allocations = []
    for v in vessels:
        allocations.append({
            "name": v["name"],
            "type": v["type"],
            "length": v["length"],
            "eta": v["eta"],
            "etd": v["etd"],
            "start": value(start[v["name"]]),
            "end": value(start[v["name"]]) + v["length"],
            "delay": value(delay[v["name"]])
        })
    return allocations


# -----------------------------
# Visualization
# -----------------------------
def plot_berth_allocation(allocations, berth_length):
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.set_xlim(0, berth_length)
    ax.set_ylim(0, 20)
    ax.set_title("Optimized Berth Allocation (PuLP)", fontsize=16)
    ax.set_xlabel("Berth Position (m)")
    ax.set_ylabel("Berth Line")

    ax.hlines(0, 0, berth_length, colors='black', linewidth=3)

    for idx, alloc in enumerate(allocations):
        start = alloc["start"]
        end = alloc["end"]
        y_pos = 5 + idx * 2.5
        ship_length = end - start

        rect = plt.Rectangle((start, y_pos - 0.5), ship_length, 1.0,
                             color=np.random.rand(3,), alpha=0.7)
        ax.add_patch(rect)

        mid_x = (start + end) / 2
        ax.text(mid_x, y_pos + 0.7, f"🚢 {alloc['name']} ({alloc['type']})", 
                ha='center', va='bottom', fontsize=9, weight='bold')
        ax.text(mid_x, y_pos - 1.0, f"ETA:{alloc['eta']} | Delay:{alloc['delay']:.1f}", 
                ha='center', va='top', fontsize=8, color='gray')

    st.pyplot(fig)


# -----------------------------
# Random Data Generator
# -----------------------------
def generate_random_vessels(num_vessels):
    vessel_types = ["Container", "Bulk", "Tanker", "RORO", "Passenger"]
    vessels = []
    for i in range(num_vessels):
        vtype = random.choice(vessel_types)
        length = random.randint(50, 250)
        eta_hour = random.randint(1, 24)
        etd_hour = eta_hour + random.randint(4, 12)
        vessels.append({
            "name": f"Vessel_{i+1}",
            "type": vtype,
            "length": length,
            "eta": f"{eta_hour}:00",
            "etd": f"{etd_hour}:00"
        })
    return vessels


# -----------------------------
# Streamlit UI
# -----------------------------
st.title("🚢 Berth Allocation Optimization with Random Data (PuLP)")

st.sidebar.header("Simulation Settings")
num_vessels = st.sidebar.slider("Number of Vessels", 3, 15, 6)
berth_length = st.sidebar.slider("Total Berth Length (m)", 200, 2000, 800, step=100)

st.write("Click the button below to generate random vessel data and run optimization:")

if st.button("🎲 Generate & Optimize"):
    vessels = generate_random_vessels(num_vessels)
    st.subheader("Generated Vessel Data")
    st.dataframe(vessels)

    allocations = berth_allocation_optimization(vessels, berth_length)
    if allocations:
        st.success("✅ Optimization completed successfully")
        st.subheader("Optimized Allocation Results")
        st.dataframe(allocations)
        plot_berth_allocation(allocations, berth_length)
    else:
        st.error("❌ No feasible allocation found. Try adjusting parameters.")

st.markdown("---")
st.caption("Developed for berth scheduling research | Random data + PuLP + Streamlit")



# import streamlit as st
# import pulp
# import pandas as pd
# import matplotlib.pyplot as plt
# import random

# st.set_page_config(page_title="Berth Allocation Problem", layout="wide")

# st.title("⚓ Berth Allocation Problem with Vessel Variations")
# st.markdown("Define vessels, berths, and run the optimization interactively.")

# # -----------------------------
# # Sidebar Inputs
# # -----------------------------
# st.sidebar.header("Simulation Parameters")

# n_vessels = st.sidebar.number_input("Number of Vessels", 1, 10, 4)
# n_berths = st.sidebar.number_input("Number of Berths", 1, 10, 3)

# st.sidebar.markdown("---")
# st.sidebar.header("Generate Random Example (optional)")
# randomize = st.sidebar.checkbox("Generate Random Data")

# # -----------------------------
# # Input Tables
# # -----------------------------
# if randomize:
#     vessel_data = pd.DataFrame({
#         "Vessel": [f"V{i+1}" for i in range(n_vessels)],
#         "ArrivalTime": [random.randint(0, 5) for _ in range(n_vessels)],
#         "HandlingTime": [random.randint(2, 5) for _ in range(n_vessels)],
#         "Type": random.choices(["Container", "Bulk", "Tanker"], k=n_vessels)
#     })
#     berth_data = pd.DataFrame({
#         "Berth": [f"B{i+1}" for i in range(n_berths)],
#         "OpenTime": [0 for _ in range(n_berths)],
#         "CloseTime": [15 for _ in range(n_berths)],
#         "AllowedTypes": [",".join(random.sample(["Container", "Bulk", "Tanker"], random.randint(2,3))) for _ in range(n_berths)],
#         "X": [i*10 for i in range(n_berths)],
#         "Y": [0 for _ in range(n_berths)]
#     })
# else:
#     st.subheader("🛳️ Vessel Data")
#     vessel_data = st.data_editor(pd.DataFrame({
#         "Vessel": [f"V{i+1}" for i in range(n_vessels)],
#         "ArrivalTime": [0]*n_vessels,
#         "HandlingTime": [0]*n_vessels,
#         "Type": ["Container"]*n_vessels
#     }), key="vessel_editor")

#     st.subheader("🏗️ Berth Data")
#     berth_data = st.data_editor(pd.DataFrame({
#         "Berth": [f"B{i+1}" for i in range(n_berths)],
#         "OpenTime": [0]*n_berths,
#         "CloseTime": [15]*n_berths,
#         "AllowedTypes": ["Container,Bulk,Tanker"]*n_berths,
#         "X": [i*10 for i in range(n_berths)],
#         "Y": [0]*n_berths
#     }), key="berth_editor")

# # -----------------------------
# # Solve Optimization
# # -----------------------------
# if st.button("🚀 Solve Berth Allocation"):
#     vessels = vessel_data["Vessel"].tolist()
#     berths = berth_data["Berth"].tolist()

#     arrival_time = dict(zip(vessel_data["Vessel"], vessel_data["ArrivalTime"]))
#     handling_time = dict(zip(vessel_data["Vessel"], vessel_data["HandlingTime"]))
#     vessel_type = dict(zip(vessel_data["Vessel"], vessel_data["Type"]))

#     berth_open = dict(zip(berth_data["Berth"], berth_data["OpenTime"]))
#     berth_close = dict(zip(berth_data["Berth"], berth_data["CloseTime"]))
#     berth_coord = dict(zip(berth_data["Berth"], zip(berth_data["X"], berth_data["Y"])))

#     compatible_berth = {
#         b: berth_data.loc[i, "AllowedTypes"].split(",") for i, b in enumerate(berths)
#     }

#     # Model
#     model = pulp.LpProblem("Berth_Allocation_Problem", pulp.LpMinimize)
#     x = pulp.LpVariable.dicts("Assign", [(v, b) for v in vessels for b in berths], cat='Binary')
#     start_time = pulp.LpVariable.dicts("StartTime", vessels, lowBound=0)

#     # Objective: minimize total departure time
#     model += pulp.lpSum([start_time[v] + handling_time[v] for v in vessels])

#     # Constraints
#     for v in vessels:
#         model += pulp.lpSum([x[(v, b)] for b in berths]) == 1

#     for v in vessels:
#         for b in berths:
#             if vessel_type[v] not in compatible_berth[b]:
#                 model += x[(v, b)] == 0

#     for v in vessels:
#         model += start_time[v] >= arrival_time[v]

#     M = 1e5
#     for b in berths:
#         for v1 in vessels:
#             for v2 in vessels:
#                 if v1 != v2:
#                     model += start_time[v1] + handling_time[v1] <= start_time[v2] + M * (1 - x[(v1, b)] + 1 - x[(v2, b)])
#                     model += start_time[v2] + handling_time[v2] <= start_time[v1] + M * (1 - x[(v1, b)] + 1 - x[(v2, b)])

#     for v in vessels:
#         for b in berths:
#             model += start_time[v] >= berth_open[b] - (1 - x[(v, b)]) * 1e6
#             model += start_time[v] + handling_time[v] <= berth_close[b] + (1 - x[(v, b)]) * 1e6

#     model.solve(pulp.PULP_CBC_CMD(msg=0))

#     # -----------------------------
#     # Output Results
#     # -----------------------------
#     st.success(f"Optimization completed! Status: {pulp.LpStatus[model.status]}")

#     results = []
#     for v in vessels:
#         for b in berths:
#             if pulp.value(x[(v, b)]) > 0.5:
#                 results.append({
#                     "Vessel": v,
#                     "Berth": b,
#                     "Start": pulp.value(start_time[v]),
#                     "Finish": pulp.value(start_time[v]) + handling_time[v],
#                     "Type": vessel_type[v]
#                 })

#     df_result = pd.DataFrame(results)
#     st.subheader("📊 Allocation Results")
#     st.dataframe(df_result)

#     # -----------------------------
#     # Cartesian Visualization
#     # -----------------------------
#     st.subheader("🧭 Berth Layout Simulation (Cartesian View)")

#     fig, ax = plt.subplots(figsize=(10, 4))

#     # Plot berths
#     for b, (x_coord, y_coord) in berth_coord.items():
#         ax.plot(x_coord, y_coord, "s", markersize=12, label=f"{b}")
#         ax.text(x_coord, y_coord - 0.5, b, ha='center', va='top', fontsize=9, color='blue')

#     colors = {"Container": "orange", "Bulk": "green", "Tanker": "red"}

#     # Plot vessels near their assigned berth
#     for _, row in df_result.iterrows():
#         bx, by = berth_coord[row["Berth"]]
#         ax.plot(bx, by + 1, "o", color=colors[row["Type"]])
#         ax.text(bx, by + 1.2, f"{row['Vessel']} ({row['Start']:.1f}-{row['Finish']:.1f})",
#                 ha='center', fontsize=8, color=colors[row["Type"]])

#     ax.set_xlabel("X (Berth position)")
#     ax.set_ylabel("Y (Dock line)")
#     ax.set_title("Vessel Assignments on Cartesian Coordinate System")
#     ax.grid(True)
#     st.pyplot(fig)


