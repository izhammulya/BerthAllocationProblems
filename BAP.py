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
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Set up the coordinate system
    ax.set_xlim(0, berth_length)
    ax.set_ylim(0, len(allocations) * 3 + 5)
    ax.set_title("Optimized Berth Allocation - Cartesian Coordinate View", fontsize=16)
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
    
    # Plot each vessel as a rectangle in cartesian coordinates
    for idx, alloc in enumerate(allocations):
        start = alloc["start"]
        end = alloc["end"]
        y_pos = 5 + idx * 3  # Position vessels vertically with spacing
        ship_length = end - start
        
        # Get color based on vessel type
        color = vessel_colors.get(alloc["type"], "blue")
        
        # Draw vessel as rectangle
        rect = plt.Rectangle((start, y_pos - 0.5), ship_length, 1.0,
                             color=color, alpha=0.7, edgecolor='black', linewidth=1)
        ax.add_patch(rect)
        
        # Add vessel information
        mid_x = (start + end) / 2
        ax.text(mid_x, y_pos + 0.7, f"🚢 {alloc['name']} ({alloc['type']})", 
                ha='center', va='bottom', fontsize=9, weight='bold')
        ax.text(mid_x, y_pos - 1.0, 
                f"Pos:{start:.1f}-{end:.1f}m | ETA:{alloc['eta']} | Delay:{alloc['delay']:.1f}", 
                ha='center', va='top', fontsize=8, color='gray')
        
        # Draw connection line from vessel to berth
        ax.plot([mid_x, mid_x], [y_pos - 0.5, 1], 'k--', alpha=0.5, linewidth=0.8)
    
    # Add berth length markers
    ax.text(berth_length/2, 0.5, f"Total Berth Length: {berth_length}m", 
            ha='center', va='bottom', fontsize=10, weight='bold', color='blue')
    
    # Add legend for vessel types
    legend_elements = []
    for vtype, color in vessel_colors.items():
        legend_elements.append(plt.Rectangle((0, 0), 1, 1, fc=color, alpha=0.7, label=vtype))
    ax.legend(handles=legend_elements, loc='upper right', title="Vessel Types")
    
    st.pyplot(fig)

# -----------------------------
# Enhanced Visualization with Timeline View
# -----------------------------
def plot_timeline_view(allocations, berth_length):
    """Alternative view showing vessels along the berth with time dimension"""
    fig, ax = plt.subplots(figsize=(14, 6))
    
    ax.set_xlim(0, berth_length)
    ax.set_ylim(0, 10)
    ax.set_title("Berth Allocation - Spatial Distribution", fontsize=16)
    ax.set_xlabel("Berth Position (m)")
    ax.set_ylabel("")
    ax.set_yticks([])  # Remove y-axis ticks
    
    # Draw the berth as a horizontal line
    ax.hlines(5, 0, berth_length, colors='navy', linewidth=6, label='Berth')
    
    # Draw position markers along the berth
    for pos in range(0, berth_length + 1, 100):
        if pos <= berth_length:
            ax.vlines(pos, 4.8, 5.2, colors='gray', alpha=0.5, linewidth=0.5)
            if pos % 200 == 0:  # Label every 200m
                ax.text(pos, 4.5, f"{pos}m", ha='center', va='top', fontsize=8, color='gray')
    
    # Plot vessels along the berth line
    vessel_colors = {
        "Container": "red",
        "Bulk": "green", 
        "Tanker": "orange",
        "RORO": "purple",
        "Passenger": "brown"
    }
    
    for idx, alloc in enumerate(allocations):
        start = alloc["start"]
        end = alloc["end"]
        ship_length = end - start
        
        color = vessel_colors.get(alloc["type"], "blue")
        
        # Draw vessel above the berth line
        y_pos = 6
        rect = plt.Rectangle((start, y_pos), ship_length, 1.0,
                           color=color, alpha=0.8, edgecolor='black', linewidth=1)
        ax.add_patch(rect)
        
        # Add vessel label
        mid_x = (start + end) / 2
        ax.text(mid_x, y_pos + 1.3, f"{alloc['name']}\n({alloc['type']})", 
                ha='center', va='bottom', fontsize=8, weight='bold')
        ax.text(mid_x, y_pos - 0.3, f"Delay: {alloc['delay']:.1f}", 
                ha='center', va='top', fontsize=7, color='darkred')
    
    # Add berth capacity information
    ax.text(berth_length, 5.5, f"Berth Capacity: {berth_length}m", 
            ha='right', va='bottom', fontsize=10, weight='bold', color='navy',
            bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.7))
    
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
st.title("🚢 Berth Allocation Optimization with Cartesian Coordinates")

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
        
        # Show both visualization options
        st.subheader("📊 Cartesian Coordinate View")
        plot_berth_allocation(allocations, berth_length)
        
        st.subheader("📊 Berth Spatial Distribution")
        plot_timeline_view(allocations, berth_length)
        
        # Show summary statistics
        st.subheader("📈 Allocation Summary")
        col1, col2, col3 = st.columns(3)
        with col1:
            total_used = sum(alloc["length"] for alloc in allocations)
            utilization = (total_used / berth_length) * 100
            st.metric("Berth Utilization", f"{utilization:.1f}%")
        with col2:
            total_delay = sum(alloc["delay"] for alloc in allocations)
            st.metric("Total Delay", f"{total_delay:.1f}")
        with col3:
            avg_delay = total_delay / len(allocations)
            st.metric("Average Delay", f"{avg_delay:.1f}")
            
    else:
        st.error("❌ No feasible allocation found. Try adjusting parameters.")

st.markdown("---")
st.caption("Developed for berth scheduling research | Cartesian coordinate visualization with berth line")
