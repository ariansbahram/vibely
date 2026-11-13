// Understands any mood description with a small AI model that runs in the
// browser (WebLLM, using the computer's GPU through WebGPU). Free, no API key,
// and the description never leaves the user's computer for this step.
//
// The model turns "first snow, missing someone, but hopeful" into music the
// backend can search for: levels for each audio feature, a few mood words,
// maybe some genres, and a playlist title. The backend checks everything again.
//
// The model is about 1 GB. It downloads once, then loads from the browser's cache.

const WEBLLM_URL = "https://esm.run/@mlc-ai/web-llm@0.2.88";

// Small enough for most laptops (about 1.6 GB of GPU memory), good at following
// the JSON format below. See webllm's prebuiltAppConfig for other models.
export const MODEL_ID = "Qwen2.5-1.5B-Instruct-q4f16_1-MLC";

// Small models are much better at picking a level than at inventing numbers,
// so the model picks a level and the backend turns it into a number.
const LEVELS = ["very_low", "low", "medium", "high", "very_high"];
const TEMPOS = ["very_slow", "slow", "medium", "fast", "very_fast"];

// Genre names exactly as in the song dataset (backend/data/spotify_data.csv).
// Left out because the dataset's label means something other than it sounds:
// "romance" (Russian romance ballads), "comedy" (stand-up), "songwriter" (tiny).
const GENRES = [
    "acoustic", "afrobeat", "alt-rock", "ambient", "black-metal", "blues", "breakbeat",
    "cantopop", "chicago-house", "chill", "classical", "club", "comedy", "country", "dance",
    "dancehall", "death-metal", "deep-house", "detroit-techno", "disco", "drum-and-bass",
    "dub", "dubstep", "edm", "electro", "electronic", "emo", "folk", "forro", "french",
    "funk", "garage", "german", "gospel", "goth", "grindcore", "groove", "guitar",
    "hard-rock", "hardcore", "hardstyle", "heavy-metal", "hip-hop", "house", "indian",
    "indie-pop", "industrial", "jazz", "k-pop", "metal", "metalcore", "minimal-techno",
    "new-age", "opera", "party", "piano", "pop", "pop-film", "power-pop",
    "progressive-house", "psych-rock", "punk", "punk-rock", "rock", "rock-n-roll",
    "sad", "salsa", "samba", "sertanejo", "show-tunes", "singer-songwriter",
    "ska", "sleep", "soul", "spanish", "swedish", "techno", "trance",
    "trip-hop",
];

// WebLLM only lets the model write JSON that fits this shape
const RESPONSE_SCHEMA = {
    type: "object",
    properties: {
        moods: { type: "array", items: { type: "string" }, minItems: 1, maxItems: 4 },
        energy: { type: "string", enum: LEVELS },
        valence: { type: "string", enum: LEVELS },
        tempo: { type: "string", enum: TEMPOS },
        acousticness: { type: "string", enum: LEVELS },
        danceability: { type: "string", enum: LEVELS },
        instrumentalness: { type: "string", enum: LEVELS },
        genres: { type: "array", items: { type: "string", enum: GENRES }, maxItems: 3 },
        title: { type: "string" },
    },
    required: [
        "moods", "energy", "valence", "tempo", "acousticness",
        "danceability", "instrumentalness", "genres", "title",
    ],
};

