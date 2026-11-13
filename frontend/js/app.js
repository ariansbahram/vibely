import * as vibeAi from "./vibe-ai.js";

const API_URL = "http://127.0.0.1:8000";

const moodForm = document.getElementById("moodForm");
const moodInput = document.getElementById("moodInput");
const generateButton = document.getElementById("generateButton");
const generateSpinner = document.getElementById("generateSpinner");
const generateLabel = document.getElementById("generateLabel");
const moodError = document.getElementById("moodError");
const moodCounter = document.getElementById("moodCounter");
const moodTermsLine = document.getElementById("moodTerms");

const progressCard = document.getElementById("progressCard");
const progressSteps = document.getElementById("progressSteps");
const progressTime = document.getElementById("progressTime");
const progressHint = document.getElementById("progressHint");
const cancelGenerateButton = document.getElementById("cancelGenerate");
const songSkeletons = document.getElementById("songSkeletons");

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
let currentMoodTerms = [];
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
            moodTerms: currentMoodTerms,
            suggestedTitle,
            playlistName: playlistName.value,
            playlistIds: playlistTracks.map((song) => song.id),
            orderMode,
            onPlaylistPage: isPlaylistPageOpen(),
            vibe: currentVibe,
            addedSongs,
            excludedIds: [...excludedIds],
        }));
    }

    window.location.href = `${API_URL}/auth/login`;
});


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
        const {
            mood, songs, moodTerms, suggestedTitle: title, playlistName: name,
            playlistIds, orderMode: savedOrder, onPlaylistPage,
            vibe: savedVibe, addedSongs: added, excludedIds: excluded,
        } = JSON.parse(saved);

        moodInput.value = mood;
        updateCounter();
        showResults(mood, songs, title, moodTerms, undefined, savedVibe);
        setPlaylistName(name);

        // Bring back the playlist page as it was: same songs, same order
        if (playlistIds) {
            addedSongs = added || [];
            excludedIds = new Set(excluded || []);
            const pool = getSongPool();
            playlistTracks = playlistIds.map((id) => pool.find((song) => song.id === id)).filter(Boolean);
            orderMode = savedOrder || "custom";
            renderPlaylist();
        }

        if (onPlaylistPage) {
            window.location.hash = "playlist";
        }
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


// ---------- Mood form ----------

// Same limits the backend checks (RecommendationRequest in models/recommendation.py)
const MOOD_MIN_LENGTH = 3;
const MOOD_MAX_LENGTH = 500;

// Show a "running out of room" color once this much of the limit is used
const COUNTER_WARNING_AT = 450;

// Give up waiting for recommendations after this long (the first request after
// starting the backend takes a few seconds while the song dataset loads)
const REQUEST_TIMEOUT_MS = 60000;

// Errors show while typing only after the user has tried to submit once,
// so they aren't told off for an unfinished sentence
let showErrorsWhileTyping = false;

let isGenerating = false;


moodInput.addEventListener("input", () => {
    updateCounter();

    if (showErrorsWhileTyping) {
        showMoodError(validateMood(moodInput.value));
    }
});


// Cmd+Enter (Mac) or Ctrl+Enter submits; plain Enter still starts a new line
moodInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        moodForm.requestSubmit();
    }
});


document.querySelectorAll(".mood-example").forEach((button) => {
    button.addEventListener("click", () => {
        moodInput.value = button.textContent.trim();
        updateCounter();
        showMoodError(null);
        moodInput.focus();
    });
});


moodForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (isGenerating) {
        return;   // a request is already running
    }

    const mood = cleanMood(moodInput.value);
    const problem = validateMood(mood);

    if (problem) {
        showErrorsWhileTyping = true;
        showMoodError(problem);
        moodInput.focus();
        return;
    }

    moodInput.value = mood;   // show the cleaned-up text that is actually sent
    updateCounter();
    showMoodError(null);
    setGenerating(true);

    const usingAi = smartMoodReady;
    const run = startProgress(usingAi ? ["mood", "songs"] : ["songs"]);

    try {
        let vibe = null;

        if (usingAi) {
            setProgressStep("mood");
            generateLabel.textContent = "Understanding your vibe...";
            vibe = await readVibe(mood);
            throwIfCancelled(run);
        }

        setProgressStep("songs");
        generateLabel.textContent = "Finding songs...";
        const data = await fetchRecommendations(mood, vibe, run.controller.signal);

        stopProgress();
        showErrorsWhileTyping = false;

        if (data.recommendations.length === 0) {
            showNoMatches(data.mood_terms, data.notes);
            return;
        }

        showResults(
            mood, data.recommendations, data.playlist_title, data.mood_terms, data.understood_by,
            // The backend may have answered without the AI's reading (if it rejected it)
            data.understood_by === "ai" ? vibe : null, data.notes,
        );
        recommendations.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) {
        stopProgress();

        // Cancelled on purpose: just go back to how things were, no error message
        if (!error.cancelled) {
            showMoodError(error.message);
        }

        moodInput.focus();
    } finally {
        setGenerating(false);
    }
});


cancelGenerateButton.addEventListener("click", () => {
    if (!progress) {
        return;
    }

    progress.cancelled = true;
    progress.controller.abort();       // stops the request to the backend
    vibeAi.cancelInterpretation();     // stops the AI if it's still reading the mood
});


function throwIfCancelled(run) {
    if (run.cancelled) {
        const error = new Error("Cancelled");
        error.cancelled = true;
        throw error;
    }
}


// ---------- Progress while a mood is processed ----------

const PROGRESS_STEPS = {
    mood: "Understanding your mood (smart mood understanding)",
    songs: "Finding songs that match",
};

