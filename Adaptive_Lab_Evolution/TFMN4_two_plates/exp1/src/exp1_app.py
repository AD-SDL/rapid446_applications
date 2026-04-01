import json
import os
import time
import sys

# Add the root project folder (TFMN4 directory) to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))


from utils.load_settings import try_reload_config
#Adaptive_Lab_Evolution/TFMN4_two_plates/exp1/utils

CONFIG_FILE = "/Users/cstone/Documents/RPL/repos/applications/rapid446_applications/Adaptive_Lab_Evolution/TFMN4_two_plates/exp1/exp1_settings.json"
config = {}


try_reload_config.last_mtime = None

# --- Your experiment loop ---
while True:
    config = try_reload_config(CONFIG_FILE)  # check for updates right before use

    # use config values here...
    #run_experiment_step(config)

    print(config)
    time.sleep(5)
    