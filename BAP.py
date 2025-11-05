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
import time

# -----------------------------
# GENETIC ALGORITHM
# -----------------------------
def genetic_algorithm_berth(vessels, berth_length, pop_size=50, generations=100, mutation_rate=0.1):
    """
    Genetic Algorithm for Berth Allocation
    """
    n_vessels = len(vessels)
    vessel_lengths = [v["length"] for v in vessels]
    eta_hours = [v["eta_hour"] for v in vessels]
    
    def create_individual():
        # Create random permutation of vessels
        order = random.sample(range(n_vessels), n_vessels)
        positions = []
        
        # Assign positions sequentially without overlap
        current_pos = 0
        for idx in order:
            vessel_idx = order[idx]
            max_pos = berth_length - vessel_lengths[vessel_idx]
            # Try to place vessel at a random position that fits
            pos = random.uniform(0, max(0, max_pos - current_pos)) + current_pos
            positions.append(pos)
            current_pos = pos + vessel_lengths[vessel_idx] + random.uniform(1, 10)  # Small gap
        
        return order, positions
    
    def fitness(individual):
        order, positions = individual
        total_delay = 0
        conversion_factor = 50
        
        # Check constraints
        for i in range(n_vessels):
            vessel_idx = order[i]
            pos = positions[i]
            length = vessel_lengths[vessel_idx]
            
            # Check if vessel fits within berth
            if pos + length > berth_length:
                return float('inf')
            
            # Check overlaps
            for j in range(i + 1, n_vessels):
                other_idx = order[j]
                other_pos = positions[j]
                other_length = vessel_lengths[other_idx]
                
                if (pos < other_pos + other_length and pos + length > other_pos):
                    return float('inf')
            
            # Calculate delay
            start_time = pos / conversion_factor
            delay = max(0, start_time - eta_hours[vessel_idx])
            total_delay += delay
        
        return total_delay
    
    def crossover(parent1, parent2):
        order1, positions1 = parent1
        order2, positions2 = parent2
        
        # Order crossover
        crossover_point = random.randint(1, n_vessels - 1)
        child_order = order1[:crossover_point]
        
        # Add missing vessels from parent2
        for vessel in order2:
            if vessel not in child_order:
                child_order.append(vessel)
        
        # Position crossover (average)
        child_positions = []
        for i in range(n_vessels):
            pos = (positions1[i] + positions2[i]) / 2
            child_positions.append(pos)
        
        return child_order, child_positions
    
    def mutate(individual):
        order, positions = individual
        
        if random.random() < mutation_rate:
            # Swap two vessels
            i, j = random.sample(range(n_vessels), 2)
            order[i], order[j] = order[j], order[i]
        
        if random.random() < mutation_rate:
            # Mutate a position
            idx = random.randint(0, n_vessels - 1)
            max_pos = berth_length - vessel_lengths[order[idx]]
            positions[idx] = random.uniform(0, max_pos)
        
        return order, positions
    
    # Initialize population
    population = [create_individual() for _ in range(pop_size)]
    
    best_fitness = float('inf')
    best_individual = None
    
    for generation in range(generations):
        # Evaluate fitness
        fitness_scores = [fitness(ind) for ind in population]
        
        # Find best
        current_best = min(fitness_scores)
        if current_best < best_fitness:
            best_fitness = current_best
            best_individual = population[fitness_scores.index(current_best)]
        
        # Selection (tournament selection)
        new_population = []
        for _ in range(pop_size):
            # Tournament selection
            tournament = random.sample(list(zip(population, fitness_scores)), 3)
            winner = min(tournament, key=lambda x: x[1])[0]
            new_population.append(winner)
        
        # Crossover and mutation
        population = []
        for i in range(0, pop_size, 2):
            parent1 = new_population[i]
            parent2 = new_population[(i + 1) % pop_size]
            
            child1 = crossover(parent1, parent2)
            child2 = crossover(parent2, parent1)
            
            child1 = mutate(child1)
            child2 = mutate(child2)
            
            population.extend([child1, child2])
    
    # Convert best solution to allocation format
    if best_individual and best_fitness != float('inf'):
        order, positions = best_individual
        allocations = []
        conversion_factor = 50
        
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
    else:
        return []

