import click
from app import db
from app.models.user import User
from app.services.auth import AuthService
from sqlalchemy.exc import IntegrityError
users_to_seed = [
    {
        "username": "admin",
        "email": "admin@example.com", 
        "password": "admin123",
        "user_type": "superuser"
    },
    {
        "username": "user",
        "email": "patient1@example.com",
        "password": "user123", 
        "user_type": "patient"
    },

]

def register_commands(app):
    """Register all custom CLI commands with the Flask app."""
    
    @app.cli.command("init-db")
    def init_db():
        """Creates all database tables from the models. Run this first."""
        try:
            db.create_all()
            click.echo("Database tables created successfully!")
        except Exception as e:
            click.echo(f"Error creating database tables: {e}")
    
    @app.cli.command("seed-users") 
    def seed_users():
        """Seeds the database with predefined users."""
        with app.app_context():
            click.echo("Seeding users...")
            
            for user_data in users_to_seed:
                username = user_data.get("username")
                email = user_data.get("email") 
                password = user_data.get("password")
                user_type = user_data.get("user_type", "patient")
                
                # Check if user already exists
                existing_user = User.query.filter_by(username=username).first()
                if not existing_user:
                    try:
                        user = AuthService.register_user(username, email, password, user_type)
                        click.echo(f"  - User '{username}' ({user_type}) created.")
                    except ValueError as e:
                        click.echo(f"  - Error creating user '{username}': {e}")
                else:
                    # Update user type if different
                    if existing_user.user_type != user_type:
                        existing_user.user_type = user_type
                        click.echo(f"  - User '{username}' already exists. Type updated to '{user_type}'.")
                    else:
                        click.echo(f"  - User '{username}' already exists.")
            
            try:
                db.session.commit()
                click.echo("User seeding complete.")
            except IntegrityError as e:
                db.session.rollback()
                click.echo(f"Error during seeding: {e}")
    
    @app.cli.command("create-admin")
    def create_admin():
        """Create a superuser admin account interactively."""
        username = click.prompt('Admin username')
        email = click.prompt('Admin email')
        password = click.prompt('Admin password', hide_input=True)
        
        try:
            user = AuthService.register_user(username, email, password, 'superuser')
            click.echo(f'Admin user {username} created successfully!')
        except ValueError as e:
            click.echo(f'Error creating admin: {e}')
    
    @app.cli.command("reset-db")
    def reset_db():
        """Drop all tables and recreate them. WARNING: This deletes all data!"""
        if click.confirm('This will delete ALL data. Are you sure?'):
            try:
                db.drop_all()
                db.create_all()
                click.echo("Database reset successfully!")
            except Exception as e:
                click.echo(f"Error resetting database: {e}")
        else:
            click.echo("Database reset cancelled.")
    
    @app.cli.command("list-users")
    def list_users():
        """List all users in the database."""
        users = User.query.all()
        if not users:
            click.echo("No users found.")
            return
        
        click.echo(f"Found {len(users)} users:")
        for user in users:
            status = "Active" if user.is_active else "Inactive"
            click.echo(f"  - {user.username} ({user.user_type}) - {user.email} [{status}]")\

  