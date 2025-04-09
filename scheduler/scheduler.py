# scheduler/scheduler.py
import pandas as pd
from datetime import datetime, timedelta

def read_and_analyze_data(filepath):
    data = pd.read_excel(filepath, engine='openpyxl')
    # Optionally print some summary information if needed
    num_students = data['Student ID'].nunique()
    num_exams = data['Exam ID'].nunique()
    print(f"Total number of students: {num_students}")
    print(f"Total number of exams: {num_exams}")
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
    Fixed schedules (a dict mapping exam IDs to dates) are given priority.
    Returns a tuple: (exam_dates, final_schedule)
      - exam_dates: dict mapping exam ID -> scheduled date
      - final_schedule: list of tuples (date, exam, course, number_of_students)
    """
    available_days = find_weekdays(start_date, end_date, excluded_dates)
    
    # Build lookups: exam_students and exam_course.
    exam_students = {}
    exam_course = {}
    for exam in data['Exam ID'].unique():
        subset = data[data['Exam ID'] == exam]
        exam_students[exam] = subset['Student ID'].unique().tolist()
        exam_course[exam] = subset['Course Name'].iloc[0] if not subset.empty else "Unknown Course"
    
    exam_dates = {}  # Mapping: exam -> scheduled date.
    student_schedule = {student: set() for student in data['Student ID'].unique()}
    
    # Schedule fixed exams first.
    for exam, fixed_day in fixed_schedules.items():
        if fixed_day not in available_days:
            print(f"Fixed day {fixed_day.strftime('%Y-%m-%d')} for exam {exam} is not valid or is excluded.")
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
    
    # Schedule remaining exams.
    remaining_exams = [e for e in data['Exam ID'].unique() if e not in exam_dates]
    # Sort by enrollment size (largest first)
    remaining_exams.sort(key=lambda e: len(exam_students[e]), reverse=True)
    
    for exam in remaining_exams:
        placed = False
        for day in available_days:
            if all(day not in student_schedule[student] for student in exam_students[exam]):
                exam_dates[exam] = day
                for student in exam_students[exam]:
                    student_schedule[student].add(day)
                placed = True
                break
        if not placed:
            print(f"Could not schedule exam {exam} without conflict.")
    
    final_schedule = [(exam_dates[e], e, exam_course[e], len(exam_students[e])) for e in exam_dates]
    final_schedule.sort(key=lambda x: x[0])
    
    print("\nFinal Exam Schedule:")
    for date, exam, course, count in final_schedule:
        print(f"{course} ({exam}) scheduled on {date.strftime('%Y-%m-%d')} for {count} students.")
    
    # Check overall conflicts
    conflicts_found = False
    for student, days in student_schedule.items():
        registered_exams = data[data['Student ID'] == student]['Exam ID'].nunique()
        if len(days) < registered_exams:
            print(f"Conflict: Student {student} has {registered_exams} exams but only {len(days)} unique days scheduled.")
            conflicts_found = True
    if not conflicts_found:
        print("No conflicts detected. All exams are scheduled without overlapping students.")
    
    return exam_dates, final_schedule
