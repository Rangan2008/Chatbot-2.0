import os
import re
import io
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import PyPDF2
from PIL import Image
import pytesseract
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__, static_folder='static')
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-secret-key'),
    SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'sqlite:///chatbot.db'),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    MAX_CONTENT_LENGTH=512* 1024 * 1024,
    UPLOAD_FOLDER=os.path.join(os.path.abspath(os.path.dirname(__file__)), 'user_uploads'),
    ALLOWED_EXTENSIONS={'pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp'},
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax'
)

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
CORS(app, supports_credentials=True, resources={r"/*": {"origins": os.environ.get('ALLOWED_ORIGINS', 'http://localhost:3000')}})

# Optional: Configure Tesseract path
try:
    pytesseract.pytesseract.tesseract_cmd = os.environ.get('TESSERACT_CMD', '/usr/bin/tesseract')
except:
    print("Tesseract OCR not configured properly")

# ========== ROUTES FOR PAGES ==========
@app.route('/')
def home():
    return render_template('index.html')  # ✅ shows landing page

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/signup')
def signup_page():
    return render_template('signup.html')

@app.route('/chat')
@login_required
def chat_page():
    return render_template('chat.html')

# ========== USER MODEL ==========
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    avatar = db.Column(db.String(255), default='/static/Avatar.jpeg')
    theme = db.Column(db.String(20), default='light')
    notifications = db.Column(db.Boolean, default=True)
    language = db.Column(db.String(20), default='English')
    joined_date = db.Column(db.DateTime, default=datetime.utcnow)
    chats = db.relationship('Chat', backref='user', lazy=True, cascade='all, delete-orphan')
    files = db.relationship('UploadedFile', backref='user', lazy=True, cascade='all, delete-orphan')

class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user_message = db.Column(db.Text, nullable=False)
    ai_message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

class UploadedFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(512), nullable=False)
    filetype = db.Column(db.String(50), nullable=False)
    filesize = db.Column(db.Integer, nullable=False)
    extracted_text = db.Column(db.Text)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
# ========== HELPER FUNCTIONS ==========    

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def validate_email(email):
    return re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email)

def validate_username(username):
    return re.match(r"^[a-zA-Z0-9_-]{3,32}$", username)

def extract_text_from_pdf(file_stream):
    try:
        reader = PyPDF2.PdfReader(file_stream)
        text = '\n'.join([page.extract_text() or '' for page in reader.pages])
        return text.strip() or '[No extractable text found in PDF]'
    except Exception as e:
        return f'[Error extracting PDF text: {str(e)}]'

def extract_text_from_image(file_stream):
    try:
        image = Image.open(file_stream)
        text = pytesseract.image_to_string(image)
        return text.strip() or '[No text found in image]'
    except Exception as e:
        return f'[Error extracting image text: {str(e)}]'

def save_uploaded_file(file, user_id):
    filename = secure_filename(file.filename)
    user_upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(user_id))
    os.makedirs(user_upload_dir, exist_ok=True)
    filepath = os.path.join(user_upload_dir, filename)
    file.save(filepath)
    return filename, filepath

# ========== API ROUTES ==========

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username = data.get('username', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not all([username, email, password]):
        return jsonify({'error': 'All fields are required'}), 400
    if not validate_username(username):
        return jsonify({'error': 'Invalid username format'}), 400
    if not validate_email(email):
        return jsonify({'error': 'Invalid email format'}), 400
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({'error': 'Username or email already exists'}), 409

    user = User(username=username, email=email, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'User registered successfully'}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'error': 'Invalid credentials'}), 401
    login_user(user)
    return jsonify({'message': 'Login successful'}), 200

@app.route('/api/auth/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logged out successfully'}), 200

