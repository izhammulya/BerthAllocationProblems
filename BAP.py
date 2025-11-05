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
# Optimization Model - FIXED
# -----------------------------
def berth_allocation_optimization(vessels, berth_length):
    try:
        model = LpProblem("Berth_Allocation", LpMinimize)

        # Decision variables
        start = {v["name"]: LpVariable(f"start_{v['name']}", lowBound=0, upBound=berth_length - v["length"]) for v in vessels}
        delay = {v["name"]: LpVariable(f"delay_{v['name']}", lowBound=0) for v in vessels}

        # Objective: minimize total delay (in hours)
        model += lpSum(delay[v["name"]] for v in vessels)

        # Constraints for each vessel
        for i, vi in enumerate(vessels):
            li = vi["length"]
            eta_i = vi["eta_hour"]
            
            # Constraint: vessel must fit within berth (already handled in lowBound)
            
            # FIXED: Delay constraint - convert position to time units
            # Assuming 50 meters = 1 hour for conversion
            conversion_factor = 50  # meters per hour
            model += delay[vi["name"]] >= (start[vi["name"]] / conversion_factor) - eta_i

        # Non-overlapping constraints
        for i, vi in enumerate(vessels):
            for j, vj in enumerate(vessels):
                if i < j:  # Only consider each pair once
                    li = vi["length"]
                    lj = vj["length"]
                    M = berth_length * 2
                    
                    # Binary variable for ordering
                    y_ij = LpVariable(f"y_{vi['name']}_{vj['name']}", cat="Binary")
                    
                    # Either vi is before vj OR vj is before vi
                    model += start[vi["name"]] + li <= start[vj["name"]] + M * (1 - y_ij)
                    model += start[vj["name"]] + lj <= start[vi["name"]] + M * y_ij

        # Solve the model
        model.solve()

        if LpStatus[model.status] != "Optimal":
            st.warning(f"⚠️ Optimization status: {LpStatus[model.status]}")
            return []

        # Extract results
        allocations = []
        for v in vessels:
            start_pos = value(start[v["name"]])
            delay_hours = max(0, value(delay[v["name"]]))  # Ensure non-negative
            allocations.append({
                "name": v["name"],
                "type": v["type"],
                "length": v["length"],
                "eta": v["eta"],
                "etd": v["etd"],
                "eta_hour": v["eta_hour"],
                "start": start_pos,
                "end": start_pos + v["length"],
                "delay": delay_hours
            })
        
        return allocations
    
    except Exception as e:
        st.error(f"Error in optimization: {str(e)}")
        return []

# -----------------------------
# Visualization
# -----------------------------
def plot_berth_allocation(allocations, berth_length):
    fig, ax = plt.subplots(figsize=(14, 8))
    
    ax.set_xlim(0, berth_length)
    ax.set_ylim(0, len(allocations) * 3 + 5)
    ax.set_title("Optimized Berth Allocation (Delay in Hours)", fontsize=16)
    ax.set_xlabel("Berth Position (meters)")
    ax.set_ylabel("Vessel Position")
    
    # Draw the berth line
    ax.hlines(1, 0, berth_length, colors='blue', linewidth=4, label='Berth Line')
    
    # Draw coordinate grid
    ax.grid(True, alpha=0.3)
    
    # Define colors for different vessel types
    vessel_colors = {
        "Container": "#FF6B6B",
        "Bulk": "#4ECDC4", 
        "Tanker": "#FFD166",
        "RORO": "#9D4EDD",
        "Passenger": "#06D6A0"
    }
    
    # Plot each vessel
    for idx, alloc in enumerate(allocations):
        start = alloc["start"]
        end = alloc["end"]
        y_pos = 5 + idx * 3
        ship_length = end - start
        
        color = vessel_colors.get(alloc["type"], "#118AB2")
        
        # Draw vessel as rectangle
        rect = plt.Rectangle((start, y_pos - 0.5), ship_length, 1.0,
                             color=color, alpha=0.8, edgecolor='black', linewidth=1.5)
        ax.add_patch(rect)
        
        # Add vessel information
        mid_x = (start + end) / 2
        
        # Vessel name and type
        ax.text(mid_x, y_pos + 0.8, f"{alloc['name']}\n({alloc['type']})", 
                ha='center', va='bottom', fontsize=9, weight='bold', style='italic')
        
        # Delay information
        delay_text = f"Delay: {alloc['delay']:.1f}h" if alloc['delay'] > 0.1 else "On time"
        delay_color = 'red' if alloc['delay'] > 0.1 else 'green'
        
        ax.text(mid_x, y_pos - 1.0, 
                f"Position: {start:.0f}-{end:.0f}m\nETA: {alloc['eta']} | {delay_text}", 
                ha='center', va='top', fontsize=8, color=delay_color, weight='bold')
        
        # Draw connection line from vessel to berth
        ax.plot([mid_x, mid_x], [y_pos - 0.5, 1.5], 'k--', alpha=0.4, linewidth=1)

    # Berth information
    ax.text(berth_length/2, 0.3, f"TOTAL BERTH LENGTH: {berth_length}m", 
            ha='center', va='bottom', fontsize=12, weight='bold', color='blue',
            bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.7))
    
    # Add legend
    legend_elements = []
    for vtype, color in vessel_colors.items():
        legend_elements.append(plt.Rectangle((0, 0), 1, 1, fc=color, alpha=0.8, label=vtype))
    ax.legend(handles=legend_elements, loc='upper right', title="Vessel Types")
    
    plt.tight_layout()
    st.pyplot(fig)

