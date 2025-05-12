document.addEventListener("DOMContentLoaded", function () {
    const sidebar = document.getElementById("mySidebar");
    const mainContent = document.querySelector(".main-content");

    // Expande ao passar o rato
    sidebar.addEventListener("mouseenter", () => {
        sidebar.classList.add("expanded");
        mainContent.style.paddingLeft = "270px";
    });

    // Recolhe ao sair o rato
    sidebar.addEventListener("mouseleave", () => {
        sidebar.classList.remove("expanded");
        mainContent.style.paddingLeft = "120px";
    });
});