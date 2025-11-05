import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import random
import time
import pandas as pd
from pulp import LpProblem, LpVariable, LpMinimize, lpSum, LpStatus, value
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')

# -----------------------------
# 1. MILP WITH PULP (UPDATED WITH CONTAINER CONSTRAINTS)
# -----------------------------
def milp_berth_allocation(vessels, berth_length, container_constraints=None):
    """Exact MILP solver with container position constraints"""
    try:
        model = LpProblem("Berth_Allocation_MILP", LpMinimize)
        
        # Decision variables
        start = {v["name"]: LpVariable(f"start_{v['name']}", lowBound=0, upBound=berth_length - v["length"]) for v in vessels}
        
        # Objective: minimize total starting position
        model += lpSum(start[v["name"]] for v in vessels)

        # Constraints
        for i, vi in enumerate(vessels):
            li = vi["length"]
            model += start[vi["name"]] + li <= berth_length, f"WithinBerth_{vi['name']}"
            
            # Container position constraints
            if container_constraints and vi["type"] == "Container":
                min_pos = container_constraints.get("min_position", 0)
                max_pos = container_constraints.get("max_position", berth_length)
                model += start[vi["name"]] >= min_pos, f"ContainerMinPos_{vi['name']}"
                model += start[vi["name"]] + li <= max_pos, f"ContainerMaxPos_{vi['name']}"

        # Non-overlapping constraints
        for i, vi in enumerate(vessels):
            for j, vj in enumerate(vessels):
                if i < j:
                    li, lj = vi["length"], vj["length"]
                    M = berth_length * 2
                    y_ij = LpVariable(f"y_{vi['name']}_{vj['name']}", cat="Binary")
                    model += start[vi["name"]] + li <= start[vj["name"]] + M * (1 - y_ij)
                    model += start[vj["name"]] + lj <= start[vi["name"]] + M * y_ij

        # Solve
        model.solve()

        if LpStatus[model.status] != "Optimal":
            return []

        # Convert results
        allocations = []
        for v in vessels:
            start_pos = value(start[v["name"]])
            ideal_position = v["eta_hour"] * 50
            delay = max(0, (start_pos - ideal_position) / 50)
            
            allocations.append({
                "name": v["name"], "type": v["type"], "length": v["length"],
                "eta": v["eta"], "etd": v["etd"], "eta_hour": v["eta_hour"],
                "start": start_pos, "end": start_pos + v["length"], "delay": delay
            })
        
        return allocations
    
    except Exception as e:
        st.error(f"MILP Error: {str(e)}")
        return []

# -----------------------------
# 2. GENETIC ALGORITHM (UPDATED WITH CONTAINER CONSTRAINTS)
# -----------------------------
def genetic_algorithm_berth(vessels, berth_length, container_constraints=None, pop_size=50, generations=100):
    """Genetic Algorithm with container position constraints"""
    try:
        n_vessels = len(vessels)
        vessel_lengths = [v["length"] for v in vessels]
        eta_hours = [v["eta_hour"] for v in vessels]
        vessel_types = [v["type"] for v in vessels]
        conversion_factor = 50
        
        def create_individual():
            order = list(range(n_vessels))
            random.shuffle(order)
            
            positions = []
            current_pos = 0
            
            for idx in order:
                vessel_type = vessel_types[idx]
                max_pos = berth_length - vessel_lengths[idx]
                
                # Apply container constraints if specified
                if container_constraints and vessel_type == "Container":
                    min_pos = container_constraints.get("min_position", 0)
                    max_pos = min(max_pos, container_constraints.get("max_position", berth_length) - vessel_lengths[idx])
                    # Ensure we're within container zone
                    current_pos = max(current_pos, min_pos)
                
                if current_pos > max_pos:
                    current_pos = max_pos
                
                pos = current_pos + random.uniform(0, 10)
                pos = min(pos, max_pos)
                positions.append(pos)
                current_pos = pos + vessel_lengths[idx] + 2
            
            return order, positions
        
        def fitness(individual):
            order, positions = individual
            total_delay = 0
            
            for i in range(n_vessels):
                vessel_idx = order[i]
                pos = positions[i]
                length = vessel_lengths[vessel_idx]
                vessel_type = vessel_types[vessel_idx]
                
                # Berth capacity
                if pos + length > berth_length:
                    return float('inf')
                
                # Container position constraints
                if container_constraints and vessel_type == "Container":
                    min_pos = container_constraints.get("min_position", 0)
                    max_pos = container_constraints.get("max_position", berth_length)
                    if pos < min_pos or pos + length > max_pos:
                        return float('inf')
                
                # Check overlaps
                for j in range(i + 1, n_vessels):
                    other_idx = order[j]
                    other_pos = positions[j]
                    other_length = vessel_lengths[other_idx]
                    
                    overlap = (pos < other_pos + other_length) and (pos + length > other_pos)
                    if overlap:
                        return float('inf')
                
                # Calculate delay
                start_time = pos / conversion_factor
                delay = max(0, start_time - eta_hours[vessel_idx])
                total_delay += delay
            
            return total_delay
        
        # Crossover and mutation functions (same as before)
        def crossover(parent1, parent2):
            order1, positions1 = parent1
            order2, positions2 = parent2
            
            crossover_point = random.randint(1, n_vessels - 1)
            child_order = order1[:crossover_point]
            
            for vessel in order2:
                if vessel not in child_order:
                    child_order.append(vessel)
            
            child_positions = []
            for i in range(n_vessels):
                alpha = random.random()
                pos = alpha * positions1[i] + (1 - alpha) * positions2[i]
                child_positions.append(pos)
            
            return child_order, child_positions
        
        def mutate(individual, mutation_rate=0.1):
            order, positions = individual
            
            if random.random() < mutation_rate:
                i, j = random.sample(range(n_vessels), 2)
                order[i], order[j] = order[j], order[i]
            
            if random.random() < mutation_rate:
                idx = random.randint(0, n_vessels - 1)
                max_pos = berth_length - vessel_lengths[order[idx]]
                
                # Apply container constraints for mutation
                if container_constraints and vessel_types[order[idx]] == "Container":
                    min_pos = container_constraints.get("min_position", 0)
                    max_pos = min(max_pos, container_constraints.get("max_position", berth_length) - vessel_lengths[order[idx]])
                    positions[idx] = random.uniform(min_pos, max_pos)
                else:
                    positions[idx] = random.uniform(0, max_pos)
            
            return order, positions
        
        # GA main loop
        population = [create_individual() for _ in range(pop_size)]
        best_fitness = float('inf')
        best_individual = None
        
        for generation in range(generations):
            fitness_scores = [fitness(ind) for ind in population]
            
            current_best = min(fitness_scores)
            if current_best < best_fitness:
                best_fitness = current_best
                best_individual = population[fitness_scores.index(current_best)]
            
            # Selection
            new_population = []
            for _ in range(pop_size):
                tournament_indices = random.sample(range(len(population)), 3)
                tournament_scores = [fitness_scores[i] for i in tournament_indices]
                best_idx = tournament_indices[np.argmin(tournament_scores)]
                new_population.append(population[best_idx])
            
            # Crossover and mutation
            population = []
            for i in range(0, len(new_population), 2):
                if i + 1 < len(new_population):
                    parent1 = new_population[i]
                    parent2 = new_population[i + 1]
                    
                    child1 = crossover(parent1, parent2)
                    child2 = crossover(parent2, parent1)
                    
                    child1 = mutate(child1)
                    child2 = mutate(child2)
                    
                    population.extend([child1, child2])
                else:
                    population.append(new_population[i])
        
        # Convert best solution
        if best_individual and best_fitness < float('inf'):
            order, positions = best_individual
            allocations = []
            
            for i in range(n_vessels):
                vessel_idx = order[i]
                start_pos = positions[i]
                start_time = start_pos / conversion_factor
                delay = max(0, start_time - eta_hours[vessel_idx])
                
                allocations.append({
                    "name": vessels[vessel_idx]["name"],
                    "type": vessels[vessel_idx]["type"],
                    "length": vessels[vessel_idx]["length"],
                    "eta": vessels[vessel_idx]["eta"],
                    "etd": vessels[vessel_idx]["etd"],
                    "eta_hour": vessels[vessel_idx]["eta_hour"],
                    "start": start_pos,
                    "end": start_pos + vessels[vessel_idx]["length"],
                    "delay": delay
                })
            
            return allocations
        
        return []
    
    except Exception as e:
        st.error(f"GA Error: {str(e)}")
        return []

