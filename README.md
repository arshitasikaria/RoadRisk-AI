# RoadRisk AI

A full-stack Road Safety Management and Accident Severity Prediction Platform (MCA40130 Mini Project,
MIT World Peace University, Pune). Built with Django, Django REST Framework, Scikit-learn / XGBoost,
Chart.js and Bootstrap, with a Power BI reporting layer.

## Quick start

Requirement: Python 3.10 or higher (tick "Add Python to PATH" while installing on Windows).

- **Windows:** double-click `run.bat`
- **macOS / Linux:** run `./run.sh`

The script creates a virtual environment, installs the requirements, creates the database, loads the real
accident dataset and the NCRB state statistics, trains the models and starts the server at
**http://127.0.0.1:8000**. The first run takes a few minutes (package download and training).
Later runs start in seconds. The app works fully offline: Bootstrap, Chart.js and icons are bundled.

Manual alternative (VS Code terminal):

    python -m venv venv
    venv\Scripts\activate          (Windows)   |   source venv/bin/activate   (macOS/Linux)
    pip install -r requirements.txt
    python manage.py migrate
    python manage.py setup_project
    python manage.py runserver

## Demo logins

| Role | Username | Password | Can do |
|---|---|---|---|
| Administrator | admin | admin123 | Everything: datasets, train/compare models, users and roles, Power BI export |
| Traffic Analyst | analyst | analyst123 | Predict, dashboard, all predictions, analytics Excel report |
| Public User | public | public123 | Predict, dashboard, own predictions and reports |
| Guest | (no login) | | Road risk search and India statistics |

New users who register become Public Users; an administrator can change roles under Administration > Users & Roles.

## Data

| Data | Source | Used for |
|---|---|---|
| 4,020 NHAI highway accident records (Pune-Solapur NH-9, Barwa-Adda-Panagarh NH-2, Nagpur and Chengapally-Walayar 2022-23) | Khanum, Kulkarni, Garg & Faheem (2025), Zenodo, doi:10.5281/zenodo.16946653, CC BY 4.0 | Model training, dashboard, road risk search, Power BI |
| State / UT / city road accident totals | NCRB, Accidental Deaths & Suicides in India, Table 1A.2 | India Statistics page |

How the accident file was prepared (`tools/prepare_nhai_dataset.py`, raw file in `raw_data/`):
the numeric codes were decoded with the authors' code tables (F1000Research 2023, 12:494, Table 1);
the raw file lists every record twice, so exact duplicates were removed (8,116 to 4,053 rows); the weekday was
derived from the date because the raw day code is inconsistent; records were assigned to corridors from
chainage and year; 10-km road stretches were built from the chainage; and the four injury classes were grouped into
Fatal / Serious (grievous) / Minor (minor or no injury). Source licence CC BY 4.0: credit the authors when you present the work.

To use your own data: Administration > Datasets > upload a CSV with the required columns
`road_name, weather, time_of_day, vehicle_type, severity` (optional: `date, corridor, area_type, road_type,
road_condition, day_of_week, cause`), then Administration > Train & Compare Models.

## Model results (honest summary)

Severity prediction on this data is hard: the factors available explain only part of what decides how severe a
crash is. Hold-out accuracy is about 0.56 against a majority-class baseline of 0.555, but weighted F1 is about
0.54 against roughly 0.40 for the baseline. The rare Fatal class (about 9 percent of records) has very low recall.
The Train page shows the exact numbers, the confusion matrix, per-class results and feature importance.

## Project structure

    manage.py, run.bat, run.sh, requirements.txt
    roadrisk/                 Django settings and root URLs
    core/models.py            User, Dataset, Accident, MLModel, Prediction, Report, Recommendation, RegionStat
    core/ml.py                Preprocessing, Random Forest vs XGBoost, evaluation, best-model selection, prediction
    core/analytics.py         Dashboard, high-risk stretches, road profile queries
    core/recommendations.py   Rule-based road safety recommendations
    core/reports.py           PDF and Excel reports
    core/ingest.py            CSV validation, de-duplication and import
    core/views.py, api.py     Web pages and REST API
    core/templates/, static/  Dark dashboard UI (sidebar layout) and bundled libraries
    core/tests.py             Automated tests (python manage.py test)
    sample_data/              Cleaned accident dataset and NCRB table
    raw_data/, tools/         Original file and the preparation script
    powerbi/                  Export CSV, dark theme and step-by-step guide
    docs/                     Project report (Word) and application screenshots

## REST API

Authenticate with a logged-in session or HTTP Basic auth.

    GET  /api/predict/            input fields and allowed values
    POST /api/predict/            predict (form or JSON fields from the GET above)
    GET  /api/stats/?corridor=Pune-Solapur (NH-9)&year=2016
    GET  /api/road-risk/?q=NH-9

## MySQL or PostgreSQL instead of SQLite (optional)

Install the driver (`pip install mysqlclient` or `pip install psycopg2-binary`), create an empty database,
set these environment variables, then run `migrate` and `setup_project`:

    set DB_ENGINE=mysql          (or postgres)
    set DB_NAME=roadrisk
    set DB_USER=root
    set DB_PASSWORD=yourpassword
    set DB_HOST=127.0.0.1

## Power BI

See `powerbi/POWERBI_GUIDE.md`. A `.pbix` file cannot be generated by code, so you build the report once in Power BI
Desktop from `powerbi/roadrisk_powerbi_data.csv`. Paste the published embed URL in `POWERBI_EMBED_URL`
(settings.py or an environment variable) to show it inside the app.

## Tests

    python manage.py test

## Troubleshooting

- "python is not recognized": reinstall Python and tick "Add to PATH".
- Port busy: `python manage.py runserver 8001`.
- Reset everything: delete `db.sqlite3`, `media/` and `ml_models/`, then run the script again.
