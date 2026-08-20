from flask import Flask, render_template, request, redirect, session, url_for, flash
from db import get_db, close_db
from admin_routes import admin_bp
from user_routes import user_bp
from chatbot_routes import chatbot_bp
# Comment out simulator import until numpy is installed
# from simulator import simulator_bp
from config import Config
from mail import mail, send_welcome_email, send_password_reset
import bcrypt
import secrets
import datetime
import psycopg2
import os

app = Flask(__name__) 
app.secret_key = Config.SECRET_KEY
app.config.from_object(Config)

# Initialize extensions
mail.init_app(app)

app.register_blueprint(admin_bp)
app.register_blueprint(user_bp)
app.register_blueprint(chatbot_bp)
# Comment out simulator blueprint registration
# app.register_blueprint(simulator_bp)

@app.teardown_appcontext
def teardown_db(exception):
    close_db()

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

@app.route('/')
def landing():
    if 'user_id' in session:
        session.clear()
    return render_template('landing.html')

@app.route('/home')
def home():
    if 'user_id' in session:
        if session.get('is_admin'):
            return redirect(url_for('admin'))
        else:
            return redirect(url_for('user'))
    else:
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        db = get_db()
        cur = db.cursor()
        username = request.form['username']
        password = request.form['password']
        cur.execute(
            'SELECT user_id, username, password, is_admin FROM users WHERE username = %s',
            (username, ))
        user = cur.fetchone()
        cur.close()
        if user and bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['is_admin'] = user[3]
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            print("Attempting to connect to database...")
            db = get_db()
            print("Database connection successful")
            cur = db.cursor()
            username = request.form['username']
            password = request.form['password']
            email = request.form['email']

            print(f"Attempting to register user: {username}")

            # Check if the username already exists
            cur.execute('SELECT * FROM users WHERE username = %s',
                        (username, ))
            existing_user = cur.fetchone()
            if existing_user:
                print("Username already exists")
                flash('Username already taken', 'error')
                return redirect(url_for('register'))

            # Check if the email already exists
            cur.execute('SELECT * FROM users WHERE email = %s', (email, ))
            existing_email = cur.fetchone()
            if existing_email:
                print("Email already exists")
                flash('Email already registered', 'error')
                return redirect(url_for('register'))

            # Hash the password
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            print("Attempting to insert new user...")
            cur.execute(
                'INSERT INTO users (username, password, email, is_admin) VALUES (%s, %s, %s, %s)',
                (username, hashed_password, email, False))
            db.commit()
            print("User inserted successfully")
            cur.close()
            
            # Send welcome email
            try:
                print(f"Attempting to send welcome email to {email}")
                email_queued = send_welcome_email(email, username)
                if email_queued:
                    print(f"Welcome email queued for {email}")
                else:
                    print("Email not configured - skipping welcome email")
            except Exception as e:
                print(f"ERROR sending welcome email: {str(e)}")
                print(f"Error type: {type(e)}")
                # Log the error but don't prevent registration
                
            flash('Registration successful', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            print("Error during registration:", str(e))
            if 'db' in locals():
                db.rollback()
            flash('Registration failed: ' + str(e), 'error')
            return redirect(url_for('register'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('landing'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/search', methods=['GET', 'POST'])
def search():
    if 'user_id' not in session:
        flash('You need to log in to search', 'error')
        return redirect(url_for('login'))

    results = []
    query = ""
    if request.method == 'POST':
        query = request.form['query']
        db = get_db()
        cur = db.cursor()

        # Search in teams
        cur.execute(
            "SELECT team_id, name, 'team' AS source FROM teams WHERE name ILIKE %s",
            ('%' + query + '%', ))
        results.extend(cur.fetchall())

        # Search in coaches
        cur.execute(
            "SELECT coach_id, name, 'coach' AS source FROM coaches WHERE name ILIKE %s",
            ('%' + query + '%', ))
        results.extend(cur.fetchall())

        # Search in players
        cur.execute(
            "SELECT player_id, name, 'player' AS source FROM players WHERE name ILIKE %s",
            ('%' + query + '%', ))
        results.extend(cur.fetchall())

        # Search in stadiums
        cur.execute(
            "SELECT stadium_id, name, 'stadium' AS source FROM stadiums WHERE name ILIKE %s",
            ('%' + query + '%', ))
        results.extend(cur.fetchall())

        # Search in leagues
        cur.execute(
            "SELECT league_id, name, 'league' AS source FROM leagues WHERE name ILIKE %s",
            ('%' + query + '%', ))
        results.extend(cur.fetchall())

        cur.close()

    return render_template('search.html', results=results, query=query)

@app.route('/admin')
def admin():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    
    db = get_db()
    cur = db.cursor()
    
    # Get total teams count
    cur.execute('SELECT COUNT(*) FROM teams')
    teams_count = cur.fetchone()[0]
    
    # Get total players count
    cur.execute('SELECT COUNT(*) FROM players')
    players_count = cur.fetchone()[0]
    
    # Get upcoming matches count
    cur.execute("SELECT COUNT(*) FROM matches WHERE status = 'SCHEDULED'")
    upcoming_matches = cur.fetchone()[0]
    
    cur.close()
    
    return render_template('admin.html', 
                         teams_count=teams_count,
                         players_count=players_count,
                         upcoming_matches=upcoming_matches)

@app.route('/user')
def user():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('user.user_dashboard'))

@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        try:
            db = get_db()
            cur = db.cursor()
            username = request.form['username']
            password = request.form['password']
            email = request.form['email']

            # Hash the password
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            cur.execute(
                'INSERT INTO users (username, password, email) VALUES (%s, %s, %s)',
                (username, hashed_password, email))
            db.commit()
            cur.close()
            flash('User added successfully', 'success')
            return redirect(url_for('user'))
        except Exception as e:
            db.rollback()
            print("Error: ", str(e))
            flash('Failed to add user', 'error')
            return redirect(url_for('add_user'))
    return render_template('add_user.html')

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    cur = db.cursor()
    user_id = session['user_id']

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Check if the username already exists
        cur.execute(
            'SELECT * FROM users WHERE username = %s AND user_id != %s',
            (username, user_id))
        existing_user = cur.fetchone()
        if existing_user:
            flash('Username already taken', 'error')
            return redirect(url_for('profile'))

        # Check if the email already exists
        cur.execute('SELECT * FROM users WHERE email = %s AND user_id != %s',
                    (email, user_id))
        existing_email = cur.fetchone()
        if existing_email:
            flash('Email already registered', 'error')
            return redirect(url_for('profile'))

        # Hash the password if it is updated
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        cur.execute(
            'UPDATE users SET username = %s, email = %s, password = %s WHERE user_id = %s',
            (username, email, hashed_password, user_id))
        db.commit()
        flash('Profile updated successfully', 'success')
        return redirect(url_for('profile'))

    cur.execute('SELECT username, email FROM users WHERE user_id = %s',
                (user_id, ))
    user = cur.fetchone()
    cur.close()

    return render_template('profile.html', user=user)

@app.route('/recreate_db')
def recreate_db():
    try:
        from db import recreate_database
        recreate_database()
        return "Database recreated successfully!"
    except Exception as e:
        return f"Error recreating database: {str(e)}"

@app.route('/update_starters')
def update_starters():
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('DB_NAME', 'sports_league_db'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'postgres')
        )
        cur = conn.cursor()
        
        # Read and execute update_starters.sql file
        schema_path = os.path.join(os.path.dirname(__file__), 'update_starters.sql')
        with open(schema_path, 'r', encoding='utf-8') as f:
            cur.execute(f.read())
        
        conn.commit()
        cur.close()
        conn.close()
        return "Starting players updated successfully!"
    except Exception as e:
        return f"Error updating starting players: {str(e)}"

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        
        # Check if the email exists
        db = get_db()
        cur = db.cursor()
        cur.execute('SELECT user_id, username FROM users WHERE email = %s', (email,))
        user = cur.fetchone()
        
        if user:
            # Generate a token
            token = secrets.token_urlsafe(32)
            expiration = datetime.datetime.now() + datetime.timedelta(hours=24)
            
            # Store the token in the database
            try:
                # Check if a reset token already exists
                cur.execute('SELECT * FROM password_resets WHERE user_id = %s', (user[0],))
                if cur.fetchone():
                    # Update existing token
                    cur.execute(
                        'UPDATE password_resets SET token = %s, expires_at = %s WHERE user_id = %s',
                        (token, expiration, user[0])
                    )
                else:
                    # Insert new token
                    cur.execute(
                        'INSERT INTO password_resets (user_id, token, expires_at) VALUES (%s, %s, %s)',
                        (user[0], token, expiration)
                    )
                db.commit()
                
                # Send reset email
                reset_link = url_for('reset_password', token=token, _external=True)
                email_queued = send_password_reset(email, user[1], reset_link)
                if email_queued:
                    flash('Password reset instructions have been sent to your email', 'success')
                else:
                    flash('Password reset token created, but email is not configured for local testing', 'success')
            except Exception as e:
                db.rollback()
                print(f"Error in password reset: {str(e)}")
                flash('An error occurred. Please try again later.', 'error')
        else:
            # We don't want to reveal that the email doesn't exist
            # So we still show a success message
            flash('If your email is registered, you will receive password reset instructions', 'success')
        
        return redirect(url_for('login'))
    
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    # Verify token
    db = get_db()
    cur = db.cursor()
    cur.execute(
        'SELECT pr.user_id, u.username FROM password_resets pr '
        'JOIN users u ON pr.user_id = u.user_id '
        'WHERE pr.token = %s AND pr.expires_at > %s',
        (token, datetime.datetime.now())
    )
    result = cur.fetchone()
    
    if not result:
        flash('Invalid or expired password reset link', 'error')
        return redirect(url_for('login'))
    
    user_id, username = result
    
    if request.method == 'POST':
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('reset_password.html', token=token, username=username)
        
        try:
            # Update the password
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cur.execute('UPDATE users SET password = %s WHERE user_id = %s', (hashed_password, user_id))
            
            # Delete the token
            cur.execute('DELETE FROM password_resets WHERE user_id = %s', (user_id,))
            db.commit()
            
            flash('Your password has been reset successfully. You can now log in with your new password.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.rollback()
            print(f"Error in password reset: {str(e)}")
            flash('An error occurred. Please try again later.', 'error')
    
    return render_template('reset_password.html', token=token, username=username)

if __name__ == '__main__':
    app.run(debug=True)