// Shown under the steps when one runs long: [seconds into the step, message]
const PROGRESS_HINTS = {
    mood: [
        [10, "Smart mood understanding can take 10–20 seconds on older computers. Turning it off (under the mood box) makes this step instant."],
    ],
    songs: [
        [5, "This can take a few more seconds when Vibely looks up a song or artist online, or right after the backend starts."],
        [25, "This is taking longer than usual. Vibely will stop waiting after a minute."],
    ],
};

const SKELETON_CARDS = 3;

// The run in progress: { steps, current, startedAt, stepStartedAt, timer, controller, cancelled, hadResults }
let progress = null;


function startProgress(steps) {
    progress = {
        steps,
        current: null,
        startedAt: Date.now(),
        stepStartedAt: Date.now(),
        timer: setInterval(updateProgressTime, 1000),
        controller: new AbortController(),
        cancelled: false,
        hadResults: currentSongs.length > 0,
    };

    progressSteps.replaceChildren(...steps.map((name) => {
        const step = element("li", "progress-step");
        step.dataset.step = name;
        step.dataset.status = "pending";
        step.append(element("span", "step-icon"), element("span", "", PROGRESS_STEPS[name]));
        return step;
    }));

    progressTime.textContent = "0s";
    progressHint.classList.add("hidden");
    recommendationStatus.classList.add("hidden");
    recommendations.classList.remove("hidden");
    progressCard.classList.remove("hidden");

    if (progress.hadResults) {
        // Keep the previous songs visible but faded until the new ones arrive
        setStale(true);
    } else {
        songSkeletons.replaceChildren(...Array.from({ length: SKELETON_CARDS }, createSkeletonCard));
        songSkeletons.classList.remove("hidden");
    }

    progressCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
    return progress;
}


function setProgressStep(name) {
    for (const step of progressSteps.children) {
        const index = progress.steps.indexOf(step.dataset.step);
        const currentIndex = progress.steps.indexOf(name);
        step.dataset.status = index < currentIndex ? "done" : index === currentIndex ? "active" : "pending";

        // Screen readers only hear the step that's running
        step.setAttribute("aria-hidden", String(index !== currentIndex));
    }

    progress.current = name;
    progress.stepStartedAt = Date.now();
    progressHint.classList.add("hidden");
}


function updateProgressTime() {
    if (!progress) {
        return;
    }

    const now = Date.now();
    progressTime.textContent = `${Math.floor((now - progress.startedAt) / 1000)}s`;

    // The latest hint whose time has come for the current step
    const stepSeconds = (now - progress.stepStartedAt) / 1000;
    const hint = (PROGRESS_HINTS[progress.current] || [])
        .filter(([seconds]) => stepSeconds >= seconds)
        .at(-1);

    if (hint) {
        progressHint.textContent = hint[1];
        progressHint.classList.remove("hidden");
    }
}


// Hide the progress card and placeholders. If nothing new is shown (error or
// cancel), the previous results come back, or the section hides if there were none.
function stopProgress() {
    if (!progress) {
        return;
    }

    clearInterval(progress.timer);
    progressCard.classList.add("hidden");
    songSkeletons.classList.add("hidden");
    songSkeletons.replaceChildren();
    setStale(false);

    if (!progress.hadResults) {
        recommendations.classList.add("hidden");
    }

    progress = null;
}


function setStale(stale) {
    for (const part of [songList, moodTermsLine, playlistPreview]) {
        part.classList.toggle("is-stale", stale);
        part.toggleAttribute("aria-hidden", stale);
    }
}


function createSkeletonCard() {
    const card = element("div", "bg-zinc-900 rounded-xl p-4 flex items-center gap-4 animate-pulse motion-reduce:animate-none");
    const lines = element("div", "flex-1 space-y-2");
    lines.append(
        element("div", "h-4 bg-zinc-800 rounded w-1/2"),
        element("div", "h-3 bg-zinc-800 rounded w-1/3"),
        element("div", "h-3 bg-zinc-800 rounded w-3/4"),
    );
    card.append(element("div", "w-16 h-16 rounded-lg bg-zinc-800 flex-shrink-0"), lines);
    return card;
}


// Trim and collapse repeated spaces and line breaks, as the backend does
function cleanMood(text) {
    return text.trim().split(/\s+/).join(" ");
}


// Returns a message saying what's wrong, or null if the mood can be sent
function validateMood(text) {
    const mood = cleanMood(text);

    if (mood.length === 0) {
        return "Describe your mood or situation first.";
    }

    if (mood.length < MOOD_MIN_LENGTH) {
        return `Add a bit more detail (at least ${MOOD_MIN_LENGTH} characters).`;
    }

    if (mood.length > MOOD_MAX_LENGTH) {
        return `Keep it under ${MOOD_MAX_LENGTH} characters (it's ${mood.length} now).`;
    }

    if (!/\p{L}/u.test(mood)) {
        return "Use words to describe your mood, not just numbers or symbols.";
    }

    return null;
}


function showMoodError(message) {
    moodError.textContent = message || "";
    moodInput.setAttribute("aria-invalid", message ? "true" : "false");
}


function updateCounter() {
    const length = moodInput.value.length;

    moodCounter.textContent = `${length} / ${MOOD_MAX_LENGTH}`;
    moodCounter.classList.toggle("text-amber-400", length >= COUNTER_WARNING_AT);
    moodCounter.classList.toggle("text-zinc-500", length < COUNTER_WARNING_AT);
}


function setGenerating(generating) {
    isGenerating = generating;

    generateButton.disabled = generating;
    updateSaveButton();   // off while the songs are about to change
    moodInput.readOnly = generating;
    generateSpinner.classList.toggle("hidden", !generating);
    generateLabel.textContent = generating ? "Finding songs..." : "Generate Playlist";
    moodForm.setAttribute("aria-busy", String(generating));
}


