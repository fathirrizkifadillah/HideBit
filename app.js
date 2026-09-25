const views = [...document.querySelectorAll(".view")];
const navItems = [...document.querySelectorAll("[data-route]")];
const state = { coverFile: null, stegoFile: null, analysisFile: null, imageUrl: null, stegoUrl: null, lastKey: "" };

function setRoute(route) {
  const requested = route || "home";
  const target = document.querySelector(`[data-view="${requested}"]`) ? requested : "home";
  views.forEach((view) => view.classList.toggle("active", view.dataset.view === target));
  navItems.forEach((item) => item.classList.toggle("active", item.dataset.route === target));
  if (location.hash.slice(1) !== target) history.replaceState(null, "", `#${target}`);
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  return `${(bytes / 1024).toFixed(1)} KB`;
}

function readImage(file, callback) {
  const url = URL.createObjectURL(file);
  const image = new Image();
  image.onload = () => callback(image, url);
  image.src = url;
}

function imageMeta(file, image) {
  const capacity = Math.max(0, Math.floor((image.width * image.height * 3 - 64) / 8));
  return `<strong>${file.name}</strong><span>${image.width} x ${image.height}px · ${formatBytes(file.size)} · ${formatBytes(capacity)} available</span>`;
}

function bindImageInput(inputId, metaId, kind) {
  const input = document.getElementById(inputId);
  const meta = document.getElementById(metaId);
  input.addEventListener("change", () => {
    const file = input.files[0];
    if (!file) return;
    readImage(file, (image, url) => {
      state[`${kind}File`] = file;
      state[`${kind}Url`] = url;
      meta.innerHTML = imageMeta(file, image);
      meta.classList.remove("hidden");
      if (kind === "cover") {
        document.getElementById("coverPreview").innerHTML = `<img src="${url}" alt="Cover image preview">`;
        document.getElementById("resultImageSize").textContent = `${image.width} x ${image.height}px`;
      }
    });
  });
}

function updateCapacity() {
  const message = document.getElementById("messageInput").value;
  const image = state.coverFile;
  const percent = image ? Math.min(100, Math.round(((message.length + 44) / Math.max(1, image._capacity)) * 100)) : 0;
  document.getElementById("capacityText").textContent = `${percent}%`;
  document.getElementById("capacityBar").style.width = `${percent}%`;
  document.getElementById("charCount").textContent = `${message.length} / 1000`;
}

function prepareCoverCapacity() {
  if (!state.coverFile) return;
  readImage(state.coverFile, (image) => { state.coverFile._capacity = Math.max(0, Math.floor((image.width * image.height * 3 - 64) / 8)); updateCapacity(); });
}

function resetHide() {
  document.getElementById("hideResult").classList.add("hidden");
  document.getElementById("messageInput").value = "";
  document.getElementById("hideKey").value = "";
  document.getElementById("coverMeta").classList.add("hidden");
  document.getElementById("charCount").textContent = "0 / 1000";
  document.getElementById("capacityText").textContent = "0%";
  document.getElementById("capacityBar").style.width = "0%";
}

function showHideResult() {
  const message = document.getElementById("messageInput").value.trim();
  const key = document.getElementById("hideKey").value;
  if (!state.coverFile || !message || !key) { alert("Choose an image, enter a message, and provide a stego key."); return; }
  state.lastKey = key;
  setRoute("processing");
  setTimeout(() => {
    document.getElementById("resultMessageSize").textContent = formatBytes(new TextEncoder().encode(message).length + 44);
    const preview = document.getElementById("stegoPreview");
    preview.innerHTML = state.coverUrl ? `<img src="${state.coverUrl}" alt="Stego image preview"><small>Protected</small>` : "Stego Image";
    document.getElementById("hideResult").classList.remove("hidden");
    setRoute("hide");
    document.getElementById("hideResult").scrollIntoView({ behavior: "smooth" });
  }, 950);
}

function showRevealResult() {
  const key = document.getElementById("revealKey").value;
  if (!state.stegoFile || !key || (state.lastKey && key !== state.lastKey)) { document.getElementById("revealError").classList.remove("hidden"); document.getElementById("revealResult").classList.add("hidden"); return; }
  document.getElementById("revealError").classList.add("hidden");
  document.getElementById("revealResult").classList.remove("hidden");
  document.getElementById("revealResult").scrollIntoView({ behavior: "smooth" });
}

function renderAnalysis() {
  if (!state.analysisFile) { alert("Choose an image to analyze first."); return; }
  const score = 72.35;
  document.getElementById("scoreValue").textContent = score.toFixed(2);
  document.getElementById("scoreRing").style.background = `conic-gradient(var(--teal) ${score * 3.6}deg, #344142 0deg)`;
  document.getElementById("analysisState").textContent = "Analysis complete";
  document.getElementById("channelRows").innerHTML = [["red", "Red", "18.42", "128", "0.72"], ["green", "Green", "21.07", "128", "0.61"], ["blue", "Blue", "16.89", "128", "0.78"]].map(([color, name, chi, dof, p]) => `<tr><td><i class="channel-dot ${color}"></i> ${name}</td><td>${chi}</td><td>${dof}</td><td>${p}</td></tr>`).join("");
}

document.querySelectorAll("a[href^='#']").forEach((link) => link.addEventListener("click", (event) => { const route = link.getAttribute("href").slice(1); if (document.querySelector(`[data-view="${route}"]`)) { event.preventDefault(); setRoute(route); } }));
window.addEventListener("hashchange", () => setRoute(location.hash.slice(1)));
document.getElementById("messageInput").addEventListener("input", updateCapacity);
document.getElementById("coverInput").addEventListener("change", prepareCoverCapacity);
document.getElementById("hideButton").addEventListener("click", showHideResult);
document.getElementById("hideAnother").addEventListener("click", resetHide);
document.getElementById("revealButton").addEventListener("click", showRevealResult);
document.getElementById("revealAnother").addEventListener("click", () => { document.getElementById("revealResult").classList.add("hidden"); document.getElementById("revealError").classList.add("hidden"); });
document.getElementById("analyzeButton").addEventListener("click", renderAnalysis);
document.getElementById("downloadButton").addEventListener("click", () => { if (state.coverUrl) { const link = document.createElement("a"); link.href = state.coverUrl; link.download = `hidebit-${state.coverFile.name}`; link.click(); } });
document.getElementById("copyButton").addEventListener("click", async (event) => { try { await navigator.clipboard.writeText(document.getElementById("revealedText").textContent); event.currentTarget.textContent = "Copied"; } catch { event.currentTarget.textContent = "Select to copy"; } });
document.querySelectorAll("[data-toggle-password]").forEach((button) => button.addEventListener("click", () => { const input = document.getElementById(button.dataset.togglePassword); input.type = input.type === "password" ? "text" : "password"; button.textContent = input.type === "password" ? "Show" : "Hide"; }));
bindImageInput("coverInput", "coverMeta", "cover");
bindImageInput("stegoInput", "stegoMeta", "stego");
bindImageInput("analysisInput", "analysisMeta", "analysis");
setRoute(location.hash.slice(1) || "home");