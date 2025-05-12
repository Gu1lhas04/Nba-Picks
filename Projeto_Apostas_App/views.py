# Arquivo views.py limpo e organizado
# IMPORTS PADRÃO DJANGO
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib import messages
from django.http import JsonResponse
from django.utils.timezone import get_current_timezone, localtime
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count, Sum, Q
from django.views.decorators.cache import cache_page
from django.core.cache import cache

# IMPORTS MODELS & FORMS
from .forms import RegistroForm, PerfilForm, SaldoForm, ApostaForm, ApostaMultiplaForm
from .models import Aposta, ApostaMultipla

# IMPORTS EXTERNOS
from nba_api.stats.static import players, teams
from nba_api.stats.endpoints import commonplayerinfo, PlayerGameLog, commonteamroster, boxscoretraditionalv2
from nba_api.live.nba.endpoints import scoreboard,boxscore, playbyplay
from bs4 import BeautifulSoup
from unidecode import unidecode
from dateutil import parser
from collections import defaultdict
from datetime import timezone
from decimal import Decimal
from requests.exceptions import Timeout


# IMPORTS PADRÃO PYTHON
from datetime import datetime, timezone, timedelta
import time as time_module  # Renomeando para evitar conflito
from time import sleep
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import requests
import json
import re
import plotly.graph_objects as go
import plotly.io as pio
import numpy as np
from scipy.stats import norm



def get_current_season():
    """
    Obtém a temporada atual da NBA.
    
    Returns:
        str: Ano da temporada atual no formato 'YYYY-YY'.
    """
    # Obtém a data e hora atual
    now = datetime.now()
    year = now.year
    month = now.month

    # Verifica se o mês atual é outubro (10) ou posterior
    if month >= 10: 
        # Se sim, a época é do ano atual até ao próximo ano
        season = f"{year}-{str(year + 1)[-2:]}"
    else:  # Janeiro até Setembro
        # Caso contrário, a época é do ano anterior até ao ano atual 
        season = f"{year - 1}-{str(year)[-2:]}"
    
    return season


#Registo
def registo_view(request):
    """
    View para registo de novos utilizadores.
    
    Args:
        request: HttpRequest do Django.
    
    Returns:
        HttpResponse: Página de registo ou redirecionamento após registo bem-sucedido.
    """
    if request.method == 'POST':
        form = RegistroForm(request.POST)  
        if form.is_valid():
            user = form.save()  
            login(request, user)  
            return redirect('perfil')  
    else:
        form = RegistroForm() 
    return render(request, 'Registo.html', {'form': form})


def login_view(request):
    """
    View para autenticação de utilizadores.
    
    Args:
        request: HttpRequest do Django.
    
    Returns:
        HttpResponse: Página de login ou redirecionamento após login bem-sucedido.
    """
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, "✅ Login realizado com sucesso!") 
            return redirect('home')  
        else:
            messages.error(request, "❌ Nome de Utilizador ou senha incorretos.")  
            return redirect('login')  
        
    return render(request, 'Login.html')


# Visualizar Perfil
@login_required
def perfil_view(request):
    """
    View para exibição e gestão do perfil do utilizador.
    
    Args:
        request: HttpRequest do Django.
    
    Returns:
        HttpResponse: Página do perfil do utilizador.
    """
    if request.method == 'POST':
        form = PerfilForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('perfil')
    else:
        form = PerfilForm(instance=request.user)
    
    return render(request, 'perfil.html', {'form': form})


#Carregar o Saldo
@login_required
def carregar_saldo(request):
    """
    View para carregamento de saldo na conta do utilizador.
    
    Args:
        request: HttpRequest do Django.
    
    Returns:
        HttpResponse: Página de carregamento de saldo ou redirecionamento após carregamento.
    """
    user = request.user
    
    if request.method == "POST":
        form = SaldoForm(request.POST)
        if form.is_valid():
            valor = form.cleaned_data['valor']
            user.saldo += valor
            user.save()

            messages.success(request, '✅ Você depositou com sucesso!')
            referer_url = request.META.get('HTTP_REFERER', 'home')
            return redirect(referer_url)

    else:
        form = SaldoForm()

    return render(request, 'carregar_saldo.html', {'form': form})


def editar_perfil(request):
    """
    View para edição do perfil do usuário logado.
    Permite atualizar dados e foto de perfil, além de alterar a senha.
    
    Args:
        request: HttpRequest do Django.
    
    Returns:
        HttpResponse: Página de edição de perfil ou resposta JSON em caso de POST.
    """
    if request.method == 'POST':
        form = PerfilForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            user = form.save(commit=False)

            password = form.cleaned_data.get('password')
            if password:
                user.set_password(password)
            
            user.save()

            if 'password' in form.changed_data:
                update_session_auth_hash(request, user)

            # Responde com um JSON indicando que a foto foi salva e redirecionamento
            return JsonResponse({'redirect_url': '/perfil/'})  # Pode mudar para onde quiser redirecionar
        else:
            return JsonResponse({'error': 'Formulário inválido!'}, status=400)

    else:
        form = PerfilForm(instance=request.user)

    return render(request, 'editar_perfil.html', {'form': form})


@login_required
def home(request):
    """
    View principal (home) do utilizador logado.
    Apresenta jogos ao vivo, futuros, apostas e melhores apostas sugeridas.
    
    Args:
        request: HttpRequest do Django.
    
    Returns:
        HttpResponse: Página inicial com dados dos jogos e apostas.
    """
    print(f"Cache key: home_{request.user.id}")
    def format_game_time(time_str):
        if time_str and time_str.startswith("PT"):
            try:
                time_str = time_str[2:-1]
                minutes, seconds = time_str.split("M")
                seconds = seconds.split('.')[0]
                return f"{minutes} min {seconds} sec"
            except Exception:
                return "Tempo não disponível"
        return "Tempo não disponível"

    def get_game_time(home_team_name, away_team_name, all_games):
        for g in all_games:
            ht = g['homeTeam']['teamName'].lower()
            at = g['awayTeam']['teamName'].lower()
            if (ht in home_team_name.lower() and at in away_team_name.lower()) or \
               (ht in away_team_name.lower() and at in home_team_name.lower()):
                time_local = parser.parse(g['gameTimeUTC']).replace(tzinfo=timezone.utc).astimezone(tz=None)
                return time_local.strftime("%H:%M")
        return "–"

    filtro = request.GET.get('filtro', '24h')
    today = datetime.now().date()
    now = datetime.now(timezone.utc)

    if filtro == 'hoje':
        inicio = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
        fim = now
    elif filtro == 'ontem':
        ontem = today - timedelta(days=1)
        inicio = datetime.combine(ontem, datetime.min.time(), tzinfo=timezone.utc)
        fim = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
    elif filtro == '2dias':
        inicio = now - timedelta(days=2)
        fim = now
    elif filtro == '7dias':
        inicio = now - timedelta(days=7)
        fim = now
    elif filtro == '15dias':
        inicio = now - timedelta(days=15)
        fim = now
    elif filtro == 'pendentes':
        inicio = fim = None
    else:
        inicio = now - timedelta(hours=24)
        fim = now

    if filtro == 'pendentes':
        apostas_simples = Aposta.objects.filter(user=request.user, status="pendente")
        apostas_multipla = ApostaMultipla.objects.filter(user=request.user, status="pendente")
        apostas_em_multipla = apostas_multipla.values_list('apostas__id', flat=True)
        apostas_simples = apostas_simples.exclude(id__in=apostas_em_multipla)
    else:
        apostas = Aposta.objects.filter(user=request.user, data_aposta__range=(inicio, fim))
        apostas_multipla = ApostaMultipla.objects.filter(user=request.user, data_aposta__range=(inicio, fim))
        aposta_ids_multipla = apostas_multipla.values_list('apostas__id', flat=True)
        apostas_simples = apostas.exclude(id__in=aposta_ids_multipla)

    # Buscar apostas pendentes do utilizador
    apostas_pendentes = Aposta.objects.filter(user=request.user, status="pendente")

    # Debug: Exibir os IDs de jogos das apostas pendentes
    print(f"Apostas pendentes do utilizador: {[aposta.jogo_id for aposta in apostas_pendentes]}")

    # Verificar as apostas pendentes para jogos finalizados
    for aposta in apostas_pendentes:
        jogo_id = aposta.jogo_id  # Pega o jogo_id da aposta

        print(f"Verificando aposta com jogo ID: {jogo_id}")

        if jogo_id:
            # Chama a função de verificação de apostas para esse jogo
            verificar_apostas_por_jogo(jogo_id, user=request.user)
        else:
            print(f"Jogo com ID {jogo_id} não encontrado ou inválido.")

    # Construção dos dados dos jogos
    game_data_live = []
    game_data_future = []
    
    # Carrega jogos e prepara verificação
    board = scoreboard.ScoreBoard()
    games = board.games.get_dict()

    for game in games:
        home_name = game['homeTeam']['teamName']
        away_name = game['awayTeam']['teamName']
        game_time_local = get_game_time(home_name, away_name, games)
        game_status = game.get("gameStatus", "")
        game_id = game['gameId']

        game_data = {
            'game_info': f"{game_id}: {away_name} vs. {home_name} @ {game_time_local}",
            'away_team': away_name,
            'away_team_id': game['awayTeam']['teamId'],
            'home_team': home_name,
            'home_team_id': game['homeTeam']['teamId'],
            'game_time': game_time_local,
            'game_id': game_id,
        }

        if game_status == 2:  # live
            game_data.update({
                'home_team_score': game['homeTeam'].get('score'),
                'away_team_score': game['awayTeam'].get('score'),
                'period': game.get('period', '—'),
                'game_clock': format_game_time(game.get('gameClock', '—'))
            })
            game_data_live.append(game_data)

        elif game_status == 1:  # agendado
            game_data_future.append(game_data)
            
    # Buscar as melhores apostas (já cacheadas)
    jogos, mensagem = get_best_bets_data(request)

    return render(request, 'index.html', {
        'game_data_live': game_data_live,
        'game_data_future': game_data_future,
        'apostas': apostas_simples,
        'apostas_multipla': apostas_multipla,
        'filtro': filtro,
        'jogos': jogos,
        'mensagem': mensagem,
    })


def gerar_grafico_lucro_simplificado(user):
    """
    Gera um gráfico de linha mostrando o lucro/prejuízo acumulado do utilizador ao longo do tempo.
    
    Args:
        user: Utilizador autenticado do Django.
    
    Returns:
        str: HTML do gráfico Plotly.
    """
    apostas = Aposta.objects.filter(
        user=user,
        status__in=["ganha", "perdida", "cancelada"]
    ).exclude(
        status="ganha",
        apostamultipla__status="perdida"
    )

    lucro_por_dia = defaultdict(float)
    contagem_por_dia = defaultdict(int)
    jogadores_por_dia = defaultdict(list)

    for aposta in apostas:
        dia_str = aposta.data_jogo or aposta.data_aposta.strftime('%d/%m/%Y')

        try:
            dia_formatado = datetime.strptime(dia_str, '%d/%m/%Y').strftime('%d/%m/%Y')
        except ValueError:
            continue

        if aposta.status == "ganha":
            lucro = float(aposta.possiveis_ganhos) - float(aposta.valor_apostado)
        elif aposta.status == "perdida":
            lucro = -float(aposta.valor_apostado)
        else:
            lucro = 0  # canceladas

        lucro_por_dia[dia_formatado] += lucro
        contagem_por_dia[dia_formatado] += 1
        jogadores_por_dia[dia_formatado].append(aposta.jogador)

    dias_ordenados = sorted(
        lucro_por_dia.keys(),
        key=lambda x: datetime.strptime(x, '%d/%m/%Y')
    )

    valores = []
    hover_texts = []
    acumulado = 0

    for dia in dias_ordenados:
        acumulado += round(lucro_por_dia[dia], 2)
        valores.append(acumulado)
        jogadores_str = ", ".join(jogadores_por_dia[dia])
        hover_texts.append(
            f"<b>{dia}</b><br>Lucro: {acumulado:.2f}€<br>Apostas: {contagem_por_dia[dia]}<br>Jogadores: {jogadores_str}"
        )

    fig = go.Figure()

    cor_linha = "red" if valores and valores[-1] < 0 else "green"

    fig.add_trace(go.Scatter(
        x=dias_ordenados,
        y=valores,
        mode='lines+markers+text',
        text=[f"{v:.2f}€" for v in valores],
        textposition="top center",
        hovertext=hover_texts,
        hoverinfo="text",
        line=dict(color=cor_linha, width=4),
        marker=dict(size=7),
        name='Lucro'
    ))

    fig.update_layout(
        title="Lucro/Prejuízo",
        xaxis_title="Data",
        yaxis_title="Lucro (€)",
        template="simple_white",
        height=1000,
        shapes=[
            dict(
                type="line",
                xref="paper",
                yref="y",
                x0=0,
                x1=1,
                y0=0,
                y1=0,
                line=dict(
                    color="gray",
                    width=2,
                    dash="dot"
                ),
            )
        ]
    )

    return pio.to_html(fig, full_html=False)


