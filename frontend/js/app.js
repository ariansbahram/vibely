const API_URL = "http://127.0.0.1:8000";

const moodForm = document.getElementById("moodForm");
const moodInput = document.getElementById("moodInput");
const generateButton = document.getElementById("generateButton");

const recommendations = document.getElementById("recommendations");
const recommendationStatus = document.getElementById("recommendationStatus");
const songList = document.getElementById("songList");
const playlistPreview = document.getElementById("playlistPreview");
const playlistName = document.getElementById("playlistName");
const savePlaylistButton = document.getElementById("savePlaylist");
const playlistStatus = document.getElementById("playlistStatus");
const useSuggestedNameButton = document.getElementById("useSuggestedName");

// The songs currently shown, and the mood they were found for (used when saving)
let currentSongs = [];
let currentMood = "";
let suggestedTitle = "";   // playlist name the backend suggested for this mood

const spotifyLogin = document.getElementById("spotifyLogin");
const spotifyMessage = document.getElementById("spotifyMessage");

// Logging in leaves this page, so the songs on screen are kept here until we're back
const SAVED_STATE_KEY = "vibely:beforeLogin";

const LOGIN_MESSAGES = {
    connected: ["Connected to Spotify.", "bg-green-900 text-green-200"],
    denied: ["Spotify login was cancelled.", "bg-zinc-800 text-zinc-300"],
    error: ["Couldn't connect to Spotify. Please try again.", "bg-red-900 text-red-200"],
};


spotifyLogin.addEventListener("click", () => {
    if (currentSongs.length > 0) {
        sessionStorage.setItem(SAVED_STATE_KEY, JSON.stringify({
            mood: currentMood,
            songs: currentSongs,
            suggestedTitle,
            playlistName: playlistName.value,
        }));
    }

    window.location.href = `${API_URL}/auth/login`;
});


// When the page opens: show how a Spotify login went, bring back the songs
// from before it, and show whether the user is connected
showLoginResult();
restoreStateFromBeforeLogin();
showConnectedUser();


function showLoginResult() {
    const params = new URLSearchParams(window.location.search);
    const result = LOGIN_MESSAGES[params.get("spotify")];

    if (!result) {
        return;
    }

    const [message, classes] = result;
    spotifyMessage.textContent = message;
    spotifyMessage.className = `text-center px-6 py-3 ${classes}`;

    // Remove ?spotify=... so a refresh doesn't show the message again
    window.history.replaceState(null, "", window.location.pathname);
}


function restoreStateFromBeforeLogin() {
    const saved = sessionStorage.getItem(SAVED_STATE_KEY);
    sessionStorage.removeItem(SAVED_STATE_KEY);

    if (!saved) {
        return;
    }

    try {
        const { mood, songs, suggestedTitle: title, playlistName: name } = JSON.parse(saved);

        moodInput.value = mood;
        showResults(mood, songs, title);
        setPlaylistName(name);
    } catch {
        // Saved data is unreadable; just start fresh
    }
}


async function showConnectedUser() {
    try {
        const response = await fetch(`${API_URL}/me`, { credentials: "include" });

        if (!response.ok) {
            return;   // not logged in: keep "Connect Spotify"
        }

        const user = await response.json();
        spotifyLogin.textContent = `Connected as ${user.display_name || user.id}`;
        spotifyLogin.title = "Click to log in with a different Spotify account";
    } catch {
        // Backend not running; the mood form will report that when used
    }
}


moodForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const mood = moodInput.value.trim();

    if (!mood) {
        alert("Please describe your mood or situation.");
        return;
    }

    recommendations.classList.remove("hidden");
    playlistPreview.classList.add("hidden");
    songList.replaceChildren();
    currentSongs = [];
    showStatus("Finding songs that match your vibe...");
    generateButton.disabled = true;

    try {
        const { recommendations: songs, playlist_title: title } = await fetchRecommendations(mood);

        if (songs.length === 0) {
            showStatus("No songs matched. Try describing your mood differently.");
            return;
        }

        showResults(mood, songs, title);
    } catch (error) {
        showStatus(error.message, true);
    } finally {
        generateButton.disabled = false;
    }
});


playlistName.addEventListener("input", updateSuggestedNameButton);

useSuggestedNameButton.addEventListener("click", () => {
    setPlaylistName(suggestedTitle);
    playlistName.focus();
});


savePlaylistButton.addEventListener("click", async () => {
    // An empty box means "just use the suggestion"
    const name = playlistName.value.trim() || suggestedTitle;
    setPlaylistName(name);

    savePlaylistButton.disabled = true;
    showPlaylistStatus("Saving to Spotify...");

    try {
        const playlist = await postJson("/playlists", {
            name,
            description: `Made by Vibely for "${currentMood}"`.slice(0, 300),
            track_ids: currentSongs.map((song) => song.id),
        });

        showPlaylistSaved(playlist);
    } catch (error) {
        if (error.status === 401) {
            showPlaylistStatus("Connect Spotify first (top right), then come back and save.", true);
        } else {
            showPlaylistStatus(error.message, true);
        }
    } finally {
        savePlaylistButton.disabled = false;
    }
});


