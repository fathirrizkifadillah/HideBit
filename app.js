/**
 * app.js
 * ======
 * Client-side script untuk HideBit Web Interface
 * Menghubungkan UI ke backend Flask API (/api/capacity, /api/embed, /api/extract, /api/analyze)
 * Dilengkapi pratinjau thumbnail instan, tombol ganti/batal gambar, dan statistik komparasi mendalam.
 */

const views = [...document.querySelectorAll(".view")];
const navItems = [...document.querySelectorAll("[data-route]")];

const state = {
  coverFile: null,
  stegoFile: null,
  analysisFile: null,
  coverUrl: null,
  stegoDataUrl: null,
  capacityBytes: 0,
};

function setRoute(route) {
  const requested = route || "home";
  const target = document.querySelector(`[data-view="${requested}"]`) ? requested : "home";
  views.forEach((view) => view.classList.toggle("active", view.dataset.view === target));
  navItems.forEach((item) => item.classList.toggle("active", item.dataset.route === target));
  if (location.hash.slice(1) !== target) {
    history.replaceState(null, "", `#${target}`);
  }
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

function imageMeta(file, image, capacityBytes = 0) {
  const capStr = capacityBytes > 0 ? ` · ${formatBytes(capacityBytes)} available` : "";
  return `<strong>${file.name}</strong><span>${image.width} x ${image.height}px · ${formatBytes(file.size)}${capStr}</span>`;
}

function setupImagePicker({
  inputId,
  dropId,
  cardId,
  thumbId,
  metaId,
  cancelBtnId,
  kind,
}) {
  const input = document.getElementById(inputId);
  const drop = document.getElementById(dropId);
  const card = document.getElementById(cardId);
  const thumb = document.getElementById(thumbId);
  const meta = document.getElementById(metaId);
  const cancelBtn = document.getElementById(cancelBtnId);

  const clearSelection = () => {
    input.value = "";
    state[`${kind}File`] = null;
    state[`${kind}Url`] = null;
    if (thumb) thumb.src = "";
    if (meta) meta.innerHTML = "";
    if (card) card.classList.add("hidden");
    if (drop) drop.classList.remove("hidden");

    if (kind === "cover") {
      state.capacityBytes = 0;
      updateCapacity();
      const cp = document.getElementById("coverPreview");
      if (cp) cp.innerHTML = "Cover Image";
      const sz = document.getElementById("resultImageSize");
      if (sz) sz.textContent = "--";
    }
  };

  if (cancelBtn) {
    cancelBtn.addEventListener("click", (e) => {
      e.preventDefault();
      clearSelection();
    });
  }

  input.addEventListener("change", async () => {
    const file = input.files[0];
    if (!file) return;

    readImage(file, async (image, url) => {
      state[`${kind}File`] = file;
      state[`${kind}Url`] = url;

      // 1. Tampilkan thumbnail gambar seketika
      if (thumb) thumb.src = url;
      if (meta) meta.innerHTML = imageMeta(file, image);
      if (drop) drop.classList.add("hidden");
      if (card) card.classList.remove("hidden");

      if (kind === "cover") {
        const cp = document.getElementById("coverPreview");
        if (cp) cp.innerHTML = `<img src="${url}" alt="Cover image preview">`;
        const sz = document.getElementById("resultImageSize");
        if (sz) sz.textContent = `${image.width} x ${image.height}px`;

        // Request kapasitas riil ke backend
        try {
          const fd = new FormData();
          fd.append("image", file);
          const res = await fetch("/api/capacity", { method: "POST", body: fd });
          const json = await res.json();
          if (json.success) {
            state.capacityBytes = json.capacity.max_payload_bytes;
            if (meta) meta.innerHTML = imageMeta(file, image, state.capacityBytes);
            updateCapacity();
          }
        } catch (err) {
          console.warn("Gagal mengecek kapasitas backend:", err);
          state.capacityBytes = Math.max(0, Math.floor((image.width * image.height * 3 - 64) / 8));
          updateCapacity();
        }
      }
    });
  });

  return { clearSelection };
}

function updateCapacity() {
  const message = document.getElementById("messageInput").value;
  const msgBytes = new TextEncoder().encode(message).length;
  // Payload enkripsi overhead: 16 salt + 12 nonce + 16 auth tag = 44 bytes
  const estPayloadBytes = msgBytes > 0 ? msgBytes + 44 : 0;
  const maxBytes = state.capacityBytes || 1;
  const percent = Math.min(100, Math.round((estPayloadBytes / maxBytes) * 100));

  document.getElementById("capacityText").textContent = `${percent}%`;
  document.getElementById("capacityBar").style.width = `${percent}%`;
  document.getElementById("charCount").textContent = `${message.length} / 1000`;
}

// Inisialisasi Image Pickers dengan Thumbnail & Tombol Batal/Ganti
const coverPicker = setupImagePicker({
  inputId: "coverInput",
  dropId: "coverDrop",
  cardId: "coverCard",
  thumbId: "coverThumbImg",
  metaId: "coverMeta",
  cancelBtnId: "coverCancelBtn",
  kind: "cover",
});

const stegoPicker = setupImagePicker({
  inputId: "stegoInput",
  dropId: "stegoDrop",
  cardId: "stegoCard",
  thumbId: "stegoThumbImg",
  metaId: "stegoMeta",
  cancelBtnId: "stegoCancelBtn",
  kind: "stego",
});

const analysisPicker = setupImagePicker({
  inputId: "analysisInput",
  dropId: "analysisDrop",
  cardId: "analysisCard",
  thumbId: "analysisThumbImg",
  metaId: "analysisMeta",
  cancelBtnId: "analysisCancelBtn",
  kind: "analysis",
});

function resetHide() {
  document.getElementById("hideResult").classList.add("hidden");
  document.getElementById("messageInput").value = "";
  document.getElementById("hideKey").value = "";
  document.getElementById("charCount").textContent = "0 / 1000";
  document.getElementById("capacityText").textContent = "0%";
  document.getElementById("capacityBar").style.width = "0%";
  coverPicker.clearSelection();
  state.stegoDataUrl = null;
}

async function handleHideMessage() {
  const message = document.getElementById("messageInput").value.trim();
  const key = document.getElementById("hideKey").value.trim();

  if (!state.coverFile) {
    alert("Silakan pilih citra cover terlebih dahulu.");
    return;
  }
  if (!message) {
    alert("Pesan rahasia tidak boleh kosong.");
    return;
  }
  if (!key) {
    alert("Stego-key wajib diisi.");
    return;
  }

  // Tampilkan loading screen
  setRoute("processing");

  try {
    const formData = new FormData();
    formData.append("cover", state.coverFile);
    formData.append("message", message);
    formData.append("key", key);

    const res = await fetch("/api/embed", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();

    if (!data.success) {
      alert("Proses Embedding Gagal: " + (data.error || "Unknown error"));
      setRoute("hide");
      return;
    }

    // Berhasil: simpan stego data url
    state.stegoDataUrl = data.stego_image;

    // Tampilkan pratinjau citra stego
    const preview = document.getElementById("stegoPreview");
    preview.innerHTML = `<img src="${state.stegoDataUrl}" alt="Stego image preview"><small>Protected</small>`;

    // Tampilkan pratinjau Difference Heatmap (Peta Sebaran PRNG)
    const diffPreview = document.getElementById("diffPreview");
    if (diffPreview && data.difference_map) {
      diffPreview.innerHTML = `<img src="${data.difference_map}" alt="Difference Map"><small>PRNG Spread (×255)</small>`;
    }

    // Update spesifikasi metrik
    document.getElementById("resultMessageSize").textContent = `${data.payload_bytes} B (${data.message_chars} chars)`;
    const compEl = document.getElementById("resultCompression");
    if (compEl) {
      if (data.compression && data.compression.is_compressed) {
        compEl.textContent = `zlib -${data.compression.ratio_percent}% (${data.compression.saved_bytes}B saved)`;
        compEl.style.color = "var(--teal)";
      } else {
        compEl.textContent = "Raw (no gain)";
        compEl.style.color = "inherit";
      }
    }
    document.getElementById("resultImageSize").textContent = data.image_size;
    if (document.getElementById("resultPSNR")) {
      document.getElementById("resultPSNR").textContent = `${data.metrics.psnr_db} dB`;
    }
    if (document.getElementById("resultMSE")) {
      document.getElementById("resultMSE").textContent = `${data.metrics.mse}`;
    }
    if (document.getElementById("resultCapacity")) {
      document.getElementById("resultCapacity").textContent = `${data.capacity_percent}%`;
    }
    if (document.getElementById("resultChangedPixels")) {
      document.getElementById("resultChangedPixels").textContent = `${data.metrics.changed_pixels} px (${data.metrics.pixel_change_percent}%)`;
    }

    // Update Kotak Statistik Komparasi Piksel Mendalam
    if (data.metrics) {
      const m = data.metrics;
      const setVal = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
      };

      setVal("statUnchangedPx", `${m.unchanged_pixels.toLocaleString()} px`);
      setVal("statUnchangedPct", `${m.unchanged_percent}% identik sempurna`);
      setVal("statChangedPx", `${m.changed_pixels.toLocaleString()} px`);
      setVal("statChangedPct", `${m.pixel_change_percent}% sebaran PRNG`);
      setVal("fidelityTag", `${m.unchanged_percent}% Identik`);
      setVal("statPsnrBadge", `${m.psnr_db}`);
      setVal("statMaxDelta", `±${m.max_delta || 1} / 255 (0.39%)`);

      if (m.channel_changes) {
        setVal("statChangedR", `${m.channel_changes.r.toLocaleString()} px`);
        setVal("statChangedG", `${m.channel_changes.g.toLocaleString()} px`);
        setVal("statChangedB", `${m.channel_changes.b.toLocaleString()} px`);
      }
    }

    document.getElementById("hideResult").classList.remove("hidden");
    setRoute("hide");
    document.getElementById("hideResult").scrollIntoView({ behavior: "smooth" });

  } catch (err) {
    alert("Terjadi kendala koneksi ke server: " + err.message);
    setRoute("hide");
  }
}

async function handleRevealMessage() {
  const key = document.getElementById("revealKey").value.trim();
  const errorBanner = document.getElementById("revealError");
  const resultCard = document.getElementById("revealResult");

  if (!state.stegoFile) {
    alert("Silakan unggah citra stego terlebih dahulu.");
    return;
  }
  if (!key) {
    alert("Silakan masukkan stego-key.");
    return;
  }

  const revealBtn = document.getElementById("revealButton");
  revealBtn.disabled = true;
  revealBtn.textContent = "Extracting...";

  try {
    const formData = new FormData();
    formData.append("stego", state.stegoFile);
    formData.append("key", key);

    const res = await fetch("/api/extract", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();

    if (data.success) {
      errorBanner.classList.add("hidden");
      resultCard.classList.remove("hidden");
      document.getElementById("revealedText").textContent = data.message;
      resultCard.scrollIntoView({ behavior: "smooth" });
    } else {
      resultCard.classList.add("hidden");
      errorBanner.classList.remove("hidden");
      const errSpan = errorBanner.querySelector("span");
      if (errSpan) errSpan.textContent = data.error || "Stego-key salah atau citra tidak mengandung pesan rahasia HideBit.";
      errorBanner.scrollIntoView({ behavior: "smooth" });
    }
  } catch (err) {
    alert("Gagal menghubungi server ekstraksi: " + err.message);
  } finally {
    revealBtn.disabled = false;
    revealBtn.innerHTML = "Reveal Message <span>-></span>";
  }
}

async function handleSteganalysis() {
  if (!state.analysisFile) {
    alert("Pilih berkas citra yang ingin dianalisis terlebih dahulu.");
    return;
  }

  const analyzeBtn = document.getElementById("analyzeButton");
  const stateLabel = document.getElementById("analysisState");
  analyzeBtn.disabled = true;
  stateLabel.textContent = "Analyzing statistical patterns...";

  try {
    const formData = new FormData();
    formData.append("image", state.analysisFile);

    const res = await fetch("/api/analyze", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();

    if (!data.success) {
      alert("Analisis gagal: " + (data.error || "Unknown error"));
      stateLabel.textContent = "Analysis failed";
      return;
    }

    // 1. Update Skor Kecurigaan (0 - 100)
    const score = Number(data.score) || 0;
    document.getElementById("scoreValue").textContent = score.toFixed(2);
    document.getElementById("scoreRing").style.background = `conic-gradient(var(--teal) ${score * 3.6}deg, #344142 0deg)`;
    stateLabel.textContent = "Analysis complete";

    // 2. Update Tabel Chi-Square per kanal
    const ch = data.channels || {};
    const rows = [
      ["red", "Red", ch.red?.chi_square, ch.red?.degrees_of_freedom, ch.red?.p_value],
      ["green", "Green", ch.green?.chi_square, ch.green?.degrees_of_freedom, ch.green?.p_value],
      ["blue", "Blue", ch.blue?.chi_square, ch.blue?.degrees_of_freedom, ch.blue?.p_value],
    ];

    document.getElementById("channelRows").innerHTML = rows.map(([color, name, chi, dof, p]) => {
      const chiStr = typeof chi === "number" ? chi.toFixed(2) : "--";
      const dofStr = dof !== undefined ? dof : "--";
      const pStr = typeof p === "number" ? p.toFixed(4) : "--";
      return `<tr><td><i class="channel-dot ${color}"></i> ${name}</td><td>${chiStr}</td><td>${dofStr}</td><td>${pStr}</td></tr>`;
    }).join("");

    // 3. Render Visual LSB Planes
    if (data.lsb_planes) {
      const rEl = document.getElementById("lsbRed");
      const gEl = document.getElementById("lsbGreen");
      const bEl = document.getElementById("lsbBlue");
      if (rEl && data.lsb_planes.red) rEl.innerHTML = `<img src="${data.lsb_planes.red}" alt="Red LSB Plane">`;
      if (gEl && data.lsb_planes.green) gEl.innerHTML = `<img src="${data.lsb_planes.green}" alt="Green LSB Plane">`;
      if (bEl && data.lsb_planes.blue) bEl.innerHTML = `<img src="${data.lsb_planes.blue}" alt="Blue LSB Plane">`;
    }

  } catch (err) {
    alert("Gagal melakukan analisis steganalisis: " + err.message);
    stateLabel.textContent = "Error occurred";
  } finally {
    analyzeBtn.disabled = false;
  }
}

// Download berkas citra stego asli
document.getElementById("downloadButton").addEventListener("click", () => {
  if (!state.stegoDataUrl) {
    alert("Citra stego belum tersedia untuk diunduh.");
    return;
  }
  const link = document.createElement("a");
  link.href = state.stegoDataUrl;
  const originalName = state.coverFile ? state.coverFile.name.replace(/\.[^/.]+$/, "") : "stego";
  link.download = `hidebit-${originalName}.png`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
});

// Event Listeners
document.querySelectorAll("a[href^='#']").forEach((link) => {
  link.addEventListener("click", (event) => {
    const route = link.getAttribute("href").slice(1);
    if (document.querySelector(`[data-view="${route}"]`)) {
      event.preventDefault();
      setRoute(route);
    }
  });
});

window.addEventListener("hashchange", () => setRoute(location.hash.slice(1)));
document.getElementById("messageInput").addEventListener("input", updateCapacity);
document.getElementById("hideButton").addEventListener("click", handleHideMessage);
document.getElementById("hideAnother").addEventListener("click", resetHide);
document.getElementById("revealButton").addEventListener("click", handleRevealMessage);
document.getElementById("revealAnother").addEventListener("click", () => {
  document.getElementById("revealResult").classList.add("hidden");
  document.getElementById("revealError").classList.add("hidden");
  document.getElementById("revealKey").value = "";
  stegoPicker.clearSelection();
});
document.getElementById("analyzeButton").addEventListener("click", handleSteganalysis);

document.getElementById("copyButton").addEventListener("click", async (event) => {
  try {
    await navigator.clipboard.writeText(document.getElementById("revealedText").textContent);
    event.currentTarget.textContent = "Copied ✓";
    setTimeout(() => { event.currentTarget.textContent = "Copy Message"; }, 2000);
  } catch {
    event.currentTarget.textContent = "Select to copy";
  }
});

document.querySelectorAll("[data-toggle-password]").forEach((button) => {
  button.addEventListener("click", () => {
    const input = document.getElementById(button.dataset.togglePassword);
    input.type = input.type === "password" ? "text" : "password";
    button.textContent = input.type === "password" ? "Show" : "Hide";
  });
});

setRoute(location.hash.slice(1) || "home");