@login_required
def estatisticas(request):
    """
    View que exibe estatísticas gerais das apostas do utilizador.
    Mostra totais, taxas de sucesso, lucro/prejuízo e um gráfico de desempenho.
    
    Args:
        request: HttpRequest do Django.
    
    Returns:
        HttpResponse: Página de estatísticas com dados e gráfico.
    """
    user = request.user
    apostas = Aposta.objects.filter(user=user)

    total = apostas.count()
    pendentes = apostas.filter(status='pendente').count()
    ganhas = apostas.filter(status='ganha').count()
    perdidas = apostas.filter(status='perdida').count()
    canceladas = apostas.filter(status='cancelada').count()
    sucesso = round((ganhas / total) * 100, 2) if total else 0

    # 🔍 Apostas ganhas válidas (excluindo se em múltiplas perdidas)
    apostas_validas_ganhas = Aposta.objects.filter(
        user=user,
        status='ganha'
    ).exclude(
        apostamultipla__status='perdida'
    )

    ganhos_total = apostas_validas_ganhas.aggregate(Sum('possiveis_ganhos'))['possiveis_ganhos__sum'] or 0

    # 💡 Valor apostado nas válidas (ganhas válidas + perdidas)
    apostas_validas_para_apostado = Aposta.objects.filter(
        Q(user=user),
        Q(status='perdida') | Q(
            Q(status='ganha') & ~Q(apostamultipla__status='perdida')
        )
    )

    apostado_total = apostas_validas_para_apostado.aggregate(Sum('valor_apostado'))['valor_apostado__sum'] or 0

    lucro = ganhos_total - apostado_total

    # DEBUG opcional
    print("🧾 DEBUG: Apostas ganhas que contam para o lucro:")
    for aposta in apostas_validas_ganhas:
        print(f" - {aposta.jogador} | {aposta.tipo_aposta} | Apostado: {aposta.valor_apostado}€ | Ganhos: {aposta.possiveis_ganhos}€")

    print(f"💰 Total apostado válido: {apostado_total}€")
    print(f"💸 Total ganhos válidos: {ganhos_total}€")
    print(f"📊 Lucro/Prejuízo final: {lucro}€")

    grafico_html = gerar_grafico_lucro_simplificado(user)

    return render(request, 'estatisticas.html', {
        'total_apostas': total,
        'apostas_pendentes': pendentes,
        'apostas_ganhas': ganhas,
        'apostas_perdidas': perdidas,
        'apostas_canceladas': canceladas,
        'taxa_sucesso': sucesso,
        'lucro_prejuizo': round(lucro, 2),
        'grafico_html': grafico_html,
    })



def get_best_bets_data(request):
    """
    Obtém dados para as melhores apostas sugeridas.
    
    Args:
        request: Objeto HttpRequest do Django.
    
    Returns:
        dict: Dados formatados para as melhores apostas:
            - jogos: Lista de jogos
            - apostas: Lista de apostas sugeridas
            - odds: Informações sobre odds
    """
    cache_key = "best_bets_data"
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data

    print("\n🔍 INICIANDO FUNÇÃO GET_BEST_BETS_DATA")
    
    # Cache global para scraping e logs
    scraping_cache = {}
    logs_cache = {}
    
    try:
        # 1. Obter jogos do dia
        print("\n📅 Buscando jogos do dia...")
        sb = scoreboard.ScoreBoard()
        games = sb.games.get_dict()
        print(f"✅ Encontrados {len(games)} jogos")

        jogos_do_dia = []
        for game in games:
            try:
                # Verifica se o jogo está agendado (game_status == 1)
                if game.get('gameStatus') != 1:
                    continue

                game_time_utc = parser.parse(game['gameTimeUTC']).replace(tzinfo=timezone.utc)
                game_time_local = game_time_utc.astimezone(tz=None)
                
                jogos_do_dia.append({
                    'home_team': {
                        'id': game['homeTeam']['teamId'],
                        'name': game['homeTeam']['teamName'],
                        'abbr': game['homeTeam']['teamTricode']
                    },
                    'away_team': {
                        'id': game['awayTeam']['teamId'],
                        'name': game['awayTeam']['teamName'],
                        'abbr': game['awayTeam']['teamTricode']
                    },
                    'game_time': game_time_local.strftime('%H:%M'),           
                    'full_date': game_time_local.strftime('%d/%m/%Y'),
                    'game_id': game['gameId']
                })
            except Exception as e:
                print(f"❌ Erro ao processar jogo: {e}")
                continue

        if not jogos_do_dia:
            return [], "Não há jogos agendados disponíveis para hoje."

        sugestoes_por_jogo = []
        
        # 2. Processar cada jogo
        for jogo in jogos_do_dia:
            try:
                sugestoes_jogo = {
                    'home_team': jogo['home_team']['name'],
                    'away_team': jogo['away_team']['name'],
                    'game_time': jogo['game_time'],
                    'full_date': jogo['full_date'], 
                    'game_id': jogo['game_id'],
                    'home_sugestoes': [],
                    'away_sugestoes': []
                }

                # 3. Processar cada time
                for team_type in ['home', 'away']:
                    team_id = jogo[f'{team_type}_team']['id']
                    try:
                        roster = commonteamroster.CommonTeamRoster(team_id=team_id).get_data_frames()[0]
                        
                        for _, player in roster.iterrows():
                            try:
                                player_name = player['PLAYER']
                                player_info = players.find_players_by_full_name(player_name)
                                
                                if not player_info:
                                    continue
                                    
                                player_id = player_info[0]['id']
                                
                                # Buscar props do jogador (usando cache)
                                if player_id not in scraping_cache:
                                    props_data = scrape_player_props(player_info[0]['first_name'], player_info[0]['last_name'])
                                    scraping_cache[player_id] = props_data
                                else:
                                    props_data = scraping_cache[player_id]
                                    
                                if not props_data:
                                    continue

                                # Buscar logs do jogador (usando cache)
                                if player_id not in logs_cache:
                                    logs = []
                                    for season_type in ["Playoffs", "PlayIn", "Regular Season"]:
                                        try:
                                            df = PlayerGameLog(
                                                player_id=player_id,
                                                season=get_current_season(),
                                                season_type_all_star=season_type
                                            ).get_data_frames()[0]
                                            logs.append(df)
                                        except Exception:
                                            continue
                                            
                                    logs = [df for df in logs if not df.empty]
                                    if not logs:
                                        continue
                                    player_log = pd.concat(logs, ignore_index=True)
                                    logs_cache[player_id] = player_log
                                else:
                                    player_log = logs_cache[player_id]
                                    
                                player_log = player_log.head(10)
                                
                                # 4. Processar estatísticas
                                stats_to_check = ['PTS', 'AST', 'REB', 'PTS+AST', 'PTS+REB', 'AST+REB', 'PTS+AST+REB', '3PT', 'BLK', 'STL']
                                sugestoes_jogador = []
                                
                                for stat in stats_to_check:
                                    if stat not in props_data:
                                        continue
                                        
                                    try:
                                        line = float(props_data[stat]['line'])
                                        over_odds = props_data[stat].get('over_odds')
                                        under_odds = props_data[stat].get('under_odds')
                                        
                                        # Calcular estatísticas
                                        if '+' in stat:
                                            components = stat.split('+')
                                            player_log = player_log.copy()
                                            player_log[stat] = player_log[components].sum(axis=1)
                                        else:
                                            stat_col = 'FG3M' if stat == '3PT' else stat
                                            player_log[stat] = player_log[stat_col]
                                            
                                        over_count = sum(player_log[stat] > line)
                                        under_count = sum(player_log[stat] < line)
                                        total = len(player_log)
                                        
                                        # Só mostrar se tiver pelo menos 5 jogos e taxa >= 8/10
                                        if total >= 5 and over_count >= 8:
                                            sugestoes_jogador.append({
                                                'player_id': player_id,
                                                'stat': stat,
                                                'line': line,
                                                'over': f"{over_count}/{total}",
                                                'under': f"{under_count}/{total}",
                                                'over_pct': round((over_count/total) * 100, 1),
                                                'under_pct': round((under_count/total) * 100, 1),
                                                'tendencia': 'OVER' if over_count > under_count else 'UNDER',
                                                'over_odds': over_odds,
                                                'under_odds': under_odds,
                                                'taxa_acerto': over_count/total
                                            })
                                        elif total >= 5 and under_count >= 8:
                                            sugestoes_jogador.append({
                                                'player_id': player_id,
                                                'stat': stat,
                                                'line': line,
                                                'over': f"{over_count}/{total}",
                                                'under': f"{under_count}/{total}",
                                                'over_pct': round((over_count/total) * 100, 1),
                                                'under_pct': round((under_count/total) * 100, 1),
                                                'tendencia': 'UNDER',
                                                'over_odds': over_odds,
                                                'under_odds': under_odds,
                                                'taxa_acerto': under_count/total
                                            })
                                    except Exception:
                                        continue
                                
                                if sugestoes_jogador:
                                    sugestoes_jogador.sort(key=lambda x: x['taxa_acerto'], reverse=True)
                                    sugestoes_jogo[f'{team_type}_sugestoes'].append({
                                        'nome': player_name,
                                        'sugestoes': sugestoes_jogador
                                    })
                                    
                            except Exception:
                                continue
                                
                    except Exception:
                        continue
                        
                # Ordena as sugestões de cada time por taxa de acerto
                for team_type in ['home', 'away']:
                    sugestoes_jogo[f'{team_type}_sugestoes'].sort(
                        key=lambda x: max(s['taxa_acerto'] for s in x['sugestoes']),
                        reverse=True
                    )
                        
                sugestoes_por_jogo.append(sugestoes_jogo)
                
            except Exception:
                continue

        # Filtrar sugestões para mostrar só jogos ainda não iniciados
        board = scoreboard.ScoreBoard()
        games = board.games.get_dict()
        jogos_ids_ativos = {g['gameId'] for g in games if g.get('gameStatus') == 1}
        sugestoes_por_jogo = [j for j in sugestoes_por_jogo if str(j['game_id']) in jogos_ids_ativos]

        resultado = (sugestoes_por_jogo, None)
        cache.set(cache_key, resultado, 60 * 120)  # 2hrs
        return resultado

    except Exception as e:
        print(f"❌ Erro geral em get_best_bets_data: {e}")
        return [], "Ocorreu um erro ao carregar as sugestões. Por favor, tente novamente mais tarde."


@login_required
def best_bets(request):
    jogos, mensagem = get_best_bets_data(request)

    board = scoreboard.ScoreBoard()
    games = board.games.get_dict()
    jogos_ids_ativos = {g['gameId'] for g in games if g.get('gameStatus') == 1}

    # Filtra sugestões para mostrar só jogos ainda não iniciados
    jogos_filtrados = [j for j in jogos if str(j['game_id']) in jogos_ids_ativos]

    return render(request, "best_bets.html", {
        "jogos": jogos_filtrados,
        "mensagem": mensagem
    })


# Dicionário para guardar os rosters já carregados e evitar múltiplas chamadas
_roster_cache = {}

def try_load_team_roster(team_id, season=get_current_season(), retries=3, delay=2):
    """
    Tenta carregar o roster de uma equipa com sistema de retry.
    
    Args:
        team_id: ID da equipa.
        season: Temporada (padrão: temporada atual).
        retries: Número de tentativas (padrão: 3).
        delay: Tempo de espera entre tentativas em segundos (padrão: 2).
    
    Returns:
        dict: Dados do roster da equipa ou None se falhar.
    """
    # Cria uma chave para o cache baseada no ID do time e na temporada
    cache_key = f"{team_id}_{season}"
    
    # Se o roster já está no cache, retorna diretamente
    if cache_key in _roster_cache:
        return _roster_cache[cache_key]
    
    # Tenta carregar o roster, com múltiplas tentativas se necessário
    for i in range(retries):
        try:
            # Tenta buscar o roster usando a API
            print(f"🔄 Carregando roster do time {team_id} (tentativa {i+1})")
            df = commonteamroster.CommonTeamRoster(team_id=team_id, season=season).get_data_frames()[0]
            # Guarda no cache para futuras utilizações
            _roster_cache[cache_key] = df
            return df
        except Exception as e:
            # Em caso de erro, espera um pouco antes de tentar novamente
            print(f"❌ Erro ao carregar roster (tentativa {i+1}): {e}")
            sleep(delay)
    
    # Se todas as tentativas falharem, retorna None
    return None

def normalize_name(name):
    """
    Normaliza o nome de um jogador para pesquisa.
    
    Args:
        name: Nome do jogador.
    
    Returns:
        str: Nome normalizado (sem acentos, em minúsculas e sem espaços extras).
    """
    # Normaliza o nome: remove espaços extras, acentos e converte para minúsculas
    return unidecode(re.sub(r"\s+", " ", name.strip().lower()))


