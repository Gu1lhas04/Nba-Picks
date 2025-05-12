function toggleDropdown(element) {
    let gameCard = element.closest(".game-card"); // Encontra o card do jogo
    gameCard.classList.toggle("expanded"); // Alterna a classe 'expanded'
  }
  