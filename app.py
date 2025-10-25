from flask import Flask, render_template, request, redirect, url_for, flash, session
from models import db, User, P_Lot, P_Spot, UserTransaction
from datetime import datetime
from datetime import timedelta
from math import ceil


app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SECRET_KEY'] = 'Aarush123@'


#connecting db and app with init_app
db.init_app(app)



def initialize_admin():
    admin = User.query.filter_by(username='Aarush').first()
    if not admin:
        admin = User(username='Aarush', email='aarushgoyal581@gmail.com', password='Admin123', role='admin', tel='1234567890')
        db.session.add(admin)
        db.session.commit()

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/user_login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Check if user exists
        user = User.query.filter_by(username=username).first()
        
        if user:
            # User exists, check password
            if user.password == password:  # Simple comparison
                # Password correct - redirect to home
                flash('Login successful!', 'success')

                session['username'] = user.username
                session['role'] = user.role

                if username=="Aarush" and password=="Admin123":
                    session['username'] = user.username
                    session['role'] = user.role
                    return redirect(url_for('admin_home'))
                    
                else:
                    return redirect(url_for('home'))
            else:
                # Wrong password - stay on login page with error
                flash('Invalid password. Please try again.', 'error')
                return render_template('user_login.html')
        else:
            # User doesn't exist - redirect to registration
            flash('Username not found. Please register first.', 'error')
            return redirect(url_for('user_register'))
    
    return render_template('user_login.html')


@app.route('/user_register', methods=['GET', 'POST'])
def user_register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        tel = request.form['tel']
        new_user = User(username=username, email=email, password=password,tel=tel)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('user_login'))
    return render_template('user_register.html')





@app.route('/home', methods=['GET', 'POST'])
def home():
    if not session.get('username'):
        return redirect(url_for('user_login'))


    user = User.query.filter_by(username=session['username']).first()

    search_query = request.form.get('search_location')
    if search_query:
        lots = P_Lot.query.filter(P_Lot.loc.ilike(f"%{search_query}%")).all()
    else:
        lots = P_Lot.query.all()

    user_txns = UserTransaction.query.filter_by(user_id=user.id).order_by(UserTransaction.entry_time.desc()).limit(5).all()

    return render_template('home.html', lots=lots, user=user, history=user_txns, timedelta=timedelta)

@app.route('/book_form/<int:spot_id>')
def render_book_form(spot_id):
    print(f"RENDERING BOOK FORM FOR SPOT ID: {spot_id}")
    spot = P_Spot.query.get_or_404(spot_id)
    print("Fetched Spot:", spot)

    if spot.status == 'O':
        flash("This spot is already occupied.", "error")
        return redirect(url_for('home'))

    return render_template('book_spot_form.html', spot=spot)

@app.route('/book_spot/<int:spot_id>', methods=['POST'])
def book_spot(spot_id):
    if not session.get('username'):
        return redirect(url_for('user_login'))

    spot = P_Spot.query.get_or_404(spot_id)

    if spot.status == 'O':
        flash('Spot already occupied.', 'error')
        return redirect(url_for('home'))

    spot.status = 'O'
    user = User.query.filter_by(username=session['username']).first()

    vehicle_number = request.form.get('vehicle_number')
    transaction = UserTransaction(spot_id=spot.id, user_id=user.id, vehicle_number=vehicle_number)

    db.session.add(transaction)
    db.session.commit()

    flash('Spot booked successfully!', 'success')
    return redirect(url_for('home'))


@app.route('/release_form/<int:spot_id>')
def release_form(spot_id):
    user = User.query.filter_by(username=session['username']).first()
    spot = P_Spot.query.get_or_404(spot_id)
    txn = UserTransaction.query.filter_by(user_id=user.id, spot_id=spot.id, leave_time=None).first()

    if not txn:
        flash("No active booking found for this spot.", "error")
        return redirect(url_for('home'))

    return render_template('release_spot_form.html', txn=txn, spot=spot)

@app.route('/release_spot/<int:spot_id>', methods=['POST'])
def release_spot(spot_id):
    user = User.query.filter_by(username=session['username']).first()
    spot = P_Spot.query.get_or_404(spot_id)
    txn = UserTransaction.query.filter_by(user_id=user.id, spot_id=spot.id, leave_time=None).first()

    if txn:
        txn.leave_time = datetime.utcnow()
        txn.cost = txn.calculate_cost()
        spot.status = 'V'
        db.session.commit()

        flash(f'Spot released! Total cost: ₹{txn.cost:.2f}', 'success')
    else:
        flash("No active transaction found.", "error")

    return redirect(url_for('feedback_form', txn_id=txn.id))


