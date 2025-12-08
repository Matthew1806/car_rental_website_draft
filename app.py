from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, send_from_directory
from werkzeug.utils import secure_filename
from flask_wtf import CSRFProtect
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import os
from datetime import datetime, timedelta, date
from models import db, Car, User, Booking, Review, PaymentMethod
from forms import RegistrationForm, LoginForm, BookingForm, ReviewForm, CarForm, UserForm
import re

app = Flask(__name__)
app.secret_key = "supersecret"
csrf = CSRFProtect(app)

# Database settings
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'car_rental.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static/images/uploads')
app.config['IMAGES_FOLDER'] = os.path.join(app.root_path, 'static/images')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

db.init_app(app)

# Set up user login system
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Helper Functions
def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def admin_required(f):
    """Decorator to check if user is admin."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def parse_price(price_str):
    """Extract numeric price from string. Returns 0.0 if invalid."""
    if not price_str:
        return 0.0
    s = re.sub(r"[^0-9.]", "", price_str)
    try:
        return float(s)
    except Exception:
        return 0.0

def format_peso(amount):
    """Format amount as peso currency."""
    return f"₱{int(amount):,}" if float(amount).is_integer() else f"₱{amount:,.2f}"

def is_valid_status(status):
    """Check if booking status is valid."""
    return status in ['Pending', 'Approved', 'Rejected', 'Completed', 'Returned']

def get_car_stats(car_id):
    """Get average rating and review count for a car."""
    reviews = Review.query.filter_by(car_id=car_id).all()
    if not reviews:
        return None, 0
    avg_rating = sum(r.rating for r in reviews) / len(reviews)
    return round(avg_rating, 1), len(reviews)

# Public Routes
@app.route('/')
def home():
    """Homepage shows general info."""
    return render_template('index.html')

@app.route('/cars')
def cars_page():
    """Display all available cars."""
    cars = Car.query.all()
    
    # Calculate average rating for each car
    for car in cars:
        reviews = Review.query.filter_by(car_id=car.id).all()
        if reviews:
            car.average_rating = round(sum(review.rating for review in reviews) / len(reviews), 1)
            car.review_count = len(reviews)
            car.reviews = reviews
        else:
            car.average_rating = None
            car.review_count = 0
            car.reviews = []
    
    return render_template('cars.html', cars=cars)

@app.route('/cars/<int:car_id>')
def car_details(car_id):
    """Show detailed information about a specific car."""
    car = Car.query.get_or_404(car_id)
    return render_template('car_details.html', car=car)

@app.route('/cars/<int:car_id>/reviews')
def car_reviews(car_id):
    """View all reviews for a specific car"""
    car = Car.query.get_or_404(car_id)
    
    # Fetch reviews for this car (most recent first)
    raw_reviews = Review.query.filter_by(car_id=car_id).order_by(Review.created_at.desc()).all()
    
    # Build a safe list of review dicts for the template
    reviews = []
    for r in raw_reviews:
        author = None
        try:
            user = User.query.get(r.user_id)
            author = user.name if user else 'Anonymous'
        except Exception:
            author = 'Anonymous'
        
        reviews.append({
            'author': author,
            'rating': r.rating,
            'comment': r.comment,
            'created_at': r.created_at.strftime('%Y-%m-%d') if getattr(r, 'created_at', None) else None
        })
    
    # Compute average rating if not already present on car
    if not getattr(car, 'average_rating', None):
        if reviews:
            avg = round(sum(r['rating'] for r in reviews) / len(reviews), 1)
            car.average_rating = avg
            car.review_count = len(reviews)
        else:
            car.average_rating = None
            car.review_count = 0
    
    return render_template('car_reviews.html', car=car, reviews=reviews)

@app.route('/about')
def about_contact():
    """About page with company information."""
    return render_template('about_contact.html')

# API Routes
@app.route('/api/car/<int:car_id>/booked')
def api_car_booked(car_id):
    """Return a JSON list of booked ranges for a given car."""
    car = Car.query.get_or_404(car_id)
    
    # Only show Approved, Returned, and Completed bookings as blocked
    bookings = Booking.query.filter(
        Booking.car_id == car_id,
        Booking.status.in_(['Approved', 'Returned', 'Completed'])
    ).all()
    
    ranges = []
    for b in bookings:
        start = b.pickup_date
        end = b.return_date
        
        if not start or not end:
            continue
        
        if isinstance(start, datetime):
            start_str = start.strftime('%Y-%m-%d')
        elif isinstance(start, date):
            start_str = start.strftime('%Y-%m-%d')
        else:
            start_str = str(start)
        
        if isinstance(end, datetime):
            end_str = end.strftime('%Y-%m-%d')
        elif isinstance(end, date):
            end_str = end.strftime('%Y-%m-%d')
        else:
            end_str = str(end)
        
        ranges.append({'from': start_str, 'to': end_str})
    
    return jsonify({'booked_ranges': ranges})

@app.route('/api/booked-dates/<int:car_id>')
@login_required
def get_booked_dates(car_id):
    """Get booked dates for a specific car."""
    # Only approved, returned, and completed bookings block dates
    bookings = Booking.query.filter(
        Booking.car_id == car_id,
        Booking.status.in_(['Approved', 'Returned', 'Completed'])
    ).all()
    
    booked_dates = []
    for booking in bookings:
        current_date = booking.pickup_date
        while current_date <= booking.return_date:
            booked_dates.append(current_date.isoformat())
            current_date = current_date + timedelta(days=1)
    
    return jsonify({'booked_dates': booked_dates})

# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login page - authenticate users and admins."""
    form = LoginForm()
    
    if form.validate_on_submit():
        # Special handling for test admin account
        if form.email.data == 'admin@test.com' and form.password.data == 'password123':
            user = User.query.filter_by(email='admin@test.com').first()
            if not user:
                hashed_password = generate_password_hash('password123', method='pbkdf2:sha256')
                user = User(name='Admin', email='admin@test.com', password=hashed_password, is_admin=True)
                db.session.add(user)
                db.session.commit()
            else:
                user.is_admin = True
                db.session.commit()
            
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('home'))
        else:
            # Regular user authentication
            user = User.query.filter_by(email=form.email.data).first()
            if user and check_password_hash(user.password, form.password.data):
                login_user(user)
                flash('Logged in successfully!', 'success')
                return redirect(url_for('home'))
            else:
                flash('Invalid email or password.', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page - create new user accounts."""
    form = RegistrationForm()
    
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        new_user = User(name=form.name.data, email=form.email.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    """Log out the current user."""
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('home'))

# Booking Routes
@app.route('/book', methods=['GET', 'POST'])
@login_required
def book():
    """Handle car booking form - requires user login."""
    form = BookingForm()
    cars = Car.query.all()
    form.car.choices = [(car.id, f"{car.name} - {car.price}") for car in cars]
    
    if form.validate_on_submit():
        # Check for date conflicts with approved, returned, or completed bookings
        car_id = form.car.data
        pickup_date = form.pickup.data
        return_date = form.return_date.data
        
        # Get all approved/returned/completed bookings for this car
        conflicting_bookings = Booking.query.filter(
            Booking.car_id == car_id,
            Booking.status.in_(['Approved', 'Returned', 'Completed']),
            Booking.return_date >= pickup_date,
            Booking.pickup_date <= return_date
        ).all()
        
        if conflicting_bookings:
            flash('The selected dates conflict with an existing booking. Please choose different dates.', 'danger')
            return render_template('book.html', form=form, cars=cars)
        
        # Handle file uploads for ID and license
        id_filename = None
        license_filename = None
        
        if form.id_file.data and allowed_file(form.id_file.data.filename):
            id_filename = secure_filename(form.id_file.data.filename)
            form.id_file.data.save(os.path.join(app.config['UPLOAD_FOLDER'], id_filename))
        
        if form.license_file.data and allowed_file(form.license_file.data.filename):
            license_filename = secure_filename(form.license_file.data.filename)
            form.license_file.data.save(os.path.join(app.config['UPLOAD_FOLDER'], license_filename))
        
        # Create booking
        booking = Booking(
            user_id=current_user.id,
            name=form.name.data,
            email=form.email.data,
            contact=form.contact.data,
            car_id=form.car.data,
            pickup_date=form.pickup.data,
            return_date=form.return_date.data,
            id_file=id_filename,
            license_file=license_filename,
            notes=form.notes.data
        )
        
        db.session.add(booking)
        db.session.commit()
        
        flash('Your booking has been submitted successfully! Please wait for admin approval.', 'success')
        return redirect(url_for('my_bookings'))
    
    return render_template('book.html', form=form, cars=cars)

@app.route('/confirmation/<int:booking_id>')
@login_required
def confirmation(booking_id):
    """Show booking confirmation page with overlap-adjusted pricing."""
    booking = Booking.query.get_or_404(booking_id)
    
    # Ensure user can only view their own bookings (unless admin)
    if booking.user_id != current_user.id and not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))
    
    car = Car.query.get(booking.car_id)
    
    # Calculate price with overlap exclusion
    price_per_day = parse_price(car.price if car else '')
    
    # Calculate total days
    try:
        total_days = (booking.return_date - booking.pickup_date).days + 1
        if total_days < 1:
            total_days = 1
    except Exception:
        total_days = 1
    
    # Find overlapping bookings (Approved, Returned, Completed)
    overlapping_bookings = Booking.query.filter(
        Booking.car_id == booking.car_id,
        Booking.id != booking.id,
        Booking.status.in_(['Approved', 'Returned', 'Completed']),
        Booking.return_date >= booking.pickup_date,
        Booking.pickup_date <= booking.return_date
    ).all()
    
    # Calculate overlapping days
    overlapping_days = set()
    for other_booking in overlapping_bookings:
        current_date = max(booking.pickup_date, other_booking.pickup_date)
        end_date = min(booking.return_date, other_booking.return_date)
        
        while current_date <= end_date:
            overlapping_days.add(current_date)
            current_date += timedelta(days=1)
    
    # Billable days = total days - overlapping days
    days = total_days - len(overlapping_days)
    if days < 1:
        days = 1
    
    total = round(price_per_day * days, 2)
    total_display = format_peso(total)
    
    return render_template('confirmation.html', booking=booking, car=car, total_display=total_display, total_amount=total)

@app.route('/confirmation/<int:booking_id>/payment', methods=['POST'])
@login_required
def confirmation_payment(booking_id):
    """Handle payment method selection by user."""
    booking = Booking.query.get_or_404(booking_id)
    
    # Ensure user can only update their own bookings
    if booking.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))
    
    # Can only select payment if booking is approved
    if booking.status != 'Approved':
        flash('Payment can only be made for approved bookings.', 'warning')
        return redirect(url_for('my_bookings'))
    
    payment_method = request.form.get('payment_method')
    
    if payment_method:
        booking.payment_method = payment_method
        # For Cash payment, mark as Unpaid since payment is at pickup
        # For online payment (GCash/Card), keep as Unpaid until they complete the payment form
        if payment_method == 'Cash':
            booking.payment_status = 'Unpaid'  # Will pay upon pickup
        db.session.commit()
        flash('Payment method selected successfully!', 'success')
    
    return redirect(url_for('confirmation', booking_id=booking_id))

@app.route('/process-payment/<int:booking_id>', methods=['POST'])
@login_required
def process_payment(booking_id):
    """Process payment for GCash or Card."""
    booking = Booking.query.get_or_404(booking_id)
    
    # Ensure user can only process their own bookings
    if booking.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    # Can only process payment if booking is approved
    if booking.status != 'Approved':
        return jsonify({'success': False, 'message': 'Payment can only be made for approved bookings'}), 400
    
    try:
        data = request.get_json()
        payment_method = data.get('payment_method')
        
        # Here you would integrate with actual payment gateway
        # For now, we'll simulate successful payment
        
        # Update booking with payment details
        booking.payment_method = payment_method
        booking.payment_status = 'Paid'  # Mark as paid
        
        # You could store additional payment details if needed
        # For example: transaction_id, payment_date, etc.
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Payment processed successfully'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/my-bookings')
@login_required
def my_bookings():
    """Display user's booking history organized by status."""
    try:
        all_bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.submitted_at.desc()).all()
        
        # Organize bookings by status
        bookings_by_status = {
            'Pending': [],
            'Approved': [],
            'Rejected': [],
            'Returned': [],
            'Completed': []
        }
        
        for booking in all_bookings:
            status = booking.status
            if status in bookings_by_status:
                bookings_by_status[status].append(booking)
            else:
                if 'Other' not in bookings_by_status:
                    bookings_by_status['Other'] = []
                bookings_by_status['Other'].append(booking)
        
        return render_template('my_bookings.html', bookings_by_status=bookings_by_status, total_bookings=len(all_bookings))
    
    except Exception as e:
        flash('An error occurred while loading your bookings.', 'danger')
        return redirect(url_for('home'))

