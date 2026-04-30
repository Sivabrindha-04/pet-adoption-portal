from flask import Flask, render_template, request, redirect, url_for, session ,jsonify
from datetime import date
from db import get_db_connection

app = Flask(__name__)
app.secret_key = "pet_adoption_secret"

# ---------------- LOGIN PAGE ----------------
@app.route('/')
def login_page():
    return render_template("login.html")

#---------------- LOGIN LOGIC -----------------
@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM users WHERE email=%s AND password=%s",
        (email, password)
    )
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if user:
        session['user_id'] = user['user_id']
        session['user_name'] = user['full_name']
        return redirect(url_for('dashboard'))

    return "Invalid login"

# ---------------- REGISTER ----------------
@app.route('/register-page')
def register_page():
    return render_template('register.html')

#-------------- REGISTER LOGIC---------------
@app.route('/register', methods=['POST'])
def register():
    full_name = request.form.get('full_name')
    email = request.form.get('email')
    password = request.form.get('password')

    if not full_name or not email or not password:
        return "All fields required"

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (full_name, email, password) VALUES (%s, %s, %s)",
        (full_name, email, password)
    )
    conn.commit()

    cursor.close()
    conn.close()

    return redirect(url_for('login_page'))


# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return render_template('dashboard.html')

# ---------------- ADD TO WISHLIST ----------------
@app.route('/add-to-wishlist/<int:pet_id>', methods=['POST'])
def add_to_wishlist(pet_id):
    if 'wishlist' not in session:
        session['wishlist'] = []

    if pet_id not in session['wishlist']:
        session['wishlist'].append(pet_id)
        session.modified = True

    return redirect('/wishlist')


# ---------------- VIEW WISHLIST ----------------
@app.route('/wishlist')
def wishlist_page():
    wishlist_ids = session.get('wishlist', [])

    # Dummy pet data (since no database)
    all_pets = [
        {"pet_id":1,"pet_name":"Tommy","breed":"Labrador","price":5000,"image_url":"/static/dog.jpg"},
        {"pet_id":2,"pet_name":"Milo","breed":"Persian Cat","price":4000,"image_url":"/static/cat.jpg"},
        {"pet_id":3,"pet_name":"Bunny","breed":"White Rabbit","price":2000,"image_url":"/static/rabbit.jpg"},
    ]

    pets = [p for p in all_pets if p["pet_id"] in wishlist_ids]

    return render_template('wishlist.html', pets=pets)


# ---------------- REMOVE FROM WISHLIST ----------------
@app.route('/remove-wishlist/<int:pet_id>')
def remove_wishlist(pet_id):
    if 'wishlist' in session and pet_id in session['wishlist']:
        session['wishlist'].remove(pet_id)
        session.modified = True

    return redirect('/wishlist')

#---------------- DONATION ------------------
@app.route('/donate')
def donation_page():
    if 'user_id' not in session:
        return redirect('/')

    return render_template('donation.html')

#---------------- PROCESS DONATION --------------
@app.route('/process-donation', methods=['POST'])
def process_donation():
    name = request.form.get('name')
    email = request.form.get('email')
    amount = request.form.get('amount')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO donations (name, email, amount) VALUES (%s, %s, %s)",
        (name, email, amount)
    )

    conn.commit()
    donation_id = cursor.lastrowid

    cursor.close()
    conn.close()

    return redirect(url_for('donation_receipt', donation_id=donation_id))


#------------------ DONATION RECEIPT ---------------
@app.route('/donation_receipt/<int:donation_id>')
def donation_receipt(donation_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT id, name, email, amount, donation_date FROM donations WHERE id = %s",
        (donation_id,)
    )
    donation = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template("donation_receipt.html", donation=donation)

# ---------------- PET LIST ----------------
@app.route('/pets/dogs')
def dogs():
    return render_template('dogs.html')

@app.route('/pets/cats')
def cats():
    return render_template('cats.html')

@app.route('/pets/rabbits')
def rabbits():
    return render_template('rabbits.html')

@app.route('/pets/hamsters')
def hamsters():
    return render_template('hamsters.html')

@app.route('/pets/birds')
def birds():
    return render_template('birds.html')

# ---------------- ADOPTION FORM PAGE ----------------
@app.route('/adoption')
def adoption():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))

    return render_template('adoption_form.html')

