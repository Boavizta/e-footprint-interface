document.addEventListener("htmx:beforeRequest", function() {
    let progressBar = document.querySelector("#loading-bar .progress-bar");
    if (progressBar) {
        progressBar.style.animation = "loadingMove 0.5s infinite linear";
    }
});

document.addEventListener("htmx:afterRequest", function() {
    hideLoadingBar();
    updateLines();
});

function hideLoadingBar() {
    let progressBar = document.querySelector("#loading-bar .progress-bar");
    progressBar.style.animation = "none";
    progressBar.style.width = "0%";
}
