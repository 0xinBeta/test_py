import os
import json
from datetime import datetime, timedelta

TRACKER_FILE = "balance_tracker.json"


def read_tracker_file():
    if not os.path.exists(TRACKER_FILE):
        return {}
    
    with open(TRACKER_FILE, "r") as file:
        return json.load(file)


def update_tracker_file(data):
    with open(TRACKER_FILE, "w") as file:
        json.dump(data, file)


def set_initial_balance(balance):
    data = read_tracker_file()
    data["initial_balance"] = balance
    data["start_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    update_tracker_file(data)


def get_initial_balance():
    data = read_tracker_file()
    return data.get("initial_balance", None)


def get_start_date():
    data = read_tracker_file()
    start_date_str = data.get("start_date", None)
    if start_date_str:
        return datetime.strptime(start_date_str, "%Y-%m-%d %H:%M:%S")
    return None


def should_restart_bot(current_balance):
    initial_balance = get_initial_balance()
    start_date = get_start_date()

    if initial_balance is None or start_date is None:
        set_initial_balance(current_balance)
        return False, 0

    percentage_change = (current_balance - initial_balance) / initial_balance * 100

    if abs(percentage_change) >= 1:
        time_elapsed = datetime.now() - start_date
        if time_elapsed >= timedelta(days=1):
            set_initial_balance(current_balance)
            return False, percentage_change
        else:
            return True, percentage_change
    return False, percentage_change
