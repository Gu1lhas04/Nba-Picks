// Função para atualizar a pré-visualização da imagem de perfil ao selecionar um arquivo
document.getElementById("fileInput").addEventListener("change", function(event) {
    // Obtém o primeiro ficheiro selecionado pelo utilizador
    const file = event.target.files[0];

    if (file) {
        // Cria um FileReader para ler o conteúdo do ficheiro
        const reader = new FileReader();

        // Quando o ficheiro estiver carregado...
        reader.onload = function(e) {
            // Atualiza a imagem de pré-visualização com o conteúdo do ficheiro
            document.getElementById("profilePreview").src = e.target.result;
        };

        // Lê o ficheiro como uma URL (base64) para poder exibir no src da imagem
        reader.readAsDataURL(file);
    }
});
