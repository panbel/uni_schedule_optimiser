# scheduler/calendar_utils.py
import calendar
import io
import base64
import matplotlib.pyplot as plt

def plot_calendar_month(exam_dates, year, month):
    """
    Creates a matplotlib figure for the calendar of a given month with exam IDs annotated.
    Cells with one exam are shaded light green; cells with multiple exams are shaded light pink.
    """
    # Map day -> list of exam IDs
    day_exams = {}
    for exam, dt in exam_dates.items():
        if dt.year == year and dt.month == month:
            day_exams.setdefault(dt.day, []).append(exam)
    
    cal_matrix = calendar.monthcalendar(year, month)
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
                        row_colors.append("#D5F5E3")  # light green
                    else:
                        bullet_list = "\n".join(f"• {ex}" for ex in exams_today)
                        cell_text += "\n" + bullet_list
                        row_colors.append("#F5B7B1")  # light pink
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
        edges="vertical"  # you can adjust this setting
    )
    the_table.auto_set_font_size(False)
    the_table.set_fontsize(10)
    the_table.scale(1, 2)
    ax.set_title(f"{calendar.month_name[month]} {year}", fontsize=16)
    plt.tight_layout()
    return fig

def generate_calendar_images(exam_dates):
    """
    Automatically generates base64-encoded PNG images for all months in the range of scheduled exam dates.
    Returns a dictionary with keys as (year, month) tuples and values as base64 strings.
    """
    if not exam_dates:
        return {}
    
    min_date = min(exam_dates.values())
    max_date = max(exam_dates.values())
    images = {}
    
    current_year, current_month = min_date.year, min_date.month
    while (current_year < max_date.year) or (current_year == max_date.year and current_month <= max_date.month):
        fig = plot_calendar_month(exam_dates, current_year, current_month)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        buf.seek(0)
        img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        images[(current_year, current_month)] = img_b64
        plt.close(fig)
        if current_month == 12:
            current_month = 1
            current_year += 1
        else:
            current_month += 1
    return images
