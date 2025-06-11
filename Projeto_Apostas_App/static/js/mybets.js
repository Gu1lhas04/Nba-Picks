// Alterna a expansão de uma aposta múltipla
function toggleBet(event) {
    const card = event.currentTarget;
    console.log("Clique no card múltiplo", card);

    card.classList.toggle("expanded");
}




// Alterna abertura/fecho do menu dropdown
function toggleDropdown() {
    var dropdown = document.getElementById("dropdownMenu");
    var button = document.querySelector(".dropdown-btn");

    if (dropdown.style.display === "block") {
        dropdown.style.display = "none";
        button.classList.remove("active");
    } else {
        dropdown.style.display = "block";
        button.classList.add("active");
    }
}

// Atualiza texto do botão ao selecionar uma opção do dropdown
document.querySelectorAll(".dropdown-content a").forEach(option => {
    option.addEventListener("click", function(event) {
        event.stopPropagation();
        let buttonText = document.querySelector(".dropdown-btn span");
        buttonText.textContent = this.textContent; // Atualiza só o texto, mantém a seta
        document.getElementById("dropdownMenu").style.display = "none"; // Fecha o menu
        document.querySelector(".dropdown-btn").classList.remove("active");
    });
});