function showResults(mood, songs, title) {
    recommendations.classList.remove("hidden");
    showStatus("");
    songList.replaceChildren(...songs.map(createSongCard));

    currentSongs = songs;
    currentMood = mood;
    showPlaylistForm(title);
}


// The full reply: recommendations, playlist_title, mood_terms, ...
async function fetchRecommendations(mood) {
    return postJson("/recommendations", { mood });
}


// POST JSON to the backend and return the JSON reply.
// Throws an Error with a readable message (and the HTTP status) if it fails.
async function postJson(path, body) {
    let response;

    try {
        response = await fetch(`${API_URL}${path}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",   // sends the Spotify login cookie, if there is one
            body: JSON.stringify(body),
        });
    } catch {
        throw new Error("Can't reach the Vibely backend. Is it running on port 8000?");
    }

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        const error = new Error(getErrorMessage(data, response.status));
        error.status = response.status;
        throw error;
    }

    return data;
}


function showPlaylistForm(title) {
    suggestedTitle = title;
    playlistName.placeholder = title;
    setPlaylistName(title);
    showPlaylistStatus("");
    playlistPreview.classList.remove("hidden");
}


function setPlaylistName(name) {
    playlistName.value = name;
    updateSuggestedNameButton();
}


// "Use suggested name" only makes sense once the user has changed the name
function updateSuggestedNameButton() {
    const edited = playlistName.value.trim() !== suggestedTitle;
    useSuggestedNameButton.classList.toggle("hidden", !edited);
}


function showPlaylistStatus(message, isError = false) {
    playlistStatus.replaceChildren(message);
    playlistStatus.classList.toggle("hidden", !message);
    playlistStatus.classList.toggle("text-red-400", isError);
    playlistStatus.classList.toggle("text-zinc-400", !isError);
}


function showPlaylistSaved(playlist) {
    const link = element("a", "text-green-400 underline", "Open it in Spotify");
    link.href = playlist.spotify_url;
    link.target = "_blank";
    link.rel = "noopener";

    showPlaylistStatus(`Saved "${playlist.name}" with ${playlist.track_count} songs. `);
    playlistStatus.append(link);
}


function getErrorMessage(data, status) {
    // 422 (invalid input) gives a list of problems; other errors give one message
    if (Array.isArray(data.detail)) {
        return data.detail
            .map((problem) => problem.msg.replace(/^Value error, /, ""))
            .join(" ");
    }

    return data.detail || `Something went wrong (error ${status}).`;
}


function showStatus(message, isError = false) {
    recommendationStatus.textContent = message;
    recommendationStatus.classList.toggle("hidden", !message);
    recommendationStatus.classList.toggle("text-red-400", isError);
    recommendationStatus.classList.toggle("text-zinc-400", !isError);
}


// Small helper: create an element with classes and (optional) text.
// Text is set with textContent, so song titles can't inject HTML.
function element(tag, className, text) {
    const node = document.createElement(tag);
    node.className = className;

    if (text !== undefined) {
        node.textContent = text;
    }

    return node;
}


function createSongCard(song) {
    const card = element("div", "bg-zinc-900 rounded-xl p-4 flex items-center gap-4");

    // Album artwork, or a plain square if there is none
    if (song.album_image_url) {
        const artwork = element("img", "w-16 h-16 rounded-lg object-cover flex-shrink-0");
        artwork.src = song.album_image_url;
        artwork.alt = song.album ? `${song.album} cover` : `${song.title} cover`;
        artwork.loading = "lazy";
        card.append(artwork);
    } else {
        card.append(element("div", "w-16 h-16 rounded-lg bg-zinc-800 flex-shrink-0"));
    }

    // Title, artists and album, and the song's music attributes
    const details = element("div", "flex-1 min-w-0");
    details.append(
        element("h4", "font-semibold truncate", song.title),
        element("p", "text-zinc-400 truncate", [song.artists.join(", "), song.album].filter(Boolean).join(" · ")),
        createAttributeList(song),
    );
    card.append(details);

    // Match percentage and a link to the song on Spotify
    const side = element("div", "flex flex-col items-end gap-2 flex-shrink-0");
    side.append(element("span", "text-green-400 font-semibold", `${Math.round(song.score * 100)}% match`));

    const link = element("a", "text-sm text-zinc-300 hover:text-green-400 underline", "Open in Spotify");
    link.href = song.spotify_url;
    link.target = "_blank";
    link.rel = "noopener";
    side.append(link);

    card.append(side);
    return card;
}


function createAttributeList(song) {
    const list = element("div", "flex flex-wrap gap-2 mt-2");
    const features = song.audio_features;

    const tags = [song.genre, song.release_year];

    if (features) {
        tags.push(
            `${Math.round(features.tempo)} BPM`,
            `Energy ${percent(features.energy)}`,
            `Mood ${percent(features.valence)}`,   // valence: sad (0%) to happy (100%)
            `Acoustic ${percent(features.acousticness)}`,
            `Danceable ${percent(features.danceability)}`,
        );
    }

    if (song.explicit) {
        tags.push("Explicit");
    }

    for (const tag of tags) {
        if (tag !== null && tag !== undefined) {
            list.append(element("span", "text-xs bg-zinc-800 text-zinc-300 rounded-full px-2 py-1", String(tag)));
        }
    }

    return list;
}


function percent(value) {
    return `${Math.round(value * 100)}%`;
}