# -----------------------------
# 3. INTERACTIVE PLOTLY VISUALIZATION WITH HOVER
# -----------------------------
def create_interactive_berth_allocation(allocations, berth_length, container_constraints=None):
    """Create interactive Plotly visualization with hover tooltips"""
    
    fig = go.Figure()
    
    # Add berth line
    fig.add_trace(go.Scatter(
        x=[0, berth_length],
        y=[0, 0],
        mode='lines',
        line=dict(color='blue', width=8),
        name='Berth Line',
        hoverinfo='skip'
    ))
    
    # Add container zone if constraints exist
    if container_constraints:
        min_pos = container_constraints.get("min_position", 0)
        max_pos = container_constraints.get("max_position", berth_length)
        
        fig.add_trace(go.Scatter(
            x=[min_pos, max_pos, max_pos, min_pos, min_pos],
            y=[-0.5, -0.5, 0.5, 0.5, -0.5],
            fill='toself',
            fillcolor='rgba(173, 216, 230, 0.3)',
            line=dict(color='lightblue', width=2, dash='dash'),
            name='Container Zone',
            hoverinfo='skip'
        ))
        
        # Add container zone label
        fig.add_annotation(
            x=(min_pos + max_pos) / 2,
            y=-1,
            text=f"Container Zone: {min_pos}-{max_pos}m",
            showarrow=False,
            font=dict(color='blue', size=10)
        )
    
    # Color mapping for vessel types
    color_map = {
        "Container": "#FF6B6B",
        "Bulk": "#4ECDC4", 
        "Tanker": "#FFD166",
        "RORO": "#9D4EDD",
        "Passenger": "#06D6A0"
    }
    
    # Add vessels as rectangles with hover information
    for i, alloc in enumerate(allocations):
        start, end = alloc['start'], alloc['end']
        vessel_type = alloc['type']
        
        # Create hover text
        hover_text = (
            f"<b>{alloc['name']}</b><br>"
            f"Type: {vessel_type}<br>"
            f"Position: {start:.1f}-{end:.1f}m<br>"
            f"Length: {alloc['length']}m<br>"
            f"ETA: {alloc['eta']}<br>"
            f"Delay: {alloc['delay']:.2f}h<br>"
            f"Range: {end - start:.1f}m"
        )
        
        # Add vessel rectangle
        fig.add_trace(go.Scatter(
            x=[start, end, end, start, start],
            y=[i+0.5, i+0.5, i-0.5, i-0.5, i+0.5],
            fill='toself',
            fillcolor=color_map.get(vessel_type, "#118AB2"),
            line=dict(color='black', width=1),
            name=vessel_type,
            hoverinfo='text',
            hovertext=hover_text,
            showlegend=False
        ))
        
        # Add vessel label
        fig.add_annotation(
            x=(start + end) / 2,
            y=i,
            text=alloc['name'],
            showarrow=False,
            font=dict(color='white', size=9, weight='bold')
        )
    
    # Update layout for better interactivity
    fig.update_layout(
        title=dict(
            text="Interactive Berth Allocation Visualization",
            x=0.5,
            font=dict(size=16)
        ),
        xaxis=dict(
            title="Berth Position (meters)",
            range=[0, berth_length],
            gridcolor='lightgray'
        ),
        yaxis=dict(
            title="Vessel",
            range=[-2, len(allocations) + 1],
            showticklabels=False,
            gridcolor='lightgray'
        ),
        hovermode='closest',
        plot_bgcolor='white',
        height=400 + len(allocations) * 30,
        showlegend=True
    )
    
    # Add berth length annotation
    fig.add_annotation(
        x=berth_length/2,
        y=-1.5,
        text=f"Total Berth Length: {berth_length}m",
        showarrow=False,
        font=dict(color='blue', size=12, weight='bold'),
        bgcolor='lightblue'
    )
    
    return fig

# -----------------------------
# 4. STREAMLIT APP WITH NEW FEATURES
# -----------------------------
def main():
    st.set_page_config(page_title="Berth Allocation - Interactive", layout="wide")
    st.title("🚢 Interactive Berth Allocation with Container Constraints")
    st.markdown("---")
    
    # Initialize session state for container constraints
    if 'container_constraints' not in st.session_state:
        st.session_state.container_constraints = None
    
    # Sidebar
    st.sidebar.header("⚙️ Simulation Settings")
    num_vessels = st.sidebar.slider("Number of Vessels", 3, 8, 5)
    berth_length = st.sidebar.slider("Total Berth Length (meters)", 500, 2000, 1000, 100)
    
    # Container constraints section
    st.sidebar.header("📦 Container Vessel Constraints")
    use_container_constraints = st.sidebar.checkbox("Enable Container Position Constraints", value=False)
    
    if use_container_constraints:
        col1, col2 = st.sidebar.columns(2)
        with col1:
            min_position = st.number_input("Min Position (m)", min_value=0, max_value=berth_length, value=200)
        with col2:
            max_position = st.number_input("Max Position (m)", min_value=min_position, max_value=berth_length, value=800)
        
        st.session_state.container_constraints = {
            "min_position": min_position,
            "max_position": max_position
        }
        
        st.sidebar.info(f"📦 Containers restricted to: {min_position}-{max_position}m")
    else:
        st.session_state.container_constraints = None
    
    algorithm_choice = st.sidebar.radio(
        "Run Mode:",
        ["Single Algorithm", "Compare Algorithms"]
    )
    
    if algorithm_choice == "Single Algorithm":
        selected_algorithm = st.sidebar.selectbox(
            "Select Algorithm:",
            ["MILP (PuLP)", "Genetic Algorithm"]
        )
    
    st.sidebar.markdown("---")
    st.sidebar.info("""
    **New Features:**
    - 🎯 **Interactive hover** for vessel details
    - 📦 **Container zone** visualization
    - 🔧 **Position constraints** for container vessels
    - 📊 **Real-time range** display
    """)
    
    # Main content
    if st.button("🎲 Generate & Optimize", type="primary"):
        with st.spinner("Generating vessels and running optimization..."):
            vessels = generate_random_vessels(num_vessels)
            
            # Display vessel data
            st.subheader("📋 Generated Vessel Data")
            display_vessels = []
            for v in vessels:
                display_vessels.append({
                    "Vessel": v["name"], "Type": v["type"], 
                    "Length (m)": v["length"], "ETA": v["eta"], "ETD": v["etd"]
                })
            st.dataframe(display_vessels, use_container_width=True)
            
            # Show container constraints info
            if st.session_state.container_constraints:
                min_pos = st.session_state.container_constraints["min_position"]
                max_pos = st.session_state.container_constraints["max_position"]
                st.info(f"📦 **Container Constraints Active**: All container vessels will be placed between {min_pos}m and {max_pos}m")
            
            if algorithm_choice == "Single Algorithm":
                start_time = time.time()
                
                if selected_algorithm == "MILP (PuLP)":
                    allocations = milp_berth_allocation(vessels, berth_length, st.session_state.container_constraints)
                else:  # Genetic Algorithm
                    allocations = genetic_algorithm_berth(vessels, berth_length, st.session_state.container_constraints)
                
                computation_time = time.time() - start_time
                
                if allocations:
                    st.success(f"✅ {selected_algorithm} completed in {computation_time:.2f}s!")
                    display_interactive_results(allocations, berth_length, selected_algorithm, computation_time)
                else:
                    st.error("❌ No feasible solution found. Try relaxing constraints or increasing berth length.")
                    
            else:  # Compare algorithms
                results = compare_algorithms(vessels, berth_length, st.session_state.container_constraints)
                display_comparison_results(results, berth_length)

def display_interactive_results(allocations, berth_length, algorithm_name, computation_time):
    """Display interactive results with Plotly"""
    
    # Results table
    st.subheader(f"📈 {algorithm_name} Results")
    
    results_df = []
    for alloc in allocations:
        results_df.append({
            "Vessel": alloc["name"], 
            "Type": alloc["type"],
            "Length": f"{alloc['length']}m", 
            "ETA": alloc["eta"],
            "Start Pos": f"{alloc['start']:.0f}m", 
            "End Pos": f"{alloc['end']:.0f}m",
            "Range": f"{alloc['end'] - alloc['start']:.0f}m",
            "Delay": f"{alloc['delay']:.2f}h"
        })
    st.dataframe(results_df, use_container_width=True)
    
    # Interactive visualization
    st.subheader("🎯 Interactive Berth Allocation")
    st.markdown("**📍 Hover over vessels to see detailed information**")
    
    fig = create_interactive_berth_allocation(allocations, berth_length, st.session_state.container_constraints)
    st.plotly_chart(fig, use_container_width=True)
    
    # Summary statistics
    st.subheader("📊 Performance Summary")
    col1, col2, col3, col4 = st.columns(4)
    
    total_used = sum(alloc["length"] for alloc in allocations)
    utilization = (total_used / berth_length) * 100
    total_delay = sum(alloc["delay"] for alloc in allocations)
    avg_delay = total_delay / len(allocations)
    
    with col1:
        st.metric("Berth Utilization", f"{utilization:.1f}%")
    with col2:
        st.metric("Total Delay", f"{total_delay:.1f} hours")
    with col3:
        st.metric("Average Delay", f"{avg_delay:.1f} hours")
    with col4:
        st.metric("Computation Time", f"{computation_time:.2f}s")
    
    # Container-specific analysis
    if st.session_state.container_constraints:
        container_vessels = [a for a in allocations if a["type"] == "Container"]
        if container_vessels:
            st.subheader("📦 Container Vessel Analysis")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Container Vessels", len(container_vessels))
            with col2:
                avg_container_delay = sum(a["delay"] for a in container_vessels) / len(container_vessels)
                st.metric("Avg Container Delay", f"{avg_container_delay:.1f}h")
            with col3:
                container_utilization = sum(a["length"] for a in container_vessels) / berth_length * 100
                st.metric("Container Space Used", f"{container_utilization:.1f}%")

def compare_algorithms(vessels, berth_length, container_constraints):
    """Compare MILP and GA algorithms"""
    results = {}
    algorithms = {
        "MILP (PuLP)": milp_berth_allocation,
        "Genetic Algorithm": genetic_algorithm_berth
    }
    
    for algo_name, algo_func in algorithms.items():
        with st.spinner(f"Running {algo_name}..."):
            start_time = time.time()
            allocations = algo_func(vessels, berth_length, container_constraints)
            computation_time = time.time() - start_time
            
            if allocations and len(allocations) == len(vessels):
                total_delay = sum(a["delay"] for a in allocations)
                utilization = (sum(a["length"] for a in allocations) / berth_length) * 100
                feasible = True
            else:
                total_delay = float('inf')
                utilization = 0
                feasible = False
            
            results[algo_name] = {
                "allocations": allocations,
                "computation_time": computation_time,
                "total_delay": total_delay,
                "utilization": utilization,
                "feasible": feasible
            }
    
    return results

