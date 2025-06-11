# Projeto_Apostas_App/urls.py
from django.urls import path
from django.shortcuts import redirect
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('registo/', views.registo_view, name='registo'), 
    path('perfil/', views.perfil_view, name='perfil'),
    path('editar/', views.editar_perfil, name='editar_perfil'), 
    path('', views.home, name='home'),
    path('best_bets/', views.best_bets, name='best_bets'),
    path('my_bets/', views.my_bets, name='my_bets'),
    path('logout/', views.logout_view, name='logout'),
    path('carregar-saldo/', views.carregar_saldo, name='carregar_saldo'),
    path('criar-aposta/', views.criar_aposta, name='criar_aposta'),
    path('search_ajax/', views.search_ajax, name='search_ajax'),
    path('player_details/<int:player_id>/', views.player_details, name='player_details'),
    path('live-games/', views.live_games, name='live_games'),
    path('game-stats/<str:game_id>/', views.game_stats, name='game_stats'),
    path('next_games/', views.next_games, name='next_games'),
    path('estatisticas/', views.estatisticas, name='estatisticas'),
    path('player/<int:player_id>/stat/<str:stat_type>/', views.player_stat, name='player_stat'),
    path('get_filtered_graph/', views.player_filtered_graph, name='get_filtered_graph'),
    path('get_next_game/', views.get_next_game, name='get_next_game'),
    
        # Redirecionar /accounts/login/ para /login/
    path('accounts/login/', lambda request: redirect('login')),

]
