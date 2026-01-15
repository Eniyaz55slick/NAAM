from flask import Blueprint, request, jsonify, session, send_from_directory
from models import db, User, Animal, Injection
from utils import (save_base64_image, delete_file, generate_verification_code,
                   send_verification_email, mail, Message)
from datetime import datetime
import os

api = Blueprint('api', __name__)

# Auth Routes
@api.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        name = data.get('name')
        
        if not email or not password or not name:
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Check if user exists
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already exists'}), 400
        
        # Generate verification code
        code = generate_verification_code()
        
        # Create new user
        user = User(email=email, name=name, verification_code=code)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Send email verification (will show code in console if email not configured)
        message = f'Verification code sent to {email}. Code: {code}'
        try:
            send_verification_email(email, code, name)
        except:
            print(f"Verification code for {email}: {code}")
        
        return jsonify({
            'message': message,
            'user_id': user.id,
            'requires_verification': True
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@api.route('/verify', methods=['POST'])
def verify_code():
    """Verify user with code"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        code = data.get('code')
        
        if not user_id or not code:
            return jsonify({'error': 'Missing user_id or code'}), 400
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if user.verification_code != code:
            return jsonify({'error': 'Invalid verification code'}), 400
        
        # Mark as verified
        user.is_verified = True
        user.verification_code = None
        db.session.commit()
        
        # Set session
        session['user_id'] = user.id
        
        return jsonify({
            'message': 'Verification successful',
            'user': user.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@api.route('/resend-code', methods=['POST'])
def resend_code():
    """Resend verification code"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'Missing user_id'}), 400
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Generate new code
        code = generate_verification_code()
        user.verification_code = code
        db.session.commit()
        
        # Send code
        message = f'Code resent to {user.email}. Code: {code}'
        try:
            send_verification_email(user.email, code, user.name)
        except:
            print(f"Verification code for {user.email}: {code}")
        
        return jsonify({'message': message}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/login', methods=['POST'])
def login():
    """Login user"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Missing email or password'}), 400
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        if not user.is_verified:
            return jsonify({
                'error': 'Account not verified',
                'user_id': user.id,
                'requires_verification': True
            }), 403
        
        # Send login notification
        try:
            msg = Message(
                subject='NAAM - Login Notification',
                recipients=[user.email],
                body=f'''Hello {user.name},

Someone just logged into your NAAM account.

Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

If this wasn't you, please change your password immediately.

Thank you,
NAAM Team'''
            )
            mail.send(msg)
        except:
            pass
        
        # Set session
        session['user_id'] = user.id
        
        return jsonify({
            'message': 'Login successful',
            'user': user.to_dict()
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/logout', methods=['POST'])
def logout():
    """Logout user"""
    session.pop('user_id', None)
    return jsonify({'message': 'Logout successful'}), 200

@api.route('/current-user', methods=['GET'])
def get_current_user():
    """Get current logged in user"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({'user': user.to_dict()}), 200

# Animal Routes (keep all existing animal routes)
@api.route('/animals', methods=['GET'])
def get_animals():
    """Get all animals for current user"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    animals = Animal.query.filter_by(user_id=user_id).order_by(Animal.created_at.desc()).all()
    return jsonify({'animals': [animal.to_dict() for animal in animals]}), 200

@api.route('/animals', methods=['POST'])
def create_animal():
    """Create new animal"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401
        
        data = request.get_json()
        
        # Required fields
        name = data.get('name')
        animal_type = data.get('type')
        
        if not name or not animal_type:
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Create animal
        animal = Animal(
            user_id=user_id,
            name=name,
            animal_type=animal_type,
            calf_details=data.get('calfDetails'),
            notes=data.get('notes')
        )
        
        # Handle dates
        if data.get('inseminatedDate'):
            animal.inseminated_date = datetime.fromisoformat(data['inseminatedDate']).date()
        if data.get('deliveryDate'):
            animal.delivery_date = datetime.fromisoformat(data['deliveryDate']).date()
        
        # Handle photo
        if data.get('photoData'):
            from flask import current_app
            filename = save_base64_image(
                data['photoData'],
                current_app.config['UPLOAD_FOLDER'],
                f"animal_{name}"
            )
            if filename:
                animal.photo_path = filename
        
        db.session.add(animal)
        db.session.flush()
        
        # Handle injections
        if data.get('injections'):
            for inj_data in data['injections']:
                injection = Injection(
                    animal_id=animal.id,
                    date=datetime.fromisoformat(inj_data['date']).date(),
                    details=inj_data['details']
                )
                db.session.add(injection)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Animal created successfully',
            'animal': animal.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@api.route('/animals/<int:animal_id>', methods=['PUT'])
def update_animal(animal_id):
    """Update animal"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401
        
        animal = Animal.query.filter_by(id=animal_id, user_id=user_id).first()
        if not animal:
            return jsonify({'error': 'Animal not found'}), 404
        
        data = request.get_json()
        
        # Update fields
        if 'name' in data:
            animal.name = data['name']
        if 'type' in data:
            animal.animal_type = data['type']
        if 'calfDetails' in data:
            animal.calf_details = data['calfDetails']
        if 'notes' in data:
            animal.notes = data['notes']
        
        # Update dates
        if 'inseminatedDate' in data:
            animal.inseminated_date = datetime.fromisoformat(data['inseminatedDate']).date() if data['inseminatedDate'] else None
        if 'deliveryDate' in data:
            animal.delivery_date = datetime.fromisoformat(data['deliveryDate']).date() if data['deliveryDate'] else None
        
        # Update photo
        if 'photoData' in data and data['photoData']:
            from flask import current_app
            # Delete old photo
            if animal.photo_path:
                old_path = os.path.join(current_app.config['UPLOAD_FOLDER'], animal.photo_path)
                delete_file(old_path)
            
            # Save new photo
            filename = save_base64_image(
                data['photoData'],
                current_app.config['UPLOAD_FOLDER'],
                f"animal_{animal.name}"
            )
            if filename:
                animal.photo_path = filename
        
        # Update injections
        if 'injections' in data:
            # Delete old injections
            Injection.query.filter_by(animal_id=animal.id).delete()
            
            # Add new injections
            for inj_data in data['injections']:
                injection = Injection(
                    animal_id=animal.id,
                    date=datetime.fromisoformat(inj_data['date']).date(),
                    details=inj_data['details']
                )
                db.session.add(injection)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Animal updated successfully',
            'animal': animal.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@api.route('/animals/<int:animal_id>', methods=['DELETE'])
def delete_animal(animal_id):
    """Delete animal"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401
        
        animal = Animal.query.filter_by(id=animal_id, user_id=user_id).first()
        if not animal:
            return jsonify({'error': 'Animal not found'}), 404
        
        # Delete photo
        if animal.photo_path:
            from flask import current_app
            photo_path = os.path.join(current_app.config['UPLOAD_FOLDER'], animal.photo_path)
            delete_file(photo_path)
        
        db.session.delete(animal)
        db.session.commit()
        
        return jsonify({'message': 'Animal deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# File serving route
@api.route('/uploads/<filename>')
def serve_upload(filename):
    """Serve uploaded files"""
    from flask import current_app
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)