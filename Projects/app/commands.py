import click
from flask.cli import with_appcontext

from .extensions import db
from .db_models import TeamMember, Backlog, SprintModel


"""
Flask command line interface command to re-initialise the database
"""
@click.command(name='create_db')
@with_appcontext
def create_db():
    db.drop_all()
    db.create_all()