@app.route('/summary')
def user_summary():
    if not session.get('username'):
        return redirect(url_for('user_login'))

    user = User.query.filter_by(username=session['username']).first()
    txns = UserTransaction.query.filter_by(user_id=user.id).order_by(UserTransaction.entry_time.desc()).all()

    total_bookings = len(txns)
    active_booking = any(txn.leave_time is None for txn in txns)
    total_spent = sum(txn.cost for txn in txns if txn.cost)
    avg_duration = None

    durations = [
        (txn.leave_time - txn.entry_time).total_seconds() / 3600
        for txn in txns if txn.leave_time
    ]
    if durations:
        avg_duration = sum(durations) / len(durations)

        # Chart.js data
    labels = []
    costs = []

    for txn in txns:
        if txn.cost:
            labels.append(txn.entry_time.strftime('%b %d'))  # e.g., 'Jul 17'
            costs.append(txn.cost)

    return render_template(
        'summary.html',
        total_bookings=total_bookings,
        active_booking=active_booking,
        total_spent=total_spent,
        avg_duration=avg_duration,
        recent_txns=txns[:5],
        labels=labels,
        costs=costs,
        timedelta=timedelta
    )

@app.route('/feedback/<int:txn_id>')
def feedback_form(txn_id):
    txn = UserTransaction.query.get_or_404(txn_id)
    return render_template('feedback_form.html', txn=txn)

@app.route('/submit_feedback/<int:txn_id>', methods=['POST'])
def submit_feedback(txn_id):
    txn = UserTransaction.query.get_or_404(txn_id)
    txn.rating = int(request.form.get('rating')) if request.form.get('rating') else None
    txn.feedback = request.form.get('feedback')
    db.session.commit()
    flash('Thanks for your feedback! ⭐', 'success')
    return redirect(url_for('home'))






@app.route('/admin_home')
def admin_home():
        
    # Get all parking lots and spots for display
    parking_lots = P_Lot.query.all()
    
    return render_template('admin_home.html', parking_lots=parking_lots)

@app.route('/create_parking_lot', methods=['GET', 'POST'])
def create_parking_lot():
    
    if request.method == 'POST':
        location = request.form['location']
        price = int(request.form['price'])
        spots = int(request.form['spots'])
        
        # Create new parking lot
        new_lot = P_Lot(loc=location, price=price, spots=spots)
        db.session.add(new_lot)
        db.session.commit()
        
        # Create parking spots for this lot
        for i in range(1, spots + 1):
            spot_id = f"{new_lot.id}-{i}"
            new_spot = P_Spot(lot_id=new_lot.id, spot_id=spot_id, status="V")
            db.session.add(new_spot)
        
        db.session.commit()
        flash(f'Parking lot created successfully with {spots} spots!', 'success')
        return redirect(url_for('admin_home'))
    
    return render_template('create_parking_lot.html')

@app.route('/view_parking_lot/<int:lot_id>')
def view_parking_lot(lot_id):
    
    lot = P_Lot.query.get_or_404(lot_id)
    spots = P_Spot.query.filter_by(lot_id=lot_id).all()
    
    return render_template('view_parking_lot.html', lot=lot, spots=spots)

@app.route('/admin/delete_lot/<int:lot_id>')
def delete_parking_lot(lot_id):
    lot = P_Lot.query.get_or_404(lot_id)
    occupied_spots = P_Spot.query.filter_by(lot_id=lot.id, status='O').all()

    if occupied_spots:
        flash('❌ Cannot delete this lot — it has occupied spots.', 'error')
        return redirect(url_for('view_parking_lot', lot_id=lot.id))

    # Delete all spots under this lot
    P_Spot.query.filter_by(lot_id=lot.id).delete()

    # Now delete the lot itself
    db.session.delete(lot)
    db.session.commit()

    flash(f'✅ Parking lot at "{lot.loc}" was deleted successfully.', 'success')
    return redirect(url_for('admin_home'))


@app.route('/admin/edit_lot/<int:lot_id>', methods=['GET', 'POST'])
def edit_parking_lot(lot_id):
    lot = P_Lot.query.get_or_404(lot_id)
    spots = P_Spot.query.filter_by(lot_id=lot.id).all()

    # Sort spots numerically by the suffix in spot_id (e.g., '3-2' -> 2)
    def extract_suffix(s):
        try:
            return int(str(s.spot_id).split('-')[-1])
        except:
            return float('inf')  # Put bad data at end

    spots.sort(key=extract_suffix)

    if request.method == 'POST':
        # --- Update price ---
        new_price = request.form.get('price')
        if new_price:
            try:
                lot.price = float(new_price)
            except ValueError:
                flash("⚠️ Invalid price entered.", 'error')
                return redirect(request.url)

        # --- Add new spots ---
        new_spots_raw = request.form.get('add_spots', '').strip()
        if new_spots_raw:
            if new_spots_raw.isdigit():
                new_spots = int(new_spots_raw)
                if new_spots > 0:
                    numeric_ids = []
                    for s in spots:
                        try:
                            suffix = str(s.spot_id).split('-')[-1]
                            numeric_ids.append(int(suffix))
                        except (ValueError, IndexError):
                            continue
                    max_suffix = max(numeric_ids, default=0)

                    for i in range(1, new_spots + 1):
                        new_spot_id = f"{lot.id}-{max_suffix + i}"
                        new_spot = P_Spot(
                            spot_id=new_spot_id,
                            lot_id=lot.id,
                            status='V'
                        )
                        db.session.add(new_spot)

                    lot.spots += new_spots
                else:
                    flash("⚠️ Number of spots must be greater than 0.", 'error')
                    return redirect(request.url)
            else:
                flash("⚠️ Please enter a valid positive integer for number of spots.", 'error')
                return redirect(request.url)

        # --- Delete selected vacant spots ---
        spot_ids_to_delete = request.form.getlist('delete_spots')
        for sid in spot_ids_to_delete:
            try:
                spot = P_Spot.query.filter_by(lot_id=lot.id, spot_id=sid, status='V').first()
                if spot:
                    db.session.delete(spot)
                    lot.spots -= 1
            except Exception:
                continue

        db.session.commit()
        flash("✅ Lot updated successfully.", 'success')
        return redirect(url_for('view_parking_lot', lot_id=lot.id))

    return render_template("edit_parking_lot.html", lot=lot, spots=spots)


