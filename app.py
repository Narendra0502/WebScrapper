from flask import Flask, render_template
import sqlite3

app = Flask(__name__)

@app.route('/')
def index():
    conn = sqlite3.connect('events.db')
    c = conn.cursor()
    c.execute("SELECT title, date, location, description, url FROM events")
    events = c.fetchall()
    conn.close()
    return render_template('index.html', events=events)

if __name__ == "__main__":
    app.run(debug=True)