# ========== PROFILE API ROUTES ==========
@app.route('/api/profile', methods=['GET'])
@login_required
def get_profile():
    user = current_user
    total_chats = Chat.query.filter_by(user_id=user.id).count()
    return jsonify({
        'username': user.username,
        'email': user.email,
        'avatar': user.avatar,
        'theme': user.theme,
        'notifications': user.notifications,
        'language': user.language,
        'joined_date': user.joined_date.strftime('%Y-%m-%d'),
        'total_chats': total_chats
    })

@app.route('/api/profile/update', methods=['POST'])
@login_required
def update_profile():
    data = request.get_json()
    user = current_user
    
    # Validate and update email
    email = data.get('email', '').strip().lower()
    if email and email != user.email:
        if not validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400
        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user and existing_user.id != user.id:
            return jsonify({'error': 'Email already exists'}), 409
        user.email = email
    
    # Validate and update username
    username = data.get('username', '').strip()
    if username and username != user.username:
        if not validate_username(username):
            return jsonify({'error': 'Invalid username format'}), 400
        # Check if username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user and existing_user.id != user.id:
            return jsonify({'error': 'Username already exists'}), 409
        user.username = username
    
    # Update password if provided
    password = data.get('password', '').strip()
    if password:
        if len(password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters'}), 400
        user.password_hash = generate_password_hash(password)
    
    # Update preferences
    user.theme = data.get('theme', user.theme)
    user.notifications = data.get('notifications', user.notifications)
    user.language = data.get('language', user.language)
    
    try:
        db.session.commit()
        return jsonify({'message': 'Profile updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update profile'}), 500

@app.route('/api/profile/avatar', methods=['POST'])
@login_required
def upload_avatar():
    if 'avatar' not in request.files:
        return jsonify({'error': 'No avatar file provided'}), 400
    
    file = request.files['avatar']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Please upload an image.'}), 400
    
    try:
        # Create avatars directory if it doesn't exist
        avatars_dir = os.path.join(app.static_folder, 'avatars')
        os.makedirs(avatars_dir, exist_ok=True)
        
        # Save the file with a unique name
        filename = f"avatar_{current_user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file.filename.rsplit('.', 1)[1].lower()}"
        filepath = os.path.join(avatars_dir, filename)
        file.save(filepath)
        
        # Update user's avatar path
        current_user.avatar = f'/static/avatars/{filename}'
        db.session.commit()
        
        return jsonify({
            'message': 'Avatar updated successfully',
            'filename': current_user.avatar
        })
    except Exception as e:
        return jsonify({'error': 'Failed to upload avatar'}), 500

@app.route('/api/profile/delete', methods=['POST'])
@login_required
def delete_account():
    try:
        user_id = current_user.id
        
        # Delete user's uploaded files from filesystem
        user_upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(user_id))
        if os.path.exists(user_upload_dir):
            import shutil
            shutil.rmtree(user_upload_dir)
        
        # Delete user's avatar if it's not the default
        if current_user.avatar and current_user.avatar != '/static/Avatar.jpeg':
            avatar_path = os.path.join(app.static_folder, current_user.avatar.lstrip('/static/'))
            if os.path.exists(avatar_path):
                os.remove(avatar_path)
        
        # The database cascades will handle deleting chats and files records
        db.session.delete(current_user)
        db.session.commit()
        logout_user()
        
        return jsonify({'message': 'Account deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete account'}), 500

@app.route('/api/chat', methods=['POST'])
@login_required
def save_chat():
    data = request.get_json()
    chat = Chat(user_id=current_user.id, user_message=data.get('user_message', '').strip(), ai_message=data.get('ai_message', '').strip())
    db.session.add(chat)
    db.session.commit()
    return jsonify({
        'message': 'Chat saved',
        'chat_id': chat.id,
        'timestamp': chat.timestamp.isoformat()
    }), 201

