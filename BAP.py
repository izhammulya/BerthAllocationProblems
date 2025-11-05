# import streamlit as st
# import matplotlib.pyplot as plt
# import numpy as np
# import random
# from pulp import LpProblem, LpVariable, LpMinimize, lpSum, LpStatus, value

# # -----------------------------
# # Optimization Model
# # -----------------------------
# def berth_allocation_optimization(vessels, berth_length):
#     model = LpProblem("Berth_Allocation", LpMinimize)

#     start = {v["name"]: LpVariable(f"start_{v['name']}", lowBound=0, upBound=berth_length) for v in vessels}
#     delay = {v["name"]: LpVariable(f"delay_{v['name']}", lowBound=0) for v in vessels}

#     # Objective: minimize total delay
#     model += lpSum(delay[v["name"]] for v in vessels)

#     for i, vi in enumerate(vessels):
#         li = vi["length"]
#         eta_i = int(vi["eta"].split(":")[0])  # hour-based ETA
#         model += start[vi["name"]] + li <= berth_length, f"WithinBerth_{vi['name']}"
#         model += delay[vi["name"]] >= start[vi["name"]] - eta_i * 10

#         for j, vj in enumerate(vessels):
#             if i >= j:
#                 continue
#             lj = vj["length"]
#             M = berth_length * 2
#             y_ij = LpVariable(f"y_{vi['name']}_{vj['name']}", cat="Binary")
#             model += start[vi["name"]] + li <= start[vj["name"]] + M * (1 - y_ij)
#             model += start[vj["name"]] + lj <= start[vi["name"]] + M * y_ij

#     model.solve()

#     if LpStatus[model.status] != "Optimal":
#         st.warning("⚠️ Optimization did not find an optimal solution.")
#         return []

#     allocations = []
#     for v in vessels:
#         allocations.append({
#             "name": v["name"],
#             "type": v["type"],
#             "length": v["length"],
#             "eta": v["eta"],
#             "etd": v["etd"],
#             "start": value(start[v["name"]]),
#             "end": value(start[v["name"]]) + v["length"],
#             "delay": value(delay[v["name"]])
#         })
#     return allocations


# # -----------------------------
# # Visualization
# # -----------------------------
# def plot_berth_allocation(allocations, berth_length):
#     fig, ax = plt.subplots(figsize=(12, 6))
#     ax.set_xlim(0, berth_length)
#     ax.set_ylim(0, 20)
#     ax.set_title("Optimized Berth Allocation (PuLP)", fontsize=16)
#     ax.set_xlabel("Berth Position (m)")
#     ax.set_ylabel("Berth Line")

#     ax.hlines(0, 0, berth_length, colors='black', linewidth=3)

#     for idx, alloc in enumerate(allocations):
#         start = alloc["start"]
#         end = alloc["end"]
#         y_pos = 5 + idx * 2.5
#         ship_length = end - start

#         rect = plt.Rectangle((start, y_pos - 0.5), ship_length, 1.0,
#                              color=np.random.rand(3,), alpha=0.7)
#         ax.add_patch(rect)

#         mid_x = (start + end) / 2
#         ax.text(mid_x, y_pos + 0.7, f"🚢 {alloc['name']} ({alloc['type']})", 
#                 ha='center', va='bottom', fontsize=9, weight='bold')
#         ax.text(mid_x, y_pos - 1.0, f"ETA:{alloc['eta']} | Delay:{alloc['delay']:.1f}", 
#                 ha='center', va='top', fontsize=8, color='gray')

#     st.pyplot(fig)


# # -----------------------------
# # Random Data Generator
# # -----------------------------
# def generate_random_vessels(num_vessels):
#     vessel_types = ["Container", "Bulk", "Tanker", "RORO", "Passenger"]
#     vessels = []
#     for i in range(num_vessels):
#         vtype = random.choice(vessel_types)
#         length = random.randint(50, 250)
#         eta_hour = random.randint(1, 24)
#         etd_hour = eta_hour + random.randint(4, 12)
#         vessels.append({
#             "name": f"Vessel_{i+1}",
#             "type": vtype,
#             "length": length,
#             "eta": f"{eta_hour}:00",
#             "etd": f"{etd_hour}:00"
#         })
#     return vessels


