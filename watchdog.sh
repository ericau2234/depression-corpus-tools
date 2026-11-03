#!/bin/bash
# Corpus crawler watchdog: the VM restarts roughly hourly (deployments).
# Relaunch any lane that is incomplete and not currently running.
# Idempotent; safe to run every 15 min from cron.
cd /home/hatch/workspace/depression-corpus || exit 0
LOG=watchdog.log

alive() { pgrep -f "$1" >/dev/null 2>&1; }

# --- Reddit deep trawl: complete at 500 window .done files ---
n_done=$(ls data/deep2/*.done 2>/dev/null | wc -l)
if [ "$n_done" -lt 500 ] && ! alive "reddit_deep2.py"; then
  for i in 0 1 2 3 4 5 6 7 8 9; do
    nohup python3 reddit_deep2.py $i 10 >> deep2_$i.log 2>&1 &
  done
  echo "$(date '+%F %T') relaunched deep2 (windows done: $n_done/500)" >> $LOG
fi

# --- Patient.info wave2: complete when PATIENT2 DONE lands in the log ---
if ! grep -q "PATIENT2 DONE" patient2b.log 2>/dev/null && ! alive "patient2.py"; then
  nohup python3 patient2.py 37593 >> patient2b.log 2>&1 &
  echo "$(date '+%F %T') relaunched patient2" >> $LOG
fi

# --- LiveJournal: complete when LJ DONE lands in the log ---
if ! grep -q "LJ DONE" lj3.log 2>/dev/null && ! alive "lj_crawler.py"; then
  nohup python3 lj_crawler.py >> lj3.log 2>&1 &
  echo "$(date '+%F %T') relaunched lj" >> $LOG
fi
