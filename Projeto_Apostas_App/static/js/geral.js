function restoreBetsFromStorage() {
    const stored = localStorage.getItem("betList");
    if (!stored) return;
    try {
        const parsed = JSON.parse(stored);
        if (!Array.isArray(parsed)) return;
        window.betList = [];
        // Limpa o slip antes de renderizar para evitar duplicatas
        const bettingDetails = document.getElementById("bettingDetails");
        if (bettingDetails) bettingDetails.innerHTML = "";
        parsed.forEach(bet => {
            const el = document.createElement("div");
            el.classList.add("betting-slip__details");
            el.innerHTML = `
                <button class="betting-slip__details-close">
                    <img src="/static/Images/x.png" alt="Fechar" class="betting-slip__close-icon" />
                </button>
                <div class="betting-slip__image-container">
                    <img src="${bet.playerImage}" alt="${bet.playerName}" />
                </div>
                <div style="display:flex; flex-direction:column;">
                    <h2 class="betting-slip__player">${bet.playerName}</h2>
                    <h3 class="betting-slip__bet">${bet.betType}</h3>
                    <p class="betting-slip__game">${bet.homeTeam} vs ${bet.awayTeam} • ${bet.gameDate}</p>
                    <span class="betting-slip__odds">Odd: ${parseFloat(bet.odd).toFixed(2)}</span>
                </div>`;
            el.querySelector(".betting-slip__details-close").addEventListener("click", () => {
                el.remove();
                window.betList = window.betList.filter(b => !(b.playerName === bet.playerName && b.betType === bet.betType));
                localStorage.setItem("betList", JSON.stringify(window.betList));
                document.querySelector(".count-badge").textContent = window.betList.length;
                updateWinnings();
            });
            document.getElementById("bettingDetails")?.appendChild(el);
            window.betList.push(bet);
        });
        document.querySelector(".count-badge").textContent = window.betList.length;
        updateWinnings();
    } catch (e) {
        console.error("Erro ao restaurar apostas:", e);
    }
}

// Exibe uma notificação rápida
function showNotification(message, type = "success") {
    console.log("🔔 Notificação:", message, type);
    const notification = document.createElement("div");
    notification.classList.add("bet-notification", type); 
    notification.textContent = message; 

    document.body.appendChild(notification);

    // ⏳ Remove notificação depois de 2 segundos
    setTimeout(() => {
        notification.classList.add("fade-out");
        setTimeout(() => notification.remove(), 500);
    }, 2000);
}

// Inicializa a aplicação assim que o DOM carregar
document.addEventListener('DOMContentLoaded', () => {
    // 🔗 Liga botões principais às respetivas funções
    elements.betButton?.addEventListener('click', fetchNextGame);
    elements.overBtn?.addEventListener('click', () => selectBetType('Over'));
    elements.underBtn?.addEventListener('click', () => selectBetType('Under'));

    selectBetType('Over'); // Seleção padrão: 'Over'
    console.log("Aplicação inicializada com sucesso");
    
});


document.addEventListener("DOMContentLoaded", () => {
    const betInput = document.querySelector("#betAmount");
    if (betInput && !betInput.value) {
        betInput.value = "10";  // valor padrão visível + funcional
    }
    const notification = document.querySelector('.bet-notification');   

    if (notification) {
        setTimeout(() => {
            notification.classList.add('fade-out'); // Aplica fade-out
            setTimeout(() => {
                notification.remove(); // Remove elemento após fade
            }, 500);
        }, 3000); // Espera 3 segundos antes de desaparecer
    }
    restoreBetsFromStorage();
    initializeBettingFunctions();
    updateWinnings();
});