def find_active_player_id_by_partial_name(abbreviated_name, team_id=None, season=get_current_season()):
    """
    Encontra o ID de um jogador ativo pelo nome parcial.
    
    Args:
        abbreviated_name: Nome parcial do jogador.
        team_id: ID da equipa (opcional).
        season: Temporada (padrão: temporada atual).
    
    Returns:
        int: ID do jogador se encontrado, None caso contrário.
    """
    try:
        # Obtém a lista de todos os jogadores ativos
        all_players = players.get_active_players()

        # Limpa o nome recebido, removendo marcações de status
        cleaned = abbreviated_name.replace("GTD", "").replace("OUT", "").replace("OFS", "").strip()
        parts = cleaned.split()
        
        # Se não houver pelo menos nome e sobrenome, retorna None
        if len(parts) < 2:
            return None

        # Se a primeira palavra for uma posição (ex: PG, SG), ignora-a
        name_parts = parts[1:] if parts[0] in ["C", "F", "G", "PG", "SG", "SF", "PF", "C."] else parts
        name_only = " ".join(name_parts)
        
        # Normaliza o nome para facilitar a comparação
        name_normalized = normalize_name(name_only)
        is_abbreviated = "." in name_parts[0]

        print(f"\n🔍 [BUSCA] Nome recebido: '{abbreviated_name}' → Normalizado: '{name_normalized}' | Team ID: {team_id}")

        roster_names = set()
        roster_lookup = {}

        # Se o ID do time for fornecido, tenta carregar o roster correspondente
        if team_id:
            roster_df = try_load_team_roster(team_id, season)
            if roster_df is None:
                print(f"❌ Não foi possível carregar o roster da equipe {team_id}")
                return None

            # Adiciona uma coluna com o nome normalizado no roster
            roster_df["NORMALIZED_NAME"] = roster_df["PLAYER"].apply(normalize_name)
            roster_names = set(roster_df["NORMALIZED_NAME"])
            roster_lookup = dict(zip(roster_df["NORMALIZED_NAME"], roster_df["PLAYER_ID"]))

        # 1. Tenta encontrar um match exato no roster
        if name_normalized in roster_lookup:
            print(f"✅ Match exato no roster: {name_normalized}")
            return roster_lookup[name_normalized]

        # 2️. Tenta encontrar o nome parcialmente no roster
        for roster_name, player_id in roster_lookup.items():
            if name_normalized in roster_name:
                print(f"✅ Match parcial no roster: {roster_name}")
                return player_id

        # 3️. Tenta combinar a inicial do primeiro nome com o sobrenome
        if len(name_parts) >= 2:
            first_initial = name_parts[0][0].upper()
            last_name_normalized = normalize_name(name_parts[1])
            for full_name, player_id in roster_lookup.items():
                full_parts = full_name.split()
                if len(full_parts) >= 2:
                    if (normalize_name(full_parts[-1]) == last_name_normalized and 
                        full_parts[0][0].upper() == first_initial):
                        print(f"✅ Match por inicial e sobrenome no roster: {full_name}")
                        return player_id

        # Se não encontrar nenhum jogador correspondente
        print("❌ Nenhum match encontrado no roster da equipe.")
        return None

    except Exception as e:
        # Se ocorrer qualquer erro, imprime-o e retorna None
        print(f"❌ Erro ao buscar ID de '{abbreviated_name}': {e}")
        return None


@login_required
def my_bets(request):
    """
    View para exibição das apostas do utilizador.
    
    Args:
        request: HttpRequest do Django.
    
    Returns:
        HttpResponse: Página com lista de apostas do utilizador.
    """
    filtro = request.GET.get('filtro', 'todas')

    apostas = Aposta.objects.filter(user=request.user)
    apostas_multipla = ApostaMultipla.objects.filter(user=request.user)

    aposta_ids_multipla = apostas_multipla.values_list('apostas__id', flat=True)
    apostas_simples = apostas.exclude(id__in=aposta_ids_multipla)

    if filtro == 'ganhas':
        apostas_simples = apostas_simples.filter(status='ganha')
        apostas_multipla = apostas_multipla.filter(status='ganha')
    elif filtro == 'perdidas':
        apostas_simples = apostas_simples.filter(status='perdida')
        apostas_multipla = apostas_multipla.filter(status='perdida')
    elif filtro == 'pendentes':
        apostas_simples = apostas_simples.filter(status='pendente')
        apostas_multipla = apostas_multipla.filter(status='pendente')

    return render(request, 'my_bets.html', {
        'apostas': apostas_simples,
        'apostas_multipla': apostas_multipla,
        'filtro': filtro
    })


# Logout 
def logout_view(request):
    logout(request) 
    messages.success(request, '✅ Você foi desconectado com sucesso!')
    return redirect('login') 

@login_required
def criar_aposta(request):
    # Log para indicar que a função foi chamada
    print("🔄 criar_aposta foi chamada")

    if request.method == "POST":
        try:
            # Obtém os dados das apostas enviados no POST
            apostas_json = request.POST.get('apostas_data', '[]')
            valor_apostado = Decimal(request.POST.get('valor_apostado', '0'))
            apostas_data = json.loads(apostas_json)

            print("📥 JSON recebido:")
            print(json.dumps(apostas_data, indent=2))

            # Verifica se os dados das apostas são válidos
            if not apostas_data or valor_apostado <= 0:
                messages.error(request, "⚠️ Dados de aposta inválidos!")
                return redirect(request.META.get("HTTP_REFERER", "home"))

            # ⚠️ Verifica se o utilizador tem saldo suficiente
            if request.user.saldo < valor_apostado:
                messages.error(request, "❌ Saldo insuficiente para essa aposta!")
                return redirect(request.META.get("HTTP_REFERER", "home"))

            # Desconta o valor apostado do saldo do utilizador
            request.user.saldo -= valor_apostado
            request.user.save()
            print(f"💰 Novo saldo: {request.user.saldo}")

            apostas_salvas = []
            aposta_multipla = None

            # Verifica se é uma aposta múltipla
            if len(apostas_data) > 1:
                # Cria uma ApostaMultipla
                aposta_multipla = ApostaMultipla(
                    user=request.user,
                    valor_apostado=valor_apostado
                )
                aposta_multipla.save()

                # Cria apostas individuais e associa à aposta múltipla
                for aposta_data in apostas_data:
                    print("🎯 Dados recebidos no servidor (múltipla):", aposta_data)

                    jogador = aposta_data.get('playerName')
                    tipo_aposta = aposta_data.get('betType')
                    odd = Decimal(str(aposta_data.get('odd', 1)))
                    jogo_id = aposta_data.get('gameId') or ''
                    data_jogo = aposta_data.get('gameDate') or ''
                    home_team = aposta_data.get('homeTeam') or ''
                    away_team = aposta_data.get('awayTeam') or ''
                    possiveis_ganhos = valor_apostado * odd

                    aposta = Aposta.objects.create(
                        user=request.user,
                        jogador=jogador,
                        tipo_aposta=tipo_aposta,
                        odds=float(odd),
                        valor_apostado=valor_apostado,
                        possiveis_ganhos=possiveis_ganhos,
                        jogo_id=jogo_id,
                        data_jogo=data_jogo,
                        home_team=home_team,
                        away_team=away_team
                    )

                    apostas_salvas.append(aposta)
                    aposta_multipla.apostas.add(aposta)

                # Calcula a odd total da aposta múltipla
                aposta_multipla.calcular_odd_total()
                
                # Apresenta mensagem de sucesso para aposta múltipla
                messages.success(
                    request,
                    f"✅ Você apostou com sucesso! Possíveis Ganhos: {aposta_multipla.possiveis_ganhos:.2f} €"
                )

            else:
                # Trata-se de uma aposta simples
                aposta_data = apostas_data[0]
                print("🎯 Dados recebidos no servidor (simples):", aposta_data)

                jogador = aposta_data.get('playerName')
                tipo_aposta = aposta_data.get('betType')
                odd = Decimal(str(aposta_data.get('odd', 1)))
                jogo_id = aposta_data.get('gameId') or ''
                data_jogo = aposta_data.get('gameDate') or ''
                home_team = aposta_data.get('homeTeam') or ''
                away_team = aposta_data.get('awayTeam') or ''
                possiveis_ganhos = valor_apostado * odd

                # Cria a aposta simples
                aposta = Aposta.objects.create(
                    user=request.user,
                    jogador=jogador,
                    tipo_aposta=tipo_aposta,
                    odds=float(odd),
                    valor_apostado=valor_apostado,
                    possiveis_ganhos=possiveis_ganhos,
                    jogo_id=jogo_id,
                    data_jogo=data_jogo,
                    home_team=home_team,
                    away_team=away_team
                )

                apostas_salvas.append(aposta)

                # Apresenta mensagem de sucesso para aposta simples
                messages.success(
                    request,
                    f"✅ Você apostou com sucesso! Possíveis Ganhos: {possiveis_ganhos:.2f} €"
                )

        except Exception as e:
            # Em caso de erro durante o processamento da aposta
            print("❌ Erro ao processar aposta:", e)
            messages.error(request, "❌ Ocorreu um erro ao processar sua aposta.")

        # Redireciona de volta para a página anterior
        return redirect(request.META.get("HTTP_REFERER", "home"))

    # Se o método não for POST, renderiza a página de criação de apostas
    return render(request, 'criar_aposta.html')




# Função para pesquisa dos jogadores
def search_ajax(request):
    """
    View para pesquisa de jogadores via AJAX.
    
    Args:
        request: HttpRequest do Django.
    
    Returns:
        JsonResponse: Lista de jogadores filtrados.
    """
    query = request.GET.get('query', '')

    # Remover acentos da consulta de pesquisa
    query = unidecode(query.lower())

    # Obtém todos os jogadores ativos
    active_players = players.get_active_players()

    # Filtra jogadores
    filtered_players = [
        player for player in active_players if query in unidecode(player['full_name'].lower())
    ]

    return JsonResponse({'jogadores': filtered_players})


# Função para obter dados do PlayerIndex e calcular a idade
def get_player_info(player_id):
    """
    Obtém informações básicas de um jogador, incluindo idade, altura, peso, equipa e data de nascimento.
    
    Args:
        player_id: ID do jogador.
    
    Returns:
        dict: Informações do jogador.
    """
    player_data = commonplayerinfo.CommonPlayerInfo(player_id=player_id)

    player_df = player_data.common_player_info.get_data_frame()

    # Seleciona as colunas relevantes (nome, altura, peso, time, e data de nascimento)
    player_filtered = player_df[['FIRST_NAME', 'LAST_NAME', 'HEIGHT', 'WEIGHT', 'TEAM_NAME', 'BIRTHDATE', 'TEAM_ID']]

    # Função para calcular a idade do jogador a partir da data de nascimento
    def calculate_age(birth_date):
        birth_date = datetime.strptime(birth_date.split('T')[0], "%Y-%m-%d") 
        age = (datetime.now() - birth_date).days // 365  
        return age
    
    # Função para converter altura de pés e polegadas para metros
    def converter_height_to_meters(height):
        # Divide a altura em pés e polegadas
        feet, inches = map(int, height.split('-'))

        # Converte para metros
        meters = (feet * 0.3048) + (inches * 0.0254)
        
        return round(meters, 2)

    player_filtered['AGE'] = player_filtered['BIRTHDATE'].apply(calculate_age)

    player_filtered['HEIGHT_METERS'] = player_filtered['HEIGHT'].apply(converter_height_to_meters)

    return player_filtered[['FIRST_NAME', 'LAST_NAME', 'HEIGHT_METERS', 'AGE', 'TEAM_NAME', 'TEAM_ID']].iloc[0]




# View para listar os jogos ao vivo
def live_games(request):
    """
    View para listar os jogos ao vivo.
    
    Args:
        request: HttpRequest do Django.
    
    Returns:
        HttpResponse: Página com jogos ao vivo.
    """
    # Formato de string para exibir informações do jogo
    f = "{gameId}: {awayTeam} vs. {homeTeam} @ {gameTimeUTC}"

    # Obtém a lista de jogos do ScoreBoard
    board = scoreboard.ScoreBoard()
    games = board.games.get_dict()

    game_data = []
    today = datetime.now().date() 
    current_time = datetime.now().time()  

    # Percorre todos os jogos
    for game in games:
        gameTimeUTC = parser.parse(game["gameTimeUTC"])

        # Filtra para mostrar apenas jogos de hoje ou que ainda vão começar
        if gameTimeUTC.date() > today or (gameTimeUTC.date() == today and gameTimeUTC.time() >= current_time):
            # Prepara os dados do jogo
            game_info = f.format(
                gameId=game['gameId'], 
                awayTeam=game['awayTeam']['teamName'], 
                homeTeam=game['homeTeam']['teamName'], 
                gameTimeUTC=gameTimeUTC  
            )
            
            # Adiciona o jogo à lista
            game_data.append({
                'game_info': game_info,
                'away_team': game['awayTeam']['teamName'],
                'away_team_id': game['awayTeam']['teamId'], 
                'home_team': game['homeTeam']['teamName'],
                'home_team_id': game['homeTeam']['teamId'], 
                'game_time': gameTimeUTC.strftime('%H:%M'),
                'game_id': game['gameId'],
            })

    # Renderiza a página com os jogos ao vivo
    return render(request, 'live_games.html', {
        'game_data': game_data,
    })


# Função para obter as lineups (quintetos) atuais de um jogo ao vivo
def get_live_lineups(game_id):
    """
    Obtém as lineups atuais de um jogo ao vivo.
    
    Args:
        game_id: ID do jogo.
    
    Returns:
        dict: Informações sobre as lineups do jogo.
    """
    # Obtém o boxscore do jogo
    box = boxscore.BoxScore(game_id=game_id)
    game_data = box.game.get_dict()
    
    # Obtém dados das equipas (casa e fora)
    home_team = box.home_team.get_dict()
    away_team = box.away_team.get_dict()

    # Cria um dicionário com informações dos jogadores
    player_info = {
        p['personId']: {
            'name': p['name'],
            'team': 'home' if p in home_team['players'] else 'away'
        }
        for p in home_team['players'] + away_team['players']
    }

    home_lineup = []
    away_lineup = []

    # Identifica os jogadores que começaram como titulares
    for p in home_team['players']:
        if p['starter'] == '1':
            home_lineup.append(p['personId'])

    for p in away_team['players']:
        if p['starter'] == '1':
            away_lineup.append(p['personId'])

    # Obtém as jogadas para verificar substituições
    pbp = playbyplay.PlayByPlay(game_id=game_id)
    plays = pbp.get_dict().get('game', {}).get('actions', [])

    # Atualiza as lineups de acordo com as substituições
    for play in plays:
        if play['actionType'] == 'substitution':
            action_type = play['subType']
            player_id = play['personId']
            team = 'Home' if play['teamTricode'] == home_team['teamTricode'] else 'Away'

            if action_type == 'out':
                if player_id in home_lineup:
                    home_lineup.remove(player_id)
                if player_id in away_lineup:
                    away_lineup.remove(player_id)

            if action_type == 'in':
                if team == 'Home':
                    home_lineup.append(player_id)
                else:
                    away_lineup.append(player_id)

    # Atualiza o status de "em campo" para cada jogador
    for player in home_team['players']:
        player['in_court'] = player['personId'] in home_lineup

    for player in away_team['players']:
        player['in_court'] = player['personId'] in away_lineup

    # Retorna as lineups atuais e informações básicas do jogo
    return {
        'home_team': home_team['teamName'],
        'away_team': away_team['teamName'],
        'home_lineup': home_lineup,
        'away_lineup': away_lineup,
        'game_clock': game_data.get('gameClock', 'Desconhecido'),
        'period': game_data.get('period', 'Desconhecido')
    }