@app.route('/admin/users')
def view_all_users():
    search = request.args.get('search', '').strip().lower()
    filter_date = request.args.get('date')
    page = int(request.args.get('page', 1))

    # Filter users
    if search:
        users = User.query.filter(
            (User.username.ilike(f'%{search}%')) |
            (User.email.ilike(f'%{search}%'))
        ).all()
    else:
        users = User.query.all()

    user_data = []

    for user in users:
        query = UserTransaction.query.filter_by(user_id=user.id)

        if filter_date:
            try:
                from datetime import datetime
                date_obj = datetime.strptime(filter_date, '%Y-%m-%d').date()
                query = query.filter(
                    db.func.date(UserTransaction.entry_time) == date_obj
                )
            except:
                pass

        total_txns = query.count()

        transactions = query.order_by(UserTransaction.entry_time.desc()) \
                            .offset((page - 1) * 5).limit(5).all()

        enriched_txns = []

        for txn in transactions:
            spot = P_Spot.query.get(txn.spot_id)
            lot = P_Lot.query.get(spot.lot_id) if spot else None

            enriched_txns.append({
                "lot_location": lot.loc if lot else "Unknown",
                "entry_time": txn.entry_time,
                "exit_time": txn.leave_time,
                "cost": txn.cost,
                "rating": txn.rating,
                "vehicle_number": txn.vehicle_number
            })

        user_data.append({
            "user": user,
            "transactions": enriched_txns,
            "total_txns": total_txns
        })

    return render_template("admin_users.html",
                           user_data=user_data,
                           search=search,
                           date_filter=filter_date,
                           current_page=page)

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # Delete user transactions
    user_txns = UserTransaction.query.filter_by(user_id=user.id).all()
    for txn in user_txns:
        # Free the spot if user was currently occupying it
        spot = P_Spot.query.filter_by(spot_id=txn.spot_id).first()
        if spot and spot.status == 'O':
            spot.status = 'V'
            db.session.add(spot)
        db.session.delete(txn)
    
    db.session.delete(user)
    db.session.commit()
    flash(f'🗑️ User "{user.username}" and all related records have been deleted.', 'success')
    return redirect(url_for('view_all_users'))

@app.route('/admin/summary')
def admin_summary():
    lots = P_Lot.query.all()
    spot_data = P_Spot.query.all()
    txns = UserTransaction.query.all()

    # Pie chart data (Top 5 lots by revenue)
    lot_revenue_map = {}
    for txn in txns:
        spot = P_Spot.query.get(txn.spot_id)
        if spot:
            lot = P_Lot.query.get(spot.lot_id)
            if lot:
                lot_revenue_map[lot.loc] = lot_revenue_map.get(lot.loc, 0) + (txn.cost or 0)

    sorted_lots = sorted(lot_revenue_map.items(), key=lambda x: x[1], reverse=True)
    top_lots = sorted_lots[:5]
    others_total = sum(r for _, r in sorted_lots[5:])

    pie_labels = [name for name, _ in top_lots]
    pie_values = [val for _, val in top_lots]
    if others_total > 0:
        pie_labels.append("Others")
        pie_values.append(others_total)

    # Bar chart data (available vs occupied)
    available = sum(1 for spot in spot_data if spot.status == 'V')
    occupied = sum(1 for spot in spot_data if spot.status == 'O')

    # Dropdown table data
    lot_summary = []
    total_revenue = sum(lot_revenue_map.values())
    for lot in lots:
        rev = lot_revenue_map.get(lot.loc, 0)
        pct = (rev / total_revenue) * 100 if total_revenue > 0 else 0
        lot_summary.append({
            "loc": lot.loc,
            "revenue": rev,
            "percentage": round(pct, 2)
        })

    return render_template(
        "admin_summary.html",
        pie_labels=pie_labels,
        pie_values=pie_values,
        available=available,
        occupied=occupied,
        lot_summary=lot_summary
    )









@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('landing'))




if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        initialize_admin()
    app.run(debug=True)