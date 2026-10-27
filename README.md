# ShopPulse: Live E-Commerce Analytics Dashboard

White-theme dashboard that updates live. No Java, no Spark install, no database server needed.

## Run it (Ubuntu, 2 minutes)
```
unzip shoppulse.zip
cd shoppulse
bash start.sh
```
Open http://localhost:8501 (it also opens automatically). Press Ctrl+C in the terminal to stop.

`start.sh` creates a virtual environment, installs the packages and starts everything.
To see the code in VS Code, run `code .` inside the folder.

## Your own data
Put your 6 files in the `data` folder, named exactly: events.csv, orders.csv, order_items.csv,
users.csv, products.csv, reviews.csv. Then run `bash start.sh`.
Without them, sample data with the same columns is created automatically.
To reload data later: delete ecom.db and run `bash start.sh` again.

## What runs
| Part | File | Job |
|---|---|---|
| Database | ecom.db (SQLite) | Stores your tables plus live data |
| Live data | generator.py | Creates new events, orders and reviews every 2 seconds |
| Pipeline | pipeline_lite.py | Loads each new micro-batch into the database, logs every batch |
| Analytics | ml_lite.py | Every 45 s: customer segments (RFM + KMeans), top-10 recommendations (SVD matrix factorisation), basket rules |
| Dashboard | app.py | Auto-refreshes every few seconds; 6 tabs; pause and speed controls in the sidebar |

## Spark version (optional, for the Hadoop/Spark syllabus)
Install Java 17 (`sudo apt install openjdk-17-jdk`) and `pip install pyspark==3.5.1`, then run
`python spark_optional/stream_pipeline.py` and `python spark_optional/batch_ml.py 60` instead of
pipeline_lite.py and ml_lite.py. Start generator.py and app.py as usual. These use Spark Structured
Streaming and MLlib (ALS, KMeans, FP-Growth) with the same database.

## Troubleshooting
| Problem | Fix |
|---|---|
| python3 -m venv fails | `sudo apt install python3-venv python3-pip` and run again |
| Port 8501 busy | Close the old run (Ctrl+C) or `pkill -f streamlit` |
| Charts show waiting | Wait about 45 seconds for the first analytics run |
| Want a clean restart | Ctrl+C, delete ecom.db, `bash start.sh` |

The live data is simulated. Say so in your report and viva.
