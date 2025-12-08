# ---------------- IMPORTS ----------------
# These are the tools we need to make forms that users can fill out.
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, RadioField, TextAreaField, DateField, SelectMultipleField, SelectField, FileField, DateTimeField, IntegerField  # Form field types
from wtforms.validators import DataRequired, Length, ValidationError, Email, NumberRange, EqualTo, InputRequired  # Rules to check form inputs


# ---------------- REGISTRATION FORM ----------------
# This form is for users to register
class RegistrationForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])  # User's full name
    email = StringField('Email Address', validators=[DataRequired(), Email()])  # Email with validation
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])  # Password (min 6 chars)
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])  # Must match password
    submit = SubmitField('Create Account')  # Submit button

    def validate_email(self, email):
        from models import User  # Import here to avoid circular import
        user = User.query.filter_by(email=email.data).first()  # Check if email already exists
        if user:
            raise ValidationError('Email is already registered.')  # Show error if duplicate


# ---------------- LOGIN FORM ----------------
# This form is for users to log in
class LoginForm(FlaskForm):
    email = StringField('Email Address', validators=[DataRequired(), Email()])  # Email field
    password = PasswordField('Password', validators=[DataRequired()])  # Password field
    submit = SubmitField('Sign In')  # Submit button


# ---------------- BOOKING FORM ----------------
# This form is for users to book cars
class BookingForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])  # Customer name
    email = StringField('Email Address', validators=[DataRequired(), Email()])  # Customer email
    contact = StringField('Contact Number', validators=[DataRequired(), Length(min=10, max=15)])  # Phone number
    car = SelectField('Selected Car', coerce=int, validators=[DataRequired()], validate_choice=False)  # Dropdown for car selection
    pickup = DateField('Pick-up Date', validators=[DataRequired()])  # Date picker for pickup
    return_date = DateField('Return Date', validators=[DataRequired()])  # Date picker for return
    id_file = FileField('Upload Valid ID', validators=[InputRequired()])  # File upload for ID (required)
    license_file = FileField('Upload Driver License', validators=[InputRequired()])  # File upload for license
    notes = TextAreaField('Notes/Comments')  # Text area for special requests
    submit = SubmitField('Submit')  # Submit button


# ---------------- REVIEW FORM ----------------
# This form is for users to submit reviews
class ReviewForm(FlaskForm):
    rating = SelectField('Rating', choices=[
        ('5', '5 - Excellent'),
        ('4', '4 - Very Good'),
        ('3', '3 - Good'),
        ('2', '2 - Fair'),
        ('1', '1 - Poor')
    ], validators=[DataRequired()])  # Rating dropdown with descriptions
    comment = TextAreaField('Comment', validators=[Length(max=500)])  # Review text with max length
    submit = SubmitField('Submit Review')  # Submit button


# ---------------- CAR FORM ----------------
# This form is for admin to add or edit cars
class CarForm(FlaskForm):
    name = StringField('Car Name', validators=[DataRequired(), Length(min=2, max=100)])  # Car model name
    price = StringField('Price', validators=[DataRequired(), Length(min=1, max=50)])  # Daily price
    specs = StringField('Description', validators=[DataRequired(), Length(min=2, max=200)])  # Car description
    image = FileField('Main Image', validators=[DataRequired()])  # Main car image upload
    transmission = SelectField('Transmission', choices=[('Automatic', 'Automatic'), ('Manual', 'Manual')], validators=[DataRequired()])  # Auto/Manual
    fuel = SelectField('Fuel', choices=[('Gas', 'Gas'), ('Diesel', 'Diesel'), ('Electric', 'Electric')], validators=[DataRequired()])  # Fuel type
    capacity = StringField('Capacity', validators=[DataRequired(), Length(min=1, max=50)])  # Seating capacity
    engine = StringField('Engine', validators=[DataRequired(), Length(max=100)])  # Engine details
    mileage = StringField('Mileage', validators=[DataRequired(), Length(max=50)])  # Fuel efficiency
    color = StringField('Color', validators=[DataRequired(), Length(max=50)])  # Car color
    submit = SubmitField('Save Car')  # Submit button


# ---------------- USER FORM ----------------
# This form is for admin to add or edit users
class UserForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=100)])  # User name
    email = StringField('Email Address', validators=[DataRequired(), Email()])  # User email
    password = PasswordField('Password', validators=[Length(min=6)])  # Password (only for adding new users)
    is_admin = RadioField('Admin', choices=[('True', 'Yes'), ('False', 'No')], default='False')  # Admin status
    submit = SubmitField('Save User')  # Submit button
