from .extensions import db
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy import case

class TaskStatus(Enum):
    TO_DO = "Not Started"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    
class TaskTag(Enum):
    CORE = 'Core'
    UI = 'UI'
    TEST = 'Testing'

class TaskPriority(Enum):
    CRIT = 'Critical'
    HIGH = 'High'
    MID = 'Medium'
    LOW = 'Low'

class SprintStatus(Enum):
    NOT_STARTED = "Not Started"
    ACTIVE = "Active"
    COMPLETED = "Completed"

"""
Database models for teammembers, specifying all their information
"""
class TeamMember(db.Model):
    __tablename__ = 'team_member'
    id = db.Column(db.Integer, primary_key=True)
    givenName = db.Column(db.String(50), nullable=False)
    familyName = db.Column(db.String(50), nullable=False)
    dob = db.Column(db.Date, nullable=False)
    contact_no = db.Column(db.String(10), nullable=False)
    contact_email = db.Column(db.String(50), nullable=False)
    tasks = db.relationship('Backlog', backref='team_member', lazy=True)
    date_added = db.Column(db.DateTime, default=datetime.today)

    def __str__(self):
        return f"({self.id}) {self.givenName} {self.familyName}"

"""
Database models for tasks in the backlog, specifying all their information
"""
class Backlog(db.Model):
    __tablename__ = 'product_backlog'
    id = db.Column(db.Integer, primary_key=True)
    taskName = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    start_date = db.Column(db.Date, nullable=True)
    complete_date = db.Column(db.Date, nullable=True)
    story_points = db.Column(db.Integer, nullable=False)
    priority = db.Column(db.Enum(*tuple(priority.value for priority in TaskPriority)), nullable=False)
    tag = db.Column(db.Enum(*tuple(tag.value for tag in TaskTag)), nullable=False)
    status = db.Column(db.Enum(*tuple(status.value for status in TaskStatus)), nullable=False)
    team_member_id = db.Column(db.Integer, db.ForeignKey("team_member.id"), nullable=True)
    sprint_id = db.Column(db.Integer, db.ForeignKey("sprint.id"), nullable=True)
    time_taken = db.Column(db.Interval, default=timedelta(hours=0))

    def __str__(self):
        return f"({self.id}) {self.taskName}"

"""
Database models for sprints, specifying all their information
"""
class SprintModel(db.Model):
    __tablename__ = 'sprint'
    id = db.Column(db.Integer, primary_key=True)
    sprintName = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    tasks = db.relationship('Backlog', backref='sprint', lazy=True, order_by=Backlog.complete_date)
    status = db.Column(db.Enum(*tuple(status.value for status in SprintStatus)), nullable=False)

    def __str__(self):
        return f"({self.id}) {self.sprintName}"


# Sorting the priorities of the task
enums = Backlog.priority.type.enums
whens = {priority: i for i, priority in enumerate(enums)}
sort_priority = case(value=Backlog.priority, whens=whens).label("priority")