# # -----------------------------
# # Streamlit UI
# # -----------------------------
# st.title("🚢 Berth Allocation Optimization with Random Data (PuLP)")

# st.sidebar.header("Simulation Settings")
# num_vessels = st.sidebar.slider("Number of Vessels", 3, 15, 6)
# berth_length = st.sidebar.slider("Total Berth Length (m)", 200, 2000, 800, step=100)

# st.write("Click the button below to generate random vessel data and run optimization:")

# if st.button("🎲 Generate & Optimize"):
#     vessels = generate_random_vessels(num_vessels)
#     st.subheader("Generated Vessel Data")
#     st.dataframe(vessels)

#     allocations = berth_allocation_optimization(vessels, berth_length)
#     if allocations:
#         st.success("✅ Optimization completed successfully")
#         st.subheader("Optimized Allocation Results")
#         st.dataframe(allocations)
#         plot_berth_allocation(allocations, berth_length)
#     else:
#         st.error("❌ No feasible allocation found. Try adjusting parameters.")

# st.markdown("---")
# st.caption("Developed for berth scheduling research | Random data + PuLP + Streamlit")




import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import random
from pulp import LpProblem, LpVariable, LpMinimize, lpSum, LpStatus, value
import datetime

# -----------------------------
# Optimization Model - FIXED
# -----------------------------
def berth_allocation_optimization(vessels, berth_length):
    model = LpProblem("Berth_Allocation", LpMinimize)

    start = {v["name"]: LpVariable(f"start_{v['name']}", lowBound=0, upBound=berth_length) for v in vessels}
    delay = {v["name"]: LpVariable(f"delay_{v['name']}", lowBound=0) for v in vessels}

    # Objective: minimize total delay (in hours)
    model += lpSum(delay[v["name"]] for v in vessels)

    for i, vi in enumerate(vessels):
        li = vi["length"]
        eta_i = vi["eta_hour"]  # Use the pre-calculated ETA hour
        
        # Constraint: vessel must fit within berth
        model += start[vi["name"]] + li <= berth_length, f"WithinBerth_{vi['name']}"
        
        # FIXED: Delay constraint - convert position to time
        # Assuming vessels move at constant speed to their assigned positions
        # Delay = actual start time - ETA (in hours)
        model += delay[vi["name"]] >= (start[vi["name"]] / 10) - eta_i

        # Non-overlapping constraints
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
        start_pos = value(start[v["name"]])
        delay_hours = value(delay[v["name"]])
        allocations.append({
            "name": v["name"],
            "type": v["type"],
            "length": v["length"],
            "eta": v["eta"],
            "etd": v["etd"],
            "eta_hour": v["eta_hour"],
            "start": start_pos,
            "end": start_pos + v["length"],
            "delay": delay_hours  # Now in hours
        })
    return allocations

