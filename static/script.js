"use strict";

let mode = "check";
let season = "Spring";
let availableCrops = [];

const byId = (id) => document.getElementById(id);

function setMode(next) {
  mode = next;
  byId("checkMode").classList.toggle("active", next === "check");
  byId("recommendMode").classList.toggle("active", next === "recommend");
  byId("cropField").style.display = next === "recommend" ? "none" : "grid";
  byId("submitLabel").textContent = next === "recommend"
    ? "Recommend varieties" : "Check crop suitability";
  byId("result").classList.remove("visible");
}

function selectSeason(button) {
  document.querySelectorAll(".season").forEach((item) => {
    item.classList.remove("selected");
  });
  button.classList.add("selected");
  season = button.dataset.season;
}

function scrollToPlanner() {
  byId("planner").scrollIntoView({ behavior: "smooth" });
}

function addSection(parent, heading, items = []) {
  if (!items.length) return;
  const title = document.createElement("h5");
  title.textContent = heading;
  const list = document.createElement("ul");
  for (const item of items) {
    const entry = document.createElement("li");
    entry.textContent = item;
    list.appendChild(entry);
  }
  parent.append(title, list);
}

function closeCropDropdown() {
  byId("cropDropdown").classList.remove("show");
  byId("cropSearch").setAttribute("aria-expanded", "false");
}

function selectCrop(slug, label) {
  byId("crop").value = slug;
  byId("cropSearch").value = label;
  closeCropDropdown();
}



function filterCrops() {
    const search = document
        .getElementById("cropSearch")
        .value.toLowerCase().trim();

    const dropdown = document.getElementById("cropDropdown");

    dropdown.replaceChildren();

    let matches = [];

    if (search === "") {
        // Show a variety of crop categories initially
        const seenCategories = new Set();

        matches = availableCrops.filter(crop => {
            const category = crop.category.toLowerCase();

            if (seenCategories.has(category)) {
                return false;
            }

            seenCategories.add(category);
            return true;
        }).slice(0, 40);

    } else {
        // Search the entire crop dataset
        matches = availableCrops.filter(crop =>
            crop.name.toLowerCase().includes(search) ||
            crop.category.toLowerCase().includes(search)
        ).slice(0, 40);
    }

    if (matches.length === 0) {
        const empty = document.createElement("div");
        empty.className = "crop-empty";
        empty.textContent = "No matching crops found.";
        dropdown.appendChild(empty);

    } else {
        matches.forEach(crop => {
            const option = document.createElement("button");

            option.type = "button";
            option.className = "crop-option";
            option.textContent =
                `${crop.name} (${crop.category})`;

            option.addEventListener("click", () => {
                selectCrop(crop.id, option.textContent);
            });

            dropdown.appendChild(option);
        });
    }

    dropdown.classList.add("show");
}



async function loadCatalog() {
    try {
        const response = await fetch("/api/catalog");

        if (!response.ok) {
            throw new Error("Catalog unavailable");
        }

        const data = await response.json();

        // Load all crop varieties from Flask
        availableCrops = (data.varieties || []).map(crop => ({
            id: crop.slug,
            name: crop.name,
            category: crop.category
        }));

        byId("cropSearch").placeholder =
            "Search crops or varieties...";

        console.log(
            `Loaded ${availableCrops.length} crop varieties`
        );

    } catch (error) {
        console.error("Failed to load crops:", error);

        byId("cropSearch").placeholder =
            "Could not load crop varieties";
    }
}


function plannerPayload() {
  const city = byId("city").value.trim();
  const state = byId("state").value.trim();
  const postalCode = byId("postalCode").value.trim();
  const country = byId("country").value.trim();
  return {
    mode,
    city,
    state,
    postal_code: postalCode,
    country,
    location: [city, state, postalCode, country].filter(Boolean).join(", "),
    season,
    soil: byId("soil").value,
    variety: byId("crop").value,
    zone: byId("zone").value,
    soil_ph: byId("soilPh").value,
    moisture: byId("moisture").value,
    nitrogen: byId("nitrogen").value,
  };
}



function locationHeaderLines(data, assessment) {
  const located = (data.context && data.context.location) || null;
  const lines = [];
  const place =
    (assessment && assessment.location) ||
    (located && located.display_name) ||
    (data.context && data.context.query) ||
    "";
  if (place) {
    lines.push(`Resolved place: ${place}`);
  }
  const lat = located && located.latitude;
  const lon = located && located.longitude;
  const coords =
    (assessment && assessment.coordinates) ||
    (lat != null && lon != null
      ? `${Number(lat).toFixed(5)}, ${Number(lon).toFixed(5)}`
      : "");
  if (coords) {
    lines.push(
      `Coordinates: ${coords} (place centroid, not a field boundary).`
    );
  }
  return lines;
}