#--------------------SAVE ADOPTION--------------------------------
@app.route('/save-adoption', methods=['POST'])
def save_adoption():

    if 'user_id' not in session:
        return redirect(url_for('login_page'))

    pet_id = request.form['pet_id']
    pet_name = request.form['pet_name']
    pet_breed = request.form['pet_breed']

    name = request.form['user_name']
    email = request.form['user_email']
    phone = request.form['user_phone']
    address = request.form['user_address']

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO adoptions
        (pet_id, pet_name, pet_breed, user_name, user_email, user_phone, user_address)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
    """, (pet_id, pet_name, pet_breed, name, email, phone, address))

    cursor.execute(
        "UPDATE pets SET status='Adopted' WHERE pet_id=%s",
        (pet_id,)
    )

    conn.commit()
    cursor.close()
    conn.close()

    return redirect('/payment')

# ---------------- PAYMENT ----------------
@app.route('/payment', methods=['GET', 'POST'])
def payment():

    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO adoptions (
                user_id,
                pet_name,
                pet_breed,
                pet_price,
                payment_status,
                adoption_date
            )
            VALUES (%s, %s, %s, %s, %s, NOW())
        """, (
            session['user_id'],
            session['pet_name'],
            session['pet_breed'],
            float(session['pet_price']),  # IMPORTANT
            'Paid'
        ))

        conn.commit()
        cursor.close()
        conn.close()

        return redirect('/receipt')

    return render_template('payment.html')

# ---------------- RECEIPT ----------------
@app.route('/receipt')
def receipt():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM adoptions ORDER BY adoption_id DESC LIMIT 1")
    adoption = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template("receipt.html", adoption=adoption)

#----------------- FEEDBACK -------------------
@app.route('/feedback', methods=['POST'])
def feedback():
    name = request.form.get('name')
    email = request.form.get('email')
    message = request.form.get('message')

    # You can store this in DB later
    return redirect('/')


# ---------------- ADMIN LOGIN ----------------
@app.route('/admin')
def admin_login_page():
    return render_template('admin_login.html')

#----------------- ADMIN LOGIN LOGIC -----------
@app.route('/admin-login', methods=['POST'])
def admin_login():
    username = request.form.get('username')
    password = request.form.get('password')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM admin WHERE username=%s AND password=%s",
        (username, password)
    )
    admin = cursor.fetchone()

    cursor.close()
    conn.close()

    if admin:
        session['admin'] = True
        return redirect(url_for('admin_dashboard'))

    return "Invalid Admin Login"

# ---------------- ADMIN DASHBOARD ----------------
@app.route('/admin-dashboard')
def admin_dashboard():
    conn=get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS total FROM pets")
    total_pets = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) AS adopted FROM pets WHERE status='Adopted'")
    adopted_pets = cursor.fetchone()['adopted']

    cursor.execute("SELECT COUNT(*) AS users FROM users")
    total_users = cursor.fetchone()['users']

    return render_template(
        "admin_dashboard.html",
        total_pets=total_pets,
        adopted_pets=adopted_pets,
        total_users=total_users
    )

#------------- ADMIN-MANAGE PETS ------------------
# ---------------- ADMIN PET LIST ----------------
@app.route('/admin-pets')
def admin_pets():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM pets")
    pets = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_pets.html', pets=pets)

# ---------------- ADD PET ----------------
@app.route('/add-pet', methods=['GET', 'POST'])
def add_pet():
    if request.method == 'POST':
        name = request.form['pet_name']   # form field can still be pet_name
        breed = request.form['breed']
        age = request.form['age']
        price = request.form['price']
        status = request.form['status']

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO pets (name, breed, age, price, status)
            VALUES (%s,%s,%s,%s,%s)
        """, (name, breed, age, price, status))

        conn.commit()
        cursor.close()
        conn.close()

        return redirect('/admin-pets')

    return render_template('add_pet.html')

# ---------------- EDIT PET ----------------
@app.route('/edit-pet/<int:pet_id>', methods=['GET', 'POST'])
def edit_pet(pet_id):

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        name = request.form['pet_name']
        breed = request.form['breed']
        age = request.form['age']
        price = request.form['price']
        status = request.form['status']

        cursor.execute("""
            UPDATE pets
            SET name=%s, breed=%s, age=%s, price=%s, status=%s
            WHERE pet_id=%s
        """, (name, breed, age, price, status, pet_id))

        conn.commit()
        cursor.close()
        conn.close()

        return redirect('/admin-pets')

    cursor.execute("SELECT * FROM pets WHERE pet_id=%s", (pet_id,))
    pet = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template('edit_pet.html', pet=pet)

# ---------------- DELETE PET ----------------
@app.route('/delete-pet/<int:pet_id>')
def delete_pet(pet_id):

    if 'admin' not in session:
        return redirect('/admin')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM pets WHERE pet_id=%s", (pet_id,))
    conn.commit()

    cursor.close()
    conn.close()

    return redirect('/admin-pets')


# ---------------- ADMIN VIEW ADOPTIONS ----------------
@app.route('/admin-adoptions')
def admin_adoptions():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM adoptions")
    adoptions = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("admin_adoption.html", adoptions=adoptions)

#----------------- ADMIN-USERS ---------------
@app.route('/admin-users')
def admin_users():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT user_id, full_name, email FROM users")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_users.html', users=users)

#----------------- ADMIN-DONATION ----------------
@app.route('/admin-donation')
def admin_donation():
    conn=get_db_connection()
    cursor=conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, name, email, amount, donation_date
        FROM donations
        ORDER BY donation_date DESC
    """)
    donations=cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_donation.html', donations=donations)

# ---------------- LOGOUT ----------------
@app.route('/admin-login')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)