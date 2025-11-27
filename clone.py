# backend/app.py
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
from datetime import datetime
import uuid
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = 'isightu-secret-key-2024'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# In-memory storage (replace with database in production)
users = {}
chats = {}
messages = {}
online_users = set()
contacts = {}  # user_phone -> list of contact phones
contact_requests = {}  # to_phone -> list of request objects

def validate_phone_number(phone):
    """Validate phone number format"""
    pattern = r'^\+?1?\d{9,15}$'
    return re.match(pattern, phone) is not None

@app.route('/')
def home():
    return jsonify({
        "message": "iSightU Chat API", 
        "status": "running",
        "version": "2.0",
        "features": ["real-time-chat", "contact-management", "online-status"]
    })

@app.route('/api/auth/register', methods=['POST'])
def register_user():
    try:
        data = request.get_json()
        phone = data.get('phone')
        name = data.get('name')
        
        if not phone or not name:
            return jsonify({"error": "Phone and name are required"}), 400
        
        if not validate_phone_number(phone):
            return jsonify({"error": "Invalid phone number format"}), 400
        
        # Check if user already exists
        if phone in users:
            return jsonify({"error": "User already exists"}), 400
        
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        users[phone] = {
            "id": user_id,
            "phone": phone,
            "name": name,
            "status": "Hey there! I'm using iSightU",
            "last_seen": datetime.now().isoformat(),
            "is_online": False,
            "created_at": datetime.now().isoformat(),
            "profile_status": "Available"
        }
        
        # Initialize contacts list
        contacts[phone] = []
        
        return jsonify({
            "success": True,
            "user": users[phone],
            "message": "Registration successful"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login_user():
    try:
        data = request.get_json()
        phone = data.get('phone')
        
        if not phone:
            return jsonify({"error": "Phone number is required"}), 400
        
        user = users.get(phone)
        if not user:
            return jsonify({"error": "User not found. Please register first."}), 404
        
        # Update last seen and online status
        user['last_seen'] = datetime.now().isoformat()
        user['is_online'] = True
        online_users.add(phone)
        
        return jsonify({
            "success": True,
            "user": user,
            "message": "Login successful"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/users', methods=['GET'])
def get_users():
    return jsonify(list(users.values()))

@app.route('/api/users/search/<phone>', methods=['GET'])
def search_user(phone):
    """Search for a user by phone number"""
    current_user = request.args.get('current_user')
    
    if not validate_phone_number(phone):
        return jsonify({"error": "Invalid phone number format"}), 400
    
    user = users.get(phone)
    if not user:
        return jsonify({"found": False, "message": "User not found on iSightU"})
    
    # Check if already in contacts
    is_contact = phone in contacts.get(current_user, [])
    
    return jsonify({
        "found": True,
        "user": user,
        "is_contact": is_contact,
        "is_online": user['is_online']
    })

@app.route('/api/users/online', methods=['GET'])
def get_online_users():
    online_list = [users[phone] for phone in online_users if phone in users]
    return jsonify(online_list)

@app.route('/api/contacts', methods=['GET'])
def get_contacts():
    user_phone = request.args.get('user_phone')
    if not user_phone:
        return jsonify([])
    
    user_contacts = []
    for contact_phone in contacts.get(user_phone, []):
        contact_user = users.get(contact_phone)
        if contact_user:
            user_contacts.append(contact_user)
    
    return jsonify(user_contacts)

@app.route('/api/contacts/add', methods=['POST'])
def add_contact():
    try:
        data = request.get_json()
        user_phone = data.get('user_phone')
        contact_phone = data.get('contact_phone')
        
        if not user_phone or not contact_phone:
            return jsonify({"error": "User phone and contact phone are required"}), 400
        
        if contact_phone not in users:
            return jsonify({"error": "Contact user not found"}), 404
        
        if user_phone not in contacts:
            contacts[user_phone] = []
        
        if contact_phone in contacts[user_phone]:
            return jsonify({"error": "Contact already added"}), 400
        
        contacts[user_phone].append(contact_phone)
        
        return jsonify({
            "success": True,
            "message": "Contact added successfully",
            "contact": users[contact_phone]
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/contacts/remove', methods=['POST'])
def remove_contact():
    try:
        data = request.get_json()
        user_phone = data.get('user_phone')
        contact_phone = data.get('contact_phone')
        
        if user_phone in contacts and contact_phone in contacts[user_phone]:
            contacts[user_phone].remove(contact_phone)
            return jsonify({"success": True, "message": "Contact removed successfully"})
        else:
            return jsonify({"error": "Contact not found"}), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/chats', methods=['GET'])
def get_chats():
    user_phone = request.args.get('user_phone')
    if not user_phone:
        return jsonify([])
    
    user_chats = []
    for chat_id, chat_data in chats.items():
        if user_phone in chat_data['participants']:
            chat_messages = messages.get(chat_id, [])
            last_message = chat_messages[-1] if chat_messages else None
            
            # Get other participant's info for direct chats
            other_participants = [p for p in chat_data['participants'] if p != user_phone]
            other_user = users.get(other_participants[0]) if other_participants and len(other_participants) == 1 else None
            
            user_chats.append({
                'id': chat_id,
                'name': chat_data['name'],
                'participants': chat_data['participants'],
                'last_message': last_message,
                'is_group': chat_data.get('is_group', False),
                'other_user': other_user
            })
    
    return jsonify(user_chats)

@app.route('/api/chats/<chat_id>/messages', methods=['GET'])
def get_chat_messages(chat_id):
    return jsonify(messages.get(chat_id, []))

@socketio.on('connect')
def handle_connect():
    print('Client connected to iSightU')
    emit('connected', {'data': 'Connected to iSightU successfully'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected from iSightU')

@socketio.on('user_online')
def handle_user_online(data):
    phone = data.get('phone')
    if phone and phone in users:
        users[phone]['is_online'] = True
        online_users.add(phone)
        print(f'User {phone} is now online')
        emit('user_status_changed', {
            'phone': phone,
            'is_online': True,
            'name': users[phone]['name']
        }, broadcast=True)

@socketio.on('user_offline')
def handle_user_offline(data):
    phone = data.get('phone')
    if phone and phone in users:
        users[phone]['is_online'] = False
        users[phone]['last_seen'] = datetime.now().isoformat()
        if phone in online_users:
            online_users.remove(phone)
        print(f'User {phone} is now offline')
        emit('user_status_changed', {
            'phone': phone,
            'is_online': False,
            'name': users[phone]['name'],
            'last_seen': users[phone]['last_seen']
        }, broadcast=True)

@socketio.on('join_chat')
def handle_join_chat(data):
    chat_id = data.get('chat_id')
    user_phone = data.get('user_phone')
    join_room(chat_id)
    print(f'User {user_phone} joined chat {chat_id}')

@socketio.on('leave_chat')
def handle_leave_chat(data):
    chat_id = data.get('chat_id')
    user_phone = data.get('user_phone')
    leave_room(chat_id)
    print(f'User {user_phone} left chat {chat_id}')

@socketio.on('create_chat')
def handle_create_chat(data):
    try:
        participants = data.get('participants', [])
        chat_name = data.get('name', 'Direct Chat')
        
        # Create consistent chat ID for direct chats
        if len(participants) == 2:
            chat_id = '_'.join(sorted(participants))
        else:
            chat_id = str(uuid.uuid4())
        
        # Check if chat already exists
        if chat_id not in chats:
            chats[chat_id] = {
                'id': chat_id,
                'name': chat_name,
                'participants': participants,
                'created_at': datetime.now().isoformat(),
                'is_group': len(participants) > 2
            }
            
            # Initialize messages array for this chat
            if chat_id not in messages:
                messages[chat_id] = []
        
        # Return chat info to creator
        emit('chat_created', chats[chat_id])
        
        # Notify all participants
        for participant in participants:
            emit('chat_created', chats[chat_id], room=participant)
                
    except Exception as e:
        print(f"Error creating chat: {e}")
        emit('error', {'message': 'Failed to create chat'})

@socketio.on('send_message')
def handle_send_message(data):
    try:
        chat_id = data.get('chat_id')
        user_phone = data.get('sender_phone')
        content = data.get('content')
        
        if not chat_id or not user_phone or not content:
            return
        
        message_id = str(uuid.uuid4())
        message = {
            'id': message_id,
            'chat_id': chat_id,
            'sender_phone': user_phone,
            'sender_name': users.get(user_phone, {}).get('name', 'Unknown'),
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'type': 'text'
        }
        
        # Initialize messages array if not exists
        if chat_id not in messages:
            messages[chat_id] = []
        
        messages[chat_id].append(message)
        
        # Broadcast to all participants in the chat room
        emit('new_message', message, room=chat_id)
        
        print(f'Message sent in chat {chat_id} by {user_phone}: {content}')
        
    except Exception as e:
        print(f"Error sending message: {e}")

@socketio.on('typing_start')
def handle_typing_start(data):
    chat_id = data.get('chat_id')
    user_phone = data.get('user_phone')
    emit('user_typing', {
        'chat_id': chat_id,
        'user_phone': user_phone,
        'user_name': users.get(user_phone, {}).get('name', 'Unknown'),
        'is_typing': True
    }, room=chat_id)

@socketio.on('typing_stop')
def handle_typing_stop(data):
    chat_id = data.get('chat_id')
    user_phone = data.get('user_phone')
    emit('user_typing', {
        'chat_id': chat_id,
        'user_phone': user_phone,
        'is_typing': False
    }, room=chat_id)

# Add some demo users on startup
def create_demo_users():
    demo_users = [
        {'phone': '+1234567890', 'name': 'John Doe', 'status': 'Available'},
        {'phone': '+1987654321', 'name': 'Jane Smith', 'status': 'At the gym'},
        {'phone': '+1122334455', 'name': 'Mike Johnson', 'status': 'Busy'},
        {'phone': '+1555666777', 'name': 'Sarah Wilson', 'status': 'Available'},
        {'phone': '+1444333222', 'name': 'Alex Chen', 'status': 'In a meeting'},
        {'phone': '+1666777888', 'name': 'Maria Garcia', 'status': 'Online'}
    ]
    
    for user_data in demo_users:
        if user_data['phone'] not in users:
            user_id = f"user_{uuid.uuid4().hex[:8]}"
            users[user_data['phone']] = {
                "id": user_id,
                "phone": user_data['phone'],
                "name": user_data['name'],
                "status": user_data['status'],
                "last_seen": datetime.now().isoformat(),
                "is_online": True,
                "created_at": datetime.now().isoformat(),
                "profile_status": user_data['status']
            }
            contacts[user_data['phone']] = []
            online_users.add(user_data['phone'])

if __name__ == '__main__':
    create_demo_users()
    print("🚀 iSightU Chat Server starting on http://127.0.0.1:5000")
    print("📞 Demo users created:")
    for phone, user in users.items():
        print(f"   - {user['name']}: {phone} ({user['status']})")
    print("💬 Ready for real-time messaging with contact management!")
    socketio.run(app, debug=True, host='127.0.0.1', port=5000)