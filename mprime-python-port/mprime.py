#!/usr/bin/env python3

# Daniel Connelly and Teal Dulcet
# Usage: ./mprime.py [PrimeNet User ID] [Computer name] [Type of work] [Idle time to run (mins)]
# ./mprime.py "$USER" "$HOSTNAME" 150 10
# ./mprime.py ANONYMOUS

import hashlib  # sha256
import os
import re  # regular expression matching
import socket
import subprocess
import sys
import tarfile

DIR = "mprime"
FILE = "p95v308b17.linux64.tar.gz"
SUM = "5180c3843d2b5a7c7de4aa5393c13171b0e0709e377c01ca44154608f498bec7"


def misc_check(condition, err):
    if condition:
        print(err, file=sys.stderr)
        sys.exit(1)

# Source: https://stackoverflow.com/questions/22058048/hashing-a-file-in-python
# There is no sha256sum in the hashlib library normally
def sha256sum(filename):
    """Completes a checksum of the folder
    Parameters:
    filename (string): directory to be checked
    Returns:
    The hash sum string in hexidecimal digits.
    """
    h = hashlib.sha256()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(128 * h.block_size), b""):
            h.update(chunk)
    return h.hexdigest()


# Main script
USERID = sys.argv[1] if len(sys.argv) > 1 else os.environ["USER"]
COMPUTER = sys.argv[2] if len(sys.argv) > 2 else socket.gethostname()
TYPE = sys.argv[3] if len(sys.argv) > 3 else str(150)
TIME = (int(sys.argv[4]) if len(sys.argv) > 4 else 10) * 60


print(f"PrimeNet User ID:\t{USERID}")
print(f"Computer name:\t\t{COMPUTER}")
print(f"Type of work:\t\t{TYPE}")
print(f"Idle time to run:\t{TIME // 60} minutes\n")

#---Dependencies/Downloads---#
print("Asserting Python version is >= Python3.6")
assert sys.version_info >= (3, 6)

try:
    import requests
except ImportError:
    print("Installing requests dependency")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests
#----------------------------#
#---Command Line Checks------#
misc_check(len(sys.argv) > 5, f"Usage: {sys.argv[0]} [PrimeNet User ID] [Computer name] [Type of work] [Idle time to run (mins)]")
misc_check(not re.match(r"^([024568]|1(0[0124]|5[0123]|6[01])?)$", TYPE), "Usage: [Type of work] is not a valid number")
misc_check(not re.match(r"^([0-9]*\.)?[0-9]+$", TIME), "Usage: [Idle time to run] must be a number")
#----------------------------#

#---Downloading/Directory Ops---#
misc_check(os.path.exists(DIR), "Error: Prime95 is already downloaded")
print("Making directory to house contents of Prime95")
os.mkdir(DIR)
misc_check(not os.path.exists(DIR), f"Error: Failed to create directory: {DIR}")

os.chdir(DIR)
DIR = os.getcwd()

print("\nDownloading Prime95\n")
with requests.get(f"https://www.mersenne.org/download/software/v30/30.8/{FILE}", stream=True) as r:
    r.raise_for_status()
    with open(FILE, "wb") as f:
        for chunk in r.iter_content(chunk_size=None):
            if chunk:
                f.write(chunk)
misc_check(sha256sum(FILE).lower() == SUM, f'Error: sha256sum does not match. Please run "rm -r {DIR!r}" make sure you are using the latest version of this script and try running it again\nIf you still get this error, please create an issue: https://github.com/tdulcet/Distributed-Computing-Scripts/issues')

print("\nDecompressing the files")
with tarfile.open(FILE) as tar:
    tar.list()
    tar.extractall()
#---------------------------------------#

#---Configuration---#

print("Setting up Prime95.")
subprocess.check_call([sys.executable, "../exp.py", USERID, COMPUTER, TYPE])
#---------------------------------------#

#---Starting Program---#
print("Starting up Prime95.")
subprocess.Popen(["./mprime"])  # daemon process

print("\nSetting it to start if the computer has not been used in the specified idle time and stop it when someone uses the computer\n")

subprocess.check_call(fr"""crontab -l | {{ cat; echo "* * * * * if who -s | awk '{{ print \$2 }}' | (cd /dev && xargs -r stat -c '\%U \%X') | awk '{{if ('\"\${{EPOCHSECONDS:-\$(date +\%s)}}\"'-\$2<{TIME}) {{ print \$1\"\t\"'\"\${{EPOCHSECONDS:-\$(date +\%s)}}\"'-\$2; ++count }}}} END{{if (count>0) {{ exit 1 }}}}' >/dev/null; then pgrep -x mprime >/dev/null || (cd {DIR!r} && exec nohup ./mprime -d >> 'mprime.out' &); else pgrep -x mprime >/dev/null && killall mprime; fi"; }} | crontab -""", shell=True)
#----------------------#
