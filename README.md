# BerthAllocationProblems
BAP Problem simply simulation
#Simple Model
Minimize: Σ x_i
Subject to:
x_i + l_i ≤ L, ∀i
x_i + l_i ≤ x_j + M(1 - y_ij), ∀i<j  
x_j + l_j ≤ x_i + M y_ij, ∀i<j
0 ≤ x_i ≤ L - l_i, ∀i
y_ij ∈ {0,1}, ∀i<j

Where:
x_i = start position of vessel i
l_i = length of vessel i
L = total berth length
M = sufficiently large number (Big-M)
y_ij = binary variable for ordering

#Advance Model
Minimize: Σ d_i
Subject to:
x_i + l_i ≤ L, ∀i
x_i = s_i × C, ∀i
d_i ≥ s_i - t_i, ∀i
x_i + l_i ≤ x_j + M(1 - y_ij), ∀i<j
x_j + l_j ≤ x_i + M y_ij, ∀i<j
x_i, s_i, d_i ≥ 0, ∀i
y_ij ∈ {0,1}, ∀i<j

Where:
d_i = delay of vessel i (hours)
s_i = scaled start time of vessel i (hours)
t_i = ETA of vessel i (hours)
C = conversion factor (50 meters/hour)


#Rule-based
START
  │
  ▼
Sort vessels by ETA (ascending)
  │
  ▼
For each vessel in sorted order:
  │
  ▼
Determine search range:
  │─ If Container → Use constraint min/max
  │─ Else → Use full berth range
  │
  ▼
Start from minimum position
  │
  ▼
Check for overlaps with existing vessels
  │
  ▼
If no overlap → ALLOCATE at current position
  │
  ▼
If overlap → Move to next position (+5m gap)
  │
  ▼
If no position found → Place at end of berth
  │
  ▼
Continue until all vessels allocated
  │
  ▼
Calculate delays based on actual positions
  │
  ▼
END