@app.route('/bookings/<int:booking_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_booking(booking_id):
    """Allow users to edit their pending or approved bookings."""
    booking = Booking.query.get_or_404(booking_id)
    
    # Ensure user can only edit their own bookings
    if booking.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('my_bookings'))
    
    # Only pending or approved bookings can be edited
    if booking.status not in ['Pending', 'Approved']:
        flash('You cannot edit a booking that is not pending or approved.', 'warning')
        return redirect(url_for('my_bookings'))
    
    if request.method == 'POST':
        pickup_date = request.form.get('pickup_date')
        return_date = request.form.get('return_date')
        notes = request.form.get('notes')
        
        if not pickup_date or not return_date:
            flash('Pick-up and return dates are required.', 'danger')
            return redirect(url_for('edit_booking', booking_id=booking_id))
        
        booking.pickup_date = datetime.strptime(pickup_date, '%Y-%m-%d').date()
        booking.return_date = datetime.strptime(return_date, '%Y-%m-%d').date()
        booking.notes = notes
        
        db.session.commit()
        flash('Booking updated successfully!', 'success')
        return redirect(url_for('my_bookings'))
    
    return render_template('edit_booking.html', booking=booking)

@app.route('/bookings/<int:booking_id>/delete', methods=['POST'])
@login_required
def delete_booking(booking_id):
    """Allow users to delete their own bookings."""
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        # Ensure user can only delete their own bookings
        if booking.user_id != current_user.id:
            flash('Access denied. You can only delete your own bookings.', 'danger')
            return redirect(url_for('my_bookings'))
        
        # Check if booking can be deleted (only pending or approved)
        if booking.status not in ['Pending', 'Approved']:
            flash('You can only delete pending or approved bookings.', 'warning')
            return redirect(url_for('my_bookings'))
        
        db.session.delete(booking)
        db.session.commit()
        flash('Booking deleted successfully.', 'success')
    
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the booking. Please try again.', 'danger')
        print(f"Error deleting booking: {str(e)}")
    
    return redirect(url_for('my_bookings'))

