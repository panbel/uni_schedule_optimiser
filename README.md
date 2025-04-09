# uni_schedule_optimiser
Optimise the exam schedule for universities

uni_schedule_optimiser/
│
├── scheduler/
│   ├── __init__.py            # (Can be empty; marks scheduler as a package)
│   ├── scheduler.py           # Contains functions like read_and_analyze_data, find_weekdays, schedule_exams
│   └── calendar_utils.py      # Contains functions to plot calendars (plot_calendar_month, plot_calendar_all_months)
│
├── web/
│   ├── app.py                 # Flask web application code
│   ├── templates/             # HTML templates for the web app
│   │   ├── index.html
│   │   └── result.html
│   └── static/                # CSS, JavaScript, images, etc.
│       └── style.css
│
├── data/                      # (Optional) For sample input files such as your Excel file(s)
│   └── Students dummy data_v1.xlsx
│
├── .gitignore                 # To ignore venv/ and other unnecessary files
├── requirements.txt           # List of dependencies
└── README.md                  # Project description and instructions