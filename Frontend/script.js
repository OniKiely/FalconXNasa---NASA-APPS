let mode = "check";
let season = "Spring";

const cropData = {
  maize: { name: "Maize", ideal: ["loam", "silt"], seasons: ["Spring", "Summer"], score: 92, note: "Your conditions look strong for maize. Loam or silt soils give roots room to establish, while warm planting windows support steady growth." },
  beans: { name: "Beans", ideal: ["loam", "sandy"], seasons: ["Spring", "Fall"], score: 88, note: "Beans should be a good match. Prioritise drainage and avoid planting into waterlogged soil; a gentle, warm season will help germination." },
  tomato: { name: "Tomatoes", ideal: ["loam", "sandy"], seasons: ["Spring", "Summer"], score: 84, note: "Tomatoes are a promising fit. They prefer warm conditions and well-drained soil, with consistent moisture once established." },
  potato: { name: "Potatoes", ideal: ["loam", "sandy"], seasons: ["Spring", "Fall"], score: 86, note: "Potatoes look compatible with your profile. Loose, well-drained soil will help tubers develop evenly." },
  rice: { name: "Rice", ideal: ["clay", "silt"], seasons: ["Summer"], score: 79, note: "Rice can work well when water is available. Clay or silt soils help retain moisture, but drainage and flooding should be managed carefully." },
  carrot: { name: "Carrots", ideal: ["sandy", "loam"], seasons: ["Spring", "Fall"], score: 90, note: "Carrots are a strong match. Loose soil helps roots grow straight, while cooler planting seasons support a sweeter harvest." },
  wheat: { name: "Wheat", ideal: ["loam", "clay"], seasons: ["Fall", "Winter"], score: 81, note: "Wheat looks like a workable choice. Aim for fertile soil and avoid planting where water pools after rain." }
};

function setMode(next) {
  mode = next;
  document.getElementById("checkMode").classList.toggle("active", next === "check");
  document.getElementById("recommendMode").classList.toggle("active", next === "recommend");
  document.getElementById("cropField").style.display = next === "recommend" ? "none" : "grid";
  document.getElementById("submitLabel").textContent = next === "recommend" ? "Find my best crop" : "Check crop suitability";
  document.getElementById("result").classList.remove("visible");
}

function selectSeason(button) {
  document.querySelectorAll(".season").forEach(x => x.classList.remove("selected"));
  button.classList.add("selected");
  season = button.dataset.season;
}

function runPlanner() {
  const soil = document.getElementById("soil").value;
  const location = document.getElementById("location").value.trim() || "your area";
  let selected;

  if (mode === "recommend") {
    selected = Object.values(cropData).sort((a, b) => {
      const aScore = (a.ideal.includes(soil) ? 30 : 0) + (a.seasons.includes(season) ? 20 : 0) + a.score;
      const bScore = (b.ideal.includes(soil) ? 30 : 0) + (b.seasons.includes(season) ? 20 : 0) + b.score;
      return bScore - aScore;
    })[0];
    document.getElementById("resultTitle").textContent = `${selected.name} is your best match`;
    document.getElementById("score").textContent = `${selected.score}% fit`;
    document.getElementById("resultText").textContent = `For ${location} in ${season}, ${selected.name.toLowerCase()} is a promising place to start. ${selected.note}`;
  } else {
    selected = cropData[document.getElementById("crop").value];
    let score = selected.score;
    if (!selected.ideal.includes(soil)) score -= 18;
    if (!selected.seasons.includes(season)) score -= 10;
    score = Math.max(48, score);
    document.getElementById("resultTitle").textContent = `${selected.name} compatibility`;
    document.getElementById("score").textContent = `${score}% fit`;
    document.getElementById("resultText").textContent = `${selected.note} Based on the profile for ${location}, this is a ${score >= 80 ? "strong" : "moderate"} starting point.`;
    selected = { ...selected, score };
  }

  document.getElementById("meterFill").style.width = `${selected.score}%`;
  document.getElementById("result").classList.add("visible");
}

function scrollToPlanner() {
  showHome();
  setTimeout(() => document.getElementById("planner").scrollIntoView({ behavior: "smooth" }), 30);
}

function showAbout() {
  document.getElementById("homePage").style.display = "none";
  document.getElementById("aboutPage").classList.add("visible");
  window.scrollTo({ top: 0, behavior: "smooth" });
  history.replaceState(null, "", "#about");
}

function showHome() {
  document.getElementById("homePage").style.display = "block";
  document.getElementById("aboutPage").classList.remove("visible");
  history.replaceState(null, "", "#home");
}

if (location.hash === "#about") showAbout();
