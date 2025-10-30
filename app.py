from flask import Flask, request, jsonify, session, redirect, url_for, render_template, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from datetime import datetime
import json
import time # Lisa see

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Muuda seda tootmiskeskkonnas
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
DB_PATH = os.environ.get('DB_PATH', 'todo.db')

# Andmebaasi initsialiseerimine
def init_db():
    """Andmebaasi tabelite loomine"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Kasutajate tabel
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Todo ülesannete tabel
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            priority TEXT DEFAULT 'medium',
            due_date DATE,
            completed BOOLEAN DEFAULT FALSE,
            tags TEXT DEFAULT '',
            attachment_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    # Tegevuslogi tabel
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            todo_id INTEGER,
            action TEXT NOT NULL,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Skeemi uuendused olemasolevatele instantsidele (lisab veerud kui neid pole)
    cursor.execute("PRAGMA table_info(todos)")
    cols = [row[1] for row in cursor.fetchall()]
    if 'tags' not in cols:
        cursor.execute("ALTER TABLE todos ADD COLUMN tags TEXT DEFAULT ''")
    if 'attachment_path' not in cols:
        cursor.execute("ALTER TABLE todos ADD COLUMN attachment_path TEXT")
    
    conn.commit()
    conn.close()

# Kasutaja sisselogimise kontroll
def is_logged_in():
    """Kontrollib kas kasutaja on sisse logitud"""
    return 'user_id' in session

# Kasutaja andmete hankimine
def get_user_data(user_id):
    """Hankib kasutaja andmed andmebaasist"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, username FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def log_activity(user_id, todo_id, action, details=None):
    """Salvestab tegevuslogi kirje"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO activity_logs (user_id, todo_id, action, details) VALUES (?, ?, ?, ?)',
                   (user_id, todo_id, action, details))
    conn.commit()
    conn.close()

@app.route('/')
def index():
    """Pealeht - näitab HTML-i"""
    return render_template('index.html')

@app.route('/api/register', methods=['POST'])
def register():
    """Kasutaja registreerimine"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'success': False, 'message': 'Kasutajanimi ja parool on kohustuslikud'})
    
    if len(password) < 6:
        return jsonify({'success': False, 'message': 'Parool peab olema vähemalt 6 tähemärki pikk'})
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Kontrollib kas kasutajanimi on juba olemas
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'Kasutajanimi on juba kasutusel'})
        
        # Loob uue kasutaja
        password_hash = generate_password_hash(password)
        cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', 
                       (username, password_hash))
        conn.commit()
        
        return jsonify({'success': True, 'message': 'Kasutaja loodud edukalt'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': 'Viga kasutaja loomisel'})
    finally:
        conn.close()

@app.route('/api/login', methods=['POST'])
def login():
    """Kasutaja sisselogimine"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'success': False, 'message': 'Kasutajanimi ja parool on kohustuslikud'})
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Otsib kasutajat andmebaasist
        cursor.execute('SELECT id, password_hash FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        
        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            log_activity(user[0], None, 'login', 'Kasutaja logis sisse')
            return jsonify({'success': True, 'message': 'Sisselogimine õnnestus'})
        else:
            return jsonify({'success': False, 'message': 'Vale kasutajanimi või parool'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': 'Viga sisselogimisel'})
    finally:
        conn.close()

@app.route('/api/logout', methods=['POST'])
def logout():
    """Kasutaja väljalogimine"""
    uid = session.get('user_id')
    if uid:
        log_activity(uid, None, 'logout', 'Kasutaja logis välja')
    session.pop('user_id', None)
    return jsonify({'success': True, 'message': 'Väljalogimine õnnestus'})

@app.route('/api/change-password', methods=['POST'])
def change_password():
    """Kasutaja parooli muutmine"""
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Sa pead olema sisse logitud'})
    
    data = request.get_json()
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    if not old_password or not new_password:
        return jsonify({'success': False, 'message': 'Vana ja uus parool on kohustuslikud'})
    
    if len(new_password) < 6:
        return jsonify({'success': False, 'message': 'Uus parool peab olema vähemalt 6 tähemärki pikk'})
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Kontrollib vana parooli
        cursor.execute('SELECT password_hash FROM users WHERE id = ?', (session['user_id'],))
        user = cursor.fetchone()
        
        if not user or not check_password_hash(user[0], old_password):
            return jsonify({'success': False, 'message': 'Vale vana parool'})
        
        # Uuendab parooli
        new_password_hash = generate_password_hash(new_password)
        cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', 
                       (new_password_hash, session['user_id']))
        conn.commit()
        log_activity(session['user_id'], None, 'password_change', 'Kasutaja muutis parooli')
        
        return jsonify({'success': True, 'message': 'Parool muudetud edukalt'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': 'Viga parooli muutmisel'})
    finally:
        conn.close()

@app.route('/api/todos', methods=['GET'])
def get_todos():
    """Kasutaja todo ülesannete hankimine koos otsingu/filtri/sortimisega"""
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Sa pead olema sisse logitud'})
    
    q = request.args.get('q', '').strip()
    tag = request.args.get('tag', '').strip()
    sort_by = request.args.get('sort_by', 'created_at')
    sort_dir = request.args.get('sort_dir', 'desc').lower()
    allowed_sort = {'created_at', 'due_date', 'priority', 'completed', 'title'}
    if sort_by not in allowed_sort:
        sort_by = 'created_at'
    sort_dir_sql = 'DESC' if sort_dir == 'desc' else 'ASC'

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        query = '''
            SELECT id, title, description, priority, due_date, completed, created_at, tags, attachment_path
            FROM todos
            WHERE user_id = ?
        '''
        params = [session['user_id']]
        if q:
            query += ' AND (title LIKE ? OR description LIKE ?)'
            like = f'%{q}%'
            params.extend([like, like])
        if tag:
            query += ' AND tags LIKE ?'
            params.append(f'%{tag}%')
        query += f' ORDER BY {sort_by} {sort_dir_sql}'

        cursor.execute(query, params)
        todos = []
        for row in cursor.fetchall():
            todos.append({
                'id': row[0],
                'title': row[1],
                'description': row[2],
                'priority': row[3],
                'due_date': row[4],
                'completed': bool(row[5]),
                'created_at': row[6],
                'tags': row[7] or '',
                'attachment_path': row[8]
            })
        return jsonify({'success': True, 'todos': todos})
    except Exception:
        return jsonify({'success': False, 'message': 'Viga ülesannete hankimisel'})
    finally:
        conn.close()

@app.route('/api/todos', methods=['POST'])
def create_todo():
    """Uue todo ülesande loomine"""
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Sa pead olema sisse logitud'})
    
    data = request.get_json()
    title = data.get('title')
    description = data.get('description', '')
    priority = data.get('priority', 'medium')
    due_date = data.get('due_date')
    tags = (data.get('tags') or '').strip()
    
    if not title:
        return jsonify({'success': False, 'message': 'Pealkiri on kohustuslik'})
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO todos (user_id, title, description, priority, due_date, tags) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session['user_id'], title, description, priority, due_date, tags))
        conn.commit()
        todo_id = cursor.lastrowid
        log_activity(session['user_id'], todo_id, 'create', f'Lisati ülesanne: {title}')
        
        return jsonify({'success': True, 'message': 'Ülesanne loodud edukalt'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': 'Viga ülesande loomisel'})
    finally:
        conn.close()

@app.route('/api/todos/<int:todo_id>', methods=['PUT'])
def update_todo(todo_id):
    """Todo ülesande uuendamine"""
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Sa pead olema sisse logitud'})
    
    data = request.get_json()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Kontrollib kas ülesanne kuulub kasutajale
        cursor.execute('SELECT id FROM todos WHERE id = ? AND user_id = ?', 
                       (todo_id, session['user_id']))
        if not cursor.fetchone():
            return jsonify({'success': False, 'message': 'Ülesannet ei leitud'})
        
        # Uuendab ülesannet
        update_fields = []
        update_values = []
        
        if 'title' in data:
            update_fields.append('title = ?')
            update_values.append(data['title'])
        
        if 'description' in data:
            update_fields.append('description = ?')
            update_values.append(data['description'])
        
        if 'priority' in data:
            update_fields.append('priority = ?')
            update_values.append(data['priority'])
        
        if 'due_date' in data:
            update_fields.append('due_date = ?')
            update_values.append(data['due_date'])
        
        if 'completed' in data:
            update_fields.append('completed = ?')
            update_values.append(data['completed'])
        if 'tags' in data:
            update_fields.append('tags = ?')
            update_values.append(data['tags'])
        if 'attachment_path' in data:
            update_fields.append('attachment_path = ?')
            update_values.append(data['attachment_path'])
        
        if update_fields:
            update_values.append(todo_id)
            cursor.execute(f'''
                UPDATE todos 
                SET {', '.join(update_fields)} 
                WHERE id = ?
            ''', update_values)
            conn.commit()
            log_activity(session['user_id'], todo_id, 'update', 'Ülesannet uuendati')
        
        return jsonify({'success': True, 'message': 'Ülesanne uuendatud edukalt'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': 'Viga ülesande uuendamisel'})
    finally:
        conn.close()

@app.route('/api/todos/<int:todo_id>', methods=['DELETE'])
def delete_todo(todo_id):
    """Todo ülesande kustutamine"""
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Sa pead olema sisse logitud'})
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Kontrollib kas ülesanne kuulub kasutajale
        cursor.execute('SELECT id FROM todos WHERE id = ? AND user_id = ?', 
                       (todo_id, session['user_id']))
        if not cursor.fetchone():
            return jsonify({'success': False, 'message': 'Ülesannet ei leitud'})
        
        cursor.execute('DELETE FROM todos WHERE id = ?', (todo_id,))
        conn.commit()
        log_activity(session['user_id'], todo_id, 'delete', 'Ülesanne kustutati')
        
        return jsonify({'success': True, 'message': 'Ülesanne kustutatud edukalt'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': 'Viga ülesande kustutamisel'})
    finally:
        conn.close()

@app.route('/api/user', methods=['GET'])
def get_user():
    """Kasutaja andmete hankimine"""
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Sa pead olema sisse logitud'})
    
    user = get_user_data(session['user_id'])
    if user:
        return jsonify({'success': True, 'user': {'id': user[0], 'username': user[1]}})
    else:
        return jsonify({'success': False, 'message': 'Kasutajat ei leitud'})

@app.route('/api/todos/bulk', methods=['POST'])
def bulk_actions():
    """Mass-tegevused valitud ülesannetele (tehtuks märkimine või kustutamine)"""
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Sa pead olema sisse logitud'})
    data = request.get_json() or {}
    action = data.get('action')
    ids = data.get('ids') or []
    if action not in ('complete', 'incomplete', 'delete') or not ids:
        return jsonify({'success': False, 'message': 'Vigane päring'})
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        placeholders = ','.join('?' for _ in ids)
        params = ids + [session['user_id']]
        cursor.execute(f'SELECT id FROM todos WHERE id IN ({placeholders}) AND user_id = ?', params)
        valid_ids = [row[0] for row in cursor.fetchall()]
        if not valid_ids:
            return jsonify({'success': False, 'message': 'Ülesandeid ei leitud'})
        if action == 'delete':
            placeholders = ','.join('?' for _ in valid_ids)
            cursor.execute(f'DELETE FROM todos WHERE id IN ({placeholders})', valid_ids)
            log_activity(session['user_id'], None, 'bulk_delete', f'Kustutati {len(valid_ids)} ülesannet')
        else:
            value = 1 if action == 'complete' else 0
            placeholders = ','.join('?' for _ in valid_ids)
            cursor.execute(f'UPDATE todos SET completed = ? WHERE id IN ({placeholders})', [value] + valid_ids)
            log_activity(session['user_id'], None, 'bulk_update', f'Märgiti {len(valid_ids)} ülesannet')
        conn.commit()
        return jsonify({'success': True})
    except Exception:
        return jsonify({'success': False, 'message': 'Viga mass-tegevuses'})
    finally:
        conn.close()

@app.route('/api/todos/<int:todo_id>/attachment', methods=['POST', 'DELETE'])
def manage_attachment(todo_id):
    """Faili manuse lisamine või eemaldamine"""
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Sa pead olema sisse logitud'})
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT id, attachment_path FROM todos WHERE id = ? AND user_id = ?', (todo_id, session['user_id']))
        row = cursor.fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'Ülesannet ei leitud'})
        if request.method == 'POST':
            file = request.files.get('file')
            if not file or not file.filename:
                return jsonify({'success': False, 'message': 'Fail puudub'})
            filename = f"{session['user_id']}_{todo_id}_{int(datetime.now().timestamp())}_{file.filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            cursor.execute('UPDATE todos SET attachment_path = ? WHERE id = ?', (filepath, todo_id))
            conn.commit()
            log_activity(session['user_id'], todo_id, 'attach', 'Lisati manus')
            return jsonify({'success': True, 'attachment_path': filepath})
        else:
            # DELETE manus
            current = row[1]
            if current and os.path.exists(current):
                try:
                    os.remove(current)
                except Exception:
                    pass
            cursor.execute('UPDATE todos SET attachment_path = NULL WHERE id = ?', (todo_id,))
            conn.commit()
            log_activity(session['user_id'], todo_id, 'detach', 'Eemaldati manus')
            return jsonify({'success': True})
    except Exception:
        return jsonify({'success': False, 'message': 'Viga manuse töötlemisel'})
    finally:
        conn.close()

@app.route('/api/export', methods=['GET'])
def export_data():
    """Ekspordib kasutaja ülesanded JSON-ina"""
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Sa pead olema sisse logitud'})
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''SELECT title, description, priority, due_date, completed, tags FROM todos WHERE user_id = ?''', (session['user_id'],))
    items = []
    for row in cursor.fetchall():
        items.append({
            'title': row[0],
            'description': row[1],
            'priority': row[2],
            'due_date': row[3],
            'completed': bool(row[4]),
            'tags': row[5] or ''
        })
    conn.close()
    return jsonify({'success': True, 'items': items})

@app.route('/api/import', methods=['POST'])
def import_data():
    """Impordib kasutaja ülesanded JSON-ist"""
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Sa pead olema sisse logitud'})
    data = request.get_json() or {}
    items = data.get('items') or []
    if not isinstance(items, list):
        return jsonify({'success': False, 'message': 'Vale formaat'})
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        for it in items:
            cursor.execute('''
                INSERT INTO todos (user_id, title, description, priority, due_date, completed, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                session['user_id'],
                it.get('title'),
                it.get('description', ''),
                it.get('priority', 'medium'),
                it.get('due_date'),
                1 if it.get('completed') else 0,
                it.get('tags', '')
            ))
        conn.commit()
        log_activity(session['user_id'], None, 'import', f'Imporditi {len(items)} kirjet')
        return jsonify({'success': True})
    except Exception:
        return jsonify({'success': False, 'message': 'Viga importimisel'})
    finally:
        conn.close()

@app.route('/api/activity', methods=['GET'])
def activity():
    """Tagastab viimased tegevuslogid"""
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Sa pead olema sisse logitud'})
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT action, details, created_at, todo_id FROM activity_logs
        WHERE user_id = ? ORDER BY created_at DESC LIMIT 100
    ''', (session['user_id'],))
    logs = []
    for row in cursor.fetchall():
        logs.append({'action': row[0], 'details': row[1], 'created_at': row[2], 'todo_id': row[3]})
    conn.close()
    return jsonify({'success': True, 'logs': logs})

@app.route('/api/user/profile', methods=['POST'])
def update_profile():
    """Kasutajanime muutmine"""
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Sa pead olema sisse logitud'})
    data = request.get_json() or {}
    new_username = (data.get('username') or '').strip()
    if not new_username:
        return jsonify({'success': False, 'message': 'Kasutajanimi on kohustuslik'})
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT id FROM users WHERE username = ? AND id != ?', (new_username, session['user_id']))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'Kasutajanimi on juba kasutusel'})
        cursor.execute('UPDATE users SET username = ? WHERE id = ?', (new_username, session['user_id']))
        conn.commit()
        log_activity(session['user_id'], None, 'username_change', 'Kasutajanimi muudetud')
        return jsonify({'success': True})
    except Exception:
        return jsonify({'success': False, 'message': 'Viga profiili uuendamisel'})
    finally:
        conn.close()

@app.route('/api/user', methods=['DELETE'])
def delete_account():
    """Kasutajakonto kustutamine (kustutab ka kasutaja ülesanded)"""
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Sa pead olema sisse logitud'})
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        uid = session['user_id']
        cursor.execute('DELETE FROM todos WHERE user_id = ?', (uid,))
        cursor.execute('DELETE FROM activity_logs WHERE user_id = ?', (uid,))
        cursor.execute('DELETE FROM users WHERE id = ?', (uid,))
        conn.commit()
        session.pop('user_id', None)
        return jsonify({'success': True})
    except Exception:
        return jsonify({'success': False, 'message': 'Viga konto kustutamisel'})
    finally:
        conn.close()

# --- Stress-testimise näidislehed ---

@app.route('/fast')
def fast_page():
    """Kiire leht - tagastab kohe vastuse."""
    return "See leht laadis väga kiiresti!"

@app.route('/medium')
def medium_page():
    """Keskmise kiirusega leht - teeb väikese andmebaasi päringu."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    user_count = cursor.fetchone()[0]
    conn.close()
    return f"Meil on kokku {user_count} kasutajat. See leht laadis keskmise kiirusega."

@app.route('/slow')
def slow_page():
    """Aeglane leht - simuleerib 2-sekundilist ootamist."""
    time.sleep(2) # Simuleerime pikka operatsiooni
    return "See leht laadis aeglaselt (2 sekundit viivitust)."


if __name__ == '__main__':
    init_db()
    # Kasutaja muutis pordi 5001 peale, jätame selle alles
    app.run(debug=True, host='0.0.0.0', port=5001)