# Review Routes
@app.route('/review/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def review(booking_id):
    """Allow users to submit ratings for returned bookings."""
    booking = Booking.query.get_or_404(booking_id)
    
    # Ensure user can only review their own bookings
    if booking.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('my_bookings'))
    
    # Only returned bookings can be reviewed
    if booking.status != 'Returned':
        flash('You can only review returned bookings.', 'warning')
        return redirect(url_for('my_bookings'))
    
    # Check if review already exists
    existing_review = Review.query.filter_by(booking_id=booking_id).first()
    if existing_review:
        flash('You have already reviewed this booking.', 'info')
        return redirect(url_for('my_bookings'))
    
    form = ReviewForm()
    
    if form.validate_on_submit():
        review_obj = Review(
            user_id=current_user.id,
            car_id=booking.car_id,
            booking_id=booking_id,
            rating=form.rating.data,
            comment=form.comment.data if form.comment.data else None
        )
        
        db.session.add(review_obj)
        booking.status = 'Completed'
        db.session.commit()
        
        flash('Thank you for your review!', 'success')
        return redirect(url_for('my_bookings'))
    
    car = Car.query.get(booking.car_id)
    return render_template('review.html', form=form, booking=booking, car=car)

# Admin Routes
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Admin dashboard with statistics."""
    total_cars = Car.query.count()
    total_bookings = Booking.query.count()
    total_users = User.query.filter_by(is_admin=False).count()
    
    # Get bookings by status for dashboard display
    pending_bookings = Booking.query.filter_by(status='Pending').order_by(Booking.submitted_at.desc()).limit(5).all()
    approved_bookings = Booking.query.filter_by(status='Approved').order_by(Booking.submitted_at.desc()).limit(5).all()
    completed_bookings = Booking.query.filter_by(status='Completed').order_by(Booking.submitted_at.desc()).limit(5).all()
    rejected_bookings = Booking.query.filter_by(status='Rejected').order_by(Booking.submitted_at.desc()).limit(5).all()
    
    return render_template('admin_dashboard.html',
                         total_cars=total_cars,
                         total_bookings=total_bookings,
                         total_users=total_users,
                         pending_bookings=pending_bookings,
                         approved_bookings=approved_bookings,
                         completed_bookings=completed_bookings,
                         rejected_bookings=rejected_bookings)

@app.route('/admin/bookings')
@admin_required
def admin_bookings():
    """Admin view all bookings with optional status filter."""
    status_filter = request.args.get('status', None)
    
    if status_filter:
        bookings = Booking.query.filter_by(status=status_filter).order_by(Booking.submitted_at.desc()).all()
    else:
        bookings = Booking.query.order_by(Booking.submitted_at.desc()).all()
    
    return render_template('admin_bookings.html', bookings=bookings, status_filter=status_filter)

@app.route('/admin/bookings/<int:booking_id>')
@admin_required
def admin_booking_details(booking_id):
    """Admin view detailed booking information."""
    booking = Booking.query.get_or_404(booking_id)
    car = Car.query.get(booking.car_id)
    user = User.query.get(booking.user_id)
    
    return render_template('admin_booking_details.html', booking=booking, car=car, user=user)

@app.route('/admin/bookings/<int:booking_id>/status', methods=['POST'])
@admin_required
def admin_update_booking_status(booking_id):
    """Admin update booking status with validation."""
    booking = Booking.query.get_or_404(booking_id)
    new_status = request.form.get('status')
    current_status = booking.status
    
    # Check if payment method exists
    has_payment = booking.payment_method is not None and booking.payment_method != ''
    
    # Validation 0: Check for date overlaps when approving
    if new_status == 'Approved' and current_status == 'Pending':
        # Check for conflicting bookings with the same car
        conflicting_bookings = Booking.query.filter(
            Booking.car_id == booking.car_id,
            Booking.id != booking.id,
            Booking.status.in_(['Approved', 'Returned', 'Completed']),
            Booking.return_date >= booking.pickup_date,
            Booking.pickup_date <= booking.return_date
        ).all()
        
        if conflicting_bookings:
            conflict_details = []
            for cb in conflicting_bookings:
                conflict_details.append(f"Booking #{cb.id} ({cb.pickup_date.strftime('%b %d')} - {cb.return_date.strftime('%b %d')})")
            
            flash(f'Cannot approve booking due to date overlap with: {", ".join(conflict_details)}. Please reject this booking or ask the customer to change dates.', 'danger')
            return redirect(url_for('admin_booking_details', booking_id=booking_id))
    
    # Validation 1: Cannot change to Pending if payment method exists
    if new_status == 'Pending' and has_payment:
        flash('Cannot change status to Pending because a payment method has been selected.', 'warning')
        return redirect(url_for('admin_booking_details', booking_id=booking_id))
    
    # Validation 2: Status transition rules
    error = None
    
    if current_status == 'Pending':
        if new_status not in ['Pending', 'Approved', 'Rejected']:
            error = 'From Pending, you can only approve or reject.'
    
    elif current_status == 'Approved':
        if new_status not in ['Approved', 'Returned']:
            error = 'From Approved, you can only mark as Returned.'
    
    elif current_status == 'Rejected':
        error = 'Cannot change status from Rejected (final status).'
    
    elif current_status == 'Returned':
        if new_status in ['Pending', 'Approved', 'Rejected']:
            error = 'Cannot go back from Returned status.'
    
    elif current_status == 'Completed':
        error = 'Cannot change status from Completed (final status).'
    
    if error:
        flash(error, 'danger')
        return redirect(url_for('admin_booking_details', booking_id=booking_id))
    
    # Update status if valid
    if is_valid_status(new_status):
        booking.status = new_status
        db.session.commit()
        flash('Booking status updated successfully!', 'success')
    else:
        flash('Invalid status.', 'danger')
    
    return redirect(url_for('admin_booking_details', booking_id=booking_id))

@app.route('/admin/bookings/<int:booking_id>/delete', methods=['POST'])
@admin_required
def admin_delete_booking(booking_id):
    """Allow admins to delete any booking."""
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        # Delete associated reviews if exists
        Review.query.filter_by(booking_id=booking_id).delete()
        
        db.session.delete(booking)
        db.session.commit()
        flash('Booking deleted successfully.', 'success')
    
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the booking. Please try again.', 'danger')
        print(f"Error deleting booking: {str(e)}")
    
    return redirect(url_for('admin_bookings'))

# Admin Car Routes
@app.route('/admin/cars')
@admin_required
def admin_cars():
    """Admin view all cars."""
    cars = Car.query.all()
    return render_template('admin_cars.html', cars=cars)

@app.route('/admin/cars/add', methods=['GET', 'POST'])
@admin_required
def admin_add_car():
    """Admin add a new car."""
    form = CarForm()
    
    if form.validate_on_submit():
        # Handle main image upload
        image_filename = None
        
        if form.image.data and allowed_file(form.image.data.filename):
            image_filename = secure_filename(form.image.data.filename)
            form.image.data.save(os.path.join(app.config['IMAGES_FOLDER'], 'cars', image_filename))
        
        car = Car(
            name=form.name.data,
            price=form.price.data,
            specs=form.specs.data,
            image=f"images/cars/{image_filename}" if image_filename else None,
            transmission=form.transmission.data,
            fuel=form.fuel.data,
            capacity=form.capacity.data,
            engine=form.engine.data,
            mileage=form.mileage.data,
            color=form.color.data
        )
        
        db.session.add(car)
        db.session.commit()
        flash('Car added successfully!', 'success')
        return redirect(url_for('admin_cars'))
    
    return render_template('admin_car_form.html', form=form, title='Add Car')

@app.route('/admin/cars/<int:car_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_car(car_id):
    """Admin edit an existing car."""
    car = Car.query.get_or_404(car_id)
    form = CarForm(obj=car)
    
    if form.validate_on_submit():
        # Handle main image upload if new
        if form.image.data and allowed_file(form.image.data.filename):
            image_filename = secure_filename(form.image.data.filename)
            form.image.data.save(os.path.join(app.config['IMAGES_FOLDER'], 'cars', image_filename))
            car.image = f"images/cars/{image_filename}"
        
        car.name = form.name.data
        car.price = form.price.data
        car.specs = form.specs.data
        car.transmission = form.transmission.data
        car.fuel = form.fuel.data
        car.capacity = form.capacity.data
        car.engine = form.engine.data
        car.mileage = form.mileage.data
        car.color = form.color.data
        
        db.session.commit()
        flash('Car updated successfully!', 'success')
        return redirect(url_for('admin_cars'))
    
    return render_template('admin_car_form.html', form=form, title='Edit Car', car=car)

@app.route('/admin/cars/<int:car_id>/delete', methods=['POST'])
@admin_required
def admin_delete_car(car_id):
    """Admin delete a car and all related data (cascade)."""
    car = Car.query.get_or_404(car_id)
    
    # Cascade delete: Remove all related reviews and bookings
    Review.query.filter_by(car_id=car_id).delete()
    Booking.query.filter_by(car_id=car_id).delete()
    
    db.session.delete(car)
    db.session.commit()
    flash('Car and all related data deleted successfully!', 'success')
    return redirect(url_for('admin_cars'))

# Admin User Routes
@app.route('/admin/users')
@admin_required
def admin_users():
    """Admin view all users."""
    users = User.query.filter_by(is_admin=False).all()
    admins = User.query.filter_by(is_admin=True).all()
    return render_template('admin_users.html', users=users, admins=admins)

@app.route('/admin/users/add', methods=['GET', 'POST'])
@admin_required
def admin_add_user():
    """Admin add a new user."""
    form = UserForm()
    
    if form.validate_on_submit():
        # Use password from form or default password
        password = form.password.data if form.password.data else 'defaultpassword'
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        
        user = User(
            name=form.name.data,
            email=form.email.data,
            password=hashed_password,
            is_admin=form.is_admin.data == 'True'
        )
        
        db.session.add(user)
        db.session.commit()
        flash('User added successfully!', 'success')
        return redirect(url_for('admin_users'))
    
    return render_template('admin_user_form.html', form=form, title='Add User', is_edit=False)

@app.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_user(user_id):
    """Admin edit an existing user."""
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)
    
    if form.validate_on_submit():
        user.name = form.name.data
        user.email = form.email.data
        user.is_admin = form.is_admin.data == 'True'
        # Password is not updated when editing
        
        db.session.commit()
        flash('User updated successfully!', 'success')
        return redirect(url_for('admin_users'))
    
    return render_template('admin_user_form.html', form=form, title='Edit User', is_edit=True)

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    """Admin delete a user."""
    user = User.query.get_or_404(user_id)
    
    # Prevent deleting yourself
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin_users'))
    
    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully!', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/reports')
@admin_required
def admin_reports():
    """Admin reports page (placeholder)."""
    return render_template('admin_reports.html')

# File Serving Route
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files (ID and license documents)."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Database Initialization
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Add sample cars if not exist
        if not Car.query.first():
            sample_cars = [
                Car(
                    name="Toyota Vios 2020",
                    price="2,000",
                    specs="Automatic, 5 Seater",
                    image="images/cars/vios.png",
                    transmission="Automatic",
                    fuel="Gas",
                    capacity="5-Seater",
                    engine="1.5L 4-Cylinder",
                    mileage="25 km/l",
                    color="White"
                ),
                Car(
                    name="Honda City 2020",
                    price="2,200",
                    specs="Manual, 5 Seater",
                    image="images/cars/city.jpg",
                    transmission="Manual",
                    fuel="Gas",
                    capacity="5-Seater",
                    engine="1.5L 4-Cylinder",
                    mileage="22 km/l",
                    color="Silver"
                ),
                Car(
                    name="Mitsubishi Montero 2020",
                    price="3,500",
                    specs="Automatic, 7 Seater",
                    image="images/cars/montero.jpg",
                    transmission="Automatic",
                    fuel="Diesel",
                    capacity="7-Seater",
                    engine="2.5L Turbo Diesel",
                    mileage="15 km/l",
                    color="Black"
                )
            ]
            db.session.add_all(sample_cars)
            db.session.commit()
        
        # Create hardcoded admin user if not exist
        admin_user = User.query.filter_by(email='admin@test.com').first()
        if not admin_user:
            hashed_password = generate_password_hash('password123', method='pbkdf2:sha256')
            admin_user = User(name='Admin', email='admin@test.com', password=hashed_password, is_admin=True)
            db.session.add(admin_user)
        else:
            admin_user.is_admin = True
        
        db.session.commit()
    
    app.run(debug=True)

