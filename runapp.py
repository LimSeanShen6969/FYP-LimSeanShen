import streamlit as st
import queue
import time
import random
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt

# Define the Customer class
class Customer:
    def __init__(self, customer_id, purpose, queue_in_time):
        self.customer_id = customer_id
        self.purpose = purpose
        self.estimated_time = self.get_estimated_time()
        self.counter = None
        self.queue_in_time = queue_in_time
        self.queue_out_time = None
        self.wait_time = 0

    def get_estimated_time(self):
        if self.purpose == 'Mailing':
            return random.randint(3, 10)
        elif self.purpose == 'Payment':
            return random.randint(1, 5)
        elif self.purpose == 'Package Pickup':
            return random.randint(1, 10)
        else:
            return random.randint(1, 5)

# Define the PostOfficeQueueSystem class
class PostOfficeQueueSystem:
    def __init__(self, counters, db_name="post_office_queue.db"):
        self.queue = queue.Queue()
        self.counters = counters
        self.customers_served = 0
        self.total_wait_time = 0
        self.db_name = db_name
        self.create_db()

    def create_db(self):
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute("DROP TABLE IF EXISTS queue_records")
        c.execute('''CREATE TABLE IF NOT EXISTS queue_records (
                        customer_id INTEGER,
                        purpose TEXT,
                        estimated_time INTEGER,
                        wait_time REAL,
                        counter_no INTEGER,
                        queue_in_time TEXT,
                        queue_out_time TEXT
                    )''')
        conn.commit()
        conn.close()

    def add_customer(self, customer):
        self.queue.put(customer)

    def save_to_db(self, customer):
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute("""INSERT INTO queue_records (customer_id, purpose, estimated_time, wait_time, counter_no, queue_in_time, queue_out_time)
                      VALUES (?, ?, ?, ?, ?, ?, ?)""",
                  (customer.customer_id, customer.purpose, customer.estimated_time, customer.wait_time, customer.counter,
                   customer.queue_in_time.strftime('%Y-%m-%d %H:%M:%S'),
                   customer.queue_out_time.strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()

    def process_queue(self):
        counter_no = 1
        end_of_day = datetime.combine(datetime.today(), datetime.strptime('17:00:00', '%H:%M:%S').time())

        while not self.queue.empty():
            customer = self.queue.get()
            customer.counter = counter_no

            customer.queue_out_time = self.get_random_queue_out_time(customer.queue_in_time, min_wait=10, max_wait=30)

            if customer.queue_out_time > end_of_day:
                print("End of queue processing as it's past 5 PM.")
                break

            queue_wait_time = (customer.queue_out_time - customer.queue_in_time).total_seconds() / 60
            customer.wait_time = queue_wait_time
            self.total_wait_time += queue_wait_time
            self.customers_served += 1
            self.save_to_db(customer)
            time.sleep(customer.estimated_time / 100 + random.uniform(0.05, 0.15))
            counter_no = (counter_no % self.counters) + 1

    def get_random_queue_out_time(self, queue_in_time, min_wait=10, max_wait=30):
        wait_time_minutes = random.uniform(min_wait, max_wait)
        queue_out_time = queue_in_time + timedelta(minutes=wait_time_minutes)
        return queue_out_time

# Streamlit UI
st.title("Post Office Queue Simulation")

# User inputs
num_counters = st.number_input("Number of Counters", min_value=1, max_value=10, value=5)
num_customers = st.number_input("Number of Customers (10,000 - 20,000)", min_value=10000, max_value=20000, value=10000)

# Simulate post office queue when the button is clicked
if st.button("Simulate Queue"):
    post_office = PostOfficeQueueSystem(counters=num_counters)
    purposes = ['Mailing', 'Payment', 'Package Pickup', 'Inquiry']

    start_time = datetime.combine(datetime.today(), datetime.strptime('08:00:00', '%H:%M:%S').time())
    current_time = start_time

    # Distribution of customers per hour
    hours_distribution = {
        '08:00-09:00': random.randint(500, 1000),
        '09:00-10:00': random.randint(1000, 1500),
        '10:00-11:00': random.randint(800, 1000),
        '11:00-12:00': random.randint(1000, 1500),
        '12:00-14:00': random.randint(4000, 6000),
        '14:00-15:00': random.randint(1000, 1500),
        '15:00-16:00': random.randint(800, 1000),
        '16:00-17:00': random.randint(500, 800),
        '17:00-18:00': num_customers - sum([random.randint(500, 1000) for _ in range(8)])
    }

    for time_period, num_customers_in_period in hours_distribution.items():
        for _ in range(num_customers_in_period):
            purpose = random.choice(purposes)
            customer = Customer(customer_id=random.randint(1, 20000), purpose=purpose, queue_in_time=current_time)
            post_office.add_customer(customer)
            current_time += timedelta(seconds=random.uniform(1, 4))  # Increment time for the next customer

    post_office.process_queue()
    st.success("Simulation complete!")

    # Load the data from SQLite for analysis
    conn = sqlite3.connect(post_office.db_name)
    query = "SELECT queue_in_time, queue_out_time, wait_time FROM queue_records"
    df = pd.read_sql_query(query, conn)
    conn.close()

    # Data analysis and visualization
    df['queue_in_time'] = pd.to_datetime(df['queue_in_time'])
    df['queue_out_time'] = pd.to_datetime(df['queue_out_time'])
    df.set_index('queue_in_time', inplace=True)
    
    # Average wait time
    average_wait_time = df['wait_time'].resample('30T').mean()
    
    # Customer count per hour
    df['hour_slot'] = df['queue_in_time'].dt.floor('H')
    customer_count_hourly = df['hour_slot'].value_counts().sort_index()

    # Plotting average wait time
    st.subheader("Average Wait Time Throughout the Queue")
    fig, ax = plt.subplots()
    ax.plot(average_wait_time.index, average_wait_time.values, marker='o', linestyle='-')
    ax.set_title('Average Wait Time Over Time')
    ax.set_xlabel('Time')
    ax.set_ylabel('Average Wait Time (minutes)')
    plt.xticks(rotation=45)
    st.pyplot(fig)

    # Plotting customer count per hour
    st.subheader("Number of Customers in Each Hour Slot")
    fig, ax = plt.subplots()
    customer_count_hourly.plot(kind='bar', color='#1f77b4', ax=ax)
    ax.set_title('Number of Customers per Hour Slot')
    ax.set_xlabel('Hour Slot')
    ax.set_ylabel('Number of Customers')
    plt.xticks(rotation=45)
    st.pyplot(fig)
