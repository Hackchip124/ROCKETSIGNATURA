import streamlit as st
import pandas as pd
import numpy as np
import time
import datetime
import hashlib
import json
import os
import shutil
import zipfile
from PIL import Image
import fpdf as FPDF
import io
import base64
import uuid
import serial
import serial.tools.list_ports
import subprocess
import threading
import platform
import pytz
from datetime import timedelta

# Constants
DATA_DIR = "data"
BACKUP_DIR = "backups"
TEMPLATE_DIR = "templates"
USERS_FILE = os.path.join(DATA_DIR, "users.json")
PRODUCTS_FILE = os.path.join(DATA_DIR, "products.json")
INVENTORY_FILE = os.path.join(DATA_DIR, "inventory.json")
TRANSACTIONS_FILE = os.path.join(DATA_DIR, "transactions.json")
DISCOUNTS_FILE = os.path.join(DATA_DIR, "discounts.json")
OFFERS_FILE = os.path.join(DATA_DIR, "offers.json")
LOYALTY_FILE = os.path.join(DATA_DIR, "loyalty.json")
CATEGORIES_FILE = os.path.join(DATA_DIR, "categories.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
SUPPLIERS_FILE = os.path.join(DATA_DIR, "suppliers.json")
SHIFTS_FILE = os.path.join(DATA_DIR, "shifts.json")
CASH_DRAWER_FILE = os.path.join(DATA_DIR, "cash_drawer.json")
RETURNS_FILE = os.path.join(DATA_DIR, "returns.json")
PURCHASE_ORDERS_FILE = os.path.join(DATA_DIR, "purchase_orders.json")
# Add these constants at the top with other constants
BRANDS_FILE = os.path.join(DATA_DIR, "brands.json")
OUTDOOR_ORDERS_FILE = os.path.join(DATA_DIR, "outdoor_orders.json")
# Authentication functions
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_user(username, password):
    users = load_data(USERS_FILE)
    if username in users:
        if users[username]["password"] == hash_password(password):
            return users[username]
    return None

def get_current_user_role():
    if 'user_info' in st.session_state:
        return st.session_state.user_info.get('role')
    return None

def is_admin():
    return get_current_user_role() == 'admin'

def is_manager():
    return get_current_user_role() in ['admin', 'manager']

def is_cashier():
    return get_current_user_role() in ['admin', 'manager', 'cashier']

# Ensure data and template directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)
os.makedirs(TEMPLATE_DIR, exist_ok=True)

# Data loading and saving functions
def load_data(file):
    try:
        with open(file, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_data(data, file):
    with open(file, 'w') as f:
        json.dump(data, f, indent=4)

# Initialize empty data files if they don't exist
def ensure_default_user():
    """Ensure the default admin user exists"""
    users = load_data(USERS_FILE)
    
    # Check if admin user exists and has correct password
    if "admin" not in users:
        # Create default admin user
        users["admin"] = {
            "username": "admin",
            "password": hash_password("admin123"),
            "role": "admin",
            "full_name": "Administrator",
            "email": "admin@supermarket.com",
            "active": True,
            "date_created": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "created_by": "system"
        }
        save_data(users, USERS_FILE)
        print("Default admin user created")
    elif users["admin"]["password"] != hash_password("admin123"):
        # Reset password to default if it's been changed
        users["admin"]["password"] = hash_password("admin123")
        save_data(users, USERS_FILE)
        print("Admin password reset to default")

def initialize_empty_data():
    """Initialize all data files with default values"""
    # Ensure data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)
    
    default_data = {
        USERS_FILE: {
            "admin": {
                "username": "admin",
                "password": hash_password("admin123"),
                "role": "admin",
                "full_name": "Administrator",
                "email": "admin@supermarket.com",
                "active": True,
                "date_created": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "created_by": "system"
            }
        },
        PRODUCTS_FILE: {},
        INVENTORY_FILE: {},
        TRANSACTIONS_FILE: {},
        DISCOUNTS_FILE: {},
        OFFERS_FILE: {},
        LOYALTY_FILE: {
            "tiers": {},
            "customers": {},
            "rewards": {}
        },
        CATEGORIES_FILE: {
            "categories": [],
            "subcategories": {}
        },
        SETTINGS_FILE: {
            "store_name": "Supermarket POS",
            "store_address": "",
            "store_phone": "",
            "store_email": "",
            "store_logo": "",
            "tax_rate": 0.0,
            "tax_inclusive": False,
            "receipt_template": "Simple",
            "theme": "Light",
            "session_timeout": 30,
            "printer_name": "Browser Printer",
            "barcode_scanner": "keyboard",
            "timezone": "UTC",
            "currency_symbol": "$",
            "decimal_places": 2,
            "auto_logout": True,
            "cash_drawer_enabled": False,
            "cash_drawer_command": "",
            "barcode_scanner_port": "auto",
            "receipt_header": "",
            "receipt_footer": "",
            "receipt_print_logo": False
        },
        SUPPLIERS_FILE: {},
        SHIFTS_FILE: {},
        CASH_DRAWER_FILE: {
            "current_balance": 0.0,
            "transactions": []
        },
        RETURNS_FILE: {},
        PURCHASE_ORDERS_FILE: {},
        BRANDS_FILE: {
            "brands": [],
            "brand_products": {}
        },
        OUTDOOR_ORDERS_FILE: {
            "orders": {},
            "delivery_charges": {
                "standard": 5.0,
                "express": 10.0,
                "free_threshold": 50.0
            }
        }
    }
    
    for file, data in default_data.items():
        if not os.path.exists(file):
            # Create parent directories if they don't exist
            os.makedirs(os.path.dirname(file), exist_ok=True)
            with open(file, 'w') as f:
                json.dump(data, f, indent=4)
            print(f"Created {file} with default data")


# Add to session state initialization 
if 'outdoor_cart' not in st.session_state:
    st.session_state.outdoor_cart = {}
if 'selected_brand' not in st.session_state:
    st.session_state.selected_brand = None
    
# Hardware functions
def get_available_printers():
    printers = []
    try:
        if platform.system() == "Windows":
            try:
                result = subprocess.run(['wmic', 'printer', 'get', 'name'], capture_output=True, text=True)
                if result.returncode == 0:
                    printers = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            except:
                pass
        else:
            try:
                result = subprocess.run(['lpstat', '-a'], capture_output=True, text=True)
                if result.returncode == 0:
                    printers = [line.split()[0] for line in result.stdout.splitlines()]
            except:
                pass
    except:
        printers = ["No printers found"]
    return printers if printers else ["No printers found"]

def get_available_com_ports():
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports] + ["auto"]

def print_receipt(receipt_text):
    settings = load_data(SETTINGS_FILE)
    
    # 1. Browser-based printing
    try:
        js = f"""
        <script>
        function printReceipt() {{
            var win = window.open('', '', 'height=400,width=600');
            win.document.write(`<pre>{receipt_text}</pre>`);
            win.document.close();
            win.print();
            setTimeout(() => win.close(), 500);
        }}
        printReceipt();
        </script>
        """
        st.components.v1.html(js, height=0)
        return True
    except:
        pass
    
    # 2. PDF fallback
    try:
        pdf = FPDF.FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        
        # Add store header if enabled
        if settings.get('receipt_print_logo', False) and 'store_logo' in settings and os.path.exists(settings['store_logo']):
            try:
                pdf.image(settings['store_logo'], x=10, y=8, w=30)
                pdf.ln(20)  # Move down after logo
            except:
                pass
        
        # Add receipt content
        for line in receipt_text.split('\n'):
            pdf.cell(0, 10, line, ln=1)
        
        pdf_path = "receipt.pdf"
        pdf.output(pdf_path)
        
        # Open PDF for printing
        if platform.system() == "Windows":
            os.startfile(pdf_path, "print")
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["lp", pdf_path])
        else:  # Linux
            subprocess.run(["lp", pdf_path])
        
        return True
    except Exception as e:
        st.error(f"Printing failed: {str(e)}")
        return False

def open_cash_drawer():
    settings = load_data(SETTINGS_FILE)
    if not settings.get('cash_drawer_enabled', False):
        return False
    
    command = settings.get('cash_drawer_command', '')
    if not command:
        return False
    
    try:
        subprocess.run(command, shell=True)
        return True
    except Exception as e:
        st.error(f"Failed to open cash drawer: {str(e)}")
        return False

# Improved Barcode Scanner
class BarcodeScanner:
    def __init__(self):
        self.scanner = None
        self.scanner_thread = None
        self.running = False
        self.last_barcode = ""
        self.last_scan_time = 0
        self.scan_buffer = ""
    
    def init_serial_scanner(self, port='auto'):
        if port == 'auto':
            ports = serial.tools.list_ports.comports()
            if not ports:
                st.warning("No serial ports found")
                return False
            port = ports[0].device
        
        try:
            self.scanner = serial.Serial(
                port=port,
                baudrate=9600,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False
            )
            return True
        except Exception as e:
            st.error(f"Failed to open serial port {port}: {str(e)}")
            return False
    
    def start_serial_scanning(self):
        self.running = True
        while self.running:
            try:
                if self.scanner.in_waiting > 0:
                    data = self.scanner.readline().decode('utf-8').strip()
                    if data:
                        self.last_barcode = data
                        self.last_scan_time = time.time()
                        st.session_state.scanned_barcode = data
            except Exception as e:
                time.sleep(0.1)
    
    def stop_scanning(self):
        self.running = False
        if self.scanner and hasattr(self.scanner, 'close'):
            self.scanner.close()
        if self.scanner_thread and self.scanner_thread.is_alive():
            self.scanner_thread.join()
    
    def get_barcode(self):
        if time.time() - self.last_scan_time < 1:  # 1 second debounce
            barcode = self.last_barcode
            self.last_barcode = ""
            return barcode
        return None

# Initialize barcode scanner
barcode_scanner = BarcodeScanner()

def setup_barcode_scanner():
    settings = load_data(SETTINGS_FILE)
    scanner_type = settings.get('barcode_scanner', 'keyboard')
    port = settings.get('barcode_scanner_port', 'auto')
    
    if scanner_type == 'serial':
        if barcode_scanner.init_serial_scanner(port):
            barcode_scanner.scanner_thread = threading.Thread(
                target=barcode_scanner.start_serial_scanning, 
                daemon=True
            )
            barcode_scanner.scanner_thread.start()
            st.session_state.barcode_scanner_setup = True
            st.session_state.scanner_status = "Connected"
        else:
            st.session_state.scanner_status = "Disconnected"
    else:
        st.session_state.scanner_status = "Keyboard Mode"

# Backup and Restore functions
def create_backup():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"pos_backup_{timestamp}.zip"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    
    with zipfile.ZipFile(backup_path, 'w') as zipf:
        for root, _, files in os.walk(DATA_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, DATA_DIR))
    
    return backup_path

def restore_backup(backup_file):
    with zipfile.ZipFile(backup_file, 'r') as zipf:
        zipf.extractall(DATA_DIR)
    return True

# Utility functions
def generate_barcode():
    return str(uuid.uuid4().int)[:12]

def generate_short_id():
    return str(uuid.uuid4())[:8]

def format_currency(amount):
    settings = load_data(SETTINGS_FILE)
    symbol = settings.get('currency_symbol', '$')
    decimals = settings.get('decimal_places', 2)
    return f"{symbol}{amount:.{decimals}f}"

def get_current_datetime():
    settings = load_data(SETTINGS_FILE)
    tz = pytz.timezone(settings.get('timezone', 'UTC'))
    return datetime.datetime.now(tz)

# Purchase Order functions
def generate_purchase_order(supplier_id, items):
    suppliers = load_data(SUPPLIERS_FILE)
    products = load_data(PRODUCTS_FILE)
    purchase_orders = load_data(PURCHASE_ORDERS_FILE)
    
    if supplier_id not in suppliers:
        return None
    
    supplier = suppliers[supplier_id]
    po_id = generate_short_id()
    
    # Calculate totals
    total_cost = 0
    for item in items:
        product = products.get(item['barcode'], {})
        total_cost += item['quantity'] * product.get('cost', 0)
    
    # Create PO
    purchase_orders[po_id] = {
        'po_id': po_id,
        'supplier_id': supplier_id,
        'supplier_name': supplier['name'],
        'date_created': get_current_datetime().strftime("%Y-%m-%d %H:%M:%S"),
        'created_by': st.session_state.user_info['username'],
        'items': items,
        'total_cost': total_cost,
        'status': 'pending',
        'date_received': None,
        'received_by': None
    }
    
    save_data(purchase_orders, PURCHASE_ORDERS_FILE)
    return po_id

def generate_po_report(po_id):
    purchase_orders = load_data(PURCHASE_ORDERS_FILE)
    products = load_data(PRODUCTS_FILE)
    settings = load_data(SETTINGS_FILE)
    
    if po_id not in purchase_orders:
        return None
    
    po = purchase_orders[po_id]
    
    report = f"PURCHASE ORDER #{po_id}\n"
    report += f"{settings.get('store_name', 'Supermarket POS')}\n"
    report += f"Date: {po['date_created']}\n"
    report += "=" * 50 + "\n"
    report += f"Supplier: {po['supplier_name']}\n"
    report += f"Created by: {po['created_by']}\n"
    report += "=" * 50 + "\n"
    report += "ITEMS:\n"
    report += "Barcode\tProduct\tQty\tUnit Cost\tTotal\n"
    
    for item in po['items']:
        product = products.get(item['barcode'], {'name': 'Unknown', 'cost': 0})
        report += f"{item['barcode']}\t{product['name']}\t{item['quantity']}\t"
        report += f"{format_currency(product.get('cost', 0))}\t"
        report += f"{format_currency(item['quantity'] * product.get('cost', 0))}\n"
    
    report += "=" * 50 + "\n"
    report += f"TOTAL COST: {format_currency(po['total_cost'])}\n"
    report += f"STATUS: {po['status'].upper()}\n"
    
    if po['status'] == 'received':
        report += f"Received on: {po['date_received']} by {po['received_by']}\n"
    
    return report

def process_received_po(po_id):
    purchase_orders = load_data(PURCHASE_ORDERS_FILE)
    inventory = load_data(INVENTORY_FILE)
    
    if po_id not in purchase_orders:
        return False
    
    po = purchase_orders[po_id]
    
    if po['status'] == 'received':
        return True  # Already processed
    
    # Update inventory
    for item in po['items']:
        barcode = item['barcode']
        quantity = item['quantity']
        
        if barcode in inventory:
            inventory[barcode]['quantity'] += quantity
        else:
            inventory[barcode] = {'quantity': quantity, 'reorder_point': 10}
        
        inventory[barcode]['last_updated'] = get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
        inventory[barcode]['updated_by'] = st.session_state.user_info['username']
    
    # Update PO status
    po['status'] = 'received'
    po['date_received'] = get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
    po['received_by'] = st.session_state.user_info['username']
    
    save_data(purchase_orders, PURCHASE_ORDERS_FILE)
    save_data(inventory, INVENTORY_FILE)
    return True

# Session state initialization
if 'user_info' not in st.session_state:
    st.session_state.user_info = None
if 'cart' not in st.session_state:
    st.session_state.cart = {}
if 'current_page' not in st.session_state:
    st.session_state.current_page = "Login"
if 'shift_started' not in st.session_state:
    st.session_state.shift_started = False
if 'shift_id' not in st.session_state:
    st.session_state.shift_id = None
if 'last_activity' not in st.session_state:
    st.session_state.last_activity = time.time()
if 'barcode_scanner_setup' not in st.session_state:
    st.session_state.barcode_scanner_setup = False
if 'scanned_barcode' not in st.session_state:
    st.session_state.scanned_barcode = None
if 'scanner_status' not in st.session_state:
    st.session_state.scanner_status = "Not Connected"
if 'pos_mode' not in st.session_state:
    st.session_state.pos_mode = 'scan'
if 'selected_category' not in st.session_state:
    st.session_state.selected_category = None
if 'selected_subcategory' not in st.session_state:
    st.session_state.selected_subcategory = None
if 'return_reason' not in st.session_state:
    st.session_state.return_reason = ""
if 'po_supplier' not in st.session_state:
    st.session_state.po_supplier = None
if 'po_items' not in st.session_state:
    st.session_state.po_items = []

# Setup barcode scanner if not already done
if not st.session_state.barcode_scanner_setup:
    setup_barcode_scanner()

# Login Page
def login_page():
    st.title("Supermarket POS - Login")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Login")
        
        if submit_button:
            user = verify_user(username, password)
            if user:
                if not user.get('active', True):
                    st.error("This account is inactive. Please contact administrator.")
                else:
                    st.session_state.user_info = user
                    st.session_state.current_page = "Dashboard"
                    st.session_state.last_activity = time.time()
                    st.rerun()
            else:
                st.error("Invalid username or password")

# Shift Management
def start_shift():
    shifts = load_data(SHIFTS_FILE)
    shift_id = generate_short_id()
    current_time = get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
    
    shifts[shift_id] = {
        'shift_id': shift_id,
        'user_id': st.session_state.user_info['username'],
        'start_time': current_time,
        'end_time': None,
        'starting_cash': 0.0,
        'ending_cash': 0.0,
        'transactions': [],
        'status': 'active'
    }
    
    save_data(shifts, SHIFTS_FILE)
    st.session_state.shift_started = True
    st.session_state.shift_id = shift_id
    return shift_id

def end_shift():
    if not st.session_state.shift_started:
        return False
    
    shifts = load_data(SHIFTS_FILE)
    shift_id = st.session_state.shift_id
    
    if shift_id in shifts:
        current_time = get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
        shifts[shift_id]['end_time'] = current_time
        shifts[shift_id]['status'] = 'completed'
        
        transactions = load_data(TRANSACTIONS_FILE)
        shift_transactions = [t for t in transactions.values() 
                            if t.get('shift_id') == shift_id and t['payment_method'] == 'Cash']
        total_cash = sum(t['total'] for t in shift_transactions)
        
        shifts[shift_id]['ending_cash'] = total_cash
        
        save_data(shifts, SHIFTS_FILE)
        st.session_state.shift_started = False
        st.session_state.shift_id = None
        return True
    return False

# Dashboard
def dashboard():
    settings = load_data(SETTINGS_FILE)
    if settings.get('auto_logout', True):
        inactive_time = time.time() - st.session_state.last_activity
        timeout_minutes = settings.get('session_timeout', 30)
        if inactive_time > timeout_minutes * 60:
            st.session_state.user_info = None
            st.session_state.current_page = "Login"
            st.rerun()
    
    st.session_state.last_activity = time.time()
    
    st.title("Supermarket POS Dashboard")
    st.sidebar.title("Navigation")
    
    # Shift management for cashiers
    if is_cashier() and not st.session_state.shift_started:
        with st.sidebar:
            st.subheader("Shift Management")
            starting_cash = st.number_input("Starting Cash Amount", min_value=0.0, value=0.0, step=1.0)
            if st.button("Start Shift"):
                shift_id = start_shift()
                shifts = load_data(SHIFTS_FILE)
                shifts[shift_id]['starting_cash'] = starting_cash
                save_data(shifts, SHIFTS_FILE)
                st.success("Shift started successfully")
                st.rerun()
    
    # Navigation
    pages = {
        "Dashboard": dashboard_content,
        "POS Terminal": pos_terminal,
        "Product Management": product_management,
        "Inventory Management": inventory_management,
        "User Management": user_management,
        "Discounts & Promotions": discounts_management,
        "Offers Management": offers_management,
        "Loyalty Program": loyalty_management,
        "Categories": categories_management,
        "Brands": brands_management,
        "Suppliers": suppliers_management,
        "Purchase Orders": purchase_orders_management,
        "Outdoor Sales": outdoor_sales_portal,
        "Reports & Analytics": reports_analytics,
        "Shifts Management": shifts_management,
        "Returns & Refunds": returns_management,
        "System Settings": system_settings,
        "Backup & Restore": backup_restore
    }
    if is_admin():
        pass  # All pages already included
    elif is_manager():
        pages.pop("User Management", None)
        pages.pop("Backup & Restore", None)
    elif is_cashier():
        pages = {
            "Dashboard": dashboard_content,
            "POS Terminal": pos_terminal,
            "Shifts Management": shifts_management,
            "Returns & Refunds": returns_management
        }
    
    selected_page = st.sidebar.radio("Go to", list(pages.keys()))
    
    if st.sidebar.button("Logout"):
        if is_cashier() and st.session_state.shift_started:
            st.warning("Please end your shift before logging out")
        else:
            st.session_state.user_info = None
            st.session_state.current_page = "Login"
            st.rerun()
    
    # Display selected page
    pages[selected_page]()

def dashboard_content():
    st.header("Overview")
    
    col1, col2, col3 = st.columns(3)
    
    products = load_data(PRODUCTS_FILE)
    inventory = load_data(INVENTORY_FILE)
    transactions = load_data(TRANSACTIONS_FILE)
    
    total_products = len(products)
    low_stock_items = sum(1 for item in inventory.values() if item.get('quantity', 0) < item.get('reorder_point', 10))
    
    today_sales = 0
    today = datetime.date.today()
    for t in transactions.values():
        try:
            trans_date = datetime.datetime.strptime(t.get('date', ''), "%Y-%m-%d %H:%M:%S").date()
            if trans_date == today:
                today_sales += t.get('total', 0)
        except (ValueError, KeyError):
            continue
    
    col1.metric("Total Products", total_products)
    col2.metric("Low Stock Items", low_stock_items)
    col3.metric("Today's Sales", format_currency(today_sales))
    
    st.subheader("Recent Transactions")
    
    def get_transaction_date(t):
        try:
            return datetime.datetime.strptime(t.get('date', ''), "%Y-%m-%d %H:%M:%S")
        except (ValueError, KeyError):
            return datetime.datetime.min
    
    recent_transactions = sorted(transactions.values(), 
                               key=get_transaction_date, 
                               reverse=True)[:5]
    
    if recent_transactions:
        display_data = []
        for t in recent_transactions:
            display_data.append({
                'transaction_id': t.get('transaction_id', 'N/A'),
                'date': t.get('date', 'N/A'),
                'total': format_currency(t.get('total', 0)),
                'cashier': t.get('cashier', 'N/A')
            })
        
        trans_df = pd.DataFrame(display_data)
        st.dataframe(trans_df)
    else:
        st.info("No recent transactions")

# POS Terminal - Main Page
# POS Terminal - Enhanced with Payment Charges and Offers
def pos_terminal():
    if is_cashier() and not st.session_state.shift_started:
        st.warning("Please start your shift before using the POS terminal")
        return
    
    st.title("POS Terminal")
    
    # Scanner status indicator
    if 'scanner_status' in st.session_state:
        status_color = "green" if st.session_state.scanner_status == "Connected" else "red"
        st.markdown(f"**Scanner Status:** <span style='color:{status_color}'>{st.session_state.scanner_status}</span>", 
                   unsafe_allow_html=True)
    
    # POS Mode Selection
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Barcode Scan Mode", use_container_width=True):
            st.session_state.pos_mode = 'scan'
    with col2:
        if st.button("Manual Entry Mode", use_container_width=True):
            st.session_state.pos_mode = 'manual'
    
    if st.session_state.pos_mode == 'scan':
        pos_scan_mode()
    else:
        pos_manual_mode()

def pos_scan_mode():
    products = load_data(PRODUCTS_FILE)
    inventory = load_data(INVENTORY_FILE)
    
    st.header("Barcode Scan Mode")
    
    # Offer selection
    offers = load_data(OFFERS_FILE)
    active_offers = [o for o in offers.values() if o['active']]
    
    if active_offers:
        st.subheader("🎁 Active Offers")
        offer_options = {o['name']: o for o in active_offers}
        
        # Initialize selected_offer in session state if not exists
        if 'selected_offer' not in st.session_state:
            st.session_state.selected_offer = None
            
        selected_offer = st.selectbox(
            "Select Offer to Apply", 
            [""] + list(offer_options.keys()),
            key="offer_select"
        )
        
        # Store the selected offer in session state
        st.session_state.selected_offer = selected_offer
        
        if selected_offer:
            st.info(f"Selected: {offer_options[selected_offer]['description']}")
    
    # Check for barcode scanner input
    if st.session_state.scanner_status == "Connected":
        barcode = barcode_scanner.get_barcode()
        if barcode:
            if barcode in products:
                product = products[barcode]
                stock = inventory.get(barcode, {}).get('quantity', 0)
                
                if stock > 0:
                    if barcode in st.session_state.cart:
                        st.session_state.cart[barcode]['quantity'] += 1
                    else:
                        st.session_state.cart[barcode] = {
                            'name': product['name'],
                            'price': product['price'],
                            'quantity': 1,
                            'description': product.get('description', ''),
                            'brand': product.get('brand')
                        }
                    st.success(f"Added {product['name']} to cart")
                    # Use a different approach to clear the input
                    st.rerun()
                else:
                    st.error(f"{product['name']} is out of stock")
            else:
                st.error("Product not found with this barcode")
    
    # Manual barcode entry as fallback
    st.subheader("Manual Barcode Entry")
    
    # Use a callback function to handle automatic addition
    def handle_barcode_input():
        manual_barcode = st.session_state.manual_barcode_input
        if manual_barcode and manual_barcode in products:
            product = products[manual_barcode]
            stock = inventory.get(manual_barcode, {}).get('quantity', 0)
            
            if stock > 0:
                if manual_barcode in st.session_state.cart:
                    st.session_state.cart[manual_barcode]['quantity'] += 1
                else:
                    st.session_state.cart[manual_barcode] = {
                        'name': product['name'],
                        'price': product['price'],
                        'quantity': 1,
                        'description': product.get('description', ''),
                        'brand': product.get('brand')
                    }
                st.success(f"Added {product['name']} to cart")
                # Clear the input field by resetting the session state
                st.session_state.manual_barcode_input = ""
            else:
                st.error(f"{product['name']} is out of stock")
        elif manual_barcode:
            st.error("Product not found with this barcode")
    
    # Text input with on_change callback
    manual_barcode = st.text_input(
        "Enter Barcode Manually", 
        key="manual_barcode_input",
        on_change=handle_barcode_input,
        placeholder="Scan or type barcode and press Enter"
    )
    
    # Display cart and checkout
    display_cart_and_checkout()

def pos_manual_mode():
    products = load_data(PRODUCTS_FILE)
    inventory = load_data(INVENTORY_FILE)
    categories = load_data(CATEGORIES_FILE)
    brands = load_data(BRANDS_FILE).get('brands', [])
    
    st.header("Manual Entry Mode")
    
    # Offer selection
    offers = load_data(OFFERS_FILE)
    active_offers = [o for o in offers.values() if o['active']]
    
    if active_offers:
        st.subheader("🎁 Active Offers")
        offer_options = {o['name']: o for o in active_offers}
        selected_offer = st.selectbox("Select Offer to Apply", [""] + list(offer_options.keys()))
        
        if selected_offer:
            st.info(f"Selected: {offer_options[selected_offer]['description']}")
    
    # Category, subcategory, and brand selection
    col1, col2, col3 = st.columns(3)
    with col1:
        selected_category = st.selectbox(
            "Select Category", 
            [""] + categories.get('categories', []),
            key="manual_category"
        )
    with col2:
        if selected_category:
            subcategories = categories.get('subcategories', {}).get(selected_category, [])
            selected_subcategory = st.selectbox(
                "Select Subcategory", 
                [""] + subcategories,
                key="manual_subcategory"
            )
        else:
            selected_subcategory = None
    with col3:
        selected_brand = st.selectbox("Filter by Brand", [""] + brands, key="manual_brand")
    
    # Display products based on category/subcategory/brand selection
    st.subheader("Products")
    
    filtered_products = {}
    for barcode, product in products.items():
        # Check category
        matches_category = not selected_category or product.get('category') == selected_category
        
        # Check subcategory
        matches_subcategory = not selected_subcategory or product.get('subcategory') == selected_subcategory
        
        # Check brand
        matches_brand = not selected_brand or product.get('brand') == selected_brand
        
        # Check stock
        stock = inventory.get(barcode, {}).get('quantity', 0)
        has_stock = stock > 0
        
        if matches_category and matches_subcategory and matches_brand and has_stock:
            filtered_products[barcode] = product
    
    if not filtered_products:
        st.info("No products found with the selected filters")
    else:
        cols_per_row = 3  # Fewer columns to accommodate quantity inputs
        product_list = list(filtered_products.items())
        
        for i in range(0, len(product_list), cols_per_row):
            cols = st.columns(cols_per_row)
            for col_idx in range(cols_per_row):
                if i + col_idx < len(product_list):
                    barcode, product = product_list[i + col_idx]
                    with cols[col_idx]:
                        with st.container():
                            # Product image
                            if 'image' in product and os.path.exists(product['image']):
                                try:
                                    img = Image.open(product['image'])
                                    img.thumbnail((150, 150))
                                    st.image(img, use_column_width=True)
                                except:
                                    pass
                            
                            # Product name and details
                            st.subheader(product['name'])
                            st.text(f"Price: {format_currency(product['price'])}")
                            
                            # Stock status
                            stock = inventory.get(barcode, {}).get('quantity', 0)
                            status = "In Stock" if stock > 0 else "Out of Stock"
                            color = "green" if stock > 0 else "red"
                            st.markdown(f"Status: <span style='color:{color}'>{status}</span>", unsafe_allow_html=True)
                            
                            # Brand and category
                            if product.get('brand'):
                                st.text(f"Brand: {product['brand']}")
                            if product.get('category'):
                                st.text(f"Category: {product.get('category')}")
                            
                            # Product description
                            if product.get('description'):
                                with st.expander("Description"):
                                    st.write(product['description'])
                            
                            # Quantity selection
                            quantity = st.number_input(
                                "Quantity", 
                                min_value=1, 
                                max_value=min(100, stock), 
                                value=1, 
                                key=f"qty_{barcode}"
                            )
                            
                            # Add to cart button
                            if st.button(f"Add to Cart", key=f"add_manual_{barcode}", use_container_width=True):
                                if barcode in st.session_state.cart:
                                    st.session_state.cart[barcode]['quantity'] += quantity
                                else:
                                    st.session_state.cart[barcode] = {
                                        'name': product['name'],
                                        'price': product['price'],
                                        'quantity': quantity,
                                        'description': product.get('description', ''),
                                        'brand': product.get('brand')
                                    }
                                st.success(f"Added {quantity} {product['name']} to cart")
    
    display_cart_and_checkout()
def display_cart_and_checkout():
    # Check if we just completed a sale and need to print
    if st.session_state.get('just_completed_sale', False) and st.session_state.get('receipt_to_print'):
        receipt_text = st.session_state.receipt_to_print
        # Clear the state first
        st.session_state.just_completed_sale = False
        st.session_state.receipt_to_print = None
        
        # Use JavaScript to print the receipt
        js_code = f"""
        <script>
        function printReceipt() {{
            const printWindow = window.open('', '_blank', 'width=400,height=600');
            const htmlContent = `
            <!DOCTYPE html>
            <html>
            <head>
                <title>Receipt</title>
                <style>
                    body {{
                        font-family: 'Courier New', monospace;
                        font-size: 12px;
                        padding: 10px;
                        line-height: 1.2;
                        white-space: pre-wrap;
                    }}
                    @media print {{
                        body {{
                            margin: 0;
                            padding: 10px;
                        }}
                    }}
                </style>
            </head>
            <body>
                <pre>{receipt_text}</pre>
            </body>
            </html>
            `;
            
            printWindow.document.write(htmlContent);
            printWindow.document.close();
            
            printWindow.onload = function() {{
                printWindow.print();
                setTimeout(() => printWindow.close(), 500);
            }};
        }}
        
        // Print immediately when page loads
        window.onload = function() {{
            setTimeout(printReceipt, 100);
        }};
        </script>
        """
        
        st.components.v1.html(js_code, height=0)
        return  # Early return to avoid showing the rest of the cart
    settings = load_data(SETTINGS_FILE)
    payment_charges = settings.get('payment_charges', {
        "cash": 0.0,
        "credit_card": 2.0,
        "debit_card": 1.0,
        "mobile_payment": 1.5,
        "bank_transfer": 0.5,
        "international_card": 3.0
    })
    
    st.header("Current Sale")
    
    # Initialize loyalty session state
    if 'loyalty_customer_id' not in st.session_state:
        st.session_state.loyalty_customer_id = None
    if 'loyalty_points_to_redeem' not in st.session_state:
        st.session_state.loyalty_points_to_redeem = 0
    if 'loyalty_customer_data' not in st.session_state:
        st.session_state.loyalty_customer_data = None
    
    # Create a copy of the cart items to avoid modification during iteration
    cart_items = list(st.session_state.cart.items())
    items_to_remove = []
    
    if cart_items:
        for barcode, item in cart_items:
            with st.container():
                col1, col2, col3, col4 = st.columns([4, 2, 2, 1])
                with col1:
                    st.write(f"**{item['name']}**")
                    if item.get('description'):
                        with st.expander("Description"):
                            st.write(item['description'])
                with col2:
                    new_qty = st.number_input(
                        "Qty", 
                        min_value=1, 
                        max_value=100, 
                        value=item['quantity'], 
                        key=f"edit_{barcode}"
                    )
                    if new_qty != item['quantity']:
                        st.session_state.cart[barcode]['quantity'] = new_qty
                with col3:
                    st.write(f"{format_currency(item['price'] * item['quantity'])}")
                with col4:
                    if st.button("❌", key=f"remove_{barcode}"):
                        items_to_remove.append(barcode)
        
        # Remove items after iteration is complete
        for barcode in items_to_remove:
            if barcode in st.session_state.cart:
                del st.session_state.cart[barcode]
        
        # Recalculate totals after potential changes
        subtotal = sum(item['price'] * item['quantity'] for item in st.session_state.cart.values())
        tax_rate = settings.get('tax_rate', 0.0)
        tax_amount = subtotal * tax_rate
        
        # Calculate total before offers and payment charges
        total_before_offers = subtotal + tax_amount
        
        # Apply offers only if selected
        offers = load_data(OFFERS_FILE)
        active_offers = [o for o in offers.values() if o['active']]
        
        # Check if any offer is selected in the session state
        selected_offer_name = st.session_state.get('selected_offer', None)
        selected_offer = None
        
        if selected_offer_name:
            for offer in active_offers:
                if offer['name'] == selected_offer_name:
                    selected_offer = offer
                    break
        
        # Apply the selected offer if any
        total_after_offers = total_before_offers
        if selected_offer:
            total_after_offers = apply_selected_offer(st.session_state.cart, total_before_offers, selected_offer)
        
        # Apply discounts
        discounts = load_data(DISCOUNTS_FILE)
        active_discounts = [d for d in discounts.values() if d['active']]
        
        final_total = total_after_offers
        
        if active_discounts:
            discount_options = {d['name']: d for d in active_discounts}
            selected_discount = st.selectbox("Apply Discount", [""] + list(discount_options.keys()))
            
            if selected_discount:
                discount = discount_options[selected_discount]
                if discount['type'] == 'percentage':
                    discount_amount = final_total * (discount['value'] / 100)
                else:
                    discount_amount = discount['value']
                
                final_total -= discount_amount
                st.write(f"Discount Applied: -{format_currency(discount_amount)}")
        
        # LOYALTY SECTION - Separate from the main sale processing
        st.markdown("---")
        st.subheader("Loyalty Program")
        
        loyalty_data = load_data(LOYALTY_FILE)
        customers = loyalty_data.get('customers', {})
        
        # Customer lookup form
        with st.form("loyalty_lookup_form"):
            col1, col2 = st.columns(2)
            with col1:
                customer_phone = st.text_input("Customer Phone", key="loyalty_phone_input")
            with col2:
                customer_id_input = st.text_input("Customer ID", key="customer_id_input")
            
            if st.form_submit_button("Find Customer", use_container_width=True):
                customer_found = None
                customer_id = None
                
                # Search by phone
                if customer_phone:
                    for cust_id, cust_data in customers.items():
                        if cust_data.get('phone') == customer_phone:
                            customer_found = cust_data
                            customer_id = cust_id
                            break
                
                # Search by ID
                if not customer_found and customer_id_input and customer_id_input in customers:
                    customer_found = customers[customer_id_input]
                    customer_id = customer_id_input
                
                if customer_found:
                    st.session_state.loyalty_customer_id = customer_id
                    st.session_state.loyalty_customer_data = customer_found
                    st.success(f"Customer found: {customer_found.get('name', 'Unknown')}")
                else:
                    st.session_state.loyalty_customer_id = None
                    st.session_state.loyalty_customer_data = None
                    st.warning("Customer not found")
        
        # Display customer info if found
        if st.session_state.loyalty_customer_data:
            customer = st.session_state.loyalty_customer_data
            st.info(f"**{customer.get('name', 'Unknown')}** - {customer.get('tier', 'Bronze')} Tier")
            st.info(f"Points: {customer.get('points', 0)}")
            
            # Points redemption
            max_points_to_redeem = customer.get('points', 0)
            points_value = loyalty_data.get('settings', {}).get('points_value', 0.01)
            
            if max_points_to_redeem > 0:
                st.session_state.loyalty_points_to_redeem = st.number_input(
                    "Points to redeem", 
                    min_value=0, 
                    max_value=min(max_points_to_redeem, int(final_total / points_value)),
                    value=st.session_state.loyalty_points_to_redeem,
                    step=10,
                    key="points_redeem_input"
                )
                
                if st.session_state.loyalty_points_to_redeem > 0:
                    points_discount = st.session_state.loyalty_points_to_redeem * points_value
                    final_total -= points_discount
                    st.success(f"Redeeming {st.session_state.loyalty_points_to_redeem} points: -{format_currency(points_discount)}")
        
        # Calculate loyalty points to earn (for display only)
        if st.session_state.loyalty_customer_id:
            points_per_dollar = loyalty_data.get('settings', {}).get('points_per_dollar', 1)
            loyalty_points_earned = int(final_total * points_per_dollar)
            st.info(f"Points to earn: {loyalty_points_earned}")
        
        # Apply tier discount if customer has a tier
        loyalty_discount_applied = 0
        if st.session_state.loyalty_customer_data:
            current_tier = st.session_state.loyalty_customer_data.get('tier', 'Bronze')
            tier_settings = loyalty_data.get('tiers', {}).get(current_tier, {})
            tier_discount = tier_settings.get('discount', 0)
            
            if tier_discount > 0:
                loyalty_discount_applied = final_total * tier_discount
                final_total -= loyalty_discount_applied
                st.success(f"Tier discount ({current_tier}): -{format_currency(loyalty_discount_applied)}")
        
        st.markdown("---")
        
        # PAYMENT SECTION
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Summary")
            st.write(f"Subtotal: {format_currency(subtotal)}")
            st.write(f"Tax ({tax_rate*100}%): {format_currency(tax_amount)}")
            if total_after_offers != total_before_offers:
                st.write(f"After Offers: {format_currency(total_after_offers)}")
            if final_total != total_after_offers:
                st.write(f"After Discount: {format_currency(final_total)}")
            if loyalty_discount_applied > 0:
                st.write(f"Loyalty Discount: -{format_currency(loyalty_discount_applied)}")
            st.write(f"**Total: {format_currency(final_total)}**")
        
        with col2:
            st.subheader("Payment")
            payment_method = st.selectbox("Payment Method", 
                                        ["Cash", "Credit Card", "Debit Card", "Mobile Payment", "Bank Transfer", "International Card"])
            
            # Calculate payment charge
            payment_method_key = payment_method.lower().replace(" ", "_")
            payment_charge_percent = payment_charges.get(payment_method_key, 0.0)
            payment_charge_amount = final_total * (payment_charge_percent / 100)
            
            total_with_payment_charge = final_total + payment_charge_amount
            
            if payment_charge_percent > 0:
                st.info(f"Payment Fee ({payment_charge_percent}%): +{format_currency(payment_charge_amount)}")
                st.write(f"**Amount Due: {format_currency(total_with_payment_charge)}**")
            
            amount_tendered = st.number_input("Amount Tendered", min_value=0.0, value=total_with_payment_charge, step=1.0)
            
            if st.button("Complete Sale", type="primary", use_container_width=True):
                if amount_tendered < total_with_payment_charge:
                    st.error("Amount tendered is less than total")
                else:
                    # Process the sale
                    success = process_sale(
                        st.session_state.cart,
                        payment_method,
                        payment_charge_percent,
                        payment_charge_amount,
                        amount_tendered,
                        selected_offer,
                        st.session_state.loyalty_customer_id,
                        st.session_state.loyalty_points_to_redeem,
                        loyalty_discount_applied
                    )
                    
                    if success:
                        st.success("Sale completed successfully!")
                        # Reset cart and loyalty state
                        st.session_state.cart = {}
                        st.session_state.selected_offer = None
                        st.session_state.loyalty_customer_id = None
                        st.session_state.loyalty_points_to_redeem = 0
                        st.session_state.loyalty_customer_data = None
                        st.rerun()
                    
    else:
        st.info("Cart is empty")

def process_sale(cart_items, payment_method, payment_charge_percent, payment_charge_amount, amount_tendered, selected_offer=None, customer_id=None, points_to_redeem=0, loyalty_discount=0):
    try:
        # Load necessary data
        products = load_data(PRODUCTS_FILE)
        inventory = load_data(INVENTORY_FILE)
        transactions = load_data(TRANSACTIONS_FILE)
        loyalty_data = load_data(LOYALTY_FILE)
        customers = loyalty_data.get('customers', {})
        
        # Calculate totals
        subtotal = sum(item['price'] * item['quantity'] for item in cart_items.values())
        tax_rate = load_data(SETTINGS_FILE).get('tax_rate', 0.0)
        tax_amount = subtotal * tax_rate
        total = subtotal + tax_amount
        
        # Apply discount if any
        discount_amount = 0
        if selected_offer:
            # Handle offer discount (this would be calculated based on the offer type)
            pass
        
        # Apply loyalty discount
        total -= loyalty_discount
        
        # Apply points redemption
        points_value = loyalty_data.get('settings', {}).get('points_value', 0.01)
        points_discount = points_to_redeem * points_value
        total -= points_discount
        
        # Add payment charge
        total_with_charge = total + payment_charge_amount
        change = amount_tendered - total_with_charge
        
        # Generate transaction ID
        transaction_id = generate_short_id()
        
        # Calculate loyalty points to earn
        loyalty_points_earned = 0
        if customer_id:
            points_per_dollar = loyalty_data.get('settings', {}).get('points_per_dollar', 1)
            loyalty_points_earned = int(total * points_per_dollar)
        
        # Create transaction record
        transaction = {
            'transaction_id': transaction_id,
            'date': get_current_datetime().strftime("%Y-%m-%d %H:%M:%S"),
            'cashier': st.session_state.user_info['username'],
            'items': cart_items.copy(),
            'subtotal': subtotal,
            'tax': tax_amount,
            'discount': discount_amount,
            'loyalty_discount': loyalty_discount,
            'points_discount': points_discount,
            'total': total,
            'payment_method': payment_method,
            'payment_charge_percent': payment_charge_percent,
            'payment_charge_amount': payment_charge_amount,
            'amount_tendered': amount_tendered,
            'change': change,
            'shift_id': st.session_state.shift_id if st.session_state.shift_started else None,
            'customer_id': customer_id,
            'loyalty_points_earned': loyalty_points_earned,
            'loyalty_points_redeemed': points_to_redeem
        }
        
        # Add offer information if applied
        if selected_offer:
            transaction['applied_offer'] = selected_offer['name']
        
        # Update inventory
        for barcode, item in cart_items.items():
            if barcode in inventory:
                inventory[barcode]['quantity'] -= item['quantity']
                inventory[barcode]['last_updated'] = get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
                inventory[barcode]['updated_by'] = st.session_state.user_info['username']
            else:
                st.error(f"Product {barcode} not found in inventory")
                return False
        
        # Update loyalty points
        if customer_id and customer_id in customers:
            # Calculate net points change
            net_points_change = loyalty_points_earned - points_to_redeem
            customers[customer_id]['points'] = customers[customer_id].get('points', 0) + net_points_change
            customers[customer_id]['last_activity'] = get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
            
            # Check for tier upgrade
            current_points = customers[customer_id]['points']
            current_tier = customers[customer_id].get('tier', 'Bronze')
            
            # Check all tiers to see if customer qualifies for upgrade
            tiers = loyalty_data.get('tiers', {})
            new_tier = current_tier
            for tier_name, tier_data in tiers.items():
                if current_points >= tier_data.get('min_points', 0):
                    # Check if this tier is higher than current
                    tier_order = list(tiers.keys())
                    if tier_order.index(tier_name) > tier_order.index(current_tier):
                        new_tier = tier_name
            
            if new_tier != current_tier:
                customers[customer_id]['tier'] = new_tier
            
            loyalty_data['customers'] = customers
            save_data(loyalty_data, LOYALTY_FILE)
        
        # Update cash drawer if payment is cash
        if payment_method == "Cash" and st.session_state.shift_started:
            cash_drawer = load_data(CASH_DRAWER_FILE)
            cash_drawer['current_balance'] += total_with_charge
            cash_drawer['transactions'].append({
                'type': 'sale',
                'amount': total_with_charge,
                'date': get_current_datetime().strftime("%Y-%m-%d %H:%M:%S"),
                'transaction_id': transaction_id,
                'processed_by': st.session_state.user_info['username']
            })
            save_data(cash_drawer, CASH_DRAWER_FILE)
        
        # Save all changes
        transactions[transaction_id] = transaction
        save_data(transactions, TRANSACTIONS_FILE)
        save_data(inventory, INVENTORY_FILE)
        
        # Generate and print receipt - THIS IS THE KEY CHANGE
        receipt_text = generate_receipt(transaction)
        
        # Store receipt in session state for printing after rerun
        st.session_state.receipt_to_print = receipt_text
        st.session_state.just_completed_sale = True
        
        # Open cash drawer if enabled
        if payment_method == "Cash":
            open_cash_drawer()
        
        return True
        
    except Exception as e:
        st.error(f"Error processing sale: {str(e)}")
        return False


def generate_receipt(transaction):
    settings = load_data(SETTINGS_FILE)
    receipt = ""
    
    # Header
    receipt += f"{settings.get('store_name', 'Supermarket POS')}\n"
    receipt += f"{settings.get('store_address', '')}\n"
    receipt += f"{settings.get('store_phone', '')}\n"
    receipt += "=" * 40 + "\n"
    
    if settings.get('receipt_header', ''):
        receipt += f"{settings['receipt_header']}\n"
        receipt += "=" * 40 + "\n"
    
    receipt += f"Date: {transaction['date']}\n"
    receipt += f"Cashier: {transaction['cashier']}\n"
    receipt += f"Transaction ID: {transaction['transaction_id']}\n"
    
    # Customer info if available
    if transaction.get('customer_id'):
        loyalty_data = load_data(LOYALTY_FILE)
        customer = loyalty_data.get('customers', {}).get(transaction['customer_id'], {})
        if customer:
            receipt += f"Customer: {customer.get('name', 'N/A')}\n"
            receipt += f"Loyalty ID: {transaction['customer_id']}\n"
    
    receipt += "=" * 40 + "\n"
    
    # Items
    for barcode, item in transaction['items'].items():
        receipt += f"{item['name']} x{item['quantity']}: {format_currency(item['price'] * item['quantity'])}\n"
    
    receipt += "=" * 40 + "\n"
    receipt += f"Subtotal: {format_currency(transaction['subtotal'])}\n"
    receipt += f"Tax: {format_currency(transaction['tax'])}\n"
    
    # Discounts
    if transaction.get('discount', 0) != 0:
        receipt += f"Discount: -{format_currency(abs(transaction['discount']))}\n"
    
    if transaction.get('loyalty_discount', 0) != 0:
        receipt += f"Loyalty Discount: -{format_currency(abs(transaction['loyalty_discount']))}\n"
    
    receipt += f"Total: {format_currency(transaction['total'])}\n"
    
    # Loyalty points
    if transaction.get('loyalty_points_earned', 0) > 0:
        receipt += f"Loyalty Points Earned: +{transaction['loyalty_points_earned']}\n"
    
    if transaction.get('loyalty_points_redeemed', 0) > 0:
        receipt += f"Loyalty Points Redeemed: -{transaction['loyalty_points_redeemed']}\n"
    
    # Show payment charge if any
    if transaction.get('payment_charge_amount', 0) > 0:
        receipt += f"Payment Fee ({transaction.get('payment_charge_percent', 0)}%): {format_currency(transaction['payment_charge_amount'])}\n"
        receipt += f"Amount Due: {format_currency(transaction['total'] + transaction['payment_charge_amount'])}\n"
    
    receipt += f"Payment Method: {transaction['payment_method']}\n"
    receipt += f"Amount Tendered: {format_currency(transaction['amount_tendered'])}\n"
    receipt += f"Change: {format_currency(transaction['change'])}\n"
    receipt += "=" * 40 + "\n"
    
    # Loyalty summary
    if transaction.get('customer_id'):
        loyalty_data = load_data(LOYALTY_FILE)
        customer = loyalty_data.get('customers', {}).get(transaction['customer_id'], {})
        if customer:
            receipt += f"Total Points: {customer.get('points', 0)}\n"
            receipt += f"Tier: {customer.get('tier', 'Bronze')}\n"
    
    if settings.get('receipt_footer', ''):
        receipt += f"{settings['receipt_footer']}\n"
        receipt += "=" * 40 + "\n"
    
    receipt += "Thank you for shopping with us!\n"
    
    return receipt

# Add this function to initialize loyalty settings if they don't exist
def initialize_loyalty_settings():
    loyalty_data = load_data(LOYALTY_FILE)
    
    if 'settings' not in loyalty_data:
        loyalty_data['settings'] = {
            'points_per_dollar': 1,  # 1 point per $1 spent
            'points_value': 0.01,    # 1 point = $0.01
            'signup_bonus': 100,     # 100 points for signing up
            'min_redemption': 100,   # Minimum 100 points to redeem
            'points_expiry_days': 365  # Points expire after 1 year
        }
    
    if 'tiers' not in loyalty_data:
        loyalty_data['tiers'] = {
            'Bronze': {
                'min_points': 0,
                'discount': 0.0,
                'benefits': ['Basic rewards']
            },
            'Silver': {
                'min_points': 1000,
                'discount': 0.05,  # 5% discount
                'benefits': ['5% discount', 'Early access to sales']
            },
            'Gold': {
                'min_points': 5000,
                'discount': 0.10,  # 10% discount
                'benefits': ['10% discount', 'Free delivery', 'Birthday rewards']
            },
            'Platinum': {
                'min_points': 10000,
                'discount': 0.15,  # 15% discount
                'benefits': ['15% discount', 'Personal shopper', 'VIP events']
            }
        }
    
    save_data(loyalty_data, LOYALTY_FILE)

# Call this function during initialization
initialize_loyalty_settings()
def apply_selected_offer(cart_items, current_total, offer):
    """
    Apply a specific selected offer to the cart
    """
    products = load_data(PRODUCTS_FILE)
    total_after_offer = current_total
    
    if offer['type'] == 'bogo':
        # Buy One Get One Free offer
        for barcode, item in cart_items.items():
            if barcode in offer.get('products', []):
                if item['quantity'] >= offer['buy_quantity']:
                    free_qty = (item['quantity'] // offer['buy_quantity']) * offer['get_quantity']
                    discount_amount = free_qty * item['price']
                    total_after_offer -= discount_amount
    
    elif offer['type'] == 'bundle':
        # Bundle offer - check if all bundle products are in cart
        bundle_products = offer.get('products', [])
        if all(barcode in cart_items for barcode in bundle_products):
            bundle_price = offer.get('bundle_price', 0)
            original_price = sum(cart_items[barcode]['price'] * cart_items[barcode]['quantity'] 
                               for barcode in bundle_products)
            discount_amount = original_price - bundle_price
            total_after_offer -= discount_amount
    
    elif offer['type'] == 'special_price':
        # Special price offer
        product_barcode = offer.get('product')
        if product_barcode in cart_items:
            special_price = offer.get('special_price', 0)
            original_price = cart_items[product_barcode]['price']
            quantity = cart_items[product_barcode]['quantity']
            discount_amount = (original_price - special_price) * quantity
            total_after_offer -= discount_amount
    
    elif offer['type'] == 'percentage_discount':
        # Percentage discount offer
        discount_percent = offer.get('discount_percent', 0) / 100
        applicable_products = []
        
        if offer.get('apply_to_all', False):
            # Apply to all products
            applicable_products = list(cart_items.keys())
        else:
            # Apply to specific products
            applicable_products = offer.get('products', [])
        
        for barcode in applicable_products:
            if barcode in cart_items:
                item = cart_items[barcode]
                discount_amount = item['price'] * item['quantity'] * discount_percent
                total_after_offer -= discount_amount
    
    elif offer['type'] == 'fixed_discount':
        # Fixed amount discount offer
        discount_amount_per_item = offer.get('discount_amount', 0)
        applicable_products = []
        
        if offer.get('apply_to_all', False):
            # Apply to all products
            applicable_products = list(cart_items.keys())
        else:
            # Apply to specific products
            applicable_products = offer.get('products', [])
        
        for barcode in applicable_products:
            if barcode in cart_items:
                item = cart_items[barcode]
                total_discount = discount_amount_per_item * item['quantity']
                total_after_offer -= total_discount
    
    return max(total_after_offer, 0)  # Ensure total doesn't go negative


# Outdoor Sales Module
# Outdoor Sales Module - Fixed without rerun
def outdoor_sales_portal():
    if not is_cashier():
        st.warning("You don't have permission to access this page")
        return
    
    # Initialize session state
    if 'outdoor_cart' not in st.session_state:
        st.session_state.outdoor_cart = {}
    if 'current_order_id' not in st.session_state:
        st.session_state.current_order_id = None
    if 'print_requested' not in st.session_state:
        st.session_state.print_requested = False
    if 'order_to_print' not in st.session_state:
        st.session_state.order_to_print = None
    if 'print_type' not in st.session_state:
        st.session_state.print_type = 'browser_printer'
    if 'show_cart' not in st.session_state:
        st.session_state.show_cart = True
    
    # Handle print requests if any
    if st.session_state.get('print_requested', False) and st.session_state.get('order_to_print'):
        handle_print_requests()
        return
    
    st.title("🛒 Outdoor Sales POS")
    
    # Load data
    outdoor_orders_data = load_data(OUTDOOR_ORDERS_FILE)
    if 'orders' not in outdoor_orders_data:
        outdoor_orders_data['orders'] = {}
    if 'delivery_charges' not in outdoor_orders_data:
        outdoor_orders_data['delivery_charges'] = {
            "standard": 5.0,
            "express": 10.0,
            "free_threshold": 50.0
        }
        save_data(outdoor_orders_data, OUTDOOR_ORDERS_FILE)
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 Create Order", 
        "📦 My Orders", 
        "⏳ Approval Queue", 
        "🚚 Delivery Management",
        "⚙️ Delivery Settings"
    ])
    
    with tab1:
        create_order_tab(outdoor_orders_data)
    
    with tab2:
        my_orders_tab()
    
    with tab3:
        approval_queue_tab()
    
    with tab4:
        delivery_management_tab()
    
    with tab5:
        delivery_settings_tab(outdoor_orders_data)

def create_order_tab(outdoor_orders_data):
    st.header("Create Outdoor Order")
    
    # Use a unique key for this tab to prevent conflicts
    tab_key = "create_order_tab"
    
    # Quick action buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔄 Clear Cart", key=f"clear_cart_{tab_key}", use_container_width=True):
            st.session_state.outdoor_cart = {}
    with col2:
        if st.button("📋 View Cart", key=f"view_cart_{tab_key}", use_container_width=True):
            st.session_state.show_cart = not st.session_state.get('show_cart', True)
    
    products = load_data(PRODUCTS_FILE)
    inventory = load_data(INVENTORY_FILE)
    customers = load_data(LOYALTY_FILE).get('customers', {})
    delivery_charges = outdoor_orders_data.get('delivery_charges', {
        "standard": 5.0,
        "express": 10.0,
        "free_threshold": 50.0
    })
    
    # Load payment charges from settings
    settings = load_data(SETTINGS_FILE)
    payment_charges = settings.get('payment_charges', {
        "cash": 0.0,
        "credit_card": 2.0,
        "debit_card": 1.0,
        "mobile_payment": 1.5,
        "bank_transfer": 0.5,
        "international_card": 3.0
    })
    
    # Customer section
    st.subheader("👤 Customer Information")
    customer_options = {f"{v['name']} - {v.get('phone', 'No phone')}": k for k, v in customers.items()}
    customer_options["➕ New Customer"] = "new"
    
    selected_customer = st.selectbox("Select Customer", [""] + list(customer_options.keys()), key=f"customer_select_{tab_key}")
    
    customer_info = {}
    if selected_customer == "➕ New Customer":
        col1, col2 = st.columns(2)
        with col1:
            customer_info['name'] = st.text_input("Customer Name*", key=f"new_cust_name_{tab_key}")
        with col2:
            customer_info['phone'] = st.text_input("Customer Phone*", key=f"new_cust_phone_{tab_key}")
        col1, col2 = st.columns(2)
        with col1:
            customer_info['email'] = st.text_input("Customer Email", key=f"new_cust_email_{tab_key}")
        with col2:
            customer_info['address'] = st.text_input("Customer Address", key=f"new_cust_address_{tab_key}")
    elif selected_customer:
        customer_id = customer_options[selected_customer]
        customer_info = customers[customer_id]
    
    # Product search and selection
    st.subheader("🛍️ Product Selection")
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search_term = st.text_input("🔍 Search Products", placeholder="Name or barcode...", key=f"search_{tab_key}")
    with col2:
        categories = load_data(CATEGORIES_FILE).get('categories', [])
        selected_category = st.selectbox("Category", [""] + categories, key=f"category_{tab_key}")
    with col3:
        brands = load_data(BRANDS_FILE)
        brand_options = [""] + brands.get('brands', [])
        selected_brand = st.selectbox("Brand", brand_options, key=f"brand_{tab_key}")
    
    # Filter products
    filtered_products = {}
    for barcode, product in products.items():
        matches_search = not search_term or (
            search_term.lower() in product['name'].lower() or 
            search_term.lower() in barcode.lower()
        )
        matches_category = not selected_category or product.get('category') == selected_category
        matches_brand = not selected_brand or product.get('brand') == selected_brand
        has_stock = inventory.get(barcode, {}).get('quantity', 0) > 0
        
        if matches_search and matches_category and matches_brand and has_stock:
            filtered_products[barcode] = product
    
    # Display products in grid
    st.subheader("Available Products")
    if not filtered_products:
        st.info("No products match your search criteria")
    else:
        cols = st.columns(4)
        for idx, (barcode, product) in enumerate(filtered_products.items()):
            with cols[idx % 4]:
                with st.container():
                    # Product card
                    st.markdown(f"**{product['name']}**")
                    st.write(f"Price: {format_currency(product['price'])}")
                    
                    stock = inventory.get(barcode, {}).get('quantity', 0)
                    status_color = "green" if stock > 10 else "orange" if stock > 0 else "red"
                    st.markdown(f"Stock: <span style='color:{status_color}'>{stock}</span>", unsafe_allow_html=True)
                    
                    if product.get('brand'):
                        st.write(f"Brand: {product['brand']}")
                    
                    # Add to cart with proper state management
                    quantity = st.number_input("Qty", 0, stock, 1, key=f"qty_{barcode}_{tab_key}")
                    
                    if st.button(f"➕ Add to Cart", key=f"add_{barcode}_{tab_key}", use_container_width=True):
                        if barcode in st.session_state.outdoor_cart:
                            st.session_state.outdoor_cart[barcode]['quantity'] += quantity
                        else:
                            st.session_state.outdoor_cart[barcode] = {
                                'name': product['name'],
                                'price': product['price'],
                                'quantity': quantity,
                                'brand': product.get('brand')
                            }
                        st.success(f"Added {quantity} {product['name']}")
    
    # Display current cart
    if st.session_state.get('show_cart', True) and st.session_state.outdoor_cart:
        st.subheader("🛒 Current Order Cart")
        
        # Display cart items
        for barcode, item in st.session_state.outdoor_cart.items():
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            with col1:
                st.write(f"**{item['name']}**")
            with col2:
                st.write(f"Qty: {item['quantity']}")
            with col3:
                st.write(f"{format_currency(item['price'] * item['quantity'])}")
            with col4:
                if st.button("❌", key=f"remove_{barcode}_{tab_key}"):
                    del st.session_state.outdoor_cart[barcode]
        
        # Calculate totals
        subtotal = sum(item['price'] * item['quantity'] for item in st.session_state.outdoor_cart.values())
        
        # Delivery options
        st.subheader("🚚 Delivery Options")
        col1, col2 = st.columns(2)
        with col1:
            delivery_type = st.selectbox(
                "Delivery Type", 
                ["Standard", "Express", "Pickup"],
                help="Standard: 3-5 business days, Express: Next day, Pickup: Customer picks up",
                key=f"delivery_type_{tab_key}"
            )
        
        # Calculate delivery charges
        delivery_charge = 0
        if delivery_type == "Standard":
            delivery_charge = delivery_charges['standard']
            if subtotal >= delivery_charges['free_threshold']:
                delivery_charge = 0
                st.success("🎉 Free standard delivery!")
        elif delivery_type == "Express":
            delivery_charge = delivery_charges['express']
        
        with col2:
            # FIXED: Removed 'key' parameter from st.metric()
            st.metric("Delivery Charge", format_currency(delivery_charge))
        
        # Payment method
        st.subheader("💳 Payment Method")
        payment_method = st.selectbox(
            "Select Payment Method", 
            ["Cash", "Credit Card", "Debit Card", "Mobile Payment", "Bank Transfer", "International Card"],
            key=f"payment_method_{tab_key}"
        )
        
        # Calculate payment charge
        payment_method_key = payment_method.lower().replace(" ", "_")
        payment_charge_percent = payment_charges.get(payment_method_key, 0.0)
        payment_charge_amount = subtotal * (payment_charge_percent / 100)
        
        if payment_charge_percent > 0:
            st.info(f"ℹ️ {payment_method} fee: {payment_charge_percent}% ({format_currency(payment_charge_amount)})")
        
        total = subtotal + delivery_charge + payment_charge_amount
        
        # Display order summary
        st.subheader("💰 Order Summary")
        col1, col2 = st.columns(2)
        with col1:
            # FIXED: Removed 'key' parameter from st.metric()
            st.metric("Subtotal", format_currency(subtotal))
            st.metric("Delivery", format_currency(delivery_charge))
            if payment_charge_amount > 0:
                st.metric("Payment Fee", format_currency(payment_charge_amount))
        with col2:
            # FIXED: Removed 'key' parameter from st.metric()
            st.metric("Total", format_currency(total), delta=None)
        
        # Delivery address
        st.subheader("🏠 Delivery Address")
        if selected_customer and selected_customer != "➕ New Customer" and customer_info.get('address'):
            delivery_address = st.text_area("Address", value=customer_info.get('address', ''), key=f"address_{tab_key}")
        else:
            delivery_address = st.text_area("Address*", placeholder="Enter delivery address...", key=f"address_input_{tab_key}")
        
        # Notes
        order_notes = st.text_area("📝 Order Notes", placeholder="Special instructions...", key=f"notes_{tab_key}")
        
        # Submit order
        if st.button("✅ Submit Order for Approval", type="primary", key=f"submit_{tab_key}", use_container_width=True):
            if not st.session_state.outdoor_cart:
                st.error("❌ Order cart is empty")
            elif not selected_customer or (selected_customer == "➕ New Customer" and 
                                         (not customer_info.get('name') or not customer_info.get('phone'))):
                st.error("❌ Customer information is required")
            elif not delivery_address:
                st.error("❌ Delivery address is required")
            else:
                success = create_outdoor_order(
                    selected_customer,
                    customer_options if selected_customer != "➕ New Customer" else None,
                    customer_info,
                    delivery_type,
                    delivery_charge,
                    payment_method,
                    payment_charge_percent,
                    payment_charge_amount,
                    delivery_address,
                    order_notes,
                    total
                )
                if success:
                    st.session_state.outdoor_cart = {}
                    st.session_state.current_order_id = success
                    st.success("✅ Order submitted for approval!")
                    
                    # Store order for printing
                    outdoor_orders_data = load_data(OUTDOOR_ORDERS_FILE)
                    st.session_state.print_requested = True
                    st.session_state.order_to_print = outdoor_orders_data['orders'][success]
                    st.session_state.print_type = "browser_printer"

def my_orders_tab():
    st.header("My Orders")
    
    outdoor_orders_data = load_data(OUTDOOR_ORDERS_FILE)
    outdoor_orders = outdoor_orders_data.get('orders', {})
    user_orders = [o for o in outdoor_orders.values() if o['created_by'] == st.session_state.user_info['username']]
    
    if not user_orders:
        st.info("You haven't created any outdoor orders yet")
        return
    
    # Filter options
    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.selectbox("Filter by Status", 
                                   ["All", "pending_approval", "approved", "rejected", "delivered", "returned"],
                                   key="status_filter_my_orders")
    with col2:
        sort_by = st.selectbox("Sort By", ["Date (Newest)", "Date (Oldest)", "Total (High)", "Total (Low)"],
                              key="sort_by_my_orders")
    
    # Apply filters
    filtered_orders = user_orders
    if status_filter != "All":
        filtered_orders = [o for o in filtered_orders if o['status'] == status_filter]
    
    # Apply sorting
    if sort_by == "Date (Newest)":
        filtered_orders.sort(key=lambda x: x['created_date'], reverse=True)
    elif sort_by == "Date (Oldest)":
        filtered_orders.sort(key=lambda x: x['created_date'])
    elif sort_by == "Total (High)":
        filtered_orders.sort(key=lambda x: x['total'], reverse=True)
    elif sort_by == "Total (Low)":
        filtered_orders.sort(key=lambda x: x['total'])
    
    for i, order in enumerate(filtered_orders):
        with st.expander(f"Order #{order['order_id']} - {order['status'].replace('_', ' ').title()} - {format_currency(order['total'])}"):
            display_order_details(order, "my_orders", i, "my_orders")

def approval_queue_tab():
    if not is_manager():
        st.warning("You need manager privileges to access the approval queue")
        return
    
    st.header("Approval Queue")
    
    outdoor_orders_data = load_data(OUTDOOR_ORDERS_FILE)
    outdoor_orders = outdoor_orders_data.get('orders', {})
    pending_orders = [o for o in outdoor_orders.values() if o['status'] == 'pending_approval']
    
    if not pending_orders:
        st.info("No orders pending approval")
        return
    
    for i, order in enumerate(pending_orders):
        with st.expander(f"Order #{order['order_id']} - {order['customer_name']} - {format_currency(order['total'])}"):
            display_order_details(order, "approval", i, "approval")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Approve", key=f"approve_{order['order_id']}", use_container_width=True):
                    approve_order(order['order_id'])
            with col2:
                if st.button("❌ Reject", key=f"reject_{order['order_id']}", use_container_width=True):
                    reject_order(order['order_id'])

def delivery_management_tab():
    st.header("Delivery Management")
    
    outdoor_orders_data = load_data(OUTDOOR_ORDERS_FILE)
    outdoor_orders = outdoor_orders_data.get('orders', {})
    approved_orders = [o for o in outdoor_orders.values() if o['status'] == 'approved']
    
    if not approved_orders:
        st.info("No orders ready for delivery")
        return
    
    for i, order in enumerate(approved_orders):
        with st.expander(f"Order #{order['order_id']} - {order['customer_name']} - {format_currency(order['total'])}"):
            display_order_details(order, "delivery", i, "delivery")
            
            if st.button("🚚 Mark as Delivered", key=f"deliver_{order['order_id']}", use_container_width=True):
                mark_as_delivered(order['order_id'])

def delivery_settings_tab(outdoor_orders_data):
    if not is_manager():
        st.warning("You need manager privileges to access delivery settings")
        return
    
    st.header("Delivery Settings")
    
    delivery_charges = outdoor_orders_data.get('delivery_charges', {
        "standard": 5.0,
        "express": 10.0,
        "free_threshold": 50.0
    })
    
    with st.form("delivery_settings_form"):
        st.subheader("Delivery Charges Configuration")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            standard_charge = st.number_input(
                "Standard Delivery Charge",
                min_value=0.0,
                value=float(delivery_charges.get('standard', 5.0)),
                step=0.5,
                key="standard_charge"
            )
        with col2:
            express_charge = st.number_input(
                "Express Delivery Charge",
                min_value=0.0,
                value=float(delivery_charges.get('express', 10.0)),
                step=0.5,
                key="express_charge"
            )
        with col3:
            free_threshold = st.number_input(
                "Free Delivery Threshold",
                min_value=0.0,
                value=float(delivery_charges.get('free_threshold', 50.0)),
                step=1.0,
                key="free_threshold"
            )
        
        if st.form_submit_button("💾 Save Delivery Settings"):
            outdoor_orders_data['delivery_charges'] = {
                'standard': standard_charge,
                'express': express_charge,
                'free_threshold': free_threshold
            }
            save_data(outdoor_orders_data, OUTDOOR_ORDERS_FILE)
            st.success("Delivery settings saved successfully")

# ... rest of the helper functions remain the same but also remove any st.rerun() calls

def display_order_details(order, tab_id, index, tab_type):
    """Display order details in a standardized format"""
    st.write(f"**Customer:** {order['customer_name']}")
    st.write(f"**Phone:** {order.get('customer_phone', 'N/A')}")
    st.write(f"**Delivery Address:** {order['delivery_address']}")
    st.write(f"**Delivery Type:** {order['delivery_type']}")
    st.write(f"**Payment Method:** {order['payment_method']}")
    
    if order.get('payment_charge_percent', 0) > 0:
        st.write(f"**Payment Fee:** {order['payment_charge_percent']}% ({format_currency(order.get('payment_charge_amount', 0))})")
    
    st.write(f"**Created:** {order['created_date']} by {order['created_by']}")
    st.write(f"**Status:** {order['status'].replace('_', ' ').title()}")
    
    if order['status'] == 'approved' and order.get('approved_by'):
        st.write(f"**Approved:** {order['approved_date']} by {order['approved_by']}")
    
    if order['status'] == 'delivered' and order.get('delivered_by'):
        st.write(f"**Delivered:** {order['delivery_date']} by {order['delivered_by']}")
    
    st.write("**Items:**")
    for barcode, item in order['items'].items():
        st.write(f"- {item['name']} x{item['quantity']} @ {format_currency(item['price'])} each")
    
    st.write(f"**Subtotal:** {format_currency(order['subtotal'])}")
    st.write(f"**Delivery Charge:** {format_currency(order['delivery_charge'])}")
    st.write(f"**Total:** {format_currency(order['total'])}")
    
    # Print button with unique key that includes tab type
    if st.button("🖨️ Print Receipt", key=f"print_{order['order_id']}_{tab_id}_{index}_{tab_type}"):
        st.session_state.print_requested = True
        st.session_state.order_to_print = order
        st.session_state.print_type = "browser_printer"
        st.rerun()

# Helper functions
def create_outdoor_order(selected_customer, customer_options, customer_info, delivery_type, 
                        delivery_charge, payment_method, payment_charge_percent, 
                        payment_charge_amount, delivery_address, order_notes, total):
    try:
        outdoor_orders_data = load_data(OUTDOOR_ORDERS_FILE)
        order_id = generate_short_id()
        
        # Handle customer
        if selected_customer == "➕ New Customer":
            loyalty_data = load_data(LOYALTY_FILE)
            customer_id = generate_short_id()
            loyalty_data['customers'][customer_id] = {
                'id': customer_id,
                'name': customer_info['name'],
                'phone': customer_info['phone'],
                'email': customer_info.get('email', ''),
                'address': customer_info.get('address', ''),
                'points': 0,
                'tier': 'Bronze',
                'date_added': get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
            }
            save_data(loyalty_data, LOYALTY_FILE)
        else:
            customer_id = customer_options[selected_customer]
            customers = load_data(LOYALTY_FILE).get('customers', {})
            customer_name = customers[customer_id]['name']
            customer_phone = customers[customer_id].get('phone', '')
        
        # Create order
        outdoor_orders_data['orders'][order_id] = {
            'order_id': order_id,
            'customer_id': customer_id,
            'customer_name': customer_info['name'] if selected_customer == "➕ New Customer" else customer_name,
            'customer_phone': customer_info['phone'] if selected_customer == "➕ New Customer" else customer_phone,
            'items': st.session_state.outdoor_cart.copy(),
            'subtotal': sum(item['price'] * item['quantity'] for item in st.session_state.outdoor_cart.values()),
            'delivery_charge': delivery_charge,
            'payment_method': payment_method,
            'payment_charge_percent': payment_charge_percent,
            'payment_charge_amount': payment_charge_amount,
            'delivery_type': delivery_type,
            'total': total,
            'delivery_address': delivery_address,
            'notes': order_notes,
            'status': 'pending_approval',
            'created_by': st.session_state.user_info['username'],
            'created_date': get_current_datetime().strftime("%Y-%m-%d %H:%M:%S"),
            'approved_by': None,
            'approved_date': None,
            'delivered_by': None,
            'delivery_date': None
        }
        
        save_data(outdoor_orders_data, OUTDOOR_ORDERS_FILE)
        return order_id
        
    except Exception as e:
        st.error(f"Error creating order: {str(e)}")
        return False

def approve_order(order_id):
    outdoor_orders_data = load_data(OUTDOOR_ORDERS_FILE)
    outdoor_orders_data['orders'][order_id]['status'] = 'approved'
    outdoor_orders_data['orders'][order_id]['approved_by'] = st.session_state.user_info['username']
    outdoor_orders_data['orders'][order_id]['approved_date'] = get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
    save_data(outdoor_orders_data, OUTDOOR_ORDERS_FILE)
    st.success("Order approved")
    st.rerun()

def reject_order(order_id):
    outdoor_orders_data = load_data(OUTDOOR_ORDERS_FILE)
    outdoor_orders_data['orders'][order_id]['status'] = 'rejected'
    outdoor_orders_data['orders'][order_id]['approved_by'] = st.session_state.user_info['username']
    outdoor_orders_data['orders'][order_id]['approved_date'] = get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
    save_data(outdoor_orders_data, OUTDOOR_ORDERS_FILE)
    st.success("Order rejected")
    st.rerun()

def mark_as_delivered(order_id):
    outdoor_orders_data = load_data(OUTDOOR_ORDERS_FILE)
    order = outdoor_orders_data['orders'][order_id]
    
    outdoor_orders_data['orders'][order_id]['status'] = 'delivered'
    outdoor_orders_data['orders'][order_id]['delivered_by'] = st.session_state.user_info['username']
    outdoor_orders_data['orders'][order_id]['delivery_date'] = get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
    
    # Update inventory
    inventory = load_data(INVENTORY_FILE)
    for barcode, item in order['items'].items():
        if barcode in inventory:
            inventory[barcode]['quantity'] -= item['quantity']
            inventory[barcode]['last_updated'] = get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
            inventory[barcode]['updated_by'] = st.session_state.user_info['username']
    
    save_data(outdoor_orders_data, OUTDOOR_ORDERS_FILE)
    save_data(inventory, INVENTORY_FILE)
    st.success("Order marked as delivered. Inventory updated.")
    st.rerun()

def handle_print_requests():
    """Handle print requests after page rerun"""
    if st.session_state.get('print_requested', False) and st.session_state.get('order_to_print'):
        order_data = st.session_state.order_to_print
        print_type = st.session_state.get('print_type', 'browser_printer')
        
        with st.container():
            st.info("🖨️ Processing print request...")
            
            if print_type == 'browser_printer':
                success = print_pos_receipt(order_data)
            elif print_type == 'pdf_download':
                success = download_pdf_receipt(order_data)
            elif print_type == 'text_receipt':
                success = download_text_receipt(order_data)
            else:
                success = print_pos_receipt(order_data)
            
            if success:
                st.success("✅ Receipt printed successfully!")
            else:
                st.warning("⚠️ Could not print automatically. Use download options.")
            
            # Continue button with unique key
            if st.button("➡️ Continue", key=f"continue_print_{st.session_state.tab_counter}"):
                st.session_state.print_requested = False
                st.session_state.order_to_print = None
                st.rerun()
                
def print_pos_receipt(order_data):
    """POS-style receipt printing"""
    try:
        settings = load_data(SETTINGS_FILE)
        receipt_content = generate_pos_receipt_html(order_data, settings)
        
        js_code = f"""
        <script>
        function printReceipt() {{
            const printWindow = window.open('', '_blank', 'width=380,height=600,toolbar=no,menubar=no');
            
            printWindow.document.write(`{receipt_content}`);
            printWindow.document.close();
            
            setTimeout(() => {{
                printWindow.print();
                setTimeout(() => printWindow.close(), 1000);
            }}, 300);
            
            return true;
        }}
        
        printReceipt();
        </script>
        """
        
        st.components.v1.html(js_code, height=0)
        return True
        
    except Exception as e:
        st.error(f"Printing error: {str(e)}")
        return False

def generate_pos_receipt_html(order_data, settings):
    """Generate POS-style receipt HTML"""
    store_name = settings.get('store_name', 'SUPERMARKET POS')
    store_address = settings.get('store_address', '')
    store_phone = settings.get('store_phone', '')
    
    items_html = ""
    for item in order_data['items'].values():
        items_html += f"""
        <div style="display: flex; justify-content: space-between; margin: 2px 0; font-size: 11px;">
            <div>{item['name'][:20]}{'...' if len(item['name']) > 20 else ''}</div>
            <div>{item['quantity']} x {format_currency(item['price'])}</div>
            <div>{format_currency(item['price'] * item['quantity'])}</div>
        </div>
        """
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Receipt #{order_data['order_id']}</title>
        <style>
            @media print {{
                body {{
                    font-family: 'Courier New', monospace;
                    font-size: 12px;
                    width: 80mm;
                    margin: 0;
                    padding: 5mm;
                    line-height: 1.2;
                }}
                .header {{ text-align: center; margin-bottom: 10px; }}
                .divider {{ border-top: 1px dashed #000; margin: 8px 0; }}
                .total-row {{ border-top: 2px solid #000; padding-top: 5px; font-weight: bold; }}
                .footer {{ text-align: center; margin-top: 15px; font-size: 10px; }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2 style="margin: 5px 0; font-size: 14px;">{store_name}</h2>
            <div style="font-size: 10px;">{store_address}</div>
            <div style="font-size: 10px;">Tel: {store_phone}</div>
        </div>
        
        <div class="divider"></div>
        
        <div style="text-align: center; font-weight: bold;">
            OUTDOOR ORDER RECEIPT
        </div>
        
        <div style="display: flex; justify-content: space-between; font-size: 11px;">
            <div>Order #: {order_data['order_id']}</div>
            <div>{order_data['created_date']}</div>
        </div>
        
        <div class="divider"></div>
        
        <div style="font-size: 11px;">
            <div><strong>Customer:</strong> {order_data['customer_name']}</div>
            <div><strong>Phone:</strong> {order_data.get('customer_phone', 'N/A')}</div>
            <div><strong>Delivery:</strong> {order_data['delivery_type']}</div>
        </div>
        
        <div class="divider"></div>
        
        <div style="font-weight: bold; display: flex; justify-content: space-between; font-size: 11px;">
            <div>ITEM</div>
            <div>QTY</div>
            <div>AMOUNT</div>
        </div>
        
        <div class="divider"></div>
        
        {items_html}
        
        <div class="divider"></div>
        
        <div style="display: flex; justify-content: space-between; font-size: 11px;">
            <div>Subtotal:</div>
            <div>{format_currency(order_data['subtotal'])}</div>
        </div>
        
        <div style="display: flex; justify-content: space-between; font-size: 11px;">
            <div>Delivery:</div>
            <div>{format_currency(order_data['delivery_charge'])}</div>
        </div>
        
        {"".join([f'<div style="display: flex; justify-content: space-between; font-size: 11px;"><div>Payment Fee ({order_data["payment_charge_percent"]}%):</div><div>{format_currency(order_data["payment_charge_amount"])}</div></div>' if order_data.get('payment_charge_amount', 0) > 0 else ''])}
        
        <div class="total-row" style="display: flex; justify-content: space-between; font-size: 12px;">
            <div><strong>TOTAL:</strong></div>
            <div><strong>{format_currency(order_data['total'])}</strong></div>
        </div>
        
        <div style="font-size: 10px; margin-top: 5px;">
            <div>Payment: {order_data['payment_method']}</div>
            <div>Status: {order_data['status'].replace('_', ' ').title()}</div>
        </div>
        
        <div class="divider"></div>
        
        <div style="font-size: 10px;">
            <div><strong>Delivery Address:</strong></div>
            <div>{order_data['delivery_address']}</div>
        </div>
        
        {"".join([f'<div style="font-size: 10px; margin-top: 5px;"><strong>Notes:</strong> {order_data["notes"]}</div>' if order_data.get('notes') else ''])}
        
        <div class="footer">
            <div>Thank you for your order!</div>
            <div>{get_current_datetime().strftime('%Y-%m-%d %H:%M:%S')}</div>
            <div>Printed by: {order_data['created_by']}</div>
        </div>
    </body>
    </html>
    """

def download_pdf_receipt(order_data):
    """Download PDF receipt"""
    try:
        settings = load_data(SETTINGS_FILE)
        pdf = FPDF.FPDF(format=(80, 200))  # POS receipt size
        pdf.add_page()
        pdf.set_font("Courier", size=10)
        
        # Store header
        pdf.cell(0, 5, settings.get('store_name', 'SUPERMARKET POS'), 0, 1, 'C')
        pdf.set_font("Courier", size=8)
        pdf.cell(0, 4, settings.get('store_address', ''), 0, 1, 'C')
        pdf.cell(0, 4, f"Tel: {settings.get('store_phone', '')}", 0, 1, 'C')
        
        pdf.ln(2)
        pdf.set_font("Courier", size=10)
        pdf.cell(0, 5, "OUTDOOR ORDER RECEIPT", 0, 1, 'C')
        pdf.line(10, pdf.get_y(), 70, pdf.get_y())
        pdf.ln(2)
        
        # Order info
        pdf.cell(0, 4, f"Order #: {order_data['order_id']}", 0, 1)
        pdf.cell(0, 4, f"Date: {order_data['created_date']}", 0, 1)
        pdf.line(10, pdf.get_y(), 70, pdf.get_y())
        pdf.ln(2)
        
        # Customer info
        pdf.cell(0, 4, f"Customer: {order_data['customer_name']}", 0, 1)
        pdf.cell(0, 4, f"Phone: {order_data.get('customer_phone', 'N/A')}", 0, 1)
        pdf.cell(0, 4, f"Delivery: {order_data['delivery_type']}", 0, 1)
        pdf.line(10, pdf.get_y(), 70, pdf.get_y())
        pdf.ln(2)
        
        # Items
        pdf.cell(30, 4, "ITEM", 0, 0)
        pdf.cell(15, 4, "QTY", 0, 0, 'R')
        pdf.cell(25, 4, "AMOUNT", 0, 1, 'R')
        pdf.line(10, pdf.get_y(), 70, pdf.get_y())
        
        for item in order_data['items'].values():
            pdf.cell(30, 4, item['name'][:15] + ('...' if len(item['name']) > 15 else ''), 0, 0)
            pdf.cell(15, 4, str(item['quantity']), 0, 0, 'R')
            pdf.cell(25, 4, format_currency(item['price'] * item['quantity']), 0, 1, 'R')
        
        pdf.line(10, pdf.get_y(), 70, pdf.get_y())
        pdf.ln(2)
        
        # Totals
        pdf.cell(45, 4, "Subtotal:", 0, 0)
        pdf.cell(25, 4, format_currency(order_data['subtotal']), 0, 1, 'R')
        
        pdf.cell(45, 4, "Delivery:", 0, 0)
        pdf.cell(25, 4, format_currency(order_data['delivery_charge']), 0, 1, 'R')
        
        if order_data.get('payment_charge_amount', 0) > 0:
            pdf.cell(45, 4, f"Fee ({order_data['payment_charge_percent']}%):", 0, 0)
            pdf.cell(25, 4, format_currency(order_data['payment_charge_amount']), 0, 1, 'R')
        
        pdf.set_font("Courier", 'B', 10)
        pdf.cell(45, 5, "TOTAL:", 0, 0)
        pdf.cell(25, 5, format_currency(order_data['total']), 0, 1, 'R')
        pdf.set_font("Courier", size=8)
        
        pdf.ln(2)
        pdf.cell(0, 4, f"Payment: {order_data['payment_method']}", 0, 1)
        pdf.cell(0, 4, f"Status: {order_data['status'].replace('_', ' ').title()}", 0, 1)
        pdf.line(10, pdf.get_y(), 70, pdf.get_y())
        
        # Delivery address
        pdf.multi_cell(0, 4, f"Delivery Address:\n{order_data['delivery_address']}")
        
        if order_data.get('notes'):
            pdf.ln(2)
            pdf.multi_cell(0, 4, f"Notes: {order_data['notes']}")
        
        pdf.ln(5)
        pdf.cell(0, 4, "Thank you for your order!", 0, 1, 'C')
        pdf.cell(0, 4, get_current_datetime().strftime('%Y-%m-%d %H:%M:%S'), 0, 1, 'C')
        pdf.cell(0, 4, f"Printed by: {order_data['created_by']}", 0, 1, 'C')
        
        pdf_data = pdf.output(dest='S').encode('latin1')
        
        st.download_button(
            label="📄 Download PDF Receipt",
            data=pdf_data,
            file_name=f"receipt_{order_data['order_id']}.pdf",
            mime="application/pdf"
        )
        return True
        
    except Exception as e:
        st.error(f"PDF creation failed: {str(e)}")
        return False

def download_text_receipt(order_data):
    """Download text receipt"""
    try:
        receipt_text = generate_text_receipt(order_data)
        
        st.download_button(
            label="📝 Download Text Receipt",
            data=receipt_text,
            file_name=f"receipt_{order_data['order_id']}.txt",
            mime="text/plain"
        )
        return True
        
    except Exception as e:
        st.error(f"Text receipt failed: {str(e)}")
        return False

def generate_text_receipt(order_data):
    """Generate text format receipt"""
    settings = load_data(SETTINGS_FILE)
    receipt = []
    
    receipt.append("=" * 40)
    receipt.append(f"{settings.get('store_name', 'SUPERMARKET POS').center(40)}")
    receipt.append(f"{settings.get('store_address', '').center(40)}")
    receipt.append(f"Tel: {settings.get('store_phone', '').center(40)}")
    receipt.append("=" * 40)
    receipt.append("OUTDOOR ORDER RECEIPT".center(40))
    receipt.append("=" * 40)
    receipt.append(f"Order #: {order_data['order_id']}")
    receipt.append(f"Date: {order_data['created_date']}")
    receipt.append("-" * 40)
    receipt.append(f"Customer: {order_data['customer_name']}")
    receipt.append(f"Phone: {order_data.get('customer_phone', 'N/A')}")
    receipt.append(f"Delivery: {order_data['delivery_type']}")
    receipt.append("-" * 40)
    receipt.append("ITEM".ljust(20) + "QTY".rjust(5) + "AMOUNT".rjust(15))
    receipt.append("-" * 40)
    
    for item in order_data['items'].values():
        name = item['name'][:18] + ('..' if len(item['name']) > 18 else '')
        receipt.append(f"{name.ljust(20)}{str(item['quantity']).rjust(5)}{format_currency(item['price'] * item['quantity']).rjust(15)}")
    
    receipt.append("-" * 40)
    receipt.append(f"Subtotal:".ljust(25) + format_currency(order_data['subtotal']).rjust(15))
    receipt.append(f"Delivery:".ljust(25) + format_currency(order_data['delivery_charge']).rjust(15))
    
    if order_data.get('payment_charge_amount', 0) > 0:
        receipt.append(f"Fee ({order_data['payment_charge_percent']}%):".ljust(25) + format_currency(order_data['payment_charge_amount']).rjust(15))
    
    receipt.append("=" * 40)
    receipt.append(f"TOTAL:".ljust(25) + format_currency(order_data['total']).rjust(15))
    receipt.append("=" * 40)
    receipt.append(f"Payment: {order_data['payment_method']}")
    receipt.append(f"Status: {order_data['status'].replace('_', ' ').title()}")
    receipt.append("-" * 40)
    receipt.append("DELIVERY ADDRESS:")
    receipt.append(order_data['delivery_address'])
    
    if order_data.get('notes'):
        receipt.append("-" * 40)
        receipt.append(f"NOTES: {order_data['notes']}")
    
    receipt.append("=" * 40)
    receipt.append("Thank you for your order!".center(40))
    receipt.append(get_current_datetime().strftime('%Y-%m-%d %H:%M:%S').center(40))
    receipt.append(f"Printed by: {order_data['created_by']}".center(40))
    receipt.append("=" * 40)
    
    return "\n".join(receipt)


def save_draft_order():
    """Save current order as draft"""
    # Implementation for saving draft orders
    pass

def brands_management():
    if not is_manager():
        st.warning("You don't have permission to access this page")
        return
    
    st.title("Brand Management")
    
    tab1, tab2, tab3 = st.tabs(["Manage Brands", "Assign Brands to Products", "Brand Reports"])
    
    with tab1:
        st.header("Manage Brands")
        
        brands_data = load_data(BRANDS_FILE)
        brands_list = brands_data.get('brands', [])
        brand_products = brands_data.get('brand_products', {})
        
        st.subheader("Current Brands")
        if not brands_list:
            st.info("No brands defined yet")
        else:
            st.dataframe(pd.DataFrame(brands_list, columns=["Brands"]))
        
        st.subheader("Add New Brand")
        with st.form("add_brand_form"):
            new_brand = st.text_input("Brand Name")
            
            if st.form_submit_button("Add Brand"):
                if new_brand and new_brand not in brands_list:
                    brands_list.append(new_brand)
                    brands_data['brands'] = brands_list
                    if new_brand not in brand_products:
                        brand_products[new_brand] = []
                    brands_data['brand_products'] = brand_products
                    save_data(brands_data, BRANDS_FILE)
                    st.success(f"Brand '{new_brand}' added successfully")
                    st.rerun()
                elif new_brand in brands_list:
                    st.error("Brand already exists")
        
        st.subheader("Remove Brand")
        if brands_list:
            brand_to_remove = st.selectbox("Select Brand to Remove", [""] + brands_list)
            
            if brand_to_remove and st.button("Remove Brand"):
                # Check if brand has products assigned
                if brand_products.get(brand_to_remove):
                    st.error(f"Cannot remove brand '{brand_to_remove}' because it has products assigned to it")
                else:
                    brands_list.remove(brand_to_remove)
                    brands_data['brands'] = brands_list
                    if brand_to_remove in brand_products:
                        del brand_products[brand_to_remove]
                    brands_data['brand_products'] = brand_products
                    save_data(brands_data, BRANDS_FILE)
                    st.success(f"Brand '{brand_to_remove}' removed successfully")
                    st.rerun()
    
    with tab2:
        st.header("Assign Brands to Products")
        
        brands_data = load_data(BRANDS_FILE)
        products = load_data(PRODUCTS_FILE)
        brands_list = brands_data.get('brands', [])
        
        if not brands_list:
            st.info("No brands available. Please add brands first.")
        else:
            # Filter products without brands
            products_without_brands = {k: v for k, v in products.items() if not v.get('brand')}
            
            if not products_without_brands:
                st.info("All products already have brands assigned")
            else:
                st.subheader("Products Without Brands")
                product_options = {f"{v['name']} ({k})": k for k, v in products_without_brands.items()}
                selected_product = st.selectbox("Select Product", [""] + list(product_options.keys()))
                
                if selected_product:
                    barcode = product_options[selected_product]
                    product = products[barcode]
                    
                    st.write(f"**Selected Product:** {product['name']}")
                    
                    selected_brand = st.selectbox("Assign Brand", [""] + brands_list)
                    
                    if selected_brand and st.button("Assign Brand"):
                        products[barcode]['brand'] = selected_brand
                        
                        # Update brand_products mapping
                        brand_products = brands_data.get('brand_products', {})
                        if selected_brand not in brand_products:
                            brand_products[selected_brand] = []
                        if barcode not in brand_products[selected_brand]:
                            brand_products[selected_brand].append(barcode)
                        
                        brands_data['brand_products'] = brand_products
                        
                        save_data(products, PRODUCTS_FILE)
                        save_data(brands_data, BRANDS_FILE)
                        st.success(f"Brand '{selected_brand}' assigned to {product['name']}")
                        st.rerun()
            
            st.subheader("Bulk Brand Assignment")
            st.info("Assign the same brand to multiple products")
            
            # Multi-select products
            all_products = {f"{v['name']} ({k})": k for k, v in products.items()}
            selected_products = st.multiselect("Select Products", list(all_products.keys()))
            
            if selected_products:
                bulk_brand = st.selectbox("Assign Brand to Selected Products", [""] + brands_list)
                
                if bulk_brand and st.button("Assign to Selected"):
                    updated_count = 0
                    brand_products = brands_data.get('brand_products', {})
                    
                    for product_label in selected_products:
                        barcode = all_products[product_label]
                        products[barcode]['brand'] = bulk_brand
                        
                        if bulk_brand not in brand_products:
                            brand_products[bulk_brand] = []
                        if barcode not in brand_products[bulk_brand]:
                            brand_products[bulk_brand].append(barcode)
                            updated_count += 1
                    
                    brands_data['brand_products'] = brand_products
                    
                    save_data(products, PRODUCTS_FILE)
                    save_data(brands_data, BRANDS_FILE)
                    st.success(f"Brand '{bulk_brand}' assigned to {updated_count} products")
                    st.rerun()
    
    with tab3:
        st.header("Brand Reports")
        
        brands_data = load_data(BRANDS_FILE)
        products = load_data(PRODUCTS_FILE)
        inventory = load_data(INVENTORY_FILE)
        transactions = load_data(TRANSACTIONS_FILE)
        brands_list = brands_data.get('brands', [])
        brand_products = brands_data.get('brand_products', {})
        
        if not brands_list:
            st.info("No brands available for reporting")
        else:
            report_type = st.selectbox("Report Type", [
                "Brand Overview",
                "Sales by Brand",
                "Inventory by Brand",
                "Product Count by Brand"
            ])
            
            selected_brand = st.selectbox("Select Brand", [""] + brands_list)
            
            if report_type == "Brand Overview":
                if selected_brand:
                    st.subheader(f"Overview for {selected_brand}")
                    
                    # Product count
                    product_count = len(brand_products.get(selected_brand, []))
                    st.write(f"**Number of Products:** {product_count}")
                    
                    # Inventory value
                    total_value = 0
                    total_quantity = 0
                    for barcode in brand_products.get(selected_brand, []):
                        inv_data = inventory.get(barcode, {})
                        product = products.get(barcode, {})
                        quantity = inv_data.get('quantity', 0)
                        cost = product.get('cost', 0)
                        total_value += quantity * cost
                        total_quantity += quantity
                    
                    st.write(f"**Total Inventory Quantity:** {total_quantity}")
                    st.write(f"**Total Inventory Value:** {format_currency(total_value)}")
                    
                    # Sales data (last 30 days)
                    thirty_days_ago = (datetime.datetime.now() - datetime.timedelta(days=30)).date()
                    sales_total = 0
                    units_sold = 0
                    
                    for transaction in transactions.values():
                        try:
                            trans_date = datetime.datetime.strptime(transaction.get('date', ''), "%Y-%m-%d %H:%M:%S").date()
                            if trans_date >= thirty_days_ago:
                                for barcode, item in transaction.get('items', {}).items():
                                    if barcode in brand_products.get(selected_brand, []):
                                        sales_total += item['price'] * item['quantity']
                                        units_sold += item['quantity']
                        except (ValueError, KeyError):
                            continue
                    
                    st.write(f"**Sales (Last 30 Days):** {format_currency(sales_total)}")
                    st.write(f"**Units Sold (Last 30 Days):** {units_sold}")
                    
                else:
                    st.info("Please select a brand to view details")
            
            elif report_type == "Sales by Brand":
                st.subheader("Sales by Brand")
                
                # Date range
                col1, col2 = st.columns(2)
                with col1:
                    start_date = st.date_input("Start Date", value=datetime.date.today() - datetime.timedelta(days=30))
                with col2:
                    end_date = st.date_input("End Date", value=datetime.date.today())
                
                brand_sales = {}
                for brand in brands_list:
                    brand_sales[brand] = {'revenue': 0, 'units': 0}
                
                for transaction in transactions.values():
                    try:
                        trans_date = datetime.datetime.strptime(transaction.get('date', ''), "%Y-%m-%d %H:%M:%S").date()
                        if start_date <= trans_date <= end_date:
                            for barcode, item in transaction.get('items', {}).items():
                                product = products.get(barcode, {})
                                brand = product.get('brand')
                                if brand and brand in brand_sales:
                                    brand_sales[brand]['revenue'] += item['price'] * item['quantity']
                                    brand_sales[brand]['units'] += item['quantity']
                    except (ValueError, KeyError):
                        continue
                
                sales_df = pd.DataFrame.from_dict(brand_sales, orient='index')
                sales_df = sales_df.sort_values('revenue', ascending=False)
                
                st.dataframe(sales_df)
                
                # Chart
                st.bar_chart(sales_df['revenue'])
            
            elif report_type == "Inventory by Brand":
                st.subheader("Inventory by Brand")
                
                brand_inventory = {}
                for brand in brands_list:
                    brand_inventory[brand] = {'value': 0, 'quantity': 0, 'products': 0}
                
                for barcode, product in products.items():
                    brand = product.get('brand')
                    if brand and brand in brand_inventory:
                        inv_data = inventory.get(barcode, {})
                        quantity = inv_data.get('quantity', 0)
                        cost = product.get('cost', 0)
                        
                        brand_inventory[brand]['value'] += quantity * cost
                        brand_inventory[brand]['quantity'] += quantity
                        brand_inventory[brand]['products'] += 1
                
                inv_df = pd.DataFrame.from_dict(brand_inventory, orient='index')
                inv_df = inv_df.sort_values('value', ascending=False)
                
                st.dataframe(inv_df)
                
                # Chart
                st.bar_chart(inv_df['value'])
            
            elif report_type == "Product Count by Brand":
                st.subheader("Product Count by Brand")
                
                product_counts = {}
                for brand in brands_list:
                    product_counts[brand] = len(brand_products.get(brand, []))
                
                count_df = pd.DataFrame.from_dict(product_counts, orient='index', columns=['Product Count'])
                count_df = count_df.sort_values('Product Count', ascending=False)
                
                st.dataframe(count_df)
                
                # Chart
                st.bar_chart(count_df['Product Count'])

def generate_receipt(transaction):
    settings = load_data(SETTINGS_FILE)
    receipt = ""
    
    # Header
    receipt += f"{settings.get('store_name', 'Supermarket POS')}\n"
    receipt += f"{settings.get('store_address', '')}\n"
    receipt += f"{settings.get('store_phone', '')}\n"
    receipt += "=" * 40 + "\n"
    
    if settings.get('receipt_header', ''):
        receipt += f"{settings['receipt_header']}\n"
        receipt += "=" * 40 + "\n"
    
    receipt += f"Date: {transaction['date']}\n"
    receipt += f"Cashier: {transaction['cashier']}\n"
    receipt += f"Transaction ID: {transaction['transaction_id']}\n"
    receipt += "=" * 40 + "\n"
    
    # Items
    for barcode, item in transaction['items'].items():
        receipt += f"{item['name']} x{item['quantity']}: {format_currency(item['price'] * item['quantity'])}\n"
    
    receipt += "=" * 40 + "\n"
    receipt += f"Subtotal: {format_currency(transaction['subtotal'])}\n"
    receipt += f"Tax: {format_currency(transaction['tax'])}\n"
    if transaction['discount'] != 0:
        receipt += f"Discount: -{format_currency(abs(transaction['discount']))}\n"
    receipt += f"Total: {format_currency(transaction['total'])}\n"
    receipt += f"Payment Method: {transaction['payment_method']}\n"
    receipt += f"Amount Tendered: {format_currency(transaction['amount_tendered'])}\n"
    receipt += f"Change: {format_currency(transaction['change'])}\n"
    receipt += "=" * 40 + "\n"
    
    if settings.get('receipt_footer', ''):
        receipt += f"{settings['receipt_footer']}\n"
        receipt += "=" * 40 + "\n"
    
    receipt += "Thank you for shopping with us!\n"
    
    return receipt

# Returns & Refunds Management
# Returns & Refunds Management with proper receipt printing
# Returns & Refunds Management Module
# Returns & Refunds Management Module - with reliable print functionality
def returns_management():
    st.title("🔄 Returns & Refunds")
    
    # Initialize session state
    if 'print_receipt' not in st.session_state:
        st.session_state.print_receipt = None
    if 'print_return_id' not in st.session_state:
        st.session_state.print_return_id = None
    if 'exchange_cart' not in st.session_state:
        st.session_state.exchange_cart = {}
    if 'exchange_mode' not in st.session_state:
        st.session_state.exchange_mode = False
    
    # Handle print requests
    if st.session_state.print_receipt and st.session_state.print_return_id:
        print_return_receipt(st.session_state.print_return_id)
        return
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔄 Process Return", 
        "📋 View Returns", 
        "📊 Return Analytics", 
        "⚙️ Return Settings"
    ])
    
    with tab1:
        process_return_tab()
    
    with tab2:
        view_returns_tab()
    
    with tab3:
        return_analytics_tab()
    
    with tab4:
        return_settings_tab()


def return_settings_tab():
    if not is_manager():
        st.warning("You need manager privileges to access return settings")
        return
    
    st.header("Return Settings")
    
    settings = load_data(SETTINGS_FILE)
    return_settings = settings.get('return_settings', {})
    
    with st.form("return_settings_form"):
        st.subheader("Return Policy Configuration")
        
        # Return policy settings
        return_period = st.number_input(
            "Return Period (days)", 
            min_value=0, 
            max_value=365, 
            value=return_settings.get('return_period', 30),
            help="Number of days customers have to return items"
        )
        
        require_receipt = st.checkbox(
            "Require Receipt for Returns",
            value=return_settings.get('require_receipt', True),
            help="Whether customers must provide a receipt to process returns"
        )
        
        restocking_fee = st.number_input(
            "Restocking Fee (%)",
            min_value=0.0,
            max_value=25.0,
            value=return_settings.get('restocking_fee', 0.0),
            step=0.5,
            help="Percentage fee charged for restocking returned items"
        )
        
        non_returnable_items = st.text_area(
            "Non-Returnable Items",
            value="\n".join(return_settings.get('non_returnable_items', [])),
            help="List of item categories or types that cannot be returned (one per line)"
        )
        
        # Refund method preferences
        st.subheader("Refund Method Preferences")
        default_refund_method = st.selectbox(
            "Default Refund Method",
            ["Original Payment Method", "Store Credit", "Cash"],
            index=["Original Payment Method", "Store Credit", "Cash"].index(
                return_settings.get('default_refund_method', "Original Payment Method")
            )
        )
        
        # Exchange settings
        st.subheader("Exchange Settings")
        exchange_period = st.number_input(
            "Exchange Period (days)",
            min_value=0,
            max_value=365,
            value=return_settings.get('exchange_period', 60),
            help="Number of days customers have to exchange items"
        )
        
        allow_partial_exchange = st.checkbox(
            "Allow Partial Exchanges",
            value=return_settings.get('allow_partial_exchange', True),
            help="Allow customers to exchange only some of the returned items"
        )
        
        if st.form_submit_button("Save Settings"):
            settings['return_settings'] = {
                'return_period': return_period,
                'require_receipt': require_receipt,
                'restocking_fee': restocking_fee,
                'non_returnable_items': [item.strip() for item in non_returnable_items.split('\n') if item.strip()],
                'default_refund_method': default_refund_method,
                'exchange_period': exchange_period,
                'allow_partial_exchange': allow_partial_exchange
            }
            save_data(settings, SETTINGS_FILE)
            st.success("Return settings saved successfully")

def process_return_tab():
    st.header("Process Return/Exchange")
    
    transactions = load_data(TRANSACTIONS_FILE)
    products = load_data(PRODUCTS_FILE)
    inventory = load_data(INVENTORY_FILE)
    settings = load_data(SETTINGS_FILE)
    tax_rate = settings.get('tax_rate', 0.0)
    
    # Step 1: Find transaction
    st.subheader("Step 1: Find Transaction")
    transaction_id = st.text_input("Enter Transaction ID or Scan Receipt Barcode", key="return_transaction_id")
    
    if transaction_id and transaction_id in transactions:
        transaction = transactions[transaction_id]
        
        # Display transaction details
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info(f"**Date:** {transaction['date']}")
        with col2:
            st.info(f"**Total:** {format_currency(transaction['total'])}")
        with col3:
            st.info(f"**Payment Method:** {transaction['payment_method']}")
        
        # Step 2: Select items to return
        st.subheader("Step 2: Select Items to Return")
        
        return_items = {}
        for barcode, item in transaction['items'].items():
            with st.expander(f"{item['name']} - {item['quantity']} x {format_currency(item['price'])}"):
                col1, col2 = st.columns(2)
                with col1:
                    max_returnable = item['quantity']
                    current_stock = inventory.get(barcode, {}).get('quantity', 0)
                    st.write(f"**Purchased:** {max_returnable}")
                    st.write(f"**Current Stock:** {current_stock}")
                    
                    return_qty = st.number_input(
                        "Quantity to Return", 
                        min_value=0, 
                        max_value=max_returnable, 
                        value=0, 
                        key=f"return_{barcode}"
                    )
                
                with col2:
                    if return_qty > 0:
                        return_reason = st.selectbox(
                            "Reason for Return",
                            ["", "Defective", "Wrong Item", "Customer Changed Mind", 
                             "Damaged", "Expired", "Quality Issue", "Other"],
                            key=f"reason_{barcode}"
                        )
                        
                        if return_reason == "Other":
                            return_reason = st.text_input("Please specify reason", key=f"other_reason_{barcode}")
                        
                        condition = st.selectbox(
                            "Item Condition",
                            ["", "Unopened", "Opened", "Damaged", "Used"],
                            key=f"condition_{barcode}"
                        )
                        
                        if return_qty > 0 and return_reason and condition:
                            return_items[barcode] = {
                                'name': item['name'],
                                'quantity': return_qty,
                                'price': item['price'],
                                'subtotal': return_qty * item['price'],
                                'reason': return_reason,
                                'condition': condition
                            }
                            st.success(f"{return_qty} item(s) marked for return")
        
        # Step 3: Process return or exchange
        if return_items:
            st.subheader("Step 3: Process Return")
            
            # Calculate refund amounts
            total_refund = sum(item['subtotal'] for item in return_items.values())
            original_tax_rate = transaction['tax'] / transaction['subtotal'] if transaction['subtotal'] > 0 else 0
            tax_refund = total_refund * original_tax_rate
            total_refund_amount = total_refund + tax_refund
            
            st.write(f"**Subtotal Refund:** {format_currency(total_refund)}")
            st.write(f"**Tax Refund:** {format_currency(tax_refund)}")
            st.write(f"**Total Refund:** {format_currency(total_refund_amount)}")
            
            # Return/Exchange options
            st.subheader("Return Options")
            return_option = st.radio("Select Option", 
                                   ["Refund", "Exchange", "Store Credit"], 
                                   help="Choose how to handle the return")
            
            exchange_difference = 0
            exchange_products = []  # Changed to list
            exchange_subtotal = 0
            exchange_tax = 0
            exchange_total = 0
            refund_method = None
            
            if return_option == "Exchange":
                st.session_state.exchange_mode = True
                st.session_state.exchange_cart = {}
                
                st.info("🔄 Exchange Mode: Select products for exchange")
                
                # Display products for exchange
                products_data = load_data(PRODUCTS_FILE)
                inventory_data = load_data(INVENTORY_FILE)
                
                # Filter available products
                available_products = {}
                for barcode, product in products_data.items():
                    stock = inventory_data.get(barcode, {}).get('quantity', 0)
                    if stock > 0 and product.get('active', True):
                        available_products[barcode] = product
                
                # Product selection for exchange
                st.subheader("Select Exchange Products")
                
                # Search and filter
                col1, col2 = st.columns(2)
                with col1:
                    search_term = st.text_input("Search Products", placeholder="Product name or barcode")
                with col2:
                    categories = load_data(CATEGORIES_FILE).get('categories', [])
                    selected_category = st.selectbox("Filter by Category", [""] + categories)
                
                # Filter products
                filtered_products = {}
                for barcode, product in available_products.items():
                    matches_search = not search_term or (
                        search_term.lower() in product['name'].lower() or 
                        search_term.lower() in barcode.lower()
                    )
                    matches_category = not selected_category or product.get('category') == selected_category
                    
                    if matches_search and matches_category:
                        filtered_products[barcode] = product
                
                # Display products in grid
                if filtered_products:
                    cols = st.columns(3)
                    for idx, (barcode, product) in enumerate(filtered_products.items()):
                        with cols[idx % 3]:
                            with st.container():
                                st.markdown(f"**{product['name']}**")
                                st.write(f"Price: {format_currency(product['price'])}")
                                
                                stock = inventory_data.get(barcode, {}).get('quantity', 0)
                                st.write(f"Stock: {stock}")
                                
                                # Add to exchange cart
                                exchange_qty = st.number_input("Qty", 0, stock, 1, key=f"ex_qty_{barcode}")
                                
                                if st.button(f"Add to Exchange", key=f"add_ex_{barcode}", use_container_width=True):
                                    if barcode in st.session_state.exchange_cart:
                                        st.session_state.exchange_cart[barcode]['quantity'] += exchange_qty
                                    else:
                                        st.session_state.exchange_cart[barcode] = {
                                            'name': product['name'],
                                            'price': product['price'],
                                            'quantity': exchange_qty
                                        }
                                    st.success(f"Added {exchange_qty} {product['name']} to exchange")
                
                # Display exchange cart
                if st.session_state.exchange_cart:
                    st.subheader("🛒 Exchange Cart")
                    
                    exchange_subtotal = 0
                    for barcode, item in st.session_state.exchange_cart.items():
                        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                        with col1:
                            st.write(f"**{item['name']}**")
                        with col2:
                            st.write(f"Qty: {item['quantity']}")
                        with col3:
                            item_total = item['price'] * item['quantity']
                            st.write(f"{format_currency(item_total)}")
                        with col4:
                            if st.button("❌", key=f"remove_ex_{barcode}"):
                                del st.session_state.exchange_cart[barcode]
                                st.rerun()
                        
                        exchange_subtotal += item_total
                    
                    # Calculate exchange tax and total
                    exchange_tax = exchange_subtotal * tax_rate
                    exchange_total = exchange_subtotal + exchange_tax
                    
                    st.write(f"**Exchange Subtotal:** {format_currency(exchange_subtotal)}")
                    st.write(f"**Exchange Tax ({tax_rate*100}%):** {format_currency(exchange_tax)}")
                    st.write(f"**Exchange Total:** {format_currency(exchange_total)}")
                    
                    # Calculate difference
                    exchange_difference = exchange_total - total_refund_amount
                    if exchange_difference > 0:
                        st.warning(f"Customer needs to pay: {format_currency(exchange_difference)}")
                    elif exchange_difference < 0:
                        st.info(f"Customer gets refund: {format_currency(abs(exchange_difference))}")
                    else:
                        st.success("Even exchange - no payment needed")
                    
                    # Convert exchange cart to list format for storage
                    exchange_products = [
                        {
                            'barcode': barcode,
                            'name': item['name'],
                            'price': item['price'],
                            'quantity': item['quantity'],
                            'subtotal': item['price'] * item['quantity']
                        }
                        for barcode, item in st.session_state.exchange_cart.items()
                    ]
            
            # Payment method for refund or additional payment
            if return_option in ["Refund", "Exchange"] and (return_option != "Exchange" or exchange_difference != 0):
                st.subheader("Payment Details")
                
                if return_option == "Refund":
                    refund_method = st.selectbox(
                        "Refund Method",
                        ["Original Payment Method", "Cash", "Store Credit"],
                        index=0 if transaction['payment_method'] != "Cash" else 1
                    )
                else:  # Exchange
                    if exchange_difference > 0:
                        refund_method = st.selectbox(
                            "Additional Payment Method",
                            ["Cash", "Credit Card", "Debit Card", "Mobile Payment"],
                            help="Customer needs to pay the difference"
                        )
                    else:
                        refund_method = st.selectbox(
                            "Refund Method for Difference",
                            ["Cash", "Store Credit", "Original Payment Method"],
                            help="Customer gets refund for the difference"
                        )
            
            # Additional notes
            return_notes = st.text_area("Additional Notes", placeholder="Any special instructions...")
            
            if st.button("Process Return", type="primary", use_container_width=True):
                # Create return record
                returns = load_data(RETURNS_FILE)
                return_id = f"RET_{generate_short_id()}"
                
                # Determine refund method for the record
                if return_option == "Store Credit":
                    record_refund_method = "Store Credit"
                elif return_option == "Exchange" and exchange_difference == 0:
                    record_refund_method = "Exchange (Even)"
                else:
                    record_refund_method = refund_method
                
                return_record = {
                    'return_id': return_id,
                    'transaction_id': transaction_id,
                    'original_date': transaction['date'],
                    'return_date': get_current_datetime().strftime("%Y-%m-%d %H:%M:%S"),
                    'items': return_items,
                    'subtotal_refund': total_refund,
                    'tax_refund': tax_refund,
                    'total_refund': total_refund_amount,
                    'refund_method': record_refund_method,
                    'original_payment_method': transaction['payment_method'],
                    'reason': "Multiple items" if len(return_items) > 1 else list(return_items.values())[0]['reason'],
                    'condition': "Various" if len(return_items) > 1 else list(return_items.values())[0]['condition'],
                    'notes': return_notes,
                    'processed_by': st.session_state.user_info['username'],
                    'shift_id': st.session_state.shift_id if is_cashier() else None,
                    'status': 'completed'
                }
                
                # Handle exchange
                if return_option == "Exchange":
                    return_record['exchange_products'] = exchange_products
                    return_record['exchange_subtotal'] = exchange_subtotal
                    return_record['exchange_tax'] = exchange_tax
                    return_record['exchange_total'] = exchange_total
                    return_record['exchange_difference'] = exchange_difference
                    return_record['status'] = 'exchange_processed'
                
                # Update inventory for returned items
                for barcode, item in return_items.items():
                    if barcode in inventory:
                        inventory[barcode]['quantity'] += item['quantity']
                    else:
                        inventory[barcode] = {'quantity': item['quantity']}
                    
                    # Add restock note
                    inventory[barcode]['last_restock'] = get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
                    inventory[barcode]['restock_reason'] = f"Return: {item['reason']}"
                
                # Update inventory for exchange products
                if return_option == "Exchange":
                    for item in exchange_products:
                        barcode = item['barcode']
                        if barcode in inventory:
                            inventory[barcode]['quantity'] -= item['quantity']
                            inventory[barcode]['last_updated'] = get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
                            inventory[barcode]['updated_by'] = st.session_state.user_info['username']
                
                # Handle cash drawer for cash transactions
                if (return_option == "Refund" and refund_method == "Cash") or \
                   (return_option == "Exchange" and refund_method == "Cash"):
                    if is_cashier() and st.session_state.shift_started:
                        cash_drawer = load_data(CASH_DRAWER_FILE)
                        
                        if return_option == "Refund":
                            # Regular refund
                            cash_drawer['current_balance'] -= total_refund_amount
                            cash_drawer['transactions'].append({
                                'type': 'refund',
                                'amount': -total_refund_amount,
                                'date': get_current_datetime().strftime("%Y-%m-%d %H:%M:%S"),
                                'return_id': return_id,
                                'processed_by': st.session_state.user_info['username']
                            })
                        else:
                            # Exchange with cash difference
                            if exchange_difference > 0:
                                # Customer pays difference
                                cash_drawer['current_balance'] += exchange_difference
                                cash_drawer['transactions'].append({
                                    'type': 'exchange_payment',
                                    'amount': exchange_difference,
                                    'date': get_current_datetime().strftime("%Y-%m-%d %H:%M:%S"),
                                    'return_id': return_id,
                                    'processed_by': st.session_state.user_info['username']
                                })
                            else:
                                # Customer gets refund
                                cash_drawer['current_balance'] -= abs(exchange_difference)
                                cash_drawer['transactions'].append({
                                    'type': 'exchange_refund',
                                    'amount': -abs(exchange_difference),
                                    'date': get_current_datetime().strftime("%Y-%m-%d %H:%M:%S"),
                                    'return_id': return_id,
                                    'processed_by': st.session_state.user_info['username']
                                })
                        
                        save_data(cash_drawer, CASH_DRAWER_FILE)
                
                # Save everything
                returns[return_id] = return_record
                save_data(returns, RETURNS_FILE)
                save_data(inventory, INVENTORY_FILE)
                
                st.success(f"Return processed successfully! Return ID: {return_id}")
                
                # Show receipt and print options
                return_receipt = generate_return_receipt(return_record)
                st.subheader("Return Receipt")
                st.text(return_receipt)
                
                # Print options
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("🖨️ Print Receipt", key="print_return_btn"):
                        st.session_state.print_receipt = True
                        st.session_state.print_return_id = return_id
                        st.rerun()
                with col2:
                    if st.button("📄 Download PDF", key="dl_pdf_return_btn"):
                        download_pdf_receipt(return_record, "return")
                with col3:
                    st.download_button(
                        label="📝 Download Text",
                        data=return_receipt,
                        file_name=f"return_receipt_{return_id}.txt",
                        mime="text/plain",
                        key="dl_txt_return_btn"
                    )
                
                # Reset exchange state
                st.session_state.exchange_mode = False
                st.session_state.exchange_cart = {}
        else:
            st.info("No items selected for return")
    elif transaction_id:
        st.error("Transaction not found. Please check the Transaction ID.")

def return_analytics_tab():
    st.header("Return Analytics")
    
    returns = load_data(RETURNS_FILE)
    products = load_data(PRODUCTS_FILE)
    
    if not returns:
        st.info("No return data available for analysis")
        return
    
    # Date range selector
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=datetime.date.today() - datetime.timedelta(days=30), key="analytics_start")
    with col2:
        end_date = st.date_input("End Date", value=datetime.date.today(), key="analytics_end")
    
    # Filter returns by date
    filtered_returns = []
    for return_data in returns.values():
        try:
            return_date = datetime.datetime.strptime(return_data['return_date'], "%Y-%m-%d %H:%M:%S").date()
            if start_date <= return_date <= end_date:
                filtered_returns.append(return_data)
        except (ValueError, KeyError):
            continue
    
    if not filtered_returns:
        st.info("No returns in selected date range")
        return
    
    # Calculate analytics
    total_returns = len(filtered_returns)
    total_refund_amount = sum(r.get('total_refund', 0) for r in filtered_returns)
    avg_refund = total_refund_amount / total_returns if total_returns > 0 else 0
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Returns", total_returns)
    col2.metric("Total Refund Amount", format_currency(total_refund_amount))
    col3.metric("Average Refund", format_currency(avg_refund))
    
    # Return rate calculation (would need sales data)
    st.subheader("Return Reasons")
    return_reasons = {}
    for return_data in filtered_returns:
        reason = return_data.get('reason', 'Unknown')
        return_reasons[reason] = return_reasons.get(reason, 0) + 1
    
    if return_reasons:
        reasons_df = pd.DataFrame({
            'Reason': list(return_reasons.keys()),
            'Count': list(return_reasons.values())
        }).sort_values('Count', ascending=False)
        
        st.bar_chart(reasons_df.set_index('Reason'))
    
    # Products with most returns
    st.subheader("Most Returned Products")
    product_returns = {}
    for return_data in filtered_returns:
        for barcode, item in return_data.get('items', {}).items():
            product_name = products.get(barcode, {}).get('name', 'Unknown')
            product_returns[product_name] = product_returns.get(product_name, 0) + item.get('quantity', 0)
    
    if product_returns:
        product_df = pd.DataFrame({
            'Product': list(product_returns.keys()),
            'Return Quantity': list(product_returns.values())
        }).sort_values('Return Quantity', ascending=False).head(10)
        
        st.bar_chart(product_df.set_index('Product'))
    
    # Refund methods
    st.subheader("Refund Methods")
    refund_methods = {}
    for return_data in filtered_returns:
        method = return_data.get('refund_method', 'Unknown')
        refund_methods[method] = refund_methods.get(method, 0) + 1
    
    if refund_methods:
        method_df = pd.DataFrame({
            'Method': list(refund_methods.keys()),
            'Count': list(refund_methods.values())
        })
        
        st.bar_chart(method_df.set_index('Method'))


def view_returns_tab():
    st.header("View Returns")
    
    returns = load_data(RETURNS_FILE)
    
    if not returns:
        st.info("No returns processed yet")
        return
    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        date_filter = st.selectbox("Date Range", ["Last 7 days", "Last 30 days", "Last 90 days", "All time"], key="view_date_filter")
    with col2:
        status_filter = st.selectbox("Status", ["All", "completed", "pending_exchange", "cancelled", "exchange_processed"], key="view_status_filter")
    with col3:
        refund_filter = st.selectbox("Refund Method", ["All", "Cash", "Store Credit", "Original Payment Method", "Exchange"], key="view_refund_filter")
    
    # Apply filters
    filtered_returns = []
    for return_id, return_data in returns.items():
        # Date filter
        return_date = datetime.datetime.strptime(return_data['return_date'], "%Y-%m-%d %H:%M:%S")
        if date_filter == "Last 7 days" and return_date < datetime.datetime.now() - datetime.timedelta(days=7):
            continue
        if date_filter == "Last 30 days" and return_date < datetime.datetime.now() - datetime.timedelta(days=30):
            continue
        if date_filter == "Last 90 days" and return_date < datetime.datetime.now() - datetime.timedelta(days=90):
            continue
        
        # Status filter
        if status_filter != "All" and return_data.get('status', 'completed') != status_filter:
            continue
        
        # Refund method filter
        if refund_filter != "All" and return_data.get('refund_method') != refund_filter:
            continue
        
        filtered_returns.append((return_id, return_data))
    
    # Sort by date
    filtered_returns.sort(key=lambda x: x[1]['return_date'], reverse=True)
    
    if not filtered_returns:
        st.info("No returns match the selected filters")
        return
    
    # Display returns
    for return_id, return_data in filtered_returns:
        with st.expander(f"Return #{return_id} - {format_currency(return_data.get('total_refund', 0))} - {return_data['return_date']}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Original Transaction:** {return_data['transaction_id']}")
                st.write(f"**Date Processed:** {return_data['return_date']}")
                st.write(f"**Processed by:** {return_data['processed_by']}")
                st.write(f"**Refund Method:** {return_data['refund_method']}")
                st.write(f"**Status:** {return_data.get('status', 'completed').title()}")
            
            with col2:
                st.write(f"**Subtotal Refund:** {format_currency(return_data.get('subtotal_refund', 0))}")
                st.write(f"**Tax Refund:** {format_currency(return_data.get('tax_refund', 0))}")
                st.write(f"**Total Refund:** {format_currency(return_data.get('total_refund', 0))}")
                st.write(f"**Reason:** {return_data.get('reason', 'N/A')}")
            
            # Exchange details if any - FIXED: Handle list format
            if 'exchange_products' in return_data and return_data['exchange_products']:
                st.write("**Exchange Items:**")
                # Handle list format for exchange products
                for item in return_data['exchange_products']:
                    st.write(f"- {item.get('name', 'Unknown')} x{item.get('quantity', 0)} @ {format_currency(item.get('price', 0))}")
                
                if 'exchange_difference' in return_data:
                    difference = return_data['exchange_difference']
                    if difference > 0:
                        st.write(f"**Additional Payment:** {format_currency(difference)}")
                    elif difference < 0:
                        st.write(f"**Refund Given:** {format_currency(abs(difference))}")
            
            # Items details
            st.write("**Returned Items:**")
            for barcode, item in return_data['items'].items():
                st.write(f"- {item['name']} x{item['quantity']} ({item.get('condition', 'N/A')}) - {format_currency(item.get('subtotal', 0))}")
            
            # Actions
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("View Receipt", key=f"view_{return_id}"):
                    receipt_text = generate_return_receipt(return_data)
                    st.text_area("Receipt Content", receipt_text, height=200, key=f"receipt_{return_id}")
            
            with col2:
                if st.button("Print Receipt", key=f"print_{return_id}"):
                    st.session_state.print_receipt = True
                    st.session_state.print_return_id = return_id
                    st.rerun()
            
            with col3:
                if is_manager() and return_data.get('status') == 'pending_exchange':
                    if st.button("Complete Exchange", key=f"complete_{return_id}"):
                        returns = load_data(RETURNS_FILE)
                        returns[return_id]['status'] = 'completed'
                        returns[return_id]['exchange_completed_date'] = get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
                        save_data(returns, RETURNS_FILE)
                        st.success("Exchange marked as completed")
                        st.rerun()


def refund_history_tab():
    st.header("Refund History")
    
    returns = load_data(RETURNS_FILE)
    
    if not returns:
        st.info("No refunds processed yet")
        return
    
    # Date range filter
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=datetime.date.today() - datetime.timedelta(days=30), key="refund_start")
    with col2:
        end_date = st.date_input("End Date", value=datetime.date.today(), key="refund_end")
    
    # Filter returns by date
    filtered_returns = []
    for return_data in returns.values():
        return_date = datetime.datetime.strptime(return_data['return_date'], "%Y-%m-%d %H:%M:%S").date()
        if start_date <= return_date <= end_date:
            filtered_returns.append(return_data)
    
    if not filtered_returns:
        st.info("No refunds in selected date range")
        return
    
    # Summary statistics
    total_refunds = len(filtered_returns)
    total_amount = sum(r['total_refund'] for r in filtered_returns)
    avg_refund = total_amount / total_refunds if total_refunds > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Refunds", total_refunds)
    with col2:
        st.metric("Total Amount", format_currency(total_amount))
    with col3:
        st.metric("Average Refund", format_currency(avg_refund))
    with col4:
        pending = sum(1 for r in filtered_returns if r['status'] == "Pending")
        st.metric("Pending", pending)
    
    # Refund method breakdown
    st.subheader("Refund Method Breakdown")
    method_counts = {}
    for return_data in filtered_returns:
        method = return_data['refund_method']
        method_counts[method] = method_counts.get(method, 0) + 1
    
    method_df = pd.DataFrame({
        'Method': list(method_counts.keys()),
        'Count': list(method_counts.values())
    })
    st.bar_chart(method_df.set_index('Method'))
    
    # Detailed list
    st.subheader("Refund Details")
    for return_data in filtered_returns:
        with st.expander(f"Return #{return_data['return_id']} - {format_currency(return_data['total_refund'])} - {return_data['status']}"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Date:** {return_data['return_date']}")
                st.write(f"**Original Transaction:** {return_data['transaction_id']}")
                st.write(f"**Processed by:** {return_data['processed_by']}")
            with col2:
                st.write(f"**Refund Method:** {return_data['refund_method']}")
                st.write(f"**Reason:** {return_data['reason']}")
                st.write(f"**Status:** {return_data['status']}")

def print_return_receipt(return_id):
    """Handle return receipt printing"""
    returns_data = load_data(RETURNS_FILE)
    
    if return_id in returns_data:
        return_data = returns_data[return_id]
        receipt_text = generate_return_receipt(return_data)
        
        st.title("🖨️ Print Return Receipt")
        
        # Display the receipt content
        st.text_area("Receipt Content", receipt_text, height=300, key="receipt_display")
        
        # Print options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🖨️ Browser Print", use_container_width=True):
                print_receipt_browser(receipt_text, "Return Receipt")
        
        with col2:
            if st.button("📄 Download PDF", use_container_width=True):
                download_pdf_receipt(return_data, "return")
        
        with col3:
            st.download_button(
                label="📝 Download Text",
                data=receipt_text,
                file_name=f"return_receipt_{return_id}.txt",
                mime="text/plain",
                key="download_return_txt"
            )
        
        # Back button
        if st.button("← Back to Returns", use_container_width=True):
            st.session_state.print_receipt = None
            st.session_state.print_return_id = None
            st.rerun()
    else:
        st.error("Return not found")
        if st.button("← Back to Returns"):
            st.session_state.print_receipt = None
            st.session_state.print_return_id = None
            st.rerun()

def print_receipt_browser(receipt_text, title="Receipt"):
    """Print receipt using browser's print functionality"""
    js_code = f"""
    <script>
    function printReceipt() {{
        const printWindow = window.open('', '_blank', 'width=400,height=600');
        const htmlContent = `
        <!DOCTYPE html>
        <html>
        <head>
            <title>{title}</title>
            <style>
                body {{
                    font-family: 'Courier New', monospace;
                    font-size: 12px;
                    padding: 10px;
                    line-height: 1.2;
                }}
                .receipt {{
                    white-space: pre-wrap;
                    word-wrap: break-word;
                }}
                @media print {{
                    body {{
                        margin: 0;
                        padding: 10px;
                    }}
                    .no-print {{
                        display: none !important;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="receipt">{receipt_text}</div>
        </body>
        </html>
        `;
        
        printWindow.document.write(htmlContent);
        printWindow.document.close();
        
        printWindow.onload = function() {{
            printWindow.print();
            setTimeout(() => printWindow.close(), 500);
        }};
    }}
    
    setTimeout(printReceipt, 100);
    </script>
    """
    
    st.components.v1.html(js_code, height=0)

def download_pdf_receipt(return_data, receipt_type="return"):
    """Download PDF receipt for returns"""
    try:
        pdf = FPDF.FPDF(format=(80, 200))
        pdf.add_page()
        pdf.set_font("Courier", size=10)
        
        # Store header
        settings = load_data(SETTINGS_FILE)
        pdf.cell(0, 5, settings.get('store_name', 'SUPERMARKET POS'), 0, 1, 'C')
        pdf.set_font("Courier", size=8)
        pdf.cell(0, 4, settings.get('store_address', ''), 0, 1, 'C')
        pdf.cell(0, 4, f"Tel: {settings.get('store_phone', '')}", 0, 1, 'C')
        
        pdf.ln(2)
        pdf.set_font("Courier", size=10)
        
        if receipt_type == "return":
            pdf.cell(0, 5, "RETURN RECEIPT", 0, 1, 'C')
        else:
            pdf.cell(0, 5, "EXCHANGE RECEIPT", 0, 1, 'C')
            
        pdf.line(10, pdf.get_y(), 70, pdf.get_y())
        pdf.ln(2)
        
        # Return information
        pdf.cell(0, 4, f"Return #: {return_data.get('return_id', 'N/A')}", 0, 1)
        pdf.cell(0, 4, f"Original Trans: {return_data.get('transaction_id', 'N/A')}", 0, 1)
        pdf.cell(0, 4, f"Date: {return_data.get('return_date', 'N/A')}", 0, 1)
        pdf.cell(0, 4, f"Processed by: {return_data.get('processed_by', 'N/A')}", 0, 1)
        pdf.line(10, pdf.get_y(), 70, pdf.get_y())
        pdf.ln(2)
        
        # Returned items
        pdf.cell(0, 4, "RETURNED ITEMS:", 0, 1)
        pdf.line(10, pdf.get_y(), 70, pdf.get_y())
        
        for barcode, item in return_data.get('items', {}).items():
            name = item.get('name', 'Unknown')[:18] + ('..' if len(item.get('name', '')) > 18 else '')
            pdf.cell(30, 4, name, 0, 0)
            pdf.cell(15, 4, f"x{item.get('quantity', 0)}", 0, 0, 'R')
            pdf.cell(25, 4, format_currency(item.get('subtotal', 0)), 0, 1, 'R')
        
        pdf.line(10, pdf.get_y(), 70, pdf.get_y())
        pdf.ln(2)
        
        # Exchange products if any - FIXED: Handle list format
        if 'exchange_products' in return_data and return_data['exchange_products']:
            pdf.cell(0, 4, "EXCHANGE ITEMS:", 0, 1)
            pdf.line(10, pdf.get_y(), 70, pdf.get_y())
            
            # Handle list format for exchange products
            for item in return_data['exchange_products']:
                name = item.get('name', 'Unknown')[:18] + ('..' if len(item.get('name', '')) > 18 else '')
                item_total = item.get('price', 0) * item.get('quantity', 0)
                pdf.cell(30, 4, name, 0, 0)
                pdf.cell(15, 4, f"x{item.get('quantity', 0)}", 0, 0, 'R')
                pdf.cell(25, 4, format_currency(item_total), 0, 1, 'R')
            
            pdf.line(10, pdf.get_y(), 70, pdf.get_y())
            pdf.ln(2)
            
            # Exchange totals
            if 'exchange_subtotal' in return_data:
                pdf.cell(45, 4, "Exchange Subtotal:", 0, 0)
                pdf.cell(25, 4, format_currency(return_data.get('exchange_subtotal', 0)), 0, 1, 'R')
                
                pdf.cell(45, 4, "Exchange Tax:", 0, 0)
                pdf.cell(25, 4, format_currency(return_data.get('exchange_tax', 0)), 0, 1, 'R')
                
                pdf.cell(45, 4, "Exchange Total:", 0, 0)
                pdf.cell(25, 4, format_currency(return_data.get('exchange_total', 0)), 0, 1, 'R')
            
            # Exchange difference
            if 'exchange_difference' in return_data:
                difference = return_data.get('exchange_difference', 0)
                if difference > 0:
                    pdf.cell(45, 4, "Additional Payment:", 0, 0)
                    pdf.cell(25, 4, format_currency(difference), 0, 1, 'R')
                elif difference < 0:
                    pdf.cell(45, 4, "Refund Due:", 0, 0)
                    pdf.cell(25, 4, format_currency(abs(difference)), 0, 1, 'R')
        
        # Totals
        pdf.cell(45, 4, "Subtotal Refund:", 0, 0)
        pdf.cell(25, 4, format_currency(return_data.get('subtotal_refund', 0)), 0, 1, 'R')
        
        pdf.cell(45, 4, "Tax Refund:", 0, 0)
        pdf.cell(25, 4, format_currency(return_data.get('tax_refund', 0)), 0, 1, 'R')
        
        pdf.set_font("Courier", 'B', 10)
        pdf.cell(45, 5, "TOTAL REFUND:", 0, 0)
        pdf.cell(25, 5, format_currency(return_data.get('total_refund', 0)), 0, 1, 'R')
        
        pdf.set_font("Courier", size=8)
        pdf.cell(0, 4, f"Method: {return_data.get('refund_method', 'N/A')}", 0, 1)
        pdf.cell(0, 4, f"Reason: {return_data.get('reason', 'N/A')}", 0, 1)
        
        pdf_data = pdf.output(dest='S').encode('latin1')
        
        st.download_button(
            label="📄 Download PDF Receipt",
            data=pdf_data,
            file_name=f"return_receipt_{return_data.get('return_id', 'unknown')}.pdf",
            mime="application/pdf",
            key=f"dl_pdf_{return_data.get('return_id', 'unknown')}"
        )
        return True
        
    except Exception as e:
        st.error(f"PDF creation failed: {str(e)}")
        return False
    
def generate_return_receipt(return_data):
    settings = load_data(SETTINGS_FILE)
    receipt = []
    
    # Header
    receipt.append("=" * 50)
    receipt.append(f"{settings.get('store_name', 'SUPERMARKET POS').center(50)}")
    receipt.append(f"{settings.get('store_address', '').center(50)}")
    receipt.append(f"Tel: {settings.get('store_phone', '').center(50)}")
    receipt.append("=" * 50)
    
    if 'exchange_products' in return_data:
        receipt.append("EXCHANGE RECEIPT".center(50))
    else:
        receipt.append("RETURN RECEIPT".center(50))
    
    receipt.append("=" * 50)
    
    # Return information
    receipt.append(f"Return ID: {return_data['return_id']}")
    receipt.append(f"Original Transaction: {return_data['transaction_id']}")
    receipt.append(f"Date: {return_data['return_date']}")
    receipt.append(f"Processed by: {return_data['processed_by']}")
    receipt.append(f"Reason: {return_data['reason']}")
    receipt.append("-" * 50)
    
    # Returned items
    receipt.append("RETURNED ITEMS:")
    receipt.append("-" * 50)
    receipt.append(f"{'ITEM'.ljust(30)}{'QTY'.rjust(5)}{'AMOUNT'.rjust(15)}")
    receipt.append("-" * 50)
    
    for barcode, item in return_data['items'].items():
        name = item['name'][:28] + ('..' if len(item['name']) > 28 else '')
        receipt.append(f"{name.ljust(30)}{str(item['quantity']).rjust(5)}{format_currency(item['subtotal']).rjust(15)}")
    
    # Exchange items if any - FIXED: Handle list format
    if 'exchange_products' in return_data and return_data['exchange_products']:
        receipt.append("-" * 50)
        receipt.append("EXCHANGE ITEMS:")
        receipt.append("-" * 50)
        receipt.append(f"{'ITEM'.ljust(30)}{'QTY'.rjust(5)}{'AMOUNT'.rjust(15)}")
        receipt.append("-" * 50)
        
        # Handle list format for exchange products
        for item in return_data['exchange_products']:
            name = item['name'][:28] + ('..' if len(item['name']) > 28 else '')
            item_total = item['price'] * item['quantity']
            receipt.append(f"{name.ljust(30)}{str(item['quantity']).rjust(5)}{format_currency(item_total).rjust(15)}")
    
    # Totals
    receipt.append("-" * 50)
    receipt.append(f"{'Subtotal Refund:'.ljust(35)}{format_currency(return_data['total_refund'] - return_data.get('tax_refund', 0)).rjust(15)}")
    receipt.append(f"{'Tax Refund:'.ljust(35)}{format_currency(return_data.get('tax_refund', 0)).rjust(15)}")
    
    # Exchange totals if any
    if 'exchange_subtotal' in return_data:
        receipt.append("-" * 50)
        receipt.append("EXCHANGE TOTALS:")
        receipt.append(f"{'Exchange Subtotal:'.ljust(35)}{format_currency(return_data.get('exchange_subtotal', 0)).rjust(15)}")
        receipt.append(f"{'Exchange Tax:'.ljust(35)}{format_currency(return_data.get('exchange_tax', 0)).rjust(15)}")
        receipt.append(f"{'Exchange Total:'.ljust(35)}{format_currency(return_data.get('exchange_total', 0)).rjust(15)}")
    
    # Exchange difference
    if 'exchange_difference' in return_data:
        difference = return_data['exchange_difference']
        if difference > 0:
            receipt.append(f"{'Additional Payment:'.ljust(35)}{format_currency(difference).rjust(15)}")
        elif difference < 0:
            receipt.append(f"{'Refund Due:'.ljust(35)}{format_currency(abs(difference)).rjust(15)}")
    
    receipt.append("=" * 50)
    receipt.append(f"{'TOTAL REFUND:'.ljust(35)}{format_currency(return_data['total_refund']).rjust(15)}")
    receipt.append("=" * 50)
    
    # Payment information
    receipt.append(f"Refund Method: {return_data['refund_method']}")
    receipt.append(f"Status: {return_data['status'].replace('_', ' ').title()}")
    receipt.append("-" * 50)
    
    # Footer
    if settings.get('receipt_footer', ''):
        receipt.append(settings['receipt_footer'])
    receipt.append("Thank you for your business!".center(50))
    receipt.append("=" * 50)
    
    return "\n".join(receipt)

# Purchase Orders Management
# Constants (at the top of your file)
PURCHASE_ORDERS_FILE = os.path.join(DATA_DIR, "purchase_orders.json")

def generate_purchase_order(supplier_id, items):
    suppliers = load_data(SUPPLIERS_FILE)
    products = load_data(PRODUCTS_FILE)
    purchase_orders = load_data(PURCHASE_ORDERS_FILE)
    
    if supplier_id not in suppliers:
        return None
    
    supplier = suppliers[supplier_id]
    po_id = generate_short_id()
    
    # Calculate totals
    total_cost = 0
    for item in items:
        product = products.get(item['barcode'], {})
        total_cost += item['quantity'] * product.get('cost', 0)
    
    # Create PO
    purchase_orders[po_id] = {
        'po_id': po_id,
        'supplier_id': supplier_id,
        'supplier_name': supplier['name'],
        'date_created': get_current_datetime().strftime("%Y-%m-%d %H:%M:%S"),
        'created_by': st.session_state.user_info['username'],
        'items': items,
        'total_cost': total_cost,
        'status': 'pending',  # pending, partially_received, received, cancelled
        'receipts': [],  # Array to track multiple receipts
        'date_received': None,
        'received_by': None
    }
    
    save_data(purchase_orders, PURCHASE_ORDERS_FILE)
    return po_id

def generate_po_report(po_id):
    purchase_orders = load_data(PURCHASE_ORDERS_FILE)
    products = load_data(PRODUCTS_FILE)
    settings = load_data(SETTINGS_FILE)
    
    if po_id not in purchase_orders:
        return None
    
    po = purchase_orders[po_id]
    
    report = f"PURCHASE ORDER #{po_id}\n"
    report += f"{settings.get('store_name', 'Supermarket POS')}\n"
    report += f"Date: {po['date_created']}\n"
    report += "=" * 50 + "\n"
    report += f"Supplier: {po['supplier_name']}\n"
    report += f"Created by: {po['created_by']}\n"
    report += "=" * 50 + "\n"
    report += "ITEMS:\n"
    report += "Barcode\tProduct\tQty\tUnit Cost\tTotal\n"
    
    for item in po['items']:
        product = products.get(item['barcode'], {'name': 'Unknown', 'cost': 0})
        report += f"{item['barcode']}\t{product['name']}\t{item['quantity']}\t"
        report += f"{format_currency(product.get('cost', 0))}\t"
        report += f"{format_currency(item['quantity'] * product.get('cost', 0))}\n"
    
    report += "=" * 50 + "\n"
    report += f"TOTAL COST: {format_currency(po['total_cost'])}\n"
    report += f"STATUS: {po['status'].upper().replace('_', ' ')}\n"
    
    if po['receipts']:
        report += "\nRECEIPT HISTORY:\n"
        for receipt in po['receipts']:
            report += f"- {receipt['date']} by {receipt['received_by']}\n"
            for item in receipt['items']:
                report += f"  {item['name']}: {item['received_quantity']}/{item['ordered_quantity']}\n"
    
    if po['status'] in ['received', 'partially_received']:
        report += f"\nCompleted on: {po['date_received']} by {po['received_by']}\n"
    
    return report

def process_received_po(po_id, received_items, notes, mark_as_complete=False):
    purchase_orders = load_data(PURCHASE_ORDERS_FILE)
    inventory = load_data(INVENTORY_FILE)
    products = load_data(PRODUCTS_FILE)
    
    if po_id not in purchase_orders:
        return False
    
    po = purchase_orders[po_id]
    
    if po['status'] == 'received':
        return True  # Already fully processed
    
    # Update inventory only for received items
    for item in received_items:
        if item['received_quantity'] > 0:
            barcode = item['barcode']
            
            if barcode in inventory:
                inventory[barcode]['quantity'] += item['received_quantity']
            else:
                # Initialize inventory with default values if product doesn't exist in inventory
                inventory[barcode] = {
                    'quantity': item['received_quantity'],
                    'reorder_point': 10,  # Default reorder point
                    'cost': products.get(barcode, {}).get('cost', 0)  # Get cost from products if available
                }
            
            inventory[barcode]['last_updated'] = get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
            inventory[barcode]['updated_by'] = st.session_state.user_info['username']
    
    # Update PO status
    if all(item['received_quantity'] == item['ordered_quantity'] for item in received_items):
        po['status'] = 'received'
    elif mark_as_complete:
        po['status'] = 'partially_received'
    else:
        po['status'] = 'pending'  # Still waiting for more items
    
    # Add receipt details to PO
    po['receipts'] = po.get('receipts', [])
    po['receipts'].append({
        'date': get_current_datetime().strftime("%Y-%m-%d %H:%M:%S"),
        'received_by': st.session_state.user_info['username'],
        'items': received_items,
        'notes': notes
    })
    
    # Update the PO items if partially received and marked as complete
    if mark_as_complete and po['status'] == 'partially_received':
        # Adjust PO items to only include remaining quantities
        po['items'] = [
            {
                'barcode': item['barcode'],
                'name': item['name'],
                'quantity': item['ordered_quantity'] - item['received_quantity'],
                'cost': item['cost']
            }
            for item in received_items
            if item['received_quantity'] < item['ordered_quantity']
        ]
    
    # Update completion info if fully or partially completed
    if po['status'] in ['received', 'partially_received']:
        po['date_received'] = get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
        po['received_by'] = st.session_state.user_info['username']
    
    save_data(purchase_orders, PURCHASE_ORDERS_FILE)
    save_data(inventory, INVENTORY_FILE)
    return True

def purchase_orders_management():
    if not is_manager():
        st.warning("You don't have permission to access this page")
        return
    
    st.title("Purchase Orders Management")
    
    tab1, tab2, tab3 = st.tabs(["Create PO", "View POs", "Receive PO"])
    
    with tab1:
        st.header("Create Purchase Order")
        
        suppliers = load_data(SUPPLIERS_FILE)
        products = load_data(PRODUCTS_FILE)
        inventory = load_data(INVENTORY_FILE)
        
        if not suppliers:
            st.warning("No suppliers available. Please add suppliers first.")
            return
        
        if not products:
            st.warning("No products available. Please add products first.")
            return
        
        if 'po_items' not in st.session_state:
            st.session_state.po_items = []
        
        # Display low stock items
        low_stock_items = []
        for barcode, inv_data in inventory.items():
            if barcode in products and inv_data.get('quantity', 0) < inv_data.get('reorder_point', 10):
                product = products[barcode]
                low_stock_items.append({
                    'barcode': barcode,
                    'name': product['name'],
                    'current_stock': inv_data.get('quantity', 0),
                    'reorder_point': inv_data.get('reorder_point', 10),
                    'cost': product.get('cost', 0),
                    'quantity': max(inv_data.get('reorder_point', 10) - inv_data.get('quantity', 0), 1)
                })
        
        if low_stock_items:
            st.info("The following items are below reorder point:")
            low_stock_df = pd.DataFrame(low_stock_items)
            st.dataframe(low_stock_df[['name', 'current_stock', 'reorder_point', 'cost']])
            
            if st.button("Add All Low Stock Items to PO"):
                for item in low_stock_items:
                    if not any(i['barcode'] == item['barcode'] for i in st.session_state.po_items):
                        st.session_state.po_items.append({
                            'barcode': item['barcode'],
                            'name': item['name'],
                            'quantity': item['quantity'],
                            'cost': item['cost']
                        })
                st.rerun()
        
        with st.form("po_form"):
            supplier_options = {f"{v['name']} ({k})": k for k, v in suppliers.items()}
            selected_supplier = st.selectbox("Select Supplier", [""] + list(supplier_options.keys()))
            
            product_options = {f"{v['name']} ({k})": k for k, v in products.items()}
            selected_product = st.selectbox("Select Product", [""] + list(product_options.keys()))
            quantity = st.number_input("Quantity", min_value=1, value=1, step=1)
            
            po_notes = st.text_area("Notes")
            
            col1, col2 = st.columns(2)
            with col1:
                add_item = st.form_submit_button("Add Item to PO")
            with col2:
                create_po = st.form_submit_button("Create Purchase Order")
            
            if add_item and selected_product:
                barcode = product_options[selected_product]
                if not any(i['barcode'] == barcode for i in st.session_state.po_items):
                    st.session_state.po_items.append({
                        'barcode': barcode,
                        'name': products[barcode]['name'],
                        'quantity': quantity,
                        'cost': products[barcode].get('cost', 0)
                    })
                    st.rerun()
                else:
                    st.warning("Item already in PO. Adjust quantity in PO items below.")
            
            if create_po:
                if not selected_supplier:
                    st.error("Please select a supplier")
                elif not st.session_state.po_items:
                    st.error("Please add items to the purchase order")
                else:
                    supplier_id = supplier_options[selected_supplier]
                    po_id = generate_purchase_order(supplier_id, st.session_state.po_items)
                    
                    if po_id:
                        st.session_state.last_po_id = po_id
                        po_report = generate_po_report(po_id)
                        st.success("Purchase order created successfully!")
                        st.subheader("Purchase Order")
                        st.text(po_report)
                        
                        st.session_state.po_items = []
                        
                    else:
                        st.error("Failed to create purchase order")
        
        st.subheader("Current PO Items")
        if not st.session_state.po_items:
            st.info("No items in PO")
        else:
            items_copy = st.session_state.po_items.copy()
            items_to_remove = []
            
            for idx, item in enumerate(st.session_state.po_items):
                with st.container():
                    col1, col2, col3, col4 = st.columns([4, 2, 2, 1])
                    with col1:
                        st.write(f"**{item['name']}**")
                    with col2:
                        new_qty = st.number_input(
                            "Qty", 
                            min_value=1, 
                            value=item['quantity'], 
                            key=f"po_qty_{idx}"
                        )
                        if new_qty != item['quantity']:
                            items_copy[idx]['quantity'] = new_qty
                    with col3:
                        st.write(f"Cost: {format_currency(item['cost'])}")
                        st.write(f"Total: {format_currency(item['cost'] * item['quantity'])}")
                    with col4:
                        if st.button("❌", key=f"remove_po_{idx}"):
                            items_to_remove.append(idx)
            
            if items_copy != st.session_state.po_items:
                st.session_state.po_items = items_copy
                st.rerun()
            
            if items_to_remove:
                for idx in sorted(items_to_remove, reverse=True):
                    st.session_state.po_items.pop(idx)
                st.rerun()
        
        if st.button("Print Last Purchase Order"):
            if 'last_po_id' in st.session_state:
                po_report = generate_po_report(st.session_state.last_po_id)
                if print_receipt(po_report):
                    st.success("Purchase order printed successfully")
                else:
                    st.error("Failed to print purchase order")
            else:
                st.warning("No purchase order created yet")

    with tab2:
        st.header("View Purchase Orders")
        
        purchase_orders = load_data(PURCHASE_ORDERS_FILE)
        suppliers = load_data(SUPPLIERS_FILE)
        
        if not purchase_orders:
            st.info("No purchase orders available")
        else:
            col1, col2 = st.columns(2)
            with col1:
                status_filter = st.selectbox("Filter by Status", ["All", "pending", "partially_received", "received"])
            with col2:
                supplier_filter = st.selectbox("Filter by Supplier", ["All"] + list(set(po['supplier_name'] for po in purchase_orders.values())))
            
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date", value=datetime.date.today() - datetime.timedelta(days=30))
            with col2:
                end_date = st.date_input("End Date", value=datetime.date.today())
            
            filtered_pos = []
            for po_id, po in purchase_orders.items():
                try:
                    po_date = datetime.datetime.strptime(po['date_created'], "%Y-%m-%d %H:%M:%S").date()
                    if (status_filter == "All" or po['status'] == status_filter) and \
                       (supplier_filter == "All" or po['supplier_name'] == supplier_filter) and \
                       (start_date <= po_date <= end_date):
                        filtered_pos.append(po)
                except (ValueError, KeyError):
                    continue
            
            if not filtered_pos:
                st.info("No purchase orders match the filters")
            else:
                st.subheader("Purchase Orders Summary")
                po_summary = []
                for po in filtered_pos:
                    po_summary.append({
                        'PO ID': po['po_id'],
                        'Supplier': po['supplier_name'],
                        'Date': po['date_created'],
                        'Items': len(po['items']),
                        'Total Cost': format_currency(po['total_cost']),
                        'Status': po['status'].capitalize().replace('_', ' '),
                        'Created By': po['created_by']
                    })
                
                st.dataframe(pd.DataFrame(po_summary))
                
                selected_po = st.selectbox("View PO Details", [""] + [f"{po['po_id']} - {po['supplier_name']}" for po in filtered_pos])
                
                if selected_po:
                    po_id = selected_po.split(" - ")[0]
                    po = purchase_orders[po_id]
                    
                    # Initialize receipts if not exists
                    if 'receipts' not in po:
                        po['receipts'] = []
                    
                    st.subheader(f"Purchase Order #{po_id}")
                    st.write(f"Supplier: {po['supplier_name']}")
                    st.write(f"Date Created: {po['date_created']}")
                    st.write(f"Created By: {po['created_by']}")
                    st.write(f"Status: {po['status'].capitalize().replace('_', ' ')}")
                    st.write(f"Total Cost: {format_currency(po['total_cost'])}")
                    
                    st.subheader("Items")
                    items_df = pd.DataFrame(po['items'])
                    st.dataframe(items_df)
                    
                    if po['receipts']:
                        st.subheader("Receipt History")
                        for receipt in po['receipts']:
                            st.write(f"**{receipt['date']}** by {receipt['received_by']}")
                            if receipt.get('notes'):
                                st.write(f"Notes: {receipt['notes']}")
                            receipt_df = pd.DataFrame(receipt['items'])
                            st.dataframe(receipt_df)
                    
                    if st.button("Print PO"):
                        po_report = generate_po_report(po_id)
                        if print_receipt(po_report):
                            st.success("Purchase order printed successfully")
                        else:
                            st.error("Failed to print purchase order")

    with tab3:
        st.header("Receive Purchase Order")
        
        purchase_orders = load_data(PURCHASE_ORDERS_FILE)
        pending_pos = [po for po in purchase_orders.values() if po.get('status') in ['pending', 'partially_received']]
        
        if not pending_pos:
            st.info("No pending purchase orders to receive")
        else:
            selected_po = st.selectbox("Select PO to Receive", [""] + [f"{po['po_id']} - {po['supplier_name']}" for po in pending_pos])
            
            if selected_po:
                po_id = selected_po.split(" - ")[0]
                po = purchase_orders[po_id]
                
                # Initialize receipts if not exists
                if 'receipts' not in po:
                    po['receipts'] = []
                
                st.subheader(f"Purchase Order #{po_id}")
                st.write(f"Supplier: {po['supplier_name']}")
                st.write(f"Date Created: {po['date_created']}")
                st.write(f"Total Cost: {format_currency(po['total_cost'])}")
                st.write(f"Current Status: {po['status'].capitalize().replace('_', ' ')}")
                
                if po['receipts']:
                    st.subheader("Previous Receipts")
                    for receipt in po['receipts']:
                        st.write(f"**{receipt['date']}** by {receipt['received_by']}")
                        if receipt.get('notes'):
                            st.write(f"Notes: {receipt['notes']}")
                        receipt_df = pd.DataFrame(receipt['items'])
                        st.dataframe(receipt_df)
                
                st.subheader("Receive Items")
                with st.form("receive_po_form"):
                    received_items = []
                    for item in po['items']:
                        max_qty = item['quantity']
                        received_qty = st.number_input(
                            f"Quantity received for {item['name']} (ordered: {max_qty})",
                            min_value=0,
                            max_value=max_qty,
                            value=max_qty,
                            key=f"receive_{item['barcode']}"
                        )
                        received_items.append({
                            'barcode': item['barcode'],
                            'name': item['name'],
                            'ordered_quantity': item['quantity'],
                            'received_quantity': received_qty,
                            'cost': item.get('cost', 0)
                        })
                    
                    notes = st.text_area("Receiving Notes")
                    mark_as_complete = st.checkbox("Mark as complete (even if not all items received)", 
                                                 value=po['status'] == 'partially_received')
                    
                    if st.form_submit_button("Process Receipt"):
                        if all(item['received_quantity'] == 0 for item in received_items):
                            st.error("Cannot process receipt with all quantities as zero")
                        else:
                            if process_received_po(po_id, received_items, notes, mark_as_complete):
                                st.success("Receipt processed successfully")
                                st.rerun()
                            else:
                                st.error("Failed to process receipt")

def generate_purchase_order(supplier_id, items):
    suppliers = load_data(SUPPLIERS_FILE)
    products = load_data(PRODUCTS_FILE)
    purchase_orders = load_data(PURCHASE_ORDERS_FILE)
    
    if supplier_id not in suppliers:
        return None
    
    supplier = suppliers[supplier_id]
    po_id = generate_short_id()
    
    # Calculate totals
    total_cost = 0
    for item in items:
        product = products.get(item['barcode'], {})
        total_cost += item['quantity'] * product.get('cost', 0)
    
    # Create PO
    purchase_orders[po_id] = {
        'po_id': po_id,
        'supplier_id': supplier_id,
        'supplier_name': supplier['name'],
        'date_created': get_current_datetime().strftime("%Y-%m-%d %H:%M:%S"),
        'created_by': st.session_state.user_info['username'],
        'items': items,
        'total_cost': total_cost,
        'status': 'pending',
        'date_received': None,
        'received_by': None
    }
    
    save_data(purchase_orders, PURCHASE_ORDERS_FILE)
    return po_id

def generate_po_report(po_id):
    purchase_orders = load_data(PURCHASE_ORDERS_FILE)
    products = load_data(PRODUCTS_FILE)
    settings = load_data(SETTINGS_FILE)
    
    if po_id not in purchase_orders:
        return None
    
    po = purchase_orders[po_id]
    
    report = f"PURCHASE ORDER #{po_id}\n"
    report += f"{settings.get('store_name', 'Supermarket POS')}\n"
    report += f"Date: {po['date_created']}\n"
    report += "=" * 50 + "\n"
    report += f"Supplier: {po['supplier_name']}\n"
    report += f"Created by: {po['created_by']}\n"
    report += "=" * 50 + "\n"
    report += "ITEMS:\n"
    report += "Barcode\tProduct\tQty\tUnit Cost\tTotal\n"
    
    for item in po['items']:
        product = products.get(item['barcode'], {'name': 'Unknown', 'cost': 0})
        report += f"{item['barcode']}\t{product['name']}\t{item['quantity']}\t"
        report += f"{format_currency(product.get('cost', 0))}\t"
        report += f"{format_currency(item['quantity'] * product.get('cost', 0))}\n"
    
    report += "=" * 50 + "\n"
    report += f"TOTAL COST: {format_currency(po['total_cost'])}\n"
    report += f"STATUS: {po['status'].upper()}\n"
    
    if po['status'] == 'received':
        report += f"Received on: {po['date_received']} by {po['received_by']}\n"
    
    return report

def process_received_po(po_id, received_items, notes, mark_as_complete=False):
    purchase_orders = load_data(PURCHASE_ORDERS_FILE)
    inventory = load_data(INVENTORY_FILE)
    products = load_data(PRODUCTS_FILE)
    
    if po_id not in purchase_orders:
        return False
    
    po = purchase_orders[po_id]
    
    if po['status'] == 'received':
        return True  # Already fully processed
    
    # Initialize receipts if not exists
    if 'receipts' not in po:
        po['receipts'] = []
    
    # Update inventory only for received items
    for item in received_items:
        if item['received_quantity'] > 0:
            barcode = item['barcode']
            
            if barcode in inventory:
                inventory[barcode]['quantity'] += item['received_quantity']
            else:
                # Initialize inventory with default values if product doesn't exist in inventory
                inventory[barcode] = {
                    'quantity': item['received_quantity'],
                    'reorder_point': 10,  # Default reorder point
                    'cost': products.get(barcode, {}).get('cost', 0)  # Get cost from products if available
                }
            
            inventory[barcode]['last_updated'] = get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
            inventory[barcode]['updated_by'] = st.session_state.user_info['username']
    
    # Update PO status
    if all(item['received_quantity'] == item['ordered_quantity'] for item in received_items):
        po['status'] = 'received'
    elif mark_as_complete:
        po['status'] = 'partially_received'
    else:
        po['status'] = 'pending'  # Still waiting for more items
    
    # Add receipt details to PO
    po['receipts'].append({
        'date': get_current_datetime().strftime("%Y-%m-%d %H:%M:%S"),
        'received_by': st.session_state.user_info['username'],
        'items': received_items,
        'notes': notes
    })
    
    # Update the PO items if partially received and marked as complete
    if mark_as_complete and po['status'] == 'partially_received':
        # Adjust PO items to only include remaining quantities
        po['items'] = [
            {
                'barcode': item['barcode'],
                'name': item['name'],
                'quantity': item['ordered_quantity'] - item['received_quantity'],
                'cost': item['cost']
            }
            for item in received_items
            if item['received_quantity'] < item['ordered_quantity']
        ]
    
    # Update completion info if fully or partially completed
    if po['status'] in ['received', 'partially_received']:
        po['date_received'] = get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
        po['received_by'] = st.session_state.user_info['username']
    
    save_data(purchase_orders, PURCHASE_ORDERS_FILE)
    save_data(inventory, INVENTORY_FILE)
    return True

# product Management 
def product_management():
    if not is_manager():
        st.warning("You don't have permission to access this page")
        return
    
    st.title("Product Management")
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Add Product", 
        "View/Edit Products", 
        "Delete Product", 
        "Bulk Import", 
        "Template Management",
        "Category Management"
    ])
    
    # Helper function to load categories with proper structure
    def load_categories_data():
        categories_data = load_data(CATEGORIES_FILE)
        # Ensure the data structure is correct
        if 'categories' not in categories_data:
            categories_data['categories'] = []
        if 'subcategories' not in categories_data:
            categories_data['subcategories'] = {}
        return categories_data
    
    # Helper function to get subcategories for a category
    def get_subcategories(category):
        categories_data = load_categories_data()
        return categories_data['subcategories'].get(category, [])
    
    # Helper function to add new subcategory
    def add_subcategory(category, subcategory):
        categories_data = load_categories_data()
        if category not in categories_data['subcategories']:
            categories_data['subcategories'][category] = []
        if subcategory and subcategory not in categories_data['subcategories'][category]:
            categories_data['subcategories'][category].append(subcategory)
        save_data(categories_data, CATEGORIES_FILE)
    
    with tab1:
        st.header("Add New Product")
        
        categories_data = load_categories_data()
        categories = categories_data.get('categories', [])
        brands_data = load_data(BRANDS_FILE)
        brands = brands_data.get('brands', [])
        suppliers = load_data(SUPPLIERS_FILE)
        
        # Separate form for adding new category (outside the main form)
        with st.expander("Quick Add Category/Subcategory"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_category_name = st.text_input("New Category Name", key="quick_add_category")
                if st.button("Add Category", key="add_category_btn"):
                    if new_category_name and new_category_name not in categories:
                        categories_data['categories'].append(new_category_name)
                        categories_data['subcategories'][new_category_name] = []
                        save_data(categories_data, CATEGORIES_FILE)
                        st.success(f"Category '{new_category_name}' added")
                        st.rerun()
                    elif new_category_name in categories:
                        st.error("Category already exists")
            
            with col2:
                selected_category_for_sub = st.selectbox("Select Category for Subcategory", 
                                                       [""] + categories, key="cat_for_sub")
                new_subcategory_name = st.text_input("New Subcategory Name", key="quick_add_subcategory",
                                                   disabled=not selected_category_for_sub)
                if st.button("Add Subcategory", key="add_subcategory_btn") and selected_category_for_sub:
                    if new_subcategory_name:
                        add_subcategory(selected_category_for_sub, new_subcategory_name)
                        st.success(f"Subcategory '{new_subcategory_name}' added to '{selected_category_for_sub}'")
                        st.rerun()
        
        # Main product form
        with st.form("add_product_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Product Name*", help="Enter the product name")
                description = st.text_area("Description", help="Product description for customers")
                
                # Category selection
                category = st.selectbox("Category", [""] + categories, help="Select product category", 
                                      key="add_product_category")
                
                # Get subcategories based on selected category
                subcategories_list = []
                if category:
                    subcategories_list = get_subcategories(category)
                
                # Subcategory selection (dynamic based on category)
                subcategory = st.selectbox("Subcategory", [""] + subcategories_list, 
                                         help="Select product subcategory",
                                         key="add_product_subcategory")
                
                # Brand selection
                brand = st.selectbox("Brand", [""] + brands, help="Select product brand",
                                   key="add_product_brand")
            
            with col2:
                price = st.number_input("Selling Price*", min_value=0.01, step=0.01, value=1.0, 
                                      help="Customer selling price", key="add_product_price")
                cost = st.number_input("Cost Price*", min_value=0.01, step=0.01, value=1.0, 
                                     help="Wholesale or manufacturing cost", key="add_product_cost")
                
                # Barcode options
                barcode_option = st.radio("Barcode Options", 
                                         ["Generate Automatically", "Enter Manually"], 
                                         help="Choose how to handle barcode",
                                         key="add_product_barcode_option")
                
                if barcode_option == "Enter Manually":
                    barcode = st.text_input("Barcode*", help="Enter 12-13 digit barcode",
                                          key="add_product_barcode_manual")
                else:
                    barcode = st.text_input("Barcode (leave blank to auto-generate)", 
                                          value="", help="Leave empty to auto-generate barcode",
                                          key="add_product_barcode_auto")
                
                # Initial stock
                initial_stock = st.number_input("Initial Stock", min_value=0, value=0, step=1,
                                              help="Initial inventory quantity",
                                              key="add_product_stock")
                
                # Reorder point
                reorder_point = st.number_input("Reorder Point", min_value=0, value=10, step=1,
                                              help="Stock level to trigger reordering",
                                              key="add_product_reorder")
                
                # Product image
                image = st.file_uploader("Product Image", type=['jpg', 'png', 'jpeg', 'gif'],
                                       help="Upload product image (optional)",
                                       key="add_product_image")
            
            # Supplier information
            supplier_options = [""]
            if suppliers:
                supplier_options.extend([v['name'] for v in suppliers.values()])
            
            # FIXED: Safe supplier selection
            selected_supplier = st.selectbox("Primary Supplier", supplier_options,
                                           help="Select main supplier for this product",
                                           key="add_product_supplier")
            
            # Product status
            active = st.checkbox("Active Product", value=True, help="Enable/disable product for sales",
                               key="add_product_active")
            
            submit_button = st.form_submit_button("Add Product")
            
            if submit_button:
                # Validation
                errors = []
                if not name:
                    errors.append("Product name is required")
                if price <= 0:
                    errors.append("Price must be greater than 0")
                if cost <= 0:
                    errors.append("Cost must be greater than 0")
                if barcode_option == "Enter Manually" and not barcode:
                    errors.append("Barcode is required when selecting manual entry")
                if barcode_option == "Enter Manually" and barcode and not barcode.isdigit():
                    errors.append("Barcode must contain only digits")
                if barcode_option == "Enter Manually" and barcode and len(barcode) not in [12, 13]:
                    errors.append("Barcode must be 12 or 13 digits")
                
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    products = load_data(PRODUCTS_FILE)
                    inventory = load_data(INVENTORY_FILE)
                    
                    # Generate barcode if needed
                    if not barcode or barcode_option == "Generate Automatically":
                        barcode = generate_barcode()
                    
                    # Check for duplicate barcode
                    if barcode in products:
                        st.error(f"Product with barcode {barcode} already exists")
                    else:
                        # Save product
                        products[barcode] = {
                            'barcode': barcode,
                            'name': name,
                            'description': description,
                            'price': price,
                            'cost': cost,
                            'category': category,
                            'subcategory': subcategory,
                            'brand': brand,
                            'supplier': selected_supplier if selected_supplier else None,
                            'active': active,
                            'date_added': get_current_datetime().strftime("%Y-%m-%d %H:%M:%S"),
                            'added_by': st.session_state.user_info['username']
                        }
                        
                        # Save image if provided
                        if image:
                            # Create images directory if it doesn't exist
                            images_dir = os.path.join(DATA_DIR, "product_images")
                            os.makedirs(images_dir, exist_ok=True)
                            
                            # Save image with barcode as filename
                            image_ext = image.name.split('.')[-1]
                            image_path = os.path.join(images_dir, f"{barcode}.{image_ext}")
                            with open(image_path, 'wb') as f:
                                f.write(image.getbuffer())
                            products[barcode]['image'] = image_path
                        
                        # Initialize inventory
                        inventory[barcode] = {
                            'quantity': initial_stock,
                            'reorder_point': reorder_point,
                            'last_updated': get_current_datetime().strftime("%Y-%m-%d %H:%M:%S"),
                            'updated_by': st.session_state.user_info['username']
                        }
                        
                        # Update brand mapping if brand is selected
                        if brand:
                            brands_data = load_data(BRANDS_FILE)
                            brand_products = brands_data.get('brand_products', {})
                            if brand not in brand_products:
                                brand_products[brand] = []
                            if barcode not in brand_products[brand]:
                                brand_products[brand].append(barcode)
                            brands_data['brand_products'] = brand_products
                            save_data(brands_data, BRANDS_FILE)
                        
                        save_data(products, PRODUCTS_FILE)
                        save_data(inventory, INVENTORY_FILE)
                        st.success(f"Product '{name}' added successfully with barcode: {barcode}")

    with tab2:
        st.header("View/Edit Products")
        
        products = load_data(PRODUCTS_FILE)
        inventory = load_data(INVENTORY_FILE)
        categories_data = load_categories_data()
        brands_data = load_data(BRANDS_FILE)
        suppliers = load_data(SUPPLIERS_FILE)
        
        if not products:
            st.info("No products available")
        else:
            # Advanced filtering
            st.subheader("Filter Products")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                search_term = st.text_input("Search by name or barcode", key="filter_search")
                category_filter = st.selectbox("Filter by Category", 
                                             [""] + categories_data.get('categories', []),
                                             key="filter_category")
            
            with col2:
                brand_filter = st.selectbox("Filter by Brand", 
                                          [""] + brands_data.get('brands', []),
                                          key="filter_brand")
                status_filter = st.selectbox("Filter by Status", 
                                           ["All", "Active", "Inactive"],
                                           key="filter_status")
            
            with col3:
                stock_filter = st.selectbox("Filter by Stock", 
                                          ["All", "In Stock", "Low Stock", "Out of Stock"],
                                          key="filter_stock")
                sort_by = st.selectbox("Sort By", 
                                     ["Name (A-Z)", "Name (Z-A)", "Price (High-Low)", 
                                      "Price (Low-High)", "Stock (High-Low)", "Stock (Low-High)"],
                                     key="filter_sort")
            
            # Apply filters
            filtered_products = products.copy()
            
            if search_term:
                filtered_products = {k: v for k, v in filtered_products.items() 
                                   if search_term.lower() in v['name'].lower() or 
                                   search_term.lower() in k.lower()}
            
            if category_filter:
                filtered_products = {k: v for k, v in filtered_products.items() 
                                   if v.get('category') == category_filter}
            
            if brand_filter:
                filtered_products = {k: v for k, v in filtered_products.items() 
                                   if v.get('brand') == brand_filter}
            
            if status_filter != "All":
                active_status = status_filter == "Active"
                filtered_products = {k: v for k, v in filtered_products.items() 
                                   if v.get('active', True) == active_status}
            
            if stock_filter != "All":
                for barcode in list(filtered_products.keys()):
                    stock = inventory.get(barcode, {}).get('quantity', 0)
                    reorder = inventory.get(barcode, {}).get('reorder_point', 10)
                    
                    if stock_filter == "In Stock" and stock <= 0:
                        del filtered_products[barcode]
                    elif stock_filter == "Low Stock" and (stock > reorder or stock == 0):
                        del filtered_products[barcode]
                    elif stock_filter == "Out of Stock" and stock > 0:
                        del filtered_products[barcode]
            
            # Apply sorting
            if sort_by == "Name (A-Z)":
                filtered_products = dict(sorted(filtered_products.items(), 
                                              key=lambda x: x[1]['name'].lower()))
            elif sort_by == "Name (Z-A)":
                filtered_products = dict(sorted(filtered_products.items(), 
                                              key=lambda x: x[1]['name'].lower(), reverse=True))
            elif sort_by == "Price (High-Low)":
                filtered_products = dict(sorted(filtered_products.items(), 
                                              key=lambda x: x[1]['price'], reverse=True))
            elif sort_by == "Price (Low-High)":
                filtered_products = dict(sorted(filtered_products.items(), 
                                              key=lambda x: x[1]['price']))
            elif sort_by == "Stock (High-Low)":
                filtered_products = dict(sorted(filtered_products.items(), 
                                              key=lambda x: inventory.get(x[0], {}).get('quantity', 0), 
                                              reverse=True))
            elif sort_by == "Stock (Low-High)":
                filtered_products = dict(sorted(filtered_products.items(), 
                                              key=lambda x: inventory.get(x[0], {}).get('quantity', 0)))
            
            st.write(f"**Found {len(filtered_products)} products**")
            
            # Pagination
            items_per_page = 10
            total_pages = max(1, (len(filtered_products) + items_per_page - 1) // items_per_page)
            page = st.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1,
                                 key="pagination_page")
            
            start_idx = (page - 1) * items_per_page
            end_idx = min(start_idx + items_per_page, len(filtered_products))
            
            # Display products for current page
            product_items = list(filtered_products.items())[start_idx:end_idx]
            
            for barcode, product in product_items:
                with st.expander(f"{product['name']} - {barcode}"):
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        # Display product image if available
                        if 'image' in product and os.path.exists(product['image']):
                            try:
                                img = Image.open(product['image'])
                                img.thumbnail((200, 200))
                                st.image(img, use_column_width=True)
                            except Exception as e:
                                st.error(f"Error loading image: {str(e)}")
                        else:
                            st.info("No image available")
                    
                    with col2:
                        # Create a unique form for each product
                        with st.form(key=f"edit_{barcode}"):
                            name = st.text_input("Name", value=product.get('name', ''), 
                                               key=f"edit_name_{barcode}")
                            description = st.text_area("Description", value=product.get('description', ''),
                                                     key=f"edit_desc_{barcode}")
                            
                            col21, col22 = st.columns(2)
                            with col21:
                                price = st.number_input("Price", value=product.get('price', 1.0), 
                                                      min_value=0.01, step=0.01,
                                                      key=f"edit_price_{barcode}")
                                cost = st.number_input("Cost", value=product.get('cost', 1.0), 
                                                     min_value=0.01, step=0.01,
                                                     key=f"edit_cost_{barcode}")
                                
                                # Category selection - FIXED: Safe index handling
                                current_category = product.get('category', '')
                                category_options = [""] + categories_data.get('categories', [])
                                category_index = 0
                                if current_category and current_category in category_options:
                                    category_index = category_options.index(current_category)
                                category = st.selectbox("Category", category_options, 
                                                      index=category_index,
                                                      key=f"edit_cat_{barcode}")
                                
                                # Get subcategories based on selected category
                                subcategories_list = []
                                if category:
                                    subcategories_list = get_subcategories(category)
                                
                                # Subcategory based on selected category - FIXED: Safe index handling
                                current_subcategory = product.get('subcategory', '')
                                subcategory_index = 0
                                if current_subcategory and current_subcategory in subcategories_list:
                                    subcategory_index = subcategories_list.index(current_subcategory) + 1
                                subcategory = st.selectbox("Subcategory", 
                                                         [""] + subcategories_list, 
                                                         index=subcategory_index,
                                                         key=f"edit_sub_{barcode}")
                            
                            with col22:
                                # Brand selection - FIXED: Safe index handling
                                current_brand = product.get('brand', '')
                                brand_options = [""] + brands_data.get('brands', [])
                                brand_index = 0
                                if current_brand and current_brand in brand_options:
                                    brand_index = brand_options.index(current_brand)
                                brand = st.selectbox("Brand", brand_options, 
                                                   index=brand_index,
                                                   key=f"edit_brand_{barcode}")
                                
                                # Supplier selection - FIXED: Safe index handling
                                supplier_options = [""] + [v['name'] for v in suppliers.values()]
                                current_supplier = product.get('supplier', '')
                                supplier_index = 0
                                if current_supplier and current_supplier in supplier_options:
                                    supplier_index = supplier_options.index(current_supplier)
                                supplier = st.selectbox("Supplier", supplier_options,
                                                      index=supplier_index,
                                                      key=f"edit_sup_{barcode}")
                                
                                # Inventory management
                                current_stock = inventory.get(barcode, {}).get('quantity', 0)
                                new_stock = st.number_input("Current Stock", min_value=0, value=current_stock, step=1,
                                                          key=f"edit_stock_{barcode}")
                                
                                current_reorder = inventory.get(barcode, {}).get('reorder_point', 10)
                                reorder_point = st.number_input("Reorder Point", min_value=0, value=current_reorder, step=1,
                                                              key=f"edit_reorder_{barcode}")
                                
                                active = st.checkbox("Active", value=product.get('active', True),
                                                   key=f"edit_active_{barcode}")
                            
                            # Image update
                            new_image = st.file_uploader("Update Image", type=['jpg', 'png', 'jpeg', 'gif'], 
                                                       key=f"edit_img_{barcode}")
                            
                            # Submit button
                            if st.form_submit_button("Update Product"):
                                # Update product data
                                products[barcode]['name'] = name
                                products[barcode]['description'] = description
                                products[barcode]['price'] = price
                                products[barcode]['cost'] = cost
                                products[barcode]['category'] = category
                                products[barcode]['subcategory'] = subcategory
                                products[barcode]['brand'] = brand
                                products[barcode]['supplier'] = supplier if supplier else None
                                products[barcode]['active'] = active
                                products[barcode]['last_updated'] = get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
                                products[barcode]['updated_by'] = st.session_state.user_info['username']
                                
                                # Update image if provided
                                if new_image:
                                    # Remove old image if exists
                                    if 'image' in products[barcode] and os.path.exists(products[barcode]['image']):
                                        try:
                                            os.remove(products[barcode]['image'])
                                        except:
                                            pass
                                    
                                    # Create images directory if it doesn't exist
                                    images_dir = os.path.join(DATA_DIR, "product_images")
                                    os.makedirs(images_dir, exist_ok=True)
                                    
                                    # Save new image
                                    image_ext = new_image.name.split('.')[-1]
                                    image_path = os.path.join(images_dir, f"{barcode}.{image_ext}")
                                    with open(image_path, 'wb') as f:
                                        f.write(new_image.getbuffer())
                                    products[barcode]['image'] = image_path
                                
                                # Update inventory
                                inventory[barcode]['quantity'] = new_stock
                                inventory[barcode]['reorder_point'] = reorder_point
                                inventory[barcode]['last_updated'] = get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
                                inventory[barcode]['updated_by'] = st.session_state.user_info['username']
                                
                                # Update brand mapping if brand changed
                                old_brand = product.get('brand')
                                if old_brand != brand:
                                    brands_data = load_data(BRANDS_FILE)
                                    brand_products = brands_data.get('brand_products', {})
                                    
                                    # Remove from old brand
                                    if old_brand and old_brand in brand_products and barcode in brand_products[old_brand]:
                                        brand_products[old_brand].remove(barcode)
                                    
                                    # Add to new brand
                                    if brand:
                                        if brand not in brand_products:
                                            brand_products[brand] = []
                                        if barcode not in brand_products[brand]:
                                            brand_products[brand].append(barcode)
                                    
                                    brands_data['brand_products'] = brand_products
                                    save_data(brands_data, BRANDS_FILE)
                                
                                save_data(products, PRODUCTS_FILE)
                                save_data(inventory, INVENTORY_FILE)
                                st.success("Product updated successfully")
                                
    with tab3:
        st.header("Delete Product")
        
        products = load_data(PRODUCTS_FILE)
        inventory = load_data(INVENTORY_FILE)
        
        if not products:
            st.info("No products available to delete")
        else:
            # Filter options
            col1, col2 = st.columns(2)
            with col1:
                search_term = st.text_input("Search products to delete", key="delete_search")
            with col2:
                category_filter = st.selectbox("Filter by category", 
                                             [""] + load_categories_data().get('categories', []),
                                             key="delete_category")
            
            # Apply filters
            filtered_products = products.copy()
            if search_term:
                filtered_products = {k: v for k, v in filtered_products.items() 
                                   if search_term.lower() in v['name'].lower() or 
                                   search_term.lower() in k.lower()}
            
            if category_filter:
                filtered_products = {k: v for k, v in filtered_products.items() 
                                   if v.get('category') == category_filter}
            
            if not filtered_products:
                st.info("No products match the filters")
            else:
                product_options = {f"{v['name']} ({k})": k for k, v in filtered_products.items()}
                selected_product = st.selectbox("Select Product to Delete", [""] + list(product_options.keys()),
                                              key="delete_select")
                
                if selected_product:
                    barcode = product_options[selected_product]
                    product = products[barcode]
                    
                    st.warning(f"⚠️ You are about to delete: {product['name']} ({barcode})")
                    
                    # Show product details
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Price:** {format_currency(product['price'])}")
                        st.write(f"**Category:** {product.get('category', 'N/A')}")
                        st.write(f"**Brand:** {product.get('brand', 'N/A')}")
                    
                    with col2:
                        stock = inventory.get(barcode, {}).get('quantity', 0)
                        st.write(f"**Current Stock:** {stock}")
                        st.write(f"**Status:** {'Active' if product.get('active', True) else 'Inactive'}")
                    
                    # Check if product has sales history
                    transactions = load_data(TRANSACTIONS_FILE)
                    has_sales = any(barcode in t.get('items', {}) for t in transactions.values())
                    
                    if has_sales:
                        st.error("⚠️ This product has sales history. Deleting it may affect reports.")
                        deletion_option = st.radio("Deletion Option", 
                                                  ["Deactivate only (recommended)", "Permanent deletion"],
                                                  key="delete_option")
                    else:
                        deletion_option = "Permanent deletion"
                    
                    confirmation = st.text_input("Type 'DELETE' to confirm", key="delete_confirm")
                    
                    if st.button("Confirm Delete", disabled=confirmation != "DELETE", key="confirm_delete_btn"):
                        if deletion_option == "Deactivate only (recommended)":
                            # Deactivate instead of deleting
                            products[barcode]['active'] = False
                            products[barcode]['last_updated'] = get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
                            products[barcode]['updated_by'] = st.session_state.user_info['username']
                            save_data(products, PRODUCTS_FILE)
                            st.success("Product deactivated successfully")
                        else:
                            # Permanent deletion
                            # Remove product image if exists
                            if 'image' in product and os.path.exists(product['image']):
                                try:
                                    os.remove(product['image'])
                                except:
                                    pass
                            
                            # Remove from products and inventory
                            del products[barcode]
                            if barcode in inventory:
                                del inventory[barcode]
                            
                            # Remove from brand mapping
                            brand = product.get('brand')
                            if brand:
                                brands_data = load_data(BRANDS_FILE)
                                brand_products = brands_data.get('brand_products', {})
                                if brand in brand_products and barcode in brand_products[brand]:
                                    brand_products[brand].remove(barcode)
                                brands_data['brand_products'] = brand_products
                                save_data(brands_data, BRANDS_FILE)
                            
                            save_data(products, PRODUCTS_FILE)
                            save_data(inventory, INVENTORY_FILE)
                            st.success("Product permanently deleted")

    with tab4:
        st.header("Bulk Import Products")
        
        st.info("Import multiple products at once using a CSV file")
        
        # Template management section
        st.subheader("Download Template")
        
        # Create proper template with example data
        template_data = {
            "barcode": ["AUTO_GENERATE", "1234567890123", "AUTO_GENERATE"],
            "name": ["Apple iPhone 14", "Samsung Galaxy S23", "Google Pixel 7"],
            "description": ["Latest iPhone model", "Flagship Samsung phone", "Google's premium smartphone"],
            "price": [999.99, 899.99, 699.99],
            "cost": [750.00, 650.00, 500.00],
            "category": ["Electronics", "Electronics", "Electronics"],
            "subcategory": ["Smartphones", "Smartphones", "Smartphones"],
            "brand": ["Apple", "Samsung", "Google"],
            "supplier": ["Tech Supplier Inc", "Mobile Distributors", "Gadget World"],
            "initial_stock": [50, 75, 60],
            "reorder_point": [10, 15, 12],
            "active": [True, True, True]
        }
        template_df = pd.DataFrame(template_data)
        
        st.download_button(
            label="Download Import Template",
            data=template_df.to_csv(index=False).encode('utf-8'),
            file_name="product_import_template.csv",
            mime="text/csv",
            help="Download the template with proper format and example data"
        )
        
        # Upload section
        st.subheader("Upload CSV File")
        
        uploaded_file = st.file_uploader("Choose a CSV file", type=['csv'], 
                                       help="Upload your product data CSV file")
        
        if uploaded_file:
            try:
                # Read and preview the CSV
                df = pd.read_csv(uploaded_file)
                st.success("CSV file loaded successfully")
                
                # Show preview
                st.write("**Data Preview:**")
                st.dataframe(df.head())
                
                # Validation options
                st.subheader("Import Options")
                
                col1, col2 = st.columns(2)
                with col1:
                    import_mode = st.radio("Import Mode", 
                                          ["Add new products only", "Update existing products", "Add or update"],
                                          key="import_mode")
                    on_error = st.radio("On Error", 
                                       ["Skip row and continue", "Stop import"],
                                       key="on_error")
                
                with col2:
                    generate_barcodes = st.checkbox("Generate missing barcodes", value=True,
                                                  help="Automatically generate barcodes for rows with empty or AUTO_GENERATE values",
                                                  key="generate_barcodes")
                    validate_data = st.checkbox("Validate data before import", value=True,
                                              help="Check for data issues before importing",
                                              key="validate_data")
                
                if st.button("Validate Data" if validate_data else "Import Products", key="import_btn"):
                    products = load_data(PRODUCTS_FILE)
                    inventory = load_data(INVENTORY_FILE)
                    categories_data = load_categories_data()
                    brands_data = load_data(BRANDS_FILE)
                    suppliers = load_data(SUPPLIERS_FILE)
                    
                    results = {
                        'processed': 0,
                        'added': 0,
                        'updated': 0,
                        'skipped': 0,
                        'errors': []
                    }
                    
                    # Get all existing barcodes for quick lookup
                    existing_barcodes = set(products.keys())
                    
                    for index, row in df.iterrows():
                        try:
                            # Skip empty rows
                            if pd.isna(row.get('name')) or not str(row.get('name')).strip():
                                results['skipped'] += 1
                                results['errors'].append(f"Row {index+2}: Missing product name")
                                continue
                            
                            # Handle barcode
                            barcode = str(row.get('barcode', '')).strip()
                            if not barcode or barcode == 'AUTO_GENERATE':
                                if generate_barcodes:
                                    barcode = generate_barcode()
                                else:
                                    results['skipped'] += 1
                                    results['errors'].append(f"Row {index+2}: Missing barcode and generation disabled")
                                    continue
                            
                            # Validate barcode format
                            if barcode and not barcode.isdigit():
                                results['skipped'] += 1
                                results['errors'].append(f"Row {index+2}: Invalid barcode format '{barcode}' - must be digits only")
                                continue
                            
                            if barcode and len(barcode) not in [12, 13]:
                                results['skipped'] += 1
                                results['errors'].append(f"Row {index+2}: Invalid barcode length '{barcode}' - must be 12 or 13 digits")
                                continue
                            
                            # Check if product exists
                            product_exists = barcode in existing_barcodes
                            
                            # Determine if we should process based on import mode
                            if import_mode == "Add new products only" and product_exists:
                                results['skipped'] += 1
                                continue
                            if import_mode == "Update existing products" and not product_exists:
                                results['skipped'] += 1
                                continue
                            
                            # Prepare product data with proper validation
                            product_data = {
                                'barcode': barcode,
                                'name': str(row.get('name', '')).strip(),
                                'description': str(row.get('description', '')).strip() if pd.notna(row.get('description')) else '',
                                'price': float(row.get('price', 0)) if pd.notna(row.get('price')) else 0.0,
                                'cost': float(row.get('cost', 0)) if pd.notna(row.get('cost')) else 0.0,
                                'category': str(row.get('category', '')).strip() if pd.notna(row.get('category')) else '',
                                'subcategory': str(row.get('subcategory', '')).strip() if pd.notna(row.get('subcategory')) else '',
                                'brand': str(row.get('brand', '')).strip() if pd.notna(row.get('brand')) else '',
                                'supplier': str(row.get('supplier', '')).strip() if pd.notna(row.get('supplier')) else None,
                                'active': bool(row.get('active', True)) if pd.notna(row.get('active')) else True,
                                'last_updated': get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            
                            # Validate required fields
                            if not product_data['name']:
                                results['skipped'] += 1
                                results['errors'].append(f"Row {index+2}: Product name is required")
                                continue
                            
                            if product_data['price'] <= 0:
                                results['skipped'] += 1
                                results['errors'].append(f"Row {index+2}: Price must be greater than 0")
                                continue
                            
                            if product_data['cost'] <= 0:
                                results['skipped'] += 1
                                results['errors'].append(f"Row {index+2}: Cost must be greater than 0")
                                continue
                            
                            # Set added_by/updated_by based on whether it's new or existing
                            if product_exists:
                                product_data['updated_by'] = st.session_state.user_info['username']
                                # Preserve original date added
                                product_data['date_added'] = products[barcode].get('date_added')
                            else:
                                product_data['date_added'] = get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
                                product_data['added_by'] = st.session_state.user_info['username']
                            
                            # Validate category and subcategory
                            category = product_data['category']
                            if category and category not in categories_data.get('categories', []):
                                # Add new category if it doesn't exist
                                if category not in categories_data.get('categories', []):
                                    categories_data['categories'].append(category)
                                    categories_data['subcategories'][category] = []
                            
                            # Validate brand
                            brand = product_data['brand']
                            if brand and brand not in brands_data.get('brands', []):
                                # Add new brand if it doesn't exist
                                brands_data['brands'].append(brand)
                            
                            # Save product
                            products[barcode] = product_data
                            
                            # Handle inventory
                            initial_stock = int(row.get('initial_stock', 0)) if pd.notna(row.get('initial_stock')) else 0
                            reorder_point = int(row.get('reorder_point', 10)) if pd.notna(row.get('reorder_point')) else 10
                            
                            if barcode in inventory:
                                inventory[barcode]['reorder_point'] = reorder_point
                                inventory[barcode]['last_updated'] = get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
                                inventory[barcode]['updated_by'] = st.session_state.user_info['username']
                            else:
                                inventory[barcode] = {
                                    'quantity': initial_stock,
                                    'reorder_point': reorder_point,
                                    'last_updated': get_current_datetime().strftime("%Y-%m-%d %H:%M:%S"),
                                    'updated_by': st.session_state.user_info['username']
                                }
                            
                            # Update brand mapping
                            if brand:
                                brand_products = brands_data.get('brand_products', {})
                                if brand not in brand_products:
                                    brand_products[brand] = []
                                if barcode not in brand_products[brand]:
                                    brand_products[brand].append(barcode)
                                brands_data['brand_products'] = brand_products
                            
                            results['processed'] += 1
                            if product_exists:
                                results['updated'] += 1
                            else:
                                results['added'] += 1
                            
                        except Exception as e:
                            results['skipped'] += 1
                            results['errors'].append(f"Row {index+2}: Error - {str(e)}")
                            if on_error == "Stop import":
                                break
                    
                    # Save all data
                    save_data(products, PRODUCTS_FILE)
                    save_data(inventory, INVENTORY_FILE)
                    save_data(categories_data, CATEGORIES_FILE)
                    save_data(brands_data, BRANDS_FILE)
                    
                    # Show results
                    st.success(f"Import completed: {results['processed']} processed, "
                             f"{results['added']} added, {results['updated']} updated, "
                             f"{results['skipped']} skipped")
                    
                    if results['errors']:
                        st.warning(f"Encountered {len(results['errors'])} errors:")
                        for error in results['errors']:
                            st.write(f"- {error}")
                
            except Exception as e:
                st.error(f"Error reading CSV file: {str(e)}")

    with tab5:
        st.header("Template Management")
        
        st.info("Manage and create custom import templates")
        
        # Template gallery
        st.subheader("Available Templates")
        
        # Predefined templates
        templates = {
            "Basic Products": ["barcode", "name", "price", "cost", "category"],
            "Full Products": ["barcode", "name", "description", "price", "cost", "category", "subcategory", "brand", "initial_stock", "reorder_point", "active"],
            "Products with Suppliers": ["barcode", "name", "price", "cost", "category", "supplier", "initial_stock"],
            "Inventory Update": ["barcode", "initial_stock", "reorder_point"]
        }
        
        selected_template = st.selectbox("Select Template Type", list(templates.keys()), key="template_select")
        
        if selected_template:
            st.write("**Template Fields:**")
            for field in templates[selected_template]:
                st.write(f"- {field}")
            
            # Customize template
            st.subheader("Customize Template")
            
            # Add/remove fields
            all_fields = ["barcode", "name", "description", "price", "cost", "category", 
                         "subcategory", "brand", "supplier", "initial_stock", 
                         "reorder_point", "active"]
            
            selected_fields = st.multiselect("Select Fields for Custom Template", 
                                           all_fields, 
                                           default=templates[selected_template],
                                           key="custom_fields")
            
            # Generate sample data
            if selected_fields:
                sample_data = {}
                for field in selected_fields:
                    if field == "barcode":
                        sample_data[field] = ["AUTO_GENERATE", "1234567890123"]
                    elif field == "name":
                        sample_data[field] = ["Product 1", "Product 2"]
                    elif field in ["price", "cost"]:
                        sample_data[field] = [10.99, 5.50]
                    elif field == "category":
                        sample_data[field] = ["Groceries", "Electronics"]
                    elif field == "subcategory":
                        sample_data[field] = ["Snacks", "Accessories"]
                    elif field == "brand":
                        sample_data[field] = ["Brand A", "Brand B"]
                    elif field == "supplier":
                        sample_data[field] = ["Supplier X", "Supplier Y"]
                    elif field in ["initial_stock", "reorder_point"]:
                        sample_data[field] = [100, 50]
                    elif field == "active":
                        sample_data[field] = [True, True]
                    elif field == "description":
                        sample_data[field] = ["Product description", "Another description"]
                
                template_df = pd.DataFrame(sample_data)
                
                # Download custom template
                template_name = st.text_input("Template Name", value=f"Custom_{selected_template}", key="template_name")
                
                st.download_button(
                    label="Download Custom Template",
                    data=template_df.to_csv(index=False).encode('utf-8'),
                    file_name=f"{template_name}_template.csv",
                    mime="text/csv",
                    key="download_custom"
                )
        
        # Template history
        st.subheader("Template History")
        st.info("Template history feature would be implemented here to track previously used templates")

    with tab6:
        st.header("Category Management")
        
        categories_data = load_categories_data()
        categories = categories_data.get('categories', [])
        subcategories = categories_data.get('subcategories', {})
        
        st.subheader("Current Categories")
        if not categories:
            st.info("No categories defined yet")
        else:
            # Display categories with their subcategories
            for category in categories:
                with st.expander(f"Category: {category}"):
                    cat_subcategories = subcategories.get(category, [])
                    if cat_subcategories:
                        st.write("**Subcategories:**")
                        for subcat in cat_subcategories:
                            col1, col2 = st.columns([4, 1])
                            with col1:
                                st.write(f"- {subcat}")
                            with col2:
                                if st.button("Remove", key=f"remove_sub_{category}_{subcat}"):
                                    categories_data['subcategories'][category].remove(subcat)
                                    save_data(categories_data, CATEGORIES_FILE)
                                    st.success(f"Removed subcategory '{subcat}' from '{category}'")
                                    st.rerun()
                    else:
                        st.info("No subcategories for this category")
                    
                    # Add new subcategory to this category
                    new_subcat = st.text_input("Add new subcategory", key=f"new_sub_{category}")
                    if st.button("Add Subcategory", key=f"add_sub_{category}"):
                        if new_subcat:
                            add_subcategory(category, new_subcat)
                            st.success(f"Added subcategory '{new_subcat}' to '{category}'")
                            st.rerun()
            
            # Category management
            st.subheader("Manage Categories")
            col1, col2 = st.columns(2)
            
            with col1:
                # Add new category
                new_category = st.text_input("New Category Name", key="new_cat_name")
                if st.button("Add Category", key="add_cat_btn"):
                    if new_category and new_category not in categories:
                        categories_data['categories'].append(new_category)
                        categories_data['subcategories'][new_category] = []
                        save_data(categories_data, CATEGORIES_FILE)
                        st.success(f"Category '{new_category}' added")
                        st.rerun()
                    elif new_category in categories:
                        st.error("Category already exists")
            
            with col2:
                # Remove category
                if categories:
                    category_to_remove = st.selectbox("Select Category to Remove", [""] + categories, key="remove_cat_select")
                    if category_to_remove and st.button("Remove Category", key="remove_cat_btn"):
                        # Check if category has products
                        products = load_data(PRODUCTS_FILE)
                        has_products = any(p.get('category') == category_to_remove for p in products.values())
                        
                        if has_products:
                            st.error(f"Cannot remove category '{category_to_remove}' because it has products assigned")
                        else:
                            categories_data['categories'].remove(category_to_remove)
                            if category_to_remove in categories_data['subcategories']:
                                del categories_data['subcategories'][category_to_remove]
                            save_data(categories_data, CATEGORIES_FILE)
                            st.success(f"Category '{category_to_remove}' removed")
                            st.rerun()
        
        # Bulk category import
        st.subheader("Bulk Category Import")
        
        # Template for category import
        category_template_data = {
            "category": ["Groceries", "Electronics", "Clothing"],
            "subcategories": ["Dairy|Fruits|Vegetables", "Phones|Laptops|Accessories", "Men|Women|Kids"]
        }
        category_template_df = pd.DataFrame(category_template_data)
        
        st.download_button(
            label="Download Category Template",
            data=category_template_df.to_csv(index=False).encode('utf-8'),
            file_name="category_import_template.csv",
            mime="text/csv",
            key="download_cat_template"
        )
        
        uploaded_category_file = st.file_uploader("Upload Category CSV", type=['csv'], key="cat_upload")
        
        if uploaded_category_file:
            try:
                cat_df = pd.read_csv(uploaded_category_file)
                st.dataframe(cat_df)
                
                if st.button("Import Categories", key="import_cat_btn"):
                    for _, row in cat_df.iterrows():
                        category = str(row['category']).strip()
                        subcats = str(row['subcategories']).split('|') if pd.notna(row['subcategories']) else []
                        
                        if category and category not in categories_data['categories']:
                            categories_data['categories'].append(category)
                        
                        if category and subcats:
                            if category not in categories_data['subcategories']:
                                categories_data['subcategories'][category] = []
                            
                            for subcat in subcats:
                                subcat = subcat.strip()
                                if subcat and subcat not in categories_data['subcategories'][category]:
                                    categories_data['subcategories'][category].append(subcat)
                    
                    save_data(categories_data, CATEGORIES_FILE)
                    st.success("Categories imported successfully")
                    st.rerun()
                    
            except Exception as e:
                st.error(f"Error reading category file: {str(e)}")
                
                
# Inventory Management
def inventory_management():
    if not is_manager():
        st.warning("You don't have permission to access this page")
        return
    
    st.title("Inventory Management")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "Current Inventory", 
        "Stock Adjustment", 
        "Inventory Reports", 
        "Bulk Update"
    ])
    
    with tab1:
        st.header("Current Inventory")
        
        inventory = load_data(INVENTORY_FILE)
        products = load_data(PRODUCTS_FILE)
        
        if not inventory:
            st.info("No inventory items available")
        else:
            # Merge product info with inventory
            inventory_list = []
            for barcode, inv_data in inventory.items():
                product = products.get(barcode, {'name': 'Unknown Product', 'price': 0})
                inventory_list.append({
                    'product': product['name'],
                    'barcode': barcode,
                    'quantity': inv_data.get('quantity', 0),
                    'reorder_point': inv_data.get('reorder_point', 10),
                    'status': 'Low Stock' if inv_data.get('quantity', 0) < inv_data.get('reorder_point', 10) else 'OK',
                    'last_updated': inv_data.get('last_updated', 'N/A')
                })
            
            inventory_df = pd.DataFrame(inventory_list)
            
            # Filter options
            col1, col2 = st.columns(2)
            with col1:
                show_low_stock = st.checkbox("Show Only Low Stock Items", key="inv_low_stock_filter")
            with col2:
                sort_by = st.selectbox(
                    "Sort By", 
                    ["Product Name", "Quantity", "Status"],
                    key="inv_sort_by"
                )
            
            if show_low_stock:
                inventory_df = inventory_df[inventory_df['status'] == 'Low Stock']
            
            if sort_by == "Product Name":
                inventory_df = inventory_df.sort_values('product')
            elif sort_by == "Quantity":
                inventory_df = inventory_df.sort_values('quantity')
            else:
                inventory_df = inventory_df.sort_values('status')
            
            st.dataframe(inventory_df)
            
            # Export option
            if st.button("Export Inventory to CSV", key="export_inv_csv"):
                csv = inventory_df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"inventory_report_{datetime.date.today()}.csv",
                    mime="text/csv",
                    key="inv_download_csv"
                )
    
    with tab2:
        st.header("Stock Adjustment")
        
        products = load_data(PRODUCTS_FILE)
        if not products:
            st.info("No products available")
        else:
            product_options = {f"{v['name']} ({k})": k for k, v in products.items()}
            selected_product = st.selectbox(
                "Select Product", 
                [""] + list(product_options.keys()),
                key="stock_adj_select_product"
            )
            
            if selected_product:
                barcode = product_options[selected_product]
                inventory = load_data(INVENTORY_FILE)
                current_qty = inventory.get(barcode, {}).get('quantity', 0)
                current_reorder = inventory.get(barcode, {}).get('reorder_point', 10)
                
                st.write(f"Current Stock: {current_qty}")
                st.write(f"Current Reorder Point: {current_reorder}")
                
                with st.form(key=f"adjust_{barcode}"):
                    adjustment_type = st.radio(
                        "Adjustment Type", 
                        ["Add Stock", "Remove Stock", "Set Stock", "Transfer Stock"],
                        key=f"adj_type_{barcode}"
                    )
                    
                    if adjustment_type in ["Add Stock", "Remove Stock", "Set Stock"]:
                        quantity = st.number_input(
                            "Quantity", 
                            min_value=1, 
                            value=1, 
                            step=1,
                            key=f"adj_qty_{barcode}"
                        )
                    else:
                        quantity = st.number_input(
                            "Quantity to Transfer", 
                            min_value=1, 
                            value=1, 
                            step=1,
                            key=f"transfer_qty_{barcode}"
                        )
                        transfer_to = st.text_input(
                            "Transfer To (Location/Branch)",
                            key=f"transfer_to_{barcode}"
                        )
                    
                    new_reorder = st.number_input(
                        "Reorder Point", 
                        min_value=0, 
                        value=current_reorder, 
                        step=1,
                        key=f"reorder_{barcode}"
                    )
                    notes = st.text_area(
                        "Notes",
                        key=f"notes_{barcode}"
                    )
                    
                    if st.form_submit_button("Submit Adjustment"):
                        if barcode not in inventory:
                            inventory[barcode] = {'quantity': 0, 'reorder_point': new_reorder}
                        
                        if adjustment_type == "Add Stock":
                            inventory[barcode]['quantity'] += quantity
                        elif adjustment_type == "Remove Stock":
                            inventory[barcode]['quantity'] -= quantity
                        elif adjustment_type == "Set Stock":
                            inventory[barcode]['quantity'] = quantity
                        elif adjustment_type == "Transfer Stock":
                            inventory[barcode]['quantity'] -= quantity
                        
                        inventory[barcode]['reorder_point'] = new_reorder
                        inventory[barcode]['last_updated'] = get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
                        inventory[barcode]['updated_by'] = st.session_state.user_info['username']
                        
                        adjustments = inventory[barcode].get('adjustments', [])
                        adjustments.append({
                            'date': get_current_datetime().strftime("%Y-%m-%d %H:%M:%S"),
                            'type': adjustment_type,
                            'quantity': quantity,
                            'previous_qty': current_qty,
                            'new_qty': inventory[barcode]['quantity'],
                            'notes': notes,
                            'user': st.session_state.user_info['username']
                        })
                        inventory[barcode]['adjustments'] = adjustments
                        
                        save_data(inventory, INVENTORY_FILE)
                        st.success("Inventory updated successfully")
    
    with tab3:
        st.header("Inventory Reports")
        
        inventory = load_data(INVENTORY_FILE)
        products = load_data(PRODUCTS_FILE)
        
        if not inventory:
            st.info("No inventory data available")
        else:
            report_type = st.selectbox(
                "Inventory Report Type", 
                [
                    "Stock Levels",
                    "Stock Value",
                    "Stock Movement",
                    "Inventory Audit"
                ],
                key="inv_report_type"
            )
            
            if report_type == "Stock Levels":
                inventory_list = []
                for barcode, inv_data in inventory.items():
                    product = products.get(barcode, {'name': 'Unknown'})
                    inventory_list.append({
                        'product': product['name'],
                        'barcode': barcode,
                        'quantity': inv_data.get('quantity', 0),
                        'reorder_point': inv_data.get('reorder_point', 10)
                    })
                
                inv_df = pd.DataFrame(inventory_list)
                st.dataframe(inv_df)
            
            elif report_type == "Stock Value":
                value_list = []
                for barcode, inv_data in inventory.items():
                    product = products.get(barcode, {'name': 'Unknown', 'cost': 0})
                    value_list.append({
                        'product': product['name'],
                        'barcode': barcode,
                        'quantity': inv_data.get('quantity', 0),
                        'unit_cost': product.get('cost', 0),
                        'total_value': inv_data.get('quantity', 0) * product.get('cost', 0)
                    })
                
                value_df = pd.DataFrame(value_list)
                total_value = value_df['total_value'].sum()
                
                st.write(f"Total Inventory Value: {format_currency(total_value)}")
                st.dataframe(value_df.sort_values('total_value', ascending=False))
            
            elif report_type == "Stock Movement":
                st.info("Select a product to view movement history")
                
                product_options = {f"{v['name']} ({k})": k for k, v in products.items()}
                selected_product = st.selectbox(
                    "Select Product", 
                    [""] + list(product_options.keys()),
                    key="movement_select_product"
                )
                
                if selected_product:
                    barcode = product_options[selected_product]
                    inventory = load_data(INVENTORY_FILE)
                    
                    if barcode in inventory and 'adjustments' in inventory[barcode]:
                        adjustments = inventory[barcode]['adjustments']
                        st.dataframe(pd.DataFrame(adjustments))
                    else:
                        st.info("No adjustment history for this product")
            
            elif report_type == "Inventory Audit":
                st.info("Inventory audit would compare physical counts with system records")
                if st.button("Generate Audit Sheet", key="gen_audit_sheet"):
                    audit_data = []
                    for barcode, inv_data in inventory.items():
                        product = products.get(barcode, {'name': 'Unknown'})
                        audit_data.append({
                            'Product': product['name'],
                            'Barcode': barcode,
                            'System Quantity': inv_data.get('quantity', 0),
                            'Physical Count': "",
                            'Variance': "",
                            'Notes': ""
                        })
                    
                    audit_df = pd.DataFrame(audit_data)
                    st.dataframe(audit_df)
                    
                    csv = audit_df.to_csv(index=False)
                    st.download_button(
                        label="Download Audit Sheet",
                        data=csv,
                        file_name=f"inventory_audit_{datetime.date.today()}.csv",
                        mime="text/csv",
                        key="download_audit"
                    )
    
    with tab4:
        st.header("Bulk Inventory Update")
        
        st.info("Download the template file to prepare your inventory data")
        
        # Generate template file
        template_data = {
            "barcode": ["123456789012", ""],
            "quantity": [10, ""],
            "reorder_point": [5, ""]
        }
        template_df = pd.DataFrame(template_data)
        
        st.download_button(
            label="Download Template",
            data=template_df.to_csv(index=False).encode('utf-8'),
            file_name="inventory_update_template.csv",
            mime="text/csv",
            key="dl_inv_template"
        )
        
        uploaded_file = st.file_uploader(
            "Upload CSV file", 
            type=['csv'],
            key="inv_upload_csv"
        )
        
        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file)
                st.dataframe(df)
                
                if st.button("Update Inventory", key="inv_update_btn"):
                    inventory = load_data(INVENTORY_FILE)
                    products = load_data(PRODUCTS_FILE)
                    updated = 0
                    errors = 0
                    
                    for _, row in df.iterrows():
                        try:
                            barcode = str(row['barcode']).strip()
                            
                            if barcode not in products:
                                errors += 1
                                continue
                            
                            if barcode not in inventory:
                                inventory[barcode] = {
                                    'quantity': 0,
                                    'reorder_point': 10
                                }
                            
                            if not pd.isna(row['quantity']):
                                inventory[barcode]['quantity'] = int(row['quantity'])
                            
                            if not pd.isna(row['reorder_point']):
                                inventory[barcode]['reorder_point'] = int(row['reorder_point'])
                            
                            inventory[barcode]['last_updated'] = get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
                            inventory[barcode]['updated_by'] = st.session_state.user_info['username']
                            
                            updated += 1
                        
                        except Exception as e:
                            errors += 1
                            continue
                    
                    save_data(inventory, INVENTORY_FILE)
                    st.success(f"Update completed: {updated} items updated, {errors} errors")
            except Exception as e:
                st.error(f"Error reading CSV file: {str(e)}")

# User Management
def user_management():
    if not is_admin():
        st.warning("You don't have permission to access this page")
        return
    
    st.title("User Management")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Add User", "View/Edit Users", "Delete User", "Bulk Import"])
    
    with tab1:
        st.header("Add New User")
        
        with st.form("add_user_form"):
            username = st.text_input("Username*")
            password = st.text_input("Password*", type="password")
            confirm_password = st.text_input("Confirm Password*", type="password")
            full_name = st.text_input("Full Name*")
            email = st.text_input("Email")
            role = st.selectbox("Role*", ["admin", "manager", "cashier"])
            active = st.checkbox("Active", value=True)
            
            submit_button = st.form_submit_button("Add User")
            
            if submit_button:
                if not username or not password or not full_name:
                    st.error("Fields marked with * are required")
                elif password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    users = load_data(USERS_FILE)
                    
                    if username in users:
                        st.error("Username already exists")
                    else:
                        users[username] = {
                            'username': username,
                            'password': hash_password(password),
                            'role': role,
                            'full_name': full_name,
                            'email': email,
                            'active': active,
                            'date_created': get_current_datetime().strftime("%Y-%m-%d %H:%M:%S"),
                            'created_by': st.session_state.user_info['username']
                        }
                        
                        save_data(users, USERS_FILE)
                        st.success(f"User '{username}' added successfully")
    
    with tab2:
        st.header("View/Edit Users")
        
        users = load_data(USERS_FILE)
        if not users:
            st.info("No users available")
        else:
            search_term = st.text_input("Search Users")
            
            if search_term:
                filtered_users = {k: v for k, v in users.items() 
                                 if search_term.lower() in k.lower() or 
                                 search_term.lower() in v['full_name'].lower()}
            else:
                filtered_users = users
            
            for username, user in filtered_users.items():
                if username == "admin" and st.session_state.user_info['username'] != "admin":
                    continue  # Only admin can edit admin account
                
                with st.expander(f"{user['full_name']} ({username}) - {user['role']}"):
                    with st.form(key=f"edit_{username}"):
                        full_name = st.text_input("Full Name", value=user.get('full_name', ''))
                        email = st.text_input("Email", value=user.get('email', ''))
                        
                        if username == "admin":
                            role = "admin"
                            st.text("Role: admin (cannot be changed)")
                        else:
                            role = st.selectbox("Role", ["admin", "manager", "cashier"], 
                                               index=["admin", "manager", "cashier"].index(user['role']))
                        
                        active = st.checkbox("Active", value=user.get('active', True))
                        
                        password = st.text_input("New Password (leave blank to keep current)", type="password")
                        confirm_password = st.text_input("Confirm New Password", type="password")
                        
                        if st.form_submit_button("Update User"):
                            users[username]['full_name'] = full_name
                            users[username]['email'] = email
                            users[username]['role'] = role
                            users[username]['active'] = active
                            users[username]['last_updated'] = get_current_datetime().strftime("%Y-%m-%d %H:%M:%S"),
                            users[username]['updated_by'] = st.session_state.user_info['username']
                            
                            if password:
                                if password == confirm_password:
                                    users[username]['password'] = hash_password(password)
                                else:
                                    st.error("Passwords do not match")
                                    continue
                            
                            save_data(users, USERS_FILE)
                            st.success("User updated successfully")
    
    with tab3:
        st.header("Delete User")
        
        users = load_data(USERS_FILE)
        if not users:
            st.info("No users available to delete")
        else:
            current_user = st.session_state.user_info['username']
            user_options = {f"{v['full_name']} ({k})": k for k, v in users.items() 
                          if k != current_user and k != "admin"}  # Can't delete self or admin
            
            if not user_options:
                st.info("No users available to delete (cannot delete yourself or admin)")
            else:
                selected_user = st.selectbox("Select User to Delete", [""] + list(user_options.keys()))
                
                if selected_user:
                    username = user_options[selected_user]
                    user = users[username]
                    
                    st.warning(f"You are about to delete: {user['full_name']} ({username})")
                    st.write(f"Role: {user['role']}")
                    st.write(f"Status: {'Active' if user['active'] else 'Inactive'}")
                    
                    if st.button("Confirm Delete"):
                        del users[username]
                        save_data(users, USERS_FILE)
                        st.success("User deleted successfully")
    
    with tab4:
        st.header("Bulk Import Users")
        
        st.info("Download the template file to prepare your user data")
        
        # Generate template file
        template_data = {
            "username": ["user1", ""],
            "password": ["password123", ""],
            "full_name": ["User One", ""],
            "email": ["user1@example.com", ""],
            "role": ["cashier", ""],
            "active": [True, ""]
        }
        template_df = pd.DataFrame(template_data)
        
        st.download_button(
            label="Download Template",
            data=template_df.to_csv(index=False).encode('utf-8'),
            file_name="user_import_template.csv",
            mime="text/csv"
        )
        
        uploaded_file = st.file_uploader("Upload CSV file", type=['csv'])
        
        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file)
                st.dataframe(df)
                
                if st.button("Import Users"):
                    users = load_data(USERS_FILE)
                    imported = 0
                    updated = 0
                    errors = 0
                    
                    for _, row in df.iterrows():
                        try:
                            username = str(row['username']).strip()
                            if not username:
                                errors += 1
                                continue
                            
                            password = str(row['password']).strip()
                            if not password:
                                errors += 1
                                continue
                            
                            full_name = str(row['full_name']).strip()
                            if not full_name:
                                errors += 1
                                continue
                            
                            user_data = {
                                'username': username,
                                'password': hash_password(password),
                                'full_name': full_name,
                                'email': str(row['email']).strip() if not pd.isna(row['email']) else "",
                                'role': str(row['role']).strip().lower() if not pd.isna(row['role']) else "cashier",
                                'active': bool(row['active']) if not pd.isna(row['active']) else True,
                                'date_created': get_current_datetime().strftime("%Y-%m-%d %H:%M:%S"),
                                'created_by': st.session_state.user_info['username']
                            }
                            
                            if username in users:
                                users[username].update(user_data)
                                updated += 1
                            else:
                                users[username] = user_data
                                imported += 1
                        
                        except Exception as e:
                            errors += 1
                            continue
                    
                    save_data(users, USERS_FILE)
                    st.success(f"Import completed: {imported} new users, {updated} updated, {errors} errors")
            except Exception as e:
                st.error(f"Error reading CSV file: {str(e)}")

# Discounts & Promotions
def discounts_management():
    if not is_manager():
        st.warning("You don't have permission to access this page")
        return
    
    st.title("Discounts & Promotions")
    
    tab1, tab2, tab3 = st.tabs(["Add Discount", "View/Edit Discounts", "Bulk Import"])
    
    with tab1:
        st.header("Add New Discount")
        
        with st.form("add_discount_form"):
            name = st.text_input("Discount Name*")
            description = st.text_area("Description")
            
            col1, col2 = st.columns(2)
            with col1:
                discount_type = st.selectbox("Discount Type*", ["Percentage", "Fixed Amount"])
            with col2:
                if discount_type == "Percentage":
                    value = st.number_input("Value*", min_value=1, max_value=100, value=10, step=1)
                else:
                    value = st.number_input("Value*", min_value=0.01, value=1.0, step=1.0)
            
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date*", value=datetime.date.today())
            with col2:
                end_date = st.date_input("End Date*", value=datetime.date.today() + datetime.timedelta(days=7))
            
            apply_to = st.selectbox("Apply To*", ["All Products", "Specific Categories", "Specific Products"])
            
            if apply_to == "Specific Categories":
                categories = load_data(CATEGORIES_FILE).get('categories', [])
                selected_categories = st.multiselect("Select Categories*", categories)
            elif apply_to == "Specific Products":
                products = load_data(PRODUCTS_FILE)
                product_options = {f"{v['name']} ({k})": k for k, v in products.items()}
                selected_products = st.multiselect("Select Products*", list(product_options.keys()))
            
            active = st.checkbox("Active", value=True)
            
            submit_button = st.form_submit_button("Add Discount")
            
            if submit_button:
                if not name:
                    st.error("Discount name is required")
                elif apply_to == "Specific Categories" and not selected_categories:
                    st.error("Please select at least one category")
                elif apply_to == "Specific Products" and not selected_products:
                    st.error("Please select at least one product")
                else:
                    discounts = load_data(DISCOUNTS_FILE)
                    discount_id = str(uuid.uuid4())
                    
                    discount_data = {
                        'id': discount_id,
                        'name': name,
                        'description': description,
                        'type': 'percentage' if discount_type == "Percentage" else 'fixed',
                        'value': value,
                        'start_date': start_date.strftime("%Y-%m-%d"),
                        'end_date': end_date.strftime("%Y-%m-%d"),
                        'apply_to': apply_to,
                        'active': active,
                        'created_by': st.session_state.user_info['username'],
                        'created_at': get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    if apply_to == "Specific Categories":
                        discount_data['categories'] = selected_categories
                    elif apply_to == "Specific Products":
                        discount_data['products'] = [product_options[p] for p in selected_products]
                    
                    discounts[discount_id] = discount_data
                    save_data(discounts, DISCOUNTS_FILE)
                    st.success("Discount added successfully")
    
    with tab2:
        st.header("View/Edit Discounts")
        
        discounts = load_data(DISCOUNTS_FILE)
        if not discounts:
            st.info("No discounts available")
        else:
            for discount_id, discount in discounts.items():
                with st.expander(f"{discount['name']} - {'Active' if discount['active'] else 'Inactive'}"):
                    with st.form(key=f"edit_{discount_id}"):
                        name = st.text_input("Name", value=discount.get('name', ''))
                        description = st.text_area("Description", value=discount.get('description', ''))
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            discount_type = st.selectbox("Type", 
                                                       ["Percentage", "Fixed Amount"], 
                                                       index=0 if discount.get('type') == 'percentage' else 1)
                        with col2:
                            if discount_type == "Percentage":
                                value = st.number_input("Value", 
                                                      min_value=1, 
                                                      max_value=100, 
                                                      value=int(discount.get('value', 10)),
                                                      step=1)
                            else:
                                value = st.number_input("Value", 
                                                      min_value=0.01, 
                                                      value=float(discount.get('value', 1.0)), 
                                                      step=1.0)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            start_date = st.date_input("Start Date", 
                                                     value=datetime.datetime.strptime(discount.get('start_date'), "%Y-%m-%d").date())
                        with col2:
                            end_date = st.date_input("End Date", 
                                                   value=datetime.datetime.strptime(discount.get('end_date'), "%Y-%m-%d").date())
                        
                        apply_to = st.selectbox("Apply To", 
                                              ["All Products", "Specific Categories", "Specific Products"], 
                                              index=["All Products", "Specific Categories", "Specific Products"].index(discount.get('apply_to')))
                        
                        if apply_to == "Specific Categories":
                            categories = load_data(CATEGORIES_FILE).get('categories', [])
                            selected_categories = st.multiselect("Categories", 
                                                              categories, 
                                                              default=discount.get('categories', []))
                        elif apply_to == "Specific Products":
                            products = load_data(PRODUCTS_FILE)
                            product_options = {f"{v['name']} ({k})": k for k, v in products.items()}
                            selected_products = st.multiselect("Products", 
                                                             list(product_options.keys()), 
                                                             default=[f"{products[p]['name']} ({p})" for p in discount.get('products', [])])
                        
                        active = st.checkbox("Active", value=discount.get('active', True))
                        
                        if st.form_submit_button("Update Discount"):
                            discounts[discount_id]['name'] = name
                            discounts[discount_id]['description'] = description
                            discounts[discount_id]['type'] = 'percentage' if discount_type == "Percentage" else 'fixed'
                            discounts[discount_id]['value'] = value
                            discounts[discount_id]['start_date'] = start_date.strftime("%Y-%m-%d")
                            discounts[discount_id]['end_date'] = end_date.strftime("%Y-%m-%d")
                            discounts[discount_id]['apply_to'] = apply_to
                            discounts[discount_id]['active'] = active
                            discounts[discount_id]['updated_by'] = st.session_state.user_info['username']
                            discounts[discount_id]['updated_at'] = get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
                            
                            if apply_to == "Specific Categories":
                                discounts[discount_id]['categories'] = selected_categories
                                discounts[discount_id].pop('products', None)
                            elif apply_to == "Specific Products":
                                discounts[discount_id]['products'] = [product_options[p] for p in selected_products]
                                discounts[discount_id].pop('categories', None)
                            else:
                                discounts[discount_id].pop('categories', None)
                                discounts[discount_id].pop('products', None)
                            
                            save_data(discounts, DISCOUNTS_FILE)
                            st.success("Discount updated successfully")
    
    with tab3:
        st.header("Bulk Import Discounts")
        
        st.info("Download the template file to prepare your discount data")
        
        # Generate template file
        template_data = {
            "name": ["Summer Sale", ""],
            "description": ["Summer discount on all items", ""],
            "type": ["percentage", ""],
            "value": [10, ""],
            "start_date": ["2023-06-01", ""],
            "end_date": ["2023-08-31", ""],
            "apply_to": ["All Products", ""],
            "categories": ["Groceries,Dairy", ""],
            "products": ["123456789012,987654321098", ""],
            "active": [True, ""]
        }
        template_df = pd.DataFrame(template_data)
        
        st.download_button(
            label="Download Template",
            data=template_df.to_csv(index=False).encode('utf-8'),
            file_name="discount_import_template.csv",
            mime="text/csv"
        )
        
        uploaded_file = st.file_uploader("Upload CSV file", type=['csv'])
        
        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file)
                st.dataframe(df)
                
                if st.button("Import Discounts"):
                    discounts = load_data(DISCOUNTS_FILE)
                    products = load_data(PRODUCTS_FILE)
                    categories = load_data(CATEGORIES_FILE).get('categories', [])
                    imported = 0
                    updated = 0
                    errors = 0
                    
                    for _, row in df.iterrows():
                        try:
                            if pd.isna(row['name']) or str(row['name']).strip() == "":
                                errors += 1
                                continue
                            
                            discount_id = str(uuid.uuid4())
                            
                            discount_data = {
                                'id': discount_id,
                                'name': str(row['name']).strip(),
                                'description': str(row['description']).strip() if not pd.isna(row['description']) else "",
                                'type': str(row['type']).strip().lower() if not pd.isna(row['type']) else "percentage",
                                'value': float(row['value']) if not pd.isna(row['value']) else 0.0,
                                'start_date': str(row['start_date']).strip() if not pd.isna(row['start_date']) else datetime.date.today().strftime("%Y-%m-%d"),
                                'end_date': str(row['end_date']).strip() if not pd.isna(row['end_date']) else (datetime.date.today() + datetime.timedelta(days=7)).strftime("%Y-%m-%d"),
                                'apply_to': str(row['apply_to']).strip() if not pd.isna(row['apply_to']) else "All Products",
                                'active': bool(row['active']) if not pd.isna(row['active']) else True,
                                'created_by': st.session_state.user_info['username'],
                                'created_at': get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            
                            if discount_data['apply_to'] == "Specific Categories":
                                if pd.isna(row['categories']):
                                    errors += 1
                                    continue
                                cat_list = [c.strip() for c in str(row['categories']).split(',')]
                                valid_cats = [c for c in cat_list if c in categories]
                                if not valid_cats:
                                    errors += 1
                                    continue
                                discount_data['categories'] = valid_cats
                            
                            elif discount_data['apply_to'] == "Specific Products":
                                if pd.isna(row['products']):
                                    errors += 1
                                    continue
                                prod_list = [p.strip() for p in str(row['products']).split(',')]
                                valid_prods = [p for p in prod_list if p in products]
                                if not valid_prods:
                                    errors += 1
                                    continue
                                discount_data['products'] = valid_prods
                            
                            discounts[discount_id] = discount_data
                            imported += 1
                        
                        except Exception as e:
                            errors += 1
                            continue
                    
                    save_data(discounts, DISCOUNTS_FILE)
                    st.success(f"Import completed: {imported} new discounts, {errors} errors")
            except Exception as e:
                st.error(f"Error reading CSV file: {str(e)}")


# Offers Management
# Offers Management - Improved with proper BOGO functionality and error handling
def offers_management():
    if not is_manager():
        st.warning("You don't have permission to access this page")
        return
    
    st.title("🎁 Offers Management")
    
    tab1, tab2, tab3 = st.tabs(["➕ Add Offer", "👀 View/Edit Offers", "📤 Bulk Import"])
    
    with tab1:
        st.header("Add New Offer")
        
        with st.form("add_offer_form", clear_on_submit=True):
            name = st.text_input("Offer Name*", help="Give your offer a descriptive name")
            description = st.text_area("Description", help="Describe the offer for customers and staff")
            
            offer_type = st.selectbox("Offer Type*", 
                                    ["BOGO", "Bundle", "Special Price", "Percentage Discount", "Fixed Discount"],
                                    help="Select the type of offer to create")
            
            # BOGO Offer Configuration
            if offer_type == "BOGO":
                col1, col2 = st.columns(2)
                with col1:
                    buy_quantity = st.number_input("Buy Quantity*", min_value=1, value=1, step=1,
                                                 help="Number of items customer needs to buy")
                with col2:
                    get_quantity = st.number_input("Get Quantity Free*", min_value=1, value=1, step=1,
                                                  help="Number of items customer gets free")
                
                products = load_data(PRODUCTS_FILE)
                if not products:
                    st.warning("No products available. Please add products first.")
                else:
                    product_options = {f"{v['name']} ({k})": k for k, v in products.items()}
                    selected_products = st.multiselect("Select Products*", list(product_options.keys()),
                                                     help="Products this BOGO offer applies to")
            
            # Bundle Offer Configuration
            elif offer_type == "Bundle":
                products = load_data(PRODUCTS_FILE)
                if not products:
                    st.warning("No products available. Please add products first.")
                else:
                    product_options = {f"{v['name']} ({k})": k for k, v in products.items()}
                    selected_products = st.multiselect("Select Bundle Products*", list(product_options.keys()), 
                                                     max_selections=5, help="Products included in this bundle")
                    
                    if selected_products:
                        # Calculate original total price
                        original_total = sum(products[product_options[p]].get('price', 0) for p in selected_products)
                        st.info(f"Original total price: {format_currency(original_total)}")
                        
                        bundle_price = st.number_input("Bundle Price*", min_value=0.01, value=original_total * 0.8, 
                                                     step=0.01, help="Special price for the bundle")
                        
                        discount_amount = original_total - bundle_price
                        discount_percent = (discount_amount / original_total) * 100 if original_total > 0 else 0
                        st.success(f"Discount: {format_currency(discount_amount)} ({discount_percent:.1f}% off)")
            
            # Special Price Offer Configuration
            elif offer_type == "Special Price":
                products = load_data(PRODUCTS_FILE)
                if not products:
                    st.warning("No products available. Please add products first.")
                else:
                    product_options = {f"{v['name']} ({k})": k for k, v in products.items()}
                    selected_product = st.selectbox("Select Product*", [""] + list(product_options.keys()))
                    
                    if selected_product:
                        barcode = product_options[selected_product]
                        product = products[barcode]
                        original_price = product.get('price', 0)
                        
                        special_price = st.number_input("Special Price*", min_value=0.01, value=original_price * 0.9, 
                                                       step=0.01, help="Temporary special price for this product")
                        
                        discount_amount = original_price - special_price
                        discount_percent = (discount_amount / original_price) * 100 if original_price > 0 else 0
                        st.success(f"Discount: {format_currency(discount_amount)} ({discount_percent:.1f}% off)")
            
            # Percentage Discount Offer Configuration
            elif offer_type == "Percentage Discount":
                discount_percent = st.number_input("Discount Percentage*", min_value=1, max_value=100, value=10, 
                                                  step=1, help="Percentage discount to apply")
                
                products = load_data(PRODUCTS_FILE)
                if not products:
                    st.warning("No products available. Please add products first.")
                else:
                    product_options = {f"{v['name']} ({k})": k for k, v in products.items()}
                    selected_products = st.multiselect("Select Products*", list(product_options.keys()),
                                                     help="Products this discount applies to")
            
            # Fixed Discount Offer Configuration
            elif offer_type == "Fixed Discount":
                discount_amount = st.number_input("Discount Amount*", min_value=0.01, value=1.0, 
                                                 step=0.01, help="Fixed amount to discount")
                
                products = load_data(PRODUCTS_FILE)
                if not products:
                    st.warning("No products available. Please add products first.")
                else:
                    product_options = {f"{v['name']} ({k})": k for k, v in products.items()}
                    selected_products = st.multiselect("Select Products*", list(product_options.keys()),
                                                     help="Products this discount applies to")
            
            # Date Range for Offer
            st.subheader("Offer Validity")
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date*", value=datetime.date.today())
            with col2:
                end_date = st.date_input("End Date*", value=datetime.date.today() + datetime.timedelta(days=7))
            
            # Additional Options
            st.subheader("Additional Options")
            active = st.checkbox("Active", value=True, help="Enable/disable this offer")
            apply_to_all = st.checkbox("Apply to All Products", value=False, 
                                     help="Apply this offer to all products (overrides product selection)")
            
            submit_button = st.form_submit_button("➕ Add Offer")
            
            if submit_button:
                # Validation
                errors = []
                
                if not name:
                    errors.append("Offer name is required")
                
                if offer_type in ["BOGO", "Bundle", "Percentage Discount", "Fixed Discount"] and not apply_to_all:
                    if offer_type == "BOGO" and not selected_products:
                        errors.append("Please select at least one product for BOGO offer")
                    elif offer_type == "Bundle" and not selected_products:
                        errors.append("Please select bundle products")
                    elif offer_type in ["Percentage Discount", "Fixed Discount"] and not selected_products:
                        errors.append("Please select products for discount")
                
                if offer_type == "Special Price" and not selected_product:
                    errors.append("Please select a product for special pricing")
                
                if end_date < start_date:
                    errors.append("End date cannot be before start date")
                
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    offers = load_data(OFFERS_FILE)
                    offer_id = f"offer_{generate_short_id()}"
                    
                    offer_data = {
                        'id': offer_id,
                        'name': name,
                        'description': description,
                        'type': offer_type.lower().replace(' ', '_'),
                        'start_date': start_date.strftime("%Y-%m-%d"),
                        'end_date': end_date.strftime("%Y-%m-%d"),
                        'active': active,
                        'apply_to_all': apply_to_all,
                        'created_by': st.session_state.user_info['username'],
                        'created_at': get_current_datetime().strftime("%Y-%m-%d %H:%M:%S"),
                        'updated_at': get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    # Add type-specific data
                    if offer_type == "BOGO":
                        offer_data['buy_quantity'] = buy_quantity
                        offer_data['get_quantity'] = get_quantity
                        if not apply_to_all:
                            offer_data['products'] = [product_options[p] for p in selected_products]
                    
                    elif offer_type == "Bundle":
                        offer_data['bundle_price'] = bundle_price
                        if not apply_to_all:
                            offer_data['products'] = [product_options[p] for p in selected_products]
                    
                    elif offer_type == "Special Price":
                        offer_data['product'] = product_options[selected_product]
                        offer_data['special_price'] = special_price
                    
                    elif offer_type == "Percentage Discount":
                        offer_data['discount_percent'] = discount_percent
                        if not apply_to_all:
                            offer_data['products'] = [product_options[p] for p in selected_products]
                    
                    elif offer_type == "Fixed Discount":
                        offer_data['discount_amount'] = discount_amount
                        if not apply_to_all:
                            offer_data['products'] = [product_options[p] for p in selected_products]
                    
                    # Save offer
                    offers[offer_id] = offer_data
                    save_data(offers, OFFERS_FILE)
                    
                    st.success(f"✅ Offer '{name}' added successfully!")
                    st.balloons()
    
    with tab2:
        st.header("View/Edit Offers")
        
        offers = load_data(OFFERS_FILE)
        products = load_data(PRODUCTS_FILE)
        
        if not offers:
            st.info("No offers available. Create your first offer above!")
        else:
            # Filter options
            col1, col2, col3 = st.columns(3)
            with col1:
                status_filter = st.selectbox("Filter by Status", ["All", "Active", "Inactive"])
            with col2:
                type_filter = st.selectbox("Filter by Type", ["All"] + list(set(o['type'].replace('_', ' ').title() for o in offers.values())))
            with col3:
                search_term = st.text_input("Search Offers", placeholder="Search by name...")
            
            # Apply filters
            filtered_offers = offers.copy()
            
            if status_filter != "All":
                active_status = status_filter == "Active"
                filtered_offers = {k: v for k, v in filtered_offers.items() if v['active'] == active_status}
            
            if type_filter != "All":
                type_key = type_filter.lower().replace(' ', '_')
                filtered_offers = {k: v for k, v in filtered_offers.items() if v['type'] == type_key}
            
            if search_term:
                filtered_offers = {k: v for k, v in filtered_offers.items() if search_term.lower() in v['name'].lower()}
            
            if not filtered_offers:
                st.info("No offers match the selected filters")
            else:
                st.write(f"**Found {len(filtered_offers)} offer(s)**")
                
                for offer_id, offer in filtered_offers.items():
                    # Determine offer status badge
                    current_date = datetime.date.today()
                    start_date = datetime.datetime.strptime(offer['start_date'], "%Y-%m-%d").date()
                    end_date = datetime.datetime.strptime(offer['end_date'], "%Y-%m-%d").date()
                    
                    status_badge = ""
                    if not offer['active']:
                        status_badge = "🔴 Inactive"
                    elif current_date < start_date:
                        status_badge = "⏳ Upcoming"
                    elif current_date > end_date:
                        status_badge = "⌛ Expired"
                    else:
                        status_badge = "✅ Active"
                    
                    with st.expander(f"{offer['name']} - {offer['type'].replace('_', ' ').title()} - {status_badge}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Description:** {offer.get('description', 'No description')}")
                            st.write(f"**Type:** {offer['type'].replace('_', ' ').title()}")
                            st.write(f"**Valid:** {offer['start_date']} to {offer['end_date']}")
                            st.write(f"**Status:** {'Active' if offer['active'] else 'Inactive'}")
                            st.write(f"**Apply to All:** {'Yes' if offer.get('apply_to_all', False) else 'No'}")
                            
                            # Show type-specific details
                            if offer['type'] == 'bogo':
                                st.write(f"**Buy:** {offer.get('buy_quantity', 1)} Get: {offer.get('get_quantity', 1)} Free")
                            elif offer['type'] == 'bundle':
                                st.write(f"**Bundle Price:** {format_currency(offer.get('bundle_price', 0))}")
                            elif offer['type'] == 'special_price':
                                st.write(f"**Special Price:** {format_currency(offer.get('special_price', 0))}")
                            elif offer['type'] == 'percentage_discount':
                                st.write(f"**Discount:** {offer.get('discount_percent', 0)}%")
                            elif offer['type'] == 'fixed_discount':
                                st.write(f"**Discount:** {format_currency(offer.get('discount_amount', 0))}")
                        
                        with col2:
                            # Show products if not applying to all
                            if not offer.get('apply_to_all', False):
                                st.write("**Applied to:**")
                                if offer['type'] == 'special_price':
                                    product_id = offer.get('product')
                                    if product_id and product_id in products:
                                        st.write(f"- {products[product_id].get('name', 'Unknown')} ({product_id})")
                                    else:
                                        st.warning("Product not found")
                                else:
                                    product_ids = offer.get('products', [])
                                    for pid in product_ids:
                                        if pid in products:
                                            st.write(f"- {products[pid].get('name', 'Unknown')} ({pid})")
                                        else:
                                            st.warning(f"Product {pid} not found")
                            
                            st.write(f"**Created by:** {offer.get('created_by', 'Unknown')}")
                            st.write(f"**Created at:** {offer.get('created_at', 'Unknown')}")
                            st.write(f"**Last updated:** {offer.get('updated_at', 'Unknown')}")
                        
                        # Edit form
                        with st.form(key=f"edit_{offer_id}"):
                            st.subheader("Edit Offer")
                            
                            edit_name = st.text_input("Name", value=offer.get('name', ''))
                            edit_description = st.text_area("Description", value=offer.get('description', ''))
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                edit_start_date = st.date_input("Start Date", 
                                                              value=datetime.datetime.strptime(offer.get('start_date'), "%Y-%m-%d").date())
                            with col2:
                                edit_end_date = st.date_input("End Date", 
                                                            value=datetime.datetime.strptime(offer.get('end_date'), "%Y-%m-%d").date())
                            
                            edit_active = st.checkbox("Active", value=offer.get('active', True))
                            
                            # Type-specific editing
                            if offer['type'] == 'bogo':
                                col1, col2 = st.columns(2)
                                with col1:
                                    edit_buy_qty = st.number_input("Buy Quantity", min_value=1, 
                                                                 value=offer.get('buy_quantity', 1), step=1)
                                with col2:
                                    edit_get_qty = st.number_input("Get Quantity Free", min_value=1, 
                                                                  value=offer.get('get_quantity', 1), step=1)
                            
                            elif offer['type'] == 'bundle':
                                edit_bundle_price = st.number_input("Bundle Price", min_value=0.01, 
                                                                  value=offer.get('bundle_price', 0.0), step=0.01)
                            
                            elif offer['type'] == 'special_price':
                                edit_special_price = st.number_input("Special Price", min_value=0.01, 
                                                                   value=offer.get('special_price', 0.0), step=0.01)
                            
                            elif offer['type'] == 'percentage_discount':
                                edit_discount_percent = st.number_input("Discount Percentage", min_value=1, max_value=100, 
                                                                      value=offer.get('discount_percent', 10), step=1)
                            
                            elif offer['type'] == 'fixed_discount':
                                edit_discount_amount = st.number_input("Discount Amount", min_value=0.01, 
                                                                     value=offer.get('discount_amount', 1.0), step=0.01)
                            
                            if st.form_submit_button("💾 Update Offer"):
                                # Update offer data
                                offers[offer_id]['name'] = edit_name
                                offers[offer_id]['description'] = edit_description
                                offers[offer_id]['start_date'] = edit_start_date.strftime("%Y-%m-%d")
                                offers[offer_id]['end_date'] = edit_end_date.strftime("%Y-%m-%d")
                                offers[offer_id]['active'] = edit_active
                                offers[offer_id]['updated_at'] = get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
                                
                                # Update type-specific data
                                if offer['type'] == 'bogo':
                                    offers[offer_id]['buy_quantity'] = edit_buy_qty
                                    offers[offer_id]['get_quantity'] = edit_get_qty
                                elif offer['type'] == 'bundle':
                                    offers[offer_id]['bundle_price'] = edit_bundle_price
                                elif offer['type'] == 'special_price':
                                    offers[offer_id]['special_price'] = edit_special_price
                                elif offer['type'] == 'percentage_discount':
                                    offers[offer_id]['discount_percent'] = edit_discount_percent
                                elif offer['type'] == 'fixed_discount':
                                    offers[offer_id]['discount_amount'] = edit_discount_amount
                                
                                save_data(offers, OFFERS_FILE)
                                st.success("✅ Offer updated successfully!")
                                st.rerun()
                        
                        # Delete button
                        if st.button("🗑️ Delete Offer", key=f"delete_{offer_id}"):
                            del offers[offer_id]
                            save_data(offers, OFFERS_FILE)
                            st.success("✅ Offer deleted successfully!")
                            st.rerun()
    
    with tab3:
        st.header("Bulk Import Offers")
        
        st.info("Download the template file to prepare your offer data")
        
        # Generate template file with examples for each offer type
        template_data = {
            "name": ["Summer BOGO", "Winter Bundle", "Spring Special", "Fall Discount"],
            "description": ["Buy 2 Get 1 Free Summer Special", "Winter essentials bundle", "Spring clearance special pricing", "Fall season discount"],
            "type": ["bogo", "bundle", "special_price", "percentage_discount"],
            "buy_quantity": [2, "", "", ""],
            "get_quantity": [1, "", "", ""],
            "bundle_price": ["", 29.99, "", ""],
            "special_price": ["", "", 15.99, ""],
            "discount_percent": ["", "", "", 15],
            "discount_amount": ["", "", "", ""],
            "product": ["", "", "123456789012", ""],
            "products": ["123456789012,987654321098", "123456789012,987654321098,555555555555", "", "123456789012,987654321098"],
            "start_date": ["2023-06-01", "2023-12-01", "2023-03-01", "2023-09-01"],
            "end_date": ["2023-08-31", "2023-02-28", "2023-05-31", "2023-11-30"],
            "active": [True, True, True, True],
            "apply_to_all": [False, False, False, False]
        }
        template_df = pd.DataFrame(template_data)
        
        st.download_button(
            label="📥 Download Import Template",
            data=template_df.to_csv(index=False).encode('utf-8'),
            file_name="offers_import_template.csv",
            mime="text/csv",
            help="Download the CSV template with example data for different offer types"
        )
        
        uploaded_file = st.file_uploader("Choose a CSV file", type=['csv'], 
                                       help="Upload your offers data CSV file")
        
        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file)
                st.success("✅ CSV file loaded successfully!")
                
                # Show preview
                st.subheader("Data Preview")
                st.dataframe(df.head())
                
                # Validation options
                st.subheader("Import Options")
                import_mode = st.radio("Import Mode", 
                                     ["Add new offers only", "Update existing offers", "Add or update offers"],
                                     help="Choose how to handle existing offers with the same name")
                
                on_error = st.radio("On Error", 
                                  ["Skip row and continue", "Stop import"],
                                  help="Choose what to do when encountering errors")
                
                if st.button("🚀 Import Offers", type="primary"):
                    offers = load_data(OFFERS_FILE)
                    products = load_data(PRODUCTS_FILE)
                    imported = 0
                    updated = 0
                    errors = []
                    
                    for index, row in df.iterrows():
                        try:
                            # Skip empty rows
                            if pd.isna(row.get('name')) or not str(row.get('name')).strip():
                                errors.append(f"Row {index+2}: Missing offer name")
                                continue
                            
                            # Basic validation
                            if pd.isna(row.get('type')) or str(row.get('type')).strip() not in ['bogo', 'bundle', 'special_price', 'percentage_discount', 'fixed_discount']:
                                errors.append(f"Row {index+2}: Invalid offer type")
                                continue
                            
                            offer_type = str(row.get('type')).strip()
                            
                            # Check if offer already exists
                            existing_offer_id = None
                            for oid, o in offers.items():
                                if o['name'] == str(row.get('name')).strip():
                                    existing_offer_id = oid
                                    break
                            
                            # Handle based on import mode
                            if import_mode == "Add new offers only" and existing_offer_id:
                                continue
                            if import_mode == "Update existing offers" and not existing_offer_id:
                                continue
                            
                            # Prepare offer data
                            offer_id = existing_offer_id if existing_offer_id else f"offer_{generate_short_id()}"
                            
                            offer_data = {
                                'id': offer_id,
                                'name': str(row.get('name')).strip(),
                                'description': str(row.get('description')).strip() if not pd.isna(row.get('description')) else "",
                                'type': offer_type,
                                'start_date': str(row.get('start_date')).strip() if not pd.isna(row.get('start_date')) else datetime.date.today().strftime("%Y-%m-%d"),
                                'end_date': str(row.get('end_date')).strip() if not pd.isna(row.get('end_date')) else (datetime.date.today() + datetime.timedelta(days=7)).strftime("%Y-%m-%d"),
                                'active': bool(row.get('active')) if not pd.isna(row.get('active')) else True,
                                'apply_to_all': bool(row.get('apply_to_all')) if not pd.isna(row.get('apply_to_all')) else False,
                                'updated_at': get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            
                            if not existing_offer_id:
                                offer_data['created_by'] = st.session_state.user_info['username']
                                offer_data['created_at'] = get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
                            
                            # Add type-specific data
                            if offer_type == 'bogo':
                                offer_data['buy_quantity'] = int(row.get('buy_quantity', 1)) if not pd.isna(row.get('buy_quantity')) else 1
                                offer_data['get_quantity'] = int(row.get('get_quantity', 1)) if not pd.isna(row.get('get_quantity')) else 1
                                
                                if not offer_data['apply_to_all']:
                                    if pd.isna(row.get('products')):
                                        errors.append(f"Row {index+2}: Products required for BOGO offer")
                                        continue
                                    product_list = [p.strip() for p in str(row.get('products')).split(',')]
                                    valid_products = [p for p in product_list if p in products]
                                    if not valid_products:
                                        errors.append(f"Row {index+2}: No valid products found")
                                        continue
                                    offer_data['products'] = valid_products
                            
                            elif offer_type == 'bundle':
                                if pd.isna(row.get('bundle_price')):
                                    errors.append(f"Row {index+2}: Bundle price required")
                                    continue
                                offer_data['bundle_price'] = float(row.get('bundle_price'))
                                
                                if not offer_data['apply_to_all']:
                                    if pd.isna(row.get('products')):
                                        errors.append(f"Row {index+2}: Products required for bundle offer")
                                        continue
                                    product_list = [p.strip() for p in str(row.get('products')).split(',')]
                                    valid_products = [p for p in product_list if p in products]
                                    if len(valid_products) < 2:
                                        errors.append(f"Row {index+2}: Bundle requires at least 2 products")
                                        continue
                                    offer_data['products'] = valid_products
                            
                            elif offer_type == 'special_price':
                                if pd.isna(row.get('special_price')):
                                    errors.append(f"Row {index+2}: Special price required")
                                    continue
                                offer_data['special_price'] = float(row.get('special_price'))
                                
                                if not offer_data['apply_to_all']:
                                    if pd.isna(row.get('product')):
                                        errors.append(f"Row {index+2}: Product required for special price offer")
                                        continue
                                    product_id = str(row.get('product')).strip()
                                    if product_id not in products:
                                        errors.append(f"Row {index+2}: Product {product_id} not found")
                                        continue
                                    offer_data['product'] = product_id
                            
                            elif offer_type == 'percentage_discount':
                                if pd.isna(row.get('discount_percent')):
                                    errors.append(f"Row {index+2}: Discount percentage required")
                                    continue
                                offer_data['discount_percent'] = float(row.get('discount_percent'))
                                
                                if not offer_data['apply_to_all']:
                                    if pd.isna(row.get('products')):
                                        errors.append(f"Row {index+2}: Products required for discount offer")
                                        continue
                                    product_list = [p.strip() for p in str(row.get('products')).split(',')]
                                    valid_products = [p for p in product_list if p in products]
                                    if not valid_products:
                                        errors.append(f"Row {index+2}: No valid products found")
                                        continue
                                    offer_data['products'] = valid_products
                            
                            elif offer_type == 'fixed_discount':
                                if pd.isna(row.get('discount_amount')):
                                    errors.append(f"Row {index+2}: Discount amount required")
                                    continue
                                offer_data['discount_amount'] = float(row.get('discount_amount'))
                                
                                if not offer_data['apply_to_all']:
                                    if pd.isna(row.get('products')):
                                        errors.append(f"Row {index+2}: Products required for discount offer")
                                        continue
                                    product_list = [p.strip() for p in str(row.get('products')).split(',')]
                                    valid_products = [p for p in product_list if p in products]
                                    if not valid_products:
                                        errors.append(f"Row {index+2}: No valid products found")
                                        continue
                                    offer_data['products'] = valid_products
                            
                            # Save offer
                            offers[offer_id] = offer_data
                            
                            if existing_offer_id:
                                updated += 1
                            else:
                                imported += 1
                            
                        except Exception as e:
                            error_msg = f"Row {index+2}: {str(e)}"
                            errors.append(error_msg)
                            if on_error == "Stop import":
                                break
                    
                    # Save all offers
                    save_data(offers, OFFERS_FILE)
                    
                    # Show results
                    st.success(f"✅ Import completed: {imported} new offers, {updated} updated")
                    
                    if errors:
                        st.warning(f"Encountered {len(errors)} errors:")
                        with st.expander("View Errors"):
                            for error in errors:
                                st.write(f"- {error}")
                    
            except Exception as e:
                st.error(f"❌ Error reading CSV file: {str(e)}")

# Enhanced apply_offers_to_cart function with better BOGO handling
def apply_offers_to_cart(cart_items, current_total):
    """
    Apply active offers to the cart and return the updated total
    """
    offers = load_data(OFFERS_FILE)
    products = load_data(PRODUCTS_FILE)
    
    # Get active offers (within date range)
    current_date = datetime.date.today()
    active_offers = []
    
    for offer in offers.values():
        if not offer.get('active', True):
            continue
        
        try:
            start_date = datetime.datetime.strptime(offer.get('start_date'), "%Y-%m-%d").date()
            end_date = datetime.datetime.strptime(offer.get('end_date'), "%Y-%m-%d").date()
            
            if start_date <= current_date <= end_date:
                active_offers.append(offer)
        except (ValueError, TypeError):
            # Skip offers with invalid date formats
            continue
    
    total_after_offers = current_total
    applied_offers = []
    
    # Create a copy of cart items for processing
    cart_copy = cart_items.copy()
    
    for offer in active_offers:
        try:
            if offer['type'] == 'bogo':
                # Buy One Get One Free offer
                applicable_products = []
                
                if offer.get('apply_to_all', False):
                    # Apply to all products in cart
                    applicable_products = list(cart_copy.keys())
                else:
                    # Apply only to specified products
                    applicable_products = offer.get('products', [])
                
                buy_qty = offer.get('buy_quantity', 1)
                get_qty = offer.get('get_quantity', 1)
                
                for barcode in applicable_products:
                    if barcode in cart_copy:
                        item = cart_copy[barcode]
                        eligible_sets = item['quantity'] // (buy_qty + get_qty)
                        
                        if eligible_sets > 0:
                            discount_amount = eligible_sets * get_qty * item['price']
                            total_after_offers -= discount_amount
                            
                            applied_offers.append({
                                'type': 'bogo',
                                'name': offer['name'],
                                'product': item['name'],
                                'discount': discount_amount,
                                'details': f"Buy {buy_qty} Get {get_qty} Free"
                            })
            
            elif offer['type'] == 'bundle':
                # Bundle offer - check if all bundle products are in cart
                bundle_products = offer.get('products', [])
                
                if all(barcode in cart_copy for barcode in bundle_products):
                    # Calculate total quantity of each product in the bundle
                    bundle_quantities = [cart_copy[barcode]['quantity'] for barcode in bundle_products]
                    max_bundles = min(bundle_quantities)
                    
                    if max_bundles > 0:
                        # Calculate original and bundle prices
                        original_price = 0
                        for barcode in bundle_products:
                            original_price += cart_copy[barcode]['price'] * max_bundles
                        
                        bundle_price = offer.get('bundle_price', 0) * max_bundles
                        discount_amount = original_price - bundle_price
                        total_after_offers -= discount_amount
                        
                        applied_offers.append({
                            'type': 'bundle',
                            'name': offer['name'],
                            'discount': discount_amount,
                            'details': f"Bundle of {len(bundle_products)} products"
                        })
            
            elif offer['type'] == 'special_price':
                # Special price offer
                if offer.get('apply_to_all', False):
                    # Apply to all products
                    for barcode, item in cart_copy.items():
                        special_price = offer.get('special_price', 0)
                        discount_amount = (item['price'] - special_price) * item['quantity']
                        total_after_offers -= discount_amount
                        
                        applied_offers.append({
                            'type': 'special_price',
                            'name': offer['name'],
                            'product': item['name'],
                            'discount': discount_amount,
                            'details': f"Special price: {format_currency(special_price)}"
                        })
                else:
                    # Apply to specific product
                    product_barcode = offer.get('product')
                    if product_barcode in cart_copy:
                        special_price = offer.get('special_price', 0)
                        item = cart_copy[product_barcode]
                        discount_amount = (item['price'] - special_price) * item['quantity']
                        total_after_offers -= discount_amount
                        
                        applied_offers.append({
                            'type': 'special_price',
                            'name': offer['name'],
                            'product': item['name'],
                            'discount': discount_amount,
                            'details': f"Special price: {format_currency(special_price)}"
                        })
            
            elif offer['type'] == 'percentage_discount':
                # Percentage discount offer
                applicable_products = []
                
                if offer.get('apply_to_all', False):
                    # Apply to all products
                    applicable_products = list(cart_copy.keys())
                else:
                    # Apply to specific products
                    applicable_products = offer.get('products', [])
                
                discount_percent = offer.get('discount_percent', 0) / 100
                
                for barcode in applicable_products:
                    if barcode in cart_copy:
                        item = cart_copy[barcode]
                        discount_amount = item['price'] * item['quantity'] * discount_percent
                        total_after_offers -= discount_amount
                        
                        applied_offers.append({
                            'type': 'percentage_discount',
                            'name': offer['name'],
                            'product': item['name'],
                            'discount': discount_amount,
                            'details': f"{offer.get('discount_percent', 0)}% off"
                        })
            
            elif offer['type'] == 'fixed_discount':
                # Fixed amount discount offer
                applicable_products = []
                
                if offer.get('apply_to_all', False):
                    # Apply to all products
                    applicable_products = list(cart_copy.keys())
                else:
                    # Apply to specific products
                    applicable_products = offer.get('products', [])
                
                discount_amount_per_item = offer.get('discount_amount', 0)
                
                for barcode in applicable_products:
                    if barcode in cart_copy:
                        item = cart_copy[barcode]
                        total_discount = discount_amount_per_item * item['quantity']
                        total_after_offers -= total_discount
                        
                        applied_offers.append({
                            'type': 'fixed_discount',
                            'name': offer['name'],
                            'product': item['name'],
                            'discount': total_discount,
                            'details': f"{format_currency(discount_amount_per_item)} off per item"
                        })
        
        except Exception as e:
            # Skip offers that cause errors but continue processing others
            print(f"Error applying offer {offer.get('name', 'Unknown')}: {str(e)}")
            continue
    
    # Display applied offers
    if applied_offers:
        st.subheader("🎁 Applied Offers & Discounts")
        
        for offer in applied_offers:
            col1, col2, col3 = st.columns([3, 2, 1])
            
            with col1:
                st.write(f"**{offer['name']}**")
                if 'product' in offer:
                    st.write(f"*{offer['product']}*")
                if 'details' in offer:
                    st.caption(offer['details'])
            
            with col2:
                st.write(f"Discount: -{format_currency(offer['discount'])}")
            
            with col3:
                if offer['type'] == 'bogo':
                    st.success("BOGO")
                elif offer['type'] == 'bundle':
                    st.info("BUNDLE")
                elif offer['type'] == 'special_price':
                    st.warning("SPECIAL")
                elif offer['type'] == 'percentage_discount':
                    st.info("PERCENT")
                elif offer['type'] == 'fixed_discount':
                    st.info("FIXED")
        
        st.markdown("---")
    
    return max(total_after_offers, 0)  # Ensure total doesn't go negative
                
# Loyalty Program Management
def loyalty_management():
    if not is_manager():
        st.warning("You don't have permission to access this page")
        return
    
    st.title("Loyalty Program Management")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Tier Management", "Customer Points", "Rewards", "Bulk Import"])
    
    with tab1:
        st.header("Loyalty Tiers")
        
        loyalty = load_data(LOYALTY_FILE)
        tiers = loyalty.get('tiers', {})
        
        st.subheader("Current Tiers")
        if not tiers:
            st.info("No loyalty tiers defined")
        else:
            tier_df = pd.DataFrame.from_dict(tiers, orient='index')
            tier_df['discount'] = tier_df['discount'].apply(lambda x: f"{x*100}%")
            st.dataframe(tier_df)
        
        st.subheader("Add/Edit Tier")
        with st.form("tier_form"):
            tier_name = st.text_input("Tier Name*")
            min_points = st.number_input("Minimum Points Required*", min_value=0, value=1000, step=1)
            discount = st.number_input("Discount Percentage*", min_value=0, max_value=100, value=5, step=1)
            
            submit_button = st.form_submit_button("Save Tier")
            
            if submit_button:
                if not tier_name:
                    st.error("Tier name is required")
                else:
                    tiers[tier_name] = {
                        'min_points': min_points,
                        'discount': discount / 100  # Store as decimal
                    }
                    loyalty['tiers'] = tiers
                    save_data(loyalty, LOYALTY_FILE)
                    st.success("Tier saved successfully")
    
    with tab2:
        st.header("Customer Points")
        
        loyalty = load_data(LOYALTY_FILE)
        customers = loyalty.get('customers', {})
        
        st.subheader("Customer List")
        if not customers:
            st.info("No customers in loyalty program")
        else:
            customer_df = pd.DataFrame.from_dict(customers, orient='index')
            st.dataframe(customer_df[['name', 'phone', 'email', 'points', 'tier']])
        
        st.subheader("Add/Edit Customer")
        with st.form("customer_form"):
            name = st.text_input("Customer Name*")
            phone = st.text_input("Phone Number")
            email = st.text_input("Email")
            points = st.number_input("Points*", min_value=0, value=0, step=1)
            
            tiers = loyalty.get('tiers', {})
            if tiers:
                current_tier = None
                for tier_name, tier_data in tiers.items():
                    if points >= tier_data['min_points']:
                        current_tier = tier_name
                
                tier_options = list(tiers.keys())
                tier = st.selectbox("Tier", tier_options, index=tier_options.index(current_tier) if current_tier else 0)
            else:
                tier = st.text_input("Tier (no tiers defined yet)")
            
            if st.form_submit_button("Save Customer"):
                customer_id = str(uuid.uuid4())
                customers[customer_id] = {
                    'id': customer_id,
                    'name': name,
                    'phone': phone,
                    'email': email,
                    'points': points,
                    'tier': tier,
                    'last_updated': get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
                }
                loyalty['customers'] = customers
                save_data(loyalty, LOYALTY_FILE)
                st.success("Customer saved successfully")
    
    with tab3:
        st.header("Rewards Management")
        
        loyalty = load_data(LOYALTY_FILE)
        rewards = loyalty.get('rewards', {})
        
        st.subheader("Current Rewards")
        if not rewards:
            st.info("No rewards defined")
        else:
            reward_df = pd.DataFrame.from_dict(rewards, orient='index')
            st.dataframe(reward_df)
        
        st.subheader("Add/Edit Reward")
        with st.form("reward_form"):
            name = st.text_input("Reward Name*")
            points_required = st.number_input("Points Required*", min_value=1, value=100, step=1)
            description = st.text_area("Description")
            active = st.checkbox("Active", value=True)
            
            submit_button = st.form_submit_button("Save Reward")
            
            if submit_button:
                if not name:
                    st.error("Reward name is required")
                else:
                    reward_id = str(uuid.uuid4())
                    rewards[reward_id] = {
                        'name': name,
                        'points': points_required,
                        'description': description,
                        'active': active,
                        'created_at': get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    loyalty['rewards'] = rewards
                    save_data(loyalty, LOYALTY_FILE)
                    st.success("Reward saved successfully")
    
    with tab4:
        st.header("Bulk Import Customers")
        
        st.info("Download the template file to prepare your customer data")
        
        # Generate template file
        template_data = {
            "name": ["John Doe", ""],
            "phone": ["1234567890", ""],
            "email": ["john@example.com", ""],
            "points": [100, ""],
            "tier": ["Silver", ""]
        }
        template_df = pd.DataFrame(template_data)
        
        st.download_button(
            label="Download Template",
            data=template_df.to_csv(index=False).encode('utf-8'),
            file_name="loyalty_customer_import_template.csv",
            mime="text/csv"
        )
        
        uploaded_file = st.file_uploader("Upload CSV file", type=['csv'])
        
        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file)
                st.dataframe(df)
                
                if st.button("Import Customers"):
                    loyalty = load_data(LOYALTY_FILE)
                    customers = loyalty.get('customers', {})
                    tiers = loyalty.get('tiers', {})
                    imported = 0
                    updated = 0
                    errors = 0
                    
                    for _, row in df.iterrows():
                        try:
                            if pd.isna(row['name']) or str(row['name']).strip() == "":
                                errors += 1
                                continue
                            
                            customer_id = str(uuid.uuid4())
                            
                            customer_data = {
                                'id': customer_id,
                                'name': str(row['name']).strip(),
                                'phone': str(row['phone']).strip() if not pd.isna(row['phone']) else "",
                                'email': str(row['email']).strip() if not pd.isna(row['email']) else "",
                                'points': int(row['points']) if not pd.isna(row['points']) else 0,
                                'tier': str(row['tier']).strip() if not pd.isna(row['tier']) else "",
                                'last_updated': get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            
                            # Validate tier
                            if customer_data['tier'] and customer_data['tier'] not in tiers:
                                errors += 1
                                continue
                            
                            customers[customer_id] = customer_data
                            imported += 1
                        
                        except Exception as e:
                            errors += 1
                            continue
                    
                    loyalty['customers'] = customers
                    save_data(loyalty, LOYALTY_FILE)
                    st.success(f"Import completed: {imported} new customers, {errors} errors")
            except Exception as e:
                st.error(f"Error reading CSV file: {str(e)}")

# Categories Management
def categories_management():
    if not is_manager():
        st.warning("You don't have permission to access this page")
        return
    
    st.title("Categories Management")
    
    tab1, tab2 = st.tabs(["Manage Categories", "Manage Subcategories"])
    
    with tab1:
        st.header("Manage Categories")
        
        categories_data = load_data(CATEGORIES_FILE)
        categories = categories_data.get('categories', [])
        subcategories = categories_data.get('subcategories', {})
        
        st.subheader("Current Categories")
        if not categories:
            st.info("No categories defined")
        else:
            st.dataframe(pd.DataFrame(categories, columns=["Categories"]))
        
        st.subheader("Add/Edit Category")
        with st.form("category_form"):
            new_category = st.text_input("Category Name")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("Add Category"):
                    if new_category and new_category not in categories:
                        categories.append(new_category)
                        categories_data['categories'] = categories
                        if new_category not in subcategories:
                            subcategories[new_category] = []
                        categories_data['subcategories'] = subcategories
                        save_data(categories_data, CATEGORIES_FILE)
                        st.success("Category added successfully")
                        st.rerun()
            with col2:
                if categories and st.form_submit_button("Remove Selected"):
                    category_to_remove = st.selectbox("Select Category to Remove", [""] + categories)
                    if category_to_remove:
                        categories.remove(category_to_remove)
                        categories_data['categories'] = categories
                        if category_to_remove in subcategories:
                            del subcategories[category_to_remove]
                        categories_data['subcategories'] = subcategories
                        save_data(categories_data, CATEGORIES_FILE)
                        st.success("Category removed successfully")
                        st.rerun()
    
    with tab2:
        st.header("Manage Subcategories")
        
        categories_data = load_data(CATEGORIES_FILE)
        categories = categories_data.get('categories', [])
        subcategories = categories_data.get('subcategories', {})
        
        if not categories:
            st.info("No categories available to add subcategories")
        else:
            selected_category = st.selectbox("Select Category", categories)
            
            if selected_category:
                if selected_category not in subcategories:
                    subcategories[selected_category] = []
                
                st.subheader(f"Subcategories for {selected_category}")
                if not subcategories[selected_category]:
                    st.info("No subcategories defined for this category")
                else:
                    st.dataframe(pd.DataFrame(subcategories[selected_category], columns=["Subcategories"]))
                
                st.subheader("Add/Edit Subcategory")
                with st.form("subcategory_form"):
                    new_subcategory = st.text_input("Subcategory Name")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("Add Subcategory"):
                            if new_subcategory and new_subcategory not in subcategories[selected_category]:
                                subcategories[selected_category].append(new_subcategory)
                                categories_data['subcategories'] = subcategories
                                save_data(categories_data, CATEGORIES_FILE)
                                st.success("Subcategory added successfully")
                                st.rerun()
                    with col2:
                        if subcategories[selected_category] and st.form_submit_button("Remove Selected"):
                            subcategory_to_remove = st.selectbox("Select Subcategory to Remove", 
                                                               [""] + subcategories[selected_category])
                            if subcategory_to_remove:
                                subcategories[selected_category].remove(subcategory_to_remove)
                                categories_data['subcategories'] = subcategories
                                save_data(categories_data, CATEGORIES_FILE)
                                st.success("Subcategory removed successfully")
                                st.rerun()

# Suppliers Management
def suppliers_management():
    if not is_manager():
        st.warning("You don't have permission to access this page")
        return
    
    st.title("Suppliers Management")
    
    tab1, tab2, tab3 = st.tabs(["Add Supplier", "View/Edit Suppliers", "Delete Supplier"])
    
    with tab1:
        st.header("Add New Supplier")
        
        with st.form("add_supplier_form"):
            name = st.text_input("Supplier Name*")
            contact_person = st.text_input("Contact Person")
            phone = st.text_input("Phone Number*")
            email = st.text_input("Email")
            address = st.text_area("Address")
            products_supplied = st.text_area("Products Supplied (comma separated)")
            payment_terms = st.text_input("Payment Terms")
            
            submit_button = st.form_submit_button("Add Supplier")
            
            if submit_button:
                if not name or not phone:
                    st.error("Name and phone are required")
                else:
                    suppliers = load_data(SUPPLIERS_FILE)
                    supplier_id = str(uuid.uuid4())
                    
                    suppliers[supplier_id] = {
                        'id': supplier_id,
                        'name': name,
                        'contact_person': contact_person,
                        'phone': phone,
                        'email': email,
                        'address': address,
                        'products_supplied': [p.strip() for p in products_supplied.split(',')] if products_supplied else [],
                        'payment_terms': payment_terms,
                        'date_added': get_current_datetime().strftime("%Y-%m-%d %H:%M:%S"),
                        'added_by': st.session_state.user_info['username']
                    }
                    
                    save_data(suppliers, SUPPLIERS_FILE)
                    st.success("Supplier added successfully")
    
    with tab2:
        st.header("View/Edit Suppliers")
        
        suppliers = load_data(SUPPLIERS_FILE)
        if not suppliers:
            st.info("No suppliers available")
        else:
            search_term = st.text_input("Search Suppliers")
            
            if search_term:
                filtered_suppliers = {k: v for k, v in suppliers.items() 
                                    if search_term.lower() in v['name'].lower() or 
                                    search_term.lower() in v['phone'].lower()}
            else:
                filtered_suppliers = suppliers
            
            for supplier_id, supplier in filtered_suppliers.items():
                with st.expander(f"{supplier['name']} - {supplier['phone']}"):
                    with st.form(key=f"edit_{supplier_id}"):
                        name = st.text_input("Name", value=supplier.get('name', ''))
                        contact_person = st.text_input("Contact Person", value=supplier.get('contact_person', ''))
                        phone = st.text_input("Phone Number", value=supplier.get('phone', ''))
                        email = st.text_input("Email", value=supplier.get('email', ''))
                        address = st.text_area("Address", value=supplier.get('address', ''))
                        products_supplied = st.text_area("Products Supplied", 
                                                        value=", ".join(supplier.get('products_supplied', [])))
                        payment_terms = st.text_input("Payment Terms", value=supplier.get('payment_terms', ''))
                        
                        if st.form_submit_button("Update Supplier"):
                            suppliers[supplier_id]['name'] = name
                            suppliers[supplier_id]['contact_person'] = contact_person
                            suppliers[supplier_id]['phone'] = phone
                            suppliers[supplier_id]['email'] = email
                            suppliers[supplier_id]['address'] = address
                            suppliers[supplier_id]['products_supplied'] = [p.strip() for p in products_supplied.split(',')] if products_supplied else []
                            suppliers[supplier_id]['payment_terms'] = payment_terms
                            suppliers[supplier_id]['last_updated'] = get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
                            suppliers[supplier_id]['updated_by'] = st.session_state.user_info['username']
                            
                            save_data(suppliers, SUPPLIERS_FILE)
                            st.success("Supplier updated successfully")
    
    with tab3:
        st.header("Delete Supplier")
        
        suppliers = load_data(SUPPLIERS_FILE)
        if not suppliers:
            st.info("No suppliers available to delete")
        else:
            supplier_options = {f"{v['name']} ({v['phone']})": k for k, v in suppliers.items()}
            selected_supplier = st.selectbox("Select Supplier to Delete", [""] + list(supplier_options.keys()))
            
            if selected_supplier:
                supplier_id = supplier_options[selected_supplier]
                supplier = suppliers[supplier_id]
                
                st.warning(f"You are about to delete: {supplier['name']}")
                st.write(f"Phone: {supplier['phone']}")
                st.write(f"Contact: {supplier.get('contact_person', 'N/A')}")
                
                if st.button("Confirm Delete"):
                    del suppliers[supplier_id]
                    save_data(suppliers, SUPPLIERS_FILE)
                    st.success("Supplier deleted successfully")

# Reports & Analytics
def reports_analytics():
    if not is_manager():
        st.warning("You don't have permission to access this page")
        return
    
    st.title("Reports & Analytics")
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "Sales Reports", 
        "Inventory Reports", 
        "Customer Reports", 
        "Payment Analysis",
        "Brand Reports",
        "Return Analysis",
        "Custom Reports"
    ])
    
    with tab1:
        st.header("Sales Reports")
        
        transactions = load_data(TRANSACTIONS_FILE)
        if not transactions:
            st.info("No sales data available")
        else:
            report_type = st.selectbox("Sales Report Type", [
                "Daily Sales",
                "Weekly Sales",
                "Monthly Sales",
                "Product Sales",
                "Category Sales",
                "Cashier Performance",
                "Hourly Sales"
            ])
            
            # Date range filter
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date", value=datetime.date.today() - datetime.timedelta(days=30))
            with col2:
                end_date = st.date_input("End Date", value=datetime.date.today())
            
            # Convert transactions to DataFrame with error handling
            trans_list = []
            for t in transactions.values():
                try:
                    trans_date = datetime.datetime.strptime(t.get('date', ''), "%Y-%m-%d %H:%M:%S").date()
                    if start_date <= trans_date <= end_date:
                        trans_list.append({
                            'date': t['date'],
                            'transaction_id': t.get('transaction_id', 'N/A'),
                            'total': t.get('total', 0),
                            'cashier': t.get('cashier', 'N/A'),
                            'payment_method': t.get('payment_method', 'N/A'),
                            'items': t.get('items', {})
                        })
                except (ValueError, KeyError, AttributeError):
                    continue
            
            if not trans_list:
                st.info("No transactions in selected date range")
            else:
                trans_df = pd.DataFrame(trans_list)
                trans_df['date'] = pd.to_datetime(trans_df['date'])
                
                if report_type == "Daily Sales":
                    trans_df['date_group'] = trans_df['date'].dt.date
                    report_df = trans_df.groupby('date_group').agg({
                        'total': 'sum',
                        'transaction_id': 'count'
                    }).rename(columns={'transaction_id': 'transactions'})
                    
                    st.subheader("Daily Sales Summary")
                    st.dataframe(report_df)
                    
                    st.subheader("Daily Sales Chart")
                    st.line_chart(report_df['total'])
                    
                    # Summary stats
                    total_sales = report_df['total'].sum()
                    total_transactions = report_df['transactions'].sum()
                    avg_transaction = total_sales / total_transactions if total_transactions > 0 else 0
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Total Sales", format_currency(total_sales))
                    col2.metric("Total Transactions", total_transactions)
                    col3.metric("Average Transaction", format_currency(avg_transaction))
                
                elif report_type == "Weekly Sales":
                    trans_df['week'] = trans_df['date'].dt.strftime('%Y-%U')
                    report_df = trans_df.groupby('week').agg({
                        'total': 'sum',
                        'transaction_id': 'count'
                    }).rename(columns={'transaction_id': 'transactions'})
                    
                    st.subheader("Weekly Sales Summary")
                    st.dataframe(report_df)
                    
                    st.subheader("Weekly Sales Chart")
                    st.bar_chart(report_df['total'])
                
                elif report_type == "Monthly Sales":
                    trans_df['month'] = trans_df['date'].dt.strftime('%Y-%m')
                    report_df = trans_df.groupby('month').agg({
                        'total': 'sum',
                        'transaction_id': 'count'
                    }).rename(columns={'transaction_id': 'transactions'})
                    
                    st.subheader("Monthly Sales Summary")
                    st.dataframe(report_df)
                    
                    st.subheader("Monthly Sales Chart")
                    st.area_chart(report_df['total'])
                
                elif report_type == "Product Sales":
                    products = load_data(PRODUCTS_FILE)
                    product_sales = {}
                    
                    for t in trans_list:
                        for barcode, item in t.get('items', {}).items():
                            if barcode not in product_sales:
                                product_sales[barcode] = {
                                    'name': products.get(barcode, {}).get('name', 'Unknown'),
                                    'quantity': 0,
                                    'revenue': 0.0
                                }
                            
                            product_sales[barcode]['quantity'] += item.get('quantity', 0)
                            product_sales[barcode]['revenue'] += item.get('price', 0) * item.get('quantity', 0)
                    
                    if not product_sales:
                        st.info("No product sales in selected date range")
                    else:
                        sales_df = pd.DataFrame.from_dict(product_sales, orient='index')
                        sales_df = sales_df.sort_values('revenue', ascending=False)
                        
                        st.subheader("Product Sales Summary")
                        st.dataframe(sales_df)
                        
                        st.subheader("Top Selling Products")
                        top_n = st.slider("Show Top", 1, 20, 5)
                        st.bar_chart(sales_df.head(top_n)['revenue'])
                
                elif report_type == "Category Sales":
                    products = load_data(PRODUCTS_FILE)
                    categories = load_data(CATEGORIES_FILE).get('categories', [])
                    category_sales = {}
                    
                    for cat in categories:
                        category_sales[cat] = {'revenue': 0.0, 'quantity': 0}
                    
                    for t in trans_list:
                        for barcode, item in t.get('items', {}).items():
                            product = products.get(barcode, {})
                            category = product.get('category', 'Unknown')
                            
                            if category not in category_sales:
                                category_sales[category] = {'revenue': 0.0, 'quantity': 0}
                            
                            category_sales[category]['quantity'] += item.get('quantity', 0)
                            category_sales[category]['revenue'] += item.get('price', 0) * item.get('quantity', 0)
                    
                    if not category_sales:
                        st.info("No category sales in selected date range")
                    else:
                        sales_df = pd.DataFrame.from_dict(category_sales, orient='index')
                        sales_df = sales_df.sort_values('revenue', ascending=False)
                        
                        st.subheader("Category Sales Summary")
                        st.dataframe(sales_df)
                        
                        st.subheader("Sales by Category")
                        st.bar_chart(sales_df['revenue'])
                
                elif report_type == "Cashier Performance":
                    cashier_performance = {}
                    
                    for t in trans_list:
                        cashier = t.get('cashier', 'Unknown')
                        if cashier not in cashier_performance:
                            cashier_performance[cashier] = {
                                'transactions': 0,
                                'total_sales': 0.0,
                                'avg_sale': 0.0
                            }
                        
                        cashier_performance[cashier]['transactions'] += 1
                        cashier_performance[cashier]['total_sales'] += t.get('total', 0)
                    
                    for cashier, data in cashier_performance.items():
                        if data['transactions'] > 0:
                            data['avg_sale'] = data['total_sales'] / data['transactions']
                    
                    if not cashier_performance:
                        st.info("No cashier data in selected date range")
                    else:
                        performance_df = pd.DataFrame.from_dict(cashier_performance, orient='index')
                        performance_df = performance_df.sort_values('total_sales', ascending=False)
                        
                        st.subheader("Cashier Performance Summary")
                        st.dataframe(performance_df)
                        
                        st.subheader("Sales by Cashier")
                        st.bar_chart(performance_df['total_sales'])
                
                elif report_type == "Hourly Sales":
                    trans_df['hour'] = trans_df['date'].dt.hour
                    hourly_sales = trans_df.groupby('hour').agg({
                        'total': 'sum',
                        'transaction_id': 'count'
                    }).rename(columns={'transaction_id': 'transactions'})
                    
                    st.subheader("Hourly Sales Pattern")
                    st.bar_chart(hourly_sales['total'])
                    
                    st.subheader("Hourly Transaction Count")
                    st.bar_chart(hourly_sales['transactions'])
                
                # Export option
                csv = trans_df.to_csv(index=False)
                st.download_button(
                    label="Export Sales Data",
                    data=csv,
                    file_name=f"sales_report_{start_date}_to_{end_date}.csv",
                    mime="text/csv"
                )
    
    with tab2:
        st.header("Inventory Reports")
        
        inventory = load_data(INVENTORY_FILE)
        products = load_data(PRODUCTS_FILE)
        
        if not inventory:
            st.info("No inventory data available")
        else:
            report_type = st.selectbox("Inventory Report Type", [
                "Stock Levels",
                "Stock Value",
                "Stock Movement",
                "Inventory Audit",
                "Low Stock Alert",
                "Slow Moving Items"
            ])
            
            if report_type == "Stock Levels":
                inventory_list = []
                for barcode, inv_data in inventory.items():
                    product = products.get(barcode, {'name': 'Unknown'})
                    inventory_list.append({
                        'product': product['name'],
                        'barcode': barcode,
                        'quantity': inv_data.get('quantity', 0),
                        'reorder_point': inv_data.get('reorder_point', 10),
                        'status': 'Low Stock' if inv_data.get('quantity', 0) < inv_data.get('reorder_point', 10) else 'OK'
                    })
                
                inv_df = pd.DataFrame(inventory_list)
                
                # Filter options
                show_low_stock = st.checkbox("Show Only Low Stock Items")
                if show_low_stock:
                    inv_df = inv_df[inv_df['status'] == 'Low Stock']
                
                st.dataframe(inv_df)
                
                # Summary
                total_items = len(inv_df)
                low_stock_items = len(inv_df[inv_df['status'] == 'Low Stock'])
                out_of_stock_items = len(inv_df[inv_df['quantity'] == 0])
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Items", total_items)
                col2.metric("Low Stock Items", low_stock_items)
                col3.metric("Out of Stock", out_of_stock_items)
            
            elif report_type == "Stock Value":
                value_list = []
                for barcode, inv_data in inventory.items():
                    product = products.get(barcode, {'name': 'Unknown', 'cost': 0})
                    value_list.append({
                        'product': product['name'],
                        'barcode': barcode,
                        'quantity': inv_data.get('quantity', 0),
                        'unit_cost': product.get('cost', 0),
                        'total_value': inv_data.get('quantity', 0) * product.get('cost', 0)
                    })
                
                value_df = pd.DataFrame(value_list)
                total_value = value_df['total_value'].sum()
                
                st.write(f"**Total Inventory Value:** {format_currency(total_value)}")
                st.dataframe(value_df.sort_values('total_value', ascending=False))
                
                # Value by category
                category_value = {}
                for barcode, inv_data in inventory.items():
                    product = products.get(barcode, {})
                    category = product.get('category', 'Unknown')
                    cost = product.get('cost', 0)
                    quantity = inv_data.get('quantity', 0)
                    
                    category_value[category] = category_value.get(category, 0) + (cost * quantity)
                
                if category_value:
                    cat_df = pd.DataFrame({
                        'Category': list(category_value.keys()),
                        'Value': list(category_value.values())
                    }).sort_values('Value', ascending=False)
                    
                    st.subheader("Inventory Value by Category")
                    st.bar_chart(cat_df.set_index('Category'))
            
            elif report_type == "Stock Movement":
                st.info("Stock movement analysis would show inventory changes over time")
                # This would require tracking inventory changes history
                
            elif report_type == "Inventory Audit":
                st.info("Generate audit sheets for physical inventory counting")
                if st.button("Generate Audit Sheet"):
                    audit_data = []
                    for barcode, inv_data in inventory.items():
                        product = products.get(barcode, {'name': 'Unknown'})
                        audit_data.append({
                            'Product': product['name'],
                            'Barcode': barcode,
                            'System Quantity': inv_data.get('quantity', 0),
                            'Physical Count': "",
                            'Variance': "",
                            'Notes': ""
                        })
                    
                    audit_df = pd.DataFrame(audit_data)
                    st.dataframe(audit_df)
                    
                    csv = audit_df.to_csv(index=False)
                    st.download_button(
                        label="Download Audit Sheet",
                        data=csv,
                        file_name=f"inventory_audit_{datetime.date.today()}.csv",
                        mime="text/csv"
                    )
            
            elif report_type == "Low Stock Alert":
                low_stock_items = []
                for barcode, inv_data in inventory.items():
                    if inv_data.get('quantity', 0) < inv_data.get('reorder_point', 10):
                        product = products.get(barcode, {'name': 'Unknown', 'cost': 0})
                        low_stock_items.append({
                            'Product': product['name'],
                            'Barcode': barcode,
                            'Current Stock': inv_data.get('quantity', 0),
                            'Reorder Point': inv_data.get('reorder_point', 10),
                            'Needed': max(0, inv_data.get('reorder_point', 10) - inv_data.get('quantity', 0)),
                            'Cost': product.get('cost', 0),
                            'Value Needed': max(0, inv_data.get('reorder_point', 10) - inv_data.get('quantity', 0)) * product.get('cost', 0)
                        })
                
                if not low_stock_items:
                    st.success("No low stock items! All inventory levels are adequate.")
                else:
                    low_df = pd.DataFrame(low_stock_items)
                    st.dataframe(low_df.sort_values('Needed', ascending=False))
                    
                    total_value_needed = low_df['Value Needed'].sum()
                    st.metric("Total Value Needed to Reorder", format_currency(total_value_needed))
            
            elif report_type == "Slow Moving Items":
                # This would analyze products with low sales velocity
                st.info("Slow moving items analysis would identify products with low turnover")
    
    with tab3:
        st.header("Customer Reports")
        
        loyalty = load_data(LOYALTY_FILE)
        customers = loyalty.get('customers', {})
        transactions = load_data(TRANSACTIONS_FILE)
        
        if not customers:
            st.info("No customer data available")
        else:
            report_type = st.selectbox("Customer Report Type", [
                "Customer Spending",
                "Loyalty Members",
                "Customer Segmentation",
                "New vs Returning Customers"
            ])
            
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date", value=datetime.date.today() - datetime.timedelta(days=30), key="cust_start_date")
            with col2:
                end_date = st.date_input("End Date", value=datetime.date.today(), key="cust_end_date")
            
            if report_type == "Customer Spending":
                customer_spending = {}
                
                for cust_id, customer in customers.items():
                    customer_spending[cust_id] = {
                        'name': customer['name'],
                        'email': customer['email'],
                        'phone': customer.get('phone', ''),
                        'transactions': 0,
                        'total_spent': 0.0,
                        'avg_spend': 0.0,
                        'last_purchase': None
                    }
                
                for t in transactions.values():
                    try:
                        trans_date = datetime.datetime.strptime(t.get('date', ''), "%Y-%m-%d %H:%M:%S").date()
                        if 'customer_id' in t and start_date <= trans_date <= end_date:
                            cust_id = t['customer_id']
                            if cust_id in customer_spending:
                                customer_spending[cust_id]['transactions'] += 1
                                customer_spending[cust_id]['total_spent'] += t.get('total', 0)
                                # Update last purchase date
                                if not customer_spending[cust_id]['last_purchase'] or trans_date > datetime.datetime.strptime(customer_spending[cust_id]['last_purchase'], "%Y-%m-%d").date():
                                    customer_spending[cust_id]['last_purchase'] = trans_date.strftime("%Y-%m-%d")
                    except (ValueError, KeyError, AttributeError):
                        continue
                
                for cust_id, data in customer_spending.items():
                    if data['transactions'] > 0:
                        data['avg_spend'] = data['total_spent'] / data['transactions']
                
                if not customer_spending:
                    st.info("No customer spending data in selected date range")
                else:
                    spending_df = pd.DataFrame.from_dict(customer_spending, orient='index')
                    spending_df = spending_df.sort_values('total_spent', ascending=False)
                    
                    st.subheader("Customer Spending Summary")
                    st.dataframe(spending_df)
                    
                    st.subheader("Top Spending Customers")
                    top_n = st.slider("Show Top", 1, 20, 5, key="cust_top")
                    st.bar_chart(spending_df.head(top_n)['total_spent'])
            
            elif report_type == "Loyalty Members":
                loyalty_df = pd.DataFrame.from_dict(customers, orient='index')
                st.dataframe(loyalty_df[['name', 'email', 'phone', 'points', 'tier']].sort_values('points', ascending=False))
                
                # Loyalty tier distribution
                tier_distribution = loyalty_df['tier'].value_counts()
                st.subheader("Loyalty Tier Distribution")
                st.bar_chart(tier_distribution)
            
            elif report_type == "Customer Segmentation":
                st.info("Customer segmentation analysis would group customers by purchasing behavior")
                # This would involve RFM analysis (Recency, Frequency, Monetary)
                
            elif report_type == "New vs Returning Customers":
                st.info("Analysis of new versus returning customers would be implemented here")
    
    with tab4:
        st.header("Payment Analysis")
        
        transactions = load_data(TRANSACTIONS_FILE)
        if not transactions:
            st.info("No transaction data available")
        else:
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date", value=datetime.date.today() - datetime.timedelta(days=30), key="pay_start_date")
            with col2:
                end_date = st.date_input("End Date", value=datetime.date.today(), key="pay_end_date")
            
            payment_methods = {}
            
            for t in transactions.values():
                try:
                    trans_date = datetime.datetime.strptime(t.get('date', ''), "%Y-%m-%d %H:%M:%S").date()
                    if start_date <= trans_date <= end_date:
                        method = t.get('payment_method', 'Unknown')
                        if method not in payment_methods:
                            payment_methods[method] = {'count': 0, 'total': 0.0}
                        
                        payment_methods[method]['count'] += 1
                        payment_methods[method]['total'] += t.get('total', 0)
                except (ValueError, KeyError, AttributeError):
                    continue
            
            if not payment_methods:
                st.info("No payment data in selected date range")
            else:
                payment_df = pd.DataFrame.from_dict(payment_methods, orient='index')
                payment_df = payment_df.sort_values('total', ascending=False)
                
                st.subheader("Payment Method Summary")
                st.dataframe(payment_df)
                
                st.subheader("Payment Method Distribution")
                st.bar_chart(payment_df['total'])
                
                # Payment method trends over time
                payment_trends = {}
                for t in transactions.values():
                    try:
                        trans_date = datetime.datetime.strptime(t.get('date', ''), "%Y-%m-%d %H:%M:%S").date()
                        if start_date <= trans_date <= end_date:
                            method = t.get('payment_method', 'Unknown')
                            date_key = trans_date.strftime("%Y-%m-%d")
                            
                            if date_key not in payment_trends:
                                payment_trends[date_key] = {}
                            
                            payment_trends[date_key][method] = payment_trends[date_key].get(method, 0) + t.get('total', 0)
                    except (ValueError, KeyError, AttributeError):
                        continue
                
                if payment_trends:
                    trend_df = pd.DataFrame.from_dict(payment_trends, orient='index').fillna(0)
                    st.subheader("Payment Method Trends")
                    st.line_chart(trend_df)
    
    with tab5:
        st.header("Brand Reports")
        
        brands_data = load_data(BRANDS_FILE)
        products = load_data(PRODUCTS_FILE)
        inventory = load_data(INVENTORY_FILE)
        transactions = load_data(TRANSACTIONS_FILE)
        brands_list = brands_data.get('brands', [])
        brand_products = brands_data.get('brand_products', {})
        
        if not brands_list:
            st.info("No brands available for reporting")
        else:
            report_type = st.selectbox("Brand Report Type", [
                "Sales by Brand",
                "Inventory by Brand",
                "Product Performance by Brand",
                "Brand Comparison"
            ])
            
            # Date range for sales reports
            if report_type in ["Sales by Brand", "Product Performance by Brand"]:
                col1, col2 = st.columns(2)
                with col1:
                    start_date = st.date_input("Start Date", value=datetime.date.today() - datetime.timedelta(days=30), key="brand_start_date")
                with col2:
                    end_date = st.date_input("End Date", value=datetime.date.today(), key="brand_end_date")
            
            if report_type == "Sales by Brand":
                brand_sales = {}
                for brand in brands_list:
                    brand_sales[brand] = {'revenue': 0, 'units': 0, 'transactions': 0}
                
                for transaction in transactions.values():
                    try:
                        trans_date = datetime.datetime.strptime(transaction.get('date', ''), "%Y-%m-%d %H:%M:%S").date()
                        if start_date <= trans_date <= end_date:
                            has_brand_items = False
                            for barcode, item in transaction.get('items', {}).items():
                                product = products.get(barcode, {})
                                brand = product.get('brand')
                                if brand and brand in brand_sales:
                                    brand_sales[brand]['revenue'] += item['price'] * item['quantity']
                                    brand_sales[brand]['units'] += item['quantity']
                                    has_brand_items = True
                            
                            if has_brand_items:
                                brand_sales[brand]['transactions'] += 1
                    except (ValueError, KeyError):
                        continue
                
                sales_df = pd.DataFrame.from_dict(brand_sales, orient='index')
                sales_df = sales_df.sort_values('revenue', ascending=False)
                
                st.subheader("Sales by Brand")
                st.dataframe(sales_df)
                
                # Charts
                col1, col2 = st.columns(2)
                with col1:
                    st.bar_chart(sales_df['revenue'])
                with col2:
                    st.bar_chart(sales_df['units'])
            
            elif report_type == "Inventory by Brand":
                brand_inventory = {}
                for brand in brands_list:
                    brand_inventory[brand] = {'value': 0, 'quantity': 0, 'products': 0, 'avg_cost': 0}
                
                for barcode, product in products.items():
                    brand = product.get('brand')
                    if brand and brand in brand_inventory:
                        inv_data = inventory.get(barcode, {})
                        quantity = inv_data.get('quantity', 0)
                        cost = product.get('cost', 0)
                        
                        brand_inventory[brand]['value'] += quantity * cost
                        brand_inventory[brand]['quantity'] += quantity
                        brand_inventory[brand]['products'] += 1
                        brand_inventory[brand]['avg_cost'] = brand_inventory[brand]['value'] / quantity if quantity > 0 else 0
                
                inv_df = pd.DataFrame.from_dict(brand_inventory, orient='index')
                inv_df = inv_df.sort_values('value', ascending=False)
                
                st.subheader("Inventory by Brand")
                st.dataframe(inv_df)
                
                # Charts
                col1, col2 = st.columns(2)
                with col1:
                    st.bar_chart(inv_df['value'])
                with col2:
                    st.bar_chart(inv_df['quantity'])
            
            elif report_type == "Product Performance by Brand":
                selected_brand = st.selectbox("Select Brand", [""] + brands_list)
                
                if selected_brand:
                    product_sales = {}
                    for barcode in brand_products.get(selected_brand, []):
                        product_sales[barcode] = {
                            'name': products.get(barcode, {}).get('name', 'Unknown'),
                            'revenue': 0,
                            'units': 0
                        }
                    
                    for transaction in transactions.values():
                        try:
                            trans_date = datetime.datetime.strptime(transaction.get('date', ''), "%Y-%m-%d %H:%M:%S").date()
                            if start_date <= trans_date <= end_date:
                                for barcode, item in transaction.get('items', {}).items():
                                    if barcode in product_sales:
                                        product_sales[barcode]['revenue'] += item['price'] * item['quantity']
                                        product_sales[barcode]['units'] += item['quantity']
                        except (ValueError, KeyError):
                            continue
                    
                    performance_df = pd.DataFrame.from_dict(product_sales, orient='index')
                    performance_df = performance_df.sort_values('revenue', ascending=False)
                    
                    st.subheader(f"Product Performance for {selected_brand}")
                    st.dataframe(performance_df)
                    
                    # Charts
                    col1, col2 = st.columns(2)
                    with col1:
                        st.bar_chart(performance_df['revenue'])
                    with col2:
                        st.bar_chart(performance_df['units'])
            
            elif report_type == "Brand Comparison":
                comparison_metric = st.selectbox("Comparison Metric", ["Revenue", "Inventory Value", "Product Count"])
                
                comparison_data = {}
                for brand in brands_list:
                    if comparison_metric == "Revenue":
                        # Calculate revenue for last 30 days
                        thirty_days_ago = (datetime.datetime.now() - datetime.timedelta(days=30)).date()
                        revenue = 0
                        for transaction in transactions.values():
                            try:
                                trans_date = datetime.datetime.strptime(transaction.get('date', ''), "%Y-%m-%d %H:%M:%S").date()
                                if trans_date >= thirty_days_ago:
                                    for barcode, item in transaction.get('items', {}).items():
                                        product = products.get(barcode, {})
                                        if product.get('brand') == brand:
                                            revenue += item['price'] * item['quantity']
                            except (ValueError, KeyError):
                                continue
                        comparison_data[brand] = revenue
                    
                    elif comparison_metric == "Inventory Value":
                        value = 0
                        for barcode in brand_products.get(brand, []):
                            inv_data = inventory.get(barcode, {})
                            product = products.get(barcode, {})
                            quantity = inv_data.get('quantity', 0)
                            cost = product.get('cost', 0)
                            value += quantity * cost
                        comparison_data[brand] = value
                    
                    elif comparison_metric == "Product Count":
                        comparison_data[brand] = len(brand_products.get(brand, []))
                
                comparison_df = pd.DataFrame.from_dict(comparison_data, orient='index', columns=[comparison_metric])
                comparison_df = comparison_df.sort_values(comparison_metric, ascending=False)
                
                st.subheader(f"Brand Comparison by {comparison_metric}")
                st.dataframe(comparison_df)
                
                st.bar_chart(comparison_df[comparison_metric])
    
    with tab6:
        st.header("Return Analysis")
        
        returns_data = load_data(RETURNS_FILE)
        
        if not returns_data:
            st.info("No return data available for analysis")
        else:
            # Date range
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date", value=datetime.date.today() - datetime.timedelta(days=90), key="return_start")
            with col2:
                end_date = st.date_input("End Date", value=datetime.date.today(), key="return_end")
            
            # Filter returns by date
            filtered_returns = []
            for return_data in returns_data.values():
                return_date = datetime.datetime.strptime(return_data['return_date'], "%Y-%m-%d %H:%M:%S").date()
                if start_date <= return_date <= end_date:
                    filtered_returns.append(return_data)
            
            if not filtered_returns:
                st.info("No returns in selected date range")
            else:
                # Calculate analytics
                total_returns = len(filtered_returns)
                total_refund_amount = sum(r['total_refund'] for r in filtered_returns)
                avg_refund = total_refund_amount / total_returns if total_returns > 0 else 0
                
                # Return rate calculation (would need total sales data)
                st.subheader("Return Summary")
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Returns", total_returns)
                col2.metric("Total Refund Amount", format_currency(total_refund_amount))
                col3.metric("Average Refund", format_currency(avg_refund))
                
                # Return reasons analysis
                return_reasons = {}
                for return_data in filtered_returns:
                    reason = return_data['reason']
                    return_reasons[reason] = return_reasons.get(reason, 0) + 1
                
                if return_reasons:
                    reasons_df = pd.DataFrame({
                        'Reason': list(return_reasons.keys()),
                        'Count': list(return_reasons.values())
                    }).sort_values('Count', ascending=False)
                    
                    st.subheader("Returns by Reason")
                    st.bar_chart(reasons_df.set_index('Reason'))
                
                # Return by product type
                products = load_data(PRODUCTS_FILE)
                product_returns = {}
                for return_data in filtered_returns:
                    for barcode, item in return_data['items'].items():
                        product_name = products.get(barcode, {}).get('name', 'Unknown')
                        product_returns[product_name] = product_returns.get(product_name, 0) + item['quantity']
                
                if product_returns:
                    product_df = pd.DataFrame({
                        'Product': list(product_returns.keys()),
                        'Return Quantity': list(product_returns.values())
                    }).sort_values('Return Quantity', ascending=False).head(10)
                    
                    st.subheader("Most Returned Products")
                    st.bar_chart(product_df.set_index('Product'))
    
    with tab7:
        st.header("Custom Reports")
        
        st.info("Create custom reports with specific filters and criteria")
        
        with st.form("custom_report_form"):
            report_name = st.text_input("Report Name", "Custom_Report")
            
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date", value=datetime.date.today() - datetime.timedelta(days=30), key="custom_start")
            with col2:
                end_date = st.date_input("End Date", value=datetime.date.today(), key="custom_end")
            
            report_type = st.selectbox("Report Type", [
                "Sales Summary",
                "Product Performance",
                "Customer Analysis",
                "Inventory Status"
            ])
            
            if report_type == "Sales Summary":
                st.info("Sales summary report would show overall sales performance")
            elif report_type == "Product Performance":
                st.info("Product performance report would analyze product sales and profitability")
            elif report_type == "Customer Analysis":
                st.info("Customer analysis report would examine customer behavior and value")
            elif report_type == "Inventory Status":
                st.info("Inventory status report would show current stock levels and values")
            
            if st.form_submit_button("Generate Custom Report"):
                st.success(f"Custom report '{report_name}' would be generated for {start_date} to {end_date}")

# Shifts Management
def shifts_management():
    st.title("Shifts Management")
    
    shifts = load_data(SHIFTS_FILE)
    
    if is_cashier():
        # Cashier view - only show their shifts
        user_shifts = [s for s in shifts.values() if s['user_id'] == st.session_state.user_info['username']]
        user_shifts = sorted(user_shifts, key=lambda x: x['start_time'], reverse=True)
        
        st.header("Your Shifts")
        
        if not user_shifts:
            st.info("No shifts recorded")
        else:
            shift_df = pd.DataFrame(user_shifts)
            st.dataframe(shift_df[['start_time', 'end_time', 'starting_cash', 'ending_cash', 'status']])
        
        # Current shift actions
        if st.session_state.shift_started:
            st.subheader("Current Shift")
            current_shift = shifts.get(st.session_state.shift_id, {})
            
            st.write(f"Started at: {current_shift.get('start_time', 'N/A')}")
            st.write(f"Starting Cash: {format_currency(current_shift.get('starting_cash', 0))}")
            
            # Calculate current cash
            transactions = load_data(TRANSACTIONS_FILE)
            shift_transactions = [t for t in transactions.values() 
                                if t.get('shift_id') == st.session_state.shift_id and t['payment_method'] == 'Cash']
            total_cash = sum(t['total'] for t in shift_transactions)
            st.write(f"Current Cash: {format_currency(total_cash)}")
            
            if st.button("End Shift"):
                if end_shift():
                    st.success("Shift ended successfully")
                    st.rerun()
                else:
                    st.error("Failed to end shift")
        else:
            st.info("No active shift")
    
    else:
        # Manager/Admin view - show all shifts
        st.header("All Shifts")
        
        if not shifts:
            st.info("No shifts recorded")
        else:
            # Filter options
            col1, col2 = st.columns(2)
            with col1:
                user_filter = st.selectbox("Filter by User", ["All"] + list(set(s['user_id'] for s in shifts.values())))
            with col2:
                status_filter = st.selectbox("Filter by Status", ["All", "active", "completed"])
            
            # Apply filters
            filtered_shifts = shifts.values()
            if user_filter != "All":
                filtered_shifts = [s for s in filtered_shifts if s['user_id'] == user_filter]
            if status_filter != "All":
                filtered_shifts = [s for s in filtered_shifts if s['status'] == status_filter]
            
            if not filtered_shifts:
                st.info("No shifts match the filters")
            else:
                shift_df = pd.DataFrame(filtered_shifts)
                shift_df = shift_df.sort_values('start_time', ascending=False)
                st.dataframe(shift_df[['user_id', 'start_time', 'end_time', 'starting_cash', 'ending_cash', 'status']])
        
        # Shift details
        if shifts:
            selected_shift = st.selectbox("View Shift Details", [""] + [f"{s['user_id']} - {s['start_time']}" for s in shifts.values()])
            
            if selected_shift:
                shift_id = [k for k, v in shifts.items() if f"{v['user_id']} - {v['start_time']}" == selected_shift][0]
                shift = shifts[shift_id]
                
                st.subheader("Shift Details")
                st.write(f"User: {shift['user_id']}")
                st.write(f"Start Time: {shift['start_time']}")
                st.write(f"End Time: {shift.get('end_time', 'Still active')}")
                st.write(f"Starting Cash: {format_currency(shift.get('starting_cash', 0))}")
                st.write(f"Ending Cash: {format_currency(shift.get('ending_cash', 0))}")
                st.write(f"Status: {shift['status']}")
                
                # Show transactions for this shift
                transactions = load_data(TRANSACTIONS_FILE)
                shift_transactions = [t for t in transactions.values() if t.get('shift_id') == shift_id]
                
                if shift_transactions:
                    st.subheader("Shift Transactions")
                    trans_df = pd.DataFrame(shift_transactions)
                    st.dataframe(trans_df[['transaction_id', 'date', 'total', 'payment_method']])

# System Settings
def system_settings():
    if not is_admin():
        st.warning("You don't have permission to access this page")
        return
    
    st.title("System Settings")
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Store Settings", "POS Configuration", "Tax Settings", 
        "Printer Settings", "Hardware Settings", "Payment Charges"
    ])
    
    with tab1:
        st.header("Store Information")
        
        settings = load_data(SETTINGS_FILE)
        
        with st.form("store_settings_form"):
            store_name = st.text_input("Store Name", value=settings.get('store_name', ''))
            store_address = st.text_area("Store Address", value=settings.get('store_address', ''))
            store_phone = st.text_input("Store Phone", value=settings.get('store_phone', ''))
            store_email = st.text_input("Store Email", value=settings.get('store_email', ''))
            
            logo = st.file_uploader("Store Logo", type=['jpg', 'png', 'jpeg'])
            if logo and 'logo' in settings and os.path.exists(settings['logo']):
                st.image(settings['logo'], width=150)
            
            receipt_header = st.text_area("Receipt Header Text", value=settings.get('receipt_header', ''))
            receipt_footer = st.text_area("Receipt Footer Text", value=settings.get('receipt_footer', ''))
            print_logo = st.checkbox("Print Logo on Receipt", value=settings.get('receipt_print_logo', False))
            
            if st.form_submit_button("Save Store Settings"):
                settings['store_name'] = store_name
                settings['store_address'] = store_address
                settings['store_phone'] = store_phone
                settings['store_email'] = store_email
                settings['receipt_header'] = receipt_header
                settings['receipt_footer'] = receipt_footer
                settings['receipt_print_logo'] = print_logo
                
                if logo:
                    # Remove old logo if exists
                    if 'logo' in settings and os.path.exists(settings['logo']):
                        os.remove(settings['logo'])
                    
                    # Save new logo
                    logo_path = os.path.join(DATA_DIR, f"store_logo.{logo.name.split('.')[-1]}")
                    with open(logo_path, 'wb') as f:
                        f.write(logo.getbuffer())
                    settings['logo'] = logo_path
                
                save_data(settings, SETTINGS_FILE)
                st.success("Store settings saved successfully")
    
    with tab2:
        st.header("POS Configuration")
        
        settings = load_data(SETTINGS_FILE)
        
        with st.form("pos_config_form"):
            receipt_template = st.selectbox(
                "Receipt Template",
                ["Simple", "Detailed", "Modern"],
                index=["Simple", "Detailed", "Modern"].index(settings.get('receipt_template', 'Simple'))
            )
            
            theme = st.selectbox(
                "Theme",
                ["Light", "Dark", "Blue"],
                index=["Light", "Dark", "Blue"].index(settings.get('theme', 'Light'))
            )
            
            timeout = st.number_input(
                "Session Timeout (minutes)",
                min_value=1,
                max_value=120,
                value=settings.get('session_timeout', 30)
            )
            
            timezone = st.selectbox(
                "Timezone",
                pytz.all_timezones,
                index=pytz.all_timezones.index(settings.get('timezone', 'UTC'))
            )
            
            currency_symbol = st.text_input(
                "Currency Symbol",
                value=settings.get('currency_symbol', '$')
            )
            
            decimal_places = st.number_input(
                "Decimal Places",
                min_value=0,
                max_value=4,
                value=settings.get('decimal_places', 2)
            )
            
            auto_logout = st.checkbox(
                "Enable Auto Logout",
                value=settings.get('auto_logout', True)
            )
            
            if st.form_submit_button("Save POS Configuration"):
                settings['receipt_template'] = receipt_template
                settings['theme'] = theme
                settings['session_timeout'] = timeout
                settings['timezone'] = timezone
                settings['currency_symbol'] = currency_symbol
                settings['decimal_places'] = decimal_places
                settings['auto_logout'] = auto_logout
                save_data(settings, SETTINGS_FILE)
                st.success("POS configuration saved successfully")
                st.rerun()  # Refresh to apply theme changes
    
    with tab3:
        st.header("Tax Settings")
        
        settings = load_data(SETTINGS_FILE)
        
        with st.form("tax_settings_form"):
            tax_rate = st.number_input(
                "Tax Rate (%)",
                min_value=0.0,
                max_value=25.0,
                value=settings.get('tax_rate', 0.0) * 100,
                step=0.1
            )
            
            tax_inclusive = st.checkbox(
                "Prices Include Tax",
                value=settings.get('tax_inclusive', False)
            )
            
            if st.form_submit_button("Save Tax Settings"):
                settings['tax_rate'] = tax_rate / 100
                settings['tax_inclusive'] = tax_inclusive
                save_data(settings, SETTINGS_FILE)
                st.success("Tax settings saved successfully")
    
   # In the System Settings section (tab4), replace the printer settings with:

    with tab4:
       st.header("Printer Settings")
    
       settings = load_data(SETTINGS_FILE)
    
       with st.form("printer_settings_form"):
         printer_name = st.text_input(
            "Printer Name (for reference only)",
            value=settings.get('printer_name', 'Browser Printer')
         )
        
         test_print = st.text_area("Test Receipt Text", 
                                value="POS System Test Receipt\n====================\nTest Line 1\nTest Line 2\n====================")
        
         col1, col2 = st.columns(2)
         with col1:
            if st.form_submit_button("Save Printer Settings"):
                settings['printer_name'] = printer_name
                save_data(settings, SETTINGS_FILE)
                st.success("Printer settings saved successfully")
         with col2:
            if st.form_submit_button("Test Print"):
                if print_receipt(test_print):
                    st.success("Test receipt printed successfully")
                else:
                    st.error("Failed to print test receipt")
    
   # In the system_settings function, replace the hardware settings section with:

    with tab5:
     st.header("Hardware Settings")
    
     settings = load_data(SETTINGS_FILE)
     com_ports = get_available_com_ports()
    
     with st.form("hardware_settings_form"):
        barcode_scanner_type = st.selectbox(
            "Barcode Scanner Type",
            ["Keyboard", "Serial Scanner"],
            index=0 if settings.get('barcode_scanner', 'keyboard') == 'keyboard' else 1
        )
        
        barcode_scanner_port = st.selectbox(
            "Barcode Scanner Port (for serial scanners)",
            com_ports,
            index=com_ports.index(settings.get('barcode_scanner_port', 'auto'))
        )
        
        cash_drawer_enabled = st.checkbox(
            "Enable Cash Drawer",
            value=settings.get('cash_drawer_enabled', False)
        )
        
        cash_drawer_command = st.text_input(
            "Cash Drawer Command",
            value=settings.get('cash_drawer_command', '')
        )
        
        if st.form_submit_button("Save Hardware Settings"):
            # Stop any existing scanner
            if 'barcode_scanner' in globals() and hasattr(barcode_scanner, 'stop_scanning'):
                barcode_scanner.stop_scanning()
            
            # Update settings
            settings['barcode_scanner'] = barcode_scanner_type.lower().replace(' ', '_')
            settings['barcode_scanner_port'] = barcode_scanner_port
            settings['cash_drawer_enabled'] = cash_drawer_enabled
            settings['cash_drawer_command'] = cash_drawer_command
            save_data(settings, SETTINGS_FILE)
            
            # Reinitialize scanner with new settings
            setup_barcode_scanner()
            st.success("Hardware settings saved successfully")
    with tab6:
        st.header("Payment Charges Configuration")
        
        settings = load_data(SETTINGS_FILE)
        payment_charges = settings.get('payment_charges', {
            "cash": 0.0,
            "credit_card": 2.0,
            "debit_card": 1.0,
            "mobile_payment": 1.5,
            "bank_transfer": 0.5,
            "international_card": 3.0
        })
        
        with st.form("payment_charges_form"):
            st.subheader("Payment Method Charges (%)")
            
            col1, col2 = st.columns(2)
            with col1:
                cash_charge = st.number_input(
                    "Cash Charge",
                    min_value=0.0,
                    max_value=10.0,
                    value=payment_charges.get('cash', 0.0),
                    step=0.1,
                    help="Percentage charge for cash payments (usually 0%)"
                )
                credit_card_charge = st.number_input(
                    "Credit Card Charge",
                    min_value=0.0,
                    max_value=10.0,
                    value=payment_charges.get('credit_card', 2.0),
                    step=0.1,
                    help="Percentage charge for credit card payments"
                )
                debit_card_charge = st.number_input(
                    "Debit Card Charge",
                    min_value=0.0,
                    max_value=10.0,
                    value=payment_charges.get('debit_card', 1.0),
                    step=0.1,
                    help="Percentage charge for debit card payments"
                )
            
            with col2:
                mobile_payment_charge = st.number_input(
                    "Mobile Payment Charge",
                    min_value=0.0,
                    max_value=10.0,
                    value=payment_charges.get('mobile_payment', 1.5),
                    step=0.1,
                    help="Percentage charge for mobile payments (Apple Pay, Google Pay, etc.)"
                )
                bank_transfer_charge = st.number_input(
                    "Bank Transfer Charge",
                    min_value=0.0,
                    max_value=10.0,
                    value=payment_charges.get('bank_transfer', 0.5),
                    step=0.1,
                    help="Percentage charge for bank transfers"
                )
                international_card_charge = st.number_input(
                    "International Card Charge",
                    min_value=0.0,
                    max_value=10.0,
                    value=payment_charges.get('international_card', 3.0),
                    step=0.1,
                    help="Percentage charge for international credit/debit cards"
                )
            
            if st.form_submit_button("Save Payment Charges"):
                settings['payment_charges'] = {
                    'cash': cash_charge,
                    'credit_card': credit_card_charge,
                    'debit_card': debit_card_charge,
                    'mobile_payment': mobile_payment_charge,
                    'bank_transfer': bank_transfer_charge,
                    'international_card': international_card_charge
                }
                save_data(settings, SETTINGS_FILE)
                st.success("Payment charges saved successfully")

# Backup & Restore
# Backup & Restore Management Module
def backup_restore():
    if not is_admin():
        st.warning("You don't have permission to access this page")
        return
    
    st.title("📦 Backup & Restore")
    
    tab1, tab2, tab3 = st.tabs(["Create Backup", "Restore Backup", "Backup History"])
    
    with tab1:
        create_backup_tab()
    
    with tab2:
        restore_backup_tab()
    
    with tab3:
        backup_history_tab()

def create_backup_tab():
    st.header("Create System Backup")
    
    st.info("This will create a complete backup of all system data including:")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("✓ Products and inventory")
        st.write("✓ Transaction history")
        st.write("✓ User accounts")
        st.write("✓ Customer data")
    with col2:
        st.write("✓ Settings and configuration")
        st.write("✓ Suppliers and purchase orders")
        st.write("✓ Discounts and promotions")
        st.write("✓ All other system data")
    
    backup_name = st.text_input("Backup Name (optional)", 
                               value=f"pos_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")
    
    # Backup options
    st.subheader("Backup Options")
    compress_backup = st.checkbox("Compress Backup (Recommended)", value=True)
    
    if st.button("🔄 Create Backup Now", type="primary", use_container_width=True):
        with st.spinner("Creating backup... This may take a moment"):
            try:
                backup_path = create_complete_backup(backup_name, compress=compress_backup)
                
                if backup_path and os.path.exists(backup_path):
                    st.success("✅ Backup created successfully!")
                    
                    # Show backup details
                    backup_size = os.path.getsize(backup_path)
                    st.info(f"**Backup Size:** {format_file_size(backup_size)}")
                    st.info(f"**Backup Location:** `{backup_path}`")
                    st.info(f"**Created:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    # Download button
                    with open(backup_path, "rb") as f:
                        backup_data = f.read()
                    
                    st.download_button(
                        label="📥 Download Backup File",
                        data=backup_data,
                        file_name=os.path.basename(backup_path),
                        mime="application/zip" if compress_backup else "application/octet-stream",
                        use_container_width=True
                    )
                else:
                    st.error("❌ Failed to create backup")
                    
            except Exception as e:
                st.error(f"❌ Backup creation failed: {str(e)}")
                st.error("Please check system permissions and try again")

def restore_backup_tab():
    st.header("Restore System Backup")
    
    st.warning("""
    ⚠️ **Warning:** Restoring a backup will overwrite all current system data. 
    This action cannot be undone. Make sure you have a current backup before proceeding.
    """)
    
    # Upload backup file
    uploaded_file = st.file_uploader("Choose a backup file", type=['zip', 'bak', 'posbak'], 
                                   help="Select a backup file created by this system")
    
    if uploaded_file:
        try:
            # Check file signature to determine type
            file_signature = uploaded_file.getvalue()[:4]
            is_zip = file_signature == b'PK\x03\x04'  # ZIP file signature
            
            # Save uploaded file temporarily
            temp_dir = os.path.join(BACKUP_DIR, "temp_restore")
            os.makedirs(temp_dir, exist_ok=True)
            
            temp_path = os.path.join(temp_dir, uploaded_file.name)
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getvalue())
            
            # Validate backup file
            if is_zip:
                # Validate ZIP backup
                if not validate_zip_backup(temp_path):
                    st.error("❌ Invalid backup file format. This doesn't appear to be a valid POS backup.")
                    return
            else:
                # Validate uncompressed backup
                if not validate_uncompressed_backup(temp_path):
                    st.error("❌ Invalid backup file format. This doesn't appear to be a valid POS backup.")
                    return
            
            st.success("✅ Valid backup file detected")
            
            # Show backup information
            backup_info = get_backup_info(temp_path, is_zip)
            if backup_info:
                st.subheader("Backup Information")
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Backup Name:** {backup_info.get('name', 'Unknown')}")
                    st.write(f"**Created:** {backup_info.get('timestamp', 'Unknown')}")
                with col2:
                    st.write(f"**Data Files:** {backup_info.get('file_count', 0)}")
                    st.write(f"**Size:** {format_file_size(len(uploaded_file.getvalue()))}")
            
            # Confirmation
            st.subheader("Confirmation")
            confirmation = st.text_input("Type 'RESTORE' to confirm", 
                                       help="This is required to prevent accidental restores")
            
            if st.button("🔄 Restore Backup", type="primary", use_container_width=True, 
                       disabled=confirmation != "RESTORE"):
                with st.spinner("Restoring backup... This may take a moment"):
                    try:
                        # Perform restore
                        success = restore_backup(temp_path, is_zip)
                        
                        # Clean up
                        try:
                            os.remove(temp_path)
                            os.rmdir(temp_dir)
                        except:
                            pass
                        
                        if success:
                            st.success("✅ Backup restored successfully!")
                            st.info("The system will need to be reloaded. Please refresh the page.")
                            
                            # Auto-refresh after a delay
                            st.write("Refreshing page in 5 seconds...")
                            time.sleep(5)
                            st.rerun()
                        else:
                            st.error("❌ Backup restoration failed")
                            
                    except Exception as e:
                        st.error(f"❌ Restore failed: {str(e)}")
            
        except Exception as e:
            st.error(f"❌ Error processing backup file: {str(e)}")
            # Clean up on error
            try:
                if 'temp_path' in locals() and os.path.exists(temp_path):
                    os.remove(temp_path)
                if 'temp_dir' in locals() and os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
            except:
                pass

def backup_history_tab():
    st.header("Backup History")
    
    # List existing backups
    backups = get_backup_list()
    
    if not backups:
        st.info("No backups found")
        return
    
    st.write(f"Found {len(backups)} backup(s)")
    
    # Sort backups by date (newest first)
    backups.sort(key=lambda x: x['timestamp'], reverse=True)
    
    for backup in backups:
        with st.expander(f"{backup['name']} - {backup['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}"):
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.write(f"**Size:** {format_file_size(backup['size'])}")
                st.write(f"**Path:** `{backup['path']}`")
                st.write(f"**Type:** {'Compressed' if backup['path'].endswith('.zip') else 'Uncompressed'}")
            
            with col2:
                # Download button
                if st.button("📥 Download", key=f"dl_{backup['name']}", use_container_width=True):
                    with open(backup['path'], "rb") as f:
                        backup_data = f.read()
                    
                    st.download_button(
                        label="Download Now",
                        data=backup_data,
                        file_name=os.path.basename(backup['path']),
                        mime="application/zip" if backup['path'].endswith('.zip') else "application/octet-stream",
                        key=f"dl_btn_{backup['name']}"
                    )
            
            with col3:
                # Delete button
                if st.button("🗑️ Delete", key=f"del_{backup['name']}", use_container_width=True):
                    try:
                        os.remove(backup['path'])
                        st.success("Backup deleted successfully")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error deleting backup: {str(e)}")

# Utility functions for backup/restore
def create_complete_backup(backup_name, compress=True):
    """Create a complete backup of all system data"""
    try:
        # Create backup directory if it doesn't exist
        os.makedirs(BACKUP_DIR, exist_ok=True)
        
        # Create backup filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if compress:
            backup_filename = f"{backup_name}.zip"
        else:
            backup_filename = f"{backup_name}.bak"
        
        backup_path = os.path.join(BACKUP_DIR, backup_filename)
        
        # Create backup manifest
        manifest = {
            'name': backup_name,
            'timestamp': datetime.datetime.now().isoformat(),
            'version': '1.0',
            'created_by': st.session_state.user_info['username'] if 'user_info' in st.session_state else 'system',
            'files': []
        }
        
        if compress:
            # Create ZIP backup
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add all data files
                data_files = []
                for root, _, files in os.walk(DATA_DIR):
                    for file in files:
                        if file.endswith('.json'):
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, DATA_DIR)
                            zipf.write(file_path, arcname)
                            manifest['files'].append(arcname)
                
                # Add manifest
                manifest_str = json.dumps(manifest, indent=2)
                zipf.writestr('manifest.json', manifest_str)
                
        else:
            # Create uncompressed backup (directory copy)
            backup_dir = backup_path
            os.makedirs(backup_dir, exist_ok=True)
            
            # Copy all data files
            for root, _, files in os.walk(DATA_DIR):
                for file in files:
                    if file.endswith('.json'):
                        src_path = os.path.join(root, file)
                        rel_path = os.path.relpath(src_path, DATA_DIR)
                        dst_path = os.path.join(backup_dir, rel_path)
                        
                        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                        shutil.copy2(src_path, dst_path)
                        manifest['files'].append(rel_path)
            
            # Save manifest
            with open(os.path.join(backup_dir, 'manifest.json'), 'w') as f:
                json.dump(manifest, f, indent=2)
        
        # Log backup creation
        log_backup_activity('create', backup_name, backup_path, True)
        
        return backup_path
        
    except Exception as e:
        # Log error
        log_backup_activity('create', backup_name, '', False, str(e))
        st.error(f"Backup creation failed: {str(e)}")
        return None

def validate_zip_backup(zip_path):
    """Validate if the ZIP file is a valid backup"""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            # Check for manifest file
            if 'manifest.json' not in zipf.namelist():
                return False
            
            # Check for at least some data files
            data_files = [f for f in zipf.namelist() if f.endswith('.json') and f != 'manifest.json']
            if len(data_files) == 0:
                return False
                
            return True
    except:
        return False

def validate_uncompressed_backup(backup_path):
    """Validate if the directory is a valid backup"""
    try:
        # Check if it's a directory
        if not os.path.isdir(backup_path):
            return False
        
        # Check for manifest file
        manifest_path = os.path.join(backup_path, 'manifest.json')
        if not os.path.exists(manifest_path):
            return False
        
        # Check for data files
        data_files = []
        for root, _, files in os.walk(backup_path):
            for file in files:
                if file.endswith('.json') and file != 'manifest.json':
                    data_files.append(file)
        
        if len(data_files) == 0:
            return False
            
        return True
    except:
        return False

def get_backup_info(backup_path, is_zip):
    """Get information about a backup file"""
    try:
        if is_zip:
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                if 'manifest.json' in zipf.namelist():
                    with zipf.open('manifest.json') as f:
                        manifest = json.load(f)
                    
                    return {
                        'name': manifest.get('name', 'Unknown'),
                        'timestamp': manifest.get('timestamp', 'Unknown'),
                        'file_count': len([f for f in zipf.namelist() if f.endswith('.json') and f != 'manifest.json'])
                    }
        else:
            manifest_path = os.path.join(backup_path, 'manifest.json')
            if os.path.exists(manifest_path):
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
                
                # Count data files
                data_files = []
                for root, _, files in os.walk(backup_path):
                    for file in files:
                        if file.endswith('.json') and file != 'manifest.json':
                            data_files.append(file)
                
                return {
                    'name': manifest.get('name', 'Unknown'),
                    'timestamp': manifest.get('timestamp', 'Unknown'),
                    'file_count': len(data_files)
                }
        
        return None
    except:
        return None

def restore_backup(backup_path, is_zip):
    """Restore system from backup"""
    try:
        # Create restore directory
        restore_dir = os.path.join(BACKUP_DIR, "restore_temp")
        os.makedirs(restore_dir, exist_ok=True)
        
        # Extract backup
        if is_zip:
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                zipf.extractall(restore_dir)
        else:
            # For directory backups, copy files to restore directory
            for item in os.listdir(backup_path):
                src_path = os.path.join(backup_path, item)
                dst_path = os.path.join(restore_dir, item)
                
                if os.path.isdir(src_path):
                    shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
                else:
                    shutil.copy2(src_path, dst_path)
        
        # Read manifest
        manifest_path = os.path.join(restore_dir, 'manifest.json')
        if not os.path.exists(manifest_path):
            raise Exception("Invalid backup: manifest file missing")
        
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        # Backup original data (safety measure)
        backup_original_data()
        
        # Restore all JSON files
        json_files = []
        for root, _, files in os.walk(restore_dir):
            for file in files:
                if file.endswith('.json'):
                    json_files.append(os.path.join(root, file))
        
        for json_file in json_files:
            # Get relative path
            rel_path = os.path.relpath(json_file, restore_dir)
            
            # Skip manifest for now (we'll handle it separately)
            if os.path.basename(json_file) == 'manifest.json':
                continue
            
            # Destination path
            dst_path = os.path.join(DATA_DIR, rel_path)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            
            # Copy file
            shutil.copy2(json_file, dst_path)
        
        # Clean up
        shutil.rmtree(restore_dir)
        
        # Log successful restore
        log_backup_activity('restore', manifest.get('name', 'unknown'), backup_path, True)
        
        return True
        
    except Exception as e:
        # Log error
        log_backup_activity('restore', 'unknown', backup_path, False, str(e))
        st.error(f"Restore failed: {str(e)}")
        
        # Clean up on error
        try:
            if os.path.exists(restore_dir):
                shutil.rmtree(restore_dir)
        except:
            pass
        
        return False

def get_backup_list():
    """Get list of all backups"""
    backups = []
    
    if not os.path.exists(BACKUP_DIR):
        return backups
    
    for filename in os.listdir(BACKUP_DIR):
        if filename.endswith(('.zip', '.bak')) and os.path.isfile(os.path.join(BACKUP_DIR, filename)):
            file_path = os.path.join(BACKUP_DIR, filename)
            file_size = os.path.getsize(file_path)
            file_time = datetime.datetime.fromtimestamp(os.path.getctime(file_path))
            
            backups.append({
                'name': filename,
                'path': file_path,
                'size': file_size,
                'timestamp': file_time
            })
    
    return backups

def backup_original_data():
    """Create a backup of current data before restore"""
    try:
        backup_dir = os.path.join(BACKUP_DIR, "pre_restore_backup")
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for root, _, files in os.walk(DATA_DIR):
            for file in files:
                if file.endswith('.json'):
                    src_path = os.path.join(root, file)
                    rel_path = os.path.relpath(src_path, DATA_DIR)
                    dst_path = os.path.join(backup_dir, f"{timestamp}_{rel_path}")
                    
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                    shutil.copy2(src_path, dst_path)
        
        return True
    except:
        return False

def format_file_size(size_bytes):
    """Format file size in human-readable format"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.2f} {size_names[i]}"

def log_backup_activity(action, backup_name, backup_path, success, error_msg=None):
    """Log backup/restore activities"""
    log_entry = {
        'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'action': action,
        'backup_name': backup_name,
        'backup_path': backup_path,
        'success': success,
        'user': st.session_state.user_info['username'] if 'user_info' in st.session_state else 'system'
    }
    
    if error_msg:
        log_entry['error'] = error_msg
    
    # Load existing logs
    log_file = os.path.join(DATA_DIR, "backup_logs.json")
    logs = []
    
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r') as f:
                logs = json.load(f)
        except:
            logs = []
    
    # Add new log entry
    logs.append(log_entry)
    
    # Keep only last 100 entries
    if len(logs) > 100:
        logs = logs[-100:]
    
    # Save logs
    with open(log_file, 'w') as f:
        json.dump(logs, f, indent=2)

# Check user roles
def is_admin():
    return get_current_user_role() == 'admin'

def get_current_user_role():
    if 'user_info' in st.session_state:
        return st.session_state.user_info.get('role')
    return None

# Constants
DATA_DIR = "data"
BACKUP_DIR = "backups"

# Main App
def main():
    # Set page config
    st.set_page_config(
        page_title="Supermarket POS",
        page_icon="🛒",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize data directories and files FIRST
    initialize_empty_data()
    ensure_default_user()

    
    # Apply theme from settings
    settings = load_data(SETTINGS_FILE)
    if settings.get('theme') == 'Dark':
        dark_theme = """
        <style>
        .stApp { background-color: #1E1E1E; color: white; }
        .st-bb { background-color: #1E1E1E; }
        .st-at { background-color: #2E2E2E; }
        </style>
        """
        st.markdown(dark_theme, unsafe_allow_html=True)
    elif settings.get('theme') == 'Blue':
        blue_theme = """
        <style>
        .stApp { background-color: #E6F3FF; }
        </style>
        """
        st.markdown(blue_theme, unsafe_allow_html=True)
    
    # Page routing
    if st.session_state.current_page == "Login":
        login_page()
    else:
        dashboard()

if __name__ == "__main__":
    main()                                                      