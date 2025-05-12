// 1. Elementos principais do DOM
const elements = {
    nextGameInfo: document.getElementById('nextGameInfo'),
    confirmBetModal: document.getElementById('confirmBetModal'),
    overlay: document.getElementById('overlay'),
    confirmBetType: document.getElementById('confirmBetType'),
    betButton: document.querySelector('.bet-btn'),
    overBtn: document.getElementById('overBtn'),
    underBtn: document.getElementById('underBtn')
};

// 2. Estado da aplicação
let playerBets = [];
let selectedBetType = 'Over';

// 3. Buscar próximo jogo do jogador
async function fetchNextGame() {
    console.log('Iniciando busca pelo próximo jogo...');

    if (!window.playerData || !window.playerData.fullName) {
        console.error('❌ Dados do jogador não disponíveis');
        return;
    }

    try {
        const response = await fetch(`/get_next_game/?player_name=${encodeURIComponent(window.playerData.fullName)}`);
        const data = await response.json();

        if (data.status === 'success' && data.next_game.available) {
            console.log("📦 Dados do jogo recebidos:", data.next_game);

            // Atualiza playerData com dados do próximo jogo
            window.playerData.personId = data.next_game?.person_id || null;
            window.playerData.nextGame = {
                gameId: data.next_game?.game_id || null,
                gameDate: data.next_game?.game_date || null,
                gameTime: data.next_game?.game_time || null,
                homeTeam: data.next_game?.home_team || null,
                awayTeam: data.next_game?.away_team || null,
                homeTeamLogo: data.next_game?.home_team_logo || null,
                awayTeamLogo: data.next_game?.away_team_logo || null
            };

            openConfirmBetModal(); // Abre modal para confirmar aposta
        } else {
            showNotification(data.message || "❌ Erro ao buscar o próximo jogo", "error");
        }
    } catch (error) {
        console.error('❌ Erro ao buscar próximo jogo:', error);
        showNotification('❌ Erro ao buscar o próximo jogo', "error");
    }
}

// 4. Abre o modal de confirmação da aposta
function openConfirmBetModal() {
    console.log("🟢 openConfirmBetModal chamado");

    const selectedBet = document.querySelector('.selection-btn.selected');
    const thresholdInput = document.getElementById("customLineInput");
    const oddInput = document.getElementById("amount");
    const betTypeDisplay = document.getElementById("confirmBetType");
    const oddDisplay = document.getElementById("confirmBetOdd");

    if (!selectedBet || !thresholdInput || !oddInput || !betTypeDisplay || !oddDisplay) {
        console.warn("⚠️ Elementos do modal não encontrados.");
        alert("Erro ao abrir modal. Verifique os elementos.");
        return;
    }

    const inputThreshold = parseFloat(thresholdInput.value);
    const odd = parseFloat(oddInput.value).toFixed(2);
    const statType = window.playerData?.statType || 'PTS';
    const betType = selectedBet.textContent.trim();

    if (isNaN(inputThreshold) || isNaN(odd)) {
        alert("⚠️ Threshold ou odd inválidos.");
        return;
    }

    // Atualiza dados do modal
    betTypeDisplay.textContent = `${betType} ${inputThreshold} ${statType}`;
    oddDisplay.textContent = odd;

    elements.confirmBetModal.style.display = "block";
    elements.overlay.style.display = "block";

    console.log("✅ Modal exibido com:", { betType, statType, inputThreshold, odd });
}

// 5. Atualiza informações do próximo jogo no frontend
document.addEventListener('DOMContentLoaded', () => {
    const homeTeamLogo = document.getElementById('homeTeamLogo');
    const awayTeamLogo = document.getElementById('awayTeamLogo');
    const gameDateElement = document.getElementById('gameDate');
    const gameTimeElement = document.getElementById('gameTime');

    if (homeTeamLogo && awayTeamLogo && gameDateElement && gameTimeElement) {
        fetch(`/get_next_game/?player_name=${encodeURIComponent(window.playerData.fullName)}`)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success' && data.next_game) {
                    homeTeamLogo.src = data.next_game.home_team_logo;
                    awayTeamLogo.src = data.next_game.away_team_logo;
                    gameDateElement.textContent = `${data.next_game.game_date}`;
                    gameTimeElement.textContent = `${data.next_game.game_time}`;
                } else {
                    gameDateElement.textContent = 'Nenhum jogo disponível';
                    gameTimeElement.textContent = '';
                }
            })
            .catch(error => {
                console.error('Erro ao buscar jogo:', error);
                gameDateElement.textContent = 'Erro ao carregar';
                gameTimeElement.textContent = '';
            });
    }
});