# -----------------------------
# Visualization - UPDATED
# -----------------------------
def plot_berth_allocation(allocations, berth_length):
    fig, ax = plt.subplots(figsize=(14, 8))
    
    ax.set_xlim(0, berth_length)
    ax.set_ylim(0, len(allocations) * 3 + 5)
    ax.set_title("Optimized Berth Allocation (Delay in Hours)", fontsize=16)
    ax.set_xlabel("Berth Position (m)")
    ax.set_ylabel("Vessel Position")
    
    # Draw the berth line
    ax.hlines(1, 0, berth_length, colors='blue', linewidth=4, label='Berth Line')
    
    # Draw coordinate grid
    ax.grid(True, alpha=0.3)
    
    # Define colors for different vessel types
    vessel_colors = {
        "Container": "red",
        "Bulk": "green", 
        "Tanker": "orange",
        "RORO": "purple",
        "Passenger": "brown"
    }
    
    # Plot each vessel
    for idx, alloc in enumerate(allocations):
        start = alloc["start"]
        end = alloc["end"]
        y_pos = 5 + idx * 3
        ship_length = end - start
        
        color = vessel_colors.get(alloc["type"], "blue")
        
        # Draw vessel as rectangle
        rect = plt.Rectangle((start, y_pos - 0.5), ship_length, 1.0,
                             color=color, alpha=0.7, edgecolor='black', linewidth=1)
        ax.add_patch(rect)
        
        # Add vessel information with delay in hours
        mid_x = (start + end) / 2
        ax.text(mid_x, y_pos + 0.7, f"🚢 {alloc['name']} ({alloc['type']})", 
                ha='center', va='bottom', fontsize=9, weight='bold')
        
        # FIXED: Show delay in hours with proper units
        delay_text = f"Delay: {alloc['delay']:.1f} hours" if alloc['delay'] > 0 else "On time"
        delay_color = 'red' if alloc['delay'] > 0 else 'green'
        
        ax.text(mid_x, y_pos - 1.0, 
                f"Pos:{start:.1f}-{end:.1f}m | ETA:{alloc['eta']} | {delay_text}", 
                ha='center', va='top', fontsize=8, color=delay_color)
        
        # Draw connection line from vessel to berth
        ax.plot([mid_x, mid_x], [y_pos - 0.5, 1], 'k--', alpha=0.5, linewidth=0.8)
    
    ax.text(berth_length/2, 0.5, f"Total Berth Length: {berth_length}m", 
            ha='center', va='bottom', fontsize=10, weight='bold', color='blue')
    
    # Add legend
    legend_elements = []
    for vtype, color in vessel_colors.items():
        legend_elements.append(plt.Rectangle((0, 0), 1, 1, fc=color, alpha=0.7, label=vtype))
    ax.legend(handles=legend_elements, loc='upper right', title="Vessel Types")
    
    st.pyplot(fig)

# -----------------------------
# Updated Random Data Generator
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
            "eta": f"{eta_hour:02d}:00",
            "etd": f"{etd_hour:02d}:00",
            "eta_hour": eta_hour  # Store ETA as numeric for calculations
        })
    return vessels

# -----------------------------
# Streamlit UI
# -----------------------------
st.title("🚢 Berth Allocation Optimization (Delay in Hours)")

st.sidebar.header("Simulation Settings")
num_vessels = st.sidebar.slider("Number of Vessels", 3, 15, 6)
berth_length = st.sidebar.slider("Total Berth Length (m)", 200, 2000, 800, step=100)

# Explanation
st.info("""
**📝 Explanation of Delay Calculation:**
- **Delay is now in hours** (not distance)
- Assumption: Vessels move at constant speed to assigned positions
- Conversion: Position (meters) ÷ 10 = Time (hours)
- Negative delays are clamped to 0 (vessels cannot start before ETA)
""")

if st.button("🎲 Generate & Optimize"):
    vessels = generate_random_vessels(num_vessels)
    st.subheader("Generated Vessel Data")
    st.dataframe(vessels)

    allocations = berth_allocation_optimization(vessels, berth_length)
    if allocations:
        st.success("✅ Optimization completed successfully")
        st.subheader("Optimized Allocation Results")
        
        # Display results with proper delay units
        display_df = []
        for alloc in allocations:
            display_df.append({
                "Vessel": alloc["name"],
                "Type": alloc["type"],
                "Length (m)": alloc["length"],
                "ETA": alloc["eta"],
                "Start Position (m)": f"{alloc['start']:.1f}",
                "End Position (m)": f"{alloc['end']:.1f}",
                "Delay (hours)": f"{alloc['delay']:.2f}"
            })
        st.dataframe(display_df)
        
        plot_berth_allocation(allocations, berth_length)
        
        # Show summary statistics
        st.subheader("📈 Allocation Summary")
        col1, col2, col3 = st.columns(3)
        with col1:
            total_used = sum(alloc["length"] for alloc in allocations)
            utilization = (total_used / berth_length) * 100
            st.metric("Berth Utilization", f"{utilization:.1f}%")
        with col2:
            total_delay = sum(alloc["delay"] for alloc in allocations)
            st.metric("Total Delay", f"{total_delay:.1f} hours")
        with col3:
            avg_delay = total_delay / len(allocations) if allocations else 0
            st.metric("Average Delay", f"{avg_delay:.1f} hours")
            
    else:
        st.error("❌ No feasible allocation found. Try adjusting parameters.")

st.markdown("---")
st.caption("Delay is now calculated in hours instead of distance units")
