import os
import threading
from glob import glob
from flask import Flask, request, render_template, redirect, url_for, session, current_app, jsonify
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from engine import render_video_task

app = Flask(__name__)

@app.template_filter('split')
def split_filter(s, delimiter):
    return s.split(delimiter)
app.secret_key = 'super-secret-key' 


UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
OUTPUT_FOLDER = os.path.join(app.root_path, 'static', 'outputs')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

# MySQL Configuration for XAMPP Default
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'ai_video_maker'
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Error connecting to DB: {err}")
        return None

#routes

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        if not conn:
            return "Database connection error.", 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
  
        cursor.close()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid credentials")
            
    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    # Simple registration 
    username = request.form['username']
    password = request.form['password']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    hashed_pwd = generate_password_hash(password)
    try:
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, hashed_pwd))
        conn.commit()
    except mysql.connector.IntegrityError:
        pass # User exists
    
    cursor.close()
    conn.close()
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM videos WHERE user_id = %s ORDER BY created_at DESC", (session['user_id'],))
    videos = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('dashboard.html', videos=videos)

@app.route('/upload', methods=['POST'])
def upload():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    if 'images' not in request.files or 'audio' not in request.files:
        return jsonify({'error': 'Missing files'}), 400

    # Catching values from the HTML form
    template_name = request.form.get('template', 'Cinematic Fade')
    language_choice = request.form.get('language') 
    
    enable_captions = request.form.get('enable_captions', 'true') 
    
    images = request.files.getlist('images')
    audio = request.files['audio']
    
    if not images or not audio:
         return jsonify({'error': 'Empty files'}), 400
         
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO videos (user_id, template_name, status) VALUES (%s, %s, 'processing')", (session['user_id'], template_name))
    video_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    
    job_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(video_id))
    os.makedirs(job_dir, exist_ok=True)
      
    # Save files
    image_paths = []
    for img in images:
        filename = secure_filename(img.filename)
        path = os.path.join(job_dir, filename)
        img.save(path)
        image_paths.append(path)
        
    audio_filename = secure_filename(audio.filename)
    audio_path = os.path.join(job_dir, audio_filename)
    audio.save(audio_path)
   
    thread = threading.Thread(target=render_video_task, args=(
        video_id, 
        job_dir, 
        image_paths, 
        audio_path, 
        template_name, 
        language_choice, 
        enable_captions, 
        app.config['OUTPUT_FOLDER'], 
        DB_CONFIG
    ))
    thread.start()
    
    return jsonify({'success': True, 'video_id': video_id})

if __name__ == '__main__':
    app.run(debug=True, port=5000)