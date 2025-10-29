"""
Flask Web Server for AI Discord Bot Dashboard
Handles model selection, user preferences, and API endpoints
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import json
import os
import asyncio
from datetime import datetime, timedelta
import secrets
from model_manager import model_manager, ModelStatus

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Simple in-memory user store (replace with database in production)
users_db = {
    'demo_user': {
        'username': 'Demo User',
        'discord_id': '123456789',
        'password_hash': 'demo_password',  # In production, use proper password hashing
        'created_at': datetime.now().isoformat()
    }
}

@app.route('/')
def index():
    """Serve the main dashboard"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Simple demo authentication
        if username == 'demo' and password == 'demo':
            session['user_id'] = 'demo_user'
            session['username'] = 'Demo User'
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Handle user logout"""
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/user-info')
def get_user_info():
    """Get current user information"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session['user_id']
    user = users_db.get(user_id, {})
    
    return jsonify({
        'username': user.get('username', 'Unknown User'),
        'discord_id': user.get('discord_id'),
        'user_id': user_id
    })

@app.route('/api/stats')
def get_stats():
    """Get model statistics and current user preferences"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session['user_id']
    stats = model_manager.get_model_stats()
    
    # Get current user's preferred model
    current_model_id = model_manager.get_user_preference(user_id)
    current_model = model_manager.get_model_info(current_model_id)
    
    return jsonify({
        'stats': {
            'total_models': stats['total_models'],
            'online_models': stats['online_models'],
            'offline_models': stats['offline_models'],
            'degraded_models': stats['degraded_models']
        },
        'models': stats['models'],
        'current_model': {
            'id': current_model.id if current_model else 'unknown',
            'name': current_model.name if current_model else 'Unknown',
            'description': current_model.description if current_model else 'No model selected',
            'status': current_model.status.value if current_model else 'unknown',
            'provider': current_model.provider.value if current_model else 'unknown',
            'max_tokens': current_model.max_tokens if current_model else 0,
            'cost_per_1k_tokens': current_model.cost_per_1k_tokens if current_model else 0,
            'supports_images': current_model.supports_images if current_model else False,
            'supports_functions': current_model.supports_functions if current_model else False,
            'usage_count': current_model.usage_count if current_model else 0,
            'error_count': current_model.error_count if current_model else 0,
            'avg_response_time': current_model.avg_response_time if current_model else 0
        }
    })

@app.route('/api/set-model', methods=['POST'])
def set_model():
    """Set user's preferred model"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.get_json()
    model_id = data.get('model_id')
    
    if not model_id:
        return jsonify({'error': 'Model ID required'}), 400
    
    user_id = session['user_id']
    success = model_manager.set_user_preference(user_id, model_id)
    
    if success:
        return jsonify({'success': True, 'message': 'Model updated successfully'})
    else:
        return jsonify({'error': 'Invalid model ID'}), 400

