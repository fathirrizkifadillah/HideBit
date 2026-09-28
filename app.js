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
  referenceFile: null,
  secretFile: null,
  coverUrl: null,
  stegoDataUrl: null,
  capacityBytes: 0,
  payloadMode: "text", // "text" | "file"
  analysisMode: "blind", // "blind" | "compare"
  revealedBlobUrl: null,
  lastAnalysisReport: null,
  lastLsbData: null,
  lsbViewMode: "side-by-side",
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

function optimizeCoverImage(file, image, callback) {
  const maxDim = 1280;
  if (image.width <= maxDim && image.height <= maxDim) {
    callback(file, image, URL.createObjectURL(file));
    return;
  }

  let w = image.width;
  let h = image.height;
  if (w > h) {
    h = Math.round((h * maxDim) / w);
    w = maxDim;
  } else {
    w = Math.round((w * maxDim) / h);
    h = maxDim;
  }

  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(image, 0, 0, w, h);

  canvas.toBlob((blob) => {
    if (!blob) {
      callback(file, image, URL.createObjectURL(file));
      return;
    }
    const cleanName = file.name.replace(/\.[^/.]+$/, "") + ".png";
    const optimizedFile = new File([blob], cleanName, { type: "image/png" });
    const newUrl = URL.createObjectURL(blob);
    const newImg = new Image();
    newImg.onload = () => callback(optimizedFile, newImg, newUrl);
    newImg.src = newUrl;
  }, "image/png");
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
      if (cp) cp.innerHTML = '<span class="placeholder-text">Citra Cover</span>';
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
      const applySelection = (finalFile, finalImg, finalUrl) => {
        state[`${kind}File`] = finalFile;
        state[`${kind}Url`] = finalUrl;

        // 1. Tampilkan thumbnail gambar seketika
        if (thumb) thumb.src = finalUrl;
        if (meta) meta.innerHTML = imageMeta(finalFile, finalImg);
        if (drop) drop.classList.add("hidden");
        if (card) card.classList.remove("hidden");

        if (kind === "cover") {
          const cp = document.getElementById("coverPreview");
          if (cp) cp.innerHTML = `<img src="${finalUrl}" alt="Cover image preview">`;
          const sz = document.getElementById("resultImageSize");
          if (sz) sz.textContent = `${finalImg.width} x ${finalImg.height}px`;

          // Request kapasitas riil ke backend
          fetchCapacity(finalFile, finalImg);
        }
      };

      const fetchCapacity = async (finalFile, finalImg) => {
        try {
          const fd = new FormData();
          fd.append("image", finalFile);
          const res = await fetch("/api/capacity", { method: "POST", body: fd });
          const json = await res.json();
          if (json.success) {
            state.capacityBytes = json.capacity.max_payload_bytes;
            if (meta) meta.innerHTML = imageMeta(finalFile, finalImg, state.capacityBytes);
            updateCapacity();
          }
        } catch (err) {
          console.warn("Gagal mengecek kapasitas backend:", err);
          state.capacityBytes = Math.max(0, Math.floor((finalImg.width * finalImg.height * 3 - 64) / 8));
          updateCapacity();
        }
      };

      if (kind === "cover" && (image.width > 1280 || image.height > 1280)) {
        optimizeCoverImage(file, image, (optFile, optImg, optUrl) => {
          applySelection(optFile, optImg, optUrl);
        });
      } else {
        applySelection(file, image, url);
      }
    });
  });

  return { clearSelection };
}