def display_comparison_results(results, berth_length):
    """Display comparison results"""
    st.subheader("📊 Algorithm Comparison Results")
    
    # Comparison table
    comparison_data = []
    for algo_name, result in results.items():
        comparison_data.append({
            "Algorithm": algo_name,
            "Total Delay (hours)": f"{result['total_delay']:.2f}" if result['feasible'] else "N/A",
            "Computation Time (s)": f"{result['computation_time']:.3f}",
            "Berth Utilization": f"{result['utilization']:.1f}%" if result['feasible'] else "N/A",
            "Feasible": "✅" if result['feasible'] else "❌"
        })
    
    st.dataframe(comparison_data, use_container_width=True)
    
    # Find best algorithm
    feasible_results = {k: v for k, v in results.items() if v['feasible']}
    if feasible_results:
        best_algo = min(feasible_results.keys(), key=lambda x: feasible_results[x]['total_delay'])
        best_result = feasible_results[best_algo]
        
        st.success(f"🏆 Best Algorithm: {best_algo} "
                  f"(Delay: {best_result['total_delay']:.2f}h, "
                  f"Time: {best_result['computation_time']:.2f}s)")
        
        # Show interactive visualization for best algorithm
        st.subheader(f"🎯 Best Allocation Visualization ({best_algo})")
        fig = create_interactive_berth_allocation(best_result["allocations"], berth_length, st.session_state.container_constraints)
        st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# HELPER FUNCTIONS
# -----------------------------
def generate_random_vessels(num_vessels):
    """Generate random vessel data with more container vessels"""
    vessel_types = ["Container", "Bulk", "Tanker", "RORO", "Passenger"]
    vessels = []
    
    for i in range(num_vessels):
        # Increase probability of container vessels for testing constraints
        if random.random() < 0.4:  # 40% chance for container
            vtype = "Container"
        else:
            vtype = random.choice([t for t in vessel_types if t != "Container"])
            
        length_ranges = {
            "Container": (150, 350), 
            "Bulk": (200, 400),
            "Tanker": (250, 450), 
            "RORO": (100, 250), 
            "Passenger": (80, 200)
        }
        min_len, max_len = length_ranges.get(vtype, (50, 200))
        length = random.randint(min_len, max_len)
        eta_hour = random.randint(0, 18)
        etd_hour = min(eta_hour + random.randint(4, 8), 23)
        
        vessels.append({
            "name": f"Vessel_{i+1:02d}", "type": vtype, "length": length,
            "eta": f"{eta_hour:02d}:00", "etd": f"{etd_hour:02d}:00", "eta_hour": eta_hour
        })
    
    return vessels

if __name__ == "__main__":
    main()


# import streamlit as st
# import matplotlib.pyplot as plt
# import numpy as np
# import random
# import time
# import pandas as pd
# from pulp import LpProblem, LpVariable, LpMinimize, lpSum, LpStatus, value
# from collections import deque
# import warnings
# warnings.filterwarnings('ignore')

# # -----------------------------
# # 1. MILP WITH PULP
# # -----------------------------
# def milp_berth_allocation(vessels, berth_length):
#     """Exact MILP solver using PuLP"""
#     try:
#         model = LpProblem("Berth_Allocation_MILP", LpMinimize)
        
#         # Decision variables
#         start = {v["name"]: LpVariable(f"start_{v['name']}", lowBound=0, upBound=berth_length - v["length"]) for v in vessels}
        
#         # Objective: minimize total starting position
#         model += lpSum(start[v["name"]] for v in vessels)

#         # Constraints
#         for i, vi in enumerate(vessels):
#             li = vi["length"]
#             model += start[vi["name"]] + li <= berth_length, f"WithinBerth_{vi['name']}"

#         # Non-overlapping constraints
#         for i, vi in enumerate(vessels):
#             for j, vj in enumerate(vessels):
#                 if i < j:
#                     li, lj = vi["length"], vj["length"]
#                     M = berth_length * 2
#                     y_ij = LpVariable(f"y_{vi['name']}_{vj['name']}", cat="Binary")
#                     model += start[vi["name"]] + li <= start[vj["name"]] + M * (1 - y_ij)
#                     model += start[vj["name"]] + lj <= start[vi["name"]] + M * y_ij

#         # Solve
#         model.solve()

#         if LpStatus[model.status] != "Optimal":
#             return []

#         # Convert results
#         allocations = []
#         for v in vessels:
#             start_pos = value(start[v["name"]])
#             ideal_position = v["eta_hour"] * 50
#             delay = max(0, (start_pos - ideal_position) / 50)
            
#             allocations.append({
#                 "name": v["name"], "type": v["type"], "length": v["length"],
#                 "eta": v["eta"], "etd": v["etd"], "eta_hour": v["eta_hour"],
#                 "start": start_pos, "end": start_pos + v["length"], "delay": delay
#             })
        
#         return allocations
    
#     except Exception as e:
#         st.error(f"MILP Error: {str(e)}")
#         return []

# # -----------------------------
# # 2. GENETIC ALGORITHM
# # -----------------------------
# def genetic_algorithm_berth(vessels, berth_length, pop_size=50, generations=100):
#     """Standard Genetic Algorithm"""
#     try:
#         n_vessels = len(vessels)
#         vessel_lengths = [v["length"] for v in vessels]
#         eta_hours = [v["eta_hour"] for v in vessels]
#         conversion_factor = 50
        
#         def create_individual():
#             # Create random order
#             order = list(range(n_vessels))
#             random.shuffle(order)
            
#             # Assign positions sequentially
#             positions = []
#             current_pos = 0
            
#             for idx in order:
#                 max_pos = berth_length - vessel_lengths[idx]
#                 # Ensure we don't exceed berth length
#                 if current_pos > max_pos:
#                     current_pos = max_pos
                
#                 pos = current_pos + random.uniform(0, 10)  # Small random offset
#                 pos = min(pos, max_pos)
#                 positions.append(pos)
#                 current_pos = pos + vessel_lengths[idx] + 2  # Small gap
            
#             return order, positions
        
#         def fitness(individual):
#             order, positions = individual
#             total_delay = 0
            
#             # Check constraints
#             for i in range(n_vessels):
#                 vessel_idx = order[i]
#                 pos = positions[i]
#                 length = vessel_lengths[vessel_idx]
                
#                 # Berth capacity
#                 if pos + length > berth_length:
#                     return float('inf')
                
#                 # Check overlaps
#                 for j in range(i + 1, n_vessels):
#                     other_idx = order[j]
#                     other_pos = positions[j]
#                     other_length = vessel_lengths[other_idx]
                    
#                     # Check if vessels overlap
#                     overlap = (pos < other_pos + other_length) and (pos + length > other_pos)
#                     if overlap:
#                         return float('inf')
                
#                 # Calculate delay
#                 start_time = pos / conversion_factor
#                 delay = max(0, start_time - eta_hours[vessel_idx])
#                 total_delay += delay
            
#             return total_delay
        
#         def crossover(parent1, parent2):
#             order1, positions1 = parent1
#             order2, positions2 = parent2
            
#             # Order crossover (OX)
#             crossover_point = random.randint(1, n_vessels - 1)
#             child_order = order1[:crossover_point]
            
#             # Add missing vessels from parent2
#             for vessel in order2:
#                 if vessel not in child_order:
#                     child_order.append(vessel)
            
#             # Blend positions
#             child_positions = []
#             for i in range(n_vessels):
#                 alpha = random.random()
#                 pos = alpha * positions1[i] + (1 - alpha) * positions2[i]
#                 child_positions.append(pos)
            
#             return child_order, child_positions
        
#         def mutate(individual, mutation_rate=0.1):
#             order, positions = individual
            
#             if random.random() < mutation_rate:
#                 # Swap two vessels
#                 i, j = random.sample(range(n_vessels), 2)
#                 order[i], order[j] = order[j], order[i]
            
#             if random.random() < mutation_rate:
#                 # Mutate a position
#                 idx = random.randint(0, n_vessels - 1)
#                 max_pos = berth_length - vessel_lengths[order[idx]]
#                 positions[idx] = random.uniform(0, max_pos)
            
#             return order, positions
        
#         # Initialize population
#         population = [create_individual() for _ in range(pop_size)]
#         best_fitness = float('inf')
#         best_individual = None
        
#         # Evolution loop
#         for generation in range(generations):
#             # Evaluate fitness
#             fitness_scores = []
#             for ind in population:
#                 score = fitness(ind)
#                 fitness_scores.append(score)
#                 if score < best_fitness:
#                     best_fitness = score
#                     best_individual = ind
            
#             # Selection (tournament)
#             new_population = []
#             for _ in range(pop_size):
#                 # Tournament selection with size 3
#                 tournament_indices = random.sample(range(len(population)), 3)
#                 tournament_scores = [fitness_scores[i] for i in tournament_indices]
#                 best_idx = tournament_indices[np.argmin(tournament_scores)]
#                 new_population.append(population[best_idx])
            
#             # Crossover and mutation
#             population = []
#             for i in range(0, len(new_population), 2):
#                 if i + 1 < len(new_population):
#                     parent1 = new_population[i]
#                     parent2 = new_population[i + 1]
                    
#                     child1 = crossover(parent1, parent2)
#                     child2 = crossover(parent2, parent1)
                    
#                     child1 = mutate(child1)
#                     child2 = mutate(child2)
                    
