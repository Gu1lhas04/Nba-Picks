// Quando o DOM estiver carregado
document.addEventListener('DOMContentLoaded', () => {

    // Lidar com abrir/fechar de múltiplas apostas
    document.querySelectorAll('.multiple-bets').forEach(multipleBet => {
        const content = multipleBet.querySelector('.multiple-bets-content');
        const arrow = multipleBet.querySelector('.arrow-icon');

        // Começa fechado
        content.style.maxHeight = "0px";

        multipleBet.addEventListener('click', function (event) {
            // Se clicar dentro de uma aposta individual, ignora
            if (event.target.closest('.bet-item')) {
                return;
            }

            if (!this.classList.contains('open')) {
                // Abre múltipla
                this.classList.add('open');
                content.style.maxHeight = content.scrollHeight + "px"; // Expande
                arrow.style.transform = "rotate(180deg)"; // Rotaciona seta
            } else {
                // Fecha múltipla
                this.classList.remove('open');
                content.style.maxHeight = "0px"; // Colapsa
                arrow.style.transform = "rotate(0deg)"; // Volta seta
            }

            event.stopPropagation(); // Evita propagação para elementos acima
        });
    });

    // Clique em uma aposta individual (bet-item) para abrir página do jogo
    document.querySelectorAll('.bet-item').forEach(item => {
        item.addEventListener('click', function (event) {
            event.stopPropagation();
            const gameId = this.getAttribute('data-game-id');
            if (gameId) {
                window.location.href = `/game-stats/${gameId}/`; // Redireciona para estatísticas do jogo
            }
        });
    });

    // Abrir e fechar o dropdown (menu de filtros, por exemplo)
    const dropdownButton = document.querySelector(".dropdown-btn");
    if (dropdownButton) {
        dropdownButton.addEventListener('click', toggleDropdown);
    }

    function toggleDropdown() {
        const dropdown = document.getElementById("dropdownMenu");
        const button = document.querySelector(".dropdown-btn");

        dropdown.classList.toggle("show"); // Mostra/Esconde dropdown
        button.classList.toggle("active"); // Altera estilo do botão

        // Fecha dropdown se clicar fora dele
        function closeDropdown(event) {
            if (!button.contains(event.target) && !dropdown.contains(event.target)) {
                dropdown.classList.remove("show");
                button.classList.remove("active");
                document.removeEventListener("click", closeDropdown);
            }
        }

        if (dropdown.classList.contains("show")) {
            document.addEventListener("click", closeDropdown);
        }
    }

    // Atualiza texto do botão + redireciona ao selecionar item no dropdown
    document.querySelectorAll(".dropdown-content a").forEach(link => {
        link.addEventListener("click", function (event) {
            event.preventDefault();
            const filtroSelecionado = this.getAttribute('href'); // URL do filtro
            const textoSelecionado = this.textContent; // Nome do filtro selecionado

            const buttonText = document.querySelector(".dropdown-btn span");
            if (buttonText) {
                buttonText.textContent = textoSelecionado; // Atualiza texto do botão
            }

            window.location.href = filtroSelecionado; // Redireciona para aplicar o filtro
        });
    });

});
