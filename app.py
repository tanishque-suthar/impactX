import os
import sqlite3
import subprocess
from flask import Flask, request

app = Flask(__name__)

DB_PATH = "users.db"

@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")

    # ❌ SQL Injection vulnerability
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    cursor.execute(query)

    user = cursor.fetchone()
    conn.close()

    if user:
        return "Login successful"
    return "Invalid credentials"


@app.route("/ping", methods=["GET"])
def ping():
    host = request.args.get("host")

    # ❌ Command Injection vulnerability
    output = subprocess.check_output(
        f"ping -c 1 {host}",
        shell=True
    )
    return output


@app.route("/debug", methods=["GET"])
def debug():
    # ❌ Sensitive information exposure
    return {
        "cwd": os.getcwd(),
        "env": dict(os.environ)
    }


if __name__ == "__main__":
    # ❌ Debug mode enabled in production
    app.run(debug=True)
