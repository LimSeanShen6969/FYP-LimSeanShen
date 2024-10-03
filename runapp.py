import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import random
import time
from datetime import datetime, timedelta

# Define customer and queue simulation
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

class PostOfficeQueueSystem:
    def __init__(self, counters, db_name="post_office_queue.db"):
        self.counters = counters
        self.customers_served = 0
        self.total_wait_time = 0
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
        # Save the customer to the database
        conn = sqlite3.connect("post_office_queue.db")
        c = conn.cursor()
        c.execute("""
            INSERT INTO queue_records (customer_id, purpose, estimated_time, wait_time, counter_no, queue_in_time, queue_out_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
                  (customer.customer_id, customer.purpose, customer.estimated_time, customer.wait_time, customer.counter,
                   customer.queue_in_time.strftime('%Y-%m-%d %H:%M:%S'),
                   customer.queue_out_time.strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()

    def process_queue(self, total_customers):
        purposes = ['Mailing', 'Payment', 'Package Pickup', 'Inquiry']
        start_time = datetime.combine(datetime.today(), datetime.strptime('08:00:00', '%H:%M:%S').time())
        end_time = datetime.combine(datetime.today(), datetime.strptime('18:00:00', '%H:%M:%S').time())

        current_time = start_time
        counter_no = 1

        for _ in range(total_customers):
            purpose = random.choice(purposes)
            customer = Customer(customer_id=random.randint(1, 20000), purpose=purpose, queue_in_time=current_time)

            customer.counter = counter_no
            customer.queue_out_time = self.get_random_queue_out_time(customer.queue_in_time, min_wait=10, max_wait=30)
            customer.wait_time = (customer.queue_out_time - customer.queue_in_time).total_seconds() / 60
            self.total_wait_time += customer.wait_time
            self.customers_served += 1

            self.add_customer(customer)
            time.sleep(customer.estimated_time / 100 + random.uniform(0.05, 0.15))
            counter_no = (counter_no % self.counters) + 1
            current_time += timedelta(seconds=random.uniform(30, 120))  # Simulate queue-in time difference

    def get_random_queue_out_time(self, queue_in_time, min_wait=10, max_wait=30):
        wait_time_minutes = random.uniform(min_wait, max_wait)
        wait_time = timedelta(minutes=wait_time_minutes)
        return queue_in_time + wait_time


def visualize_data():
    conn = sqlite3.connect("post_office_queue.db")
    query = "SELECT queue_in_time, wait_time FROM queue_records"
    df = pd.read_sql_query(query, conn)
    conn.close()

    df['queue_in_time'] = pd.to_datetime(df['queue_in_time'])
    df.set_index('queue_in_time', inplace=True)
    average_wait_time = df['wait_time'].resample('30T').mean()

    st.line_chart(average_wait_time)


def simulate_post_office(counters, total_customers):
    post_office = PostOfficeQueueSystem(counters)
    post_office.process_queue(total_customers)
    visualize_data()


# Streamlit App
st.title('Post Office Queue Simulation')

# User inputs
counters = st.slider('Select the number of counters', 1, 10, 5)
total_customers = st.slider('Select the total number of customers', 1000, 20000, 10000)

if st.button('Start Simulation'):
    st.write(f"Simulating with {counters} counters and {total_customers} customers...")
    simulate_post_office(counters, total_customers)
    st.success('Simulation complete!')