#                     population.extend([child1, child2])
#                 else:
#                     population.append(new_population[i])
        
#         # Convert best solution
#         if best_individual and best_fitness < float('inf'):
#             order, positions = best_individual
#             allocations = []
            
#             for i in range(n_vessels):
#                 vessel_idx = order[i]
#                 start_pos = positions[i]
#                 start_time = start_pos / conversion_factor
#                 delay = max(0, start_time - eta_hours[vessel_idx])
                
#                 allocations.append({
#                     "name": vessels[vessel_idx]["name"],
#                     "type": vessels[vessel_idx]["type"],
#                     "length": vessels[vessel_idx]["length"],
#                     "eta": vessels[vessel_idx]["eta"],
#                     "etd": vessels[vessel_idx]["etd"],
#                     "eta_hour": vessels[vessel_idx]["eta_hour"],
#                     "start": start_pos,
#                     "end": start_pos + vessels[vessel_idx]["length"],
#                     "delay": delay
#                 })
            
#             return allocations
        
#         return []
    
#     except Exception as e:
#         st.error(f"GA Error: {str(e)}")
#         return []

# # -----------------------------
# # 3. SIMULATED ANNEALING
# # -----------------------------
# def simulated_annealing_berth(vessels, berth_length, initial_temp=1000, cooling_rate=0.95, iterations=500):
#     """Simulated Annealing Algorithm"""
#     try:
#         n_vessels = len(vessels)
#         vessel_lengths = [v["length"] for v in vessels]
#         eta_hours = [v["eta_hour"] for v in vessels]
#         conversion_factor = 50
        
#         def create_solution():
#             # Create random order
#             order = list(range(n_vessels))
#             random.shuffle(order)
            
#             # Assign sequential positions
#             positions = []
#             current_pos = 0
#             for idx in order:
#                 max_pos = berth_length - vessel_lengths[idx]
#                 pos = current_pos + random.uniform(0, 10)
#                 pos = min(pos, max_pos)
#                 positions.append(pos)
#                 current_pos = pos + vessel_lengths[idx] + 2
            
#             return order, positions
        
#         def calculate_cost(order, positions):
#             total_delay = 0
            
#             # Check berth capacity
#             for i in range(n_vessels):
#                 if positions[i] + vessel_lengths[order[i]] > berth_length:
#                     return float('inf')
            
#             # Check overlaps
#             for i in range(n_vessels):
#                 for j in range(i + 1, n_vessels):
#                     pos1, len1 = positions[i], vessel_lengths[order[i]]
#                     pos2, len2 = positions[j], vessel_lengths[order[j]]
                    
#                     if (pos1 < pos2 + len2) and (pos1 + len1 > pos2):
#                         return float('inf')
            
#             # Calculate delays
#             for i in range(n_vessels):
#                 start_time = positions[i] / conversion_factor
#                 delay = max(0, start_time - eta_hours[order[i]])
#                 total_delay += delay
            
#             return total_delay
        
#         def get_neighbor(current_order, current_positions):
#             new_order = current_order.copy()
#             new_positions = current_positions.copy()
            
#             # Choose random mutation
#             mutation_type = random.choice(['swap', 'position'])
            
#             if mutation_type == 'swap':
#                 i, j = random.sample(range(n_vessels), 2)
#                 new_order[i], new_order[j] = new_order[j], new_order[i]
#             else:
#                 idx = random.randint(0, n_vessels - 1)
#                 max_pos = berth_length - vessel_lengths[new_order[idx]]
#                 new_positions[idx] = random.uniform(0, max_pos)
            
#             return new_order, new_positions
        
#         # Initialize
#         current_order, current_positions = create_solution()
#         current_cost = calculate_cost(current_order, current_positions)
#         best_order, best_positions = current_order.copy(), current_positions.copy()
#         best_cost = current_cost
        
#         temperature = initial_temp
        
#         # Annealing process
#         for iteration in range(iterations):
#             new_order, new_positions = get_neighbor(current_order, current_positions)
#             new_cost = calculate_cost(new_order, new_positions)
            
#             # Acceptance criterion
#             if new_cost < current_cost:
#                 current_order, current_positions = new_order, new_positions
#                 current_cost = new_cost
#                 if new_cost < best_cost:
#                     best_order, best_positions = new_order.copy(), new_positions.copy()
#                     best_cost = new_cost
#             else:
#                 # Accept worse solution with probability
#                 acceptance_prob = np.exp((current_cost - new_cost) / temperature)
#                 if random.random() < acceptance_prob:
#                     current_order, current_positions = new_order, new_positions
#                     current_cost = new_cost
            
#             temperature *= cooling_rate
        
#         # Convert result
#         if best_cost < float('inf'):
#             allocations = []
#             for i in range(n_vessels):
#                 vessel_idx = best_order[i]
#                 start_pos = best_positions[i]
#                 start_time = start_pos / conversion_factor
#                 delay = max(0, start_time - eta_hours[vessel_idx])
                
#                 allocations.append({
#                     "name": vessels[vessel_idx]["name"],
#                     "type": vessels[vessel_idx]["type"],
#                     "length": vessels[vessel_idx]["length"],
#                     "eta": vessels[vessel_idx]["eta"],
#                     "etd": vessels[vessel_idx]["etd"],
#                     "eta_hour": vessels[vessel_idx]["eta_hour"],
#                     "start": start_pos,
#                     "end": start_pos + vessels[vessel_idx]["length"],
#                     "delay": delay
#                 })
#             return allocations
        
#         return []
    
#     except Exception as e:
#         st.error(f"SA Error: {str(e)}")
#         return []

# # -----------------------------
# # 4. ML-ENHANCED GENETIC ALGORITHM (SIMPLIFIED)
# # -----------------------------
# def ml_enhanced_ga_berth(vessels, berth_length, pop_size=50, generations=100):
#     """Genetic Algorithm with ML-inspired enhancements"""
#     try:
#         n_vessels = len(vessels)
#         vessel_lengths = [v["length"] for v in vessels]
#         eta_hours = [v["eta_hour"] for v in vessels]
#         conversion_factor = 50
        
#         # ML-inspired: Calculate vessel priorities
#         def calculate_vessel_priorities():
#             priorities = []
#             for vessel in vessels:
#                 score = 0.0
#                 # Priority based on vessel type
#                 type_weights = {"Container": 1.0, "Tanker": 0.9, "Bulk": 0.8, "RORO": 0.7, "Passenger": 0.6}
#                 score += type_weights.get(vessel["type"], 0.5)
                
#                 # Priority based on ETA (earlier = higher priority)
#                 score += (24 - vessel["eta_hour"]) / 24
                
#                 # Priority based on length (smaller = more flexible)
#                 score += (300 - vessel["length"]) / 300
                
#                 priorities.append(score)
            
#             # Normalize priorities
#             max_priority = max(priorities) if priorities else 1
#             return [p / max_priority for p in priorities]
        
#         priorities = calculate_vessel_priorities()
        
#         def create_ml_individual():
#             # Create order biased by ML priorities
#             order = list(range(n_vessels))
#             # Sort by priority with some randomness
#             order.sort(key=lambda x: priorities[x] + random.uniform(-0.2, 0.2), reverse=True)
            
#             positions = []
#             current_pos = 0
            
#             for idx in order:
#                 max_pos = berth_length - vessel_lengths[idx]
                
#                 # ML-guided: high priority vessels get positions closer to their ideal
#                 ideal_pos = eta_hours[idx] * 50
#                 ml_bias = priorities[idx] * 20
#                 base_pos = max(current_pos, ideal_pos - ml_bias)
                
#                 pos = min(base_pos + random.uniform(-10, 10), max_pos)
#                 positions.append(max(0, pos))
#                 current_pos = pos + vessel_lengths[idx] + 2
            
#             return order, positions
        
#         # Use standard GA functions but with ML initialization
#         def fitness(individual):
#             order, positions = individual
#             total_delay = 0
            
#             for i in range(n_vessels):
#                 vessel_idx = order[i]
#                 pos = positions[i]
#                 length = vessel_lengths[vessel_idx]
                
#                 if pos + length > berth_length:
#                     return float('inf')
                
#                 # Check overlaps
#                 for j in range(i + 1, n_vessels):
#                     other_idx = order[j]
#                     other_pos = positions[j]
#                     other_length = vessel_lengths[other_idx]
                    
#                     if (pos < other_pos + other_length) and (pos + length > other_pos):
#                         return float('inf')
                
#                 # Calculate delay with ML weighting
#                 start_time = pos / conversion_factor
#                 delay = max(0, start_time - eta_hours[vessel_idx])
#                 # Higher priority vessels get more weight
#                 weighted_delay = delay * (1 + priorities[vessel_idx] * 0.3)
#                 total_delay += weighted_delay
            
#             return total_delay
        
#         def crossover(parent1, parent2):
#             order1, positions1 = parent1
#             order2, positions2 = parent2
            
#             crossover_point = random.randint(1, n_vessels - 1)
#             child_order = order1[:crossover_point]
            
#             for vessel in order2:
#                 if vessel not in child_order:
#                     child_order.append(vessel)
            
#             child_positions = []
#             for i in range(n_vessels):
#                 alpha = random.random()
#                 pos = alpha * positions1[i] + (1 - alpha) * positions2[i]
#                 child_positions.append(pos)
            
#             return child_order, child_positions
        
#         def mutate(individual, mutation_rate=0.15):
#             order, positions = individual
            
#             if random.random() < mutation_rate:
#                 i, j = random.sample(range(n_vessels), 2)
#                 order[i], order[j] = order[j], order[i]
            