# View para exibir estatísticas de um jogo
@login_required
def game_stats(request, game_id):
    """
    View para exibição de estatísticas de um jogo específico.
    
    Args:
        request: HttpRequest do Django.
        game_id: ID do jogo.
    
    Returns:
        HttpResponse: Página com estatísticas do jogo.
    """
    try:
        # Tenta carregar o boxscore do jogo
        box = boxscore.BoxScore(game_id)

        # Verifica se o jogo tem dados disponíveis
        _ = box.game.get_dict()

    except Exception as e:
        # Se não conseguir carregar os dados, exibe mensagem de erro e redireciona
        print(f"⚠️ Erro ao carregar boxscore do jogo {game_id}: {e}")
        messages.error(request, "❌ As estatísticas deste jogo ainda não estão disponíveis.")
        return redirect(request.META.get("HTTP_REFERER", "home"))

    # Organiza as estatísticas dos jogadores da equipe visitante
    away_team_player_stats = box.away_team_player_stats.get_dict()
    away_team_organizado = organizar_estatisticas(away_team_player_stats)

    # Organiza as estatísticas dos jogadores da equipe da casa
    home_team_player_stats = box.home_team_player_stats.get_dict()
    home_team_organizado = organizar_estatisticas(home_team_player_stats)

    try:
        # Obtém as lineups atuais do jogo
        lineups = get_live_lineups(game_id)
    except Exception as e:
        # Se der erro ao carregar lineups, exibe mensagem de erro e redireciona
        print(f"⚠️ Erro ao carregar lineups do jogo {game_id}: {e}")
        messages.error(request, "❌ As estatísticas de jogadores ainda não estão disponíveis.")
        return redirect(request.META.get("HTTP_REFERER", "home"))
    
    # Debug das lineups carregadas
    print(f"Lineups (Home): {lineups['home_lineup']}")
    print(f"Lineups (Away): {lineups['away_lineup']}")

    # Atualiza o status 'in_court' dos jogadores da equipa da casa
    for jogador in home_team_organizado:
        jogador['in_court'] = jogador['personId'] in lineups['home_lineup']

    # Atualiza o status 'in_court' dos jogadores da equipa visitante
    for jogador in away_team_organizado:
        jogador['in_court'] = jogador['personId'] in lineups['away_lineup']

    # Informações gerais das equipas
    away_team_id = box.away_team.get_dict()["teamId"]
    away_team_name = box.away_team.get_dict()["teamName"]
    away_team_score = box.away_team.get_dict()["score"]

    home_team_id = box.home_team.get_dict()["teamId"]
    home_team_name = box.home_team.get_dict()["teamName"]
    home_team_score = box.home_team.get_dict()["score"]

    # Período e tempo do jogo
    period = box.game.get_dict()["period"]
    game_time = box.game.get_dict()["gameClock"]

    # Função interna para formatar o tempo do jogo
    def format_game_time(time_str):
        if time_str:
            time_str = time_str[2:-1]
            time_parts = time_str.split("M")
            if len(time_parts) == 2:
                minutes = time_parts[0]
                seconds = time_parts[1].split('.')[0]
                return f"{minutes} min {seconds} sec"
        return "Tempo não disponível"

    # Formata o tempo do jogo
    formatted_game_time = format_game_time(game_time)

    # Renderiza a página de estatísticas do jogo
    return render(request, 'game_stats.html', {
        'away_team_organizado': away_team_organizado,
        'home_team_organizado': home_team_organizado,
        'away_team_id': away_team_id,
        'away_team_name': away_team_name,
        'home_team_id': home_team_id,
        'home_team_name': home_team_name,
        'away_team_score': away_team_score,
        'home_team_score': home_team_score,
        'period': period,
        'game_time': formatted_game_time,
    })


# Função para organizar as estatísticas dos jogadores
def organizar_estatisticas(game_stats):
    """
    Organiza as estatísticas de um jogo em formato estruturado.
    
    Args:
        game_stats: Dicionário com estatísticas brutas do jogo.
    
    Returns:
        dict: Estatísticas organizadas por equipa e jogador.
    """
    return [
        {
            'Nome': jogador.get('name', 'N/A'),  # Nome do jogador
            'status': jogador.get('status', 'N/A'),  # Status do jogador (ativo, inativo)
            'personId': jogador.get('personId', 'N/A'),  # ID do jogador
            'Pontos': jogador.get('statistics', {}).get('points', 'N/A'),  # Pontos marcados
            'Assistências': jogador.get('statistics', {}).get('assists','N/A'),  # Assistências
            'Rebounds': jogador.get('statistics', {}).get('reboundsTotal', 'N/A'),  # Ressaltos totais
            '3P': jogador.get('statistics', {}).get('threePointersMade', 'N/A'),  # Triplos convertidos
            'Turnovers': jogador.get('statistics', {}).get('turnovers', 'N/A'),  # Turnovers
            'Faltas': jogador.get('statistics', {}).get('foulsPersonal', 'N/A'),  # Faltas pessoais
        }
        for jogador in game_stats
    ]

# Função para extrair jogadores de elementos HTML com status específico (por exemplo, ativos/inativos)
def extract_player_data(li_elements, status_classes, team_id):
    """
    Extrai dados dos jogadores a partir dos elementos HTML.
    
    Args:
        li_elements: Lista de elementos HTML contendo dados dos jogadores.
        status_classes: Classes CSS que indicam o status dos jogadores.
        team_id: ID da equipa.
    
    Returns:
        list: Lista de dicionários com dados dos jogadores:
            - id: ID do jogador
            - name: Nome do jogador
            - status: Status do jogador
            - team_id: ID da equipa
    """
    players = []
    for li in li_elements:
        class_name = li.get('class', [])
        
        # Verifica se o jogador pertence às classes de status desejadas
        if any(status_class in class_name for status_class in status_classes):
            a_tag = li.find("a")
            if a_tag and a_tag.has_attr("title"):
                name_only = a_tag["title"].strip()  # Obtém o nome do jogador pelo atributo title
            else:
                # Se não houver título, tenta extrair do texto
                name_only = " ".join(li.stripped_strings).strip()
            
            # Filtra entradas não relevantes
            if name_only and "On/Off Court Stats" not in name_only and "Projected Minutes" not in name_only:
                # Busca o ID do jogador usando o nome
                player_id = find_active_player_id_by_partial_name(name_only, team_id=team_id)
                
                if player_id:  # Se encontrar o jogador, adiciona à lista
                    players.append({"name": name_only, "id": player_id, "team_id": team_id})

    # Log do número de jogadores encontrados
    print(f"Extraindo jogadores com status {status_classes}: {len(players)} encontrados.")
    return players



# Função para obter o horário do jogo
def get_game_time(home_team_name, away_team_name, live_games):
    """
    Obtém o horário de um jogo específico.
    
    Args:
        home_team_name: Nome da equipa da casa.
        away_team_name: Nome da equipa visitante.
        live_games: Lista de jogos ao vivo.
    
    Returns:
        str: Horário do jogo.
    """
    for g in live_games:
        ht = g['homeTeam']['teamName'].lower()
        at = g['awayTeam']['teamName'].lower()

        if (ht in home_team_name.lower() and at in away_team_name.lower()) or \
           (ht in away_team_name.lower() and at in home_team_name.lower()):
            time_local = parser.parse(g['gameTimeUTC']).replace(tzinfo=timezone.utc).astimezone(tz=None)
            return time_local.strftime("%H:%M")
    return "–"

# Função para verificar se o jogador já existe na lista (evita duplicatas)
def check_duplicate(players, player_id):
    """
    Verifica se o jogador já existe na lista.
    
    Args:
        players: Lista de jogadores.
        player_id: ID do jogador.
    
    Returns:
        bool: True se o jogador já existe, False caso contrário.
    """
    return any(player['id'] == player_id for player in players)


# View para obter informações dos próximos jogos e lineups esperados
@login_required
@cache_page(60 * 15)
def next_games(request):
    """
    View para exibição dos próximos jogos.
    
    Args:
        request: HttpRequest do Django.
    
    Returns:
        HttpResponse: Página com lista de próximos jogos.
    """
    url = "https://www.rotowire.com/basketball/nba-lineups.php"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    # Faz a requisição ao site que contém as lineups
    response = requests.get(url, headers=headers)

    # Inicializa listas para armazenar informações dos jogos
    games_data = []
    home_lineups = []
    away_lineups = []
    home_gtd_players = []
    away_gtd_players = []
    home_out_players = []
    away_out_players = []

    # Obtém dados reais dos jogos através da API
    scoreboard_data = scoreboard.ScoreBoard()
    live_games = scoreboard_data.games.get_dict()

    # Função interna para cruzar nomes de equipas e obter o horário real do jogo
    def get_game_time(home_team_name, away_team_name):
        for g in live_games:
            ht = g['homeTeam']['teamName'].lower()
            at = g['awayTeam']['teamName'].lower()

            if (ht in home_team_name.lower() and at in away_team_name.lower()) or \
               (ht in away_team_name.lower() and at in home_team_name.lower()):
                time_local = parser.parse(g['gameTimeUTC']).replace(tzinfo=timezone.utc).astimezone(tz=None)
                return time_local.strftime("%H:%M")
        return "–"

    if response.status_code == 200:
        # Faz o parse do HTML usando BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        games = soup.find_all("div", class_="lineup is-nba")

        # Percorre todos os jogos encontrados
        for game in games:
            try:
                # Extrai as abreviações das equipas
                teams_abbr = game.find_all("div", class_="lineup__abbr")
                if len(teams_abbr) < 2:
                    continue

                team_home_abbr = teams_abbr[1].text.strip()
                team_away_abbr = teams_abbr[0].text.strip()

                # Encontra as equipas pelo código de abreviação
                team_home = teams.find_team_by_abbreviation(team_home_abbr)
                team_away = teams.find_team_by_abbreviation(team_away_abbr)

                team_home_id = team_home['id'] if team_home else None
                team_away_id = team_away['id'] if team_away else None

                # Monta as URLs dos logotipos
                team_home_logo = f"https://cdn.nba.com/logos/nba/{team_home_id}/global/L/logo.svg" if team_home_id else ""
                team_away_logo = f"https://cdn.nba.com/logos/nba/{team_away_id}/global/L/logo.svg" if team_away_id else ""

                expected_lineups_home = game.find_all("ul", class_="lineup__list is-home")
                expected_lineups_away = game.find_all("ul", class_="lineup__list is-visit")

                # Define o nome completo das equipas
                home_team_name = team_home['full_name'] if team_home else team_home_abbr
                away_team_name = team_away['full_name'] if team_away else team_away_abbr

                # Obtém o horário real do jogo
                game_time = get_game_time(home_team_name, away_team_name)

                # Cria o dicionário com informações do jogo
                game_info = {
                    "home_team": {
                        "name": home_team_name,
                        "logo": team_home_logo,
                        "lineup": [],
                        "gtd_players": [],
                        "out_players": [],
                    },
                    "away_team": {
                        "name": away_team_name,
                        "logo": team_away_logo,
                        "lineup": [],
                        "gtd_players": [],
                        "out_players": [],
                    },
                    "game_time": game_time
                }

                # ================= HOME TEAM ===================
                if expected_lineups_home:
                    home_li = expected_lineups_home[0].find_all("li")
                    
                    # Extrai jogadores confirmados
                    lineup_home = extract_player_data(home_li, 
                                                      ["is-pct-play-100", "is-pct-play-75", "is-pct-play-50"],
                                                      team_home_id)

                    # Extrai jogadores GTD (Game-Time Decision)
                    gtd_home = extract_player_data(home_li, 
                                                   ["is-pct-play-50", "is-pct-play-75", "is-pct-play-25"], 
                                                   team_home_id)

                    # Extrai jogadores fora
                    out_home = extract_player_data(home_li, 
                                                   ["is-pct-play-0", "is-ofs"], 
                                                   team_home_id)

                    # Guarda apenas os 5 primeiros titulares
                    game_info["home_team"]["lineup"] = lineup_home[:5]

                    # Remove duplicados dos GTD
                    gtd_home_unique = []
                    for player in gtd_home:
                        if not check_duplicate(gtd_home_unique, player['id']):
                            gtd_home_unique.append(player)

                    game_info["home_team"]["gtd_players"] = gtd_home_unique
                    game_info["home_team"]["out_players"] = out_home

                    # Atualiza as listas globais
                    home_lineups.append({"team": game_info["home_team"]["name"], "players": lineup_home[:5]})
                    home_gtd_players.append({"team": game_info["home_team"]["name"], "players": gtd_home_unique})
                    home_out_players.append({"team": game_info["home_team"]["name"], "players": out_home})

                # ================= AWAY TEAM ===================
                if expected_lineups_away:
                    away_li = expected_lineups_away[0].find_all("li")
                    
                    lineup_away = extract_player_data(away_li, 
                                                      ["is-pct-play-100", "is-pct-play-75", "is-pct-play-50"],
                                                      team_away_id)

                    gtd_away = extract_player_data(away_li, 
                                                   ["is-pct-play-50", "is-pct-play-75", "is-pct-play-25"], 
                                                   team_away_id)

                    out_away = extract_player_data(away_li, 
                                                   ["is-pct-play-0"], 
                                                   team_away_id)

                    game_info["away_team"]["lineup"] = lineup_away[:5]

                    # Remove duplicados dos GTD
                    gtd_away_unique = []
                    for player in gtd_away:
                        if not check_duplicate(gtd_away_unique, player['id']):
                            gtd_away_unique.append(player)

                    game_info["away_team"]["gtd_players"] = gtd_away_unique
                    game_info["away_team"]["out_players"] = out_away

                    # Atualiza as listas globais
                    away_lineups.append({"team": game_info["away_team"]["name"], "players": lineup_away[:5]})
                    away_gtd_players.append({"team": game_info["away_team"]["name"], "players": gtd_away_unique})
                    away_out_players.append({"team": game_info["away_team"]["name"], "players": out_away})

                games_data.append(game_info)

            except Exception as e:
                # Captura erros na extração dos dados
                print("Erro ao extrair os dados:", e)

    else:
        # Se o site não estiver disponível
        print("Erro ao acessar o site. Código de status:", response.status_code)

    # Prepara o contexto para o template
    context = {
        "games_data": games_data,
        "home_lineups": home_lineups,
        "away_lineups": away_lineups,
        "home_gtd_players": home_gtd_players,
        "away_gtd_players": away_gtd_players,
        "home_out_players": home_out_players,
        "away_out_players": away_out_players,
    }

    # Renderiza a página com os jogos e lineups
    return render(request, 'next_games.html', context)


