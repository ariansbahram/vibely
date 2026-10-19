const moodForm = document.getElementById("moodForm");
const moodInput = document.getElementById("moodInput");

const recommendations = document.getElementById("recommendations");
const playlistPreview = document.getElementById("playlistPreview");

const spotifyLogin = document.getElementById("spotifyLogin");


spotifyLogin.addEventListener("click", () => {
    window.location.href = "http://127.0.0.1:8000/auth/login";
});


moodForm.addEventListener("submit", (event) => {
    event.preventDefault();

    const mood = moodInput.value.trim();

    if (!mood) {
        alert("Please describe your mood or situation.");
        return;
    }

    console.log("Mood submitted:", mood);

    // Temporary placeholders until backend recommendation endpoint exists
    recommendations.classList.remove("hidden");
    playlistPreview.classList.remove("hidden");
});