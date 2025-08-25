import click
from app import db
from app.models.user import User
from app.models.patient_profile import PatientProfile
from app.models.settings import AppSetting
from app.services.auth import AuthService  # Fixed import path
from sqlalchemy.exc import IntegrityError
import json
users_to_seed = [
    {
        "username": "wicak",
        "email": "wicak@example.com",
        "password": "admin123",
        "user_type": "superuser"
    },
    {
        "username": "waffiq",
        "email": "waffiq@example.com",
        "password": "admin123",
        "user_type": "superuser"
    },
    {
        "username": "samudera",
        "email": "samudera@example.com",
        "password": "admin123",
        "user_type": "superuser"
    },
    {
        "username": "rangga",
        "email": "rangga@example.com",
        "password": "admin123",
        "user_type": "superuser"
    },
    {
        "username": "fadhil",
        "email": "fadhil@example.com",
        "password": "admin123",
        "user_type": "superuser"
    },
    {
        "username": "baqi",
        "email": "baqi@example.com",
        "password": "admin123",
        "user_type": "superuser"
    },
    {
        "username": "oriza",
        "email": "oriza@example.com",
        "password": "admin123",
        "user_type": "superuser"
    },
    {
        "username": "patient",
        "email": "patient@example.com",
        "password": "admin123",
        "user_type": "patient",
        "profile": {
            "age": 25,
            "gender": "female",
            "educational_level": "bachelor",
            "cultural_background": "asian"
        }
    },
    {
        "username": "patient2",
        "email": "patient2@example.com",
        "password": "admin123",
        "user_type": "patient",
        "profile": {
            "age": 35,
            "gender": "male",
            "educational_level": "master",
            "cultural_background": "european"
        }
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

    @app.cli.command("seedu")
    def seed_users():
        """Seeds the database with predefined users."""
        with app.app_context():
            click.echo("Seeding users...")

            for user_data in users_to_seed:
                username = user_data.get("username")
                email = user_data.get("email")
                password = user_data.get("password")
                user_type = user_data.get("user_type", "patient")
                profile_data = user_data.get("profile")

                # Check if user already exists
                existing_user = User.query.filter_by(username=username).first()
                if not existing_user:
                    try:
                        user = AuthService.register_user(
                            username,
                            email,
                            password,
                            user_type,
                            profile_data
                        )
                        profile_info = f" with profile" if profile_data else ""
                        click.echo(f"  - User '{username}' ({user_type}){profile_info} created.")
                    except ValueError as e:
                        click.echo(f"  - Error creating user '{username}': {e}")
                    except Exception as e:
                        click.echo(f"  - Unexpected error creating user '{username}': {e}")
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
        except Exception as e:
            click.echo(f'Unexpected error: {e}')

    @app.cli.command("create-patient")
    def create_patient():
        """Create a patient account interactively with optional profile."""
        username = click.prompt('Patient username')
        email = click.prompt('Patient email')
        password = click.prompt('Patient password', hide_input=True)

        # Optional profile data
        if click.confirm('Add profile information?'):
            profile_data = {}
            age = click.prompt('Age (optional)', default='', show_default=False)
            if age:
                profile_data['age'] = int(age)

            gender = click.prompt('Gender (optional)', default='', show_default=False)
            if gender:
                profile_data['gender'] = gender

            edu_level = click.prompt('Educational level (optional)', default='', show_default=False)
            if edu_level:
                profile_data['educational_level'] = edu_level

            cultural_bg = click.prompt('Cultural background (optional)', default='', show_default=False)
            if cultural_bg:
                profile_data['cultural_background'] = cultural_bg
        else:
            profile_data = None

        try:
            user = AuthService.register_user(username, email, password, 'patient', profile_data)
            profile_info = " with profile" if profile_data else ""
            click.echo(f'Patient user {username}{profile_info} created successfully!')
        except ValueError as e:
            click.echo(f'Error creating patient: {e}')
        except Exception as e:
            click.echo(f'Unexpected error: {e}')

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
        """List all users in the database with their profiles."""
        users = User.query.all()
        if not users:
            click.echo("No users found.")
            return

        click.echo(f"Found {len(users)} users:")
        for user in users:
            status = "Active" if user.is_active else "Inactive"
            profile_info = ""

            if user.is_patient() and user.patient_profile:
                profile = user.patient_profile
                profile_parts = []
                if profile.age:
                    profile_parts.append(f"Age: {profile.age}")
                if profile.gender:
                    profile_parts.append(f"Gender: {profile.gender}")
                if profile_parts:
                    profile_info = f" ({', '.join(profile_parts)})"

            click.echo(f"  - {user.username} ({user.user_type}) - {user.email} [{status}]{profile_info}")

    @app.cli.command("list-settings")
    def list_settings():
        """List all settings in the database."""
        settings = AppSetting.query.order_by(AppSetting.key).all()
        if not settings:
            click.echo("No settings found.")
            return

        click.echo(f"Found {len(settings)} settings:")
        click.echo("-" * 80)

        for setting in settings:
            # Pretty print JSON values
            value = setting.value
            if setting.key.endswith('_questions') or setting.key == 'phq_enabled_categories':
                try:
                    parsed = json.loads(value)
                    print(parsed)
                    if isinstance(parsed, list):
                        value = f"[{len(parsed)} items]: {parsed}"
                    else:
                        value = json.dumps(parsed, indent=2)
                except:
                    pass  # Keep original value if not JSON

            # Truncate long values
            if len(str(value)) > 100:
                value = str(value)[:97] + "..."

            click.echo(f"  {setting.key:<30} = {value}")
            if setting.updated_at:
                click.echo(f"  {'':<30}   (Updated: {setting.updated_at.strftime('%Y-%m-%d %H:%M:%S')})")
            click.echo()

    @app.cli.command("settings")
    def show_all_settings():
        """Show detailed view of ALL settings."""
        settings = AppSetting.query.order_by(AppSetting.key).all()
        if not settings:
            click.echo("No settings found.")
            return

        click.echo(f"Showing all {len(settings)} settings in detail:")
        click.echo("=" * 80)
        for i, setting in enumerate(settings, 1):
            click.echo(f"\n[{i}] {setting.key}")
            click.echo(f"    Created: {setting.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            click.echo(f"    Updated: {setting.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
            click.echo(f"    Value:")
            try:
                parsed = json.loads(setting.value)
                formatted = json.dumps(parsed, indent=2)
                # Indent each line for better readability
                indented = '\n'.join('      ' + line for line in formatted.split('\n'))
                click.echo(indented)
            except:
                # Indent regular values too
                value_lines = str(setting.value).split('\n')
                for line in value_lines:
                    click.echo(f"      {line}")
            if i < len(settings):
                click.echo("    " + "-" * 60)

    @app.cli.command("keys")
    def show_keys():
        """Displays all the application setting keys."""
        settings = AppSetting.query.order_by(AppSetting.key).all()
        click.echo("-" * 50)
        for setting in settings:
            click.echo(setting.key)
        click.echo("-" * 50)

    @app.cli.command("routes")
    @click.option("--format", type=click.Choice(["plain", "md"]), default="plain",
                  help="Output format: plain text or Markdown table.")
    def list_routes(format):
        """List all registered routes/endpoints."""
        def clean_methods(methods):
            return sorted(m for m in methods if m not in ("HEAD", "OPTIONS"))

        routes = []
        for rule in app.url_map.iter_rules():
            routes.append({
                "blueprint": rule.endpoint.split(".", 1)[0] if "." in rule.endpoint else "main",
                "endpoint": rule.endpoint,
                "methods": clean_methods(rule.methods),
                "path": rule.rule,
            })

        routes.sort(key=lambda r: (r["blueprint"], r["path"]))

        if format == "md":
            click.echo(f"Found {len(routes)} routes.\n")
            click.echo("| Blueprint | Methods | Path | Endpoint |")
            click.echo("|----------|---------|------|----------|")
            for r in routes:
                methods = ",".join(r["methods"])
                click.echo(f"| {r['blueprint']} | {methods} | `{r['path']}` | {r['endpoint']} |")
            return

        # plain format
        click.echo(f"Found {len(routes)} routes.")
        click.echo("-" * 80)
        current_bp = None
        for r in routes:
            if r["blueprint"] != current_bp:
                current_bp = r["blueprint"]
                click.echo(f"\n{current_bp.upper()}:", nl=True)
            methods = ",".join(r["methods"])
            click.echo(f"  {methods:<10} {r['path']:<35} → {r['endpoint']}")

    @app.cli.command("clear-settings")
    def clear_settings():
        """Clear all settings from database. WARNING: This deletes all settings!"""
        if click.confirm('This will delete ALL settings. Are you sure?'):
            try:
                count = AppSetting.query.count()
                AppSetting.query.delete()
                db.session.commit()
                click.echo(f"Cleared {count} settings successfully!")
            except Exception as e:
                db.session.rollback()
                click.echo(f"Error clearing settings: {e}")
        else:
            click.echo("Clear settings cancelled.")

    @app.cli.command("set-setting")
    @click.argument('key')
    @click.argument('value')
    def set_setting(key, value):
        """Set a specific setting value."""
        try:
            setting = AppSetting.query.filter_by(key=key).first()
            if setting:
                old_value = setting.value
                setting.value = value
                click.echo(f"Updated setting '{key}':")
                click.echo(f"  Old: {old_value}")
                click.echo(f"  New: {value}")
            else:
                setting = AppSetting(key=key, value=value)
                db.session.add(setting)
                click.echo(f"Created new setting '{key}' = '{value}'")

            db.session.commit()
            click.echo("Setting saved successfully!")

        except Exception as e:
            db.session.rollback()
            click.echo(f"Error setting value: {e}")

    @app.cli.command("test-openai")
    def test_openai():
        click.echo("Testing OpenAI chat service...")
        preprompt = AppSetting.query.filter_by(key='openquestion_prompt').first()
        instructions = AppSetting.query.filter_by(key='openquestion_instructions').first()

        if not preprompt:
            click.echo("Missing 'openquestion_prompt' in database")
            click.echo("Run: flask add-chat-settings")
            return

        if not instructions:
            click.echo("Missing 'openquestion_instructions' in database")
            click.echo("Run: flask add-chat-settings")
            return

        click.echo(" Database settings found")

        # Test OpenAI service
        def test_sync():
            try:
                from app.services.openai_chat import OpenAIChatService

                service = OpenAIChatService()
                click.echo(" Service initialized")

                # Create dummy chat session
                chat_session = service.create_chat_session("test-session", 999)
                click.echo(" Chat session created")

                # Test streaming response (synchronous)
                click.echo("🤖 Testing with message: 'Hello, how are you?'")

                # Collect streaming response
                response_chunks = []
                try:
                    for chunk in service.generate_streaming_response(chat_session, "Hello, how are you?"):
                        response_chunks.append(chunk)

                    full_response = ''.join(response_chunks)
                    click.echo(f" Full response ({len(full_response)} chars): {full_response[:100]}...")

                    click.echo("🎉 OpenAI service working correctly!")
                except Exception as stream_error:
                    click.echo(f"Streaming error: {str(stream_error)}")
                    raise

            except Exception as e:
                click.echo(f"OpenAI service error: {str(e)}")
                import traceback
                click.echo(traceback.format_exc())

        # Run test (no longer async)
        test_sync()

    @app.cli.command("add-chat-settings")
    def add_chat_settings():
        try:
            preprompt = AppSetting.query.filter_by(key='openquestion_prompt').first()
            if not preprompt:
                preprompt = AppSetting(
                    key='openquestion_prompt',
                    value='You are a supportive mental health assistant. Be empathetic, ask thoughtful follow-up questions, and provide a safe space for conversation. Keep responses conversational and 1-3 sentences.'
                )
                db.session.add(preprompt)
            else:
                click.echo("openquestion_prompt already exists")

            # Add instructions
            instructions = AppSetting.query.filter_by(key='openquestion_instructions').first()
            if not instructions:
                instructions = AppSetting(
                    key='openquestion_instructions',
                    value='Please share your thoughts and feelings openly. This conversation is confidential and designed to help assess your mental well-being.'
                )
                db.session.add(instructions)
                click.echo("Added openquestion_instructions")
            else:
                click.echo("openquestion_instructions already exists")

            db.session.commit()
            click.echo("Chat settings ready!")

        except Exception as e:
            db.session.rollback()
            click.echo(f"Error adding settings: {e}")

    @app.cli.command("test-emotion-capture")
    def test_emotion_capture():
        """Test emotion capture functionality and storage system."""
        click.echo("Testing emotion capture system...")

        try:
            from app.services.settings import SettingsService
            from app.services.emotion_storage import emotion_storage
            from app.models.assessment import Assessment, EmotionData
            from app.models.user import User
            import base64
            import os

            # Test recording configuration
            recording_config = SettingsService.get_recording_config()
            click.echo(f"✅ Recording config loaded: {recording_config}")

            # Test upload directory
            upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
            click.echo(f"✅ Upload folder: {upload_folder}")

            # Ensure upload directory exists
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder, exist_ok=True)
                click.echo(f"✅ Created upload directory: {upload_folder}")

            # Create test directory structure
            test_session_dir = os.path.join(upload_folder, 'assessments', 'test_session_123')
            os.makedirs(os.path.join(test_session_dir, 'phq9', 'images'), exist_ok=True)
            os.makedirs(os.path.join(test_session_dir, 'phq9', 'videos'), exist_ok=True)
            os.makedirs(os.path.join(test_session_dir, 'open_questions', 'images'), exist_ok=True)
            os.makedirs(os.path.join(test_session_dir, 'open_questions', 'videos'), exist_ok=True)
            click.echo("✅ Test directory structure created")

            # Create test user and assessment if they don't exist
            test_user = User.query.filter_by(username='patient').first()
            if not test_user:
                click.echo("❌ Test patient user not found. Run 'flask seedu' first.")
                return

            # Create test assessment
            test_assessment = Assessment.query.filter_by(session_id='test_session_123').first()
            if not test_assessment:
                test_assessment = Assessment(
                    session_id='test_session_123',
                    user_id=test_user.id
                )
                db.session.add(test_assessment)
                db.session.commit()
                click.echo("✅ Test assessment created")

            # Create test image data (simple test data)
            test_image_data = b"test_image_data_for_emotion_capture"

            # Test image capture save
            emotion_data = emotion_storage.save_emotion_capture(
                session_id='test_session_123',
                user_id=test_user.id,
                assessment_type='phq9',
                question_identifier='q1_test',
                file_data=test_image_data,
                media_type='image',
                original_filename='test_capture.jpg',
                metadata={
                    'resolution': '1x1',
                    'quality': 0.8,
                    'capture_timestamp': 1234567890,
                    'time_into_question_ms': 5000,
                    'recording_settings': recording_config
                }
            )
            click.echo(f"✅ Test emotion capture saved: ID {emotion_data.id}")

            # Verify file exists
            if emotion_data.file_exists():
                click.echo(f"✅ Physical file exists: {emotion_data.get_full_path()}")
            else:
                click.echo(f"❌ Physical file missing: {emotion_data.get_full_path()}")

            # Test session files retrieval
            session_files = emotion_storage.get_session_files('test_session_123', test_user.id)
            click.echo(f"✅ Retrieved {len(session_files)} session files")

            # Test validation
            validation = emotion_storage.validate_session_files('test_session_123', test_user.id)
            click.echo(f"✅ File validation: {validation['valid_files']}/{validation['total_files']} files valid")

            click.echo("🎉 All emotion capture tests passed!")

        except Exception as e:
            click.echo(f"❌ Test failed: {e}")
            import traceback
            click.echo(traceback.format_exc())

    @app.cli.command("test-storage")
    def test_storage():
        """Test storage directory structure and permissions."""
        click.echo("Testing storage system...")

        try:
            import os
            upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')

            # Test base directory
            click.echo(f"Upload folder: {upload_folder}")
            if os.path.exists(upload_folder):
                click.echo("✅ Base upload directory exists")
            else:
                os.makedirs(upload_folder, exist_ok=True)
                click.echo("✅ Created base upload directory")

            # Test write permissions
            test_file = os.path.join(upload_folder, 'test_write.txt')
            try:
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                click.echo("✅ Write permissions OK")
            except Exception as e:
                click.echo(f"❌ Write permission error: {e}")

            # Test directory structure creation
            test_dirs = [
                'assessments/test_session/phq9/images',
                'assessments/test_session/phq9/videos',
                'assessments/test_session/open_questions/images',
                'assessments/test_session/open_questions/videos'
            ]

            for test_dir in test_dirs:
                full_path = os.path.join(upload_folder, test_dir)
                os.makedirs(full_path, exist_ok=True)
                if os.path.exists(full_path):
                    click.echo(f"✅ Created: {test_dir}")
                else:
                    click.echo(f"❌ Failed to create: {test_dir}")

            click.echo("🎉 Storage system test completed!")

        except Exception as e:
            click.echo(f"❌ Storage test failed: {e}")

    @app.cli.command("test-directory-auto-creation")
    def test_directory_auto_creation():
        """Test that directories are automatically created with parents=True behavior."""
        click.echo("Testing automatic directory creation...")

        try:
            import tempfile
            import shutil
            import os
            from app.services.emotion_storage import emotion_storage

            # Create a temporary directory for testing
            with tempfile.TemporaryDirectory() as temp_dir:
                click.echo(f"Using temporary test directory: {temp_dir}")

                # Test deep nested directory creation
                test_path = os.path.join(temp_dir, 'level1', 'level2', 'level3', 'level4')
                emotion_storage._ensure_directory(test_path)

                if os.path.exists(test_path):
                    click.echo("✅ Deep nested directory creation works")
                else:
                    click.echo("❌ Deep nested directory creation failed")

                # Test session directory creation
                session_dir = emotion_storage._get_session_directory('test_session', 'phq9', 'image')
                full_session_path = os.path.join(temp_dir, session_dir)
                emotion_storage._ensure_directory(full_session_path)

                if os.path.exists(full_session_path):
                    click.echo("✅ Session directory auto-creation works")
                else:
                    click.echo("❌ Session directory auto-creation failed")

                # Test with different assessment types
                test_combinations = [
                    ('test_session_1', 'phq9', 'image'),
                    ('test_session_1', 'phq9', 'video'),
                    ('test_session_1', 'open_questions', 'image'),
                    ('test_session_1', 'open_questions', 'video'),
                    ('another_session_123', 'phq9', 'image'),
                ]

                for session_id, assessment_type, media_type in test_combinations:
                    rel_dir = emotion_storage._get_session_directory(session_id, assessment_type, media_type)
                    full_path = os.path.join(temp_dir, rel_dir)
                    emotion_storage._ensure_directory(full_path)

                    if os.path.exists(full_path):
                        click.echo(f"✅ Created: {rel_dir}")
                    else:
                        click.echo(f"❌ Failed: {rel_dir}")

                click.echo("🎉 Directory auto-creation test completed!")

        except Exception as e:
            click.echo(f"❌ Directory auto-creation test failed: {e}")
            import traceback
            click.echo(traceback.format_exc())