def generate_stat_graph(player_info, stat_name, stat_label, season=get_current_season(), threshold=None, odd=None):
    """
    Gera um gráfico de estatísticas para um jogador.
    
    Args:
        player_info: Informações do jogador.
        stat_name: Nome da estatística.
        stat_label: Rótulo da estatística.
        season: Temporada atual.
        threshold: Limite para a estatística.
        odd: Odds da aposta.
    
    Returns:
        tuple: HTML do gráfico, média, limite e odds.
    """
    print(f"📊 Gerando gráfico para {player_info['FIRST_NAME']} {player_info['LAST_NAME']} - Stat: {stat_name}")
    
    column_aliases = {'3PT': 'FG3M'}
    true_stat_name = column_aliases.get(stat_name, stat_name)
    stat_name = stat_name.upper()

    player_id = player_info['id'] if 'id' in player_info else player_info['PLAYER_ID']
    logs = []

    for phase in ["Playoffs", "PlayIn", "Regular Season"]:
        try:
            df = PlayerGameLog(player_id=player_id, season=season, season_type_all_star=phase).get_data_frames()[0]
            df["SEASON_TYPE"] = phase
            logs.append(df)
        except Exception as e:
            print(f"⚠️ Erro ao carregar {phase}: {e}")

    player_log = pd.concat(logs, ignore_index=True)
    player_log.columns = player_log.columns.str.upper()

    # ✅ Corrige parsing de datas com abreviações (ex: "Apr 29, 2025")
    player_log['GAME_DATE'] = pd.to_datetime(player_log['GAME_DATE'], format="%b %d, %Y", errors="coerce")
    player_log = player_log[player_log['GAME_DATE'].notna()]

    player_log = player_log.sort_values(by='GAME_DATE', ascending=False)

    if '+' in stat_name:
        parts = stat_name.split('+')
        cols = [column_aliases.get(p, p) for p in parts]
        for col in cols:
            if col not in player_log.columns:
                raise ValueError(f"Coluna {col} não encontrada.")
        player_log[stat_name] = player_log[cols].sum(axis=1)
    else:
        if true_stat_name not in player_log.columns:
            raise ValueError(f"Coluna {true_stat_name} não encontrada.")
        player_log[stat_name] = player_log[true_stat_name]

    player_log = player_log[player_log[stat_name].notnull()]
    player_log = player_log.head(10)
    player_log['DATA_STR'] = player_log['GAME_DATE'].dt.strftime('%d-%m-%Y')

    player_log['GAME_TYPE'] = player_log['SEASON_TYPE'].map({
        "Regular Season": "🏀 Temporada",
        "PlayIn": "🎯 Play-In",
        "Playoffs": "🏆 Playoffs"
    })

    df = player_log.copy()
    avg = round(df[stat_name].mean(), 2)

    if threshold is None:
        threshold = avg
    if odd is None:
        odd = 1.0

    cores = ['green' if val > threshold else 'red' for val in df[stat_name]]
    x_vals = df['DATA_STR'].tolist()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=x_vals,
        y=df[stat_name],
        marker_color=cores,
        hovertext=[
            (
                f"{row['GAME_TYPE']} | {row['DATA_STR']} | "
                f"{int(sum([row[col] for col in parts]))} ({' + '.join([f'{int(row[col])} {col}' for col in parts])}) | "
                f"MIN: {int(row['MIN'])}"
            ) if '+' in stat_name else
            f"{row['GAME_TYPE']} | {row['DATA_STR']} | {int(row[stat_name])} {stat_name} | MIN: {int(row['MIN'])}"
            for _, row in df.iterrows()
        ],
        hoverinfo="text",
        text=[
            (
                f"<b>{int(sum([row[col] for col in parts]))} ({' + '.join([f'{int(row[col])} {col}' for col in parts])})</b><br>"
                f"<span style='font-size:12px'>MIN: {int(row['MIN'])}</span>"
            ) if '+' in stat_name else
            f"<b>{int(row[stat_name])} {stat_name}</b><br><span style='font-size:12px'>MIN: {int(row['MIN'])}</span>"
            for _, row in df.iterrows()
        ],
        textangle=0,
        textposition="auto",
    ))

    fig.add_shape(type="line", x0=-0.5, x1=len(df)-0.5, y0=threshold, y1=threshold,
                  line=dict(color="blue", width=2, dash="dash"))

    fig.add_annotation(dict(
        xref='paper',
        yref='y',
        x=1.04,
        y=threshold,
        text=f"{round(threshold, 1)}",
        showarrow=False,
        font=dict(color="blue", size=14),
        align="left"
    ))

    for i, row in df.iterrows():
        x = i
        matchup = row['MATCHUP']
        abbrs = matchup.replace('@', 'vs').replace('.', '').split('vs')
        abbrs = [abbr.strip() for abbr in abbrs if abbr.strip()]
        logos = []
        for abbr in abbrs:
            team_data = teams.find_team_by_abbreviation(abbr)
            if team_data:
                team_id_logo = team_data['id']
                logos.append(f"https://cdn.nba.com/logos/nba/{team_id_logo}/global/L/logo.svg")

        if len(logos) == 2:
            logo_y = -0.22
            fig.add_layout_image(dict(
                source=logos[0],
                x=x - 0.22,
                y=logo_y,
                xref="x",
                yref="paper",
                sizex=0.28,
                sizey=0.25,
                xanchor="center",
                yanchor="bottom",
                layer="above"
            ))
            fig.add_annotation(dict(
                x=x,
                y=logo_y + 0.1,
                xref="x",
                yref="paper",
                text="vs",
                showarrow=False,
                font=dict(size=14),
                align="center"
            ))
            fig.add_layout_image(dict(
                source=logos[1],
                x=x + 0.22,
                y=logo_y,
                xref="x",
                yref="paper",
                sizex=0.28,
                sizey=0.25,
                xanchor="center",
                yanchor="bottom",
                layer="above"
            ))

    fig.update_layout(
        height=900,
        width=1800,
        margin=dict(t=100, b=250),
        title=f"{stat_label} nos Últimos 10 Jogos de {player_info['FIRST_NAME']} {player_info['LAST_NAME']}",
        xaxis=dict(
            tickmode='array',
            tickvals=x_vals,
            ticktext=x_vals,
            tickangle=0,
            title="Data",
            tickfont=dict(size=12)
        ),
        yaxis_title=stat_label,
        template="plotly_white",
        hovermode="x unified",
        showlegend=False,
    )

    html = pio.to_html(fig, full_html=False, include_plotlyjs='cdn')
    print("✅ Gráfico gerado com sucesso.")
    
    return html, avg, threshold, odd


@csrf_exempt
@login_required
def player_filtered_graph(request):
    """
    View para exibição de gráfico filtrado de estatísticas de jogador.
    
    Args:
        request: HttpRequest do Django.
    
    Returns:
        JsonResponse: Dados do gráfico filtrado.
    """
    print("🔍 Entrou na view player_filtered_graph")

    if request.method != 'POST':
        print("❌ Método HTTP inválido:", request.method)
        return JsonResponse({'error': 'Invalid request method'}, status=405)

    try:
        print("📦 Body bruto:", request.body)
        data = json.loads(request.body)
    except json.JSONDecodeError as e:
        print("❌ Erro ao decodificar JSON:", e)
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)

    stat_type = data.get("stat_type")
    main_player_name = data.get("main_player")
    missing_players = data.get("missing_players", [])

    print("📊 Stat Type:", stat_type)
    print("🏀 Main Player:", main_player_name)
    print("🙅‍♂️ Missing Players:", missing_players)

    if not stat_type or not main_player_name:
        return JsonResponse({'error': 'Missing stat_type or player name'}, status=400)

    def get_player_id_by_name(name):
        result = players.find_players_by_full_name(name)
        print(f"🔎 Buscando ID para {name}: resultado ->", result)
        return result[0]['id'] if result else None

    main_id = get_player_id_by_name(main_player_name)
    if not main_id:
        print("❌ Main player não encontrado.")
        return JsonResponse({'error': 'Main player not found'}, status=404)

    print("🆔 Main Player ID:", main_id)

    season = get_current_season()
    phases = ["Regular Season", "PlayIn", "Playoffs"]
    logs = []

    def load_phase_log(player_id, season, phase):
        try:
            print(f"📥 Carregando logs da fase: {phase}")
            df = PlayerGameLog(player_id=player_id, season=season, season_type_all_star=phase).get_data_frames()[0]
            df["SEASON_TYPE"] = phase
            df.columns = df.columns.str.upper()
            df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'], errors='coerce')
            df = df.dropna(subset=['GAME_DATE'])  # Remove registros com GAME_DATE inválido
            df['DATA_STR'] = df['GAME_DATE'].dt.strftime('%d-%m-%Y')
            df['GAME_TYPE'] = {
                "Regular Season": "🏀 Temporada",
                "PlayIn": "🎯 Play-In",
                "Playoffs": "🏆 Playoffs"
            }.get(phase, phase)
            return df
        except Exception as e:
            print(f"⚠️ Erro ao carregar {phase}: {e}")
            return pd.DataFrame()

    for phase in phases:
        df_phase = load_phase_log(main_id, season, phase)
        if not df_phase.empty:
            logs.append(df_phase)

    if not logs:
        print("❌ Nenhum log encontrado.")
        return JsonResponse({'error': 'No game logs found'}, status=404)

    main_log = pd.concat(logs, ignore_index=True)
    print("📄 Colunas do DataFrame principal:", main_log.columns.tolist())

    # Coletar datas de jogos com jogadores ausentes
    missing_dates = set()
    for missing in missing_players:
        pid = get_player_id_by_name(missing)
        if pid:
            for phase in phases:
                try:
                    log = PlayerGameLog(player_id=pid, season=season, season_type_all_star=phase).get_data_frames()[0]
                    log.columns = log.columns.str.upper()
                    log['GAME_DATE'] = pd.to_datetime(log['GAME_DATE'], errors='coerce')
                    missing_dates.update(log['GAME_DATE'].dropna())
                except Exception as e:
                    print(f"⚠️ Erro ao buscar jogos do jogador ausente {missing} na fase {phase}: {e}")

    # Filtra jogos em que os ausentes jogaram
    filtered = main_log[~main_log["GAME_DATE"].isin(missing_dates)].copy()

    column_aliases = {'3PT': 'FG3M'}

    if '+' in stat_type:
        components = stat_type.split('+')
        true_components = [column_aliases.get(comp, comp) for comp in components]
        for comp in true_components:
            if comp not in filtered.columns:
                print(f"❌ Stat component '{comp}' não encontrado.")
                return JsonResponse({'error': f"Stat component '{comp}' not found in data"}, status=400)
        filtered[stat_type] = filtered[true_components].sum(axis=1)
    else:
        true_components = [stat_type]
        if stat_type not in filtered.columns:
            print(f"❌ Stat '{stat_type}' não encontrada.")
            return JsonResponse({'error': f"Stat '{stat_type}' not found in data"}, status=400)

    df = filtered.sort_values(by='GAME_DATE', ascending=False).head(10)
    if df.empty or df[stat_type].isnull().all():
        print(f"❌ Dados inválidos para {stat_type}")
        return JsonResponse({'error': f'No valid {stat_type} data available'}, status=400)

    print("📊 Dados filtrados prontos:", df[[stat_type, 'DATA_STR']])

    threshold = data.get("threshold", df[stat_type].mean())
    colors = ['green' if val > threshold else 'red' for val in df[stat_type]]

    logos_pairs = []
    for _, row in df.iterrows():
        matchup = row['MATCHUP']
        abbrs = matchup.replace('@', 'vs').replace('.', '').split('vs')
        abbrs = [abbr.strip() for abbr in abbrs if abbr.strip()]
        logos = []
        for abbr in abbrs:
            team_data = teams.find_team_by_abbreviation(abbr)
            if team_data:
                team_id_logo = team_data['id']
                logos.append(f"https://cdn.nba.com/logos/nba/{team_id_logo}/global/L/logo.svg")
        logos_pairs.append(logos if len(logos) == 2 else [])

    text = []
    for _, row in df.iterrows():
        values = [f"{comp}: {row[comp]}" for comp in true_components]
        text.append(f"{' '.join(values)}<br>{row['MIN']} min")

    print("✅ Pronto para retorno com dados")

    return JsonResponse({
        'x': df['DATA_STR'].tolist(),
        'y': df[stat_type].tolist(),
        'text': text,
        'color': colors,
        'tickvals': list(range(len(df))),
        'ticktext': df['DATA_STR'].tolist(),
        'logos': logos_pairs,
        'threshold': round(threshold, 1)
    })





