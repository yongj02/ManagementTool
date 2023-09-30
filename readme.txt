FIT2101 readme file for pdev0010

###################### VIRTUALENV ########################
You may decide to run this program in a virtual environment,
to keep packages isolated from the rest of your system, so
future upgrades and changes to the external environment do
not interfere with this program, and vice versa. If so, do
the following from the group-33 directory of our git
repository (make sure you have python3 and pip3 installed
first):

# installing and creating virtual environment
pip3 install virtualenv
virtualenv env

# IF THE ABOVE DOESN'T WORK, TRY:
pip3 install virtualenv
python3 -m venv env

# Activating virtual environment (linux/macOS)
source env/bash/activate

# Activating virtual environment (windows)
.\env\Scripts\activate.bat

# Deactivating the virtual environment
deactivate


###############  INSTALLING DEPENDENCIES  ###############
This project requires some dependencies to run. These can 
be easily installed using pip. If you are using a virtual
environment, activate it. Then run

python -m pip install -r requirements.txt

# If this doesn't work, try:

python3 -m pip install -r requirements.txt

# Hopefully, this will install everything you need!
