from flask import Flask, render_template, request, redirect, url_for
import markdown

app = Flask(__name__)

# In-memory storage for notes
notes = []

@app.route('/')
def index():
    # Convert each note to HTML using Markdown
    formatted_notes = [markdown.markdown(note) for note in notes]
    # Generate previews (truncate to 100 characters and format as Markdown)
    previews = [
        markdown.markdown(note[:100] + ("..." if len(note) > 100 else ""))
        for note in notes
    ]
    # Zip previews with their indices
    preview_data = list(zip(previews, range(len(notes))))
    return render_template('index.html', notes=formatted_notes, preview_data=preview_data)

@app.route('/add', methods=['POST'])
def add_note():
    note = request.form.get('note')
    if note:
        # Split the input into multiple blocks by any newline
        blocks = [block.strip() for block in note.splitlines() if block.strip()]
        print("Split blocks:", blocks)  # Debugging: Check the split blocks
        notes.extend(blocks)  # Add each block as a separate note
    return redirect(url_for('index'))

@app.route('/delete/<int:note_id>')
def delete_note(note_id):
    if 0 <= note_id < len(notes):
        notes.pop(note_id)
    return redirect(url_for('index'))

@app.route('/note/<int:note_id>')
def view_note(note_id):
    if 0 <= note_id < len(notes):
        note_content = markdown.markdown(notes[note_id])  # Convert the note to HTML
        return render_template('note.html', note=note_content, note_id=note_id)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
