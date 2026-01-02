from flask import Flask, render_template, request, redirect, url_for, flash, get_flashed_messages, send_file, session
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
import os
import re


app = Flask(__name__)
DB_FILE = 'expenses.db'
app.secret_key = 'your_secret_key_here'

# 初始化資料庫
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        c = conn.cursor()
        
        # users table
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                password_hash TEXT
            )
        ''')
        
        # trips table
        c.execute('''
            CREATE TABLE IF NOT EXISTS trips (
                id INTEGER PRIMARY KEY,
                trip_name TEXT UNIQUE,
                start_date TEXT,
                end_date TEXT,
                
                country_id INTEGER,
                FOREIGN KEY(country_id) REFERENCES countries(id)
            )
        ''')

        # countries table
        c.execute('''
            CREATE TABLE IF NOT EXISTS countries (
                id INTEGER PRIMARY KEY,
                country_name TEXT UNIQUE,
                country_code TEXT UNIQUE
            )
        ''') 
        
        countries = [
            ('Taiwan', 'TW'),
            ('Japan', 'JP'),
            ('South Korea', 'KR'),
            ('Vietnam', 'VN'),
            ('United States', 'US'),
            ('United Kindom', 'GB')
        ]
        
        c.executemany(
            'INSERT OR IGNORE INTO countries (country_name, country_code) VALUES (?, ?)',
            countries
        )        
                
        # paymentMethods table
        c.execute('''
            CREATE TABLE IF NOT EXISTS paymentMethods (
                id INTEGER PRIMARY KEY,
                method_name TEXT UNIQUE
            )
        ''')
        
        # insert paymentMethods
        default_paymentMethods = [
            (1, 'card'),
            (2, 'cash')
        ]
        
        for method in default_paymentMethods:
            c.execute('INSERT OR IGNORE INTO paymentMethods (id, method_name) VALUES (?, ?)', method)

        # categories table
        c.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY,
                cat_name TEXT UNIQUE,
                order_index INTEGER
            )
        ''')
        
        # insert categories
        default_categories = [
            ('meals', 1),
            ('activities', 2),
            ('transportation', 3),
            ('accommodation', 4),
            ('others', 5)
        ]

        for cat_name, order_index in default_categories:
            c.execute(
                'INSERT OR IGNORE INTO categories (cat_name, order_index) VALUES (?, ?)',
                (cat_name, order_index)
            )

        # currencies table
        c.execute('''CREATE TABLE IF NOT EXISTS currencies (
                     id INTEGER PRIMARY KEY, 
                     code TEXT UNIQUE, 
                     currency_name TEXT,
                     symbol TEXT,
                     is_base INTEGER DEFAULT 0
                    )
                ''')
                
        default_currencies = [
            ('NTD', 'New Taiwanese Dollar', '$'),
            ('JPY', 'Japanese Yen', '¥'),
            ('KRW', 'Korean Won', '₩'),
            ('VND', 'Vietnamese Dong', '₫'),
            ('USD', 'US Dollar', '$'),
            ('EUR', 'Euro', '€'),
            ('GBP', 'British Pound', '£')
        ]

        for code, currency_name, symbol in default_currencies:
            c.execute(
                'INSERT OR IGNORE INTO currencies (code, currency_name, symbol) VALUES (?, ?, ?)',
                (code, currency_name, symbol)
            )
            
        # Exchange_rates table
        c.execute('''
            CREATE TABLE IF NOT EXISTS exchange_rates (
                id INTEGER PRIMARY KEY,
                currency_id INTEGER UNIQUE,
                rate_to_base REAL NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(currency_id) REFERENCES currencies(id)
            )
        ''')

        default_exchange_rates = [
            ('NTD', 1.0),
            ('JPY', 0.2004),
            ('KRW', 0.02114),
            ('VND', 0.001187),
            ('USD', 31.215),
            ('EUR', 36.617),
            ('GBP', 41.761)
        ]

        for code, rate in default_exchange_rates:
            c.execute('SELECT id FROM currencies WHERE code = ?', (code,))
            row = c.fetchone()
            if row:
                currency_id = row[0]
                updated_at = datetime.now().isoformat()
                c.execute('INSERT OR IGNORE INTO exchange_rates (currency_id, rate_to_base, updated_at)VALUES (?, ?, ?)', 
                    (currency_id, rate, updated_at)
                )
        
        # expenses table
        c.execute('''CREATE TABLE IF NOT EXISTS expenses (
                     id INTEGER PRIMARY KEY, 
                     purchase_date TEXT,
                     item TEXT, 
                     amount REAL,
                     
                     currency_id INTEGER,
                     method_id INTEGER, 
                     category_id INTEGER,
                     trip_id INTEGER,
                  
                     FOREIGN KEY(currency_id) REFERENCES currencies(id),
                     FOREIGN KEY(method_id) REFERENCES paymentMethods(id),
                     FOREIGN KEY(category_id) REFERENCES categories(id),
                     FOREIGN KEY(trip_id) REFERENCES trips(id)
                    )
                ''')
                
        conn.commit()


