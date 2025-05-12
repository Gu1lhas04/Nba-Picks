"""
WSGI config for Projeto_Apostas project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os
from django.core.wsgi import get_wsgi_application

# Certifique-se de que o nome do módulo de configurações está correto aqui
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Projeto_Apostas.settings')

application = get_wsgi_application()

