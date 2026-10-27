"""Starts everything: python run.py   (or: bash start.sh)"""
import os, subprocess, sys, threading, webbrowser

os.chdir(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
if not os.path.exists('ecom.db'):
    subprocess.run([PY, 'db_init.py'], check=True)
procs = [subprocess.Popen([PY, s] + a) for s, a in
         [('generator.py', []), ('pipeline_lite.py', []), ('ml_lite.py', ['45'])]]
print('\nDashboard: http://localhost:8501   (Ctrl+C to stop everything)\n')
threading.Timer(6, webbrowser.open, ['http://localhost:8501']).start()
try:
    subprocess.run([PY, '-m', 'streamlit', 'run', 'app.py', '--browser.gatherUsageStats', 'false'])
except KeyboardInterrupt:
    pass
finally:
    for p in procs:
        p.terminate()
