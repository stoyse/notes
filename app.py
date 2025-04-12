from flask import Flask, render_template, request, redirect, url_for
import markdown
import sqlite3

app = Flask(__name__)

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
    if note:
        # Split the input into multiple blocks by any newline
        blocks = [block.strip() for block in note.splitlines() if block.strip()]
        print("Split blocks:", blocks)  # Debugging: Check the split blocks
        for block in blocks:
            add_note_to_db(block)  # Add each block as a separate note
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
    # Fetch all notes from the database
    notes = get_all_notes()
    # Convert note content to HTML using Markdown
    formatted_notes = [(note[0], markdown.markdown(note[1])) for note in notes]
    return render_template('all_notes.html', notes=formatted_notes)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
