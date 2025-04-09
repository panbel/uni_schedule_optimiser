# web/app.py

import os
import io
import base64
import calendar
from datetime import datetime
import json

# Use non-interactive backend to avoid Tkinter issues.
import matplotlib
matplotlib.use('Agg')

import pandas as pd
import matplotlib.pyplot as plt
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_session import Session


# Import scheduling functions from our scheduler package.
from scheduler.scheduler import (
    read_and_analyze_data,
    schedule_exams_with_options,
    compute_conflict_details
)
from scheduler.calendar_utils import generate_calendar_images

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"
app.secret_key = "your_secret_key_here"  # Replace with a strong secret key

#configure your app to use server‑side sessions (was needed because I had to use flask sessions to ensure all the data flow through (i had a size limitation otherwise))
app.config["SESSION_TYPE"] = "filesystem"  # This uses the local file system for session data
app.config["SESSION_FILE_DIR"] = os.path.join(app.root_path, "flask_session")
app.config["SESSION_PERMANENT"] = False
Session(app)

@app.route("/")
def landing():
    """Render the landing page."""
    return render_template("landing.html")

@app.route("/schedule", methods=["GET"])
def schedule_page():
    """Render the scheduling input page."""
    return render_template("schedule.html")

@app.route("/schedule", methods=["POST"])
def schedule_post():
    """
    Process the scheduling form:
      - Parse the Excel file and input dates.
      - Run scheduling via schedule_exams_with_options().
      - Store the extended solution in session for the user to see by default.
      - Store conflict-minimized (forced) solution + conflict details in session,
        but do NOT show them yet in the result page.
      - If we had to extend beyond last_date, set extended_warning = True.
      - The user can later click "Force Schedule Within Range" to see conflict details.
    """
    if "file" not in request.files:
        flash("No file part provided.", "error")
        return redirect(url_for("schedule_page"))
    
    file = request.files["file"]
    if file.filename == "":
        flash("No file selected.", "error")
        return redirect(url_for("schedule_page"))
    
    try:
        first_date = datetime.strptime(request.form.get("first_date"), "%Y-%m-%d")
        last_date = datetime.strptime(request.form.get("last_date"), "%Y-%m-%d")
    except Exception:
        flash("Error parsing exam dates. Please use YYYY-MM-DD format.", "error")
        return redirect(url_for("schedule_page"))
    
    # Parse excluded dates.
    excluded_str = request.form.get("excluded_dates", "").strip()
    excluded_dates = []
    if excluded_str:
        for ds in excluded_str.split(","):
            try:
                excluded_dates.append(datetime.strptime(ds.strip(), "%Y-%m-%d"))
            except Exception:
                flash(f"Error parsing excluded date: {ds}", "error")
                return redirect(url_for("schedule_page"))
    
    # Parse fixed schedules.
    fixed_str = request.form.get("fixed_schedules", "").strip()
    fixed_schedules = {}
    if fixed_str:
        for pair in fixed_str.split(","):
            try:
                exam_id, date_str = pair.split("=")
                fixed_schedules[exam_id.strip()] = datetime.strptime(date_str.strip(), "%Y-%m-%d")
            except Exception:
                flash(f"Error parsing fixed schedule pair: {pair}. Format: EX_ID=YYYY-MM-DD.", "error")
                return redirect(url_for("schedule_page"))
    
    # Read the Excel file
    try:
        data = read_and_analyze_data(file)
    except Exception:
        flash("Error reading Excel file. Ensure it's a valid Excel file.", "error")
        return redirect(url_for("schedule_page"))
    
    # Run scheduling with multiple solutions
    solutions = schedule_exams_with_options(data, first_date, last_date, excluded_dates, fixed_schedules)
    
    # 1) Extended solution: used by default
    ext_sched = solutions["extended_solution"]["final_schedule"]
    extended_last_dt = solutions["extended_solution"]["extended_last_date"]
    
    # Convert extended solution to str-based date for the template.
    extended_solution_str = [
        (d.strftime("%Y-%m-%d"), exam, course, count) for d, exam, course, count in ext_sched
    ]
    extended_warning = (extended_last_dt > last_date) and not solutions["normal_complete"]
    if extended_warning:
        flash(f"Not all exams could be scheduled conflict-free by {last_date.strftime('%Y-%m-%d')}. "
              f"The schedule extends to {extended_last_dt.strftime('%Y-%m-%d')}.", "info")
    
    # 2) Conflict-minimized solution: stored in session but not displayed yet
    force_sched = solutions["conflict_solution"]["final_schedule"]
    force_sched_str = [
        (d.strftime("%Y-%m-%d"), exam, course, count) for d, exam, course, count in force_sched
    ]
    # Compute conflict details for forced solution
    conflict_details = compute_conflict_details(data, solutions["conflict_solution"]["exam_dates"])
    
    # Store forced solution data in session
    session['conflict_solution'] = json.dumps(force_sched_str)
    session['conflict_details'] = json.dumps(conflict_details)
    session['force_stats'] = json.dumps({
        "total_conflicts": solutions["conflict_solution"]["total_conflicts"],
        "impacted_students": solutions["conflict_solution"]["impacted_students"]
    })
    
    # 3) The chosen solution is extended by default
    session['chosen_solution'] = json.dumps(extended_solution_str)
    
    # Generate calendar images for extended solution
    calendar_images = generate_calendar_images(solutions["extended_solution"]["exam_dates"])
    month_names = {i: calendar.month_name[i] for i in range(1, 13)}
    
    return render_template(
        "result.html",
        schedule=extended_solution_str,
        calendar_images=calendar_images,
        months=month_names,
        extended_warning=extended_warning,
        extended_last_date=extended_last_dt.strftime("%Y-%m-%d") if extended_last_dt else "",
        
        # We do not pass conflict_details or forced stats here
        # since the user hasn't forced scheduling yet
        conflict_details=[],
        forced_mode=False
    )