# gatekeeper
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return wrapper
    
    
    
# Validate password strongness
def is_strong_password(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"

    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"

    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one number"

    if " " in password:
        return False, "Password cannot contain spaces"

    return True, ""



# register
@app.route('/register', methods=['GET', 'POST'])
def register():
    errors = False
    
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        c = conn.cursor()
        
        if request.method == 'POST':
            uiUsername = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            confirm_password = request.form.get('confirm_password', '').strip()
            
            # Validation
            if not uiUsername:
                flash("Username cannot be empty!", "error")
                errors = True
            elif not password:
                flash("Password cannot be empty!", "error")
                errors = True
            elif not confirm_password:
                flash("Confirm password cannot be empty!", "error")
                errors = True
            elif not password == confirm_password:
                flash("Password must match each other!", "error")
                errors = True
            else:
                strong, msg = is_strong_password(password)
                if not strong:
                    flash(msg, "error")
                    errors = True
                else:
                    # Validate username
                    c.execute('''
                           SELECT username FROM users WHERE username = ?
                       ''', (uiUsername,))
                    dbUsername = c.fetchone()
                    
                    if dbUsername:
                        flash("Username already exists!", "error")
                        errors = True
            
            if not errors:
                try:
                    hashPass = generate_password_hash(password)
                    
                    c.execute('''
                            INSERT INTO users (username, password_hash) VALUES (?, ?)
                            ''', (uiUsername, hashPass)
                        )
                    conn.commit()
                    flash("Registration successful!", "success")
                    return redirect(url_for('login'))
            
                except sqlite3.DatabaseError:
                        flash("Database error occurred.", "error")
        
    return render_template(
        'register.html',
        errors=errors
    )
        


#login
@app.route('/login', methods=['GET', 'POST'])
def login():
    errors = False
    
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        c = conn.cursor()
        
        if request.method == 'POST':
            uiUsername = request.form.get('username', '').strip()
            uiPassword = request.form.get('password', '').strip()
            next_page = request.args.get('next')
            
            # Validation
            if not uiUsername:
                flash("Username cannot be empty!", "error")
                errors = True
            elif not uiPassword:
                flash("Password cannot be empty!", "error")
                errors = True
            else:
                # Validate username
                c.execute('''
                       SELECT username FROM users WHERE username = ?
                   ''', (uiUsername,))
                dbUsername = c.fetchone()
                
                if not dbUsername:
                    flash("Username not found!", "error")
                    errors = True
            
            if not errors:
                try:
                    # get password
                    c.execute('''
                           SELECT id, password_hash 
                           FROM users 
                           WHERE username = ?
                       ''', (uiUsername,))
                    dbPassword = c.fetchone()
                    user_id = dbPassword[0]
                    pass_hashed = dbPassword[1]
                    
                
                    if check_password_hash(pass_hashed, uiPassword):
                        flash("Login successful!", "success")
                        session['user_id'] = user_id
                        session['username'] = uiUsername

                        return redirect(next_page or url_for('index'))
                    else:
                        flash("Wrong password!", "error")
            
                except sqlite3.DatabaseError:
                        flash("Database error occurred.", "error")
        
    return render_template(
        'login.html',
        errors=errors
    )



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
    


# Index
@app.route('/')
@login_required
def index():
     with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        
        countries = []
        
        c.execute("SELECT id, trip_name, country_id FROM trips")
        
        # Fetch countries for dropdown
        c.execute('''
                SELECT DISTINCT c.id, c.country_name, c.country_code
                FROM countries c
                JOIN trips t ON t.country_id = c.id
                ORDER BY c.id
        ''')
        for r in c.fetchall():
            countries.append({
                'id': r[0],
                'country_name': r[1],
                'country_code': r[2],
                'flag': country_flag(r[2])
            })
    
    
        return render_template(
            'index.html',
            countries=countries
        )

# tripSelection
@app.route('/tripSelection', methods=['GET', 'POST'])
@login_required
def tripSelection():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        
        countries = []

        errors = False
        
        db_trip_name = ''
        ui_trip_name = ''
        start_date = ''
        end_date = ''
        
        # Fetch countries for dropdown
        c.execute('SELECT * FROM countries')
        for r in c.fetchall():
            countries.append({
                'id': r[0],
                'country_name': r[1],
                'country_code': r[2],
                'flag': country_flag(r[2])
            })
        
        if request.method == 'POST':
            country_id = request.form.get('country_id', '').strip()
            ui_trip_name = request.form.get('trip_name', '').strip()
            db_trip_name = ui_trip_name.lower()
            start_date = request.form.get('start_date', '').strip()
            end_date = request.form.get('end_date', '').strip()

            # Validation
            if not ui_trip_name:
                flash("Trip name cannot be empty!", "error")
                errors = True
            elif not country_id:
                flash("Country cannot be empty!", "error")
                errors = True
            elif not start_date:
                flash("Start date cannot be empty!", "error")
                errors = True
            elif not end_date:
                flash("End date cannot be empty!", "error")
                errors = True
            else:
                try:
                    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                    
                    if start_dt > end_dt:
                        flash("End date must be after or equal to start date!", "error")
                        errors = True
                
                except ValueError:
                    flash("Invalid date format!", "error")
                    errors = True
            
            if not errors:
                try:
                    c.execute('''
                        INSERT INTO trips (trip_name, start_date, end_date, country_id) VALUES (?, ?, ?, ?)
                        ''', (db_trip_name, start_date, end_date, country_id)
                    )
                    conn.commit()
                    flash(f'"{ui_trip_name}" added successfully!', 'success')
                    return redirect(url_for('tripSelection'))  # PRG pattern 
                
                except sqlite3.IntegrityError:
                    flash(f'"{ui_trip_name}" already exists!', "error")

        # Refresh trips after potential insertion
        c.execute('''
                SELECT t.id, t.trip_name, t.start_date, t.end_date, c.country_code
                FROM trips t
                JOIN countries c ON t.country_id = c.id

        ''')
        trips_list = c.fetchall()

        
        # Calculate total expenses in base currency for each trip
        trips_with_total = []
        for trip in trips_list:
            trip_start_date = trip[2]
            trip_end_date = trip[3]
            
            # convert DB dates → datetime
            start_dt = datetime.strptime(trip_start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(trip_end_date, "%Y-%m-%d")
            
            start_weekday = start_dt.strftime("%a")
            end_weekday = end_dt.strftime("%a")
            
            trip_id = trip[0]
            c.execute('''
                SELECT SUM(e.amount * r.rate_to_base) 
                FROM expenses e
                JOIN exchange_rates r ON e.currency_id = r.currency_id
                WHERE e.trip_id = ?
            ''', (trip_id,))
            
            row = c.fetchone()
            total_in_base = row[0] if row[0] is not None else 0
            
            trips_with_total.append({
                'id': trip_id,
                'trip_name': trip[1],
                'start_date': trip[2],
                'end_date': trip[3],
                'start_weekday': start_weekday,
                'end_weekday': end_weekday,
                'flag': country_flag(trip[4]),
                'total_in_base': total_in_base
            })

      
        return render_template(
            'tripSelection.html',
            
            countries=countries,
            trips=trips_with_total,
            
            entered_trip_name=ui_trip_name,
            entered_start_date=start_date,
            entered_end_date=end_date
        )

    
# newExpense
@app.route('/newExpense', methods=['GET', 'POST'])
@login_required
def newExpense():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        
        errors = False
        
        trips = []
        row = []
        categories_list = []
        paymentMethods_list = []
        currencies_list = []
        all_expenses = []
        
        category = ''
        payment_method = ''
        item = ''
        amount_str = ''
        currency = ''
        
        # Fetch all trips for dropdown
        c.execute('SELECT id, trip_name FROM trips ORDER BY start_date')
        trips = [{'id': r[0], 'trip_name': r[1]} for r in c.fetchall()]
        
        trip_id = request.args.get('trip_id', type=int)
        if request.method == 'POST':
            flash("Please select a trip before add a new expense!", "error")        
            
        if trip_id:
            # Fetch trip_name, start_date for trip info card
            c.execute('''
                    SELECT t.trip_name, t.start_date, c.country_code
                    FROM trips t
                    JOIN countries c ON t.country_id = c.id
                    WHERE t.id=?
            ''', (trip_id,))
            row = c.fetchone()
            if row:
                row = {
                    'trip_name': row[0],
                    'start_date': row[1],
                    'country_code': row[2],
                    'flag': country_flag(row[2])
                }
            else:
                trip_name = start_date = trip_flag = None
        
            # Fetch categories table for dropdown
            c.execute('SELECT * FROM categories')
            categories_list = c.fetchall()
        
            # Fetch paymentMethods table for dropdown
            c.execute('SELECT * FROM paymentMethods')
            paymentMethods_list = c.fetchall()
        
            # Fetch currencies table for dropdown
            c.execute('SELECT * FROM currencies')
            currencies_list = c.fetchall()
        
            if request.method == 'POST':
            
                purchase_date = request.form.get('purchase_date', '').strip()
                category = request.form.get('category', '').strip()
                payment_method = request.form.get('payment_method', '').strip()
                item = request.form.get('item', '').strip().lower()
                amount_str = request.form.get('amount', '').strip()
                currency = request.form.get('currency', '').strip()
            
                # Validation
                if not purchase_date:
                    flash("Purchase date cannot be empty!", "error")
                    errors = True
                elif not category:
                    flash("Category cannot be empty!", "error")
                    errors = True
                elif not payment_method:
                    flash("Please select a payment method!", "error")
                    errors = True
                elif not item:
                    flash("Item cannot be empty!", "error")
                    errors = True
                elif not amount_str:
                    flash("Amount cannot be empty!", "error")
                    errors = True
                elif not currency:
                    flash("Please select a currency!", "error")
                    errors = True
                else:
                    # Validate "amount" input
                    try:
                        amount = round(float(amount_str), 2)  # 兩位小數
                        if amount <= 0:
                            flash("Amount must be greater than 0!", "error")
                            errors = True
                            
                    except ValueError:
                        flash("Invalid amount!", "error")
                        errors = True
            
                if not errors:
                
                    # Get category ID
                    c.execute('SELECT id FROM categories WHERE cat_name = ?', (category,))
                    category_row = c.fetchone()
                    if not category_row:
                        flash("Invalid category selected!", "error")
                        errors = True
                        
                    else:
                        category_id = category_row[0]

                    # Get payment method ID
                    c.execute('SELECT id FROM paymentMethods WHERE method_name = ?', (payment_method,))
                    payment_row = c.fetchone()
                    if not payment_row:
                        flash("Invalid payment method selected!", "error")
                        errors = True
                    else:
                        payment_id = payment_row[0]

                    # Get currency ID
                    c.execute('SELECT id FROM currencies WHERE code = ?', (currency,))
                    currency_row = c.fetchone()
                    if not currency_row:
                        flash("Invalid currency selected!", "error")
                        errors = True
                    else:
                        currency_id = currency_row[0]
                
                    # Ensure insert successfully or not
                    try:
                        c.execute('''
                            INSERT INTO expenses (trip_id, category_id, method_id, item, amount, currency_id, purchase_date)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (trip_id, category_id, payment_id, item, amount, currency_id, purchase_date))
                        
                        conn.commit()
                        flash("Expense added successfully!", "success")
                        return redirect(url_for('newExpense', trip_id=trip_id))
                    
                    except sqlite3.IntegrityError:
                        flash("Oh no! Something went wrong!", "error")
                        errors = True
                        
        # Fetch expenses only for selected trip
        if trip_id:
            c.execute('''
                SELECT e.id, e.purchase_date, c.cat_name, e.item, e.amount, cu.code, cu.symbol
                FROM expenses e
                JOIN categories c ON e.category_id = c.id
                JOIN currencies cu ON e.currency_id = cu.id
                WHERE trip_id = ? 
                ORDER BY e.purchase_date DESC
            ''', (trip_id,))
            rows = c.fetchall()

            for e in rows:
                all_expenses.append({
                'id': e[0],
                'purchase_date': e[1],
                'category': e[2],
                'item': e[3],
                'amount': e[4],
                'code': e[5],
                'symbol': e[6]
                })
    
        grouped_expenses = {}
    
        for e in all_expenses:
            date = e['purchase_date']
            grouped_expenses.setdefault(date, []).append(e)
    
    return render_template(
        'newExpense.html', 
        errors=errors,
        
        selected_trip=trip_id,
        row=row,
        trips=trips,
        grouped_expenses=grouped_expenses,
        
        categories_list=categories_list,
        paymentMethods_list=paymentMethods_list,
        currencies_list=currencies_list,
        
        entered_category=category,
        entered_paymentMethod=payment_method,
        entered_item=item,
        entered_amount_str=amount_str,
        entered_currency=currency
    )
    

# viewExpense
@app.route('/viewExpense')
@login_required
def viewExpense():
    errors = False
    
    dates = []
    categories = []
    trips = []
    paymentMethods_list = []
    
    expenses = []
    grouped_expenses = {}
    
    trip = None
    payment_method = None
    
    total_in_base = 0

    # Get query parameters
    trip_id = request.args.get('trip_id', type=int)
    selected_date = request.args.get('purchase_date')  # string like "2025-12-19"
    selected_cat = request.args.get('category_name')
    selected_paymentMethod = request.args.get('payment_method')

    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()

            # Fetch all trips for dropdown
            c.execute('SELECT id, trip_name FROM trips ORDER BY id DESC')
            trips = [{'id': r[0], 'trip_name': r[1]} for r in c.fetchall()]

            
            # Fetch for dropdown
            if trip_id:
                # Fetch only purchase dates that exist for this trip
                c.execute('''
                    SELECT DISTINCT purchase_date
                    FROM expenses
                    WHERE trip_id = ?
                    ORDER BY purchase_date
                ''', (trip_id,))
                dates = [r[0] for r in c.fetchall()]
                
                # Fetch all categoies that exist for this trip
                c.execute('''
                    SELECT DISTINCT c.cat_name
                    FROM categories c
                    JOIN expenses e ON e.category_id = c.id
                    WHERE e.trip_id = ?
                    ORDER BY c.order_index
                ''', (trip_id,))
                categories = [r[0] for r in c.fetchall()]
                
                # Fetch all payment methods
                c.execute('''
                    SELECT method_name
                    FROM paymentMethods 
                    ORDER BY id
                ''')
                paymentMethods_list = [r[0] for r in c.fetchall()]

            if trip_id:
                # Fetch trip info if user select a trip
                c.execute('''
                        SELECT t.id, t.trip_name, t.start_date, t.end_date, c.country_code
                        FROM trips t
                        JOIN countries c ON t.country_id = c.id
                        WHERE t.id = ?
                    ''', (trip_id,))
                row = c.fetchone()
                
                if row:
                    start_date = row[2]
                    end_date = row[3]
                    
                    # convert DB dates → datetime
                    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                    
                    start_weekday = start_dt.strftime("%a")
                    end_weekday = end_dt.strftime("%a")
                    
                    trip = {
                        'id': row[0],
                        'trip_name': row[1],
                        'start_date': row[2],
                        'end_date': row[3],
                        'start_weekday': start_weekday,
                        'end_weekday': end_weekday,
                        'flag': country_flag(row[4])
                    }
                else:
                    flash("Trip not found.", "error")
                    trip_id = None  # prevent further queries

            if trip_id:
                # Filter expenses by trip and optionally by selected date
                query = '''
                    SELECT e.id, c.cat_name, e.item, e.amount, cu.code, cu.symbol, r.rate_to_base
                    FROM expenses e
                    JOIN categories c ON e.category_id = c.id
                    JOIN currencies cu ON e.currency_id = cu.id
                    JOIN exchange_rates r ON e.currency_id = r.currency_id
                    JOIN paymentMethods p ON e.method_id = p.id
                    WHERE e.trip_id = ?
                '''
                params = [trip_id]

                if selected_date:
                    query += ' AND e.purchase_date = ?'
                    params.append(selected_date)
                    
                if selected_cat:
                    query += ' AND c.cat_name = ? '
                    params.append(selected_cat)
                    
                if selected_paymentMethod:
                    query += ' AND p.method_name = ? '
                    params.append(selected_paymentMethod)

                query += ' ORDER BY c.order_index'

                c.execute(query, params)
                rows = c.fetchall()

                for e in rows:
                    expense = {
                        'id': e[0],
                        'category': e[1],
                        'item': e[2],
                        'amount': e[3],
                        'code': e[4],
                        'symbol': e[5]
                    }
                    expenses.append(expense)
                    grouped_expenses.setdefault(e[1], []).append(expense)
                    total_in_base += e[3] * e[6]  # sum in base currency

    except NameError:
        flash("Category name not found.", "error")

    except sqlite3.DatabaseError:
        flash("Database error occurred.", "error")

    return render_template(
        'viewExpense.html',

        trips=trips,
        dates=dates,
        categories=categories,
        paymentMethods_list=paymentMethods_list,
        
        trip=trip,
        total_in_base=total_in_base,
        
        selected_trip=trip_id,
        selected_date=selected_date,
        selected_category=selected_cat,
        selected_paymentMethod=selected_paymentMethod,
        
        expenses=expenses,
        grouped_expenses=grouped_expenses
        
    )
    
    

#editTrip
@app.route('/editTrip/<int:trip_id>', methods=['GET', 'POST'])
@login_required
def editTrip(trip_id):
    errors = False
    
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        c = conn.cursor()
        
        c.execute('''
                    SELECT trip_name, start_date, end_date FROM trips WHERE id = ? 
                    ORDER BY start_date
                ''', (trip_id,))
        trip = c.fetchone()
                
        if not trip:
            flash("Trip not found!", "error")
            return redirect(url_for('tripSelection'))
                   
        trip_name, start_date, end_date = trip
            
        if request.method == 'POST':
            new_name = request.form.get('trip_name', '').strip()
            new_start = request.form.get('start_date', '').strip()
            new_end = request.form.get('end_date', '').strip()
            
            if not new_name:
                flash("Trip name cannot be empty!", "error")
                errors = True
            elif not new_start or not new_end:
                flash("Dates cannot be empty!", "error")
                errors = True
            else:
                try:
                    if datetime.strptime(new_start, '%Y-%m-%d') > datetime.strptime(new_end, '%Y-%m-%d'):
                        flash("End date must be after start date!", "error")
                        errors = True
                except:
                    flash("Invalid date format!", "error")
                    errors = True
        
            if not errors:
                c.execute('''
                    UPDATE trips
                    SET trip_name = ?, start_date = ?, end_date = ?
                    WHERE id = ?
                ''', (new_name, new_start, new_end, trip_id))
                conn.commit()
                flash("Trip updated successfully", "success")
                return redirect(url_for('tripSelection'))
            
    return render_template(
        'editTrip.html',
        trip_id=trip_id,
        trip_name=trip_name,
        start_date=start_date,
        end_date=end_date
    )   
    
# deleteTrip
@app.route('/deleteTrip/<int:trip_id>', methods=['POST'])
@login_required
def deleteTrip(trip_id):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        c = conn.cursor()
        
        # Delete trip and its related expenses (if you have a foreign key)
        c.execute('''
                DELETE FROM trips 
                WHERE id = ?
            ''', (trip_id,))
            
        conn.commit()

    return redirect(url_for('tripSelection'))
    
#editExpense
@app.route('/editExpense/<int:trip_id>/<int:expense_id>', methods=['GET', 'POST'])
@login_required
def editExpense(trip_id, expense_id):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        c = conn.cursor()
        
        next_url = request.args.get('next')  # Get the next page from query string
        if not next_url:
            next_url = url_for('newExpense', trip_id=trip_id)
        
        
        errors = False
        expense_info = None
        
        new_purchase_date = ''
        new_category = ''
        new_payment_method = ''
        new_item = ''
        new_amount = ''
        new_currency = ''
        
        if request.method == 'POST':
            new_purchase_date = request.form.get('purchase_date', '').strip()
            new_category = request.form.get('category', '').strip()
            new_payment_method = request.form.get('payment_method', '').strip()
            new_item = request.form.get('item', '').strip()
            new_amount = request.form.get('amount', '').strip()
            new_currency = request.form.get('currency', '').strip()
            
            # Validation
            if not new_purchase_date:
                flash("Purchase date cannot be empty!", "error")
                errors = True
            elif not new_category:
                flash("Category cannot be empty!", "error")
                errors = True
            elif not new_payment_method:
                flash("Please select a payment method!", "error")
                errors = True
            elif not new_item:
                flash("Item cannot be empty!", "error")
                errors = True
            elif not new_amount:
                flash("Amount cannot be empty!", "error")
                errors = True
            elif not new_currency:
                flash("Please select a currency!", "error")
                errors = True
            else:
                # Validate "amount" input
                try:
                    amount = round(float(new_amount), 2)  # 兩位小數
                    if amount <= 0:
                        flash("Amount must be greater than 0!", "error")
                        errors = True
                            
                except ValueError:
                    flash("Invalid amount!", "error")
                    errors = True
            
            if not errors:
               # Lookup IDs for foreign keys
                c.execute('SELECT id FROM categories WHERE cat_name = ?', (new_category,))
                category_row = c.fetchone()
                category_id = category_row[0] if category_row else None

                c.execute('SELECT id FROM paymentMethods WHERE method_name = ?', (new_payment_method,))
                method_row = c.fetchone()
                method_id = method_row[0] if method_row else None

                c.execute('SELECT id FROM currencies WHERE code = ?', (new_currency,))
                currency_row = c.fetchone()
                currency_id = currency_row[0] if currency_row else None

                # Make sure all IDs exist
                if None in [category_id, method_id, currency_id]:
                    flash("Invalid selection!", "error")
                    errors = True

                if not errors:
                    # Now update the expense
                    c.execute('''
                        UPDATE expenses
                        SET purchase_date = ?, category_id = ?, method_id = ?, item = ?, amount = ?, currency_id = ?
                        WHERE id = ?
                    ''', (new_purchase_date, category_id, method_id, new_item, new_amount, currency_id, expense_id))

                    conn.commit()
                    flash("Expense updated successfully!", "success")
                    return redirect(next_url)
        
        
        
        # Fetch categories table for dropdown
        c.execute('SELECT * FROM categories ')
        categories_list = c.fetchall()
        
        # Fetch paymentMethods table for dropdown
        c.execute('SELECT * FROM paymentMethods')
        paymentMethods_list = c.fetchall()
        
        # Fetch currencies table for dropdown
        c.execute('SELECT * FROM currencies')
        currencies_list = c.fetchall()
        
        if expense_id:
            c.execute('''
                SELECT e.purchase_date, ca.cat_name, p.method_name, e.item, e.amount, cu.code
                FROM expenses e
                JOIN categories ca ON e.category_id = ca.id
                JOIN paymentMethods p ON e.method_id = p.id
                JOIN currencies cu ON e.currency_id = cu.id
                
                WHERE e.id = ?
                AND trip_id = ?
            ''', (expense_id, trip_id))
            expense_info = c.fetchone()
        
        return render_template(
        'editExpense.html',
        trip_id=trip_id,
        next_url=next_url,
        
        categories_list=categories_list,
        paymentMethods_list=paymentMethods_list,
        currencies_list=currencies_list,
        
        entered_date=expense_info[0] if expense_info else '',
        entered_category=expense_info[1] if expense_info else '',
        entered_paymentMethod=expense_info[2] if expense_info else '',
        entered_item=expense_info[3] if expense_info else '',
        entered_amount_str=expense_info[4] if expense_info else '',
        entered_currency=expense_info[5] if expense_info else ''
    )
        
    
# deleteExpense
@app.route('/deleteExpense/<int:expense_id>', methods=['POST'])
@login_required
def deleteExpense(expense_id):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        c = conn.cursor()
        
        # Delete expense
        c.execute('DELETE FROM expenses WHERE id = ?', (expense_id,))
        conn.commit()

    return redirect(request.referrer or url_for('tripSelection'))

@app.route('/downloadBackup')
@login_required
def downloadBackup():
    db_path = DB_FILE

    if not os.path.exists(db_path):
        abort(404)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f'expense_backup_{timestamp}.db'

    return send_file(
        db_path,
        as_attachment=True,
        download_name=backup_name,
        mimetype='application/octet-stream'
    )
    
# A helper to generate emoji flags
def country_flag(code):
    if not code or len(code) != 2:
        return ''
    return chr(0x1F1E6 + ord(code[0].upper()) - 65) + \
           chr(0x1F1E6 + ord(code[1].upper()) - 65)

    
    
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