@app.route('/api/test-model', methods=['POST'])
def test_model():
    """Test a specific model with a prompt"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.get_json()
    model_id = data.get('model_id')
    prompt = data.get('prompt')
    
    if not model_id or not prompt:
        return jsonify({'error': 'Model ID and prompt required'}), 400
    
    # Run the async function in a new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        response, used_model = loop.run_until_complete(
            model_manager.get_chat_response(
                prompt=prompt,
                user_id=session['user_id'],
                is_nsfw=False,
                history=None,
                system_override=None,
                preferred_model=model_id
            )
        )
        
        return jsonify({
            'success': True,
            'response': response,
            'model_used': used_model
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        loop.close()

@app.route('/api/health-check')
def health_check():
    """Trigger a health check on all models"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Run health check in background
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(model_manager.health_check())
        return jsonify({'success': True, 'message': 'Health check completed'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        loop.close()

@app.route('/api/models')
def get_models():
    """Get detailed information about all models"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    models = []
    for model_id, model in model_manager.models.items():
        models.append({
            'id': model.id,
            'name': model.name,
            'provider': model.provider.value,
            'description': model.description,
            'max_tokens': model.max_tokens,
            'cost_per_1k_tokens': model.cost_per_1k_tokens,
            'supports_images': model.supports_images,
            'supports_functions': model.supports_functions,
            'status': model.status.value,
            'last_used': model.last_used,
            'usage_count': model.usage_count,
            'error_count': model.error_count,
            'avg_response_time': model.avg_response_time
        })
    
    return jsonify({'models': models})

@app.route('/api/user-preferences')
def get_user_preferences():
    """Get user's model preferences and settings"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session['user_id']
    prefs = model_manager.user_preferences.get(user_id)
    
    if prefs:
        return jsonify({
            'preferred_model': prefs.preferred_model,
            'fallback_models': prefs.fallback_models,
            'custom_settings': prefs.custom_settings,
            'last_updated': prefs.last_updated
        })
    else:
        return jsonify({
            'preferred_model': model_manager.get_default_model(),
            'fallback_models': [],
            'custom_settings': {},
            'last_updated': None
        })

@app.route('/api/set-preferences', methods=['POST'])
def set_user_preferences():
    """Update user's model preferences and settings"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.get_json()
    user_id = session['user_id']
    
    # Update preferences
    if user_id not in model_manager.user_preferences:
        from model_manager import UserPreferences
        model_manager.user_preferences[user_id] = UserPreferences(
            user_id=user_id,
            preferred_model=data.get('preferred_model', model_manager.get_default_model()),
            fallback_models=data.get('fallback_models', []),
            custom_settings=data.get('custom_settings', {}),
            last_updated=datetime.now().timestamp()
        )
    else:
        prefs = model_manager.user_preferences[user_id]
        prefs.preferred_model = data.get('preferred_model', prefs.preferred_model)
        prefs.fallback_models = data.get('fallback_models', prefs.fallback_models)
        prefs.custom_settings = data.get('custom_settings', prefs.custom_settings)
        prefs.last_updated = datetime.now().timestamp()
    
    model_manager._save_user_preferences()
    
    return jsonify({'success': True, 'message': 'Preferences updated successfully'})

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    # Move dashboard.html to templates directory
    if os.path.exists('dashboard.html'):
        import shutil
        shutil.move('dashboard.html', 'templates/dashboard.html')
    
    # Create login template
    login_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - AI Discord Bot Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        .gradient-bg {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
    </style>
</head>
<body class="gradient-bg min-h-screen flex items-center justify-center">
    <div class="max-w-md w-full space-y-8">
        <div>
            <div class="mx-auto h-12 w-12 flex items-center justify-center rounded-full bg-white bg-opacity-20">
                <i class="fas fa-robot text-white text-xl"></i>
            </div>
            <h2 class="mt-6 text-center text-3xl font-extrabold text-white">
                AI Discord Bot Dashboard
            </h2>
            <p class="mt-2 text-center text-sm text-white text-opacity-80">
                Sign in to manage your AI model preferences
            </p>
        </div>
        <form class="mt-8 space-y-6" method="POST">
            <div class="rounded-md shadow-sm -space-y-px">
                <div>
                    <label for="username" class="sr-only">Username</label>
                    <input id="username" name="username" type="text" required 
                           class="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm" 
                           placeholder="Username" value="demo">
                </div>
                <div>
                    <label for="password" class="sr-only">Password</label>
                    <input id="password" name="password" type="password" required 
                           class="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm" 
                           placeholder="Password" value="demo">
                </div>
            </div>

            {% if error %}
            <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
                {{ error }}
            </div>
            {% endif %}

            <div>
                <button type="submit" 
                        class="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                    <span class="absolute left-0 inset-y-0 flex items-center pl-3">
                        <i class="fas fa-lock text-blue-500 group-hover:text-blue-400"></i>
                    </span>
                    Sign in
                </button>
            </div>
            
            <div class="text-center">
                <p class="text-white text-opacity-80 text-sm">
                    Demo credentials: username: <strong>demo</strong>, password: <strong>demo</strong>
                </p>
            </div>
        </form>
    </div>
</body>
</html>'''
    
    with open('templates/login.html', 'w') as f:
        f.write(login_template)
    
    print("Starting Flask web server...")
    print("Dashboard will be available at: http://localhost:5000")
    print("Demo login: username='demo', password='demo'")
    
    app.run(debug=True, host='0.0.0.0', port=5000)