def fetch_and_format_lineup_data():
    """
    Obtém e formata dados dos alinhamentos dos jogos do dia.
    
    Returns:
        dict: Dados formatados dos alinhamentos:
            - jogos: Lista de jogos
            - alinhamentos: Alinhamentos por jogo
            - estatisticas: Estatísticas relevantes
    """
    url = "https://www.rotowire.com/basketball/nba-lineups.php"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    
    home_gtd_players, away_gtd_players, home_out_players, away_out_players = [], [], [], []

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        games = soup.find_all("div", class_="lineup is-nba")

        for game in games:
            try:
                teams_abbr = game.find_all("div", class_="lineup__abbr")
                if len(teams_abbr) < 2:
                    continue

                team_home_abbr = teams_abbr[1].text.strip()
                team_away_abbr = teams_abbr[0].text.strip()
                team_home = teams.find_team_by_abbreviation(team_home_abbr)
                team_away = teams.find_team_by_abbreviation(team_away_abbr)

                if team_home and team_away:
                    home_list = game.find("ul", class_="lineup__list is-home")
                    away_list = game.find("ul", class_="lineup__list is-visit")

                    if home_list:
                        li_home = home_list.find_all("li")
                        home_gtd_players.extend(extract_player_data(li_home, ["is-pct-play-50", "is-pct-play-75", "is-pct-play-25"], team_home['id']))
                        home_out_players.extend(extract_player_data(li_home, ["is-pct-play-0", "is-ofs"], team_home['id']))

                    if away_list:
                        li_away = away_list.find_all("li")
                        away_gtd_players.extend(extract_player_data(li_away, ["is-pct-play-50", "is-pct-play-75", "is-pct-play-25"], team_away['id']))
                        away_out_players.extend(extract_player_data(li_away, ["is-pct-play-0", "is-ofs"], team_away['id']))

            except Exception as e:
                print("Erro ao extrair dados do jogo:", e)

    # Format the player names
    same_team_gtd = [
        {"name": p['name'], "id": p['id'], "team_id": p['team_id']}
        for p in home_gtd_players + away_gtd_players
    ]
    same_team_out = [
        {"name": p['name'], "id": p['id'], "team_id": p['team_id']}
        for p in home_out_players + away_out_players
    ]

    same_team_gtd_formatted = [
        {"full_name": re.sub(r"^[CFG] ", "", p['name'].replace(" GTD", "").replace(" OFS", "")), "id": p['id']}
        for p in same_team_gtd
    ]
    same_team_out_formatted = [
        {"full_name": re.sub(r"^[CFG] ", "", p['name'].replace(" OUT", "").replace(" OFS", "")), "id": p['id']}
        for p in same_team_out
    ]

    return same_team_gtd_formatted, same_team_out_formatted



# Cache for storing team rosters
team_roster_cache = {}
def get_team_roster(team_id):
    """
    Obtém o roster atual de uma equipa.
    
    Args:
        team_id: ID da equipa.
    
    Returns:
        JsonResponse: Informações sobre os jogadores da equipa.
    """
    if team_id in team_roster_cache:
        return team_roster_cache[team_id]
    
    # If not cached, fetch the roster and cache it
    team_data = teams.find_team_by_id(team_id)
    if not team_data:
        return []

    # Assuming that the `find_team_by_id` returns the roster data
    team_roster = team_data.get('roster', [])
    team_roster_cache[team_id] = team_roster
    return team_roster


def fetch_and_process_lineups():
    """
    Processa os alinhamentos das equipas da casa e visitante.
    
    Returns:
        dict: Dados processados dos alinhamentos:
            - casa: Alinhamento da equipa da casa
            - visitante: Alinhamento da equipa visitante
    """
    url = "https://www.rotowire.com/basketball/nba-lineups.php"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    
    home_gtd_players, away_gtd_players, home_out_players, away_out_players = [], [], [], []

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        games = soup.find_all("div", class_="lineup is-nba")

        for game in games:
            try:
                teams_abbr = game.find_all("div", class_="lineup__abbr")
                if len(teams_abbr) < 2:
                    continue

                team_home_abbr = teams_abbr[1].text.strip()
                team_away_abbr = teams_abbr[0].text.strip()

                team_home = teams.find_team_by_abbreviation(team_home_abbr)
                team_away = teams.find_team_by_abbreviation(team_away_abbr)

                if team_home and team_away:
                    home_list = game.find("ul", class_="lineup__list is-home")
                    away_list = game.find("ul", class_="lineup__list is-visit")

                    if home_list:
                        li_home = home_list.find_all("li")
                        home_gtd_players.extend(extract_player_data(li_home, ["is-pct-play-50", "is-pct-play-75", "is-pct-play-25"], team_home['id']))
                        home_out_players.extend(extract_player_data(li_home, ["is-pct-play-0", "is-ofs"], team_home['id']))

                    if away_list:
                        li_away = away_list.find_all("li")
                        away_gtd_players.extend(extract_player_data(li_away, ["is-pct-play-50", "is-pct-play-75", "is-pct-play-25"], team_away['id']))
                        away_out_players.extend(extract_player_data(li_away, ["is-pct-play-0", "is-ofs"], team_away['id']))

            except Exception as e:
                print("Erro ao extrair dados do jogo:", e)

    return home_gtd_players, away_gtd_players, home_out_players, away_out_players

# Arredonda sempre para o valor ".5" acima
def round_to_always_half(value):
    """
    Arredonda um valor para o meio número mais próximo.
    
    Args:
        value: Valor a ser arredondado.
    
    Returns:
        float: Valor arredondado para o meio número mais próximo.
    """
    return int(value) + 0.5

# Calcula odds ajustadas com pesos recentes para estatísticas de jogador
def calculate_weighted_odds(player_points, line):
    """
    Calcula as odds ajustadas com base nas estatísticas recentes do jogador.
    
    Args:
        player_points: Lista de pontos do jogador nos últimos jogos.
        line: Linha de pontos para a aposta.
    
    Returns:
        float: Odds ajustadas calculadas.
    """
    n = len(player_points)
    if n == 0:
        return None

    # Cria pesos progressivos (jogos mais recentes têm mais peso)
    weights = np.linspace(0.5, 1.0, n)
    mean = np.average(player_points, weights=weights)
    variance = np.average((player_points - mean) ** 2, weights=weights)
    std = np.sqrt(variance)

    # Garante que o desvio padrão mínimo é 2
    if std < 2:
        std = 2

    # Calcula probabilidade de over/under
    prob_over = 1 - norm.cdf(line, loc=mean, scale=std)
    prob_under = norm.cdf(line, loc=mean, scale=std)

    # Calcula as odds ajustadas
    odds_over = round(1 / prob_over, 2) if prob_over > 0 else 100.0
    odds_under = round(1 / prob_under, 2) if prob_under > 0 else 100.0

    return {
        "over_odds": round(odds_over - 0.15, 2),
        "under_odds": round(odds_under - 0.15, 2),
        "prob_over": round(prob_over * 100, 1),
        "prob_under": round(prob_under * 100, 1)
    }



# Busca estatísticas de um jogador, calcula linha provável e odds para a aposta
def get_player_stats(player_name, stat_type="PTS", last_n_games=10, season=get_current_season()):
    """
    Obtém estatísticas de um jogador.
    
    Args:
        player_name: Nome do jogador.
        stat_type: Tipo de estatística.
        last_n_games: Número de últimos jogos.
        season: Temporada atual.
    
    Returns:
        dict: Estatísticas do jogador.
    """
    column_aliases = {'3PT': 'FG3M'}
    stat_type = stat_type.upper()

    # Busca jogador pelo nome
    player_dict = players.find_players_by_full_name(player_name)
    if not player_dict:
        print("Jogador não encontrado.")
        return None

    player_id = player_dict[0]['id']
    gamelog = PlayerGameLog(player_id=player_id, season=season).get_data_frames()[0]

    if gamelog.empty:
        print("Sem dados de jogo disponíveis.")
        return None

    # Pega os últimos jogos e inverte a ordem
    recent_games = gamelog.head(last_n_games).iloc[::-1]
    recent_games.columns = recent_games.columns.str.upper()

    if recent_games.empty or 'MIN' not in recent_games.columns:
        print("Dados inválidos.")
        return None

    # Se a estatística for composta (ex.: PTS+REB)
    if '+' in stat_type:
        components = stat_type.split('+')
        for comp in components:
            alias = column_aliases.get(comp, comp)
            if alias not in recent_games.columns:
                print(f"Coluna {alias} não encontrada.")
                return None
        recent_games[stat_type] = recent_games[[column_aliases.get(c, c) for c in components]].sum(axis=1)
    else:
        stat_col = column_aliases.get(stat_type, stat_type)
        if stat_col not in recent_games.columns:
            print(f"Coluna {stat_col} não encontrada.")
            return None
        recent_games[stat_type] = recent_games[stat_col]

    # Remove outliers extremos
    if len(recent_games) >= 10:
        z_scores = (recent_games[stat_type] - recent_games[stat_type].mean()) / recent_games[stat_type].std()
        recent_games = recent_games[(z_scores > -5) & (z_scores < 5)]

    if recent_games.empty:
        print("Todos os jogos foram filtrados.")
        return None

    # Calcula a linha (linha usada para aposta) arredondada
    line = round_to_always_half(recent_games[stat_type].mean())
    odds = calculate_weighted_odds(recent_games[stat_type].to_numpy(), line)

    if not odds:
        return None

    return {
        'player': player_name,
        'stat_type': stat_type,
        'line_used': line,
        'over_odds': odds['over_odds'],
        'under_odds': odds['under_odds'],
        'prob_over': odds['prob_over'],
        'prob_under': odds['prob_under']
    }
     
def american_to_decimal(odds_str):
    """
    Converte odds no formato americano para decimal.
    
    Args:
        odds_str: Odds no formato americano (ex: +150, -110).
    
    Returns:
        float: Odds no formato decimal.
    """
    try:
        odds = int(odds_str)
        if odds > 0:
            return round(1 + (odds / 100), 2)
        else:
            return round(1 + (100 / abs(odds)), 2)
    except ValueError:
        print(f"⚠️ Erro ao converter odds: {odds_str}")
        return None
    
    

# Função para mapear estatísticas
def map_stat_name(stat_name):
    """
    Mapeia o nome de uma estatística para um formato padrão.
    
    Args:
        stat_name: Nome da estatística.
    
    Returns:
        str: Nome da estatística no formato padrão.
    """
    stat_name_map = {
        'Points': 'PTS',
        'Assists': 'AST',
        'Rebounds': 'REB',
        'Points + Assists': 'PTS+AST',
        'Points + Rebounds': 'PTS+REB',
        'Assists + Rebounds': 'AST+REB',
        'Points + Assists + Rebounds': 'PTS+AST+REB',
        'Blocks': 'BLK',
        'Steals': 'STL',
        'Steals + Blocks': 'STL+BLK',
        'Turnovers': 'TO',
        '3PT Made': '3PT',
        'Double Double': 'DD',
        'Triple Double': 'TD'
    }
    return stat_name_map.get(stat_name, stat_name)  # Retorna o nome da estatística mapeado ou o nome original

def scrape_player_props(first_name, last_name):
    """
    Realiza scraping das props de apostas de um jogador.
    
    Args:
        first_name: Primeiro nome do jogador.
        last_name: Último nome do jogador.
    
    Returns:
        dict: Props de apostas do jogador ou None se não encontrado.
    """
    # Normalizar e formatar o nome do jogador para a URL
    first = unidecode(first_name.strip().lower())
    last = unidecode(last_name.strip().lower())
    player_slug = f"{first}-{last}"
    url = f"https://www.optimal-bet.com/player-props/{player_slug}"

    print(f"🔍 Acessando a página de props do jogador: {url}")

    # Realizar a requisição HTTP
    try:
        response = requests.get(url)
        print(f"Status da requisição HTTP: {response.status_code}")
        if response.status_code != 200:
            print(f"❌ Erro ao acessar a página: Status code {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro na requisição: {e}")
        return None

    # Analisar o conteúdo HTML
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table')

    if not table:
        print("❌ Tabela de props não encontrada na página.")
        return None

    print("✅ Tabela de props encontrada. Processando os dados...")

    # Extrair os dados da tabela
    props_dict = {}
    for tr in table.find('tbody').find_all('tr'):
        cells = [td.text.strip() for td in tr.find_all('td')]
        if len(cells) == 4:
            prop_type = cells[0]
            line = cells[1]
            over = cells[2].replace('+', '')
            under = cells[3].replace('+', '')

            # Mapear estatísticas para a convenção usada no código
            mapped_stat_type = map_stat_name(prop_type)
            
            print(f"Extraindo dados para {mapped_stat_type}: linha = {line}, over = {over}, under = {under}")

            over_decimal = american_to_decimal(over)
            under_decimal = american_to_decimal(under)

            props_dict[mapped_stat_type] = {
                'line': line,
                'over_odds': over_decimal,
                'under_odds': under_decimal
            }

    if not props_dict:
        print("❌ Nenhum dado extraído da tabela.")
        return None

    return props_dict