function showNoMatches(moodTerms, notes = []) {
    closePreview();
    recommendations.classList.remove("hidden");
    playlistPreview.classList.add("hidden");
    songList.replaceChildren();
    currentSongs = [];

    showMoodTerms(moodTerms, undefined, notes);
    showStatus("No songs matched. Try describing your mood differently.");
}


// "Vibely picked up on: nostalgic · late night · road trip"
// "Vibely picked up on: Taylor Swift · sad", plus any notes from the backend
// ("Vibely's song library only covers 2000–2023...")
function showMoodTerms(moodTerms, understoodBy, notes = []) {
    moodTermsLine.classList.remove("hidden");

    if (moodTerms && moodTerms.length > 0) {
        const how = understoodBy === "ai" ? " (smart mood understanding)" : "";
        moodTermsLine.textContent = `Vibely picked up on: ${moodTerms.join(" · ")}${how}`;
    } else {
        moodTermsLine.textContent =
            "Vibely didn't spot any mood words, so these songs have a neutral vibe. " +
            "Try adding how you feel (calm, nostalgic, energetic...), what you're doing (studying, driving...), " +
            "or an artist or genre you like.";
    }

    for (const note of notes || []) {
        moodTermsLine.append(element("span", "block mt-1 text-amber-300", note));
    }
}


playlistName.addEventListener("input", () => {
    updateSuggestedNameButton();
    updatePlaylistSummary();
    noteChangesSinceSave();
});

useSuggestedNameButton.addEventListener("click", () => {
    setPlaylistName(suggestedTitle);
    playlistName.focus();
});


savePlaylistButton.addEventListener("click", async () => {
    if (playlistTracks.length === 0) {
        return;
    }

    // An empty box means "just use the suggestion"
    const name = playlistName.value.trim() || suggestedTitle;
    setPlaylistName(name);

    savePlaylistButton.disabled = true;
    savePlaylistButton.textContent = "Saving...";
    showPlaylistStatus("Saving to Spotify...");

    try {
        const playlist = await postJson("/playlists", {
            name,
            description: getPlaylistDescription(),
            track_ids: playlistTracks.map((song) => song.id),
        });

        savedPlaylist = { url: playlist.spotify_url, signature: getPlaylistSignature() };
        showPlaylistSaved(playlist);
    } catch (error) {
        if (error.status === 401) {
            showPlaylistStatus("Connect Spotify first (top right), then come back and save. This playlist will be kept as it is.", true);
        } else {
            showPlaylistStatus(error.message, true);
        }
    } finally {
        updateSaveButton();
    }
});


function showResults(mood, songs, title, moodTerms, understoodBy, vibe = null, notes = []) {
    closePreview();
    recommendations.classList.remove("hidden");
    showMoodTerms(moodTerms, understoodBy, notes);
    showStatus("");
    songList.replaceChildren(...songs.map(createSongCard));

    currentSongs = songs;
    currentMood = mood;
    currentMoodTerms = moodTerms || [];
    currentVibe = vibe;
    showPlaylistForm(title);
}


// The full reply: recommendations, playlist_title, mood_terms, understood_by, ...
async function fetchRecommendations(mood, vibe = null, signal = undefined) {
    if (!vibe) {
        return postJson("/recommendations", { mood }, REQUEST_TIMEOUT_MS, signal);
    }

    try {
        return await postJson("/recommendations", { mood, vibe }, REQUEST_TIMEOUT_MS, signal);
    } catch (error) {
        // The backend rejected the AI's answer: ask again with the built-in mood words
        if (error.status === 422) {
            return postJson("/recommendations", { mood }, REQUEST_TIMEOUT_MS, signal);
        }

        throw error;
    }
}


