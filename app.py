from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os, json
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'taskmanager-secret-key-2024'
DB = 'tasks.db'

# ── DB ──────────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                category TEXT DEFAULT "Outros",
                priority TEXT DEFAULT "Média",
                due_date TEXT,
                done INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sender_id) REFERENCES users(id),
                FOREIGN KEY (receiver_id) REFERENCES users(id)
            );
        ''')

init_db()

# ── Auth decorator ────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ── Auth routes ──────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name  = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        pwd   = request.form.get('password', '')
        if not name or not email or not pwd:
            flash('Preencha todos os campos.', 'error')
            return render_template('auth.html', mode='register')
        if len(pwd) < 6:
            flash('A senha deve ter pelo menos 6 caracteres.', 'error')
            return render_template('auth.html', mode='register')
        try:
            with get_db() as db:
                db.execute('INSERT INTO users (name, email, password) VALUES (?, ?, ?)',
                           (name, email, generate_password_hash(pwd)))
            flash('Conta criada com sucesso! Faça login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('E-mail já cadastrado.', 'error')
    return render_template('auth.html', mode='register')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        pwd   = request.form.get('password', '')
        db    = get_db()
        user  = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        if user and check_password_hash(user['password'], pwd):
            session['user_id']   = user['id']
            session['user_name'] = user['name']
            return redirect(url_for('dashboard'))
        flash('E-mail ou senha inválidos.', 'error')
    return render_template('auth.html', mode='login')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ── Dashboard ────────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    uid = session['user_id']
    cat    = request.args.get('cat', '')
    pri    = request.args.get('pri', '')
    status = request.args.get('status', '')
    q      = request.args.get('q', '')

    query  = 'SELECT * FROM tasks WHERE user_id = ?'
    params = [uid]
    if cat:    query += ' AND category = ?';  params.append(cat)
    if pri:    query += ' AND priority = ?';  params.append(pri)
    if status == 'done':    query += ' AND done = 1'
    elif status == 'pending': query += ' AND done = 0'
    if q:      query += ' AND (title LIKE ? OR description LIKE ?)'; params += [f'%{q}%', f'%{q}%']
    query += ' ORDER BY done ASC, CASE priority WHEN "Alta" THEN 1 WHEN "Média" THEN 2 ELSE 3 END, created_at DESC'

    tasks = db.execute(query, params).fetchall()

    all_tasks = db.execute('SELECT * FROM tasks WHERE user_id = ?', (uid,)).fetchall()
    today = datetime.today().strftime('%Y-%m-%d')
    stats = {
        'total':   len(all_tasks),
        'pending': sum(1 for t in all_tasks if not t['done']),
        'done':    sum(1 for t in all_tasks if t['done']),
        'overdue': sum(1 for t in all_tasks if not t['done'] and t['due_date'] and t['due_date'] < today),
    }
    return render_template('dashboard.html', tasks=tasks, stats=stats,
                           today=today, filters={'cat': cat, 'pri': pri, 'status': status, 'q': q})

# ── Task CRUD ─────────────────────────────────────────────────────────────────

@app.route('/tasks/create', methods=['POST'])
@login_required
def create_task():
    title = request.form.get('title', '').strip()
    if not title:
        flash('O título é obrigatório.', 'error')
        return redirect(url_for('dashboard'))
    with get_db() as db:
        db.execute('''INSERT INTO tasks (user_id, title, description, category, priority, due_date)
                      VALUES (?, ?, ?, ?, ?, ?)''',
                   (session['user_id'], title,
                    request.form.get('description', '').strip(),
                    request.form.get('category', 'Outros'),
                    request.form.get('priority', 'Média'),
                    request.form.get('due_date') or None))
    flash('Tarefa criada com sucesso!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/tasks/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    db   = get_db()
    task = db.execute('SELECT * FROM tasks WHERE id = ? AND user_id = ?',
                      (task_id, session['user_id'])).fetchone()
    if not task:
        flash('Tarefa não encontrada.', 'error')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        if not title:
            flash('O título é obrigatório.', 'error')
            return render_template('edit_task.html', task=task)
        with db:
            db.execute('''UPDATE tasks SET title=?, description=?, category=?, priority=?, due_date=?
                          WHERE id=? AND user_id=?''',
                       (title,
                        request.form.get('description', '').strip(),
                        request.form.get('category', 'Outros'),
                        request.form.get('priority', 'Média'),
                        request.form.get('due_date') or None,
                        task_id, session['user_id']))
        flash('Tarefa atualizada!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('edit_task.html', task=task)

@app.route('/tasks/<int:task_id>/toggle', methods=['POST'])
@login_required
def toggle_task(task_id):
    with get_db() as db:
        db.execute('''UPDATE tasks SET done = CASE WHEN done=1 THEN 0 ELSE 1 END
                      WHERE id=? AND user_id=?''', (task_id, session['user_id']))
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/tasks/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    with get_db() as db:
        db.execute('DELETE FROM tasks WHERE id=? AND user_id=?', (task_id, session['user_id']))
    flash('Tarefa excluída.', 'success')
    return redirect(url_for('dashboard'))

# ── Chat ─────────────────────────────────────────────────────────────────────

@app.route('/chat')
@login_required
def chat():
    db  = get_db()
    uid = session['user_id']
    # All users except self
    users = db.execute('SELECT id, name, email FROM users WHERE id != ?', (uid,)).fetchall()
    # Unread count per sender
    unread = db.execute('''SELECT sender_id, COUNT(*) as cnt FROM chat_messages
                           WHERE receiver_id=? AND read=0 GROUP BY sender_id''', (uid,)).fetchall()
    unread_map = {r['sender_id']: r['cnt'] for r in unread}
    # Last message per conversation
    last_msgs = {}
    for u in users:
        msg = db.execute('''SELECT * FROM chat_messages
                            WHERE (sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?)
                            ORDER BY created_at DESC LIMIT 1''',
                         (uid, u['id'], u['id'], uid)).fetchone()
        last_msgs[u['id']] = msg
    return render_template('chat.html', users=users, unread_map=unread_map, last_msgs=last_msgs)

@app.route('/chat/<int:peer_id>')
@login_required
def chat_conversation(peer_id):
    db  = get_db()
    uid = session['user_id']
    peer = db.execute('SELECT id, name, email FROM users WHERE id=?', (peer_id,)).fetchone()
    if not peer:
        flash('Usuário não encontrado.', 'error')
        return redirect(url_for('chat'))
    # Mark messages as read
    with db:
        db.execute('UPDATE chat_messages SET read=1 WHERE sender_id=? AND receiver_id=? AND read=0',
                   (peer_id, uid))
    messages = db.execute('''SELECT m.*, u.name as sender_name FROM chat_messages m
                             JOIN users u ON u.id = m.sender_id
                             WHERE (m.sender_id=? AND m.receiver_id=?) OR (m.sender_id=? AND m.receiver_id=?)
                             ORDER BY m.created_at ASC''',
                          (uid, peer_id, peer_id, uid)).fetchall()
    users = db.execute('SELECT id, name, email FROM users WHERE id != ?', (uid,)).fetchall()
    unread = db.execute('''SELECT sender_id, COUNT(*) as cnt FROM chat_messages
                           WHERE receiver_id=? AND read=0 GROUP BY sender_id''', (uid,)).fetchall()
    unread_map = {r['sender_id']: r['cnt'] for r in unread}
    last_msgs = {}
    for u in users:
        msg = db.execute('''SELECT * FROM chat_messages
                            WHERE (sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?)
                            ORDER BY created_at DESC LIMIT 1''',
                         (uid, u['id'], u['id'], uid)).fetchone()
        last_msgs[u['id']] = msg
    return render_template('chat.html', users=users, peer=peer, messages=messages,
                           unread_map=unread_map, last_msgs=last_msgs)

@app.route('/chat/<int:peer_id>/send', methods=['POST'])
@login_required
def send_message(peer_id):
    text = request.form.get('message', '').strip()
    if not text:
        return redirect(url_for('chat_conversation', peer_id=peer_id))
    with get_db() as db:
        db.execute('INSERT INTO chat_messages (sender_id, receiver_id, message) VALUES (?,?,?)',
                   (session['user_id'], peer_id, text))
    return redirect(url_for('chat_conversation', peer_id=peer_id))

@app.route('/chat/<int:peer_id>/messages')
@login_required
def poll_messages(peer_id):
    """Polling endpoint — returns new messages as JSON."""
    db  = get_db()
    uid = session['user_id']
    after = request.args.get('after', 0, type=int)
    msgs  = db.execute('''SELECT m.id, m.sender_id, m.message, m.created_at, u.name as sender_name
                          FROM chat_messages m JOIN users u ON u.id=m.sender_id
                          WHERE ((m.sender_id=? AND m.receiver_id=?) OR (m.sender_id=? AND m.receiver_id=?))
                          AND m.id > ? ORDER BY m.created_at ASC''',
                       (uid, peer_id, peer_id, uid, after)).fetchall()
    # Mark incoming as read
    with db:
        db.execute('UPDATE chat_messages SET read=1 WHERE sender_id=? AND receiver_id=? AND read=0',
                   (peer_id, uid))
    return jsonify([dict(m) for m in msgs])

@app.route('/chat/unread')
@login_required
def unread_count():
    db  = get_db()
    uid = session['user_id']
    row = db.execute('SELECT COUNT(*) as cnt FROM chat_messages WHERE receiver_id=? AND read=0', (uid,)).fetchone()
    return jsonify({'count': row['cnt']})

# ── Chatbot IA ───────────────────────────────────────────────────────────────

@app.route('/bot')
@login_required
def bot():
    return render_template('bot.html')

@app.route('/bot/ask', methods=['POST'])
@login_required
def bot_ask():
    import urllib.request, urllib.error
    data = request.get_json()
    history = data.get('history', [])   # [{role, content}, ...]
    user_msg = data.get('message', '').strip()
    if not user_msg:
        return jsonify({'error': 'Mensagem vazia'}), 400

    # Build messages list (last 20 turns to keep context window small)
    messages = history[-20:]
    messages.append({'role': 'user', 'content': user_msg})

    # Get user tasks summary to give context to the bot
    db = get_db()
    uid = session['user_id']
    tasks = db.execute(
        'SELECT title, category, priority, due_date, done FROM tasks WHERE user_id=? ORDER BY done, created_at DESC LIMIT 30',
        (uid,)
    ).fetchall()
    tasks_summary = '\n'.join(
        f"- [{t['category']}] {t['title']} | Prioridade: {t['priority']} | "
        f"Prazo: {t['due_date'] or 'sem prazo'} | {'✓ Concluída' if t['done'] else '⏳ Pendente'}"
        for t in tasks
    ) or 'Nenhuma tarefa cadastrada.'

    system_prompt = f"""Você é o Assistente IA do TaskManager, um app de gerenciamento de tarefas.
Seu papel é ajudar o usuário '{session['user_name']}' com dúvidas sobre produtividade, organização, uso do sistema e gestão de tarefas.

Tarefas atuais do usuário:
{tasks_summary}

Diretrizes:
- Responda em português brasileiro, de forma clara e objetiva.
- Use as tarefas acima para dar conselhos personalizados quando relevante.
- Ajude com dicas de produtividade, priorização, gestão de tempo e uso do TaskManager.
- Para perguntas fora do contexto de produtividade/tarefas, redirecione gentilmente.
- Seja encorajador e positivo.
- Use listas e formatação simples quando ajudar na clareza.
- Respostas curtas e diretas (máx. 3 parágrafos, salvo quando necessário).
"""

    payload = json.dumps({
        'model': 'claude-sonnet-4-20250514',
        'max_tokens': 1000,
        'system': system_prompt,
        'messages': messages
    }).encode('utf-8')

    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        return jsonify({'error': 'ANTHROPIC_API_KEY não configurada no servidor.'}), 500

    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages',
        data=payload,
        headers={
            'Content-Type': 'application/json',
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01'
        },
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
        reply = result['content'][0]['text']
        return jsonify({'reply': reply})
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return jsonify({'error': f'Erro da API: {body}'}), 502
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
