import streamlit as st
import pandas as pd
import sqlite3
import pulp as lp

@st.cache_data
def load_data():
    conn = sqlite3.connect('post_office_queue.db')
    query = "SELECT queue_in_time, queue_out_time, wait_time FROM queue_records"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


# Function to solve LP problem based on user input
def solve_lp_model(base_wait_time, max_avg_wait_time, budget, cost_per_counter):
    # Define the LP problem
    prob = lp.LpProblem("Optimal_Counter_Configuration", lp.LpMinimize)

    # Decision variable: number of counters
    x = lp.LpVariable("Number_of_Counters", lowBound=1, cat='Integer')

    # Objective function: Minimize the number of counters
    prob += x, "Minimize_the_number_of_counters"

    # Constraint 1: Adjusted average wait time formula
    prob += (base_wait_time <= max_avg_wait_time * x), "Average_Wait_Time_Constraint"

    # Constraint 2: Total cost of counters should not exceed the budget
    prob += (cost_per_counter * x <= budget), "Cost_Constraint"

    # Solve the problem
    prob.solve()

    # Get the results
    optimal_counters = x.varValue
    if optimal_counters:
        optimal_wait_time = base_wait_time / optimal_counters
        total_cost = optimal_counters * cost_per_counter
        return optimal_counters, optimal_wait_time, total_cost
    else:
        return None, None, None

# Load data and calculate average wait time
df = load_data()
average_wait_time = df['wait_time'].mean()

# Streamlit App
st.title("Post Office Queue Management Optimization")

# User inputs for model parameters
st.sidebar.header("Model Parameters")
base_wait_time = st.sidebar.number_input("Base wait time (1 counter)", value=100, min_value=1)
max_avg_wait_time = st.sidebar.number_input("Max average wait time (minutes)", value=15, min_value=1)
budget = st.sidebar.number_input("Budget for counters", value=1500, min_value=1)
cost_per_counter = st.sidebar.number_input("Cost per counter", value=200, min_value=1)

# Button to trigger the model run
if st.sidebar.button("Run Optimization"):
    optimal_counters, optimal_wait_time, total_cost = solve_lp_model(
        base_wait_time, max_avg_wait_time, budget, cost_per_counter
    )

    # Display results
    if optimal_counters is not None:
        st.success(f"Optimal number of counters: {int(optimal_counters)}")
        st.write(f"With {int(optimal_counters)} counters, the average wait time will be approximately {optimal_wait_time:.2f} minutes.")
        st.write(f"The total cost to operate {int(optimal_counters)} counters is {total_cost}.")
    else:
        st.error("Unable to find a feasible solution. Please adjust the parameters.")

# Display the original queue data
st.header("Queue Data")
st.write(df)
