from flask import Flask, render_template, request, redirect, url_for, flash
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
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'note_%'")
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
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'note_table_%'")
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

@app.route('/')
def index():
    # Fetch notes from the database
    notes = get_all_notes()
    # Convert each note to HTML using Markdown
    formatted_notes = [markdown.markdown(note[1]) for note in notes]
    # Generate previews (truncate to 100 characters and format as Markdown)
    previews = [
        markdown.markdown(note[1][:100] + ("..." if len(note[1]) > 100 else ""))
        for note in notes
    ]
    # Zip previews with their IDs
    preview_data = list(zip(previews, [note[0] for note in notes]))
    return render_template('index.html', notes=formatted_notes, preview_data=preview_data)

@app.route('/add', methods=['POST'])
def add_note():
    note = request.form.get('note')
    table_name = request.form.get('table_name')
    if not table_name or not validate_table_name(table_name):
        flash('Invalid table name. Use only letters, numbers, and underscores.')
        return redirect(url_for('index'))
    if note:
        # Split the input into multiple blocks by any newline
        blocks = [block.strip() for block in note.splitlines() if block.strip()]
        print("Split blocks:", blocks)  # Debugging: Check the split blocks
        if blocks:
            table_name = f'note_table_{table_name}'  # Prefix to avoid conflicts
            create_table_for_notes(table_name, blocks)  # Create a new table for the blocks
    return redirect(url_for('index'))

@app.route('/delete/<int:note_id>')
def delete_note(note_id):
    delete_note_from_db(note_id)
    return redirect(url_for('index'))

@app.route('/note/<int:note_id>')
def view_note(note_id):
    note = get_note_by_id(note_id)
    if note:
        note_content = markdown.markdown(note[0])  # Convert the note to HTML
        return render_template('note.html', note=note_content, note_id=note_id)
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
    try:
        content = get_table_content(table_name)
        return render_template('view_table.html', table_name=table_name, content=content)
    except sqlite3.OperationalError:
        return redirect(url_for('list_tables'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