# -----------------------------
# SIMULATED ANNEALING
# -----------------------------
def simulated_annealing_berth(vessels, berth_length, initial_temp=1000, cooling_rate=0.95, iterations=1000):
    """
    Simulated Annealing for Berth Allocation
    """
    n_vessels = len(vessels)
    vessel_lengths = [v["length"] for v in vessels]
    eta_hours = [v["eta_hour"] for v in vessels]
    conversion_factor = 50
    
    def create_solution():
        # Create random order and positions
        order = list(range(n_vessels))
        random.shuffle(order)
        
        positions = []
        for i in range(n_vessels):
            max_pos = berth_length - vessel_lengths[order[i]]
            positions.append(random.uniform(0, max_pos))
        
        return order, positions
    
    def calculate_cost(order, positions):
        total_delay = 0
        
        # Check berth capacity
        for i in range(n_vessels):
            if positions[i] + vessel_lengths[order[i]] > berth_length:
                return float('inf')
        
        # Check overlaps
        for i in range(n_vessels):
            for j in range(i + 1, n_vessels):
                pos1, len1 = positions[i], vessel_lengths[order[i]]
                pos2, len2 = positions[j], vessel_lengths[order[j]]
                
                if (pos1 < pos2 + len2 and pos1 + len1 > pos2):
                    return float('inf')
        
        # Calculate delays
        for i in range(n_vessels):
            start_time = positions[i] / conversion_factor
            delay = max(0, start_time - eta_hours[order[i]])
            total_delay += delay
        
        return total_delay
    
    def get_neighbor(current_order, current_positions):
        new_order = current_order.copy()
        new_positions = current_positions.copy()
        
        # Choose mutation type
        mutation_type = random.choice(['swap', 'position', 'both'])
        
        if mutation_type in ['swap', 'both']:
            # Swap two vessels
            i, j = random.sample(range(n_vessels), 2)
            new_order[i], new_order[j] = new_order[j], new_order[i]
        
        if mutation_type in ['position', 'both']:
            # Change a position
            idx = random.randint(0, n_vessels - 1)
            max_pos = berth_length - vessel_lengths[new_order[idx]]
            new_positions[idx] = random.uniform(0, max_pos)
        
        return new_order, new_positions
    
    # Initialize
    current_order, current_positions = create_solution()
    current_cost = calculate_cost(current_order, current_positions)
    best_order, best_positions = current_order.copy(), current_positions.copy()
    best_cost = current_cost
    
    temperature = initial_temp
    
    for iteration in range(iterations):
        # Generate neighbor
        new_order, new_positions = get_neighbor(current_order, current_positions)
        new_cost = calculate_cost(new_order, new_positions)
        
        # Acceptance criterion
        if new_cost < current_cost or random.random() < np.exp((current_cost - new_cost) / temperature):
            current_order, current_positions = new_order, new_positions
            current_cost = new_cost
            
            if new_cost < best_cost:
                best_order, best_positions = new_order.copy(), new_positions.copy()
                best_cost = new_cost
        
        # Cool down
        temperature *= cooling_rate
    
    # Convert to allocation format
    if best_cost != float('inf'):
        allocations = []
        for i in range(n_vessels):
            vessel_idx = best_order[i]
            start_pos = best_positions[i]
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
    else:
        return []

# -----------------------------
# EXISTING OPTIMIZATION MODELS
# -----------------------------
def simple_berth_allocation(vessels, berth_length):
    """PuLP Simple Model"""
    try:
        model = LpProblem("Simple_Berth_Allocation", LpMinimize)
        start = {v["name"]: LpVariable(f"start_{v['name']}", lowBound=0, upBound=berth_length - v["length"]) for v in vessels}
        
        model += lpSum(start[v["name"]] for v in vessels)

        for i, vi in enumerate(vessels):
            li = vi["length"]
            model += start[vi["name"]] + li <= berth_length

        for i, vi in enumerate(vessels):
            for j, vj in enumerate(vessels):
                if i < j:
                    li, lj = vi["length"], vj["length"]
                    M = berth_length * 2
                    y_ij = LpVariable(f"y_{vi['name']}_{vj['name']}", cat="Binary")
                    model += start[vi["name"]] + li <= start[vj["name"]] + M * (1 - y_ij)
                    model += start[vj["name"]] + lj <= start[vi["name"]] + M * y_ij

        model.solve()

        if LpStatus[model.status] != "Optimal":
            return []

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
        st.error(f"Error in simple optimization: {str(e)}")
        return []

