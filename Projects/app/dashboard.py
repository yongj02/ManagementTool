from cProfile import label
from functools import total_ordering
import io
from operator import add, sub 
from matplotlib.figure import Figure
import numpy as np
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from .db_models import TeamMember, db, Backlog, SprintModel, TaskTag,  TaskStatus
import datetime
import math
from itertools import accumulate

dash_bp = Blueprint('dash', __name__, url_prefix='/dash')
"""
Displays the dashboard and its contents
"""
selected_sprint = 1
@dash_bp.route('/',methods=['POST', 'GET'])
def show_dash():
    global selected_sprint
    if request.method == 'POST':
        selected_sprint = int(request.form['sprint'])
        print(selected_sprint)
        return redirect('/dash/')
    else:
        sprints = SprintModel.query.order_by(SprintModel.id).all()
        story_point_over_time= plot_points(selected_sprint)
        sprint_velocity_graph = sprint_velocity()
        plots = [story_point_over_time, sprint_velocity_graph, task_by_type(selected_sprint), task_by_status(selected_sprint)]
        total_hours, average_hours = calculate_hours(selected_sprint)
        print(selected_sprint)
        start_date = None
        if len(sprints) >= selected_sprint:
            start_date = sprints[selected_sprint-1].start_date
        return render_template('dashboard.html', options = sprints,sprint_start_date = start_date, plots=plots,total_hour= total_hours, avg_hour = average_hours)
selected_member = None
@dash_bp.route('/team/', methods=['GET','POST'])
def show_team_dash():
    global selected_member
    if request.method == 'POST':
        selected_member = int(request.form['member'])
        return redirect('/dash/team/')
    else:
        team_members = TeamMember.query.order_by(TeamMember.id).all()
        if selected_member!= None:
            member_name = team_members[selected_member-1]
            plots=[team_work(), plot_teammber_work(selected_member)]
            return render_template('dashboard_team.html', members = team_members, selected_member_info = member_name, hours = team_member_work_hr(selected_member), plots=plots)
        else:
            return render_template('dashboard_team.html', members = team_members, selected_member_info = None, plots= [])