#             if random.random() < mutation_rate:
#                 idx = random.randint(0, n_vessels - 1)
#                 max_pos = berth_length - vessel_lengths[order[idx]]
#                 # ML-guided mutation
#                 if random.random() < 0.7:  # 70% chance of ML-guided mutation
#                     ideal_pos = eta_hours[order[idx]] * 50
#                     new_pos = ideal_pos + random.uniform(-30, 30)
#                 else:
#                     new_pos = random.uniform(0, max_pos)
#                 positions[idx] = max(0, min(new_pos, max_pos))
            
#             return order, positions
        
#         # GA main loop with ML initialization
#         population = [create_ml_individual() for _ in range(pop_size)]
#         best_fitness = float('inf')
#         best_individual = None
        
#         for generation in range(generations):
#             fitness_scores = [fitness(ind) for ind in population]
            
#             current_best = min(fitness_scores)
#             if current_best < best_fitness:
#                 best_fitness = current_best
#                 best_individual = population[fitness_scores.index(current_best)]
            
#             # Tournament selection
#             new_population = []
#             for _ in range(pop_size):
#                 tournament_indices = random.sample(range(len(population)), 3)
#                 tournament_scores = [fitness_scores[i] for i in tournament_indices]
#                 best_idx = tournament_indices[np.argmin(tournament_scores)]
#                 new_population.append(population[best_idx])
            
#             # Crossover and mutation
#             population = []
#             for i in range(0, len(new_population), 2):
#                 if i + 1 < len(new_population):
#                     parent1 = new_population[i]
#                     parent2 = new_population[i + 1]
                    
#                     child1 = crossover(parent1, parent2)
#                     child2 = crossover(parent2, parent1)
                    
#                     child1 = mutate(child1)
#                     child2 = mutate(child2)
                    
#                     population.extend([child1, child2])
#                 else:
#                     population.append(new_population[i])
        
#         # Convert result
#         if best_individual and best_fitness < float('inf'):
#             order, positions = best_individual
#             allocations = []
            
#             for i in range(n_vessels):
#                 vessel_idx = order[i]
#                 start_pos = positions[i]
#                 start_time = start_pos / conversion_factor
#                 delay = max(0, start_time - eta_hours[vessel_idx])
                
#                 allocations.append({
#                     "name": vessels[vessel_idx]["name"],
#                     "type": vessels[vessel_idx]["type"],
#                     "length": vessels[vessel_idx]["length"],
#                     "eta": vessels[vessel_idx]["eta"],
#                     "etd": vessels[vessel_idx]["etd"],
#                     "eta_hour": vessels[vessel_idx]["eta_hour"],
#                     "start": start_pos,
#                     "end": start_pos + vessels[vessel_idx]["length"],
#                     "delay": delay
#                 })
            
#             return allocations
        
#         return []
    
#     except Exception as e:
#         st.error(f"ML-GA Error: {str(e)}")
#         return []

# # -----------------------------
# # 5. HEURISTIC ALGORITHM (Instead of RL for stability)
# # -----------------------------
# def heuristic_berth_allocation(vessels, berth_length):
#     """Heuristic algorithm based on ETA and vessel characteristics"""
#     try:
#         # Sort vessels by ETA (earliest first)
#         sorted_vessels = sorted(vessels, key=lambda x: x["eta_hour"])
        
#         allocations = []
#         used_positions = []  # Track (start, end) positions
        
#         for vessel in sorted_vessels:
#             ideal_position = vessel["eta_hour"] * 50
#             vessel_length = vessel["length"]
            
#             # Find earliest available position
#             position_found = False
#             candidate_position = 0
            
#             while not position_found and candidate_position <= berth_length - vessel_length:
#                 # Check if this position overlaps with any existing vessel
#                 overlaps = False
#                 for used_start, used_end in used_positions:
#                     if (candidate_position < used_end and candidate_position + vessel_length > used_start):
#                         overlaps = True
#                         break
                
#                 if not overlaps:
#                     # Position is available
#                     start_pos = candidate_position
#                     end_pos = start_pos + vessel_length
                    
#                     # Calculate delay
#                     start_time = start_pos / 50
#                     delay = max(0, start_time - vessel["eta_hour"])
                    
#                     allocations.append({
#                         "name": vessel["name"],
#                         "type": vessel["type"],
#                         "length": vessel["length"],
#                         "eta": vessel["eta"],
#                         "etd": vessel["etd"],
#                         "eta_hour": vessel["eta_hour"],
#                         "start": start_pos,
#                         "end": end_pos,
#                         "delay": delay
#                     })
                    
#                     used_positions.append((start_pos, end_pos))
#                     position_found = True
#                 else:
#                     # Try next position (with some gap)
#                     candidate_position += 5
            
#             if not position_found:
#                 # If no position found, try to place at the end
#                 if used_positions:
#                     last_position = max(used_positions, key=lambda x: x[1])[1]
#                     start_pos = last_position + 1
#                 else:
#                     start_pos = 0
                
#                 if start_pos + vessel_length <= berth_length:
#                     end_pos = start_pos + vessel_length
#                     start_time = start_pos / 50
#                     delay = max(0, start_time - vessel["eta_hour"])
                    
#                     allocations.append({
#                         "name": vessel["name"],
#                         "type": vessel["type"],
#                         "length": vessel["length"],
#                         "eta": vessel["eta"],
#                         "etd": vessel["etd"],
#                         "eta_hour": vessel["eta_hour"],
#                         "start": start_pos,
#                         "end": end_pos,
#                         "delay": delay
#                     })
                    
#                     used_positions.append((start_pos, end_pos))
        
#         return allocations
    
#     except Exception as e:
#         st.error(f"Heuristic Error: {str(e)}")
#         return []

# # -----------------------------
# # HELPER FUNCTIONS
# # -----------------------------
# def generate_random_vessels(num_vessels):
#     """Generate random vessel data"""
#     vessel_types = ["Container", "Bulk", "Tanker", "RORO", "Passenger"]
#     vessels = []
    
#     for i in range(num_vessels):
#         vtype = random.choice(vessel_types)
#         length_ranges = {
#             "Container": (100, 300), "Bulk": (150, 250),
#             "Tanker": (200, 350), "RORO": (80, 180), "Passenger": (50, 150)
#         }
#         min_len, max_len = length_ranges.get(vtype, (50, 200))
#         length = random.randint(min_len, max_len)
#         eta_hour = random.randint(0, 18)
#         etd_hour = min(eta_hour + random.randint(4, 8), 23)
        
#         vessels.append({
#             "name": f"Vessel_{i+1:02d}", "type": vtype, "length": length,
#             "eta": f"{eta_hour:02d}:00", "etd": f"{etd_hour:02d}:00", "eta_hour": eta_hour
#         })
    
#     return vessels

# def plot_berth_allocation(allocations, berth_length, algorithm_name):
#     """Visualize berth allocation"""
#     if not allocations:
#         st.warning("No allocation data to visualize")
#         return
        
#     fig, ax = plt.subplots(figsize=(12, 6))
#     ax.set_xlim(0, berth_length)
#     ax.set_ylim(0, len(allocations) * 3 + 5)
#     ax.set_title(f"Berth Allocation - {algorithm_name}", fontsize=14)
#     ax.set_xlabel("Berth Position (meters)")
#     ax.set_ylabel("Vessel Position")
    
#     # Draw berth line
#     ax.hlines(1, 0, berth_length, colors='blue', linewidth=4, label='Berth Line')
#     ax.grid(True, alpha=0.3)
    
#     vessel_colors = {
#         "Container": "#FF6B6B", "Bulk": "#4ECDC4", "Tanker": "#FFD166",
#         "RORO": "#9D4EDD", "Passenger": "#06D6A0"
#     }
    
#     # Plot vessels
#     for idx, alloc in enumerate(allocations):
#         start, end = alloc['start'], alloc['end']
#         y_pos = 5 + idx * 2.5
#         color = vessel_colors.get(alloc['type'], "#118AB2")
        
#         rect = plt.Rectangle((start, y_pos - 0.5), end-start, 1.0,
#                            color=color, alpha=0.8, edgecolor='black', linewidth=1)
#         ax.add_patch(rect)
        
#         mid_x = (start + end) / 2
#         ax.text(mid_x, y_pos + 0.6, f"{alloc['name']}", 
#                 ha='center', va='bottom', fontsize=8, weight='bold')
        
#         delay_text = f"Delay: {alloc['delay']:.1f}h" if alloc['delay'] > 0.1 else "On time"
#         delay_color = 'red' if alloc['delay'] > 0.1 else 'green'
#         ax.text(mid_x, y_pos - 0.8, f"{delay_text}", 
#                 ha='center', va='top', fontsize=7, color=delay_color)
    
#     ax.text(berth_length/2, 0.3, f"Total Berth: {berth_length}m", 
#             ha='center', va='bottom', fontsize=10, weight='bold', color='blue')
    
#     plt.tight_layout()
#     st.pyplot(fig)

# # -----------------------------
# # STREAMLIT APP
# # -----------------------------
# def main():
#     st.set_page_config(page_title="Berth Allocation - 5 Algorithms", layout="wide")
#     st.title("🚢 Berth Allocation Optimization - 5 Algorithm Comparison")
#     st.markdown("---")
    
#     # Sidebar
#     st.sidebar.header("⚙️ Simulation Settings")
#     num_vessels = st.sidebar.slider("Number of Vessels", 3, 8, 5)
#     berth_length = st.sidebar.slider("Total Berth Length (meters)", 500, 1500, 1000, 100)
    
#     algorithm_choice = st.sidebar.radio(
#         "Run Mode:",
#         ["Single Algorithm", "Compare All Algorithms"]
#     )
    
