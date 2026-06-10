from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
import os
import random
from datetime import datetime, timedelta, time
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = '# Set your secret key here'

# ---------------- UPLOAD CONFIG ----------------
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ---------------- DATABASE CONNECTION FUNCTION ----------------
def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='root123',
        database='your_db'
    )

# ---------------- IS VOTING OPEN ----------------

def is_voting_open(election):
    if not election:
        return False

    now = datetime.now()
    today = now.date()
    current_time = now.time()

    status = election.get('status')
    result_declared = election.get('result_declared', 0)
    start_date = election.get('start_date')
    end_date = election.get('end_date')
    start_time = election.get('start_time')
    end_time = election.get('end_time')

    # status aur final result check
    if status != 'started' or result_declared == 1:
        return False

    # date range check
    if start_date and today < start_date:
        return False

    if end_date and today > end_date:
        return False

    # time range check
    if start_time and end_time:
        # MySQL TIME kabhi timedelta ban ke aata hai, handle karne ke liye
        if hasattr(start_time, 'total_seconds'):
            total_seconds = int(start_time.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            start_time = time(hours, minutes)

        if hasattr(end_time, 'total_seconds'):
            total_seconds = int(end_time.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            end_time = time(hours, minutes)

        if current_time < start_time or current_time > end_time:
            return False

    return True

# ---------------- HELPER: FUNCTION ----------------
def get_candidate_election_type(admin_election_type):
    if admin_election_type.strip().lower() == 'lok sabha':
        return 'Lok Sabha (General Election)'
    elif admin_election_type.strip().lower() == 'vidhan sabha':
        return 'Vidhan Sabha (State Election)'
    return admin_election_type

# ---------------- HELPER: GENERATE UNIQUE 4-DIGIT VOTER ID ----------------
def generate_unique_voter_id():
    db = get_db_connection()
    cursor = db.cursor(buffered=True)

    while True:
        voter_id = str(random.randint(1000, 9999))
        cursor.execute("SELECT id FROM users WHERE voter_id=%s", (voter_id,))
        existing = cursor.fetchone()
        if not existing:
            cursor.close()
            db.close()
            return voter_id

# ---------------- HELPER: GET LOGGED IN USER DETAILS ----------------
def get_logged_in_user(username):
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("""
        SELECT voter_id, full_name, father_name, username, email, age, gender, address, mobile_number, status
        FROM users
        WHERE username=%s
    """, (username,))
    user_data = cursor.fetchone()
    cursor.close()
    db.close()

    if not user_data:
        return None

    return {
        'voter_id': user_data[0],
        'full_name': user_data[1],
        'father_name': user_data[2],
        'username': user_data[3],
        'email': user_data[4],
        'age': user_data[5],
        'gender': user_data[6],
        'address': user_data[7],
        'mobile_number': user_data[8],
        'status': user_data[9]
    }
def generate_unique_voter_id():
    import random
    db = get_db_connection()
    cursor = db.cursor(buffered=True)

    while True:
        voter_id = str(random.randint(1000, 9999))
        cursor.execute("SELECT id FROM users WHERE voter_id=%s", (voter_id,))
        if not cursor.fetchone():
            cursor.close()
            db.close()
            return voter_id
        
# ---------------- HELPER: Is Any Election Live ----------------
def is_any_election_live():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT start_date, end_date, start_time, end_time FROM elections")
    elections = cursor.fetchall()

    cursor.close()
    db.close()

    now = datetime.now()

    for e in elections:
        start_time = e['start_time']
        end_time = e['end_time']

        if isinstance(start_time, timedelta):
            total_seconds = int(start_time.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            start_time = datetime.strptime(f"{hours}:{minutes}", "%H:%M").time()
        elif isinstance(start_time, datetime):
            start_time = start_time.time()

        if isinstance(end_time, timedelta):
            total_seconds = int(end_time.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            end_time = datetime.strptime(f"{hours}:{minutes}", "%H:%M").time()
        elif isinstance(end_time, datetime):
            end_time = end_time.time()

        start_datetime = datetime.combine(e['start_date'], start_time)
        end_datetime = datetime.combine(e['end_date'], end_time)

        if start_datetime <= now <= end_datetime:
            return True

    return False

# ---------------- HOME ----------------
@app.route('/')
def index():
    return render_template('index.html')

# ---------------- VIEW ELECTION ----------------
from datetime import datetime, timedelta
@app.route('/election')
def election():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM elections ORDER BY id ASC")
    elections = cursor.fetchall()

    now = datetime.now()

    for e in elections:

        # ✅ TIME FIX (IMPORTANT)
        if isinstance(e['start_time'], timedelta):
            total_seconds = int(e['start_time'].total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            e['start_time'] = datetime.strptime(f"{hours}:{minutes}", "%H:%M").time()

        if isinstance(e['end_time'], timedelta):
            total_seconds = int(e['end_time'].total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            e['end_time'] = datetime.strptime(f"{hours}:{minutes}", "%H:%M").time()

        # ✅ SAFE DATETIME (NULL ERROR NA AAYE)
        if e['start_date'] and e['end_date'] and e['start_time'] and e['end_time']:

            start_datetime = datetime.combine(e['start_date'], e['start_time'])
            end_datetime = datetime.combine(e['end_date'], e['end_time'])

            if e['result_declared'] == 1:
                e['live_status'] = 'declared'

            elif e['status'] != 'started':
                e['live_status'] = 'closed'

            elif now < start_datetime:
                e['live_status'] = 'upcoming'

            elif now > end_datetime:
                e['live_status'] = 'closed'

            else:
                e['live_status'] = 'started'
        else:
            e['live_status'] = 'closed'

    cursor.close()
    db.close()

    return render_template('election.html', elections=elections)

# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        full_name = request.form['full_name']
        father_name = request.form['father_name']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        age = request.form['age']
        gender = request.form['gender']
        address = request.form['address']
        mobile_number = request.form['mobile_number']
        document = request.files['document']

        if password != confirm_password:
            return render_template('register.html', error="Password and Confirm Password do not match.")

        if int(age) < 18:
            return render_template('register.html', error="Age must be 18 or above to register.")

        if len(mobile_number) != 10 or not mobile_number.isdigit():
            return render_template('register.html', error="Mobile number must be exactly 10 digits.")

        if document.filename == '':
            return render_template('register.html', error="Please upload an identification document.")

        if not allowed_file(document.filename):
            return render_template('register.html', error="Only PNG, JPG, JPEG and PDF files are allowed.")

        db = get_db_connection()
        cursor = db.cursor(buffered=True)

        # duplicate check
        cursor.execute(
            "SELECT id FROM users WHERE email=%s OR username=%s OR mobile_number=%s",
            (email, username, mobile_number)
        )
        existing_user = cursor.fetchone()

        if existing_user:
            cursor.close()
            db.close()
            return render_template('register.html', error="Email, Username, or Mobile Number already exists.")

        # save document
        filename = secure_filename(document.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        counter = 1
        original_name, extension = os.path.splitext(filename)
        while os.path.exists(filepath):
            filename = f"{original_name}_{counter}{extension}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            counter += 1

        document.save(filepath)

        cursor.execute("""
            INSERT INTO users (
                voter_id, full_name, father_name, email, username, password,
                age, gender, address, mobile_number, document, status, has_voted
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            None,
            full_name,
            father_name,
            email,
            username,
            password,
            age,
            gender,
            address,
            mobile_number,
            filepath,
            'pending',
            False
        ))

        db.commit()
        cursor.close()
        db.close()

        return render_template('register.html', success="Registration submitted successfully. Please wait for admin approval.")

    return render_template('register.html')

# ---------------- DEFAULT LOGIN REDIRECT ----------------
@app.route('/login')
def login():
    return redirect(url_for('admin_login'))

# ---------------- ADMIN LOGIN ----------------
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if (username == "admin" and password == "admin@123") or \
           (username == "admin2" and password == "admin@1234"):
            session['admin'] = username
            return redirect(url_for('admin'))
        else:
            return render_template('login.html', error_message="Only admin can login")

    return render_template('login.html')

# ---------------- USER LOGIN ----------------
@app.route('/user_login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db_connection()
        cursor = db.cursor(buffered=True)
        cursor.execute("""
            SELECT username, status
            FROM users
            WHERE username=%s AND password=%s
        """, (username, password))
        user = cursor.fetchone()
        cursor.close()
        db.close()

        if user:
            if user[1] == 'pending':
                return render_template('user_login.html', error_message="Your registration is pending admin approval.")
            elif user[1] == 'rejected':
                return render_template('user_login.html', error_message="Your registration has been rejected.")
            elif user[1] == 'approved':
                session['username'] = username
                return redirect(url_for('dashboard'))

        return render_template('user_login.html', error_message="Invalid username or password")

    return render_template('user_login.html')

# ---------------- PARTY LOGIN ----------------
@app.route('/party_login', methods=['GET', 'POST'])
def party_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db_connection()
        cursor = db.cursor(buffered=True)

        cursor.execute(
            "SELECT username, status FROM parties WHERE username=%s AND password=%s",
            (username, password)
        )
        party = cursor.fetchone()

        cursor.close()
        db.close()

        if party:
            status = party[1]

            if status == 'approved':
                session['party'] = username
                return redirect(url_for('party_dashboard'))

            elif status == 'pending':
                return render_template('party_login.html', error="Your account is not approved yet.")

            elif status == 'rejected':
                return render_template('party_login.html', error="Your request was rejected.")

        else:
            return render_template('party_login.html', error="Invalid username or password")

    return render_template('party_login.html')

# ---------------- PARTY DASHBOARD ----------------
@app.route('/party_dashboard')
def party_dashboard():
    if 'party' not in session:
        return redirect(url_for('party_login'))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, party_name, leader_name, email, username, document, status
        FROM parties
        WHERE username = %s
    """, (session['party'],))

    party = cursor.fetchone()

    cursor.close()
    db.close()

    if not party:
        session.pop('party', None)
        return redirect(url_for('party_login'))

    return render_template('party_dashboard.html', party=party)

# ---------------- PARTY ADD CANDIDATE ----------------
@app.route('/party_add_candidate', methods=['GET', 'POST'])
def party_add_candidate():
    if 'party' not in session:
        return redirect(url_for('party_login'))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT party_name, username
        FROM parties
        WHERE username = %s
    """, (session['party'],))
    party = cursor.fetchone()

    if not party:
        cursor.close()
        db.close()
        session.pop('party', None)
        return redirect(url_for('party_login'))

    if request.method == 'POST':
        candidate_name = request.form['candidate_name']
        party_name = request.form['party_name']
        age = request.form['age']
        gender = request.form['gender']
        election_type = request.form['election_type']

        cursor.execute("""
            INSERT INTO candidates (candidates_name, party, age, gender, election_type)
            VALUES (%s, %s, %s, %s, %s)
        """, (candidate_name, party_name, age, gender, election_type))
        db.commit()

        cursor.close()
        db.close()

        return render_template(
            'party_add_candidate.html',
            party=party,
            message="Candidate added successfully."
        )
    cursor.close()
    db.close()
    return render_template('party_add_candidate.html', party=party)

# ---------------- PARTY MANAGE CANDIDATE ----------------
@app.route('/party_manage_candidate')
def party_manage_candidate():
    if 'party' not in session:
        return redirect(url_for('party_login'))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # logged-in party ka name nikaalo
    cursor.execute("""
        SELECT party_name
        FROM parties
        WHERE username = %s
    """, (session['party'],))
    party = cursor.fetchone()

    if not party:
        cursor.close()
        db.close()
        session.pop('party', None)
        return redirect(url_for('party_login'))

    # sirf us party ke candidates lao
    cursor.execute("""
        SELECT id, candidates_name, party, age, gender, election_type
        FROM candidates
        WHERE party = %s
        ORDER BY id ASC
    """, (party['party_name'],))
    candidates = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template('party_manage_candidate.html', candidates=candidates)

# ---------------- REMOVE PARTY CANDIDATE ----------------
@app.route('/party_remove_candidate/<int:candidate_id>')
def party_remove_candidate(candidate_id):
    if 'party' not in session:
        return redirect(url_for('party_login'))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # logged-in party ka name
    cursor.execute("""
        SELECT party_name
        FROM parties
        WHERE username = %s
    """, (session['party'],))
    party = cursor.fetchone()

    if not party:
        cursor.close()
        db.close()
        session.pop('party', None)
        return redirect(url_for('party_login'))

    # sirf apni party ka candidate hi remove ho
    cursor.execute("""
        DELETE FROM candidates
        WHERE id = %s AND party = %s
    """, (candidate_id, party['party_name']))

    db.commit()
    cursor.close()
    db.close()

    return redirect(url_for('party_manage_candidate'))

# ---------------- RESULT FOR PARTY ----------------
@app.route('/results')
def results():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT candidates_name, party, age, gender, votes
        FROM candidates
        WHERE election_type = 'Lok Sabha (General Election)'
        ORDER BY votes DESC
    """)
    loksabha = cursor.fetchall()

    cursor.execute("""
        SELECT candidates_name, party, age, gender, votes
        FROM candidates
        WHERE election_type = 'Vidhan Sabha (State Election)'
        ORDER BY votes DESC
    """)
    vidhansabha = cursor.fetchall()

    cursor.execute("""
        SELECT id, election_name, election_type, status, result_declared
        FROM elections
        ORDER BY id ASC
    """)
    elections = cursor.fetchall()

    loksabha_info = None
    vidhansabha_info = None

    for e in elections:
        if e['election_type'].strip().lower() == 'lok sabha':
            loksabha_info = e
        elif e['election_type'].strip().lower() == 'vidhan sabha':
            vidhansabha_info = e
    winner_loksabha = loksabha[0] if loksabha and loksabha_info and loksabha_info['result_declared'] == 1 else None
    winner_vidhansabha = vidhansabha[0] if vidhansabha and vidhansabha_info and vidhansabha_info['result_declared'] == 1 else None
    cursor.close()
    db.close()

    return render_template(
    'results.html',
    loksabha=loksabha,
    vidhansabha=vidhansabha,
    loksabha_info=loksabha_info,
    vidhansabha_info=vidhansabha_info,
    winner_loksabha=winner_loksabha,
    winner_vidhansabha=winner_vidhansabha
)
    
# ---------------- PARTY REGISTER ----------------
@app.route('/party_register', methods=['GET', 'POST'])
def party_register():
    if request.method == 'POST':
        party_name = request.form['party_name']
        leader_name = request.form['leader_name']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']

        if 'document' not in request.files:
            return render_template('party_register.html', message="Please upload a document.")

        file = request.files['document']

        if file.filename == '':
            return render_template('party_register.html', message="Please select a document file.")

        if not allowed_file(file.filename):
            return render_template('party_register.html', message="Only PNG, JPG, JPEG, PDF files are allowed.")

        db = get_db_connection()
        cursor = db.cursor(buffered=True)

        # check duplicate username
        cursor.execute("SELECT username FROM parties WHERE username = %s", (username,))
        if cursor.fetchone():
            cursor.close()
            db.close()
            return render_template('party_register.html', message="Username already exists.")

        # save file
        filename = secure_filename(file.filename)
        unique_filename = f"{random.randint(1000,9999)}_{filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))

        # insert party
        cursor.execute("""
            INSERT INTO parties (party_name, leader_name, email, username, password, document, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'pending')
        """, (party_name, leader_name, email, username, password, unique_filename))

        db.commit()
        cursor.close()
        db.close()

        return render_template(
            'party_login.html',
            message="Registration submitted successfully. Wait for admin approval."
        )

    return render_template('party_register.html')

# ---------------- CANDIDATES ----------------
@app.route('/candidates')
def candidates():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT id, candidates_name, party, age, COALESCE(votes,0) FROM candidates")
    candidates = cursor.fetchall()
    cursor.close()
    db.close()

    return render_template('candidates.html', candidates=candidates)

# ---------------- AVAILABLE CANDIDATES FOR USER ----------------
@app.route('/available_candidates')
def available_candidates():
    if 'username' not in session:
        return redirect(url_for('user_login'))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT candidates_name, party, age, gender
        FROM candidates
        WHERE election_type = 'Lok Sabha (General Election)'
        ORDER BY candidates_name ASC
    """)
    loksabha = cursor.fetchall()

    cursor.execute("""
        SELECT candidates_name, party, age, gender
        FROM candidates
        WHERE election_type = 'Vidhan Sabha (State Election)'
        ORDER BY candidates_name ASC
    """)
    vidhansabha = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        'available_candidates.html',
        loksabha=loksabha,
        vidhansabha=vidhansabha
    )

# ---------------- USERS ----------------
@app.route('/users')
def users():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, voter_id, full_name, father_name, username, email, age, gender,
               address, mobile_number, document, status, has_voted
        FROM users
        ORDER BY id ASC
    """)
    users = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template('users.html', users=users)

# ---------------- Manage Voters ----------------
@app.route('/manage_voters')
def manage_voters():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, full_name, father_name, username, mobile_number, age, gender, voter_id, status, document
        FROM users
        ORDER BY id ASC
    """)
    users = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template('voters_remove.html', users=users)

# ---------------- Remove Voters ----------------
@app.route('/delete_user/<int:user_id>')
def delete_user(user_id):
    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    db.commit()

    cursor.close()
    db.close()

    return redirect(url_for('manage_voters'))

# ---------------- ADMIN APPROVE USER ----------------
@app.route('/approve_user/<int:user_id>')
def approve_user(user_id):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    db = get_db_connection()
    cursor = db.cursor(buffered=True)

    voter_id = generate_unique_voter_id()

    cursor.execute("""
        UPDATE users
        SET voter_id=%s, status='approved'
        WHERE id=%s
    """, (voter_id, user_id))

    db.commit()
    cursor.close()
    db.close()

    return redirect(url_for('users'))

# ---------------- ADMIN REJECT USER ----------------
@app.route('/reject_user/<int:user_id>')
def reject_user(user_id):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    db = get_db_connection()
    cursor = db.cursor(buffered=True)

    cursor.execute("""
        UPDATE users
        SET status='rejected'
        WHERE id=%s
    """, (user_id,))

    db.commit()
    cursor.close()
    db.close()

    return redirect(url_for('users'))

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('user_login'))

    user = get_logged_in_user(session['username'])
    if not user:
        session.pop('username', None)
        return redirect(url_for('user_login'))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT election_type, status, result_declared, start_date, end_date, start_time, end_time
        FROM elections
    """)
    elections = cursor.fetchall()

    cursor.close()
    db.close()

    status_map = {}

    for e in elections:
        etype = e['election_type'].strip().lower()

        if e['result_declared'] == 1:
            final_status = 'declared'
        elif is_voting_open(e):
            final_status = 'started'
        else:
            final_status = 'closed'

        if etype == 'lok sabha':
            status_map['general'] = final_status
        elif etype == 'vidhan sabha':
            status_map['state'] = final_status

    return render_template(
        'dashboard.html',
        data=get_election_data(),
        user=user,
        status_map=status_map,
        election_live=(status_map.get('general') == 'started' or status_map.get('state') == 'started')
    )
            
# ---------------- ADMIN ----------------
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        name = request.form['candidate_name']
        party = request.form['party_name']
        age = request.form['age']

        db = get_db_connection()
        cursor = db.cursor(buffered=True)
        cursor.execute(
            "INSERT INTO candidates (candidates_name, party, age) VALUES (%s,%s,%s)",
            (name, party, age)
        )
        db.commit()
        cursor.close()
        db.close()

        return render_template('admin.html', error_message="Candidate added")

    return render_template('admin.html')

# ---------------- PARTY VERIFICATION ----------------
@app.route('/manage_parties')
def manage_parties():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    db = get_db_connection()
    cursor = db.cursor(buffered=True)

    cursor.execute("""
        SELECT id, party_name, leader_name, email, username, document, status
        FROM parties
        ORDER BY id ASC
    """)
    parties = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template('manage_parties.html', parties=parties)

# ---------------- APPROVE PARTY ----------------
@app.route('/approve_party/<int:party_id>')
def approve_party(party_id):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    db = get_db_connection()
    cursor = db.cursor(buffered=True)

    cursor.execute("UPDATE parties SET status='approved' WHERE id=%s", (party_id,))
    db.commit()

    cursor.close()
    db.close()

    return redirect(url_for('manage_parties'))

# ---------------- REJECT PARTY ----------------
@app.route('/reject_party/<int:party_id>')
def reject_party(party_id):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    db = get_db_connection()
    cursor = db.cursor(buffered=True)

    cursor.execute("UPDATE parties SET status='rejected' WHERE id=%s", (party_id,))
    db.commit()

    cursor.close()
    db.close()

    return redirect(url_for('manage_parties'))

# ---------------- Manage Election - Remove Party ----------------
@app.route('/remove_party_page')
def remove_party_page():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, party_name, leader_name, email, username, document, status
        FROM parties
        ORDER BY id ASC
    """)
    parties = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template('remove_party.html', parties=parties)

# ---------------- Manage Election - Delete Party ----------------
@app.route('/delete_party/<int:party_id>')
def delete_party(party_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # pehle party name nikaalo
    cursor.execute("SELECT party_name FROM parties WHERE id = %s", (party_id,))
    party = cursor.fetchone()

    if party:
        party_name = party['party_name']

        # pehle us party ke candidates delete karo
        cursor.execute("DELETE FROM candidates WHERE party = %s", (party_name,))

        # fir party delete karo
        cursor.execute("DELETE FROM parties WHERE id = %s", (party_id,))
        db.commit()

    cursor.close()
    db.close()

    return redirect(url_for('remove_party_page'))

# ---------------- ADMIN - ELECTION CONTROL START ELECTION ----------------
@app.route('/start_election/<int:election_id>')
def start_election(election_id):
    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("UPDATE elections SET status='started' WHERE id=%s", (election_id,))
    db.commit()

    cursor.close()
    db.close()
    return redirect(url_for('manage_elections'))

# ---------------- ADMIN - ELECTION CONTROL STOP ELECTION ----------------
@app.route('/stop_election/<int:election_id>')
def stop_election(election_id):
    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("UPDATE elections SET status='stopped' WHERE id=%s", (election_id,))
    db.commit()

    cursor.close()
    db.close()
    return redirect(url_for('manage_elections'))

# ---------------- ADMIN: MANAGE ELECTIONS SCHEDULE ----------------
@app.route('/update_election_schedule/<int:election_id>', methods=['POST'])
def update_election_schedule(election_id):
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("""
        UPDATE elections
        SET start_date=%s, end_date=%s, start_time=%s, end_time=%s
        WHERE id=%s
    """, (start_date, end_date, start_time, end_time, election_id))

    db.commit()
    cursor.close()
    db.close()

    return redirect(url_for('manage_elections'))

# ---------------- ADMIN: MANAGE ELECTIONS ----------------
@app.route('/admin/elections', methods=['GET', 'POST'])
def manage_elections():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    if request.method == 'POST':
        election_id = request.form['election_id']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        start_time = request.form['start_time']
        end_time = request.form['end_time']

        cursor.execute("""
            UPDATE elections
            SET start_date=%s, end_date=%s, start_time=%s, end_time=%s
            WHERE id=%s
        """, (start_date, end_date, start_time, end_time, election_id))
        db.commit()

        cursor.close()
        db.close()
        return redirect(url_for('manage_elections'))

    cursor.execute("SELECT * FROM elections ORDER BY id ASC")
    elections = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template('manage_elections.html', elections=elections)

# ---------------- ADMIN: RESULT CONTROL ----------------
@app.route('/admin/control_results')
def control_results():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # elections table se status + result_declared lao
    cursor.execute("SELECT id, election_name, election_type, status, result_declared FROM elections ORDER BY id ASC")
    elections = cursor.fetchall()

    loksabha_info = None
    vidhansabha_info = None

    for e in elections:
        if e['election_type'].strip().lower() == 'lok sabha':
            loksabha_info = e
        elif e['election_type'].strip().lower() == 'vidhan sabha':
            vidhansabha_info = e

    cursor.execute("""
        SELECT candidates_name, party, age, gender, votes
        FROM candidates
        WHERE election_type = 'Lok Sabha (General Election)'
        ORDER BY votes DESC
    """)
    loksabha = cursor.fetchall()

    cursor.execute("""
        SELECT candidates_name, party, age, gender, votes
        FROM candidates
        WHERE election_type = 'Vidhan Sabha (State Election)'
        ORDER BY votes DESC
    """)
    vidhansabha = cursor.fetchall()
    winner_loksabha = loksabha[0] if loksabha and loksabha_info and loksabha_info['result_declared'] == 1 else None
    winner_vidhansabha = vidhansabha[0] if vidhansabha and vidhansabha_info and vidhansabha_info['result_declared'] == 1 else None
    cursor.close()
    db.close()

    return render_template(
        'control_results.html',
        loksabha=loksabha,
        vidhansabha=vidhansabha,
        loksabha_info=loksabha_info,
        vidhansabha_info=vidhansabha_info,
        winner_loksabha=winner_loksabha,
        winner_vidhansabha=winner_vidhansabha
)
        
 # ---------------- ADMIN: DECLARE RESULT ----------------
@app.route('/declare_result/<int:election_id>')
def declare_result(election_id):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    db = get_db_connection()
    cursor = db.cursor()

    # result final + voting stop
    cursor.execute("""
        UPDATE elections
        SET result_declared = 1, status = 'stopped'
        WHERE id = %s
    """, (election_id,))
    db.commit()

    cursor.close()
    db.close()

    return redirect(url_for('control_results'))

  # ---------------- RESET RESULT ----------------
@app.route('/reset_result/<int:election_id>')
def reset_result(election_id):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT election_type FROM elections WHERE id = %s", (election_id,))
    election = cursor.fetchone()

    if election:
        candidate_election_type = get_candidate_election_type(election['election_type'])

        # votes reset
        cursor.execute("""
            UPDATE candidates
            SET votes = 0
            WHERE election_type = %s
        """, (candidate_election_type,))

        # 🔥 FIXED LINE
        cursor.execute("""
            UPDATE elections
            SET result_declared = 0, status = 'started'
            WHERE id = %s
        """, (election_id,))

        # user voting reset
        if election['election_type'].strip().lower() == 'lok sabha':
            cursor.execute("UPDATE users SET voted_general = 0")
        elif election['election_type'].strip().lower() == 'vidhan sabha':
            cursor.execute("UPDATE users SET voted_state = 0")

        db.commit()

    cursor.close()
    db.close()

    return redirect(url_for('control_results'))
        
# ---------------- REMOVE CANDIDATE ----------------
@app.route('/cancel', methods=['GET', 'POST'])
def cancel():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    if request.method == "POST":
        candidate_id = request.form['candidate_id']

        db = get_db_connection()
        cursor = db.cursor(buffered=True)

        cursor.execute("SELECT * FROM candidates WHERE id=%s", (candidate_id,))
        if not cursor.fetchone():
            cursor.close()
            db.close()
            return render_template('cancel.html', message="Candidate not found")

        cursor.execute("DELETE FROM candidates WHERE id=%s", (candidate_id,))
        db.commit()
        cursor.close()
        db.close()

        return render_template('cancel.html', message="Candidate deleted successfully")

    return render_template('cancel.html')

# ---------------- PROFILE ----------------
@app.route('/profile')
def profile():
    if 'username' not in session:
        return redirect(url_for('user_login'))

    user = get_logged_in_user(session['username'])
    if user:
        return render_template('profile.html', user=user)

    session.pop('username', None)
    return redirect(url_for('user_login'))

# ---------------- VOTER CARD ----------------
@app.route('/voter_card')
def voter_card():
    if 'username' not in session:
        return redirect(url_for('user_login'))

    user = get_logged_in_user(session['username'])
    if not user:
        session.pop('username', None)
        return redirect(url_for('user_login'))

    return render_template('voter_card.html', user=user)

# ---------------- VOTE GENERAL ----------------
@app.route('/vote_general', methods=['GET', 'POST'])
def vote_general():
    if 'username' not in session:
        return redirect(url_for('user_login'))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT status, result_declared, start_date, end_date, start_time, end_time
        FROM elections
        WHERE election_type=%s
    """, ('Lok Sabha',))
    election = cursor.fetchone()

    if not election:
        cursor.execute("""
            SELECT status, result_declared, start_date, end_date, start_time, end_time
            FROM elections
            WHERE election_type=%s
        """, ('Lok Sabha (General Election)',))
        election = cursor.fetchone()

    if not is_voting_open(election):
        cursor.close()
        db.close()
        return "Voting is currently closed for General Election"

    cursor.execute("SELECT voted_general FROM users WHERE username=%s", (session['username'],))
    user = cursor.fetchone()

    if not user:
        cursor.close()
        db.close()
        session.pop('username', None)
        return redirect(url_for('user_login'))

    if user['voted_general'] == 1:
        cursor.close()
        db.close()
        return render_template('already_voted.html')

    if request.method == 'POST':
        candidate_id = request.form['candidate_id']

        cursor.execute(
            "UPDATE candidates SET votes = COALESCE(votes, 0) + 1 WHERE id=%s",
            (candidate_id,)
        )
        cursor.execute(
            "UPDATE users SET voted_general = 1 WHERE username=%s",
            (session['username'],)
        )
        db.commit()

        cursor.close()
        db.close()
        return render_template('vote_success.html')

    cursor.execute("""
        SELECT id, candidates_name, party, age, gender
        FROM candidates
        WHERE election_type = 'Lok Sabha (General Election)'
        ORDER BY id ASC
    """)
    candidates = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template('vote_general.html', candidates=candidates)

# ---------------- VOTE STATE ----------------
@app.route('/vote_state', methods=['GET', 'POST'])
def vote_state():
    if 'username' not in session:
        return redirect(url_for('user_login'))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT status, result_declared, start_date, end_date, start_time, end_time
        FROM elections
        WHERE election_type=%s
    """, ('Vidhan Sabha',))
    election = cursor.fetchone()

    if not election:
        cursor.execute("""
            SELECT status, result_declared, start_date, end_date, start_time, end_time
            FROM elections
            WHERE election_type=%s
        """, ('Vidhan Sabha (State Election)',))
        election = cursor.fetchone()

    if not is_voting_open(election):
        cursor.close()
        db.close()
        return "Voting is currently closed for State Election"

    cursor.execute("SELECT voted_state FROM users WHERE username=%s", (session['username'],))
    user = cursor.fetchone()

    if not user:
        cursor.close()
        db.close()
        session.pop('username', None)
        return redirect(url_for('user_login'))

    if user['voted_state'] == 1:
        cursor.close()
        db.close()
        return render_template('already_voted.html')

    if request.method == 'POST':
        candidate_id = request.form['candidate_id']

        cursor.execute(
            "UPDATE candidates SET votes = COALESCE(votes, 0) + 1 WHERE id=%s",
            (candidate_id,)
        )
        cursor.execute(
            "UPDATE users SET voted_state = 1 WHERE username=%s",
            (session['username'],)
        )
        db.commit()

        cursor.close()
        db.close()
        return render_template('vote_success.html')

    cursor.execute("""
        SELECT id, candidates_name, party, age, gender
        FROM candidates
        WHERE election_type = 'Vidhan Sabha (State Election)'
        ORDER BY id ASC
    """)
    candidates = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template('vote_state.html', candidates=candidates)

# ---------------- VOTE ----------------
@app.route('/vote', methods=['GET', 'POST'])
def vote():
    if 'username' not in session:
        return redirect(url_for('user_login'))

    # Election live check
    if not is_any_election_live():
        user = get_logged_in_user(session['username'])
        if not user:
            session.pop('username', None)
            return redirect(url_for('user_login'))

        return render_template(
            'dashboard.html',
            data=get_election_data(),
            user=user,
            election_live=False,
            vote_closed=True
        )

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT username, status, has_voted
        FROM users
        WHERE username=%s
    """, (session['username'],))
    current_user = cursor.fetchone()

    if not current_user:
        cursor.close()
        db.close()
        session.pop('username', None)
        return redirect(url_for('user_login'))

    # Only approved users can vote
    if current_user['status'] != 'approved':
        cursor.close()
        db.close()
        session.pop('username', None)
        return redirect(url_for('user_login'))

    # POST: submit vote
    if request.method == 'POST':
        if current_user['has_voted'] == 0:
            candidate_id = request.form['candidate_id']

            cursor.close()
            db.close()

            update_vote_count(candidate_id)
            mark_user_voted(session['username'])
            return redirect(url_for('thankyou'))
        else:
            cursor.close()
            db.close()

            user = get_logged_in_user(session['username'])
            if not user:
                session.pop('username', None)
                return redirect(url_for('user_login'))

            return render_template(
                'dashboard.html',
                data=get_election_data(),
                user=user,
                election_live=True,
                already_voted=True
            )

    # GET: open vote page only if not voted
    if current_user['has_voted'] == 0:
        cursor.execute("SELECT id, candidates_name, party FROM candidates")
        candidates = cursor.fetchall()
        cursor.close()
        db.close()
        return render_template('vote.html', candidates=candidates)

    cursor.close()
    db.close()

    user = get_logged_in_user(session['username'])
    if not user:
        session.pop('username', None)
        return redirect(url_for('user_login'))

    return render_template(
        'dashboard.html',
        data=get_election_data(),
        user=user,
        election_live=True,
        already_voted=True
    )

# ---------------- FUNCTIONS ----------------
def update_vote_count(candidate_id):
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute(
        "UPDATE candidates SET votes = COALESCE(votes,0)+1 WHERE id=%s",
        (candidate_id,)
    )
    db.commit()
    cursor.close()
    db.close()


def mark_user_voted(username):
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("UPDATE users SET has_voted=1 WHERE username=%s", (username,))
    db.commit()
    cursor.close()
    db.close()


def get_election_data():
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("SELECT party, candidates_name FROM candidates")
    data = {name: {'party': party} for party, name in cursor.fetchall()}
    cursor.close()
    db.close()
    return data


def get_election_result():
    db = get_db_connection()
    cursor = db.cursor(buffered=True)
    cursor.execute("""
        SELECT candidates_name, party, COALESCE(votes,0)
        FROM candidates
        ORDER BY COALESCE(votes,0) DESC
    """)
    data = {name: [votes, party] for name, party, votes in cursor.fetchall()}
    cursor.close()
    db.close()
    return data

# ---------------- THANK YOU ----------------
@app.route('/thankyou')
def thankyou():
    if 'username' not in session:
        return redirect(url_for('user_login'))

    return render_template('thankyou.html')

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('admin', None)
    return redirect(url_for('index'))

# ---------------- REMOVE USER ----------------
@app.route('/remove_user', methods=['GET', 'POST'])
def remove_user():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    if request.method == "POST":
        voter_id = request.form['voter_id']

        db = get_db_connection()
        cursor = db.cursor(buffered=True)

        query = "SELECT * FROM users WHERE voter_id = %s"
        cursor.execute(query, (voter_id,))
        user = cursor.fetchone()

        if not user:
            cursor.close()
            db.close()
            return render_template('remove_user.html', message="User not found!")

        cursor.execute("DELETE FROM users WHERE voter_id = %s", (voter_id,))
        db.commit()
        cursor.close()
        db.close()

        return render_template('remove_user.html', message="User removed successfully!")

    return render_template('remove_user.html')

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True)