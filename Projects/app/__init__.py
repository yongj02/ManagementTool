"""
This file is modified from the flask tutorial 
(https://flask.palletsprojects.com/en/2.2.x/tutorial/factory/).

Defines a function to initialise the flask app and the database
used to store application data. __init__.py also tells python
that this directory is a package.

Author: Max Tory
Created: 28/08/2022
Edited: 28/08/2022
"""
import os
from flask import Flask, url_for, redirect
from.commands import create_db
from .extensions import db

def create_app():
    """
    Create the flask app and database, and confirm that the app instance
    path exists
    """

    # create the Flask app
    app = Flask(__name__, instance_relative_config=True)

    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
    app.config['SECRET_KEY'] = "Secret Key"

    # connecting database and creating tables
    db.init_app(app)

    app.cli.add_command(create_db)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    from . import dashboard, sprints, team, backlog
    app.register_blueprint(dashboard.dash_bp)
    app.register_blueprint(backlog.backlog_bp)
    app.register_blueprint(sprints.sprints_bp)
    app.register_blueprint(team.team_bp)

    @app.route('/')
    def index():
        return redirect(url_for('dash.show_dash'))

    return app

if __name__ == "__main__":
    create_app().run(debug=True)
