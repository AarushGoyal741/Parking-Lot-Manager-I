"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    tel = db.Column(db.Integer, nullable=False)
    role = db.Column(db.String(20), default="user")
    
    # Relationship with user transactions
    transactions = db.relationship('UserTransaction', backref='user', lazy=True)

class P_Lot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    loc = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    spots = db.Column(db.Integer, nullable=False)
    
    # Relationship with parking spots
    parking_spots = db.relationship('P_Spot', backref='P_lot', lazy=True)

class P_Spot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey('P_Lot.id'), nullable=False)
    spot_id = db.Column(db.String(10), nullable=False)  # Format: lot_id-spot_number
    status = db.Column(db.String(1), nullable=False, default="V")  # V for Vacant, O for Occupied
    
    # Relationship with user transactions
    transactions = db.relationship('UserTransaction', backref='P_Spot', lazy=True)

class UserTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    spot_id = db.Column(db.Integer, db.ForeignKey('P_spot.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    entry_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    leave_time = db.Column(db.DateTime, nullable=True)
    cost = db.Column(db.Float, nullable=True)
    
    def calculate_cost(self):
        
        if self.leave_time:
            # Get the price from the parking lot
            spot = P_Spot.query.get(self.spot_id)
            lot = P_Lot.query.get(spot.lot_id)
            
            # Calculate hours (minimum 1 hour)
            duration = self.leave_time - self.entry_time
            hours = max(1, duration.total_seconds() / 3600)
            
            return lot.price * hours
        return 0

"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    tel = db.Column(db.Integer, nullable=False)
    role = db.Column(db.String(20), default="user")
    
    # Relationship with user transactions
    transactions = db.relationship('UserTransaction', backref='user', lazy=True)

class P_Lot(db.Model):
    __tablename__ = 'p_lot'  # Explicitly define table name
    
    id = db.Column(db.Integer, primary_key=True)
    loc = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    spots = db.Column(db.Integer, nullable=False)
    
    # Relationship with parking spots
    parking_spots = db.relationship('P_Spot', backref='p_lot', lazy=True)

class P_Spot(db.Model):
    __tablename__ = 'p_spot'  # Explicitly define table name
    
    id = db.Column(db.Integer, primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey('p_lot.id'), nullable=False)  # Fixed reference
    spot_id = db.Column(db.String(10), nullable=False)  # Format: lot_id-spot_number
    status = db.Column(db.String(1), nullable=False, default="V")  # V for Vacant, O for Occupied
    
    # Relationship with user transactions
    transactions = db.relationship('UserTransaction', backref='p_spot', lazy=True)

class UserTransaction(db.Model):
    __tablename__ = 'user_transaction'  # Explicitly define table name
    
    id = db.Column(db.Integer, primary_key=True)
    spot_id = db.Column(db.Integer, db.ForeignKey('p_spot.id'), nullable=False)  # Fixed reference
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    vehicle_number = db.Column(db.String(20),nullable=False)
    entry_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    leave_time = db.Column(db.DateTime, nullable=True)
    cost = db.Column(db.Float, nullable=True)
    rating = db.Column(db.Integer)         # from 1 to 5
    feedback = db.Column(db.String(200))   # optional comment

    
    def calculate_cost(self):
        """Calculate cost based on entry and leave time"""
        if self.leave_time:
            # Get the price from the parking lot
            spot = P_Spot.query.get(self.spot_id)
            lot = P_Lot.query.get(spot.lot_id)
            
            # Calculate hours (minimum 1 hour)
            duration = self.leave_time - self.entry_time
            hours = max(1, duration.total_seconds() / 3600)
            
            return lot.price * hours
        return 0