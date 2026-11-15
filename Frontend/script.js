const cropData = {
  maize: { name: "Maize", ideal: ["loam", "silt"], seasons: ["Spring", "Summer"], score: 92, note: "Your conditions look strong for maize. Loam or silt soils give roots room to establish, while warm planting windows support steady growth." },
  beans: { name: "Beans", ideal: ["loam", "sandy"], seasons: ["Spring", "Fall"], score: 88, note: "Beans should be a good match. Prioritise drainage and avoid planting into waterlogged soil; a gentle, warm season will help germination." },
  tomato: { name: "Tomatoes", ideal: ["loam", "sandy"], seasons: ["Spring", "Summer"], score: 84, note: "Tomatoes are a promising fit. They prefer warm conditions and well-drained soil, with consistent moisture once established." },
  potato: { name: "Potatoes", ideal: ["loam", "sandy"], seasons: ["Spring", "Fall"], score: 86, note: "Potatoes look compatible with your profile. Loose, well-drained soil will help tubers develop evenly." },
  rice: { name: "Rice", ideal: ["clay", "silt"], seasons: ["Summer"], score: 79, note: "Rice can work well when water is available. Clay or silt soils help retain moisture, but drainage and flooding should be managed carefully." },
  carrot: { name: "Carrots", ideal: ["sandy", "loam"], seasons: ["Spring", "Fall"], score: 90, note: "Carrots are a strong match. Loose soil helps roots grow straight, while cooler planting seasons support a sweeter harvest." },
  wheat: { name: "Wheat", ideal: ["loam", "clay"], seasons: ["Fall", "Winter"], score: 81, note: "Wheat looks like a workable choice. Aim for fertile soil and avoid planting where water pools after rain." }
};

const SOIL_BONUS = 30;
const SEASON_BONUS = 20;
const SOIL_PENALTY = 18;
const SEASON_PENALTY = 10;
const MIN_SCORE = 48;

const form = document.getElementById("plannerForm");
const cropField = document.getElementById("cropField");
const cropSelect = document.getElementById("crop");
const submitLabel = document.getElementById("submitLabel");
const result = document.getElementById("result");
const resultTitle = document.getElementById("resultTitle");
const scoreEl = document.getElementById("score");
const resultText = document.getElementById("resultText");
const meterFill = document.getElementById("meterFill");

/** Read the form into a plain object — also the shape to POST to the backend later. */
function readForm() {
  const data = new FormData(form);
  return {
    mode: data.get("mode"),
    location: (data.get("location") || "").trim(),
    season: data.get("season"),
    soil: data.get("soil"),
    crop: data.get("crop"), // null in recommend mode (select is disabled)
  };
}

function recommendCrop({ soil, season }) {
  const rank = (c) =>
    c.score + (c.ideal.includes(soil) ? SOIL_BONUS : 0) + (c.seasons.includes(season) ? SEASON_BONUS : 0);
  const best = Object.values(cropData).reduce((a, b) => (rank(b) > rank(a) ? b : a));
  return { crop: best, score: best.score };
}

function checkCrop({ crop, soil, season }) {
  const c = cropData[crop];
  let score = c.score;
  if (!c.ideal.includes(soil)) score -= SOIL_PENALTY;
  if (!c.seasons.includes(season)) score -= SEASON_PENALTY;
  return { crop: c, score: Math.max(MIN_SCORE, score) };
}

function renderResult(input) {
  const place = input.location || "your area";

  if (input.mode === "recommend") {
    const { crop, score } = recommendCrop(input);
    resultTitle.textContent = `${crop.name} is your best match`;
    scoreEl.textContent = `${score}% fit`;
    resultText.textContent = `For ${place} in ${input.season}, ${crop.name.toLowerCase()} is a promising place to start. ${crop.note}`;
    meterFill.style.width = `${score}%`;
  } else {
    const { crop, score } = checkCrop(input);
    resultTitle.textContent = `${crop.name} compatibility`;
    scoreEl.textContent = `${score}% fit`;
    resultText.textContent = `${crop.note} Based on the profile for ${place}, this is a ${score >= 80 ? "strong" : "moderate"} starting point.`;
    meterFill.style.width = `${score}%`;
  }

  result.hidden = false;
  // Restart the entry animation on repeat submissions.
  result.classList.remove("visible");
  void result.offsetWidth;
  result.classList.add("visible");
}

function applyMode(mode) {
  const recommend = mode === "recommend";
  cropField.hidden = recommend;
  cropSelect.disabled = recommend; // excluded from FormData when hidden
  submitLabel.textContent = recommend ? "Find my best crop" : "Check crop suitability";
  result.hidden = true;
}

form.addEventListener("change", (e) => {
  if (e.target.name === "mode") applyMode(e.target.value);
});

form.addEventListener("submit", (e) => {
  e.preventDefault();
  if (!form.reportValidity()) return;
  const formInfo = readForm()
  renderResult(formInfo);

  fetch("http://localhost:8000/submissionForm", {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(formInfo)
  })
    .then((response) => {
      if (!response.ok) throw new Error(`Server responded ${response.status}`);
      return response.json();
    })
    .then((data) => console.log("Backend:", data))
    .catch((err) => console.error("POST /submissionForm failed:", err));
});

applyMode(new FormData(form).get("mode"));
