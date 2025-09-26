import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from streamlit_option_menu import option_menu

# -------------------------
# Database setup
# -------------------------
conn = sqlite3.connect("inventory.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    price REAL NOT NULL,
    quantity INTEGER NOT NULL
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    timestamp TEXT NOT NULL
)
''')
conn.commit()

# -------------------------
# Functions
# -------------------------
def log_action(action):
    cursor.execute("INSERT INTO activity_log (action, timestamp) VALUES (?, ?)", 
                   (action, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()

def add_product(name, price, quantity):
    cursor.execute("INSERT INTO products (name, price, quantity) VALUES (?, ?, ?)", (name, price, quantity))
    conn.commit()
    log_action(f"Added product {name}, Qty={quantity}, Price={price}")

def update_stock(pid, quantity):
    cursor.execute("UPDATE products SET quantity = ? WHERE id = ?", (quantity, pid))
    conn.commit()
    log_action(f"Updated stock for Product ID {pid} to {quantity}")

def sell_product(pid, qty):
    cursor.execute("SELECT name, price, quantity FROM products WHERE id = ?", (pid,))
    row = cursor.fetchone()
    if row:
        name, price, stock = row
        if stock >= qty:
            new_stock = stock - qty
            cursor.execute("UPDATE products SET quantity = ? WHERE id = ?", (new_stock, pid))
            conn.commit()
            total = price * qty
            log_action(f"Sold {qty} of {name}, Total={total}")
            return f"Sold {qty} x {name}. Total = ₹{total}", True
        else:
            return "Not enough stock available.", False
    return "Product not found.", False

def delete_product(pid):
    cursor.execute("DELETE FROM products WHERE id = ?", (pid,))
    conn.commit()
    log_action(f"Deleted Product ID {pid}")

def clear_activity_log():
    cursor.execute("DELETE FROM activity_log")
    conn.commit()
    log_action("Cleared all activity history")

def get_inventory():
    return pd.read_sql("SELECT * FROM products", conn)

def get_activity_log():
    return pd.read_sql("SELECT * FROM activity_log ORDER BY id DESC", conn)

# -------------------------
# Authentication
# -------------------------
def login(username, password):
    return username == "admin" and password == "1234"  # demo creds

# -------------------------
# Streamlit Dashboard UI
# -------------------------
st.set_page_config(page_title="Inventory Management System", layout="wide")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("Login to Inventory Manager")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        if login(u, p):
            st.session_state.logged_in = True
            st.success("Login successful!")
        else:
            st.error("Invalid credentials")
    st.stop()

# -------------------------
# Sidebar with icons
# -------------------------
with st.sidebar:
    choice = option_menu(
        "Menu",
        ["Add Product", "Update Stock", "Sell Product", "View Inventory", "Activity History"],
        icons=["plus-circle", "arrow-repeat", "cart-check", "list-task", "clock-history"],
        menu_icon="boxes",
        default_index=0
    )

# -------------------------
# Pages
# -------------------------
if choice == "Add Product":
    st.subheader("Add New Product")
    name = st.text_input("Product Name")
    price = st.number_input("Price", min_value=0.0, step=0.5)
    qty = st.number_input("Quantity", min_value=0, step=1)
    if st.button("Add Product"):
        if name and price > 0 and qty > 0:
            add_product(name, price, qty)
            st.success(f"Product '{name}' added successfully!")
        else:
            st.error("Please enter valid product details.")

elif choice == "Update Stock":
    st.subheader("Update Stock")
    df = get_inventory()
    if not df.empty:
        st.dataframe(df)
        pid = st.number_input("Product ID", min_value=1, step=1)
        qty = st.number_input("New Quantity", min_value=0, step=1)
        if st.button("Update Stock"):
            update_stock(pid, qty)
            st.success("Stock updated successfully!")
    else:
        st.warning("No products available.")

elif choice == "Sell Product":
    st.subheader("Sell Product")
    df = get_inventory()
    if not df.empty:
        st.dataframe(df)
        pid = st.number_input("Product ID", min_value=1, step=1)
        qty = st.number_input("Quantity to Sell", min_value=1, step=1)
        if st.button("Sell"):
            msg, success = sell_product(pid, qty)
            if success:
                st.success(msg)
            else:
                st.error(msg)
    else:
        st.warning("No products available.")

elif choice == "View Inventory":
    st.subheader("Inventory Overview")
    df = get_inventory()
    if df.empty:
        st.info("No products in inventory.")
    else:
        for i, row in df.iterrows():
            col1, col2, col3, col4, col5 = st.columns([1, 2, 2, 2, 1])
            col1.write(row["id"])
            col2.write(row["name"])
            col3.write(row["price"])
            col4.write(row["quantity"])
            if col5.button("🗑️", key=f"del{row['id']}"):
                delete_product(row["id"])
                st.success(f"Deleted Product ID {row['id']}")
                st.rerun()

        st.bar_chart(df.set_index("name")["quantity"])

elif choice == "Activity History":
    st.subheader("Activity Log")
    logs = get_activity_log()
    if logs.empty:
        st.info("No activity recorded yet.")
    else:
        st.dataframe(logs)
        if st.button("Clear Activity Log"):
            clear_activity_log()
            st.success("Activity log cleared!")
            st.rerun()

# -------------------------
# Activity log clear (fixed)
# -------------------------
def clear_activity_log():
    cursor.execute("DELETE FROM activity_log")
    conn.commit()
    # Do NOT log this action, or the log will never be empty!

    # streamlit run app.py