#     if algorithm_choice == "Single Algorithm":
#         selected_algorithm = st.sidebar.selectbox(
#             "Select Algorithm:",
#             ["MILP (PuLP)", "Genetic Algorithm", "Simulated Annealing", 
#              "ML-Enhanced GA", "Heuristic Algorithm"]
#         )
    
#     st.sidebar.markdown("---")
#     st.sidebar.info("""
#     **Algorithms:**
#     - **MILP**: Exact optimization
#     - **GA**: Evolutionary search
#     - **SA**: Probabilistic optimization  
#     - **ML-GA**: GA with ML guidance
#     - **Heuristic**: Rule-based approach
#     """)
    
#     # Main content
#     if st.button("🎲 Generate & Optimize", type="primary"):
#         with st.spinner("Generating vessels and running optimization..."):
#             vessels = generate_random_vessels(num_vessels)
            
#             st.subheader("📋 Generated Vessel Data")
#             display_vessels = []
#             for v in vessels:
#                 display_vessels.append({
#                     "Vessel": v["name"], "Type": v["type"], 
#                     "Length (m)": v["length"], "ETA": v["eta"], "ETD": v["etd"]
#                 })
#             st.dataframe(display_vessels, use_container_width=True)
            
#             if algorithm_choice == "Single Algorithm":
#                 # Run single algorithm
#                 start_time = time.time()
                
#                 if selected_algorithm == "MILP (PuLP)":
#                     allocations = milp_berth_allocation(vessels, berth_length)
#                 elif selected_algorithm == "Genetic Algorithm":
#                     allocations = genetic_algorithm_berth(vessels, berth_length)
#                 elif selected_algorithm == "Simulated Annealing":
#                     allocations = simulated_annealing_berth(vessels, berth_length)
#                 elif selected_algorithm == "ML-Enhanced GA":
#                     allocations = ml_enhanced_ga_berth(vessels, berth_length)
#                 else:  # Heuristic Algorithm
#                     allocations = heuristic_berth_allocation(vessels, berth_length)
                
#                 computation_time = time.time() - start_time
                
#                 if allocations:
#                     st.success(f"✅ {selected_algorithm} completed in {computation_time:.2f}s!")
#                     display_single_results(allocations, berth_length, selected_algorithm, computation_time)
#                 else:
#                     st.error("❌ No feasible solution found.")
                    
#             else:  # Compare all algorithms
#                 results = compare_all_algorithms(vessels, berth_length)
#                 display_comparison_results(results, berth_length)

# def compare_all_algorithms(vessels, berth_length):
#     """Run all 5 algorithms and compare results"""
#     results = {}
#     algorithms = {
#         "MILP (PuLP)": milp_berth_allocation,
#         "Genetic Algorithm": genetic_algorithm_berth,
#         "Simulated Annealing": simulated_annealing_berth,
#         "ML-Enhanced GA": ml_enhanced_ga_berth,
#         "Heuristic Algorithm": heuristic_berth_allocation
#     }
    
#     for algo_name, algo_func in algorithms.items():
#         with st.spinner(f"Running {algo_name}..."):
#             start_time = time.time()
#             allocations = algo_func(vessels, berth_length)
#             computation_time = time.time() - start_time
            
#             if allocations and len(allocations) == len(vessels):
#                 total_delay = sum(a["delay"] for a in allocations)
#                 utilization = (sum(a["length"] for a in allocations) / berth_length) * 100
#                 feasible = True
#             else:
#                 total_delay = float('inf')
#                 utilization = 0
#                 feasible = False
            
#             results[algo_name] = {
#                 "allocations": allocations,
#                 "computation_time": computation_time,
#                 "total_delay": total_delay,
#                 "utilization": utilization,
#                 "feasible": feasible
#             }
    
#     return results

# def display_single_results(allocations, berth_length, algorithm_name, computation_time):
#     """Display results for single algorithm"""
#     st.subheader(f"📈 {algorithm_name} Results")
    
#     results_df = []
#     for alloc in allocations:
#         results_df.append({
#             "Vessel": alloc["name"], "Type": alloc["type"],
#             "Length": f"{alloc['length']}m", "ETA": alloc["eta"],
#             "Start Pos": f"{alloc['start']:.0f}m", "End Pos": f"{alloc['end']:.0f}m",
#             "Delay": f"{alloc['delay']:.2f}h"
#         })
#     st.dataframe(results_df, use_container_width=True)
    
#     # Visualization
#     st.subheader("📊 Berth Allocation Visualization")
#     plot_berth_allocation(allocations, berth_length, algorithm_name)
    
#     # Summary
#     st.subheader("📊 Performance Summary")
#     col1, col2, col3, col4 = st.columns(4)
    
#     total_used = sum(alloc["length"] for alloc in allocations)
#     utilization = (total_used / berth_length) * 100
#     total_delay = sum(alloc["delay"] for alloc in allocations)
#     avg_delay = total_delay / len(allocations)
    
#     with col1:
#         st.metric("Berth Utilization", f"{utilization:.1f}%")
#     with col2:
#         st.metric("Total Delay", f"{total_delay:.1f} hours")
#     with col3:
#         st.metric("Average Delay", f"{avg_delay:.1f} hours")
#     with col4:
#         st.metric("Computation Time", f"{computation_time:.2f}s")

# def display_comparison_results(results, berth_length):
#     """Display comparison of all algorithms"""
#     st.subheader("📊 Algorithm Comparison Results")
    
#     # Comparison table
#     comparison_data = []
#     for algo_name, result in results.items():
#         comparison_data.append({
#             "Algorithm": algo_name,
#             "Total Delay (hours)": f"{result['total_delay']:.2f}" if result['feasible'] else "N/A",
#             "Computation Time (s)": f"{result['computation_time']:.3f}",
#             "Berth Utilization": f"{result['utilization']:.1f}%" if result['feasible'] else "N/A",
#             "Feasible": "✅" if result['feasible'] else "❌"
#         })
    
#     st.dataframe(comparison_data, use_container_width=True)
    
#     # Find best algorithm
#     feasible_results = {k: v for k, v in results.items() if v['feasible']}
#     if feasible_results:
#         best_algo = min(feasible_results.keys(), key=lambda x: feasible_results[x]['total_delay'])
#         best_result = feasible_results[best_algo]
        
#         st.success(f"🏆 Best Algorithm: {best_algo} "
#                   f"(Delay: {best_result['total_delay']:.2f}h, "
#                   f"Time: {best_result['computation_time']:.2f}s)")
        
#         # Show visualization for best algorithm
#         st.subheader(f"📊 Best Allocation Visualization ({best_algo})")
#         plot_berth_allocation(best_result["allocations"], berth_length, best_algo)

# if __name__ == "__main__":
#     main()
    
# import streamlit as st
# import matplotlib.pyplot as plt
# import numpy as np
# import random
# from pulp import LpProblem, LpVariable, LpMinimize, lpSum, LpStatus, value
# import time

# # -----------------------------
# # GENETIC ALGORITHM
# # -----------------------------
# def genetic_algorithm_berth(vessels, berth_length, pop_size=50, generations=100, mutation_rate=0.1):
#     """
#     Genetic Algorithm for Berth Allocation
#     """
#     n_vessels = len(vessels)
#     vessel_lengths = [v["length"] for v in vessels]
#     eta_hours = [v["eta_hour"] for v in vessels]
    
#     def create_individual():
#         # Create random permutation of vessels
#         order = random.sample(range(n_vessels), n_vessels)
#         positions = []
        
#         # Assign positions sequentially without overlap
#         current_pos = 0
#         for idx in order:
#             vessel_idx = order[idx]
#             max_pos = berth_length - vessel_lengths[vessel_idx]
#             # Try to place vessel at a random position that fits
#             pos = random.uniform(0, max(0, max_pos - current_pos)) + current_pos
#             positions.append(pos)
#             current_pos = pos + vessel_lengths[vessel_idx] + random.uniform(1, 10)  # Small gap
        
#         return order, positions
    
#     def fitness(individual):
#         order, positions = individual
#         total_delay = 0
#         conversion_factor = 50
        
#         # Check constraints
#         for i in range(n_vessels):
#             vessel_idx = order[i]
#             pos = positions[i]
#             length = vessel_lengths[vessel_idx]
            
#             # Check if vessel fits within berth
#             if pos + length > berth_length:
#                 return float('inf')
            
#             # Check overlaps
#             for j in range(i + 1, n_vessels):
#                 other_idx = order[j]
#                 other_pos = positions[j]
#                 other_length = vessel_lengths[other_idx]
                
#                 if (pos < other_pos + other_length and pos + length > other_pos):
#                     return float('inf')
            
#             # Calculate delay
#             start_time = pos / conversion_factor
#             delay = max(0, start_time - eta_hours[vessel_idx])
#             total_delay += delay
        
#         return total_delay
    
#     def crossover(parent1, parent2):
#         order1, positions1 = parent1
#         order2, positions2 = parent2
        
#         # Order crossover
#         crossover_point = random.randint(1, n_vessels - 1)
#         child_order = order1[:crossover_point]
        
#         # Add missing vessels from parent2
#         for vessel in order2:
#             if vessel not in child_order:
#                 child_order.append(vessel)
        
#         # Position crossover (average)
#         child_positions = []
#         for i in range(n_vessels):
#             pos = (positions1[i] + positions2[i]) / 2
#             child_positions.append(pos)
        
#         return child_order, child_positions
    
#     def mutate(individual):
#         order, positions = individual
        
#         if random.random() < mutation_rate:
#             # Swap two vessels
#             i, j = random.sample(range(n_vessels), 2)
#             order[i], order[j] = order[j], order[i]
        