def scrape_injuries_foxsports(player_name):
    """
    Realiza scraping de informações de lesões de um jogador no site Fox Sports.
    
    Args:
        player_name: Nome do jogador.
    
    Returns:
        list: Lista de dicionários contendo informações sobre lesões:
            - date: Data da lesão
            - injury: Descrição da lesão
    """
    # Normaliza o nome para o formato da URL
    name_slug = unidecode(player_name.lower().replace(" ", "-"))
    url = f"https://www.foxsports.com/nba/{name_slug}-player-injuries"
    print(f"Scraping: {url}")

    try:
        response = requests.get(url)
        if response.status_code != 200:
            print("Erro ao aceder à página de lesões.")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        injuries = []
        # Procura todas as linhas da tabela de lesões
        rows = soup.select("tbody.row-data tr")
        for row in rows:
            tds = row.find_all("td")
            if len(tds) >= 2:
                date = tds[0].get_text(strip=True)
                injury = tds[1].get_text(strip=True)
                injuries.append({"date": date, "injury": injury})
        return injuries
    except Exception as e:
        print(f"Erro no scraping: {e}")
        return []



@cache_page(60 * 30)
def player_details(request, player_id):
    # Obtém informações básicas do jogador
    player_info = get_player_info(player_id)
    
    # Define a temporada a ser analisada
    season = get_current_season()
    
    # Define os tipos de temporada a considerar
    season_types = ["Regular Season", "Playoffs", "PlayIn"]

    all_logs = []

    # Busca os logs de jogos para cada tipo de temporada
    for season_type in season_types:
        try:
            log = PlayerGameLog(
                player_id=player_id,
                season=season,
                season_type_all_star=season_type
            ).get_data_frames()[0]
            
            # Se houver dados, adiciona uma coluna para identificar o tipo de temporada
            if not log.empty:
                log["SEASON_TYPE"] = season_type
                all_logs.append(log)
        except Exception as e:
            # Em caso de erro ao buscar jogos, imprime o erro
            print(f"Erro ao buscar {season_type}: {e}")

    # Se não houver jogos encontrados, cria um DataFrame vazio com as colunas necessárias
    if not all_logs:
        player_log = pd.DataFrame(columns=['GAME_DATE', 'MATCHUP', 'MIN', 'PTS', 'AST', 'REB', 'FG3M', 'BLK', 'STL'])
    else:
        # Junta todos os jogos num único DataFrame
        player_log = pd.concat(all_logs, ignore_index=True)

    # Define as colunas de interesse
    columns = ['GAME_DATE', 'MATCHUP', 'MIN', 'PTS', 'AST', 'REB', 'FG3M', 'BLK', 'STL', 'SEASON_TYPE']
    player_filtered = player_log[columns].copy()

    # Converte as datas para datetime e ordena do jogo mais recente para o mais antigo
    player_filtered['GAME_DATE'] = pd.to_datetime(player_filtered['GAME_DATE'])
    player_filtered = player_filtered.sort_values(by='GAME_DATE', ascending=False)

    # Seleciona os últimos 10 jogos
    last_10_games = player_filtered.head(10)

    # Calcula as médias dos principais estatísticas
    average_points = round(player_filtered['PTS'].mean(), 2)
    average_assists = round(player_filtered['AST'].mean(), 2)
    average_rebounds = round(player_filtered['REB'].mean(), 2)
    average_3pt = round(player_filtered['FG3M'].mean(), 2)
    average_blocks = round(player_filtered['BLK'].mean(), 2)
    average_steals = round(player_filtered['STL'].mean(), 2)

    # Prepara os dados que serão enviados ao template
    player_data = {
        'full_name': f"{player_info['FIRST_NAME']} {player_info['LAST_NAME']}",
        'age': player_info.get('AGE'),
        'height': player_info.get('HEIGHT_METERS'),
        'team_name': player_info.get('TEAM_NAME'),
        'team_id': player_info.get('TEAM_ID'),
        'last_10_games': last_10_games.to_dict(orient='records'),
        'stats': {
            'points': average_points,
            'assists': average_assists,
            'rebounds': average_rebounds,
            'three_point': average_3pt,
            'blocks': average_blocks,
            'steals': average_steals,
        },
        'player_id': player_id
    }
    
    player_name = f"{player_info['FIRST_NAME']} {player_info['LAST_NAME']}"
    injuries = scrape_injuries_foxsports(player_name)
    
    return render(request, 'player_details.html', {
        'player': player_data,
        'injuries': injuries,
    })



@cache_page(60 * 30)
def player_stat(request, player_id, stat_type):
    """
    View para exibição de estatísticas específicas de um jogador.
    
    Args:
        request: HttpRequest do Django.
        player_id: ID do jogador.
        stat_type: Tipo de estatística.
    
    Returns:
        HttpResponse: Página com estatísticas do jogador.
    """
    try:
        # Busca informações básicas do jogador
        player_info = get_player_info(player_id)
        player_info['id'] = player_id

        # Mapeia o nome da estatística para uma label amigável
        stat_label_map = {
            'PTS': 'Pontos', 'AST': 'Assistências', 'REB': 'Rebotes', 'BLK': 'Bloqueios', 'STL': 'Roubos de Bola',
            '3PT': '3 Pontos', 'PTS+AST': 'Pontos + Assistências', 'PTS+REB': 'Pontos + Rebotes',
            'AST+REB': 'Assistências + Rebotes', 'PTS+AST+REB': 'Pontos + Assistências + Rebotes',
        }
        stat_label = stat_label_map.get(stat_type, stat_type)

        # Tenta fazer scraping
        print(f"🔎 Tentando fazer scraping de dados para {player_info['FIRST_NAME']} {player_info['LAST_NAME']}")
        props_data = scrape_player_props(player_info['FIRST_NAME'], player_info['LAST_NAME'])

        if props_data:
            threshold = props_data.get(stat_type, {}).get('line', 0)
            odd = props_data.get(stat_type, {}).get('over_odds', 1.0)
            print(f"✅ Dados de props extraídos: Linha = {threshold}, Odds = {odd}")
            
            # Verificar se a linha ou odds são inválidos
            if threshold == 0 or odd == 1.0:
                print(f"⚠️ Linha ou odds inválidos, utilizando fallback.")
                stats_data = get_player_stats(
                    player_name=f"{player_info['FIRST_NAME']} {player_info['LAST_NAME']}",
                    stat_type=stat_type,
                    last_n_games=10
                )
                if stats_data:
                    threshold = stats_data['line_used']
                    odd = stats_data['over_odds']
                    print(f"✅ Fallback: Linha = {threshold}, Odds = {odd}")
                else:
                    threshold = 0
                    odd = 1.0
                    print("⚠️ Fallback falhou, usando valores padrão.")
        else:
            print(f"⚠️ Scraping falhou, tentando obter estatísticas...")
            stats_data = get_player_stats(
                player_name=f"{player_info['FIRST_NAME']} {player_info['LAST_NAME']}",
                stat_type=stat_type,
                last_n_games=10
            )

            if stats_data:
                threshold = stats_data['line_used']
                odd = stats_data['over_odds']
                print(f"✅ Estatísticas obtidas com sucesso: Linha = {threshold}, Odds = {odd}")
            else:
                threshold = 0
                odd = 1.0
                print("⚠️ Não foi possível obter dados de estatísticas. Usando valores padrão.")

        # Verificando tipos de dados para `threshold` e `odd`
        print(f"🔎 Verificando tipo de threshold: {type(threshold)} e odd: {type(odd)}")

        # Garantir que `threshold` e `odd` sejam números (floats)
        try:
            threshold = float(threshold)
            odd = float(odd)
        except ValueError as e:
            print(f"❌ Erro ao converter threshold ou odd para float: {e}")
            threshold = 0
            odd = 1.0

        # ✅ Gera o gráfico usando o threshold calculado
        try:
            graph_html, _, _, _ = generate_stat_graph(
                player_info=player_info,
                stat_name=stat_type,
                stat_label=stat_label,
                season=get_current_season(),
                threshold=threshold,
                odd=odd
            )
        except Exception as e:
            print(f"⚠️ Erro ao gerar gráfico: {e}")
            graph_html = ""

        # Busca jogadores GTD e OUT da mesma equipa
        home_gtd_players, away_gtd_players, home_out_players, away_out_players = fetch_and_process_lineups()

        # Formata jogadores GTD da mesma equipa
        same_team_gtd_formatted = []
        for p in home_gtd_players + away_gtd_players:
            if p['team_id'] == player_info['TEAM_ID']:
                formatted = {
                    "full_name": re.sub(r"^[CFG] ", "", p['name'].replace(" GTD", "").replace(" OFS", "")),
                    "id": p['id']
                }
                if not check_duplicate(same_team_gtd_formatted, p['id']):
                    same_team_gtd_formatted.append(formatted)

        # Formata jogadores OUT da mesma equipa
        same_team_out_formatted = []
        for p in home_out_players + away_out_players:
            if p['team_id'] == player_info['TEAM_ID']:
                formatted = {
                    "full_name": re.sub(r"^[CFG] ", "", p['name'].replace(" OUT", "").replace(" OFS", "")),
                    "id": p['id']
                }
                if not check_duplicate(same_team_out_formatted, p['id']):
                    same_team_out_formatted.append(formatted)

        # Prepara os dados para renderizar o template
        player_data = {
            'full_name': f"{player_info['FIRST_NAME']} {player_info['LAST_NAME']}",
            'age': player_info['AGE'],
            'height': player_info['HEIGHT_METERS'],
            'team_name': player_info.get('TEAM_NAME', None),
            'team_id': player_info['TEAM_ID'],
            'average_stat': threshold,
            'threshold': threshold,
            'odd': odd,
            'player_id': player_id,
            'same_team_gtd': same_team_gtd_formatted,
            'same_team_out': same_team_out_formatted,
            'graph_html': graph_html,
        }

        player_name = f"{player_info['FIRST_NAME']} {player_info['LAST_NAME']}"
        injuries = scrape_injuries_foxsports(player_name)

        return render(request, 'player_stat.html', {
            'player': player_data,
            'current_stat': stat_type,
            'injuries': injuries,
        })

    except Timeout:
        # Se a requisição exceder o tempo limite, exibe uma página de erro amigável
        return render(request, 'error_page.html', {
            'error_message': 'A requisição demorou muito tempo para responder. Por favor, tente novamente.',
            'suggestion': 'Tente atualizar a página.'
        })

    except Exception as e:
        # Para qualquer outro erro inesperado
        print(f"❌ Erro inesperado: {e}")
        return render(request, 'error_page.html', {
            'error_message': 'Ocorreu um erro inesperado. Por favor, tente novamente.',
            'suggestion': 'Se o erro persistir, entre em contato com o suporte.'
        })



# View para obter o próximo jogo de um jogador
def get_next_game(request):
    """
    Obtém informações sobre o próximo jogo de um jogador.
    
    Args:
        request: HttpRequest do Django.
    
    Returns:
        JsonResponse: Informações sobre o próximo jogo.
    """
    print("Recebida requisição para get_next_game")
    print("Parâmetros GET:", request.GET)
    print("player_name recebido:", request.GET.get('player_name'))

    # Inicializa a resposta padrão
    response_data = {
        'status': 'success',
        'next_game': {
            'available': False,
            'message': 'Nenhum jogo encontrado',
            'home_team': '',
            'away_team': '',
            'game_date': '',
            'game_time': '',
            'home_team_logo': '',
            'away_team_logo': '',
            'game_id': '',
            'id': ''
        }
    }

    try:
        # Validação do nome do jogador
        player_name = request.GET.get('player_name')
        if not player_name:
            response_data['status'] = 'error'
            response_data['message'] = "❌ Nome do jogador não fornecido."
            return JsonResponse(response_data, status=400)

        # Busca o ID do jogador
        player_dict = players.find_players_by_full_name(player_name)
        if not player_dict:
            response_data['status'] = 'error'
            response_data['message'] = "❌ Jogador não encontrado."
            return JsonResponse(response_data, status=400)

        player_id = player_dict[0]['id']
        player_info = commonplayerinfo.CommonPlayerInfo(player_id=player_id).get_data_frames()[0]
        team_abbr = player_info["TEAM_ABBREVIATION"].iloc[0]

        # Busca os jogos futuros
        sb = scoreboard.ScoreBoard()
        games = sb.games.get_dict()
        game_found = False

        for game in games:
            # Procura jogo onde o jogador atua
            if game['homeTeam']['teamTricode'] == team_abbr or game['awayTeam']['teamTricode'] == team_abbr:
                game_status = game.get("gameStatus", "")
                if game_status == 2:
                    # Jogo já a decorrer, não permite aposta
                    response_data['status'] = 'error'
                    response_data['message'] = "⛔ O jogo já está a decorrer, não é possível apostar."
                    return JsonResponse(response_data, status=400)

                # Converte hora do jogo para local
                game_time_utc = parser.parse(game['gameTimeUTC']).replace(tzinfo=timezone.utc)
                game_time_local = game_time_utc.astimezone(tz=None)

                game_date = game_time_local.strftime("%d/%m/%Y")
                game_time = game_time_local.strftime("%H:%M")

                # Monta URLs dos logotipos
                home_team_id = game['homeTeam']['teamId']
                away_team_id = game['awayTeam']['teamId']
                home_team_logo = f"https://cdn.nba.com/logos/nba/{home_team_id}/global/L/logo.svg"
                away_team_logo = f"https://cdn.nba.com/logos/nba/{away_team_id}/global/L/logo.svg"

                # Preenche os dados do próximo jogo
                response_data['next_game'] = {
                    'available': True,
                    'home_team': game['homeTeam']['teamName'],
                    'away_team': game['awayTeam']['teamName'],
                    'game_date': game_date,
                    'game_time': game_time,
                    'home_team_logo': home_team_logo,
                    'away_team_logo': away_team_logo,
                    'game_id': game['gameId'],
                    'person_id': player_id
                }

                game_found = True
                break

        if not game_found:
            response_data['status'] = 'error'
            response_data['message'] = "❌ Não é possível apostar neste jogador."
            return JsonResponse(response_data, status=400)

    except Exception as e:
        # Captura erro geral
        response_data['status'] = 'error'
        response_data['message'] = f"Erro inesperado: {str(e)}"
        return JsonResponse(response_data, status=400)

    return JsonResponse(response_data)


