import functools
import datetime
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DateField, EmailField
from wtforms.validators import *

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from .db_models import db, TeamMember
from werkzeug.security import check_password_hash, generate_password_hash

team_bp = Blueprint('team', __name__, url_prefix='/team')


class Member(FlaskForm):
    givenName = StringField('Given Name',
                            [Length(min=2, max=50, message='Given name must be in between 2 & 50 characters'),
                             Regexp(regex='^[A-Za-z\s-]+$',
                                    message="Given name must only contain alphabetic characters"),
                             InputRequired()])
    familyName = StringField('Family Name',
                             [Length(min=2, max=50, message="Family name must be in between 2 & 50 characters"),
                              Regexp(regex='^[A-Za-z\s-]+$',
                                     message="Family name must only contain alphabetic characters"),
                              InputRequired()])
    dob = DateField('Date of Birth', format='%Y-%m-%d', validators=[InputRequired()])
    contact_no = StringField('Number',
                             [Length(min=10, max=10, message="Mobile number must be in 10 numeric characters"),
                              Regexp(regex='^[0-9]+$',
                                     message="Contact number must be stored in 10-digits format"),
                              InputRequired()])
    email = EmailField('E-mail', validators=[Regexp(regex=r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z\.]{2,}\b',
                                                     message="Invalid E-mail format"), InputRequired()])
    submit = SubmitField('Submit')
    
    def from_db(self, team_member_model: TeamMember) -> None:
        self.givenName.data = team_member_model.givenName
        self.familyName.data = team_member_model.familyName
        self.dob.data = team_member_model.dob
        self.contact_no.data = team_member_model.contact_no
        self.email.data = team_member_model.contact_email

    def validate_dob(self, dob):
        if (datetime.datetime.today().year - dob.data.year) < 18:
            dob.errors.append("The new team member must be at least 18 years old")


'''
show_team() function will be responsible to add data and display all the data in the TeamMember table
'''
@team_bp.route('/', methods=['POST', 'GET'])
def show_team():
    memberForm = Member()
    if memberForm.validate_on_submit():
        givenName = memberForm.givenName.data
        familyName = memberForm.familyName.data
        dob = memberForm.dob.data
        contact_no = memberForm.contact_no.data
        contact_email = memberForm.email.data

        new_member = TeamMember(givenName=givenName, familyName=familyName, dob=dob, contact_no=contact_no,
                                contact_email=contact_email)

        try:
            # attempt to update the database with the new information
            db.session.add(new_member)
            db.session.commit()

            # return to the team page to display the newly added member
            return redirect('/team')
        except Exception as e:
            return f"There was an issue adding a new member to the team's database\n{e}"
    else:
        team = TeamMember.query.all()
        return render_template('team.html', team=team, memberForm=memberForm)


'''
edit_member() function will edit the specified team member's data in the TeamMember table
'''
@team_bp.route('/edit/<int:_id>', methods=['GET', 'POST'])
def edit_member(_id):
    # Get the member to edit by their id
    member_to_edit = TeamMember.query.get_or_404(_id)
    memberForm = Member()

    if memberForm.validate_on_submit():
        # Update details in the database from the form
        member_to_edit.givenName = memberForm.givenName.data
        member_to_edit.familyName = memberForm.familyName.data
        member_to_edit.dob = memberForm.dob.data
        member_to_edit.contact_no = memberForm.contact_no.data
        member_to_edit.contact_email = memberForm.email.data

        try:
            db.session.commit()
            # return to display the team members
            return redirect('/team')
        except Exception as e:
            return f'There was an issue updating the team member:\n{e}'

    else:
        # display edit form with the provided member's information
        memberForm.from_db(member_to_edit)
        team = TeamMember.query.order_by(TeamMember.familyName).all()
        return render_template('edit_team.html', team=team,
                               memberForm=memberForm, _id=_id)


'''
delete_member() function will delete the specified team member's data in the TeamMember table
'''
@team_bp.route('/delete/<int:_id>')
def delete_member(_id):
    # Get the member to delete by their id
    member_to_delete = TeamMember.query.get_or_404(_id)

    try:
        # remove them from the database and return to display the team
        db.session.delete(member_to_delete)
        db.session.commit()
        return redirect('/team')
    except:
        return 'There was an issue deleting the team member'
