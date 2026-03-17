let VIDEO_ID = null;
let statusInterval = null;

const uploadSection = document.getElementById("uploadSection");
const videoInfo = document.getElementById("videoInfo");
const actionSection = document.getElementById("actionSection");
const statusSection = document.getElementById("statusSection");
const outputSection = document.getElementById("outputSection");

const videoIdSpan = document.getElementById("videoId");
const statusList = document.getElementById("statusList");
const output = document.getElementById("output");

const processBtn = document.getElementById("processBtn");
const transcriptBtn = document.getElementById("transcriptBtn");
const summaryBtn = document.getElementById("summaryBtn");

const transcriptSection = document.getElementById("transcriptSection");
const summarySection = document.getElementById("summarySection");
const transcriptOutput = document.getElementById("transcriptOutput");
const summaryOutput = document.getElementById("summaryOutput");


async function uploadVideo() {
    const fileInput = document.getElementById("videoFile");
    if (!fileInput.files.length) return alert("Select a video");

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    uploadSection.classList.add("hidden");

    const res = await fetch("http://localhost:8000/api/v1/videos/upload", {
        method: "POST",
        body: formData
    });
    const data = await res.json();

    VIDEO_ID = data.video_id;
    videoIdSpan.textContent = VIDEO_ID;
    videoInfo.classList.remove("hidden");
    actionSection.classList.remove("hidden");
}

async function processVideo() {
    statusSection.classList.remove("hidden");
    statusList.innerHTML = "";

    // Disable process button
    processBtn.disabled = true;
    transcriptBtn.disabled = true;
    summaryBtn.disabled = true;

    await fetch(`http://localhost:8000/api/v1/videos/${VIDEO_ID}/process`, { method: "POST" });

    startStatusPolling();
}

function startStatusPolling() {
    statusInterval = setInterval(async () => {
        const res = await fetch(`http://localhost:8000/api/v1/videos/${VIDEO_ID}/status`);
        const data = await res.json();

        renderStatus(data);

        if (data.status === "completed") {
            clearInterval(statusInterval);
            // Enable transcript and summary
            transcriptBtn.disabled = false;
            summaryBtn.disabled = false;
        }
    }, 2000);
}

function renderStatus(data) {
    statusList.innerHTML = "";

    const card = document.createElement("div");
    card.classList.add("status-card");

    card.innerHTML = `
        <p><strong>Video ID:</strong> ${data.video_id || VIDEO_ID}</p>
        <p><strong>Status:</strong> <span style="color:${getStatusColor(data.status)}; font-weight:bold;">${data.status}</span></p>
        <p><strong>Current Stage:</strong> ${data.current_stage}</p>
        <div class="progress-bar-container">
            <div class="progress-bar" style="width:${data.progress || 0}%;"></div>
            <span class="progress-text">${data.progress || 0}%</span>
        </div>
        <p><strong>Message:</strong> ${data.message || ""}</p>
        ${data.error ? `<p style="color:red;"><strong>Error:</strong> ${data.error}</p>` : ""}
    `;

    statusList.appendChild(card);
}

function getStatusColor(status) {
    if (status === "processing") return "orange";
    if (status === "completed") return "green";
    if (status === "failed") return "red";
    return "gray";
}


async function fetchTranscript() {
    const res = await fetch(`http://localhost:8000/api/v1/videos/${VIDEO_ID}/transcript`);
    const data = await res.json();
    transcriptSection.classList.remove("hidden");
    transcriptOutput.textContent = JSON.stringify(data, null, 2);
}

async function fetchSummary() {
    const res = await fetch(`http://localhost:8000/api/v1/videos/${VIDEO_ID}/summary`);
    const data = await res.json();
    summarySection.classList.remove("hidden");
    summaryOutput.textContent = JSON.stringify(data, null, 2);
}