#         if random.random() < mutation_rate:
#             # Mutate a position
#             idx = random.randint(0, n_vessels - 1)
#             max_pos = berth_length - vessel_lengths[order[idx]]
#             positions[idx] = random.uniform(0, max_pos)
        
#         return order, positions
    
#     # Initialize population
#     population = [create_individual() for _ in range(pop_size)]
    
#     best_fitness = float('inf')
#     best_individual = None
    
#     for generation in range(generations):
#         # Evaluate fitness
#         fitness_scores = [fitness(ind) for ind in population]
        
#         # Find best
#         current_best = min(fitness_scores)
#         if current_best < best_fitness:
#             best_fitness = current_best
#             best_individual = population[fitness_scores.index(current_best)]
        
#         # Selection (tournament selection)
#         new_population = []
#         for _ in range(pop_size):
#             # Tournament selection
#             tournament = random.sample(list(zip(population, fitness_scores)), 3)
#             winner = min(tournament, key=lambda x: x[1])[0]
#             new_population.append(winner)
        
#         # Crossover and mutation
#         population = []
#         for i in range(0, pop_size, 2):
#             parent1 = new_population[i]
#             parent2 = new_population[(i + 1) % pop_size]
            
#             child1 = crossover(parent1, parent2)
#             child2 = crossover(parent2, parent1)
            
#             child1 = mutate(child1)
#             child2 = mutate(child2)
            
#             population.extend([child1, child2])
    
#     # Convert best solution to allocation format
#     if best_individual and best_fitness != float('inf'):
#         order, positions = best_individual
#         allocations = []
#         conversion_factor = 50
        
#         for i in range(n_vessels):
#             vessel_idx = order[i]
#             start_pos = positions[i]
#             start_time = start_pos / conversion_factor
#             delay = max(0, start_time - eta_hours[vessel_idx])
            
#             allocations.append({
#                 "name": vessels[vessel_idx]["name"],
#                 "type": vessels[vessel_idx]["type"],
#                 "length": vessels[vessel_idx]["length"],
#                 "eta": vessels[vessel_idx]["eta"],
#                 "etd": vessels[vessel_idx]["etd"],
#                 "eta_hour": vessels[vessel_idx]["eta_hour"],
#                 "start": start_pos,
#                 "end": start_pos + vessels[vessel_idx]["length"],
#                 "delay": delay
#             })
        
#         return allocations
#     else:
#         return []

# # -----------------------------
# # SIMULATED ANNEALING
# # -----------------------------
# def simulated_annealing_berth(vessels, berth_length, initial_temp=1000, cooling_rate=0.95, iterations=1000):
#     """
#     Simulated Annealing for Berth Allocation
#     """
#     n_vessels = len(vessels)
#     vessel_lengths = [v["length"] for v in vessels]
#     eta_hours = [v["eta_hour"] for v in vessels]
#     conversion_factor = 50
    
#     def create_solution():
#         # Create random order and positions
#         order = list(range(n_vessels))
#         random.shuffle(order)
        
#         positions = []
#         for i in range(n_vessels):
#             max_pos = berth_length - vessel_lengths[order[i]]
#             positions.append(random.uniform(0, max_pos))
        
#         return order, positions
    
#     def calculate_cost(order, positions):
#         total_delay = 0
        
#         # Check berth capacity
#         for i in range(n_vessels):
#             if positions[i] + vessel_lengths[order[i]] > berth_length:
#                 return float('inf')
        
#         # Check overlaps
#         for i in range(n_vessels):
#             for j in range(i + 1, n_vessels):
#                 pos1, len1 = positions[i], vessel_lengths[order[i]]
#                 pos2, len2 = positions[j], vessel_lengths[order[j]]
                
#                 if (pos1 < pos2 + len2 and pos1 + len1 > pos2):
#                     return float('inf')
        
#         # Calculate delays
#         for i in range(n_vessels):
#             start_time = positions[i] / conversion_factor
#             delay = max(0, start_time - eta_hours[order[i]])
#             total_delay += delay
        
#         return total_delay
    
#     def get_neighbor(current_order, current_positions):
#         new_order = current_order.copy()
#         new_positions = current_positions.copy()
        
#         # Choose mutation type
#         mutation_type = random.choice(['swap', 'position', 'both'])
        
#         if mutation_type in ['swap', 'both']:
#             # Swap two vessels
#             i, j = random.sample(range(n_vessels), 2)
#             new_order[i], new_order[j] = new_order[j], new_order[i]
        
#         if mutation_type in ['position', 'both']:
#             # Change a position
#             idx = random.randint(0, n_vessels - 1)
#             max_pos = berth_length - vessel_lengths[new_order[idx]]
#             new_positions[idx] = random.uniform(0, max_pos)
        
#         return new_order, new_positions
    
#     # Initialize
#     current_order, current_positions = create_solution()
#     current_cost = calculate_cost(current_order, current_positions)
#     best_order, best_positions = current_order.copy(), current_positions.copy()
#     best_cost = current_cost
    
#     temperature = initial_temp
    
#     for iteration in range(iterations):
#         # Generate neighbor
#         new_order, new_positions = get_neighbor(current_order, current_positions)
#         new_cost = calculate_cost(new_order, new_positions)
        
#         # Acceptance criterion
#         if new_cost < current_cost or random.random() < np.exp((current_cost - new_cost) / temperature):
#             current_order, current_positions = new_order, new_positions
#             current_cost = new_cost
            
#             if new_cost < best_cost:
#                 best_order, best_positions = new_order.copy(), new_positions.copy()
#                 best_cost = new_cost
        
#         # Cool down
#         temperature *= cooling_rate
    
#     # Convert to allocation format
#     if best_cost != float('inf'):
#         allocations = []
#         for i in range(n_vessels):
#             vessel_idx = best_order[i]
#             start_pos = best_positions[i]
#             start_time = start_pos / conversion_factor
#             delay = max(0, start_time - eta_hours[vessel_idx])
            
#             allocations.append({
#                 "name": vessels[vessel_idx]["name"],
#                 "type": vessels[vessel_idx]["type"],
#                 "length": vessels[vessel_idx]["length"],
#                 "eta": vessels[vessel_idx]["eta"],
#                 "etd": vessels[vessel_idx]["etd"],
#                 "eta_hour": vessels[vessel_idx]["eta_hour"],
#                 "start": start_pos,
#                 "end": start_pos + vessels[vessel_idx]["length"],
#                 "delay": delay
#             })
        
#         return allocations
#     else:
#         return []

# # -----------------------------
# # EXISTING OPTIMIZATION MODELS
# # -----------------------------
# def simple_berth_allocation(vessels, berth_length):
#     """PuLP Simple Model"""
#     try:
#         model = LpProblem("Simple_Berth_Allocation", LpMinimize)
#         start = {v["name"]: LpVariable(f"start_{v['name']}", lowBound=0, upBound=berth_length - v["length"]) for v in vessels}
        
#         model += lpSum(start[v["name"]] for v in vessels)

#         for i, vi in enumerate(vessels):
#             li = vi["length"]
#             model += start[vi["name"]] + li <= berth_length

#         for i, vi in enumerate(vessels):
#             for j, vj in enumerate(vessels):
#                 if i < j:
#                     li, lj = vi["length"], vj["length"]
#                     M = berth_length * 2
#                     y_ij = LpVariable(f"y_{vi['name']}_{vj['name']}", cat="Binary")
#                     model += start[vi["name"]] + li <= start[vj["name"]] + M * (1 - y_ij)
#                     model += start[vj["name"]] + lj <= start[vi["name"]] + M * y_ij

#         model.solve()

#         if LpStatus[model.status] != "Optimal":
#             return []

#         allocations = []
#         for v in vessels:
#             start_pos = value(start[v["name"]])
#             ideal_position = v["eta_hour"] * 50
#             delay = max(0, (start_pos - ideal_position) / 50)
            
#             allocations.append({
#                 "name": v["name"], "type": v["type"], "length": v["length"],
#                 "eta": v["eta"], "etd": v["etd"], "eta_hour": v["eta_hour"],
#                 "start": start_pos, "end": start_pos + v["length"], "delay": delay
#             })
        
#         return allocations
    
#     except Exception as e:
#         st.error(f"Error in simple optimization: {str(e)}")
#         return []

# # -----------------------------
# # COMPARISON FUNCTION
# # -----------------------------
# def compare_algorithms(vessels, berth_length):
#     """Run all algorithms and compare results"""
#     results = {}
    
#     # PuLP Simple Model
#     start_time = time.time()
#     pulp_result = simple_berth_allocation(vessels, berth_length)
#     pulp_time = time.time() - start_time
#     results["PuLP"] = {
#         "allocations": pulp_result,
#         "time": pulp_time,
#         "total_delay": sum(a["delay"] for a in pulp_result) if pulp_result else float('inf')
#     }
    
#     # Genetic Algorithm
#     start_time = time.time()
#     ga_result = genetic_algorithm_berth(vessels, berth_length, pop_size=30, generations=50)
#     ga_time = time.time() - start_time
#     results["Genetic Algorithm"] = {
#         "allocations": ga_result,
#         "time": ga_time,
#         "total_delay": sum(a["delay"] for a in ga_result) if ga_result else float('inf')
#     }
    
#     # Simulated Annealing
#     start_time = time.time()
#     sa_result = simulated_annealing_berth(vessels, berth_length, iterations=500)
#     sa_time = time.time() - start_time
#     results["Simulated Annealing"] = {
#         "allocations": sa_result,
#         "time": sa_time,
#         "total_delay": sum(a["delay"] for a in sa_result) if sa_result else float('inf')
#     }
    