def get_player_stats_by_game_id(player_name, game_id, season=None):
    """Obtém as estatísticas de um jogador para um jogo específico."""
    if season is None:
        season = get_current_season()

    try:
        # 1. Busca ID do jogador
        player_name_clean = unidecode(player_name.strip().lower())
        player_id = None
        
        for player in players.get_players():
            if player_name_clean in unidecode(player['full_name'].lower()):
                player_id = player['id']
                break

        if not player_id:
            print(f"❌ Jogador '{player_name}' não encontrado.")
            return None

        print(f"🔍 Buscando logs para {player_name} (ID: {player_id})")

        # 2. Busca logs do jogador
        logs = []
        for season_type in ["Playoffs", "PlayIn", "Regular Season"]:
            try:
                df = PlayerGameLog(
                    player_id=player_id, 
                    season=season, 
                    season_type_all_star=season_type
                ).get_data_frames()[0]
                
                if not df.empty:
                    print(f"✅ Encontrados {len(df)} jogos para {season_type}")
                    df["SEASON_TYPE"] = season_type
                    logs.append(df)
            except Exception as e:
                print(f"⚠️ Erro ao buscar logs ({season_type}) para {player_name}: {e}")
                continue

        if not logs:
            print(f"❌ Nenhum log encontrado para '{player_name}'.")
            return None

        # 3. Processa logs e encontra coluna do GAME_ID
        full_log = pd.concat(logs, ignore_index=True)
        print(f"📊 Colunas disponíveis: {full_log.columns.tolist()}")
        
        game_id_col = None
        for col in ['GAME_ID', 'Game_ID', 'game_id', 'GAMEID', 'GameID']:
            if col in full_log.columns:
                game_id_col = col
                break
                
        if not game_id_col:
            print(f"❌ Nenhuma coluna de ID de jogo encontrada. Colunas disponíveis: {full_log.columns.tolist()}")
            return None
            
        print(f"✅ Usando coluna '{game_id_col}' para ID do jogo")

        # 4. Busca estatísticas do jogo específico
        game_id_str = str(game_id)
        full_log[game_id_col] = full_log[game_id_col].astype(str)
        game_stats = full_log[full_log[game_id_col] == game_id_str]

        if game_stats.empty:
            print(f"📭 '{player_name}' não tem stats para o jogo {game_id}.")
            print(f"Jogos disponíveis: {full_log[game_id_col].unique().tolist()}")
            return None

        # 5. Processa e retorna estatísticas
        stats = game_stats.iloc[0].to_dict()
        try:
            stats['MIN'] = float(stats.get('MIN', 0))
        except:
            stats['MIN'] = 0.0

        print(f"✅ Stats encontrados para {player_name} no jogo {game_id}")
        return stats

    except Exception as e:
        print(f"❌ Erro inesperado ao buscar stats de {player_name}: {e}")
        return None


# Recalcula as odds totais de uma aposta múltipla
def recalcular_total_odds(multipla):
    """
    Recalcula as odds totais de uma aposta múltipla.
    
    Args:
        multipla: Objeto ApostaMultipla.
    
    Returns:
        float: Odds total recalculada.
    """
    odds = 1
    for aposta in multipla.apostas.all():
        if aposta.status == "cancelada":
            odds *= 1.00
        else:
            odds *= float(aposta.odds)
    return round(odds, 2)

# Cache global para stats e jogos indisponíveis
STATS_CACHE = {}  # {(jogador, game_id): (stats, timestamp)}
GAME_STATS_UNAVAILABLE = {}  # {game_id: timestamp}
CACHE_EXPIRATION = 600  # 10 minutos em segundos

def verificar_apostas_por_jogo(game_id, user=None):
    """
    Verifica e atualiza o status das apostas relacionadas a um jogo específico.
    
    Args:
        game_id: ID do jogo.
        user: Utilizador específico para verificar apostas (opcional).
    
    Returns:
        None: Atualiza diretamente o status das apostas no banco de dados.
    """
    global STATS_CACHE, GAME_STATS_UNAVAILABLE
    
    try:
        print(f"🔎 Verificando apostas via player logs para o jogo {game_id}")
        
        # Verifica o status do jogo
        try:
            box = boxscore.BoxScore(game_id=game_id)
            game_data = box.game.get_dict()
            game_status = game_data.get('gameStatus', 0)
            
            # Se o jogo ainda não terminou (status != 3), não verifica as apostas
            if game_status != 3:
                print(f"⏳ Jogo {game_id} ainda não terminou (status: {game_status})")
                return
                
        except Exception as e:
            print(f"⚠️ Erro ao verificar status do jogo {game_id}: {e}")
            return
        
        # Limpa cache expirado
        current_time = time_module.time()
        GAME_STATS_UNAVAILABLE = {k: v for k, v in GAME_STATS_UNAVAILABLE.items() 
                                if current_time - v < CACHE_EXPIRATION}
        
        apostas = Aposta.objects.filter(jogo_id=game_id, status="pendente")
        if user:
            apostas = apostas.filter(user=user)

        for aposta in apostas:
            jogador = aposta.jogador
            cache_key = (jogador, game_id)
            
            # Se já sabemos que não há stats para este jogo, ignora as próximas apostas deste jogo
            if game_id in GAME_STATS_UNAVAILABLE:
                if current_time - GAME_STATS_UNAVAILABLE[game_id] >= CACHE_EXPIRATION:
                    print(f"🔄 Cache expirado para jogo {game_id}, verificando novamente...")
                    del GAME_STATS_UNAVAILABLE[game_id]
                else:
                    print(f"⏩ Ignorando verificação repetida para jogo {game_id} (stats indisponíveis)")
                    continue

            if cache_key in STATS_CACHE:
                stats, timestamp = STATS_CACHE[cache_key]
                if current_time - timestamp < CACHE_EXPIRATION:
                    resultado = stats
                else:
                    print(f"🔄 Cache expirado para {jogador}, buscando novos dados...")
                    resultado = get_player_stats_by_game_id(jogador, game_id)
                    STATS_CACHE[cache_key] = (resultado, current_time)
            else:
                resultado = get_player_stats_by_game_id(jogador, game_id)
                STATS_CACHE[cache_key] = (resultado, current_time)

            if resultado is None:
                print(f"⚠️ {jogador} ainda sem stats disponíveis. Tentará novamente depois.")
                # Marca este jogo como já verificado sem stats
                GAME_STATS_UNAVAILABLE[game_id] = current_time
                continue

            minutos = resultado.get('MIN', 0)
            if pd.isna(minutos) or minutos == 0:
                print(f"🚫 {aposta.jogador} não jogou. Cancelando aposta.")
                aposta.status = "cancelada"
                aposta.user.saldo += aposta.valor_apostado
                aposta.user.save()
                aposta.save()
                continue

            tipo = aposta.tipo_aposta.upper()

            # Determinar qual estatística do jogador deve ser utilizada com base no tipo de aposta
            if "PTS+AST+REB" in tipo:
                real_stat = resultado["PTS"] + resultado["AST"] + resultado["REB"]
            elif "PTS+AST" in tipo:
                real_stat = resultado["PTS"] + resultado["AST"]
            elif "PTS+REB" in tipo:
                real_stat = resultado["PTS"] + resultado["REB"]
            elif "AST+REB" in tipo:
                real_stat = resultado["AST"] + resultado["REB"]
            elif "PTS" in tipo:
                real_stat = resultado["PTS"]
            elif "AST" in tipo:
                real_stat = resultado["AST"]
            elif "REB" in tipo:
                real_stat = resultado["REB"]
            elif "BLK" in tipo:
                real_stat = resultado["BLK"]
            elif "STL" in tipo:
                real_stat = resultado["STL"]
            elif "3PT" in tipo:
                real_stat = resultado["FG3M"]
            else:
                print(f"⚠️ Tipo de aposta desconhecido: {tipo}")
                continue

            # Verificar se a aposta é válida com base no threshold
            match = re.search(r"(\d+(\.\d+)?)", aposta.tipo_aposta)
            if not match:
                print(f"⚠️ Threshold inválido: {aposta.tipo_aposta}")
                continue

            threshold = float(match.group(1))
            ganhou = ("OVER" in tipo and real_stat > threshold) or ("UNDER" in tipo and real_stat < threshold)

            aposta.status = "ganha" if ganhou else "perdida"
            print(f"{'✅' if ganhou else '❌'} {aposta.jogador}: {real_stat} vs linha {threshold}")

            aposta.save()

            # PAGAMENTO DE APOSTAS SIMPLES
            multiplas = ApostaMultipla.objects.filter(apostas=aposta, status="pendente").distinct()
            if not multiplas.exists() and aposta.status == "ganha":
                ganho = (aposta.valor_apostado * Decimal(aposta.odds)).quantize(Decimal("0.01"))
                aposta.user.saldo += ganho
                print(f"💰 Pagamento realizado para aposta simples do usuário {aposta.user.id}. Valor ganho: {ganho}")
                aposta.user.save()

            # VERIFICAÇÃO DE APOSTAS MÚLTIPLAS
            for multipla in multiplas:
                print(f"Verificando múltipla {multipla.id} com {len(multipla.apostas.all())} apostas.")

                # Verificar se todas as apostas foram ganhas
                todas_ganhas = True
                for aposta_multipla in multipla.apostas.all():
                    if aposta_multipla.status != "ganha":
                        todas_ganhas = False
                        break

                if todas_ganhas:
                    novo_total_odds = recalcular_total_odds(multipla)
                    multipla.total_odds = novo_total_odds
                    multipla.possiveis_ganhos = (Decimal(multipla.valor_apostado) * Decimal(novo_total_odds)).quantize(Decimal("0.01"))

                    multipla.status = "ganha"
                    print(f"💰 Pagamento realizado para a aposta múltipla {multipla.id}.")
                    multipla.user.saldo += multipla.possiveis_ganhos
                    print(f"Novo saldo do usuário {multipla.user.id}: {multipla.user.saldo}")
                    multipla.user.save()
                else:
                    multipla.status = "perdida"
                    print(f"❌ Aposta múltipla {multipla.id} foi marcada como perdida.")

                multipla.save()

    except Exception as e:
        print(f"❌ Erro em verificar_apostas_por_jogo: {e}")

    

def get_jogadores_ajax(request):
    """
    View para obtenção de lista de jogadores via AJAX.
    
    Args:
        request: HttpRequest do Django.
    
    Returns:
        JsonResponse: Lista de jogadores.
    """
    team_id = request.GET.get("team_id")
    estatistica = "PTS"
    sugestoes = []

    try:
        team_id = int(team_id)
        roster = commonteamroster.CommonTeamRoster(team_id=team_id).get_data_frames()[0]
        amostra = roster.sample(n=min(5, len(roster)))  # Pega 5 jogadores aleatórios

        for _, player in amostra.iterrows():
            nome = player["PLAYER"]
            info = players.find_players_by_full_name(nome)
            if not info:
                continue

            player_id = info[0]['id']
            stats_info = get_player_stats(nome, estatistica)  # Função original que vai buscar a linha real

            if not stats_info:
                continue

            line = stats_info.get("line_used")
            if line is None:
                continue

            # Obter os logs reais (últimos 10 jogos, qualquer tipo de temporada)
            logs = PlayerGameLog(player_id=player_id).get_data_frames()[0]
            logs.columns = logs.columns.str.upper()
            recent = logs.head(10)

            if estatistica not in recent.columns:
                continue

            over_count = sum(recent[estatistica] > line)
            under_count = sum(recent[estatistica] < line)
            total = len(recent)
            acerto = round((over_count / total) * 100, 1) if total else 0
            tendencia = "Over" if over_count > under_count else "Under"

            sugestoes.append({
                "nome": nome,
                "estatistica": estatistica,
                "linha": line,
                "acerto": f"{acerto}%",
                "tendencia": tendencia
            })

    except Exception as e:
        return JsonResponse({"erro": str(e)})

    return JsonResponse({"jogadores": sugestoes})