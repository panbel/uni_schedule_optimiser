# scheduler/scheduler.py

import pandas as pd
from datetime import datetime, timedelta
from collections import Counter

def read_and_analyze_data(filepath):
    """
    Reads the Excel file and returns a DataFrame.
    """
    data = pd.read_excel(filepath, engine='openpyxl')
    return data

def find_weekdays(start_date, end_date, excluded_dates=[]):
    """
    Returns a list of weekdays between start_date and end_date (inclusive),
    excluding any dates in excluded_dates.
    """
    weekdays = []
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() < 5 and current_date not in excluded_dates:
            weekdays.append(current_date)
        current_date += timedelta(days=1)
    return weekdays

def schedule_exams_with_options(data, first_date, last_date, excluded_dates, fixed_schedules):
    """
    Attempts to schedule exams so that no student is double-booked.
    Returns two solutions:
    
      1. extended_solution: Schedules exams conflict-free by extending the date range (if needed).
      2. conflict_solution: Forces all exams into the given range even if some conflicts occur,
         choosing days that minimize additional conflicts.
         
    Also returns a flag 'normal_complete' indicating if a conflict‑free schedule was achieved
    within the originally requested range.
    
    Returns a dictionary:
       {
         "normal_complete": <True/False>,
         "extended_solution": {
              "exam_dates": { exam: date, ... },
              "final_schedule": [ (date, exam, course, #_students), ... ],
              "extended_last_date": <datetime>
         },
         "conflict_solution": {
              "exam_dates": { exam: date, ... },
              "final_schedule": [ (date, exam, course, #_students), ... ],
              "total_conflicts": <int>,
              "impacted_students": <int>
         }
       }
    """
    # Build lookups.
    exam_students = {}
    exam_course = {}
    for exam in data['Exam ID'].unique():
        subset = data[data['Exam ID'] == exam]
        exam_students[exam] = subset['Student ID'].unique().tolist()
        exam_course[exam] = subset['Course Name'].iloc[0] if not subset.empty else "Unknown Course"
    total_exams = len(data['Exam ID'].unique())

    ### NORMAL SOLUTION: Try to schedule conflict-free within first_date and last_date.
    available_days = find_weekdays(first_date, last_date, excluded_dates)
    exam_dates_normal = {}
    student_schedule_normal = {student: set() for student in data['Student ID'].unique()}
    
    # Fixed exams first.
    for exam, fixed_day in fixed_schedules.items():
        if fixed_day not in available_days:
            continue
        conflict = False
        for student in exam_students.get(exam, []):
            if fixed_day in student_schedule_normal[student]:
                conflict = True
                break
        if not conflict:
            exam_dates_normal[exam] = fixed_day
            for student in exam_students[exam]:
                student_schedule_normal[student].add(fixed_day)
    
    # Schedule remaining exams.
    remaining_exams = [e for e in data['Exam ID'].unique() if e not in exam_dates_normal]
    remaining_exams.sort(key=lambda e: len(exam_students[e]), reverse=True)
    for exam in remaining_exams:
        placed = False
        for day in available_days:
            if all(day not in student_schedule_normal[student] for student in exam_students[exam]):
                exam_dates_normal[exam] = day
                for student in exam_students[exam]:
                    student_schedule_normal[student].add(day)
                placed = True
                break
        # If not placed, exam remains unscheduled.
    normal_complete = (len(exam_dates_normal) == total_exams)
    
    normal_schedule = [(exam_dates_normal[e], e, exam_course[e], len(exam_students[e]))
                       for e in exam_dates_normal]
    normal_schedule.sort(key=lambda x: x[0])
    
    ### OPTION 1: EXTENDED SOLUTION - Extend the date range to schedule all exams conflict-free.
    exam_dates_extended = exam_dates_normal.copy()
    student_schedule_extended = {student: set(s) for student, s in student_schedule_normal.items()}
    extended_last_date = last_date
    if len(exam_dates_extended) < total_exams:
        max_extension = 30  # maximum extra days.
        extension = 0
        while len(exam_dates_extended) < total_exams and extension < max_extension:
            extension += 7  # extend by one week.
            extended_last_date = last_date + timedelta(days=extension)
            extended_available_days = find_weekdays(first_date, extended_last_date, excluded_dates)
            unscheduled = [e for e in data['Exam ID'].unique() if e not in exam_dates_extended]
            for exam in unscheduled:
                for day in extended_available_days:
                    if all(day not in student_schedule_extended[student] for student in exam_students[exam]):
                        exam_dates_extended[exam] = day
                        for student in exam_students[exam]:
                            student_schedule_extended[student].add(day)
                        break
        extended_schedule = [(exam_dates_extended[e], e, exam_course[e], len(exam_students[e]))
                             for e in exam_dates_extended]
        extended_schedule.sort(key=lambda x: x[0])
    else:
        extended_schedule = normal_schedule
        extended_last_date = last_date
    
    extended_solution = {
         "exam_dates": exam_dates_extended,
         "final_schedule": extended_schedule,
         "extended_last_date": extended_last_date
    }
    
    ### OPTION 2: CONFLICT-MINIMIZED SOLUTION - Force all exams into the given range.
    exam_dates_conflict = {}
    student_schedule_conflict = {student: [] for student in data['Student ID'].unique()}
    for exam, fixed_day in fixed_schedules.items():
        if fixed_day in available_days:
            exam_dates_conflict[exam] = fixed_day
            for student in exam_students.get(exam, []):
                student_schedule_conflict[student].append(fixed_day)
    unscheduled = [e for e in data['Exam ID'].unique() if e not in exam_dates_conflict]
    unscheduled.sort(key=lambda e: len(exam_students[e]), reverse=True)
    for exam in unscheduled:
        best_day = None
        best_conflict = float('inf')
        for day in available_days:
            conflict_count = sum(student_schedule_conflict[student].count(day) for student in exam_students[exam])
            if conflict_count < best_conflict:
                best_conflict = conflict_count
                best_day = day
        exam_dates_conflict[exam] = best_day
        for student in exam_students[exam]:
            student_schedule_conflict[student].append(best_day)
    
    total_conflicts = 0
    impacted_students = 0
    for student, days in student_schedule_conflict.items():
        counts = {}
        for d in days:
            key = d.strftime("%Y-%m-%d")
            counts[key] = counts.get(key, 0) + 1
        student_conflicts = sum(count - 1 for count in counts.values() if count > 1)
        if student_conflicts > 0:
            impacted_students += 1
        total_conflicts += student_conflicts
    
    conflict_schedule = [(exam_dates_conflict[e], e, exam_course[e], len(exam_students[e]))
                         for e in exam_dates_conflict]
    conflict_schedule.sort(key=lambda x: x[0])
    
    conflict_solution = {
       "exam_dates": exam_dates_conflict,
       "final_schedule": conflict_schedule,
       "total_conflicts": total_conflicts,
       "impacted_students": impacted_students
    }
    
    return {
       "normal_complete": normal_complete,
       "extended_solution": extended_solution,
       "conflict_solution": conflict_solution
    }

def compute_conflict_details(data, exam_dates):
    """
    Given the input data and an exam_dates dictionary (exam -> date),
    returns a list of tuples (Student ID, Date, Comma-separated exam IDs)
    for every student that has more than one exam scheduled on the same date.
    """
    exam_students = {}
    for exam in data['Exam ID'].unique():
        subset = data[data['Exam ID'] == exam]
        exam_students[exam] = subset['Student ID'].unique().tolist()
    
    student_date_exams = {}
    for exam, dt in exam_dates.items():
        date_str = dt.strftime("%Y-%m-%d")
        for student in exam_students.get(exam, []):
            student_date_exams.setdefault(student, {}).setdefault(date_str, []).append(exam)
    
    conflict_list = []
    for student, date_dict in student_date_exams.items():
        for date_str, exams in date_dict.items():
            if len(exams) > 1:
                conflict_list.append((student, date_str, ", ".join(exams)))
    return conflict_list