@app.route('/api/ai/chat', methods=['POST'])
@login_required
def ai_chat():
    """Generate AI response using Gemini API"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        file_id = data.get('file_id')
        
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Build prompt with file context if provided
        prompt = user_message
        if file_id:
            try:
                file_obj = UploadedFile.query.filter_by(id=file_id, user_id=current_user.id).first()
                if file_obj and file_obj.extracted_text:
                    prompt = f"Context from file \"{file_obj.filename}\":\n{file_obj.extracted_text}\n\nQuestion: {user_message}"
            except Exception as e:
                print(f"Error loading file context: {e}")
        
        # Call Gemini API
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            return jsonify({'error': 'AI service not configured'}), 500
        
        response = requests.post(
            f'https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}',
            headers={'Content-Type': 'application/json'},
            json={
                'contents': [{'parts': [{'text': prompt}]}]
            },
            timeout=30
        )
        
        if not response.ok:
            return jsonify({'error': 'AI service temporarily unavailable'}), 503
        
        result = response.json()
        ai_response = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '').strip()
        
        if not ai_response:
            ai_response = 'Sorry, I could not generate a response.'
        
        # Save chat to database
        chat = Chat(
            user_id=current_user.id,
            user_message=user_message,
            ai_message=ai_response
        )
        db.session.add(chat)
        db.session.commit()
        
        return jsonify({
            'response': ai_response,
            'chat_id': chat.id,
            'timestamp': chat.timestamp.isoformat()
        })
        
    except requests.exceptions.Timeout:
        return jsonify({'error': 'AI service timeout. Please try again.'}), 504
    except requests.exceptions.RequestException as e:
        print(f"Gemini API error: {e}")
        return jsonify({'error': 'AI service error. Please try again later.'}), 503
    except Exception as e:
        print(f"Unexpected error in ai_chat: {e}")
        return jsonify({'error': 'Something went wrong. Please try again.'}), 500

@app.route('/api/chats', methods=['GET'])
@login_required
def get_chats():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    chats = Chat.query.filter_by(user_id=current_user.id).order_by(Chat.timestamp.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'chats': [{
            'id': chat.id,
            'user_message': chat.user_message,
            'ai_message': chat.ai_message,
            'timestamp': chat.timestamp.isoformat()
        } for chat in chats.items],
        'total': chats.total,
        'pages': chats.pages,
        'current_page': chats.page
    })

@app.route('/api/chats/<int:chat_id>', methods=['GET'])
@login_required
def get_chat(chat_id):
    chat = Chat.query.filter_by(id=chat_id, user_id=current_user.id).first()
    if not chat:
        return jsonify({'error': 'Chat not found'}), 404
    return jsonify({
        'user_message': chat.user_message,
        'ai_message': chat.ai_message,
        'timestamp': chat.timestamp.isoformat()
    })

@app.route('/api/chats/<int:chat_id>', methods=['DELETE'])
@login_required
def delete_chat(chat_id):
    chat = Chat.query.filter_by(id=chat_id, user_id=current_user.id).first()
    if not chat:
        return jsonify({'error': 'Chat not found'}), 404
    db.session.delete(chat)
    db.session.commit()
    return jsonify({'message': 'Chat deleted'}), 200

@app.route('/api/files', methods=['POST'])
@login_required
def upload_file():
    file = request.files.get('file')
    if not file or file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid or missing file'}), 400

    filename, filepath = save_uploaded_file(file, current_user.id)
    file_ext = filename.rsplit('.', 1)[1].lower()

    with open(filepath, 'rb') as f:
        file_stream = io.BytesIO(f.read())

    if file_ext == 'pdf':
        text = extract_text_from_pdf(file_stream)
    else:
        text = extract_text_from_image(file_stream)

    uploaded_file = UploadedFile(
        user_id=current_user.id,
        filename=filename,
        filepath=filepath,
        filetype=file_ext,
        filesize=os.path.getsize(filepath),
        extracted_text=text
    )
    db.session.add(uploaded_file)
    db.session.commit()

    return jsonify({
        'message': 'File uploaded successfully',
        'file_id': uploaded_file.id,
        'filename': filename,
        'filetype': file_ext,
        'text': text
    }), 201

@app.route('/uploaded-files/<int:file_id>', methods=['GET'])
@login_required
def get_uploaded_file(file_id):
    file = UploadedFile.query.filter_by(id=file_id, user_id=current_user.id).first()
    if not file:
        return jsonify({'error': 'File not found'}), 404
    return jsonify({
        'filename': file.filename,
        'extracted_text': file.extracted_text
    })

@app.route('/api/chats/export', methods=['GET'])
@login_required
def export_chats():
    chats = Chat.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'user_message': c.user_message,
        'ai_message': c.ai_message,
        'timestamp': c.timestamp.isoformat()
    } for c in chats])

@app.route('/api/chats/history', methods=['GET'])
@login_required
def get_chat_history():
    """Get chat history for the current user only."""
    try:
        # Get query parameters
        limit = min(request.args.get('limit', 50, type=int), 100)  # Max 100 chats
        offset = request.args.get('offset', 0, type=int)
        
        # Query only current user's chats
        chats = Chat.query.filter_by(user_id=current_user.id)\
                         .order_by(Chat.timestamp.desc())\
                         .offset(offset)\
                         .limit(limit)\
                         .all()
        
        total_chats = Chat.query.filter_by(user_id=current_user.id).count()
        
        return jsonify({
            'chats': [{
                'id': chat.id,
                'user_message': chat.user_message,
                'ai_message': chat.ai_message,
                'timestamp': chat.timestamp.isoformat()
            } for chat in chats],
            'total': total_chats,
            'limit': limit,
            'offset': offset,
            'user_id': current_user.id  # For debugging (shows which user's chats these are)
        })
    except Exception as e:
        return jsonify({'error': 'Failed to fetch chat history'}), 500

@app.route('/api/user/stats', methods=['GET'])
@login_required
def get_user_stats():
    """Get statistics for the current user only."""
    try:
        total_chats = Chat.query.filter_by(user_id=current_user.id).count()
        total_files = UploadedFile.query.filter_by(user_id=current_user.id).count()
        
        # Get latest chat
        latest_chat = Chat.query.filter_by(user_id=current_user.id)\
                               .order_by(Chat.timestamp.desc())\
                               .first()
        
        return jsonify({
            'user_id': current_user.id,
            'username': current_user.username,
            'total_chats': total_chats,
            'total_files': total_files,
            'latest_chat_date': latest_chat.timestamp.isoformat() if latest_chat else None,
            'joined_date': current_user.joined_date.isoformat() if current_user.joined_date else None
        })
    except Exception as e:
        return jsonify({'error': 'Failed to fetch user statistics'}), 500

@app.route('/profile')
@login_required
def profile_page():
    return render_template('profile.html')

# ========== ERROR HANDLERS ==========
@app.errorhandler(400)
def bad_request(e): return jsonify({'error': 'Bad request'}), 400

@app.errorhandler(401)
def unauthorized(e): return jsonify({'error': 'Unauthorized'}), 401

@app.errorhandler(404)
def not_found(e): return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(413)
def file_too_large(e): return jsonify({'error': 'File too large'}), 413

@app.errorhandler(500)
def server_error(e): return jsonify({'error': 'Internal server error'}), 500

# ========== RUN ==========
with app.app_context():
    db.create_all()

from flask import send_from_directory

@app.route('/api/files', methods=['GET'])
@login_required
def list_user_files():
    user_files = UploadedFile.query.filter_by(user_id=current_user.id).order_by(UploadedFile.uploaded_at.desc()).all()
    return jsonify([{
        'id': f.id,
        'filename': f.filename,
        'uploaded_at': f.uploaded_at.isoformat(),
        'extracted_text': f.extracted_text[:500] + ('...' if len(f.extracted_text) > 500 else '')
    } for f in user_files])

@app.route('/media/<int:user_id>/<filename>')
@login_required
def serve_user_file(user_id, filename):
    user_upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(user_id))
    return send_from_directory(user_upload_dir, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=os.environ.get('DEBUG', 'false').lower() == 'true')