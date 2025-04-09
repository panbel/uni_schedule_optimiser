# web/app.py
import os
import io
import base64
import calendar
from datetime import datetime

import pandas as pd
import matplotlib.pyplot as plt
from flask import Flask, render_template, request, redirect, url_for, flash

# Import our scheduling and calendar modules
from scheduler.scheduler import read_and_analyze_data, schedule_exams
from scheduler.calendar_utils import generate_calendar_images

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"
app.secret_key = "your_secret_key_here"  # Replace with your secret key

# The following uses templates from the "templates" folder in the web subfolder.
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/schedule", methods=["POST"])
def schedule():
    if "file" not in request.files:
        flash("No file part")
        return redirect(request.url)
    file = request.files["file"]
    if file.filename == "":
        flash("No selected file")
        return redirect(request.url)
    
    # Parse dates from form
    try:
        first_date = datetime.strptime(request.form.get("first_date"), "%Y-%m-%d")
        last_date = datetime.strptime(request.form.get("last_date"), "%Y-%m-%d")
    except Exception as e:
        flash("Error parsing exam dates. Use YYYY-MM-DD format.")
        return redirect(url_for("index"))
    
    excluded_str = request.form.get("excluded_dates", "").strip()
    excluded_dates = []
    if excluded_str:
        for ds in excluded_str.split(","):
            try:
                excluded_dates.append(datetime.strptime(ds.strip(), "%Y-%m-%d"))
            except Exception as e:
                flash(f"Error parsing excluded date: {ds}")
                return redirect(url_for("index"))
    
    fixed_str = request.form.get("fixed_schedules", "").strip()
    fixed_schedules = {}
    if fixed_str:
        for pair in fixed_str.split(","):
            try:
                exam_id, date_str = pair.split("=")
                fixed_schedules[exam_id.strip()] = datetime.strptime(date_str.strip(), "%Y-%m-%d")
            except Exception as e:
                flash(f"Error parsing fixed schedule pair: {pair}. Format should be EX_ID=YYYY-MM-DD.")
                return redirect(url_for("index"))
    
    try:
        data = read_and_analyze_data(file)
    except Exception as e:
        flash("Error reading Excel file. Ensure it's a valid Excel file.")
        return redirect(url_for("index"))
    
    exam_dates, final_schedule = schedule_exams(data, first_date, last_date, excluded_dates, fixed_schedules)
    calendar_images = generate_calendar_images(exam_dates)
    month_names = {i: calendar.month_name[i] for i in range(1, 13)}
    
    return render_template("result.html", schedule=final_schedule, calendar_images=calendar_images, months=month_names)

if __name__ == "__main__":
    if not os.path.exists(app.config["UPLOAD_FOLDER"]):
        os.makedirs(app.config["UPLOAD_FOLDER"])
    app.run(debug=True)
