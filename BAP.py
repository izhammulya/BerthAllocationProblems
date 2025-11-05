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
# FIXED Advanced Optimization Model
# -----------------------------
def berth_allocation_optimization(vessels, berth_length):
    try:
        model = LpProblem("Berth_Allocation", LpMinimize)

        # Decision variables
        start = {v["name"]: LpVariable(f"start_{v['name']}", lowBound=0, upBound=berth_length - v["length"]) for v in vessels}
        delay = {v["name"]: LpVariable(f"delay_{v['name']}", lowBound=0) for v in vessels}
        
        # FIXED: Use scaled position for time calculation
        conversion_factor = 50  # 50 meters = 1 hour
        scaled_start = {v["name"]: LpVariable(f"scaled_{v['name']}", lowBound=0) for v in vessels}

        # Objective: minimize total delay (in hours)
        model += lpSum(delay[v["name"]] for v in vessels)

        # Constraints for each vessel
        for i, vi in enumerate(vessels):
            li = vi["length"]
            eta_i = vi["eta_hour"]
            
            # Constraint: vessel must fit within berth
            model += start[vi["name"]] + li <= berth_length, f"WithinBerth_{vi['name']}"
            
            # FIXED: Use linear relationship instead of division
            # scaled_start = start_position / conversion_factor
            # This becomes: start_position = scaled_start * conversion_factor
            model += start[vi["name"]] == scaled_start[vi["name"]] * conversion_factor
            
            # Delay constraint: delay >= scaled_start - eta
            model += delay[vi["name"]] >= scaled_start[vi["name"]] - eta_i

        # Non-overlapping constraints
        for i, vi in enumerate(vessels):
            for j, vj in enumerate(vessels):
                if i < j:
                    li = vi["length"]
                    lj = vj["length"]
                    M = berth_length * 2
                    
                    y_ij = LpVariable(f"y_{vi['name']}_{vj['name']}", cat="Binary")
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
            delay_hours = max(0, value(delay[v["name"]]))
            scaled_time = value(scaled_start[v["name"]])
            
            allocations.append({
                "name": v["name"],
                "type": v["type"],
                "length": v["length"],
                "eta": v["eta"],
                "etd": v["etd"],
                "eta_hour": v["eta_hour"],
                "start": start_pos,
                "end": start_pos + v["length"],
                "start_time": scaled_time,
                "delay": delay_hours
            })
        
        return allocations
    
    except Exception as e:
        st.error(f"Error in optimization: {str(e)}")
        import traceback
        st.error(f"Detailed error: {traceback.format_exc()}")
        return []

# -----------------------------
# Simple Optimization Model
# -----------------------------
def simple_berth_allocation(vessels, berth_length):
    """Simplified version without time conversion"""
    try:
        model = LpProblem("Simple_Berth_Allocation", LpMinimize)

        # Decision variables - only position
        start = {v["name"]: LpVariable(f"start_{v['name']}", lowBound=0, upBound=berth_length - v["length"]) for v in vessels}
        
        # Simple objective: minimize total starting position
        model += lpSum(start[v["name"]] for v in vessels)

        # Constraints for each vessel
        for i, vi in enumerate(vessels):
            li = vi["length"]
            model += start[vi["name"]] + li <= berth_length, f"WithinBerth_{vi['name']}"

        # Non-overlapping constraints
        for i, vi in enumerate(vessels):
            for j, vj in enumerate(vessels):
                if i < j:
                    li = vi["length"]
                    lj = vj["length"]
                    M = berth_length * 2
                    
                    y_ij = LpVariable(f"y_{vi['name']}_{vj['name']}", cat="Binary")
                    model += start[vi["name"]] + li <= start[vj["name"]] + M * (1 - y_ij)
                    model += start[vj["name"]] + lj <= start[vi["name"]] + M * y_ij

        model.solve()

        if LpStatus[model.status] != "Optimal":
            return []

        # Calculate delay based on position (simplified)
        allocations = []
        for v in vessels:
            start_pos = value(start[v["name"]])
            # Simplified delay: difference between actual position and ideal position
            ideal_position = v["eta_hour"] * 50  # ETA hour * 50 meters/hour
            delay = max(0, (start_pos - ideal_position) / 50)  # Convert to hours
            
            allocations.append({
                "name": v["name"],
                "type": v["type"],
                "length": v["length"],
                "eta": v["eta"],
                "etd": v["etd"],
                "eta_hour": v["eta_hour"],
                "start": start_pos,
                "end": start_pos + v["length"],
                "delay": delay
            })
        
        return allocations
    
    except Exception as e:
        st.error(f"Error in simple optimization: {str(e)}")
        return []

