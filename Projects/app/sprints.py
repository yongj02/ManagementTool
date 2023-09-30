import functools
import datetime
from matplotlib.dates import HourLocator

import nbformat.validator
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SubmitField, SelectField
from wtforms_sqlalchemy.fields import QuerySelectMultipleField
from wtforms.validators import *
from .db_models import db, SprintModel, Backlog, TaskStatus, sort_priority, SprintStatus
from .backlog import Tasks, update_start_and_end_times

sprints_bp = Blueprint('sprints', __name__, url_prefix='/sprints')


def get_not_started():
    return Backlog.query.order_by(sort_priority, Backlog.id).filter_by(status=TaskStatus.TO_DO.value)
    
def get_by_sprint_id(sprint_id: str):
    return Backlog.query.order_by(sort_priority, Backlog.id).filter_by(sprint_id=sprint_id)

"""
status_start_date method takes start_date, end_date datetime of sprint determines the status of the sprint
"""
def status_start_date(start_date: datetime, end_date: datetime):
    current_date = datetime.date.today() #current date
    if end_date <= current_date:  #Change status to completed if end_date is reached
        return "Completed"
    elif start_date > current_date: #Change status to Not Started if sprint start date is not reached yet
        return "Not Started"
    elif start_date <= current_date: #Change status to Active if sprint is started
        return "Active"

"""
changing_status method takes SprintModel as parameter and determines the status of the sprint due to changing dates
"""
def changing_status(sprint: SprintModel):
    start_date = sprint.start_date
    end_date = sprint.end_date
    status = status_start_date(start_date,end_date)
    sprint.status = status

class Sprints(FlaskForm):
    sprintName = StringField('Sprint Name',
                             [Length(min=2, max=50, message='Task name must be in between 2 & 50 characters'),
                              Regexp(regex='^[A-Za-z0-9\s\']+$',
                                     message="Task name must only contain alphabetic or numeric characters"),
                              InputRequired()])
    start_date = DateField('Start Date', format='%Y-%m-%d', validators=[InputRequired()])
    end_date = DateField('End Date', format='%Y-%m-%d', validators=[Optional()])
    tasks = QuerySelectMultipleField(query_factory=get_not_started, validators=[Optional()])
    status = SelectField('Status', choices=[status.value for status in SprintStatus], default=SprintStatus.NOT_STARTED.value)
    submit = SubmitField('Submit')

    def validate_start_date(self, start_date):
        if start_date.data is not None and\
            start_date.data < datetime.date.today():
                start_date.errors.append("Sprint cannot be created in the past")
    
    def validate_end_date(self, end_date):
        if self.start_date.data and end_date.data is not None:
            if end_date.data < self.start_date.data:
                end_date.errors.append("End date must be set after the start date")
            if datetime.timedelta(weeks=2) > end_date.data - self.start_date.data or\
                datetime.timedelta(weeks=4) < end_date.data - self.start_date.data:
                    end_date.errors.append("Sprint must be between 2-4 weeks in length")
    
    def from_db(self, sprint_model: SprintModel) -> None:
        self.sprintName.data = sprint_model.sprintName
        self.start_date.data = sprint_model.start_date
        self.end_date.data = sprint_model.end_date
        self.status.data = sprint_model.status


class SprintAddTask(FlaskForm):
    tasks = QuerySelectMultipleField("Add a task:", query_factory=lambda _id="": get_by_sprint_id(_id), validators=[Optional()])
    submit = SubmitField("Add")


'''
show_sprints() function will be responsible to add data and display all the data in the Sprint table
'''
@sprints_bp.route('/<filter_tag>', methods=['POST', 'GET'])
def show_sprints(filter_tag: str):
    sprintForm = Sprints()
    if sprintForm.validate_on_submit():
        # required fields
        start_date = sprintForm.start_date.data
        sprint_name = sprintForm.sprintName.data
        # optional fields
        end_date = sprintForm.end_date.data
        tasks = sprintForm.tasks.data
        status = status_start_date(start_date,end_date)
        new_sprint = SprintModel(sprintName=sprint_name, start_date=start_date, end_date=end_date, tasks=tasks, status=status)

        try:
            # add new sprint to the db and return to display page
            db.session.add(new_sprint)
            db.session.commit()

            return redirect(f'/sprints/{filter_tag}')
        except:
            return "There was an issue creating a new sprint"
    else:
        # load all sprints from database ordered by id and display
        sprints = SprintModel.query.order_by(SprintModel.id).all()
        # get all the tasks and sort them by which task is in which sprint
        tasks = Backlog.query.all()
        sprint_tasks = []
        for sprint in sprints:
            changing_status(sprint)
            sprint_tasks.append(get_by_sprint_id(sprint.id))
        # Get tasks in backlog
        backlog_tasks = [task for task in tasks if task.sprint_id == ""]
        # Form to add a task to a sprint
        sprintAddTaskForm = SprintAddTask()
        return render_template('sprints.html', zip=zip, sprints=sprints, sprint_tasks=sprint_tasks, 
                               backlog_tasks=backlog_tasks, sprintForm=sprintForm, 
                               add_task_form=sprintAddTaskForm, filter_tag=filter_tag)