# -----------------------------
# COMPARISON FUNCTION
# -----------------------------
def compare_algorithms(vessels, berth_length):
    """Run all algorithms and compare results"""
    results = {}
    
    # PuLP Simple Model
    start_time = time.time()
    pulp_result = simple_berth_allocation(vessels, berth_length)
    pulp_time = time.time() - start_time
    results["PuLP"] = {
        "allocations": pulp_result,
        "time": pulp_time,
        "total_delay": sum(a["delay"] for a in pulp_result) if pulp_result else float('inf')
    }
    
    # Genetic Algorithm
    start_time = time.time()
    ga_result = genetic_algorithm_berth(vessels, berth_length, pop_size=30, generations=50)
    ga_time = time.time() - start_time
    results["Genetic Algorithm"] = {
        "allocations": ga_result,
        "time": ga_time,
        "total_delay": sum(a["delay"] for a in ga_result) if ga_result else float('inf')
    }
    
    # Simulated Annealing
    start_time = time.time()
    sa_result = simulated_annealing_berth(vessels, berth_length, iterations=500)
    sa_time = time.time() - start_time
    results["Simulated Annealing"] = {
        "allocations": sa_result,
        "time": sa_time,
        "total_delay": sum(a["delay"] for a in sa_result) if sa_result else float('inf')
    }
    
    return results

# -----------------------------
# STREAMLIT UI
# -----------------------------
def main():
    st.set_page_config(page_title="Berth Allocation - Multi-Algorithm", layout="wide")
    st.title("🚢 Berth Allocation Optimization - Multi-Algorithm Comparison")
    st.markdown("---")
    
    # Sidebar
    st.sidebar.header("⚙️ Simulation Settings")
    num_vessels = st.sidebar.slider("Number of Vessels", 3, 10, 5)
    berth_length = st.sidebar.slider("Total Berth Length (meters)", 500, 2000, 1000, 100)
    
    algorithm_choice = st.sidebar.radio(
        "Choose Algorithm:",
        ["Single Algorithm", "Compare All Algorithms"],
        help="Single: Run one algorithm, Compare: Run all and compare results"
    )
    
    if algorithm_choice == "Single Algorithm":
        selected_algorithm = st.sidebar.selectbox(
            "Select Algorithm:",
            ["PuLP Simple Model", "Genetic Algorithm", "Simulated Annealing"]
        )
    
    st.sidebar.markdown("---")
    st.sidebar.info("""
    **Algorithms:**
    - **PuLP**: Exact MILP solver
    - **Genetic Algorithm**: Evolutionary approach
    - **Simulated Annealing**: Probabilistic optimization
    """)
    
    # Main content
    if st.button("🎲 Generate & Optimize", type="primary"):
        with st.spinner("Generating vessels and running optimization..."):
            vessels = generate_random_vessels(num_vessels)
            
            st.subheader("📋 Generated Vessel Data")
            display_vessels = []
            for v in vessels:
                display_vessels.append({
                    "Vessel": v["name"], "Type": v["type"], 
                    "Length (m)": v["length"], "ETA": v["eta"], "ETD": v["etd"]
                })
            st.dataframe(display_vessels, use_container_width=True)
            
            if algorithm_choice == "Single Algorithm":
                # Run single algorithm
                if selected_algorithm == "PuLP Simple Model":
                    allocations = simple_berth_allocation(vessels, berth_length)
                    algorithm_name = "PuLP Simple Model"
                elif selected_algorithm == "Genetic Algorithm":
                    allocations = genetic_algorithm_berth(vessels, berth_length)
                    algorithm_name = "Genetic Algorithm"
                else:  # Simulated Annealing
                    allocations = simulated_annealing_berth(vessels, berth_length)
                    algorithm_name = "Simulated Annealing"
                
                if allocations:
                    st.success(f"✅ {algorithm_name} completed successfully!")
                    display_single_results(allocations, berth_length, algorithm_name)
                else:
                    st.error("❌ No feasible solution found.")
                    
            else:  # Compare all algorithms
                results = compare_algorithms(vessels, berth_length)
                display_comparison_results(results, berth_length)

def display_single_results(allocations, berth_length, algorithm_name):
    """Display results for single algorithm"""
    st.subheader(f"📈 {algorithm_name} Results")
    
    results_df = []
    for alloc in allocations:
        results_df.append({
            "Vessel": alloc["name"], "Type": alloc["type"],
            "Length": f"{alloc['length']}m", "ETA": alloc["eta"],
            "Start Pos": f"{alloc['start']:.0f}m", "End Pos": f"{alloc['end']:.0f}m",
            "Delay": f"{alloc['delay']:.2f}h"
        })
    st.dataframe(results_df, use_container_width=True)
    
    # Visualization
    st.subheader("📊 Berth Allocation Visualization")
    plot_berth_allocation(allocations, berth_length)
    
    # Summary
    st.subheader("📊 Performance Summary")
    col1, col2, col3 = st.columns(3)
    
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

