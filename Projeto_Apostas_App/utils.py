import requests
from django.conf import settings
from requests.exceptions import RequestException
import logging

logger = logging.getLogger(__name__)

def make_request(url, method='GET', **kwargs):
    """
    Função utilitária para fazer requisições HTTP com suporte a proxy.
    
    Args:
        url (str): URL da requisição
        method (str): Método HTTP (GET, POST, etc)
        **kwargs: Argumentos adicionais para requests
        
    Returns:
        requests.Response: Objeto de resposta da requisição
        
    Raises:
        RequestException: Se houver erro na requisição
    """
    try:
        # Configuração do proxy
        proxies = {}
        if settings.PROXY_ENABLED and settings.PROXY_URL:
            proxies = {
                'http': settings.PROXY_URL,
                'https': settings.PROXY_URL
            }
            
            # Adiciona autenticação se necessário
            if settings.PROXY_USERNAME and settings.PROXY_PASSWORD:
                proxies['http'] = f"http://{settings.PROXY_USERNAME}:{settings.PROXY_PASSWORD}@{settings.PROXY_URL}"
                proxies['https'] = f"https://{settings.PROXY_USERNAME}:{settings.PROXY_PASSWORD}@{settings.PROXY_URL}"

        # Configuração do timeout
        timeout = kwargs.pop('timeout', settings.REQUEST_TIMEOUT)
        
        # Faz a requisição
        response = requests.request(
            method=method,
            url=url,
            proxies=proxies,
            timeout=timeout,
            **kwargs
        )
        
        # Verifica se a requisição foi bem sucedida
        response.raise_for_status()
        
        return response
        
    except RequestException as e:
        logger.error(f"Erro na requisição para {url}: {str(e)}")
        raise 