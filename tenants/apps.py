from django.apps import AppConfig


class TenantsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tenants'
    verbose_name = 'Tenant Management'

    def ready(self):
        """
        Initialize any signals or additional configurations
        when the app is ready
        """
        pass