// 6. Fecha o modal de confirmação
function closeConfirmBetModal() {
    if (elements.confirmBetModal) elements.confirmBetModal.style.display = 'none';
    if (elements.overlay) elements.overlay.style.display = 'none';
}

// 7. Adiciona aposta ao slip
function addPlayerBetToSlip() {
    const playerName = window.playerData.fullName;
    const statType = window.playerData.statType;
    const inputThreshold = parseFloat(document.getElementById("customLineInput").value);
    const odd = parseFloat(document.getElementById("amount").value);
    const betType = selectedBetType;
    const betText = `${betType} ${inputThreshold} ${statType}`;

    if (!window.betList) window.betList = [];

    // Verifica se já existe aposta igual
    const existingBet = window.betList.find(
        bet => bet.playerName === playerName && bet.betType === betText
    );
    if (existingBet) {
        showNotification("⚠️ Aposta já adicionada!", "error");
        return;
    }

    const nextGame = window.playerData.nextGame || {};
    let personId = window.playerData.personId;

    // Se não tiver personId, tenta pegar da imagem
    if (!personId) {
        const playerImageElement = document.querySelector('#confirmBetModal img');
        if (playerImageElement) {
            const src = playerImageElement.src;
            const match = src.match(/\/(\d+)\.png$/);
            if (match && match[1]) {
                personId = match[1];
                console.log(`✅ personId capturado: ${personId}`);
            }
        }
    }

    const playerImage = personId
        ? `https://cdn.nba.com/headshots/nba/latest/260x190/${personId}.png`
        : '/static/Images/default_player.png';

    // Cria visualmente a aposta no slip
    const newBet = document.createElement("div");
    newBet.classList.add("betting-slip__details");
    newBet.innerHTML = `
        <button class="betting-slip__details-close">
            <img src="/static/Images/x.png" alt="Close" class="betting-slip__close-icon" />
        </button>
        <div class="betting-slip__image-container">
            <img src="${playerImage}" alt="${playerName}" onerror="this.onerror=null;this.src='/static/Images/default_player.png';" />
        </div>
        <div class="betting-slip__info-container">
            <h2 class="betting-slip__player">${playerName}</h2>
            <h3 class="betting-slip__bet">${betText}</h3>
            <p class="betting-slip__game">${nextGame.homeTeam || ''} vs ${nextGame.awayTeam || ''} • ${nextGame.gameDate || ''}</p>
            <span class="betting-slip__odds">Odd: ${odd.toFixed(2)}</span>
        </div>
    `;

    document.getElementById("bettingDetails")?.appendChild(newBet);

    const betData = {
        playerName,
        betType: betText,
        odd,
        gameId: nextGame.gameId,
        gameDate: nextGame.gameDate,
        homeTeam: nextGame.homeTeam,
        awayTeam: nextGame.awayTeam,
        playerImage: playerImage
    };

    window.betList.push(betData);
    localStorage.setItem("betList", JSON.stringify(window.betList));

    document.querySelector(".count-badge").textContent = window.betList.length;

    // Evento para remover aposta do slip
    newBet.querySelector(".betting-slip__details-close").addEventListener("click", function () {
        window.betList = window.betList.filter(bet =>
            !(bet.playerName === betData.playerName && bet.betType === betData.betType)
        );

        if (window.betList.length > 0) {
            localStorage.setItem("betList", JSON.stringify(window.betList));
        } else {
            localStorage.removeItem("betList");
        }

        newBet.remove();
        document.querySelector(".count-badge").textContent = window.betList.length;
        
        if (typeof updateWinnings === "function") updateWinnings();
        
        showNotification("❌ Aposta removida!", "error");
    });

    if (typeof updateWinnings === "function") updateWinnings();

    showNotification("✅ Aposta adicionada!", "success");
    closeConfirmBetModal();
}

// 8. Inicialização principal
document.addEventListener('DOMContentLoaded', () => {
    elements.betButton?.addEventListener('click', fetchNextGame);
    elements.overBtn?.addEventListener('click', () => selectBetType('Over'));
    elements.underBtn?.addEventListener('click', () => selectBetType('Under'));

    selectBetType('Over'); // Default
    console.log("Aplicação inicializada com sucesso");
});

// 9. Define aposta como Over ou Under
window.selectBetType = function (type) {
    selectedBetType = type;
    elements.overBtn?.classList.remove('selected');
    elements.underBtn?.classList.remove('selected');
    document.getElementById(`${type.toLowerCase()}Btn`)?.classList.add('selected');
};

// 10. Função para alterar o threshold da aposta
function changeThreshold(delta) {
    const input = document.getElementById('customLineInput');
    let current = parseFloat(input.value);
    if (isNaN(current)) current = 0;
    input.value = (current + delta).toFixed(1);
}
