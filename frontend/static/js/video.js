
let VIDEO_ID = null;
let statusInterval = null;

const uploadSection = document.getElementById("uploadSection");
const videoInfo = document.getElementById("videoInfo");
const actionSection = document.getElementById("actionSection");
const statusSection = document.getElementById("statusSection");
const outputSection = document.getElementById("outputSection");

const videoIdSpan = document.getElementById("videoId");
const statusList = document.getElementById("statusList");
const videoList = document.getElementById("videoList");
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

// UPLOADED = "uploaded"
// PROCESSING = "processing"
// TRANSCRIBING = "transcribing"
// ANALYZING = "analyzing"
// INDEXING = "indexing"
// COMPLETED = "completed"
// FAILED = "failed"
// QUEUED = "queued"
// CANCELLED = "cancelled"


async function listVideos() {
    try {
        const res = await fetch("http://localhost:8000/api/v1/videos/list");
        const data = await res.json();
        renderVideoLibrary(data.videos);
    } catch (error) {
        console.error("Failed to fetch videos:", error);
    }
}
function renderVideoLibrary(videos) {
    const container = document.getElementById("videoListContainer");
    container.innerHTML = "";

    videos.forEach(video => {
        // Assume 'video' is the metadata object returned from your /list endpoint
        const id = video.id;
        // The path stored in DB is likely "thumbnails/uuid.jpg"
        const thumbUrl = video.thumbnail_path 
            ? `http://localhost:8000/static/${video.thumbnail_path}` 
            : null;

        const item = document.createElement("div");
        item.classList.add("video-item");
        if (id === VIDEO_ID) item.classList.add("active");

        item.innerHTML = `
            <div class="video-item-info" onclick="selectVideo('${id}')">
                ${thumbUrl 
                    ? `<img src="${thumbUrl}" class="list-thumb" onerror="this.src='/static/css/placeholder.png'">` 
                    : `<div class="list-thumb-placeholder">🎬</div>`
                }
                <div class="video-details">
                    <span class="video-id-text">${id}</span>
                    <span class="video-status-tag ${video.status}">${video.status}</span>
                </div>
            </div>
            <button class="btn-delete" onclick="deleteVideo('${id}', event)">✕</button>
        `;
        container.appendChild(item);
    });
}
async function selectVideo(id) {
    VIDEO_ID = id;
    document.getElementById("videoId").textContent = VIDEO_ID;
    
    // Show sections
    videoInfo.classList.remove("hidden");
    
    // Check status immediately to enable/disable buttons
    const res = await fetch(`http://localhost:8000/api/v1/videos/${VIDEO_ID}/status`);
    const data = await res.json();
    
    statusSection.classList.remove("hidden");
    renderStatus(data);
    
    // Enable buttons if already done
    const isDone = data.status === "completed";
    transcriptBtn.disabled = !isDone;
    summaryBtn.disabled = !isDone;
    processBtn.disabled = (data.status === "processing" || data.status === "queued");

    // Re-render library to show active state
    listVideos();
}

async function deleteVideo(id, event) {
    event.stopPropagation(); // Prevent selectVideo from firing
    if (!confirm("Delete this video and all associated data?")) return;

    try {
        await fetch(`http://localhost:8000/api/v1/videos/${id}`, { method: "DELETE" });
        if (VIDEO_ID === id) {
            VIDEO_ID = null;
            videoInfo.classList.add("hidden");
            statusSection.classList.add("hidden");
        }
        listVideos();
    } catch (error) {
        alert("Delete failed");
    }
}


// Helper to check status manually without starting a long poll
async function checkCurrentStatus() {
    const res = await fetch(`http://localhost:8000/api/v1/videos/${VIDEO_ID}/status`);
    const data = await res.json();
    statusSection.classList.remove("hidden");
    renderStatus(data);
    
    // Enable buttons if already completed
    if (data.status === "completed") {
        transcriptBtn.disabled = false;
        summaryBtn.disabled = false;
    }
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
        }else if (data.status === "failed") {
            clearInterval(statusInterval);
            alert("Video processing failed. Please try again.");
        }else if (data.status === "cancelled") {
            clearInterval(statusInterval);
            alert("Video processing was cancelled.");
        }else if (data.status === "queued") {
            clearInterval(statusInterval);
            alert("Video processing is queued. Please wait.");
        }else if (data.status === "processing") {
            // Optionally, you can add a timeout to stop polling after a certain period
            // setTimeout(() => {
            //     clearInterval(statusInterval);
            //     alert("Video processing is taking longer than expected. Please check back later.");
            //

        }
    
    }, 2000);
}


function renderStatus(data) {
    statusList.innerHTML = "";
    const thumbHtml = data.thumbnail_path 
        ? `<img src="/static/${data.thumbnail_path}" class="video-thumbnail" />` 
        : `<div class="no-thumb">No Preview</div>`;
    const card = document.createElement("div");
    card.classList.add("status-card");

    card.innerHTML = `
        ${thumbHtml}
        <p><strong>Video ID:</strong> ${data.video_id || VIDEO_ID}</p>
        <p><strong>Status:</strong> <span style="color:${getStatusColor(data.status)}; font-weight:bold;">${data.status}</span></p>
        <p><strong>Current Stage:</strong> ${data.current_stage}</p>
        <div class="progress-bar-container">
            <div class="progress-bar" style="width:${data.progress * 100 || 0}%;"></div>
            <span class="progress-text">${data.progress * 100 || 0}%</span>
        </div>
        <p><strong>Message:</strong> ${data.message || ""}</p>
        ${data.error ? `<p style="color:red;"><strong>Error:</strong> ${data.error}</p>` : ""}
    `;

    statusList.appendChild(card);
}
function renderVideosList(data) {
    videoList.innerHTML = "";

    const card = document.createElement("div");
    card.classList.add("status-card");

    for (const video of data.videos) {
        const videoItem = document.createElement("p");
        videoItem.textContent = video;
        card.appendChild(videoItem);
    }

    card.innerHTML = `
        <p><strong>Video ID:</strong> ${data.video_id || VIDEO_ID}</p>
        <p><strong>Status:</strong> <span style="color:${getStatusColor(data.status)}; font-weight:bold;">${data.status}</span></p>
        <p><strong>Current Stage:</strong> ${data.current_stage}</p>
        <div class="progress-bar-container">
            <div class="progress-bar" style="width:${data.progress * 100 || 0}%;"></div>
            <span class="progress-text">${data.progress * 100 || 0}%</span>
        </div>
        <p><strong>Message:</strong> ${data.message || ""}</p>
        ${data.error ? `<p style="color:red;"><strong>Error:</strong> ${data.error}</p>` : ""}
    `;

    videoList.appendChild(card);
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
    summaryOutput.textContent = data.summary;
}

// Initial load
window.onload = listVideos;