function showAssessment(details, data) {
  const assessment = data.result;
  const score = assessment.compatibility_score;

  const result = byId("result");
  const scoreEl = byId("score");
  const meterFill = byId("meterFill");

  // Display crop name
  byId("resultTitle").textContent =
    `${assessment.variety}: ${assessment.status}`;

  // Display assessment explanation
  byId("resultText").textContent =
    assessment.disclaimer || "";

  // Display percentage and progress bar
  if (typeof score === "number" && Number.isFinite(score)) {
    const percentage = Math.max(0, Math.min(100, score));

    scoreEl.textContent = `${percentage}% fit`;
    meterFill.style.width = `${percentage}%`;

    if (percentage >= 80) {
      meterFill.style.backgroundColor = "#597d35";
    } else if (percentage >= 60) {
      meterFill.style.backgroundColor = "#d4a63d";
    } else {
      meterFill.style.backgroundColor = "#d66b55";
    }

    byId("compatibilityMeter")?.setAttribute(
      "aria-valuenow",
      String(percentage)
    );
  } else {
    scoreEl.textContent = "N/A";
    meterFill.style.width = "0%";

    byId("compatibilityMeter")?.removeAttribute(
      "aria-valuenow"
    );
  }

  // Display assessment details
  details.replaceChildren();
  const climateLines = [
    ...locationHeaderLines(data, assessment),
    ...((assessment.field_context || []).length
      ? assessment.field_context
      : ((data.context && data.context.lines) || [])),
  ];
  addSection(details, "Location, climate, and water", climateLines);

  addSection(
    details,
    "Positive indicators",
    assessment.positive_indicators || []
  );

  addSection(
    details,
    "Issues to review",
    assessment.issues || []
  );

  addSection(
    details,
    "Missing measurements",
    assessment.unknowns || []
  );

  addSection(
    details,
    "Soil improvement actions",
    assessment.improvements || []
  );

  addSection(
    details,
    "Companion plants (not cover crops)",
    (assessment.companion_plants || []).map(plant =>
      `${plant.name}: ${plant.relationship} — ${plant.reason}`
    )
  );

  addSection(
    details,
    "Planting calendar",
    (assessment.planting_calendar || []).map(entry =>
      `Zone ${entry.usda_zone}: ` +
      `direct sow ${entry.direct_sow_start || "N/A"}–` +
      `${entry.direct_sow_end || "N/A"}; ` +
      `transplant ${entry.outdoor_transplant_start || "N/A"}–` +
      `${entry.outdoor_transplant_end || "N/A"}`
    )
  );

  // Restart result animation
  result.classList.remove("visible");
  void result.offsetWidth;
  result.classList.add("visible");
}



function showRecommendations(details, data) {
  byId("resultTitle").textContent = "Varieties to explore";
  byId("resultText").textContent = data.disclaimer || "";
  byId("score").textContent = "";
  const climateLines = [
    ...locationHeaderLines(data, null),
    ...((data.context && data.context.lines) || []),
  ];
  addSection(details, "Location, climate, and water", climateLines);
  addSection(details, "Suggested varieties", (data.recommendations || []).map((crop) =>
    `${crop.variety} (${crop.crop}) — ${crop.status}${crop.issues?.length ? ": " + crop.issues.join(" ") : ""}`));
}

function hasFarmLocation(payload) {
  const city = (payload.city || "").trim();
  const state = (payload.state || "").trim();
  const postal = (payload.postal_code || "").trim();
  return Boolean((city && state) || postal);
}

async function runPlanner() {
  const payload = plannerPayload();
  if (!hasFarmLocation(payload)) {
    alert("Enter a city and state, or a ZIP code, so we can resolve farm coordinates.");
    byId("city").focus();
    return;
  }
  if (mode === "check" && !payload.variety) {
    alert("Please search for and select a crop variety.");
    byId("cropSearch").focus();
    return;
  }

  const details = byId("resultDetails");
  byId("result").classList.add("visible");
  byId("resultTitle").textContent = "Checking your field profile...";
  byId("resultText").textContent = "";
  byId("score").textContent = "";
  byId("meterFill").style.width = "0%";
  details.replaceChildren();

  try {
    const response = await fetch("/api/planner", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Request failed");
    if (mode === "recommend") showRecommendations(details, data);
    else showAssessment(details, data);
  } catch (error) {
    byId("resultTitle").textContent = "Unable to check";
    byId("resultText").textContent = error.message;
  }
}

// Inline HTML onclick handlers need these functions in global scope.
window.setMode = setMode;
window.selectSeason = selectSeason;
window.scrollToPlanner = scrollToPlanner;
window.runPlanner = runPlanner;

document.addEventListener("DOMContentLoaded", () => {
  byId("cropSearch").addEventListener("input", filterCrops);
  byId("cropSearch").addEventListener("focus", filterCrops);
  byId("cropSearch").addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeCropDropdown();
  });
  document.addEventListener("click", (event) => {
    if (!event.target.closest(".crop-search-wrapper")) closeCropDropdown();
  });
  loadCatalog();
});

