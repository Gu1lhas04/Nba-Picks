function toggleBettingSlip() {
    const bettingSlip = document.getElementById("bettingSlip");
    const overlay = document.getElementById("overlay");

    const isHidden = bettingSlip.style.display === "none" || bettingSlip.style.display === "";
    
    bettingSlip.style.display = isHidden ? "block" : "none";
    overlay.style.display = isHidden ? "block" : "none";

    if (isHidden) {
        // ⚠️ Garante que updateWinnings seja chamado depois do DOM renderizar
        setTimeout(updateWinnings, 50);
    }
}


// Alterna a exibição da área de adicionar dinheiro
function toggleAddMoney() {
    const addMoney = document.getElementById("addMoney");
    const overlay = document.getElementById("overlay");

    if (addMoney.style.display === "none" || addMoney.style.display === "") {
        addMoney.style.display = "block";
        overlay.style.display = "block";
    } else {
        addMoney.style.display = "none";
        overlay.style.display = "none";
    }
}

// Função para pesquisar jogadores via AJAX
function searchPlayers() {
    const query = document.getElementById("search-input").value;
    const resultsDiv = document.getElementById("search-results");

    if (query.length > 2) {
        fetch('/search_ajax/?query=' + query)
            .then(response => response.json())
            .then(data => {
                resultsDiv.innerHTML = "";

                if (data.jogadores.length > 0) {
                    resultsDiv.style.display = "block";
                    data.jogadores.forEach(jogador => {
                        const resultItem = document.createElement("div");
                        resultItem.textContent = jogador.full_name;
                        resultItem.setAttribute("data-player-id", jogador.id);
                        resultItem.addEventListener("click", () => {
                            window.location.href = `/player_details/${jogador.id}/`;
                        });
                        resultsDiv.appendChild(resultItem);
                    });
                } else {
                    resultsDiv.innerHTML = "<p>Nenhum jogador encontrado.</p>";
                }
            })
            .catch(error => console.log('Erro na busca:', error));
    } else {
        resultsDiv.style.display = "none";
    }
}

function updateWinnings() {
    const betSlip = document.getElementById("bettingSlip");
    const betAmountInput = betSlip.querySelector("#betAmount");
    const betContainer = betSlip.querySelector(".betting-slip__winnings");

    if (!betAmountInput || !betContainer) return;

    const amount = parseFloat(betAmountInput.value);

    if (!window.betList || window.betList.length === 0 || isNaN(amount) || amount <= 0) {
        betContainer.textContent = "Possíveis Ganhos: 0.00 €";
        return;
    }

    const totalOdds = window.betList.reduce((acc, bet) => {
        const parsedOdd = parseFloat(bet.odd);
        return isNaN(parsedOdd) ? acc : acc * parsedOdd;
    }, 1);

    const winnings = (amount * totalOdds).toFixed(2);
    betContainer.textContent = `Possíveis Ganhos: ${winnings} €`;
}

function initializeBettingFunctions() {
    const betButtons = document.querySelectorAll(".bet-button");
    const betAmountInput = document.querySelector("#betAmount");
    const betCountElement = document.querySelector(".count-badge");

    window.betList = JSON.parse(localStorage.getItem("betList")) || [];
    updateBetCount();
    updateWinnings();

    function showNotification(message, type = "success") {
        const notification = document.createElement("div");
        notification.classList.add("bet-notification", type);
        notification.textContent = message;
        document.body.appendChild(notification);
        setTimeout(() => {
            notification.classList.add("fade-out");
            setTimeout(() => notification.remove(), 500);
        }, 2000);
    }

    function updateBetCount() {
        if (betCountElement) {
            betCountElement.textContent = window.betList.length;
        }
    }

    if (betAmountInput) {
        betAmountInput.addEventListener("input", updateWinnings);
    }

    betButtons.forEach(button => {
        button.addEventListener("click", () => {
            const betCard = button.closest(".bet-card");
            const playerName = button.dataset.player;
            const betType = `${button.dataset.tipo} ${button.dataset.linha} ${button.dataset.stat}`;
            const betOdd = parseFloat(button.dataset.odd);
            const gameDate = button.dataset.data;
            const [awayTeam, homeTeam] = button.dataset.jogo.split(" vs ").map(e => e.trim());
            const playerImage = `https://cdn.nba.com/headshots/nba/latest/260x190/${button.dataset.playerId}.png`;
            const gameId = button.dataset.gameId;

            const existingBet = window.betList.find(bet => bet.playerName === playerName && bet.betType === betType);
            if (existingBet) {
                showNotification("⚠️ Aposta já adicionada!", "error");
                return;
            }

            const bet = {
                playerName,
                betType,
                odd: betOdd,
                gameDate,
                homeTeam,
                awayTeam,
                playerImage,
                gameId
            };

            window.betList.push(bet);
            localStorage.setItem("betList", JSON.stringify(window.betList));
            updateBetCount();
            updateWinnings();
            showNotification("✅ Aposta adicionada!");
            restoreBetsFromStorage();
        });
    });
}



// Finaliza a aposta (envia o formulário)
window.finalizeBet = function finalizeBet() {
    const betSlip = document.getElementById("bettingSlip");
    const betAmountInput = betSlip.querySelector("#betAmount");

    const betAmount = parseFloat(betAmountInput.value);
    if (betAmount <= 0 || window.betList.length === 0) {
        showNotification("⚠️ Por favor, adicione apostas e um valor válido", "error");
        return;
    }

    console.table(window.betList);

    // Monta dados a serem enviados
    const apostasData = window.betList.map(bet => ({
        playerName: bet.playerName,
        betType: bet.betType,
        odd: bet.odd,
        gameId: bet.gameId,
        gameDate: bet.gameDate,
        homeTeam: bet.homeTeam,
        awayTeam: bet.awayTeam,
        playerImage: bet.playerImage
    }));

    console.log("🟢 Enviando apostas para o backend:", apostasData);

    document.getElementById("apostasDataInput").value = JSON.stringify(apostasData);
    document.getElementById("valorApostadoInput").value = betAmount;
    document.getElementById("betForm").submit();
    setTimeout(() => {
        window.location.href = '/';
    }, 1000);

    // Limpa tudo após envio
    window.betList = [];
    betAmountInput.value = '10';
    document.querySelector(".count-badge").textContent = '0';
    localStorage.removeItem("betList");
    updateWinnings();
};
