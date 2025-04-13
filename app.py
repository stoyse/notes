from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import markdown
import sqlite3
import re

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for flash messages

# Database initialization
def init_db():
    with sqlite3.connect('notes.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL
            )
        ''')
        conn.commit()

# Fetch all notes from the database
def get_all_notes():
    with sqlite3.connect('notes.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, content FROM notes')
        return cursor.fetchall()

# Fetch a single note by ID
def get_note_by_id(note_id):
    with sqlite3.connect('notes.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT content FROM notes WHERE id = ?', (note_id,))
        return cursor.fetchone()

# Add a new note to the database
def add_note_to_db(content):
    with sqlite3.connect('notes.db') as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO notes (content) VALUES (?)', (content,))
        conn.commit()

# Delete a note by ID
def delete_note_from_db(note_id):
    with sqlite3.connect('notes.db') as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM notes WHERE id = ?', (note_id,))
        conn.commit()

# Create a new table for a group of notes
def create_table_for_notes(table_name, notes):
    table_name = sanitize_table_name(table_name)  # Remove prefix logic
    with sqlite3.connect('notes.db') as conn:
        cursor = conn.cursor()
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL
            )
        ''')
        cursor.executemany(f'INSERT INTO {table_name} (content) VALUES (?)', [(note,) for note in notes])
        conn.commit()

# Fetch all content from all dynamically created tables
def get_all_tables_content():
    with sqlite3.connect('notes.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT IN ('sqlite_sequence', 'notes')")
        tables = cursor.fetchall()
        all_notes = []
        for table in tables:
            table_name = table[0]
            cursor.execute(f'SELECT content FROM {table_name}')
            notes = cursor.fetchall()
            all_notes.extend([(table_name, note[0]) for note in notes])
        return all_notes

# Fetch all dynamically created table names
def get_all_table_names():
    with sqlite3.connect('notes.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT IN ('sqlite_sequence', 'notes')")
        return [table[0] for table in cursor.fetchall()]

# Fetch all content from a specific table and convert to Markdown
def get_table_content(table_name):
    with sqlite3.connect('notes.db') as conn:
        cursor = conn.cursor()
        cursor.execute(f'SELECT content FROM {table_name}')
        return [markdown.markdown(row[0]) for row in cursor.fetchall()]

# Validate table name to ensure it is safe for SQL
def validate_table_name(table_name):
    return re.match(r'^[a-zA-Z0-9_]+$', table_name)

# Rename a table
def rename_table(old_name, new_name):
    if not validate_table_name(new_name):
        raise ValueError("Invalid table name. Use only letters, numbers, and underscores.")
    with sqlite3.connect('notes.db') as conn:
        cursor = conn.cursor()
        cursor.execute(f'ALTER TABLE {old_name} RENAME TO {new_name}')
        conn.commit()

# Utility function to sanitize table names
def sanitize_table_name(table_name):
    return table_name.replace('note_table_', '')

# Delete a table
def delete_table(table_name):
    with sqlite3.connect('notes.db') as conn:
        cursor = conn.cursor()
        cursor.execute(f'DROP TABLE IF EXISTS {table_name}')
        conn.commit()

@app.route('/')
def index():
    tables = get_all_table_names()
    return render_template('index.html', tables=tables)

@app.route('/add', methods=['POST'])
def add_note():
    note = request.form.get('note')
    table_name = request.form.get('table_name')
    if not table_name or not validate_table_name(table_name):
        flash('Invalid table name. Use only letters, numbers, and underscores.')
        return redirect(url_for('index'))
    if note:
        blocks = [block.strip() for block in note.splitlines() if block.strip()]
        if blocks:
            create_table_for_notes(table_name, blocks)  # Pass sanitized table name
    return redirect(url_for('index'))

@app.route('/rename_table', methods=['POST'])
def rename_table_route():
    data = request.get_json()
    old_name = data.get('old_name')
    new_name = data.get('new_name')
    if not old_name or not new_name:
        return jsonify({'error': 'Both old and new table names are required.'}), 400
    try:
        rename_table(old_name, new_name)  # Use raw table names directly
        return jsonify({'success': True}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except sqlite3.OperationalError as e:
        return jsonify({'error': f'Error renaming table: {str(e)}'}), 500

@app.route('/delete_table/<table_name>', methods=['POST'])
def delete_table_route(table_name):
    try:
        delete_table(table_name)
        return jsonify({'success': True}), 200
    except sqlite3.OperationalError:
        return jsonify({'error': 'Error deleting table. Please try again.'}), 500

@app.route('/delete/<int:note_id>')
def delete_note(note_id):
    delete_note_from_db(note_id)
    return redirect(url_for('index'))

@app.route('/note/<int:note_id>')
def view_note(note_id):
    note = get_note_by_id(note_id)
    tables = get_all_table_names()
    if note:
        note_content = markdown.markdown(note[0])  # Convert the note to HTML
        return render_template('note.html', note=note_content, note_id=note_id, tables=tables)
    return redirect(url_for('index'))

@app.route('/all_notes')
def all_notes():
    # Fetch all content from all dynamically created tables
    notes = get_all_tables_content()
    # Convert note content to HTML using Markdown
    formatted_notes = [(note[0], markdown.markdown(note[1])) for note in notes]
    return render_template('all_notes.html', notes=formatted_notes)

@app.route('/tables')
def list_tables():
    # Fetch all dynamically created table names
    tables = get_all_table_names()
    return render_template('list_tables.html', tables=tables)

@app.route('/table/<table_name>')
def view_table(table_name):
    # Fetch all content from the specified table
    tables = get_all_table_names()

    try:
        content = get_table_content(table_name)
        return render_template('view_table.html', table_name=table_name, content=content, tables=tables)
    except sqlite3.OperationalError:
        return redirect(url_for('list_tables'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
