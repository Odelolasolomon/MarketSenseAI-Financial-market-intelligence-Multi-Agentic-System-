// API Endpoints
const API_BASE = "http://localhost:8000/api/v1";

// DOM Elements
const queryInput = document.getElementById("query-input");
const submitQueryButton = document.getElementById("submit-query");
const microphoneButton = document.getElementById("microphone-button");
const responseContainer = document.getElementById("response-container");
const playAudioButton = document.getElementById("play-audio");
const marketCardsContainer = document.getElementById("market-cards");
const ragSearchInput = document.getElementById("rag-search");
const searchRagButton = document.getElementById("search-rag");
const ragResultsContainer = document.getElementById("rag-results");

// Submit Query
submitQueryButton.addEventListener("click", async () => {
  const query = queryInput.value;
  if (!query) return alert("Please enter a query.");

  const response = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, asset: null, timeframe: "medium" }),
  });

  const data = await response.json();
  displayResponse(data.analysis.summary);

  if (data.analysis.audio_path) {
    playAudioButton.classList.remove("hidden");
    playAudioButton.dataset.audioPath = data.analysis.audio_path;
  }
});

// Speech-to-Text
microphoneButton.addEventListener("click", async () => {
  const response = await fetch(`${API_BASE}/speech-to-text`, { method: "POST" });
  const data = await response.json();
  queryInput.value = data.text;
});

// Play Audio
playAudioButton.addEventListener("click", () => {
  const audioPath = playAudioButton.dataset.audioPath;
  if (audioPath) {
    const audio = new Audio(audioPath);
    audio.play();
  }
});

// Display Response
function displayResponse(response) {
  responseContainer.innerHTML = response;
}

// Search RAG
searchRagButton.addEventListener("click", async () => {
  const query = ragSearchInput.value;
  if (!query) return alert("Please enter a search term.");

  const response = await fetch(`${API_BASE}/translate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: query, src: "auto", dest: "en" }),
  });

  const data = await response.json();
  displayRAGResults(data.translated_text);
});

// Display RAG Results
function displayRAGResults(results) {
  ragResultsContainer.innerHTML = results
    .map(
      (item) => `
    <div class="rag-item">
      <h3>${item.title}</h3>
      <p>${item.snippet}</p>
      <small>${item.source} - ${item.date}</small>
    </div>
  `
    )
    .join("");
}