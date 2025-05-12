// ✅ best_bets.js
if (document.body.dataset.bestbets === "true") {
    document.querySelectorAll('.bet-button').forEach(btn => {
        btn.addEventListener('click', () => {
            const playerName = btn.dataset.player;
            const betType = `${btn.dataset.tipo} ${btn.dataset.linha} ${btn.dataset.stat}`;
            const odd = parseFloat(btn.dataset.odd);
            const match = btn.dataset.jogo;
            const gameDate = btn.dataset.data;
            const playerId = btn.dataset.playerId;
            const gameId = btn.dataset.gameId;
            const playerImage = `https://cdn.nba.com/headshots/nba/latest/260x190/${playerId}.png`;
            const [awayTeam, homeTeam] = match.split(" vs ").map(s => s.trim());
            if (!window.betList) window.betList = JSON.parse(localStorage.getItem("betList") || "[]");
            if (window.betList.some(b => b.playerName === playerName && b.betType === betType)) {
                alert("⚠️ Aposta já adicionada.");
                return;
            }
            const bet = { playerName, betType, odd, gameDate, awayTeam, homeTeam, playerImage, gameId };
            const el = document.createElement("div");
            el.classList.add("betting-slip__details");
            el.innerHTML = `
                <button class="betting-slip__details-close">
                    <img src="/static/Images/x.png" alt="Close" class="betting-slip__close-icon" />
                </button>
                <div class="betting-slip__image-container">
                    <img src="${playerImage}" alt="${playerName}" />
                </div>
                <div class="betting-slip__info-container">
                    <h2 class="betting-slip__player">${playerName}</h2>
                    <h3 class="betting-slip__bet">${betType}</h3>
                    <p class="betting-slip__game">${match} • ${gameDate}</p>
                    <span class="betting-slip__odds">Odd: ${odd.toFixed(2)}</span>
                </div>`;
            el.querySelector(".betting-slip__details-close").addEventListener("click", () => {
                el.remove();
                window.betList = window.betList.filter(b => !(b.playerName === playerName && b.betType === betType));
                localStorage.setItem("betList", JSON.stringify(window.betList));
                document.querySelector(".count-badge").textContent = window.betList.length;
                updateWinnings();
            });
            document.getElementById("bettingDetails").appendChild(el);
            window.betList.push(bet);
            localStorage.setItem("betList", JSON.stringify(window.betList));
            document.querySelector(".count-badge").textContent = window.betList.length;
            updateWinnings();
        });
    });
}