# -----------------------------
# Visualization
# -----------------------------
def plot_berth_allocation(allocations, berth_length):
    if not allocations:
        st.warning("No allocation data to visualize")
        return
        
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
                ha='center', va='bottom', fontsize=9, weight='bold')
        
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
# Random Data Generator
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
        eta_hour = random.randint(0, 18)  # Reduced range to avoid late allocations
        etd_hour = min(eta_hour + random.randint(4, 8), 23)
        
        vessels.append({
            "name": f"Vessel_{i+1:02d}",
            "type": vtype,
            "length": length,
            "eta": f"{eta_hour:02d}:00",
            "etd": f"{etd_hour:02d}:00",
            "eta_hour": eta_hour
        })
    
    return vessels

# -----------------------------
# Streamlit UI with Session State
# -----------------------------
def main():
    st.set_page_config(page_title="Berth Allocation", layout="wide")
    st.title("🚢 Berth Allocation Optimization System")
    st.markdown("---")
    
    # Initialize session state
    if 'allocations' not in st.session_state:
        st.session_state.allocations = None
    if 'vessels' not in st.session_state:
        st.session_state.vessels = None
    if 'berth_length' not in st.session_state:
        st.session_state.berth_length = 1000

    # Sidebar
    st.sidebar.header("⚙️ Simulation Settings")
    num_vessels = st.sidebar.slider("Number of Vessels", 3, 8, 5)
    berth_length = st.sidebar.slider("Total Berth Length (meters)", 500, 2000, 1000, 100)
    
    algorithm_choice = st.sidebar.radio(
        "Optimization Algorithm",
        ["Simple Model", "Advanced Model"],
        index=0
    )

    st.sidebar.markdown("---")
    st.sidebar.info("""
    **📊 Model Differences:**
    
    **Simple Model:**
    - Optimize positions first
    - Calculate delay after
    - Faster & more reliable
    
    **Advanced Model:**
    - Optimize delay directly  
    - More realistic
    - More complex
    """)

    # Main content
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("🎯 Optimization Control")
        
        if st.button("🎲 Generate Random Data & Optimize", type="primary", key="optimize_btn"):
            with st.spinner("Generating vessels and solving optimization..."):
                # Generate vessels
                vessels = generate_random_vessels(num_vessels)
                st.session_state.vessels = vessels
                st.session_state.berth_length = berth_length
                
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
                
                # Run optimization based on choice
                if algorithm_choice == "Simple Model":
                    allocations = simple_berth_allocation(vessels, berth_length)
                    model_type = "Simple"
                else:
                    allocations = berth_allocation_optimization(vessels, berth_length)
                    model_type = "Advanced"
                
                st.session_state.allocations = allocations
                
                if allocations:
                    st.success(f"✅ {model_type} Optimization completed successfully!")
                    display_results(allocations, berth_length)
                else:
                    st.error("❌ No feasible solution found. Try increasing berth length or reducing number of vessels.")

        # Show previous results if they exist
        if st.session_state.allocations and st.button("🔄 Show Previous Results", key="show_previous"):
            display_results(st.session_state.allocations, st.session_state.berth_length)

    with col2:
        st.subheader("ℹ️ How It Works")
        st.markdown("""
        **Optimization Process:**
        1. Generate random vessel data
        2. Solve allocation problem
        3. Ensure no overlaps
        4. Minimize delays
        5. Visualize results
        
        **Session State:**
        - Results are saved
        - No page reload needed
        - Click 🔄 to see previous results
        """)

def display_results(allocations, berth_length):
    """Display optimization results"""
    # Display results
    st.subheader("📈 Optimization Results")
    results_df = []
    for alloc in allocations:
        results_df.append({
            "Vessel": alloc["name"],
            "Type": alloc["type"],
            "Length": f"{alloc['length']}m",
            "ETA": alloc["eta"],
            "Start Pos": f"{alloc['start']:.0f}m",
            "End Pos": f"{alloc['end']:.0f}m",
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
    avg_delay = total_delay / len(allocations) if allocations else 0
    delayed_vessels = sum(1 for alloc in allocations if alloc["delay"] > 0.1)
    
    with col1:
        st.metric("Berth Utilization", f"{utilization:.1f}%")
    with col2:
        st.metric("Total Delay", f"{total_delay:.1f} hours")
    with col3:
        st.metric("Average Delay", f"{avg_delay:.1f} hours")
    with col4:
        st.metric("Delayed Vessels", f"{delayed_vessels}/{len(allocations)}")

if __name__ == "__main__":
    main()
