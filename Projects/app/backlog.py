from asyncio import tasks
import functools
import datetime
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, DateField, TextAreaField, SelectField, SubmitField, TimeField
from wtforms_sqlalchemy.fields import QuerySelectField
from wtforms.validators import *

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from .db_models import db, Backlog, TeamMember, SprintModel, TaskPriority, TaskStatus, TaskTag, sort_priority
from sqlalchemy import case

backlog_bp = Blueprint('backlog', __name__, url_prefix='/backlog')

class Tasks(FlaskForm):
    taskName = StringField(
        'Task Name',
        [Length(min=2, max=50, message='Task name must be in between 2 & 50 characters'),
        Regexp(regex='^[A-Za-z0-9\s]+$',
            message="Task name must only contain alphabetic or numeric characters"),
        InputRequired()]
    )
    description = TextAreaField(
        'Description',
        [InputRequired(),
        Length(max=150, message='No more than 150 characters')]
    )
    start_date = DateField('Start Date', format='%Y-%m-%d', validators=[Optional()])
    complete_date = DateField('Complete Date', format='%Y-%m-%d', validators=[Optional()])
    story_points = IntegerField('Story Points', [NumberRange(min=1, max=10,
                                                 message="The number range for Story Points is between 1 and 10"),
                                                 InputRequired()])
    time_taken = TimeField("Time taken", validators=[Optional()])
    priority = SelectField('Priority', choices=[priority.value for priority in TaskPriority])
    tag = SelectField('Tag', choices=[tag.value for tag in TaskTag])
    status = SelectField('Status', choices=[status.value for status in TaskStatus], default=TaskStatus.TO_DO.value)
    team_member_id = QuerySelectField(query_factory=lambda: TeamMember.query, validators=[Optional()], allow_blank=True)
    sprint_id = QuerySelectField(query_factory=lambda: SprintModel.query, validators=[Optional()], allow_blank=True)
    submit = SubmitField('Submit')

    def from_db(self, task_model: Backlog):
        self.taskName.data = task_model.taskName
        self.description.data = task_model.description
        self.start_date.data = task_model.start_date
        self.complete_date.data = task_model.complete_date
        self.story_points.data = task_model.story_points
        self.priority.data = task_model.priority
        self.tag.data = task_model.tag
        self.status.data = task_model.status
        self.time_taken.data = datetime.time(
            hour=int(task_model.time_taken.total_seconds() // 3600),
            minute=int(task_model.time_taken.total_seconds() % 3600 // 60)
        )
        # Get the team member from its database by ID
        member_id = -1 if not task_model.team_member_id else int(task_model.team_member_id)
        if member_id > 0:
            team_member = TeamMember.query.get_or_404(member_id)
            self.team_member_id.data = team_member
        # Get the sprint from its database by ID
        sprint_id = -1 if not task_model.sprint_id else int(task_model.sprint_id)
        if sprint_id > 0:
            sprint = SprintModel.query.get_or_404(sprint_id)
            self.sprint_id.data = sprint

    def validate_complete_date(self, complete_date):
        if self.start_date.data and complete_date.data is not None:
            if complete_date.data < self.start_date.data:
                complete_date.errors.append("Complete date must be set after the start date")
    

def update_start_and_end_times(task_to_edit: Backlog, taskForm: Tasks):
    """If a task's status has changed in the last edit, see if:
        - We need to set the start date
        - We need to set or re-set the end date

    Args:
        task_to_edit (Backlog): The task backlog item we're editing
        taskForm (Tasks): the form containing user inputs
    """
    if taskForm.status.data == TaskStatus.IN_PROGRESS.value and \
        task_to_edit.start_date is None:
            task_to_edit.start_date = datetime.date.today()
    elif taskForm.status.data == TaskStatus.COMPLETED.value:
        task_to_edit.complete_date = datetime.date.today()

    
'''
show_backlog() function will be responsible to add data and display all the data in the Backlog table
'''
@backlog_bp.route('/<filter_tag>', methods=['POST', 'GET'])
def show_backlog(filter_tag: str):
    taskForm = Tasks()
    if taskForm.validate_on_submit():
        # Required fields
        taskName = taskForm.taskName.data
        description = taskForm.description.data
        story_points = taskForm.story_points.data
        priority = taskForm.priority.data
        tag = taskForm.tag.data
        start_date = taskForm.start_date.data
        complete_date = taskForm.complete_date.data

        # Optional Query fields
        if taskForm.team_member_id.data is None:
            team_member_id = ''
        else:
            team_member_id = taskForm.team_member_id.data.id

        if taskForm.sprint_id.data is None:
            sprint_id = ''
        else:
            sprint_id = taskForm.sprint_id.data.id

        # Filling out db instance with the obtained info
        new_task = Backlog(taskName=taskName, description=description, story_points=story_points, priority=priority,
                           tag=tag, status='Not Started', start_date=start_date, complete_date=complete_date,
                           team_member_id=team_member_id, sprint_id=sprint_id)

        try:
            # update the database and reload the page
            db.session.add(new_task)
            db.session.commit()

            return redirect(f'/backlog/{filter_tag}')
        except:
            return "There was an issue adding your task to the product backlog"
    else:
        # Display all tasks from the database in the backlog
        tasks = Backlog.query.filter(Backlog.sprint_id == "").order_by(sort_priority, Backlog.id).all()
        team_members = [str(TeamMember.query.get_or_404(task.team_member_id))
                        if task.team_member_id is not None and task.team_member_id != ""
                        else "" for task in tasks]
        sprints = [str(SprintModel.query.get_or_404(task.sprint_id)) if task.sprint_id is not None
                   and task.sprint_id != "" else "" for task in tasks]
        return render_template('backlog.html', tasks=tasks, members=team_members, sprints=sprints, zip=zip,
                               taskForm=taskForm, filter_tag=filter_tag)


'''
edit_task() function will edit the specified task's data in the Backlog table
'''
@backlog_bp.route('/edit/<int:_id>/<filter_tag>', methods=['GET', 'POST'])
def edit_task(_id: int, filter_tag: str):
    # Get the task to edit by their id
    task_to_edit = Backlog.query.get_or_404(_id)
    taskForm = Tasks()

    if taskForm.validate_on_submit():
        # Update details in the database from the form
        task_to_edit.taskName = taskForm.taskName.data
        task_to_edit.description = taskForm.description.data
        task_to_edit.story_points = taskForm.story_points.data
        task_to_edit.priority = taskForm.priority.data
        task_to_edit.tag = taskForm.tag.data
        task_to_edit.status = taskForm.status.data
        task_to_edit.start_date = taskForm.start_date.data
        task_to_edit.complete_date = taskForm.complete_date.data

        if taskForm.team_member_id.data is not None:
            task_to_edit.team_member_id = taskForm.team_member_id.data.id

        if taskForm.sprint_id.data is not None:
            task_to_edit.sprint_id = taskForm.sprint_id.data.id

        try:
            db.session.commit()
            flash("Task updated successfully!")
            # return to display the task
            return redirect(f'/backlog/{filter_tag}')
        except:
            flash("Task update fail! Try again!")
            return redirect(f'/backlog/{filter_tag}')

    else:
        # display edit form with the provided task's information
        taskForm.from_db(task_to_edit)
        tasks = Backlog.query.order_by(sort_priority, Backlog.id).all()
        team_members = [str(TeamMember.query.get_or_404(task.team_member_id))
                        if task.team_member_id is not None and task.team_member_id != ""
                        else "" for task in tasks]
        sprints = [str(SprintModel.query.get_or_404(task.sprint_id)) if task.sprint_id is not None
                   and task.sprint_id != "" else "" for task in tasks]
        return render_template('edit_task.html', tasks=tasks, members=team_members, sprints=sprints, zip=zip,
                               taskForm=taskForm, _id=_id, filter_tag=filter_tag)


'''
delete_task() function will delete the specified task's data in the Backlog table
'''
@backlog_bp.route('/delete/<int:id>/<filter_tag>')
def delete_task(id: int, filter_tag: str):
    task_to_delete = Backlog.query.get_or_404(id)
    try:
        # Remove from database and display again
        db.session.delete(task_to_delete)
        db.session.commit()
        return redirect(f'/backlog/{filter_tag}')
    except:
        return 'There was a problem deleting that task'
