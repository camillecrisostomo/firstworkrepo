# admin_app/apps.py
from django.apps import AppConfig
from django.db.utils import OperationalError

class AdminAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'admin_app'

    def ready(self):
        try:
            # Import inside ready() to avoid AppRegistryNotReady at startup
            from django.contrib.auth.models import User

            username = 'admin'
            email = 'admin@gmail.com'
            password = 'admin123'

            if not User.objects.filter(username=username).exists():
                User.objects.create_superuser(username=username, email=email, password=password)
                print('\n✅ Default admin account created:')
                print(f'   Username: {username}')
                print(f'   Password: {password}')
                print(f'   Email: {email}\n')
        except OperationalError:
            # DB not ready during first migrate -> ignore
            pass
        except Exception as e:
            print(f"⚠️ admin_app.apps.AdminAppConfig.ready() error: {e}")