#     return results

# # -----------------------------
# # STREAMLIT UI
# # -----------------------------
# def main():
#     st.set_page_config(page_title="Berth Allocation - Multi-Algorithm", layout="wide")
#     st.title("🚢 Berth Allocation Optimization - Multi-Algorithm Comparison")
#     st.markdown("---")
    
#     # Sidebar
#     st.sidebar.header("⚙️ Simulation Settings")
#     num_vessels = st.sidebar.slider("Number of Vessels", 3, 10, 5)
#     berth_length = st.sidebar.slider("Total Berth Length (meters)", 500, 2000, 1000, 100)
    
#     algorithm_choice = st.sidebar.radio(
#         "Choose Algorithm:",
#         ["Single Algorithm", "Compare All Algorithms"],
#         help="Single: Run one algorithm, Compare: Run all and compare results"
#     )
    
#     if algorithm_choice == "Single Algorithm":
#         selected_algorithm = st.sidebar.selectbox(
#             "Select Algorithm:",
#             ["PuLP Simple Model", "Genetic Algorithm", "Simulated Annealing"]
#         )
    
#     st.sidebar.markdown("---")
#     st.sidebar.info("""
#     **Algorithms:**
#     - **PuLP**: Exact MILP solver
#     - **Genetic Algorithm**: Evolutionary approach
#     - **Simulated Annealing**: Probabilistic optimization
#     """)
    
#     # Main content
#     if st.button("🎲 Generate & Optimize", type="primary"):
#         with st.spinner("Generating vessels and running optimization..."):
#             vessels = generate_random_vessels(num_vessels)
            
#             st.subheader("📋 Generated Vessel Data")
#             display_vessels = []
#             for v in vessels:
#                 display_vessels.append({
#                     "Vessel": v["name"], "Type": v["type"], 
#                     "Length (m)": v["length"], "ETA": v["eta"], "ETD": v["etd"]
#                 })
#             st.dataframe(display_vessels, use_container_width=True)
            
#             if algorithm_choice == "Single Algorithm":
#                 # Run single algorithm
#                 if selected_algorithm == "PuLP Simple Model":
#                     allocations = simple_berth_allocation(vessels, berth_length)
#                     algorithm_name = "PuLP Simple Model"
#                 elif selected_algorithm == "Genetic Algorithm":
#                     allocations = genetic_algorithm_berth(vessels, berth_length)
#                     algorithm_name = "Genetic Algorithm"
#                 else:  # Simulated Annealing
#                     allocations = simulated_annealing_berth(vessels, berth_length)
#                     algorithm_name = "Simulated Annealing"
                
#                 if allocations:
#                     st.success(f"✅ {algorithm_name} completed successfully!")
#                     display_single_results(allocations, berth_length, algorithm_name)
#                 else:
#                     st.error("❌ No feasible solution found.")
                    
#             else:  # Compare all algorithms
#                 results = compare_algorithms(vessels, berth_length)
#                 display_comparison_results(results, berth_length)

# def display_single_results(allocations, berth_length, algorithm_name):
#     """Display results for single algorithm"""
#     st.subheader(f"📈 {algorithm_name} Results")
    
#     results_df = []
#     for alloc in allocations:
#         results_df.append({
#             "Vessel": alloc["name"], "Type": alloc["type"],
#             "Length": f"{alloc['length']}m", "ETA": alloc["eta"],
#             "Start Pos": f"{alloc['start']:.0f}m", "End Pos": f"{alloc['end']:.0f}m",
#             "Delay": f"{alloc['delay']:.2f}h"
#         })
#     st.dataframe(results_df, use_container_width=True)
    
#     # Visualization
#     st.subheader("📊 Berth Allocation Visualization")
#     plot_berth_allocation(allocations, berth_length)
    
#     # Summary
#     st.subheader("📊 Performance Summary")
#     col1, col2, col3 = st.columns(3)
    
#     total_used = sum(alloc["length"] for alloc in allocations)
#     utilization = (total_used / berth_length) * 100
#     total_delay = sum(alloc["delay"] for alloc in allocations)
#     avg_delay = total_delay / len(allocations)
    
#     with col1:
#         st.metric("Berth Utilization", f"{utilization:.1f}%")
#     with col2:
#         st.metric("Total Delay", f"{total_delay:.1f} hours")
#     with col3:
#         st.metric("Average Delay", f"{avg_delay:.1f} hours")

# def display_comparison_results(results, berth_length):
#     """Display comparison of all algorithms"""
#     st.subheader("📊 Algorithm Comparison Results")
    
#     # Comparison table
#     comparison_data = []
#     for algo_name, result in results.items():
#         if result["allocations"]:
#             total_delay = result["total_delay"]
#             utilization = (sum(a["length"] for a in result["allocations"]) / berth_length) * 100
#         else:
#             total_delay = "N/A"
#             utilization = "N/A"
        
#         comparison_data.append({
#             "Algorithm": algo_name,
#             "Total Delay (hours)": f"{total_delay:.2f}" if isinstance(total_delay, float) else total_delay,
#             "Computation Time (s)": f"{result['time']:.3f}",
#             "Berth Utilization": f"{utilization:.1f}%" if isinstance(utilization, float) else utilization,
#             "Feasible": "✅" if result["allocations"] else "❌"
#         })
    
#     st.dataframe(comparison_data, use_container_width=True)
    
#     # Find best algorithm
#     feasible_results = {k: v for k, v in results.items() if v["allocations"]}
#     if feasible_results:
#         best_algo = min(feasible_results.keys(), key=lambda x: feasible_results[x]["total_delay"])
#         st.success(f"🏆 Best Algorithm: {best_algo} (Total Delay: {feasible_results[best_algo]['total_delay']:.2f} hours)")
        
#         # Show visualization for best algorithm
#         st.subheader(f"📊 Best Allocation Visualization ({best_algo})")
#         plot_berth_allocation(feasible_results[best_algo]["allocations"], berth_length)
    
#     # Show individual results in expanders
#     for algo_name, result in results.items():
#         if result["allocations"]:
#             with st.expander(f"View {algo_name} Detailed Results"):
#                 display_single_results(result["allocations"], berth_length, algo_name)

# # -----------------------------
# # EXISTING HELPER FUNCTIONS
# # -----------------------------
# def generate_random_vessels(num_vessels):
#     vessel_types = ["Container", "Bulk", "Tanker", "RORO", "Passenger"]
#     vessels = []
    
#     for i in range(num_vessels):
#         vtype = random.choice(vessel_types)
#         length_ranges = {
#             "Container": (100, 300), "Bulk": (150, 250),
#             "Tanker": (200, 350), "RORO": (80, 180), "Passenger": (50, 150)
#         }
#         min_len, max_len = length_ranges.get(vtype, (50, 200))
#         length = random.randint(min_len, max_len)
#         eta_hour = random.randint(0, 18)
#         etd_hour = min(eta_hour + random.randint(4, 8), 23)
        
#         vessels.append({
#             "name": f"Vessel_{i+1:02d}", "type": vtype, "length": length,
#             "eta": f"{eta_hour:02d}:00", "etd": f"{etd_hour:02d}:00", "eta_hour": eta_hour
#         })
    
#     return vessels

# def plot_berth_allocation(allocations, berth_length):
#     if not allocations:
#         st.warning("No allocation data to visualize")
#         return
        
#     fig, ax = plt.subplots(figsize=(14, 8))
#     ax.set_xlim(0, berth_length)
#     ax.set_ylim(0, len(allocations) * 3 + 5)
#     ax.set_title("Berth Allocation Visualization", fontsize=16)
#     ax.set_xlabel("Berth Position (meters)")
#     ax.set_ylabel("Vessel Position")
    
#     # Draw berth line and grid
#     ax.hlines(1, 0, berth_length, colors='blue', linewidth=4, label='Berth Line')
#     ax.grid(True, alpha=0.3)
    
#     vessel_colors = {
#         "Container": "#FF6B6B", "Bulk": "#4ECDC4", "Tanker": "#FFD166",
#         "RORO": "#9D4EDD", "Passenger": "#06D6A0"
#     }
    
#     # Plot vessels
#     for idx, alloc in enumerate(allocations):
#         start, end = alloc["start"], alloc["end"]
#         y_pos = 5 + idx * 3
#         color = vessel_colors.get(alloc["type"], "#118AB2")
        
#         rect = plt.Rectangle((start, y_pos - 0.5), end-start, 1.0,
#                            color=color, alpha=0.8, edgecolor='black', linewidth=1.5)
#         ax.add_patch(rect)
        
#         mid_x = (start + end) / 2
#         ax.text(mid_x, y_pos + 0.8, f"{alloc['name']}\n({alloc['type']})", 
#                 ha='center', va='bottom', fontsize=9, weight='bold')
        
#         delay_text = f"Delay: {alloc['delay']:.1f}h" if alloc['delay'] > 0.1 else "On time"
#         delay_color = 'red' if alloc['delay'] > 0.1 else 'green'
#         ax.text(mid_x, y_pos - 1.0, 
#                 f"Pos: {start:.0f}-{end:.0f}m | {delay_text}", 
#                 ha='center', va='top', fontsize=8, color=delay_color)
    
#     ax.text(berth_length/2, 0.3, f"TOTAL BERTH LENGTH: {berth_length}m", 
#             ha='center', va='bottom', fontsize=12, weight='bold', color='blue',
#             bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.7))
    
#     plt.tight_layout()
#     st.pyplot(fig)

# if __name__ == "__main__":
#     main()



