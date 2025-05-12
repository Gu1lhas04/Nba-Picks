// Inicializar 'sortOrder' para ambas as equipes (decrescente por padrão)
let sortOrder = {
    away: [false, false, false, false, false, false, false],  // Controla a ordem da equipe visitante
    home: [false, false, false, false, false, false, false]   // Controla a ordem da equipe da casa
};

// Função de ordenação
function sortTable(colIndex, tableId) {
    const table = document.getElementById(tableId);
    const rows = Array.from(table.rows).slice(1);  // Ignora o cabeçalho da tabela
    const isNumeric = colIndex !== 0;  // As colunas de "Nome" não são numéricas
    const headers = table.querySelectorAll("th");  // Obtém os cabeçalhos da tabela
    const team = tableId === 'away-team-table' ? 'away' : 'home';  // Identifica a equipe

    // Ordena as linhas com base na coluna
    rows.sort((rowA, rowB) => {
        const valueA = isNumeric ? parseFloat(rowA.cells[colIndex].textContent) : rowA.cells[colIndex].textContent.toLowerCase();
        const valueB = isNumeric ? parseFloat(rowB.cells[colIndex].textContent) : rowB.cells[colIndex].textContent.toLowerCase();
        return sortOrder[team][colIndex] ? valueA - valueB : valueB - valueA;
    });

    // Alterna a ordem de classificação para a próxima vez
    sortOrder[team][colIndex] = !sortOrder[team][colIndex];

    // Reorganiza as linhas na tabela
    rows.forEach(row => table.appendChild(row));  

    // Atualiza a seta de ordenação
    updateArrows(headers, colIndex, team);
}

// Função para atualizar as setas nos cabeçalhos
function updateArrows(headers, colIndex, team) {
    // Limpa as setas de todos os cabeçalhos
    headers.forEach(header => header.classList.remove("asc", "desc"));

    // Adiciona a classe correta para a seta no cabeçalho clicado
    headers[colIndex].classList.add(sortOrder[team][colIndex] ? "asc" : "desc");
}

// Inicialmente, organiza pela coluna de Pontos (índice 1) em ordem decrescente (do maior para o menor)
window.onload = () => {
    sortTable(1, 'away-team-table'); // Ordena a tabela da equipe visitante por Pontos
    sortTable(1, 'home-team-table'); // Ordena a tabela da equipe da casa por Pontos
};