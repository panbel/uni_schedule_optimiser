import pandas as pd
from datetime import datetime, timedelta
import calendar
import matplotlib.pyplot as plt

def read_and_analyze_data(filepath):
    data = pd.read_excel(filepath, engine='openpyxl')
    #print("First few rows of the data:")
    #print(data.head())
    num_students = data['Student ID'].nunique()
    num_exams = data['Exam ID'].nunique()
    #print("\nSummary Statistics:")
    #print(f"Total number of students: {num_students}")
    #print(f"Total number of exams: {num_exams}")
    return data

def find_weekdays(start_date, end_date, excluded_dates=[]):
    weekdays = []
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() < 5 and current_date not in excluded_dates:
            weekdays.append(current_date)
        current_date += timedelta(days=1)
    return weekdays

def schedule_exams(data, start_date, end_date, excluded_dates, fixed_schedules):
    """
    Schedules the exams such that no student is double-booked on a single day.
    Gives priority to fixed_schedules.
    """
    # --- Identify valid days ---
    available_days = find_weekdays(start_date, end_date, excluded_dates)
    
    # --- Build lookups ---
    exam_students = {}
    exam_course = {}
    for exam in data['Exam ID'].unique():
        subset = data[data['Exam ID'] == exam]
        exam_students[exam] = subset['Student ID'].unique().tolist()
        exam_course[exam] = subset['Course Name'].iloc[0] if not subset.empty else "Unknown Course"
    
    # --- Initialize schedules ---
    exam_dates = {}  # exam -> date
    student_schedule = {student: set() for student in data['Student ID'].unique()}  # student -> set of dates

    # --- 1) Handle fixed schedules first ---
    for exam, fixed_day in fixed_schedules.items():
        if fixed_day not in available_days:
            print(f"Fixed day {fixed_day.strftime('%Y-%m-%d')} for exam {exam} is invalid/excluded.")
            continue
        conflict = False
        for student in exam_students.get(exam, []):
            if fixed_day in student_schedule[student]:
                print(f"Conflict: Student {student} already has an exam on {fixed_day.strftime('%Y-%m-%d')} (fixed {exam}).")
                conflict = True
                break
        if not conflict:
            exam_dates[exam] = fixed_day
            for student in exam_students[exam]:
                student_schedule[student].add(fixed_day)

    # --- 2) Schedule remaining exams ---
    remaining_exams = [e for e in data['Exam ID'].unique() if e not in exam_dates]
    # Sort by number of students (descending), so higher-risk (larger) exams get scheduled first
    remaining_exams.sort(key=lambda e: len(exam_students[e]), reverse=True)

    for exam in remaining_exams:
        placed = False
        for day in available_days:
            # Check if all enrolled students are free on this day
            if all(day not in student_schedule[student] for student in exam_students[exam]):
                exam_dates[exam] = day
                for student in exam_students[exam]:
                    student_schedule[student].add(day)
                placed = True
                break
        if not placed:
            print(f"Could not schedule exam {exam} without conflict.")

    # --- 3) Print final schedule ---
    final_schedule = [(exam_dates[e], e, exam_course[e], len(exam_students[e])) for e in exam_dates]
    final_schedule.sort(key=lambda x: x[0])  # sort by date
    print("\nFinal Exam Schedule:")
    for date, exam, course, count in final_schedule:
        print(f"{course} ({exam}) scheduled on {date.strftime('%Y-%m-%d')} for {count} students.")
    
    # --- 4) Check overall conflicts ---
    conflicts_found = False
    for student, days in student_schedule.items():
        registered_exams = data[data['Student ID'] == student]['Exam ID'].nunique()
        # If the student has fewer scheduled days than exams, they must share at least one day.
        if len(days) < registered_exams:
            print(f"Conflict: Student {student} has {registered_exams} exams but only {len(days)} days scheduled.")
            conflicts_found = True
    if not conflicts_found:
        print("No conflicts detected. All exams are scheduled without overlapping students.")
    
    return exam_dates

def plot_calendar_month(exam_dates, year, month):
    """
    Creates and shows a calendar for the given year/month.
    Multiple exams on the same day are displayed with bullet points.
    Cells with >1 exam are shaded in light pink, 
    cells with exactly 1 exam are shaded light green,
    and empty cells remain white.
    """
    # Map day -> list of exam IDs
    day_exams = {}
    for exam, dt in exam_dates.items():
        if dt.year == year and dt.month == month:
            day = dt.day
            day_exams.setdefault(day, []).append(exam)
    
    cal_matrix = calendar.monthcalendar(year, month)
    
    # Prepare table data and color arrays
    table_data = []
    table_colors = []
    
    for week in cal_matrix:
        row_data = []
        row_colors = []
        for day in week:
            if day == 0:
                row_data.append("")
                row_colors.append("white")
            else:
                cell_text = str(day)
                if day in day_exams:
                    exams_today = day_exams[day]
                    if len(exams_today) == 1:
                        cell_text += f"\n{exams_today[0]}"
                        # Light green if exactly 1 exam
                        row_colors.append("#D5F5E3")
                        #row_colors.append("#00FF00")  # bright green
                    else:
                        # For multiple exams, use bullet points
                        bullet_list = "\n".join(f"• {ex}" for ex in exams_today)
                        cell_text += "\n" + bullet_list
                        # Light pink if multiple exams
                        row_colors.append("#F5B7B1")
                        # row_colors.append("#FF00FF")  # bright magenta
                else:
                    row_colors.append("white")
                row_data.append(cell_text)
        table_data.append(row_data)
        table_colors.append(row_colors)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.axis("off")
    the_table = ax.table(
        cellText=table_data,
        cellColours=table_colors,
        loc="center",
        cellLoc="center",
        #edges="open"
    )
    the_table.auto_set_font_size(False)
    the_table.set_fontsize(10)
    the_table.scale(1, 2)
    ax.set_title(f"{calendar.month_name[month]} {year}", fontsize=16)
    plt.show()

def plot_calendar_all_months(exam_dates):
    """
    Automatically plots calendar(s) for all months in the range of scheduled exams.
    """
    if not exam_dates:
        print("No exams were scheduled; skipping calendar plots.")
        return
    
    # Identify earliest and latest exam dates
    min_date = min(exam_dates.values())
    max_date = max(exam_dates.values())
    
    # Loop over months from min_date to max_date
    current_year, current_month = min_date.year, min_date.month
    while (current_year < max_date.year) or (current_year == max_date.year and current_month <= max_date.month):
        plot_calendar_month(exam_dates, current_year, current_month)
        
        # Increment month
        if current_month == 12:
            current_month = 1
            current_year += 1
        else:
            current_month += 1

if __name__ == "__main__":
    filepath = 'Students dummy data_v1.xlsx'
    data = read_and_analyze_data(filepath)
    
    # Scheduling parameters
    first_exam_date = datetime.strptime('2025-05-10', '%Y-%m-%d')
    last_exam_date = datetime.strptime('2025-06-10', '%Y-%m-%d')
    excluded_dates = [datetime.strptime('2025-05-15', '%Y-%m-%d')]
    fixed_schedules = {'EX8': datetime.strptime('2025-05-12', '%Y-%m-%d')}
    
    # Schedule the exams
    exam_dates = schedule_exams(data, first_exam_date, last_exam_date, excluded_dates, fixed_schedules)
    
    # Plot calendars automatically for all months in the exam_dates range
    plot_calendar_all_months(exam_dates)