// POST JSON to the backend and return the JSON reply.
// Throws an Error with a readable message (and the HTTP status) if it fails.
// `signal` (optional) lets the caller cancel the request.
async function postJson(path, body, timeoutMs = 30000, signal = undefined) {
    let response;
    const timeout = AbortSignal.timeout(timeoutMs);

    try {
        response = await fetch(`${API_URL}${path}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",   // sends the Spotify login cookie, if there is one
            body: JSON.stringify(body),
            signal: signal ? AbortSignal.any([timeout, signal]) : timeout,
        });
    } catch (error) {
        if (signal?.aborted) {
            const cancelled = new Error("Cancelled");
            cancelled.cancelled = true;
            throw cancelled;
        }

        if (timeout.aborted) {
            throw new Error("Vibely took too long to answer. Please try again.");
        }

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

    // New recommendations: a fresh playlist, best match first
    playlistTracks = [...currentSongs];
    orderMode = "match";
    smoothOrderCache = null;
    lastChange = null;
    savedPlaylist = null;
    addedSongs = [];
    excludedIds = new Set();
    playlistNotice.textContent = "";
    renderPlaylist();
}


function setPlaylistName(name) {
    playlistName.value = name;
    updateSuggestedNameButton();
    updatePlaylistSummary();
    updateSaveButton();
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


// One card per recommended song. `index` is its place in the list (0 = best match).
function createSongCard(song, index) {
    const card = element("article", "bg-zinc-900 rounded-xl p-4");
    card.setAttribute("aria-label", `${index + 1}. ${song.title} by ${song.artists.join(", ")}`);

    const row = element("div", "flex items-center gap-4 flex-wrap sm:flex-nowrap");

    // Rank
    row.append(element("span", "w-6 text-right text-zinc-500 font-semibold tabular-nums flex-shrink-0", String(index + 1)));

    // Album artwork; clicking it opens the song in Spotify
    const artworkLink = createSpotifyLink(song, "flex-shrink-0 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500");
    artworkLink.setAttribute("aria-label", `Open ${song.title} in Spotify`);

    if (song.album_image_url) {
        const artwork = element("img", "w-20 h-20 rounded-lg object-cover bg-zinc-800");
        artwork.src = song.album_image_url;
        artwork.alt = "";   // the link's label already says what it is
        artwork.loading = "lazy";
        artworkLink.append(artwork);
    } else {
        // No artwork found: a plain square with a music note
        artworkLink.append(element("div", "w-20 h-20 rounded-lg bg-zinc-800 flex items-center justify-center text-2xl text-zinc-600", "♪"));
    }
    row.append(artworkLink);

    // Title (with an "E" badge for explicit songs), artists, album/year/length, attributes
    const details = element("div", "flex-1 min-w-0");

    const titleLine = element("div", "flex items-center gap-2 min-w-0");
    titleLine.append(element("h4", "font-semibold truncate", song.title));

    if (song.explicit) {
        const badge = element("span", "text-[10px] font-bold bg-zinc-600 text-zinc-100 rounded px-1 flex-shrink-0", "E");
        badge.title = "Explicit";
        badge.setAttribute("aria-label", "Explicit");
        titleLine.append(badge);
    }

    const facts = [song.album, song.release_year, formatDuration(song.duration_ms)].filter(Boolean);

    details.append(
        titleLine,
        element("p", "text-zinc-300 truncate", song.artists.join(", ")),
        element("p", "text-sm text-zinc-500 truncate", facts.join(" · ")),
        createAttributeList(song),
    );
    row.append(details);

    // Match score and the Preview / Open in Spotify buttons
    const side = element("div", "flex flex-wrap sm:flex-col items-center sm:items-end gap-2 flex-shrink-0 w-full sm:w-auto justify-between");

    const match = element("span", "text-green-400 font-semibold whitespace-nowrap", `${Math.round(song.score * 100)}% match`);
    match.title = "How close the song's tempo, energy, mood, etc. are to your vibe";
    side.append(match);

    const buttons = element("div", "flex flex-wrap gap-2");
    const previewButton = element("button", "text-sm bg-zinc-800 hover:bg-zinc-700 text-white rounded-full px-3 py-1 whitespace-nowrap", "▶ Preview");
    previewButton.type = "button";
    previewButton.setAttribute("aria-expanded", "false");
    previewButton.dataset.previewLabel = `Preview ${song.title}`;
    previewButton.setAttribute("aria-label", previewButton.dataset.previewLabel);

    const openLink = createSpotifyLink(song, "text-sm bg-green-500 hover:bg-green-400 text-black font-semibold rounded-full px-3 py-1 whitespace-nowrap", "Open in Spotify");

    buttons.append(previewButton, openLink);
    side.append(buttons);
    row.append(side);

    // The Spotify player goes here when Preview is clicked
    const player = element("div", "hidden mt-4");
    player.id = `player-${song.id}`;
    previewButton.setAttribute("aria-controls", player.id);
    previewButton.addEventListener("click", () => togglePreview(song, previewButton, player));

    card.append(row, player);
    return card;
}


function createSpotifyLink(song, className, text) {
    const link = element("a", className, text);
    link.href = song.spotify_url;
    link.target = "_blank";
    link.rel = "noopener";
    return link;
}


// The song whose player is open: { button, player }. Only one plays at a time.
let openPreview = null;


// Spotify's embedded player: a 30-second preview, or the full song if the
// listener is logged in to Spotify in this browser. (Spotify no longer gives
// new apps direct preview links, so this is the way to play a song on the page.)
function togglePreview(song, button, player) {
    const wasOpen = openPreview?.player === player;

    closePreview();

    if (wasOpen) {
        return;
    }

    const iframe = element("iframe", "w-full rounded-xl");
    iframe.src = `https://open.spotify.com/embed/track/${encodeURIComponent(song.id)}?utm_source=generator&theme=0`;
    iframe.height = "80";
    iframe.title = `Spotify player: ${song.title} by ${song.artists.join(", ")}`;
    iframe.allow = "autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture";
    iframe.loading = "lazy";
    iframe.style.border = "0";

    player.replaceChildren(iframe);
    player.classList.remove("hidden");
    button.textContent = "■ Close preview";
    button.setAttribute("aria-label", `Close preview of ${song.title}`);
    button.setAttribute("aria-expanded", "true");
    openPreview = { button, player };
}


// Removing the player also stops it playing
function closePreview() {
    if (!openPreview) {
        return;
    }

    openPreview.player.replaceChildren();
    openPreview.player.classList.add("hidden");
    openPreview.button.textContent = "▶ Preview";
    openPreview.button.setAttribute("aria-label", openPreview.button.dataset.previewLabel);
    openPreview.button.setAttribute("aria-expanded", "false");
    openPreview = null;
}


// 234988 -> "3:54"
function formatDuration(ms) {
    if (!ms) {
        return null;
    }

    const totalSeconds = Math.round(ms / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = String(totalSeconds % 60).padStart(2, "0");
    return `${minutes}:${seconds}`;
}


function createAttributeList(song) {
    const list = element("div", "flex flex-wrap gap-2 mt-2");
    const features = song.audio_features;

    const tags = [song.genre];

    if (features) {
        tags.push(
            `${Math.round(features.tempo)} BPM`,
            `Energy ${percent(features.energy)}`,
            `Mood ${percent(features.valence)}`,   // valence: sad (0%) to happy (100%)
            `Acoustic ${percent(features.acousticness)}`,
            `Danceable ${percent(features.danceability)}`,
        );
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


// ---------- Playlist preview page (#playlist) ----------

const homeView = document.getElementById("homeView");
const playlistView = document.getElementById("playlistView");
const playlistSummary = document.getElementById("playlistSummary");
const playlistCover = document.getElementById("playlistCover");
const playlistDescription = document.getElementById("playlistDescription");
const playlistStats = document.getElementById("playlistStats");
const playlistTrackList = document.getElementById("playlistTracks");
const playlistEmpty = document.getElementById("playlistEmpty");
const orderButtons = document.querySelectorAll("[data-order]");
const orderStatus = document.getElementById("orderStatus");
const orderHelp = document.getElementById("orderHelp");
const undoBar = document.getElementById("undoBar");
const undoText = document.getElementById("undoText");

const ORDER_HELP = {
    match: "Best matches for your mood come first.",
    smooth: "Arranged so tempo, energy, and mood change gradually from song to song. The best match still opens the playlist.",
    custom: "Your own order. Pick an option to rearrange automatically.",
};

// The songs that will be saved, in their final order
let playlistTracks = [];

// "match", "smooth", or "custom" (after moving songs by hand)
let orderMode = "match";

// The last smooth-flow answer, so switching back and forth doesn't ask again:
// { key: the songs it was for, ids: their smooth order }
let smoothOrderCache = null;

// The last removal or swap, for Undo:
// { kind: "remove", song, index } or { kind: "swap", song (the old one), replacement, index }
let lastChange = null;

// The AI's reading of the mood that the recommendations were made with (or
// null). Sent with the mood to /recommendations/more, so replacements fit the
// same mood, artists, and genres without running the AI again.
let currentVibe = null;

// Songs added as replacements or extras (the first recommendations are currentSongs)
let addedSongs = [];

// Songs the user removed or swapped out: never suggested again for this mood
let excludedIds = new Set();

// True while asking the backend for replacement songs (one request at a time)
let isReplacing = false;

// How many songs "Add songs" adds when the playlist is already full-size
const EXTRA_SONGS = 5;

// The most songs the playlist can have (the backend recommends at most 50 at once)
const MAX_PLAYLIST_SONGS = 50;

const playlistNotice = document.getElementById("playlistNotice");
const addSongsButton = document.getElementById("addSongs");

// The last save: { url, signature }. If nothing changed since, saving again is pointless.
let savedPlaylist = null;

let viewBeforeChange = "home";


window.addEventListener("hashchange", showCurrentView);

orderButtons.forEach((button) => {
    button.addEventListener("click", () => setOrder(button.dataset.order));
});

document.getElementById("undoRemove").addEventListener("click", () => {
    if (!lastChange) {
        return;
    }

    const { kind, song, index } = lastChange;

    if (kind === "swap") {
        // Put the old song back where the replacement is now
        const at = playlistTracks.findIndex((track) => track.id === lastChange.replacement.id);
        playlistTracks.splice(at === -1 ? index : at, at === -1 ? 0 : 1, song);
    } else {
        playlistTracks.splice(index, 0, song);
    }

    excludedIds.delete(song.id);
    lastChange = null;
    playlistNotice.textContent = "";
    renderPlaylist();
    focusTrackControl(song.id, kind === "swap" ? "swap" : "remove");
});

addSongsButton.addEventListener("click", addSongs);


function isPlaylistPageOpen() {
    return window.location.hash === "#playlist";
}


// Show the home page or the playlist page, depending on the address (#playlist)
function showCurrentView() {
    let onPlaylist = isPlaylistPageOpen();

    // No songs yet (e.g. a bookmarked #playlist): nothing to preview
    if (onPlaylist && currentSongs.length === 0) {
        window.history.replaceState(null, "", window.location.pathname);
        onPlaylist = false;
    }

    homeView.hidden = onPlaylist;
    playlistView.hidden = !onPlaylist;

    if (onPlaylist) {
        closePreview();   // stop any song preview playing on the home page
        renderPlaylist();
        window.scrollTo(0, 0);
        playlistView.querySelector("a").focus({ preventScroll: true });
    } else if (viewBeforeChange === "playlist") {
        // Back from the playlist page: return to the results, not the top
        playlistPreview.scrollIntoView({ block: "center" });
    }

    viewBeforeChange = onPlaylist ? "playlist" : "home";
}


function renderPlaylist() {
    renderPlaylistHeader();
    renderOrderControls();

    playlistTrackList.replaceChildren(...playlistTracks.map(createPlaylistRow));
    playlistEmpty.classList.toggle("hidden", playlistTracks.length > 0);

    undoBar.classList.toggle("hidden", !lastChange);
    if (lastChange) {
        undoText.textContent = lastChange.kind === "swap"
            ? `Swapped "${lastChange.song.title}" for "${lastChange.replacement.title}".`
            : `Removed "${lastChange.song.title}".`;
    }

    updateAddSongsButton();

    updatePlaylistSummary();
    noteChangesSinceSave();
}


function renderPlaylistHeader() {
    // Up to four different album covers in a 2×2 grid, like Spotify; one fills the square
    const covers = [...new Set(playlistTracks.map((song) => song.album_image_url).filter(Boolean))];
    const shown = covers.length >= 4 ? covers.slice(0, 4) : covers.slice(0, 1);

    playlistCover.replaceChildren(...shown.map((url) => {
        const image = element("img", "w-full h-full object-cover");
        image.src = url;
        image.alt = "";
        return image;
    }));
    playlistCover.classList.toggle("grid-cols-2", shown.length === 4);
    playlistCover.classList.toggle("grid-cols-1", shown.length !== 4);

    playlistDescription.textContent = getPlaylistDescription();

    const count = playlistTracks.length;
    playlistStats.textContent = [
        `${count} ${count === 1 ? "song" : "songs"}`,
        formatTotalDuration(playlistTracks),
        "Private",
    ].filter(Boolean).join(" · ");
}


function renderOrderControls() {
    for (const button of orderButtons) {
        button.setAttribute("aria-pressed", String(button.dataset.order === orderMode));
    }

    orderHelp.textContent = ORDER_HELP[orderMode];
}


// One row per song: position, cover, title/artist, length, match, and move/remove buttons
function createPlaylistRow(song, index) {
    const row = element("li", "bg-zinc-900 rounded-xl px-3 py-2 flex items-center gap-3");
    row.dataset.id = song.id;

    row.append(element("span", "w-6 text-right text-zinc-500 tabular-nums flex-shrink-0", String(index + 1)));

    if (song.album_image_url) {
        const cover = element("img", "w-12 h-12 rounded object-cover flex-shrink-0");
        cover.src = song.album_image_url;
        cover.alt = "";
        cover.loading = "lazy";
        row.append(cover);
    } else {
        row.append(element("div", "w-12 h-12 rounded bg-zinc-800 flex items-center justify-center text-zinc-600 flex-shrink-0", "♪"));
    }

    const text = element("div", "flex-1 min-w-0");
    const titleLine = element("div", "flex items-center gap-2 min-w-0");
    titleLine.append(element("span", "font-semibold truncate", song.title));

    if (song.explicit) {
        const badge = element("span", "text-[10px] font-bold bg-zinc-600 text-zinc-100 rounded px-1 flex-shrink-0", "E");
        badge.title = "Explicit";
        titleLine.append(badge);
    }

    text.append(titleLine, element("p", "text-sm text-zinc-400 truncate", song.artists.join(", ")));
    row.append(text);

    row.append(
        element("span", "hidden sm:inline text-sm text-green-400 w-20 text-right flex-shrink-0", `${Math.round(song.score * 100)}% match`),
        element("span", "text-sm text-zinc-400 w-12 text-right tabular-nums flex-shrink-0", formatDuration(song.duration_ms) || ""),
    );

    const controls = element("div", "flex gap-1 flex-shrink-0");
    controls.append(
        createRowButton("↑", `Move ${song.title} up`, "up", index === 0, () => moveTrack(index, -1)),
        createRowButton("↓", `Move ${song.title} down`, "down", index === playlistTracks.length - 1, () => moveTrack(index, 1)),
        createRowButton("↻", `Swap ${song.title} for a different song`, "swap", isReplacing || !currentMood, () => swapTrack(index)),
        createRowButton("✕", `Remove ${song.title} from the playlist`, "remove", false, () => removeTrack(index)),
    );
    row.append(controls);

    return row;
}


function createRowButton(symbol, label, action, disabled, onClick) {
    const button = element("button", "w-8 h-8 rounded-full text-zinc-400 hover:text-white hover:bg-zinc-800 disabled:opacity-25 disabled:hover:bg-transparent", symbol);
    button.type = "button";
    button.dataset.action = action;
    button.setAttribute("aria-label", label);
    button.title = label;
    button.disabled = disabled;
    button.addEventListener("click", onClick);
    return button;
}


function moveTrack(index, step) {
    const target = index + step;

    if (target < 0 || target >= playlistTracks.length) {
        return;
    }

    const [song] = playlistTracks.splice(index, 1);
    playlistTracks.splice(target, 0, song);
    orderMode = "custom";
    renderPlaylist();

    // Keep the keyboard on the song that moved, so it can be moved again
    focusTrackControl(song.id, step < 0 ? "up" : "down");
}


function removeTrack(index) {
    const [song] = playlistTracks.splice(index, 1);
    lastChange = { kind: "remove", song, index };
    excludedIds.add(song.id);   // don't suggest it again as a replacement
    playlistNotice.textContent = "";
    renderPlaylist();

    // Focus the song that took its place, or the Undo button if the list is now empty
    const next = playlistTracks[Math.min(index, playlistTracks.length - 1)];

    if (next) {
        focusTrackControl(next.id, "remove");
    } else {
        document.getElementById("undoRemove").focus();
    }
}


function focusTrackControl(songId, action) {
    const row = playlistTrackList.querySelector(`[data-id="${CSS.escape(songId)}"]`);
    const button = row?.querySelector(`[data-action="${action}"]:not(:disabled)`)
        || row?.querySelector("button:not(:disabled)");
    button?.focus();
}


async function setOrder(mode) {
    // The songs still in the playlist, best match first
    const kept = new Set(playlistTracks.map((song) => song.id));
    const byMatch = getSongPool().filter((song) => kept.has(song.id));

    if (mode === "match") {
        playlistTracks = byMatch;
        orderMode = "match";
        orderStatus.textContent = "";
        renderPlaylist();
        return;
    }

    const key = byMatch.map((song) => song.id).join(",");

    if (smoothOrderCache?.key !== key) {
        orderButtons.forEach((button) => { button.disabled = true; });
        orderStatus.textContent = "Arranging...";

        try {
            const reply = await postJson("/playlists/order", { track_ids: byMatch.map((song) => song.id) });
            smoothOrderCache = { key, ids: reply.track_ids };
            orderStatus.textContent = "";
        } catch (error) {
            orderStatus.textContent = `Couldn't arrange the songs: ${error.message}`;
            return;
        } finally {
            orderButtons.forEach((button) => { button.disabled = false; });
        }
    }

    const songsById = new Map(byMatch.map((song) => [song.id, song]));
    playlistTracks = smoothOrderCache.ids.map((id) => songsById.get(id)).filter(Boolean);
    orderMode = "smooth";
    renderPlaylist();
}


// Every song offered for this mood (first recommendations and replacements), best match first
function getSongPool() {
    const byId = new Map([...currentSongs, ...addedSongs].map((song) => [song.id, song]));
    return [...byId.values()].sort((a, b) => b.score - a.score);
}


// Ask the backend for `count` new songs for the same mood that aren't in the
// playlist and weren't removed. `leavingId` is a song about to be swapped out.
async function fetchReplacements(count, leavingId = null) {
    const reply = await postJson("/recommendations/more", {
        mood: currentMood,
        ...(currentVibe ? { vibe: currentVibe } : {}),
        playlist_ids: playlistTracks.map((song) => song.id).filter((id) => id !== leavingId),
        exclude_ids: [...excludedIds, ...(leavingId ? [leavingId] : [])],
        limit: count,
    }, REQUEST_TIMEOUT_MS);

    return reply.recommendations;
}


function setReplacing(replacing, message = "") {
    isReplacing = replacing;
    playlistNotice.textContent = message;
    playlistNotice.classList.remove("text-red-400");
    playlistNotice.classList.add("text-zinc-400");

    // Only one replacement request at a time
    playlistTrackList.querySelectorAll('[data-action="swap"]').forEach((button) => {
        button.disabled = replacing || !currentMood;
    });
    updateAddSongsButton();
}


function showPlaylistNotice(message, isError = false) {
    playlistNotice.textContent = message;
    playlistNotice.classList.toggle("text-red-400", isError);
    playlistNotice.classList.toggle("text-zinc-400", !isError);
}


// Replace one song, in the same spot, with the best new match for the mood
async function swapTrack(index) {
    const song = playlistTracks[index];
    const row = playlistTrackList.querySelector(`[data-id="${CSS.escape(song.id)}"]`);
    const swapButton = row?.querySelector('[data-action="swap"]');

    setReplacing(true, `Finding a song to replace "${song.title}"...`);
    row?.classList.add("opacity-60");
    if (swapButton) {
        swapButton.textContent = "…";
    }

    try {
        const [replacement] = await fetchReplacements(1, song.id);

        if (!replacement) {
            setReplacing(false);
            renderPlaylist();
            showPlaylistNotice("No other songs match this mood closely enough to swap in.");
            return;
        }

        // The song may have moved while waiting (it can't: buttons are off), but find it to be safe
        const at = playlistTracks.findIndex((track) => track.id === song.id);
        playlistTracks.splice(at === -1 ? index : at, 1, replacement);
        addedSongs.push(replacement);
        excludedIds.add(song.id);
        lastChange = { kind: "swap", song, replacement, index };

        // The new song breaks "best match first" and "smooth flow" alike
        orderMode = "custom";
        setReplacing(false);
        renderPlaylist();
        focusTrackControl(replacement.id, "swap");
    } catch (error) {
        setReplacing(false);
        renderPlaylist();
        showPlaylistNotice(`Couldn't find a replacement: ${error.message}`, true);
    }
}


// How many songs "Add songs" would add: enough to get back to the original
// size after removals, otherwise a few more
function getSongsToAdd() {
    const missing = currentSongs.length - playlistTracks.length;
    const wanted = missing > 0 ? missing : EXTRA_SONGS;
    return Math.max(0, Math.min(wanted, MAX_PLAYLIST_SONGS - playlistTracks.length));
}


function updateAddSongsButton() {
    const count = getSongsToAdd();
    const missing = currentSongs.length - playlistTracks.length;

    addSongsButton.hidden = count === 0 || !currentMood;
    addSongsButton.disabled = isReplacing;
    addSongsButton.textContent = missing > 0
        ? `+ Add ${count} ${count === 1 ? "song" : "songs"} (back to ${currentSongs.length})`
        : `+ Add ${count} more ${count === 1 ? "song" : "songs"}`;
}


async function addSongs() {
    const count = getSongsToAdd();

    if (count === 0 || isReplacing) {
        return;
    }

    setReplacing(true, "Finding more songs for this mood...");

    try {
        const newSongs = await fetchReplacements(count);
        setReplacing(false);

        if (newSongs.length === 0) {
            renderPlaylist();
            showPlaylistNotice("No other songs match this mood closely enough.");
            return;
        }

        addedSongs.push(...newSongs);
        playlistTracks.push(...newSongs);
        lastChange = null;

        // Keep the chosen order: re-sort by match, or re-arrange the flow
        if (orderMode === "match" || orderMode === "smooth") {
            await setOrder(orderMode);
        } else {
            renderPlaylist();   // custom order: new songs go at the end
        }

        const added = newSongs.length;
        showPlaylistNotice(
            added < count
                ? `Added ${added} ${added === 1 ? "song" : "songs"}; no others match this mood closely enough.`
                : `Added ${added} ${added === 1 ? "song" : "songs"}.`,
        );
    } catch (error) {
        setReplacing(false);
        renderPlaylist();
        showPlaylistNotice(`Couldn't add songs: ${error.message}`, true);
    }
}


function getPlaylistDescription() {
    return `Made by Vibely for "${currentMood}"`.slice(0, 300);
}


// What would be saved; used to tell whether anything changed since the last save
function getPlaylistSignature() {
    return JSON.stringify([playlistName.value.trim() || suggestedTitle, playlistTracks.map((song) => song.id)]);
}


function isUnchangedSinceSave() {
    return Boolean(savedPlaylist) && savedPlaylist.signature === getPlaylistSignature();
}


function updateSaveButton() {
    const unchanged = isUnchangedSinceSave();

    savePlaylistButton.disabled = isGenerating || playlistTracks.length === 0 || unchanged;
    savePlaylistButton.textContent = unchanged ? "Saved ✓" : "Save to Spotify";
}


// Called after the user edits the playlist. Changed after saving: saving again
// makes a second playlist in Spotify, so say so.
function noteChangesSinceSave() {
    updateSaveButton();

    if (savedPlaylist && !isUnchangedSinceSave()) {
        showPlaylistStatus("You've changed the playlist since saving. Saving again creates a new playlist in Spotify.");
    }
}


// The line on the results page: "10 songs · 41 min · "Rainy Morning Focus""
function updatePlaylistSummary() {
    const count = playlistTracks.length;
    const name = playlistName.value.trim() || suggestedTitle;

    playlistSummary.textContent = [
        `${count} ${count === 1 ? "song" : "songs"}`,
        formatTotalDuration(playlistTracks),
        `"${name}"`,
    ].filter(Boolean).join(" · ");
}


// [songs] -> "41 min" or "1 hr 5 min"; null if no lengths are known
function formatTotalDuration(songs) {
    const totalMs = songs.reduce((sum, song) => sum + (song.duration_ms || 0), 0);

    if (!totalMs) {
        return null;
    }

    const minutes = Math.round(totalMs / 60000);
    return minutes >= 60 ? `${Math.floor(minutes / 60)} hr ${minutes % 60} min` : `${minutes} min`;
}


// ---------- Smart mood understanding (in-browser AI) ----------

// "on" or "off" once the user has chosen; not set on a first visit, when the
// model downloads by itself if the device looks up to it (see shouldDownloadByItself)
const SMART_MOOD_KEY = "vibely:smartMood";

// Below this much device memory (GB, as the browser reports it), the 1 GB model
// isn't downloaded by itself; the user can still turn it on
const MIN_MEMORY_FOR_AUTO_DOWNLOAD = 4;

const smartMoodPanel = document.getElementById("smartMood");
const smartMoodProgress = document.getElementById("smartMoodProgress");
const smartMoodProgressText = document.getElementById("smartMoodProgressText");
const smartMoodErrorText = document.getElementById("smartMoodErrorText");

let smartMoodReady = false;


document.getElementById("smartMoodOn").addEventListener("click", turnOnSmartMood);
document.getElementById("smartMoodRetry").addEventListener("click", turnOnSmartMood);

document.getElementById("smartMoodOff").addEventListener("click", () => {
    localStorage.setItem(SMART_MOOD_KEY, "off");   // remembered: no download next visit
    smartMoodReady = false;
    showSmartMoodState("off");
    // The model stays in the browser's cache, so turning it back on is quick
});

// A download can't be stopped halfway, so this remembers the choice and reloads the page
document.getElementById("smartMoodCancel").addEventListener("click", () => {
    localStorage.setItem(SMART_MOOD_KEY, "off");
    window.location.reload();
});


function setUpSmartMood() {
    if (!vibeAi.isSupported()) {
        showSmartMoodState("unsupported");
        return;
    }

    const choice = localStorage.getItem(SMART_MOOD_KEY);

    // Turned on before, or a first visit on a device that can handle the download
    if (choice === "on" || (choice === null && shouldDownloadByItself())) {
        turnOnSmartMood();
    } else {
        showSmartMoodState("off");
    }
}


// Whether to download the model without asking: not on data-saver or slow
// connections, and not on devices with little memory
function shouldDownloadByItself() {
    const connection = navigator.connection;

    if (connection?.saveData || ["slow-2g", "2g", "3g"].includes(connection?.effectiveType)) {
        return false;
    }

    if (navigator.deviceMemory && navigator.deviceMemory < MIN_MEMORY_FOR_AUTO_DOWNLOAD) {
        return false;
    }

    return true;
}


async function turnOnSmartMood() {
    localStorage.setItem(SMART_MOOD_KEY, "on");
    showSmartMoodState("loading");
    showSmartMoodProgress({ progress: 0, text: "" });

    try {
        await vibeAi.loadModel(showSmartMoodProgress);
        smartMoodReady = true;
        showSmartMoodState("ready");
    } catch (error) {
        console.error("Smart mood understanding failed to load:", error);
        smartMoodErrorText.textContent =
            "Couldn't load the AI model, so Vibely is using its built-in mood words. " +
            "This can happen if the computer's graphics memory is too small or the download was interrupted.";
        showSmartMoodState("error");
    }
}


function showSmartMoodState(state) {
    for (const panel of smartMoodPanel.querySelectorAll("[data-state]")) {
        panel.classList.toggle("hidden", panel.dataset.state !== state);
    }
}


// WebLLM reports progress as 0..1 plus a text like "Fetching param cache[12/22]: 450MB fetched"
function showSmartMoodProgress({ progress, text }) {
    const percent = Math.round((progress || 0) * 100);
    smartMoodProgress.style.width = `${percent}%`;

    const downloading = /fetch/i.test(text || "");
    smartMoodProgressText.textContent = downloading
        ? `Downloading the AI model (once)... ${percent}%`
        : `Loading the AI model... ${percent}%`;
}


// The AI's reading of the mood, or null to let the backend use its word lists
// (AI off, still loading, or it failed this time)
async function readVibe(mood) {
    if (!smartMoodReady) {
        return null;
    }

    try {
        return await vibeAi.interpretMood(mood);
    } catch (error) {
        console.warn("Smart mood understanding failed for this mood; using built-in mood words.", error);
        return null;
    }
}


// ---------- When the page opens ----------
// (last, so every constant above is defined before it runs)

// Show how a Spotify login went, bring back the songs from before it,
// and show whether the user is connected
showLoginResult();
restoreStateFromBeforeLogin();
showConnectedUser();
updateCounter();
setUpSmartMood();
showCurrentView();