const SYSTEM_PROMPT = `You pick music for any moment. The user describes a mood, a situation, or a mix of feelings, in their own words. It can be very specific, niche, or contradictory. Work out what they are feeling and doing, then describe the music that fits.

Reply with JSON only:
- moods: 1 to 4 short lowercase words or phrases naming the vibe
- energy: how intense and active the music is
- valence: how happy it sounds (very_low = sad or dark, very_high = joyful)
- tempo: how fast it is
- acousticness: very_high = acoustic instruments, very_low = electronic
- danceability: how easy it is to dance to
- instrumentalness: very_high = no singing (good for focus or sleep), very_low = vocals
- genres: up to 3 genres from the allowed list, ONLY when the description clearly points to a style of music. Every genre must fit the mood; never add one that clashes with it. When unsure, use an empty list.
- title: a playlist title, 2 to 5 words, Title Case, no quotes or emoji

For mixed feelings, find the balance between them. Quiet, sad, sleepy, or lonely moments need low energy and slow tempo; partying, working out, and raving need high energy and fast tempo.

Example: "driving through San Francisco at night feeling nostalgic"
{"moods":["nostalgic","late night","city drive"],"energy":"medium","valence":"low","tempo":"medium","acousticness":"low","danceability":"medium","instrumentalness":"low","genres":[],"title":"Midnight City Memories"}

Example: "main character energy walking to class in the sun"
{"moods":["confident","sunny","carefree"],"energy":"high","valence":"very_high","tempo":"fast","acousticness":"low","danceability":"high","instrumentalness":"very_low","genres":["pop","indie-pop"],"title":"Main Character Walk"}

Example: "rainy afternoon alone with tea, a little lonely but peaceful"
{"moods":["lonely","peaceful","rainy"],"energy":"very_low","valence":"low","tempo":"slow","acousticness":"very_high","danceability":"low","instrumentalness":"medium","genres":["acoustic","folk"],"title":"Tea For One"}

Example: "pregame hype in the locker room before the championship"
{"moods":["hyped","confident","intense"],"energy":"very_high","valence":"high","tempo":"very_fast","acousticness":"very_low","danceability":"high","instrumentalness":"very_low","genres":["hip-hop"],"title":"Championship Mode"}`;

let webllmPromise = null;
let enginePromise = null;
let loadedEngine = null;   // set once the model is ready


// WebGPU is in recent Chrome, Edge, and Safari on computers; not in every browser
export function isSupported() {
    return "gpu" in navigator;
}


function loadWebllm() {
    webllmPromise ??= import(WEBLLM_URL);
    return webllmPromise;
}


// True if the model was downloaded before, so loading it won't download 1 GB again
export async function isModelDownloaded() {
    try {
        const webllm = await loadWebllm();
        return await webllm.hasModelInCache(MODEL_ID);
    } catch {
        return false;
    }
}


// Loads the model (downloading it the first time). onProgress gets
// { progress: 0..1, text } while it loads. Safe to call more than once.
export function loadModel(onProgress = () => {}) {
    enginePromise ??= loadWebllm()
        .then((webllm) => webllm.CreateMLCEngine(MODEL_ID, { initProgressCallback: onProgress }))
        .then((engine) => {
            loadedEngine = engine;
            return engine;
        })
        .catch((error) => {
            enginePromise = null;   // let the user try again
            throw error;
        });

    return enginePromise;
}


// Stops interpretMood() if it's running; it then throws
export function cancelInterpretation() {
    loadedEngine?.interruptGenerate();
}


export function isModelLoading() {
    return enginePromise !== null;
}


// Turns a mood description into the "vibe" object POST /recommendations accepts.
// Throws if the model isn't loaded, takes longer than timeoutMs, or gives an
// unusable answer.
export async function interpretMood(mood, timeoutMs = 45000) {
    const engine = await enginePromise;

    if (!engine) {
        throw new Error("The AI model isn't loaded.");
    }

    const timer = setTimeout(() => engine.interruptGenerate(), timeoutMs);

    try {
        return await askModel(engine, mood);
    } finally {
        clearTimeout(timer);
    }
}


async function askModel(engine, mood) {
    const reply = await engine.chat.completions.create({
        messages: [
            { role: "system", content: SYSTEM_PROMPT },
            { role: "user", content: mood },
        ],
        response_format: { type: "json_object", schema: JSON.stringify(RESPONSE_SCHEMA) },
        temperature: 0.3,
        max_tokens: 200,
    });

    // Cut off (timeout) or not valid JSON: JSON.parse throws, and the caller
    // falls back to Vibely's built-in mood words
    const vibe = JSON.parse(reply.choices[0].message.content);

    const moods = vibe.moods
        .map((word) => word.trim().toLowerCase().slice(0, 40))
        .filter(Boolean)
        .slice(0, 4);

    if (moods.length === 0) {
        throw new Error("The AI didn't name any moods.");
    }

    return {
        moods,
        energy: vibe.energy,
        valence: vibe.valence,
        tempo: vibe.tempo,
        acousticness: vibe.acousticness,
        danceability: vibe.danceability,
        instrumentalness: vibe.instrumentalness,
        genres: [...new Set(vibe.genres)].slice(0, 3),
        title: vibe.title.trim().slice(0, 100) || null,
    };
}
