// --- CONFIGURATION & STATE ---
const API_BASE_URL = "http://localhost:8000/api/v1";
let VIDEO_ID = null;
let statusInterval = null;

// --- DOM ELEMENTS ---
const uploadSection = document.getElementById("uploadSection");
const videoInfo = document.getElementById("videoInfo");
const actionSection = document.getElementById("actionSection");
const statusSection = document.getElementById("statusSection");
const statusList = document.getElementById("statusList");
const videoIdSpan = document.getElementById("videoId");

const chatContainer = document.getElementById('chatContainer');
const chatInput = document.querySelector('.chat-input-area textarea');
const sendBtn = document.querySelector('.send-btn');

const processBtn = document.getElementById("processBtn");
const transcriptBtn = document.getElementById("transcriptBtn");
const summaryBtn = document.getElementById("summaryBtn");

// --- 1. VIDEO MANAGEMENT (UPLOAD/LIST/SELECT) ---

async function uploadVideo() {
    const fileInput = document.getElementById("videoFile");
    if (!fileInput.files.length) return alert("Select a video");

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    uploadSection.classList.add("hidden");

    try {
        const res = await fetch(`${API_BASE_URL}/videos/upload`, {
            method: "POST",
            body: formData
        });
        const data = await res.json();

        setGlobalVideoContext(data.video_id);
        videoInfo.classList.remove("hidden");
        actionSection.classList.remove("hidden");
    } catch (e) {
        alert("Upload failed");
        uploadSection.classList.remove("hidden");
    }
}

async function listVideos() {
    try {
        const res = await fetch(`${API_BASE_URL}/videos/list`);
        const data = await res.json();
        renderVideoLibrary(data.videos);
    } catch (error) {
        console.error("Failed to fetch videos:", error);
    }
}

function renderVideoLibrary(videos) {
    const container = document.getElementById("videoListContainer");
    if (!container) return;
    container.innerHTML = "";

    videos.forEach(video => {
        const id = video.id;
        const thumbUrl = video.thumbnail_path ? `${API_BASE_URL.replace('/api/v1', '')}/static/${video.thumbnail_path}` : null;

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
    setGlobalVideoContext(id);
    
    videoInfo.classList.remove("hidden");
    statusSection.classList.remove("hidden");
    
    const res = await fetch(`${API_BASE_URL}/videos/${id}/status`);
    const data = await res.json();
    
    renderStatus(data);
    updateButtonStates(data.status);
    listVideos(); // Refresh active class in list
}

// Helper to keep Chat and Video ID in sync
function setGlobalVideoContext(id) {
    VIDEO_ID = id;
    if(videoIdSpan) videoIdSpan.textContent = id;
    console.log("Global context set to:", id);
    
    // Clear chat when switching videos (Optional - like ChatGPT new thread)
    chatContainer.innerHTML = '<p class="empty-msg">Chatting about video: ' + id + '</p>';
}

// --- 2. PROCESSING & STATUS ---

async function processVideo() {
    statusSection.classList.remove("hidden");
    processBtn.disabled = true;

    await fetch(`${API_BASE_URL}/videos/${VIDEO_ID}/process`, { method: "POST" });
    startStatusPolling();
}

function startStatusPolling() {
    if (statusInterval) clearInterval(statusInterval);
    statusInterval = setInterval(async () => {
        const res = await fetch(`${API_BASE_URL}/videos/${VIDEO_ID}/status`);
        const data = await res.json();

        renderStatus(data);
        updateButtonStates(data.status);

        if (["processed", "failed", "cancelled"].includes(data.status)) {
            clearInterval(statusInterval);
        }
    }, 2000);
}

function updateButtonStates(status) {
    const isDone = status === "processed" || status === "failed" || status === "cancelled";
    const isFailed = status === "failed" || status === "cancelled";
    transcriptBtn.disabled = !isDone;
    summaryBtn.disabled = !isDone;
    processBtn.disabled = (status === "processed" || status === "uploaded");

    if (isFailed) {
        transcriptBtn.disabled = true;
        summaryBtn.disabled = true;
        processBtn.textContent = "Reprocess";
    }
    if (status === "processed") {
        processBtn.textContent = "Processed";
    }
}

function renderStatus(data) {
    statusList.innerHTML = "";
    const thumbUrl = data.thumbnail_path ? `${API_BASE_URL.replace('/api/v1', '')}/static/${data.thumbnail_path}` : '';
    const card = document.createElement("div");
    card.classList.add("status-card");

    card.innerHTML = `
        ${thumbUrl ? `<img src="${thumbUrl}" class="video-thumbnail" />` : `<div class="no-thumb">No Preview</div>`}
        <p><strong>Status:</strong> <span style="color:${getStatusColor(data.status)};">${data.status}</span></p>
        <div class="progress-bar-container">
            <div class="progress-bar" style="width:${(data.progress || 0) * 100}%;"></div>
        </div>
        <p><small>${data.message || ""}</small></p>
    `;
    statusList.appendChild(card);
}

function getStatusColor(status) {
    const colors = { processing: "orange", processed: "green", failed: "red", cancelled: "gray" };
    return colors[status] || "gray";
}

// --- 3. CHAT FUNCTIONALITY (VISI-AGENT) ---

function appendMessage(text, isAi = false) {
    const emptyMsg = chatContainer.querySelector('.empty-msg, .empty-state');
    if (emptyMsg) emptyMsg.remove();

    const wrapper = document.createElement('div');
    wrapper.className = `message-wrapper ${isAi ? 'ai' : 'user'}`;
    wrapper.innerHTML = `
        <div class="avatar">${isAi ? 'VA' : 'U'}</div>
        <div class="message-content">${text}</div>
    `;
    chatContainer.appendChild(wrapper);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    return wrapper;
}

async function handleSendMessage() {
    const question = chatInput.value.trim();
    if (!question) return;
    if (!VIDEO_ID) return alert("Please select or upload a video first!");

    appendMessage(question, false);
    chatInput.value = '';
    chatInput.style.height = 'auto';

    // Add thinking state
    const aiMsgWrapper = appendMessage("Thinking...", true);
    const contentDiv = aiMsgWrapper.querySelector('.message-content');

    try {
        const response = await fetch(`${API_BASE_URL}/query/ask`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                video_id: VIDEO_ID,
                question: question,
                include_timestamps: true,
                query_type: "natural_language"
            })
        });

        const data = await response.json();
        if (response.ok) {
            contentDiv.innerText = data.answer;
            if (data.timestamps?.length > 0) {
                const tsHtml = data.timestamps.map(ts => `<button class="ts-badge" onclick="seekTo(${ts})">${ts}s</button>`).join('');
                contentDiv.innerHTML += `<div class="ts-container">${tsHtml}</div>`;
            }
        } else {
            contentDiv.innerText = "Error: " + (data.detail || "I couldn't process that.");
        }
    } catch (error) {
        contentDiv.innerText = "Connection lost. Is the backend running?";
    }
}

// --- EVENT LISTENERS ---

chatInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + "px";
});

sendBtn.addEventListener('click', handleSendMessage);
chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSendMessage();
    }
});

window.onload = listVideos;