'''
delete_sprint() function will delete the specified sprint's data in the Sprint table
'''
@sprints_bp.route('/delete/<int:id>/<filter_tag>')
def delete_sprint(id: int, filter_tag: str):
    # Get sprint to delete from db by its id
    sprint_to_delete = SprintModel.query.get_or_404(id)

    try:
        # remove sprint from db
        db.session.delete(sprint_to_delete)
        db.session.commit()
        return redirect(f'/sprints/{filter_tag}')
    except:
        return "There was a problem deleting sprint"


@sprints_bp.route('/edit/<int:_id>/<filter_tag>', methods=['GET','POST'])
def edit_sprint(_id: int, filter_tag:str):
    #Get sprint to eit from db by its id
    sprint_to_edit = SprintModel.query.get_or_404(_id)
    sprintForm = Sprints()
    sprintAddTaskForm = SprintAddTask()

    if sprintForm.validate_on_submit():
        # Update details in the database from the form
        sprint_to_edit.sprintName = sprintForm.sprintName.data
        sprint_to_edit.start_date = sprintForm.start_date.data
        sprint_to_edit.end_date = sprintForm.end_date.data
        try:
            db.session.commit()
            # return to display the sprint
            return redirect(f'/sprints/{filter_tag}')
        except Exception as e:
            return f'There was an issue updating the sprint:\n{e}'

    else:
        # display edit form with the sprints information
        sprintForm.from_db(sprint_to_edit)
        sprints = SprintModel.query.order_by(SprintModel.sprintName).all()
        sprint_tasks = []
        for sprint in sprints:
            sprint_tasks.append(get_by_sprint_id(sprint.id))
        return render_template('edit_sprint.html', zip=zip, sprints=sprints, sprint_tasks=sprint_tasks,
                               sprintForm=sprintForm, _id=_id, filter_tag=filter_tag,
                               add_task_form=sprintAddTaskForm)


@sprints_bp.route('/add_sprint_task/<int:sprint_id>/<filter_tag>', methods=['POST'])
def add_sprint_task(sprint_id: int, filter_tag: str):
    task_form = SprintAddTask()
    #if task_to_add.value = 
    if task_form.validate_on_submit():
        tasks = task_form.tasks.data
        for task_to_add in tasks:
            try:
                task_to_add.sprint_id = sprint_id
                db.session.commit()
            except Exception as e:
                return f"There was an issue adding a task to the sprint:\n{e}"
        
        return redirect(f"/sprints/{filter_tag}")


@sprints_bp.route('/edit_sprint_task/<int:_id>/<filter_tag>', methods=['GET','POST'])
def edit_sprint_task(_id: int, filter_tag: str):
    """Edit a task with a given id in the sprint board interface. 

    Args:
        _id (int): id of the task to edit
    """
    # Get the task to edit by their id
    task_to_edit = Backlog.query.get_or_404(_id)
    taskForm = Tasks()
    sprintForm = Sprints()
    sprintAddTaskForm = SprintAddTask()
    if taskForm.validate_on_submit():
        # Update details in the database from the form
        task_to_edit.taskName = taskForm.taskName.data
        task_to_edit.description = taskForm.description.data
        task_to_edit.story_points = taskForm.story_points.data
        task_to_edit.priority = taskForm.priority.data
        task_to_edit.tag = taskForm.tag.data
        if task_to_edit.status != taskForm.status.data:
            update_start_and_end_times(task_to_edit, taskForm)
        task_to_edit.status = taskForm.status.data
        try:
            task_to_edit.time_taken = datetime.timedelta(
                hours=taskForm.time_taken.data.hour,
                minutes=taskForm.time_taken.data.minute
            )
        except AttributeError:
            task_to_edit.time_taken = datetime.timedelta(0)

        # Only change team member if they selected a different one
        if taskForm.team_member_id.data is not None:
            task_to_edit.team_member_id = taskForm.team_member_id.data.id

        # Only change sprint if they selected a different one
        if taskForm.sprint_id.data is not None:
            task_to_edit.sprint_id = taskForm.sprint_id.data.id
        else:
            task_to_edit.sprint_id = ""

        try:
            db.session.commit()
            flash("Task updated successfully!")
            # return to display the task
            return redirect(f'/sprints/{filter_tag}')
        except:
            flash("Task update fail! Try again!")
            return redirect(f'/sprints/{filter_tag}')

    else:
        # display edit form with the provided task's information
        taskForm.from_db(task_to_edit)
        sprints = SprintModel.query.order_by(SprintModel.id).all()
        sprint_tasks = []
        for sprint in sprints:
            sprint_tasks.append(get_by_sprint_id(sprint.id))
        return render_template('edit_sprint_task.html', sprints=sprints, sprint_tasks=sprint_tasks, zip=zip,
                               taskForm=taskForm, sprintForm=sprintForm, _id=_id, filter_tag=filter_tag,
                               add_task_form=sprintAddTaskForm)
 