def calculate_hours(target_sprint):
    sprints = SprintModel.query.order_by(SprintModel.id).all()
    if len(sprints) >= target_sprint:
        sprint = sprints[target_sprint-1]
        tasks = sprint.tasks
        if (len(tasks)!=0):
            total_hours = sum(task.time_taken.total_seconds()//3600 for task in tasks if task.time_taken != None)
            average_hours = total_hours/len(tasks)
        else:
            average_hours = 0
            total_hours = 0
        return total_hours, average_hours
    return 0, 0


def plot_points(target_sprint):
    # data for plotting

    # story point
    sprints = SprintModel.query.order_by(SprintModel.id).all()
    if len(sprints) >= target_sprint:
        # initialising figure
        fig = Figure()
        FigureCanvas(fig)
        fig.set_size_inches(6, 4)
        ax = fig.add_subplot(111)

        # getting target sprint and its tasks
        sprint = sprints[target_sprint-1]
        tasks = sprint.tasks

        # sprint dates 
        start = sprint.start_date
        end = sprint.end_date
        today = datetime.datetime.today().date()
        
        sprint_len_days = (end - start).days
        start_to_now_days = (today - start).days
        sprint_elapsed_days = min(sprint_len_days, start_to_now_days)

        # calculating expected average progress
        story_point_total = sum(task.story_points for task in tasks)
        average = story_point_total/sprint_len_days

        expected = [story_point_total - average * day for day in range(sprint_len_days + 1)]

        # calculating actual progress
        actual = [remaining for remaining in accumulate(
            (sum(task.story_points for task in tasks if task.complete_date != None and 
                (task.complete_date - start).days == day) for day in [day for day in range(sprint_elapsed_days + 1)]),
            sub,
            initial=story_point_total
        )]

        # Plotting
        ax.plot(expected, '--k', marker='o', label="expected")
        ax.plot(actual, 'go--', linewidth=2, markersize=4, label="reality")
        ax.legend()
        ax.xaxis.set_ticks(np.arange(0,sprint_len_days +1, int(math.ceil(sprint_len_days / 21))))
        ax.set_xlabel('DAYS')
        ax.set_ylabel('STORY POINTS')
        ax.set_title(f'Burndown chart of sprint {target_sprint}!')
        ax.grid(True)

        img = io.StringIO()
        fig.savefig(img, format='svg')
        #clip off the xml headers from the image
        svg_img = '<svg' + img.getvalue().split('<svg')[1]
        
        return svg_img


def task_by_type(target_sprint):
    # data for plotting

    #number of sprint 
    # story point
    sprints = SprintModel.query.order_by(SprintModel.id).all()
    if len(sprints)>0:
        # initialising figure
        fig = Figure()
        FigureCanvas(fig)
        fig.set_size_inches(6, 4)
        ax = fig.add_subplot(111)

        #label
        tick_label =  [type.value for type in TaskTag]
        #planned story point 
        planned_sp = [0]*len(tick_label)
        #completed story point
        completed_sp = [0]*len(tick_label)
        # check all the sprints
        for task in  sprints[target_sprint-1].tasks:
            for i, tag in enumerate(tick_label):
                if task.tag == tag:
                    #task completed time
                    complete_date = task.complete_date
                    today = datetime.datetime.today().date()
                    if  complete_date != None and complete_date< today:
                        completed_sp[i]+=1
                    else:
                        planned_sp[i]+=1

        indices = range(len(planned_sp))
        width = np.min(np.diff(indices))/3.
        ax.bar(indices-width/2, planned_sp, width,tick_label = tick_label,  color='#8A2BE2', label='planned')
        ax.bar(indices+width/2,completed_sp,width,tick_label = tick_label,  color='#20B2AA', label='completed')
        # ax.axes.set_xticklabels(tick_label)
        ax.set_ylabel('Tasks')
        ax.legend()
        ax.set_title(f'Task by Type')
        img = io.StringIO()
        fig.savefig(img, format='svg')
        #clip off the xml headers from the image
        svg_img = '<svg' + img.getvalue().split('<svg')[1]
        
        return svg_img


def sprint_velocity():
    # data for plotting

    #number of sprint 
    # story point
    sprints = SprintModel.query.order_by(SprintModel.id).all()
    if len(sprints)>0:
        # initialising figure
        fig = Figure()
        FigureCanvas(fig)
        fig.set_size_inches(6, 4)
        ax = fig.add_subplot(111)

        #planned story point 
        planned_sp = [0]*len(sprints)
        #completed story point
        completed_sp = [0]*len(sprints)
        #label
        tick_label =[None]*len(sprints)
        # check all the sprints
        for index, sprint in enumerate( sprints):
            tasks = sprint.tasks
            completed = 0
            planned = 0
            
            for task in tasks:
                #task completed time
                complete_date = task.complete_date
                today = datetime.datetime.today().date()
                planned += task.story_points
                if complete_date != None and complete_date< today:
                    completed+=task.story_points
            completed_sp.append(completed)
            planned_sp.append(planned)
            tick_label.append(sprint.sprintName)

        indices = range(len(planned_sp))
        width = np.min(np.diff(indices))/3.
        ax.bar(indices-width/2, planned_sp, width,tick_label = tick_label,  color='#8A2BE2', label='planned story point')
        ax.bar(indices+width/2,completed_sp,width,tick_label = tick_label,  color='#20B2AA', label='completed story point')
        # ax.axes.set_xticklabels(tick_label)
        ax.set_ylabel('STORY POINTS')
        ax.legend()
        ax.set_title(f'Sprint Velocity')
        img = io.StringIO()
        fig.savefig(img, format='svg')
        #clip off the xml headers from the image
        svg_img = '<svg' + img.getvalue().split('<svg')[1]
        
        return svg_img
def task_by_status(target_sprint):
    # data for plotting

    #number of sprint 
    # story point
    sprints = SprintModel.query.order_by(SprintModel.id).all()
    if len(sprints)>0:
        # initialising figure
        fig = Figure()
        FigureCanvas(fig)
        fig.set_size_inches(6, 4)
        ax = fig.add_subplot(111)

        #label
        tick_label =   [status.value for status in  TaskStatus]
        #planned story point 
        task_status = [0]*len(tick_label)
        # check all the sprints
        for task in  sprints[target_sprint-1].tasks:
            for i, status in enumerate(tick_label):
                print(task.status)
                if task.status == status:
                    task_status[i]+=1

        if len(sprints[target_sprint-1].tasks)!=0:
            pie = ax.pie(task_status, autopct='%1.1f%%', shadow=True, startangle=90)
            ax2 = fig.add_subplot(212)
            ax2.axis("off") 
            ax2.legend(pie[0],tick_label,  loc="lower right")

        ax.set_title(f'Task by Type')
        img = io.StringIO()
        fig.savefig(img, format='svg')
        #clip off the xml headers from the image
        svg_img = '<svg' + img.getvalue().split('<svg')[1]
        
        return svg_img
def team_member_work_hr(selected):
    team_members = TeamMember.query.order_by(TeamMember.id).all()
    work_hr = 0
    if selected>= len(team_members):
        member = team_members[selected-1]
        work_hr =sum(task.time_taken.total_seconds()//3600 for task in member.tasks if task.time_taken is not None)
    return work_hr

def team_work():
    # members
    team_members = TeamMember.query.order_by(TeamMember.id).all()
    if len(team_members)>0:
        # initialising figure
        fig = Figure()
        FigureCanvas(fig)
        fig.set_size_inches(6, 4)
        ax = fig.add_subplot(111)

        #planned work
        remaining= [0]*len(team_members)
        #completed work
        compeleted= [0]*len(team_members)
        #label
        tick_label =[None]*len(team_members)
        # check all the tasks
        for index, member in enumerate(team_members):
            tasks = member.tasks
            completed_num = 0
            remaining_num = 0
            
            for task in tasks:
                #task completed time
                complete_date = task.complete_date
                today = datetime.datetime.today().date()
                if complete_date != None and complete_date<= today:
                    completed_num+=1
                else:
                    remaining_num += 1
            compeleted.append(completed_num)
            remaining.append(remaining_num)
            tick_label.append(member.familyName+member.givenName)

        indices = range(len(tick_label))
        width = np.min(np.diff(indices))/3.
        ax.bar(indices-width/2, compeleted, width,tick_label = tick_label,  color='#8A2BE2', label='planned task')
        ax.bar(indices+width/2,remaining,width,tick_label = tick_label,  color='#20B2AA', label='completed task')
        # ax.axes.set_xticklabels(tick_label)
        ax.set_xlabel('Team member')
        ax.set_ylabel('Tasks')
        ax.legend()
        ax.set_title(f'Team Performance')
        img = io.StringIO()
        fig.savefig(img, format='svg')
        #clip off the xml headers from the image
        svg_img = '<svg' + img.getvalue().split('<svg')[1]
        
        return svg_img
def plot_teammber_work(selected_teammembers):
     # members
    team_members = TeamMember.query.order_by(TeamMember.id).all()
    if len(team_members)>0:
        # initialising figure
        fig = Figure()
        FigureCanvas(fig)
        fig.set_size_inches(6, 4)
        ax = fig.add_subplot(111)

        today = datetime.datetime.today().date()
        start = today - datetime.timedelta(days=today.weekday())
        end =  start + datetime.timedelta(days=6)

        sprint_len_days = (end - start).days
        start_to_now_days = (today - start).days
        sprint_elapsed_days = min(sprint_len_days, start_to_now_days)

        tasks = team_members[selected_member-1].tasks
        # calculating actual progress
        actual = [remaining for remaining in accumulate(
            (sum(task.story_points for task in tasks if task.complete_date != None and 
                (task.complete_date - start).days == day) for day in [day for day in range(sprint_elapsed_days + 1)]),
            add,
            initial=0
        )]

        ax.plot(actual, 'go--', linewidth=2, markersize=4)
        ax.xaxis.set_ticks(np.arange(0, 7), ['Mon', 'Tue', 'Wed', 'Thur', 'Fri', 'Sat', 'Sun'])
        ax.set_xlabel('DAYS')
        ax.set_ylabel('STORY POINTS')
        ax.grid(True)
        ax.set_title(f'Weekly Performace of {team_members[selected_member-1].givenName+team_members[selected_member-1].familyName}')
        img = io.StringIO()
        fig.savefig(img, format='svg')
        #clip off the xml headers from the image
        svg_img = '<svg' + img.getvalue().split('<svg')[1]
        
        return svg_img