# -----------------------------
# Random Data Generator - FIXED
# -----------------------------
def generate_random_vessels(num_vessels):
    vessel_types = ["Container", "Bulk", "Tanker", "RORO", "Passenger"]
    vessels = []
    
    for i in range(num_vessels):
        vtype = random.choice(vessel_types)
        
        # Vessel length based on type
        length_ranges = {
            "Container": (100, 300),
            "Bulk": (150, 250),
            "Tanker": (200, 350),
            "RORO": (80, 180),
            "Passenger": (50, 150)
        }
        
        min_len, max_len = length_ranges.get(vtype, (50, 200))
        length = random.randint(min_len, max_len)
        
        # ETA between 0-23 hours
        eta_hour = random.randint(0, 23)
        etd_hour = eta_hour + random.randint(4, 12)
        
        vessels.append({
            "name": f"Vessel_{i+1:02d}",
            "type": vtype,
            "length": length,
            "eta": f"{eta_hour:02d}:00",
            "etd": f"{etd_hour:02d}:00" if etd_hour < 24 else "23:59",
            "eta_hour": eta_hour
        })
    
    return vessels

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="Berth Allocation", layout="wide")
st.title("🚢 Berth Allocation Optimization System")
st.markdown("---")

# Sidebar
st.sidebar.header("⚙️ Simulation Settings")
num_vessels = st.sidebar.slider("Number of Vessels", 3, 10, 5)
berth_length = st.sidebar.slider("Total Berth Length (meters)", 300, 2000, 1000, 100)

st.sidebar.markdown("---")
st.sidebar.info("""
**📊 Delay Calculation:**
- **Units**: Hours
- **Formula**: (Position / 50) - ETA
- **Assumption**: 50 meters = 1 hour travel time
- Negative delays = On time
""")

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("🎯 Optimization Control")
    if st.button("🎲 Generate Random Data & Optimize", type="primary"):
        with st.spinner("Generating vessels and solving optimization..."):
            # Generate vessels
            vessels = generate_random_vessels(num_vessels)
            
            # Display generated data
            st.subheader("📋 Generated Vessel Data")
            display_vessels = []
            for v in vessels:
                display_vessels.append({
                    "Vessel": v["name"],
                    "Type": v["type"],
                    "Length (m)": v["length"],
                    "ETA": v["eta"],
                    "ETD": v["etd"]
                })
            st.dataframe(display_vessels, use_container_width=True)
            
            # Run optimization
            allocations = berth_allocation_optimization(vessels, berth_length)
            
            if allocations:
                st.success("✅ Optimization completed successfully!")
                
                # Display results
                st.subheader("📈 Optimization Results")
                results_df = []
                for alloc in allocations:
                    results_df.append({
                        "Vessel": alloc["name"],
                        "Type": alloc["type"],
                        "Length": f"{alloc['length']}m",
                        "ETA": alloc["eta"],
                        "Start": f"{alloc['start']:.0f}m",
                        "End": f"{alloc['end']:.0f}m",
                        "Delay": f"{alloc['delay']:.2f}h"
                    })
                st.dataframe(results_df, use_container_width=True)
                
                # Show visualization
                st.subheader("📊 Berth Allocation Visualization")
                plot_berth_allocation(allocations, berth_length)
                
                # Summary statistics
                st.subheader("📊 Performance Summary")
                col1, col2, col3, col4 = st.columns(4)
                
                total_used = sum(alloc["length"] for alloc in allocations)
                utilization = (total_used / berth_length) * 100
                total_delay = sum(alloc["delay"] for alloc in allocations)
                avg_delay = total_delay / len(allocations)
                delayed_vessels = sum(1 for alloc in allocations if alloc["delay"] > 0.1)
                
                with col1:
                    st.metric("Berth Utilization", f"{utilization:.1f}%")
                with col2:
                    st.metric("Total Delay", f"{total_delay:.1f} hours")
                with col3:
                    st.metric("Average Delay", f"{avg_delay:.1f} hours")
                with col4:
                    st.metric("Delayed Vessels", f"{delayed_vessels}/{len(allocations)}")
                
            else:
                st.error("❌ No feasible solution found. Try increasing berth length or reducing number of vessels.")

with col2:
    st.subheader("ℹ️ How It Works")
    st.markdown("""
    **Optimization Process:**
    1. Generate random vessel data
    2. Solve berth allocation problem
    3. Minimize total delay hours
    4. Ensure no vessel overlaps
    5. Visualize results
    
    **Constraints:**
    - Vessels must fit within berth
    - No overlapping allocations  
    - Respect ETA times
    - Minimize waiting time
    
    **Color Coding:**
    - 🔴 Container
    - 🟢 Bulk Carrier  
    - 🟡 Tanker
    - 🟣 RORO
    - 🔵 Passenger
    """)

st.markdown("---")
st.caption("Developed for berth scheduling research | Delay measured in hours")
