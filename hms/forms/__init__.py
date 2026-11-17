"""
hms/forms/__init__.py
WTForms input validation layer (S-10).
Provides strict server-side validation, length caps, and enum whitelists.
"""
from wtforms import DecimalField, Form, PasswordField, SelectField, StringField, validators


class LoginForm(Form):
    email = StringField('Email', [
        validators.DataRequired(),
        validators.Email(),
        validators.Length(max=120)
    ])
    password = PasswordField('Password', [validators.DataRequired()])


class SignupForm(Form):
    username = StringField('Username', [
        validators.DataRequired(),
        validators.Length(min=3, max=80)
    ])
    email = StringField('Email', [
        validators.DataRequired(),
        validators.Email(),
        validators.Length(max=120)
    ])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.Length(min=10, message="Password must be at least 10 characters long.")
    ])


class ResetPasswordForm(Form):
    password = PasswordField('New Password', [
        validators.DataRequired(),
        validators.Length(min=10, message="Password must be at least 10 characters long.")
    ])
    confirm_password = PasswordField('Confirm Password', [
        validators.DataRequired(),
        validators.EqualTo('password', message="Passwords must match.")
    ])


class AddRoomForm(Form):
    room_number = StringField('Room Number', [
        validators.DataRequired(),
        validators.Length(max=20)
    ])
    ward_type = SelectField('Ward Type', choices=[
        ('General', 'General Ward'),
        ('ICU', 'ICU'),
        ('VIP', 'VIP Suite'),
        ('Maternity', 'Maternity Ward')
    ])
    rate_per_day = DecimalField('Daily Rate (₹)', [
        validators.DataRequired(),
        validators.NumberRange(min=1.00, message="Rate per day must be greater than zero.")
    ])


class BookAppointmentForm(Form):
    doctor = StringField('Doctor', [validators.DataRequired(), validators.Length(max=100)])
    date = StringField('Date', [validators.DataRequired()])
    time = StringField('Time', [validators.DataRequired()])
    disease = StringField('Reason / Symptoms', [
        validators.DataRequired(),
        validators.Length(min=2, max=255)
    ])