function updateCapacity() {
  let estPayloadBytes = 0;
  if (state.payloadMode === "file") {
    if (state.secretFile) {
      const fnBytes = new TextEncoder().encode(state.secretFile.name).length;
      // Overhead envelope berkas: 1B tag + 1B fn_len + fnBytes + 16 salt + 12 nonce + 16 auth tag = 46 + fnBytes
      estPayloadBytes = state.secretFile.size + fnBytes + 46;
    }
  } else {
    const message = document.getElementById("messageInput").value;
    const msgBytes = new TextEncoder().encode(message).length;
    // Payload enkripsi teks: 1B tag + 16 salt + 12 nonce + 16 auth tag = 45 bytes
    estPayloadBytes = msgBytes > 0 ? msgBytes + 45 : 0;
    const charCountEl = document.getElementById("charCount");
    if (charCountEl) charCountEl.textContent = `${message.length} / 50000`;
  }

  const maxBytes = state.capacityBytes || 1;
  const percent = Math.min(100, Math.round((estPayloadBytes / maxBytes) * 100));

  const capText = document.getElementById("capacityText");
  const capBar = document.getElementById("capacityBar");
  if (capText) capText.textContent = `${percent}%`;
  if (capBar) {
    capBar.style.width = `${percent}%`;
    if (percent >= 100 && estPayloadBytes > maxBytes) {
      capBar.style.background = "var(--red)";
    } else {
      capBar.style.background = "var(--teal)";
    }
  }
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

const referencePicker = setupImagePicker({
  inputId: "referenceInput",
  dropId: "referenceDrop",
  cardId: "referenceCard",
  thumbId: "referenceThumbImg",
  metaId: "referenceMeta",
  cancelBtnId: "referenceCancelBtn",
  kind: "reference",
});

// Setup Analysis Mode Switcher Tabs
function setupAnalysisModeTabs() {
  const tabBlind = document.getElementById("tabModeBlind");
  const tabCompare = document.getElementById("tabModeCompare");
  const refSection = document.getElementById("referenceSection");
  const uploadTitle = document.getElementById("analysisUploadTitle");
  const uploadSub = document.getElementById("analysisUploadSub");
  const dropLabel = document.getElementById("analysisDropLabel");
  const btnText = document.getElementById("analyzeBtnText");
  const compareMetricsPanel = document.getElementById("compareMetricsPanel");

  if (!tabBlind || !tabCompare) return;

  tabBlind.addEventListener("click", () => {
    state.analysisMode = "blind";
    tabBlind.classList.add("active");
    tabCompare.classList.remove("active");
    if (refSection) refSection.classList.add("hidden");
    if (uploadTitle) uploadTitle.textContent = "Citra untuk Dianalisis";
    if (uploadSub) uploadSub.textContent = "Unggah citra lossless (PNG, BMP, WEBP) untuk inspeksi anomali bit LSB.";
    if (dropLabel) dropLabel.textContent = "Upload Citra Uji";
    if (btnText) btnText.textContent = "Jalankan Analisis Forensik";
    if (compareMetricsPanel) compareMetricsPanel.classList.add("hidden");
  });

  tabCompare.addEventListener("click", () => {
    state.analysisMode = "compare";
    tabCompare.classList.add("active");
    tabBlind.classList.remove("active");
    if (refSection) refSection.classList.remove("hidden");
    if (uploadTitle) uploadTitle.textContent = "Citra Stego (Uji Forensik)";
    if (uploadSub) uploadSub.textContent = "Unggah citra stego yang dicurigai membawa payload tersembunyi.";
    if (dropLabel) dropLabel.textContent = "Upload Citra Stego";
    if (btnText) btnText.textContent = "Bandingkan Citra Asli vs Stego";
  });

  // Toggle Panduan Forensik (Apa yang Dianalisis & Apa Bedanya)
  const guideBtn = document.getElementById("guideToggleBtn");
  const guideContent = document.getElementById("guideContent");
  const guideIcon = document.getElementById("guideToggleIcon");
  if (guideBtn && guideContent) {
    guideBtn.addEventListener("click", () => {
      guideContent.classList.toggle("hidden");
      if (guideIcon) guideIcon.classList.toggle("open");
    });
  }
}
setupAnalysisModeTabs();

// Render dan Kontrol Tampilan Visual LSB Planes (Mode Mandiri vs Dual Komparasi)
function renderLsbPlanes() {
  const grid = document.getElementById("lsbGrid");
  const toggleWrap = document.getElementById("lsbViewToggleWrap");
  if (!grid || !state.lastLsbData?.stego) return;

  const stegoPlanes = state.lastLsbData.stego;
  const coverPlanes = state.lastLsbData.cover;
  const hasCover = Boolean(coverPlanes);

  if (toggleWrap) {
    if (hasCover) {
      toggleWrap.classList.remove("hidden");
    } else {
      toggleWrap.classList.add("hidden");
    }
  }

  const channels = [
    { key: "red", name: "Kanal Merah (R)", color: "red" },
    { key: "green", name: "Kanal Hijau (G)", color: "green" },
    { key: "blue", name: "Kanal Biru (B)", color: "blue" },
  ];

  if (hasCover && state.lsbViewMode === "side-by-side") {
    grid.innerHTML = channels.map((ch) => `
      <div class="lsb-card dual">
        <div class="lsb-card-heading">
          <i class="channel-dot ${ch.color}"></i>
          <strong>${ch.name}</strong>
        </div>
        <div class="lsb-dual-grid">
          <div class="lsb-sub-item">
            <span class="lsb-tag cover">Cover Asli</span>
            <div class="lsb-img">
              <img src="${coverPlanes[ch.key]}" alt="Cover ${ch.name}">
            </div>
          </div>
          <div class="lsb-sub-item">
            <span class="lsb-tag stego">Stego (Disisipi)</span>
            <div class="lsb-img">
              <img src="${stegoPlanes[ch.key]}" alt="Stego ${ch.name}">
            </div>
          </div>
        </div>
      </div>
    `).join("");
  } else {
    // Mode tunggal: tampilkan hanya Stego atau hanya Cover
    const activePlanes = (state.lsbViewMode === "cover" && hasCover) ? coverPlanes : stegoPlanes;
    const tagLabel = (state.lsbViewMode === "cover" && hasCover) ? "Citra Cover Asli" : (hasCover ? "Citra Stego (Disisipi)" : "Bidang Bit-0");

    grid.innerHTML = channels.map((ch) => `
      <div class="lsb-card">
        <div class="lsb-img">
          <img src="${activePlanes[ch.key]}" alt="${ch.name}">
        </div>
        <span>${ch.name} <small style="display:block;font-size:10px;color:var(--muted);font-weight:400;margin-top:3px">${tagLabel}</small></span>
      </div>
    `).join("");
  }
}

function setupLsbViewToggles() {
  const btnSide = document.getElementById("btnLsbSideBySide");
  const btnStego = document.getElementById("btnLsbStegoOnly");
  const btnCover = document.getElementById("btnLsbCoverOnly");
  const tabs = [btnSide, btnStego, btnCover];

  if (!btnSide || !btnStego || !btnCover) return;

  btnSide.addEventListener("click", () => {
    state.lsbViewMode = "side-by-side";
    tabs.forEach((t) => t?.classList.remove("active"));
    btnSide.classList.add("active");
    renderLsbPlanes();
  });

  btnStego.addEventListener("click", () => {
    state.lsbViewMode = "stego";
    tabs.forEach((t) => t?.classList.remove("active"));
    btnStego.classList.add("active");
    renderLsbPlanes();
  });

  btnCover.addEventListener("click", () => {
    state.lsbViewMode = "cover";
    tabs.forEach((t) => t?.classList.remove("active"));
    btnCover.classList.add("active");
    renderLsbPlanes();
  });
}
setupLsbViewToggles();


// Setup Secret File Picker
function setupSecretFilePicker() {
  const input = document.getElementById("secretFileInput");
  const drop = document.getElementById("secretFileDrop");
  const card = document.getElementById("secretFileCard");
  const badge = document.getElementById("secretFileExtBadge");
  const meta = document.getElementById("secretFileMeta");
  const cancelBtn = document.getElementById("secretFileCancelBtn");

  const clear = () => {
    if (input) input.value = "";
    state.secretFile = null;
    if (meta) meta.innerHTML = "";
    if (card) card.classList.add("hidden");
    if (drop) drop.classList.remove("hidden");
    updateCapacity();
  };

  if (cancelBtn) {
    cancelBtn.addEventListener("click", (e) => {
      e.preventDefault();
      clear();
    });
  }

  if (input) {
    input.addEventListener("change", () => {
      const file = input.files[0];
      if (!file) return;
      state.secretFile = file;

      const ext = file.name.includes(".") ? file.name.split(".").pop().toUpperCase().slice(0, 4) : "FILE";
      if (badge) badge.textContent = ext;
      if (meta) {
        meta.innerHTML = `<strong>${file.name}</strong><span>${formatBytes(file.size)} (${file.size.toLocaleString()} bytes)</span>`;
      }
      if (drop) drop.classList.add("hidden");
      if (card) card.classList.remove("hidden");
      updateCapacity();
    });
  }

  return { clear };
}

const secretFilePicker = setupSecretFilePicker();

// Setup Payload Mode Switcher (Teks vs Berkas)
function setupPayloadTabs() {
  const tabText = document.getElementById("tabPayloadText");
  const tabFile = document.getElementById("tabPayloadFile");
  const secText = document.getElementById("textPayloadSection");
  const secFile = document.getElementById("filePayloadSection");

  if (!tabText || !tabFile) return;

  tabText.addEventListener("click", () => {
    state.payloadMode = "text";
    tabText.classList.add("active");
    tabFile.classList.remove("active");
    if (secText) secText.classList.remove("hidden");
    if (secFile) secFile.classList.add("hidden");
    updateCapacity();
  });

  tabFile.addEventListener("click", () => {
    state.payloadMode = "file";
    tabFile.classList.add("active");
    tabText.classList.remove("active");
    if (secFile) secFile.classList.remove("hidden");
    if (secText) secText.classList.add("hidden");
    updateCapacity();
  });
}

setupPayloadTabs();

function resetHide() {
  document.getElementById("hideResult").classList.add("hidden");
  document.getElementById("messageInput").value = "";
  document.getElementById("hideKey").value = "";
  const charCountEl = document.getElementById("charCount");
  if (charCountEl) charCountEl.textContent = "0 / 50000";
  document.getElementById("capacityText").textContent = "0%";
  const capBar = document.getElementById("capacityBar");
  capBar.style.width = "0%";
  capBar.style.background = "var(--teal)";
  coverPicker.clearSelection();
  secretFilePicker.clear();
  state.stegoDataUrl = null;

  const cp = document.getElementById("coverPreview");
  if (cp) cp.innerHTML = '<span class="placeholder-text">Citra Cover</span>';
  const sp = document.getElementById("stegoPreview");
  if (sp) sp.innerHTML = '<span class="placeholder-text">Citra Stego</span>';
  const dp = document.getElementById("diffPreview");
  if (dp) dp.innerHTML = '<span class="placeholder-text">Peta Sebaran PRNG</span>';
}

// Helper fetch dengan penanganan auto-retry pada cold-start/502 dan error JSON yang aman
async function safeFetchJson(url, options = {}, retries = 3, delayMs = 3500) {
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      const res = await fetch(url, options);
      const text = await res.text();
      let data;
      try {
        data = JSON.parse(text);
        return data;
      } catch (parseErr) {
        if (res.status === 502 || res.status === 503 || res.status === 504 || !text) {
          if (attempt < retries) {
            console.warn(`[SafeFetch] Server Render sedang proses wake-up (attempt ${attempt}/${retries}). Menunggu ${delayMs / 1000}s...`);
            await new Promise((r) => setTimeout(r, delayMs));
            continue;
          }
          throw new Error("Server Cloud Render sedang 'cold start' (memulai ulang). Silakan klik tombol sekali lagi dalam beberapa detik.");
        }
        throw new Error(`Respons server tidak valid (HTTP ${res.status}): ${text.slice(0, 100)}`);
      }
    } catch (netErr) {
      if (attempt < retries) {
        console.warn(`[SafeFetch] Network retry (attempt ${attempt}/${retries})...`);
        await new Promise((r) => setTimeout(r, delayMs));
        continue;
      }
      throw netErr;
    }
  }
}

