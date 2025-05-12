// Função para abrir/fechar o relatório de lesões
function toggleInjuryReport() {
    var injuryReport = document.getElementById("InjuryReport");
    var overlay = document.getElementById("overlay");

    if (injuryReport.style.display === "none" || injuryReport.style.display === "") {
        injuryReport.style.display = "block";
        overlay.style.display = "block";
    } else {
        injuryReport.style.display = "none";
        overlay.style.display = "none";
    }
}

// Atualiza o texto do botão dropdown sem fechar o menu
document.querySelectorAll(".dropdown-content a").forEach(option => {
    option.addEventListener("click", function (event) {
        event.stopPropagation(); // Impede o dropdown de fechar
        let buttonText = document.querySelector(".dropdown-btn span");
        buttonText.textContent = this.textContent; // Atualiza apenas o texto
    });
});

// Função para obter o CSRF token (para requisições POST seguras)
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Verifica se o cookie tem o nome desejado
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Função para selecionar/deselecionar um jogador no relatório
function toggleSelection(playerElement) {
    const playerName = playerElement.querySelector(".player-name").innerText;
    const status = playerElement.querySelector(".status").innerText;
    const isSelected = playerElement.classList.contains("selected");

    if (isSelected) {
        playerElement.classList.remove("selected"); // Deseleciona jogador
    } else {
        playerElement.classList.add("selected"); // Seleciona jogador
    }

    updateSelectedCount(); // Atualiza o contador de jogadores selecionados
}

// Atualiza a contagem e o texto conforme jogadores selecionados
function updateSelectedCount() {
    const selectedPlayers = document.querySelectorAll('.player-item.selected');
    const selectedCountElement = document.getElementById("selectedCount");
    const btnText = document.getElementById("btnText");

    const newCount = selectedPlayers.length;
    selectedCountElement.innerText = `Selected Players: ${newCount}`;

    // Atualiza o botão com o último jogador selecionado
    if (newCount === 0) {
        btnText.innerText = "Stats without Player";
    } else {
        const lastSelectedPlayer = selectedPlayers[selectedPlayers.length - 1];
        const playerName = lastSelectedPlayer.querySelector(".player-name").innerText;
        btnText.innerText = `${playerName}`;
    }

    sendSelectedPlayersToBackend(); // Envia info para o backend
}

// Atualiza o botão ao selecionar jogador (dropdown "stats without player")
document.querySelectorAll(".stats-without a").forEach(option => {
    option.addEventListener("click", function (event) {
        event.stopPropagation();

        let buttonText = document.querySelector(".stats-without-btn span");
        buttonText.textContent = this.querySelector(".player-name").textContent;
    });
});

// Função para abrir/fechar qualquer dropdown (por ID)
function toggleDropdown(dropdownId) {
    const dropdown = document.getElementById(dropdownId);
    const icon = dropdown.previousElementSibling.querySelector('img');

    if (dropdown.classList.contains('show')) {
        dropdown.classList.remove('show');
        icon.style.transform = 'rotate(0deg)'; // Volta seta para cima
    } else {
        dropdown.classList.add('show');
        icon.style.transform = 'rotate(180deg)'; // Roda seta para baixo
    }
}

// Função para selecionar 'Over' ou 'Under'
function selectOption(option) {
    const overBtn = document.getElementById('overBtn');
    const underBtn = document.getElementById('underBtn');

    if (option === 'Over') {
        overBtn.classList.add('selected');
        underBtn.classList.remove('selected');
        document.getElementById('selectedOption').innerText = "Selected: Over";
    } else {
        underBtn.classList.add('selected');
        overBtn.classList.remove('selected');
        document.getElementById('selectedOption').innerText = "Selected: Under";
    }
}

// Define opção 'Over' ou 'Under' ao escolher linha do dropdown
function setLineOption(option) {
    const overBtn = document.getElementById('overBtn');
    const underBtn = document.getElementById('underBtn');

    if (option === 'Over') {
        overBtn.classList.add('selected');
        underBtn.classList.remove('selected');
        document.getElementById('selectedOption').innerText = "Selected: Over";
    } else {
        underBtn.classList.add('selected');
        overBtn.classList.remove('selected');
        document.getElementById('selectedOption').innerText = "Selected: Under";
    }

    // Fecha dropdown após escolher
    const customLinesDropdown = document.getElementById('customLinesDropdown');
    customLinesDropdown.classList.remove('show');
    customLinesDropdown.previousElementSibling.querySelector('img').style.transform = 'rotate(0deg)';
}