def display_comparison_results(results, berth_length):
    """Display comparison of all algorithms"""
    st.subheader("📊 Algorithm Comparison Results")
    
    # Comparison table
    comparison_data = []
    for algo_name, result in results.items():
        if result["allocations"]:
            total_delay = result["total_delay"]
            utilization = (sum(a["length"] for a in result["allocations"]) / berth_length) * 100
        else:
            total_delay = "N/A"
            utilization = "N/A"
        
        comparison_data.append({
            "Algorithm": algo_name,
            "Total Delay (hours)": f"{total_delay:.2f}" if isinstance(total_delay, float) else total_delay,
            "Computation Time (s)": f"{result['time']:.3f}",
            "Berth Utilization": f"{utilization:.1f}%" if isinstance(utilization, float) else utilization,
            "Feasible": "✅" if result["allocations"] else "❌"
        })
    
    st.dataframe(comparison_data, use_container_width=True)
    
    # Find best algorithm
    feasible_results = {k: v for k, v in results.items() if v["allocations"]}
    if feasible_results:
        best_algo = min(feasible_results.keys(), key=lambda x: feasible_results[x]["total_delay"])
        st.success(f"🏆 Best Algorithm: {best_algo} (Total Delay: {feasible_results[best_algo]['total_delay']:.2f} hours)")
        
        # Show visualization for best algorithm
        st.subheader(f"📊 Best Allocation Visualization ({best_algo})")
        plot_berth_allocation(feasible_results[best_algo]["allocations"], berth_length)
    
    # Show individual results in expanders
    for algo_name, result in results.items():
        if result["allocations"]:
            with st.expander(f"View {algo_name} Detailed Results"):
                display_single_results(result["allocations"], berth_length, algo_name)

# -----------------------------
# EXISTING HELPER FUNCTIONS
# -----------------------------
def generate_random_vessels(num_vessels):
    vessel_types = ["Container", "Bulk", "Tanker", "RORO", "Passenger"]
    vessels = []
    
    for i in range(num_vessels):
        vtype = random.choice(vessel_types)
        length_ranges = {
            "Container": (100, 300), "Bulk": (150, 250),
            "Tanker": (200, 350), "RORO": (80, 180), "Passenger": (50, 150)
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

def plot_berth_allocation(allocations, berth_length):
    if not allocations:
        st.warning("No allocation data to visualize")
        return
        
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.set_xlim(0, berth_length)
    ax.set_ylim(0, len(allocations) * 3 + 5)
    ax.set_title("Berth Allocation Visualization", fontsize=16)
    ax.set_xlabel("Berth Position (meters)")
    ax.set_ylabel("Vessel Position")
    
    # Draw berth line and grid
    ax.hlines(1, 0, berth_length, colors='blue', linewidth=4, label='Berth Line')
    ax.grid(True, alpha=0.3)
    
    vessel_colors = {
        "Container": "#FF6B6B", "Bulk": "#4ECDC4", "Tanker": "#FFD166",
        "RORO": "#9D4EDD", "Passenger": "#06D6A0"
    }
    
    # Plot vessels
    for idx, alloc in enumerate(allocations):
        start, end = alloc["start"], alloc["end"]
        y_pos = 5 + idx * 3
        color = vessel_colors.get(alloc["type"], "#118AB2")
        
        rect = plt.Rectangle((start, y_pos - 0.5), end-start, 1.0,
                           color=color, alpha=0.8, edgecolor='black', linewidth=1.5)
        ax.add_patch(rect)
        
        mid_x = (start + end) / 2
        ax.text(mid_x, y_pos + 0.8, f"{alloc['name']}\n({alloc['type']})", 
                ha='center', va='bottom', fontsize=9, weight='bold')
        
        delay_text = f"Delay: {alloc['delay']:.1f}h" if alloc['delay'] > 0.1 else "On time"
        delay_color = 'red' if alloc['delay'] > 0.1 else 'green'
        ax.text(mid_x, y_pos - 1.0, 
                f"Pos: {start:.0f}-{end:.0f}m | {delay_text}", 
                ha='center', va='top', fontsize=8, color=delay_color)
    
    ax.text(berth_length/2, 0.3, f"TOTAL BERTH LENGTH: {berth_length}m", 
            ha='center', va='bottom', fontsize=12, weight='bold', color='blue',
            bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.7))
    
    plt.tight_layout()
    st.pyplot(fig)

if __name__ == "__main__":
    main()