// Keep-Alive Heartbeat: Mencegah server Render tidur (spin-down) selama halaman web terbuka
function setupKeepAlive() {
  const PING_INTERVAL = 9 * 60 * 1000; // Tiap 9 menit (Render tidur otomatis setelah 15 menit)
  setInterval(() => {
    fetch("/health").catch(() => {});
  }, PING_INTERVAL);
}
setupKeepAlive();

async function handleHideMessage() {
  const key = document.getElementById("hideKey").value.trim();

  if (!state.coverFile) {
    alert("Silakan pilih citra cover terlebih dahulu.");
    return;
  }
  if (!key) {
    alert("Stego-key wajib diisi.");
    return;
  }

  const formData = new FormData();
  formData.append("cover", state.coverFile);
  formData.append("key", key);

  if (state.payloadMode === "file") {
    if (!state.secretFile) {
      alert("Silakan pilih berkas rahasia yang ingin disembunyikan.");
      return;
    }
    formData.append("secret_file", state.secretFile);
  } else {
    const message = document.getElementById("messageInput").value.trim();
    if (!message) {
      alert("Pesan rahasia tidak boleh kosong.");
      return;
    }
    formData.append("message", message);
  }

  // Tampilkan loading screen
  setRoute("processing");

  try {
    const data = await safeFetchJson("/api/embed", {
      method: "POST",
      body: formData,
    });

    if (!data.success) {
      alert("Proses Embedding Gagal: " + (data.error || "Unknown error"));
      setRoute("hide");
      return;
    }

    // Berhasil: simpan stego data url
    state.stegoDataUrl = data.stego_image;

    // Tampilkan pratinjau citra stego
    const preview = document.getElementById("stegoPreview");
    if (preview) {
      preview.innerHTML = `<img src="${state.stegoDataUrl}" alt="Citra Stego">`;
    }

    // Tampilkan pratinjau Difference Heatmap (Peta Sebaran PRNG)
    const diffPreview = document.getElementById("diffPreview");
    if (diffPreview && data.difference_map) {
      diffPreview.innerHTML = `<img src="${data.difference_map}" alt="Peta Sebaran PRNG">`;
    }

    // Update spesifikasi metrik
    const pTypeEl = document.getElementById("resultPayloadType");
    if (pTypeEl) {
      pTypeEl.textContent = data.payload_type === "file" ? `Berkas (${data.payload_label})` : "Pesan Teks";
    }

    const pSizeEl = document.getElementById("resultMessageSize");
    if (pSizeEl) {
      if (data.payload_type === "file") {
        pSizeEl.textContent = `${formatBytes(data.raw_bytes)} (${data.payload_bytes} B cipher)`;
      } else {
        pSizeEl.textContent = `${data.payload_bytes} B (${data.message_chars} chars)`;
      }
    }

    const compEl = document.getElementById("resultCompression");
    if (compEl) {
      if (data.compression && data.compression.is_compressed) {
        compEl.textContent = `zlib -${data.compression.ratio_percent}% (${formatBytes(data.compression.saved_bytes)} saved)`;
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
      document.getElementById("resultChangedPixels").textContent = `${data.metrics.changed_pixels.toLocaleString()} px (${data.metrics.pixel_change_percent}%)`;
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
  const textBox = document.getElementById("revealedTextBox");
  const fileCard = document.getElementById("revealedFileCard");
  const copyBtn = document.getElementById("copyButton");

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

    const data = await safeFetchJson("/api/extract", {
      method: "POST",
      body: formData,
    });

    if (data.success) {
      errorBanner.classList.add("hidden");
      resultCard.classList.remove("hidden");

      if (data.type === "file") {
        const headEl = document.getElementById("revealResultHeading");
        const subEl = document.getElementById("revealResultSub");
        if (headEl) headEl.textContent = "Berkas Rahasia Terbaca";
        if (subEl) subEl.textContent = "Berkas biner rahasia berhasil didekripsi dan diverifikasi otentik.";
        if (textBox) textBox.classList.add("hidden");
        if (fileCard) fileCard.classList.remove("hidden");
        if (copyBtn) copyBtn.classList.add("hidden");

        const ext = data.filename && data.filename.includes(".") ? data.filename.split(".").pop().toUpperCase().slice(0, 4) : "FILE";
        const badge = document.getElementById("revealedFileBadge");
        if (badge) badge.textContent = ext;

        const fnEl = document.getElementById("revealedFileName");
        if (fnEl) fnEl.textContent = data.filename;

        const szEl = document.getElementById("revealedFileSize");
        if (szEl) szEl.textContent = `${formatBytes(data.size)} (${data.size.toLocaleString()} bytes)`;

        // Konversi base64 string kembali menjadi Blob biner
        const binaryStr = atob(data.file_data);
        const len = binaryStr.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) {
          bytes[i] = binaryStr.charCodeAt(i);
        }
        const blob = new Blob([bytes], { type: "application/octet-stream" });

        if (state.revealedBlobUrl) {
          URL.revokeObjectURL(state.revealedBlobUrl);
        }
        state.revealedBlobUrl = URL.createObjectURL(blob);

        const dlBtn = document.getElementById("downloadRevealedFileBtn");
        if (dlBtn) {
          dlBtn.href = state.revealedBlobUrl;
          dlBtn.download = data.filename;
        }
      } else {
        const headEl = document.getElementById("revealResultHeading");
        const subEl = document.getElementById("revealResultSub");
        if (headEl) headEl.textContent = "Pesan Rahasia Terbaca";
        if (subEl) subEl.textContent = "Pesan teks rahasia berhasil didekripsi dan diverifikasi otentik.";
        if (fileCard) fileCard.classList.add("hidden");
        if (textBox) textBox.classList.remove("hidden");
        if (copyBtn) copyBtn.classList.remove("hidden");
        document.getElementById("revealedText").textContent = data.message;
      }

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

  if (state.analysisMode === "compare" && !state.referenceFile) {
    alert("Dalam Mode Komparasi, berkas Citra Referensi Asli (Cover) wajib diunggah.");
    return;
  }

  const analyzeBtn = document.getElementById("analyzeButton");
  const origBtnHtml = analyzeBtn.innerHTML;
  const progressBanner = document.getElementById("analysisProgressBanner");
  
  analyzeBtn.disabled = true;
  analyzeBtn.innerHTML = `<span>Menganalisis Forensik...</span> <div class="spinner-sm"></div>`;
  if (progressBanner) progressBanner.classList.remove("hidden");

  try {
    const formData = new FormData();
    formData.append("image", state.analysisFile);
    if (state.analysisMode === "compare" && state.referenceFile) {
      formData.append("reference", state.referenceFile);
    }

    const data = await safeFetchJson("/api/analyze", {
      method: "POST",
      body: formData,
    });

    if (!data.success) {
      alert("Analisis gagal: " + (data.error || "Unknown error"));
      return;
    }

    // 1. Update Skor Kecurigaan (0 - 100)
    const score = Number(data.score) || 0;
    document.getElementById("scoreValue").textContent = score.toFixed(2);
    
    // Gradien dinamis sesuai level kecurigaan
    let ringColor = "var(--teal)";
    if (score >= 65) ringColor = "var(--red)";
    else if (score >= 35) ringColor = "var(--yellow)";
    document.getElementById("scoreRing").style.background = `conic-gradient(${ringColor} ${score * 3.6}deg, #344142 0deg)`;

    // 2. Render Vonis Forensik Komprehensif
    // Jika Mode Komparasi aktif dan ada hasil komparasi, prioritaskan vonis komparasi
    let verdict = data.verdict || {};
    if (state.analysisMode === "compare" && data.comparison && data.comparison.comparison_verdict) {
      verdict = data.comparison.comparison_verdict;
    }

    const verdictCard = document.getElementById("forensicVerdictCard");
    const verdictBanner = document.getElementById("verdictBanner");
    const verdictBadge = document.getElementById("verdictBadge");
    const verdictTitle = document.getElementById("verdictTitle");
    const verdictNarrative = document.getElementById("verdictNarrative");
    const verdictAdvice = document.getElementById("verdictAdvice");
    const verdictRevealLink = document.getElementById("verdictRevealLink");

    if (verdictCard && verdictBanner) {
      verdictCard.classList.remove("hidden");
      verdictBanner.className = "verdict-banner " + (
        verdict.level === "CLEAN" ? "clean" :
        (verdict.level === "SUSPICIOUS" ? "suspicious" : "anomaly")
      );
      if (verdictBadge) verdictBadge.textContent = verdict.badge_label || "STATUS FORENSIK";
      if (verdictTitle) verdictTitle.textContent = verdict.title || "Hasil Pemeriksaan Forensik";
      if (verdictNarrative) verdictNarrative.textContent = verdict.narrative || "";
      if (verdictAdvice) verdictAdvice.textContent = verdict.recommendation || "";
      
      if (verdictRevealLink) {
        if (verdict.level === "ANOMALY_DETECTED" || score >= 65) {
          verdictRevealLink.classList.remove("hidden");
        } else {
          verdictRevealLink.classList.add("hidden");
        }
      }
    }

    // 3. Render Komparasi Citra (Jika Mode Komparasi Aktif)
    const compPanel = document.getElementById("compareMetricsPanel");
    if (data.comparison && data.comparison.has_reference) {
      if (compPanel) {
        compPanel.classList.remove("hidden");
        compPanel.scrollIntoView({ behavior: "smooth", block: "start" });
      }
      const m = data.comparison.metrics || {};
      const psnrEl = document.getElementById("compPsnr");
      const mseEl = document.getElementById("compMse");
      const pixEl = document.getElementById("compPixels");
      const pixPctEl = document.getElementById("compPixelPercent");
      const heatWrap = document.getElementById("compHeatmapWrap");

      if (psnrEl) psnrEl.textContent = `${m.psnr_db ?? "--"} dB`;
      if (mseEl) mseEl.textContent = `${m.mse ?? "--"}`;
      if (pixEl) pixEl.textContent = `${(m.changed_pixels || 0).toLocaleString()} piksel`;
      if (pixPctEl) pixPctEl.textContent = `${m.pixel_change_percent ?? 0}% dari resolusi citra`;
      if (heatWrap && data.comparison.difference_map) {
        heatWrap.innerHTML = `<img src="${data.comparison.difference_map}" alt="Difference Heatmap">`;
      }
    } else {
      if (compPanel) compPanel.classList.add("hidden");
    }

    // 4. Update Tabel Chi-Square per kanal (Statistik Matematis PoV)
    const ch = data.channels || {};
    const channelRows = [
      ["red", "Red", ch.red],
      ["green", "Green", ch.green],
      ["blue", "Blue", ch.blue],
    ];

    document.getElementById("channelRows").innerHTML = channelRows.map(([color, name, c]) => {
      const chiStr = typeof c?.chi_square === "number" ? c.chi_square.toLocaleString("id-ID", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "--";
      const dofStr = c?.degrees_of_freedom !== undefined ? c.degrees_of_freedom : "--";
      const pStr = c?.p_value_display || (typeof c?.p_value === "number" ? (c.p_value < 0.0001 ? "< 0.0001" : c.p_value.toFixed(4)) : "--");
      const balStr = typeof c?.balance_percent === "number" ? `${c.balance_percent}%` : "--";
      
      const st = c?.status || "Normal";
      let statusBadge = '<span class="status-pill safe">Normal</span>';
      if (st === "Anomali") {
        statusBadge = '<span class="status-pill danger">Anomali</span>';
      } else if (st === "Moderat") {
        statusBadge = '<span class="status-pill warn">Moderat</span>';
      }

      return `<tr>
        <td><i class="channel-dot ${color}"></i> ${name}</td>
        <td>${chiStr}</td>
        <td>${dofStr}</td>
        <td><span style="font-family:'Space Grotesk',monospace;font-weight:600">${pStr}</span></td>
        <td>${balStr}</td>
        <td>${statusBadge}</td>
      </tr>`;
    }).join("");

    // 5. Render Visual LSB Planes (Mendukung Dual Komparasi Cover vs Stego)
    if (data.lsb_planes) {
      state.lastLsbData = {
        stego: data.lsb_planes,
        cover: data.comparison?.reference_lsb_planes || null,
      };
      renderLsbPlanes();
    }

    // Simpan objek laporan untuk ekspor berkas .txt
    state.lastAnalysisReport = {
      timestamp: new Date().toLocaleString("id-ID"),
      fileName: state.analysisFile.name,
      fileSize: formatBytes(state.analysisFile.size),
      mode: state.analysisMode === "compare" ? "Dual Comparative Analysis (Cover vs Stego)" : "Blind Steganalysis (Single Image)",
      score: score,
      verdict: verdict,
      channels: ch,
      comparison: data.comparison || null,
      refName: state.referenceFile ? state.referenceFile.name : null
    };

    if (verdictCard) verdictCard.scrollIntoView({ behavior: "smooth", block: "nearest" });

  } catch (err) {
    alert("Gagal melakukan analisis steganalisis: " + err.message);
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtn.innerHTML = origBtnHtml;
    if (progressBanner) progressBanner.classList.add("hidden");
  }
}

function downloadForensicReport() {
  if (!state.lastAnalysisReport) {
    alert("Jalankan analisis citra terlebih dahulu sebelum mengunduh laporan.");
    return;
  }

  const r = state.lastAnalysisReport;
  const ch = r.channels || {};

  let compSection = "";
  if (r.comparison && r.comparison.has_reference) {
    const m = r.comparison.metrics || {};
    compSection = `
========================================================================
  KOMPARASI KUALITAS CITRA (COVER VS STEGO)
========================================================================
- Citra Referensi Cover : ${r.refName || "Cover Image"}
- PSNR (Peak Signal)    : ${m.psnr_db ?? "--"} dB
- MSE (Mean Squared)    : ${m.mse ?? "--"}
- Piksel Dimodifikasi   : ${(m.changed_pixels || 0).toLocaleString()} (${m.pixel_change_percent ?? 0}%)
- Piksel Utuh           : ${(m.unchanged_pixels || 0).toLocaleString()} (${m.unchanged_percent ?? 100}%)
`;
  }

  const reportContent = `========================================================================
  LAPORAN AUDIT STEGANALISIS FORENSIK CITRA - HIDEBIT
========================================================================
Tanggal & Waktu Pemeriksaan : ${r.timestamp}
Metode Pengujian             : ${r.mode}
Nama Berkas Citra Uji       : ${r.fileName} (${r.fileSize})

------------------------------------------------------------------------
HASIL DIAGNOSIS FORENSIK:
------------------------------------------------------------------------
Skor Kecurigaan Heuristik   : ${r.score.toFixed(2)} / 100
Vonis Pemeriksaan           : ${r.verdict.badge_label || "--"}
Judul Diagnosis             : ${r.verdict.title || "--"}

Narasi Forensik:
${r.verdict.narrative || "--"}

Rekomendasi Tindakan:
${r.verdict.recommendation || "--"}

------------------------------------------------------------------------
PROFIL STATISTIK PASANGAN NILAI (PoV) CHI-SQUARE:
------------------------------------------------------------------------
Kanal Red   : Chi2 = ${ch.red?.chi_square?.toFixed(2) ?? "--"}, DoF = ${ch.red?.degrees_of_freedom ?? "--"}, p-value = ${ch.red?.p_value_display ?? (ch.red?.p_value < 0.0001 ? "< 0.0001" : ch.red?.p_value?.toFixed(4))}, Simetri PoV = ${ch.red?.balance_percent ?? "--"}% [${ch.red?.status ?? "Normal"}]
Kanal Green : Chi2 = ${ch.green?.chi_square?.toFixed(2) ?? "--"}, DoF = ${ch.green?.degrees_of_freedom ?? "--"}, p-value = ${ch.green?.p_value_display ?? (ch.green?.p_value < 0.0001 ? "< 0.0001" : ch.green?.p_value?.toFixed(4))}, Simetri PoV = ${ch.green?.balance_percent ?? "--"}% [${ch.green?.status ?? "Normal"}]
Kanal Blue  : Chi2 = ${ch.blue?.chi_square?.toFixed(2) ?? "--"}, DoF = ${ch.blue?.degrees_of_freedom ?? "--"}, p-value = ${ch.blue?.p_value_display ?? (ch.blue?.p_value < 0.0001 ? "< 0.0001" : ch.blue?.p_value?.toFixed(4))}, Simetri PoV = ${ch.blue?.balance_percent ?? "--"}% [${ch.blue?.status ?? "Normal"}]

Keterangan Ilmiah:
Uji Chi-Square Pairs of Values (PoV) mengukur apakah frekuensi pasangan nilai piksel (2k, 2k+1)
terdistribusi secara wajar (heterogen alami). Pada steganografi LSB teracak (PRNG) dengan muatan
kecil, nilai Chi-Square global tetap tinggi (p-value teoretis < 0.0001) karena modifikasi bit
tersebar tipis, sehingga dianalisis bersama inspeksi visual Bit-0 Plane dan uji komparasi citra asli.
${compSection}
========================================================================
  Diverifikasi oleh Engine Forensik HideBit - Keamanan Informasi & Kriptografi
========================================================================`;

  const blob = new Blob([reportContent], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `laporan-forensik-${r.fileName.replace(/\.[^/.]+$/, "")}.txt`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
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
const exportBtn = document.getElementById("exportReportBtn");
if (exportBtn) exportBtn.addEventListener("click", downloadForensicReport);

// CSPRNG Random Key Generator (Cryptographically Secure)
function generateSecureKey(length = 20) {
  const upper = "ABCDEFGHJKLMNPQRSTUVWXYZ";
  const lower = "abcdefghijkmnopqrstuvwxyz";
  const digits = "23456789";
  const symbols = "!@#$%^&*-_+=?";
  const allChars = upper + lower + digits + symbols;

  const array = new Uint32Array(length);
  window.crypto.getRandomValues(array);

  let keyChars = [
    upper[array[0] % upper.length],
    lower[array[1] % lower.length],
    digits[array[2] % digits.length],
    symbols[array[3] % symbols.length],
  ];

  for (let i = 4; i < length; i++) {
    keyChars.push(allChars[array[i] % allChars.length]);
  }

  // Fisher-Yates shuffle
  const shuffleArray = new Uint32Array(length);
  window.crypto.getRandomValues(shuffleArray);
  for (let i = keyChars.length - 1; i > 0; i--) {
    const j = shuffleArray[i] % (i + 1);
    [keyChars[i], keyChars[j]] = [keyChars[j], keyChars[i]];
  }

  return keyChars.join("");
}

// Evaluate Key Strength & Shannon Entropy
function evaluateKeyStrength(key) {
  if (!key || key.length === 0) {
    return { score: 0, label: "Belum Ada Kunci", entropy: 0, cssClass: "", hint: "Masukkan kata sandi atau klik tombol Generate Strong Key di atas." };
  }

  let poolSize = 0;
  if (/[a-z]/.test(key)) poolSize += 26;
  if (/[A-Z]/.test(key)) poolSize += 26;
  if (/[0-9]/.test(key)) poolSize += 10;
  if (/[^a-zA-Z0-9]/.test(key)) poolSize += 32;

  const entropy = Math.round(key.length * Math.log2(Math.max(2, poolSize)));

  if (key.length < 8 || entropy < 35) {
    return {
      score: 1,
      label: "Lemah",
      entropy,
      cssClass: "weak",
      hint: "Kunci terlalu pendek atau sederhana; sangat rentan terhadap dictionary attack.",
    };
  } else if (key.length < 12 || entropy < 60) {
    return {
      score: 2,
      label: "Sedang",
      entropy,
      cssClass: "medium",
      hint: "Cukup baik, tetapi disarankan menambahkan variasi simbol dan panjang minimal 16 karakter.",
    };
  } else if (key.length < 16 || entropy < 85) {
    return {
      score: 3,
      label: "Kuat",
      entropy,
      cssClass: "strong",
      hint: "Entropi tinggi; memberikan pertahanan solid terhadap serangan brute-force.",
    };
  } else {
    return {
      score: 4,
      label: "Sangat Kuat (Kriptografis)",
      entropy,
      cssClass: "very-strong",
      hint: "Tingkat keamanan maksimal berstandar kriptografi; mustahil ditembus secara komputasi praktis.",
    };
  }
}

function updateKeyStrengthUI() {
  const input = document.getElementById("hideKey");
  if (!input) return;

  const res = evaluateKeyStrength(input.value);
  const labelEl = document.getElementById("keyStrengthLabel");
  const entropyEl = document.getElementById("keyEntropyText");
  const barEl = document.getElementById("keyStrengthBar");
  const hintEl = document.getElementById("keyStrengthHint");

  if (labelEl) labelEl.textContent = res.label;
  if (entropyEl) entropyEl.textContent = `~${res.entropy} bits`;
  if (hintEl) hintEl.textContent = res.hint;

  if (barEl) {
    barEl.className = "key-strength-bar " + res.cssClass;
  }
}

const hideKeyInput = document.getElementById("hideKey");
if (hideKeyInput) {
  hideKeyInput.addEventListener("input", updateKeyStrengthUI);
}

const genKeyBtn = document.getElementById("generateKeyBtn");
if (genKeyBtn) {
  genKeyBtn.addEventListener("click", () => {
    const newKey = generateSecureKey(20);
    const input = document.getElementById("hideKey");
    if (input) {
      input.value = newKey;
      input.type = "text";
      const toggleBtn = document.querySelector('[data-toggle-password="hideKey"]');
      if (toggleBtn) toggleBtn.textContent = "Hide";
      updateKeyStrengthUI();
    }
  });
}

const copyKeyBtn = document.getElementById("copyKeyBtn");
if (copyKeyBtn) {
  copyKeyBtn.addEventListener("click", async () => {
    const input = document.getElementById("hideKey");
    if (!input || !input.value) {
      alert("Belum ada kunci untuk disalin. Masukkan kunci atau klik Generate Strong Key.");
      return;
    }
    try {
      await navigator.clipboard.writeText(input.value);
      copyKeyBtn.textContent = "Tersalin!";
      setTimeout(() => { copyKeyBtn.textContent = "Salin Kunci"; }, 2000);
    } catch {
      alert("Kunci Anda: " + input.value);
    }
  });
}

document.getElementById("copyButton").addEventListener("click", async (event) => {
  try {
    await navigator.clipboard.writeText(document.getElementById("revealedText").textContent);
    event.currentTarget.textContent = "Tersalin";
    setTimeout(() => { event.currentTarget.textContent = "Salin Pesan"; }, 2000);
  } catch {
    event.currentTarget.textContent = "Pilih untuk Salin";
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