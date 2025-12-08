# ---------------- IMPORTS ----------------
# These tools help us define tables for our database and track time
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin

# Initialize the database object
db = SQLAlchemy()


# ---------------- CAR TABLE ----------------
# This table stores cars available for rental
class Car(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # Unique ID for each car
    name = db.Column(db.String(100), nullable=False)  # Car model name
    price = db.Column(db.String(50), nullable=False)  # Daily rental price
    specs = db.Column(db.String(200), nullable=False)  # Car description
    image = db.Column(db.String(100), nullable=False)  # Main image filename
    transmission = db.Column(db.String(50), nullable=False)  # Auto or Manual
    fuel = db.Column(db.String(50), nullable=False)  # Gas, Diesel, Electric
    capacity = db.Column(db.String(50), nullable=False)  # Number of seats
    availability = db.Column(db.String(20), default='Available')  # Available/Rented/Maintenance
    engine = db.Column(db.String(100))  # Engine details
    mileage = db.Column(db.String(50))  # Fuel efficiency
    color = db.Column(db.String(50))  # Car color


# ---------------- USER TABLE ----------------
# This table stores all users (regular and admins)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)  # Unique user ID
    name = db.Column(db.String(100), nullable=False)  # Full name
    email = db.Column(db.String(100), unique=True, nullable=False)  # Email address (must be unique)
    password = db.Column(db.String(200), nullable=False)  # Hashed password
    is_admin = db.Column(db.Boolean, default=False)  # Is this user an admin?
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Account creation date


# ---------------- BOOKING TABLE ----------------
# This table stores car bookings
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # Unique booking ID
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Who made the booking
    name = db.Column(db.String(100), nullable=False)  # Customer name
    email = db.Column(db.String(100), nullable=False)  # Customer email
    contact = db.Column(db.String(20), nullable=False)  # Phone number
    car_id = db.Column(db.Integer, db.ForeignKey('car.id'), nullable=False)  # Which car was booked
    pickup_date = db.Column(db.Date, nullable=False)  # When to pick up
    return_date = db.Column(db.Date, nullable=False)  # When to return
    id_file = db.Column(db.String(200))  # Uploaded ID filename
    license_file = db.Column(db.String(200))  # Uploaded license filename
    notes = db.Column(db.Text)  # Special requests
    status = db.Column(db.String(20), default='Pending')  # Pending/Approved/Rejected/Completed
    payment_method = db.Column(db.String(50))  # Payment method selected (GCash, Cash, Card)
    payment_status = db.Column(db.String(20), default='Unpaid')  # Unpaid/Paid
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)  # When booking was made

    # Relationships - connect to other tables
    car = db.relationship('Car', backref='bookings')  # Link to car details
    user = db.relationship('User', backref='bookings')  # Link to user details


# ---------------- REVIEW TABLE ----------------
# This table stores reviews for bookings
class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # Unique review ID
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Who wrote the review
    car_id = db.Column(db.Integer, db.ForeignKey('car.id'), nullable=False)  # Which car was reviewed
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)  # Which booking this is for
    rating = db.Column(db.Integer, nullable=False)  # Star rating (1-5)
    comment = db.Column(db.Text)  # Written review
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # When review was posted


# ---------------- PAYMENT METHOD TABLE ----------------
# This table stores available payment methods
class PaymentMethod(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # Unique payment method ID
    method_name = db.Column(db.String(50), nullable=False)  # Payment method name (e.g., Credit Card, Cash, etc.)


# ---------------- PAYMENT TABLE ----------------
# This table stores payment records for bookings
class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # Unique payment ID
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Who made the payment
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)  # Which booking was paid for
    payment_method_id = db.Column(db.Integer, db.ForeignKey('payment_method.id'), nullable=False)  # Payment method used
    amount_paid = db.Column(db.Integer, nullable=False)  # Amount paid
    date_paid = db.Column(db.String(50))  # Date of payment
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # When payment was recorded

    # Relationships
    user = db.relationship('User', backref='payments')  # Link to user
    booking = db.relationship('Booking', backref='payments')  # Link to booking
    payment_method = db.relationship('PaymentMethod', backref='payments')  # Link to payment method