@app.route("/force")
def force_solution():
    """
    Show the forced schedule with conflict-minimized logic.
    Display a table summarizing how many conflicts, as well as
    a table of conflict details for each student.
    """
    final_schedule_json = session.get("conflict_solution")
    if not final_schedule_json:
        flash("No conflict-minimized schedule available.", "error")
        return redirect(url_for("schedule_page"))
    
    final_schedule = json.loads(final_schedule_json)  # (date_str, exam, course, count)
    flash("Forced schedule within the requested range applied. Conflicts may occur.", "warning")
    
    # Retrieve conflict details + stats
    conflict_details_json = session.get("conflict_details")
    force_stats_json = session.get("force_stats")
    if not conflict_details_json or not force_stats_json:
        # No conflict data => error
        flash("No conflict data found in session.", "error")
        return redirect(url_for("schedule_page"))
    
    conflict_details = json.loads(conflict_details_json)  # list of (student, date, "EX1, EX2...")
    force_stats = json.loads(force_stats_json)  # {"total_conflicts": int, "impacted_students": int}
    
    # No calendar images for forced solution in this example
    calendar_images = {}
    month_names = {i: calendar.month_name[i] for i in range(1, 13)}
    
    # forced_mode = True => show conflict table + summary
    return render_template(
        "result.html", 
        schedule=final_schedule,
        calendar_images=calendar_images,
        months=month_names,
        extended_warning=False,     # No extended scheduling here
        extended_last_date="",      # Not relevant in forced mode
        conflict_details=conflict_details,
        forced_mode=True,
        total_conflicts=force_stats["total_conflicts"],
        impacted_students=force_stats["impacted_students"]
    )

@app.route("/export")
def export_schedule():
    """
    Generate an Excel file with two sheets:
      - "Exam Schedule": the chosen solution (extended or forced).
      - "Conflicts": if forced mode was used, a table of conflicts.
    """
    final_schedule_json = session.get("chosen_solution")
    if not final_schedule_json:
        flash("No schedule available to export.", "error")
        return redirect(url_for("schedule_page"))
    
    final_schedule = json.loads(final_schedule_json)
    
    # If conflict_details exist in session, we can also export them
    conflict_details_json = session.get("conflict_details")
    conflict_details = []
    if conflict_details_json:
        conflict_details = json.loads(conflict_details_json)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_schedule = pd.DataFrame(final_schedule, columns=["Scheduled Date", "Exam ID", "Course", "# of Students"])
        df_schedule.to_excel(writer, index=False, sheet_name="Exam Schedule")
        
        if conflict_details:
            df_conflicts = pd.DataFrame(conflict_details, columns=["Student ID", "Date", "Exams"])
            df_conflicts.to_excel(writer, index=False, sheet_name="Conflicts")
    
    output.seek(0)
    return send_file(
        output,
        as_attachment=True,
        download_name="exam_schedule.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

if __name__ == "__main__":
    if not os.path.exists(app.config["UPLOAD_FOLDER"]):
        os.makedirs(app.config["UPLOAD_FOLDER"])
    app.run(debug=True)
