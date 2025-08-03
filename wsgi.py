from flask import render_template, redirect, url_for
from flask_login import login_required, current_user
from app import create_app

app = create_app()

@app.route('/')
@login_required  
def index():
    return render_template('index.html')

@app.before_request
def before_request():
    from flask import request
    if not current_user.is_authenticated and request.endpoint not in ['auth.login', 'auth.register', 'static']:
        return redirect(url_for('auth.login'))

if __name__ == '__main__':
    app.run()