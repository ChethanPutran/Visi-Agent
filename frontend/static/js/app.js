const API_BASE = "http://localhost:8000/api/v1";
let VIDEO_ID = null;
let ALL_VIDEOS = [];

// --- Video Management ---
/**
 * Selects a video and updates the UI based on its current state.
 */
/**
 * Selects a video, updates the UI, and loads chat history.
 */
async function selectVideo(id) {
    VIDEO_ID = id;
    document.getElementById("videoId").textContent = id;
    document.getElementById("videoInfo").classList.remove("hidden");
    
    // Update Chat Context Header
    const chatTitle = document.querySelector(".header-info h2");
    if (chatTitle) chatTitle.innerText = `Chatting: ${id.slice(0, 8)}...`;

    // 1. Fetch and Update Status/Buttons
    try {
        const res = await fetch(`${API_BASE}/videos/${id}/status`);
        const data = await res.json();
        renderStatus(data);
        updateButtons(data.status);
    } catch (e) {
        console.log("No status yet.");
        updateButtons("uploaded"); 
    }

    // 2. Load Chat History for this specific video
    await loadChatHistory(id);
    
    renderLibrary(); // Refresh active class in library
}
/**
 * Fetches chat history from the backend and renders it.
 */
async function loadChatHistory(videoId) {
    const container = document.getElementById("chatContainer");
    
    // Clear existing messages and show a small loader or empty state
    container.innerHTML = '<div class="empty-state"><p><i class="fas fa-spinner fa-spin"></i> Loading history...</p></div>';

    try {
        const response = await fetch(`${API_BASE}/query/history/${videoId}`);
        const data = await response.json();

        // Clear the "Loading" message
        container.innerHTML = "";

        if (data.history && data.history.length > 0) {
            data.history.forEach(msg => {
                // Determine if message is AI or User based on your backend schema
                // Assuming schema: { role: "user" | "assistant", content: "..." }
                const isAi = (msg.role === "assistant" || msg.role === "ai");
                appendMessage(msg.content, isAi);
            });
        } else {
            // If no history exists, show the default welcome
            container.innerHTML = `
                <div class="empty-state">
                    <div class="icon-circle"><i class="fas fa-robot"></i></div>
                    <p>No previous chat found for this video. Ask a question to start!</p>
                </div>`;
        }
    } catch (error) {
        console.error("Failed to fetch chat history:", error);
        container.innerHTML = '<div class="empty-state"><p>Could not load chat history.</p></div>';
    }
}

/**
 * Logic-driven button states:
 * - "Process": Enabled ONLY if the video isn't already processing or finished.
 * - "Transcript/Summary": Enabled ONLY if the video is finished.
 */
function updateButtons(status) {
    const processBtn = document.getElementById("processBtn");
    const transcriptBtn = document.getElementById("transcriptBtn");
    const summaryBtn = document.getElementById("summaryBtn");

    const isProcessing = (status === "processing" || status === "queued");
    const isDone = (status === "processed" || status === "failed");

    // Enable Process button ONLY if it's not currently working and not already done
    processBtn.disabled = (isProcessing || isDone);

    // Enable analysis buttons only when finished
    transcriptBtn.disabled = !isDone;
    summaryBtn.disabled = !isDone;
    
    // Visual cue for the process button
    if (isProcessing) {
        processBtn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Processing...`;
    } else if (isDone) {
        processBtn.innerHTML = `<i class="fas fa-check"></i> Processed`;
    } else {
        processBtn.innerHTML = `▶ Process Video`;
    }
}

/**
 * Starts the processing and toggles button states immediately
 */
async function processVideo() {
    if (!VIDEO_ID) return;

    // UI Feedback: Disable immediately to prevent double-clicks
    updateButtons("processing");
    document.getElementById("statusSection").classList.remove("hidden");

    try {
        let response = await fetch(`${API_BASE}/videos/${VIDEO_ID}/process`, { method: "POST" });
        console.log("Process request sent, awaiting response...",response);
        response = await response.json();
        if (!response.success) throw new Error("Failed to start processing");
        
        // Start polling for updates
        const poller = setInterval(async () => {
            const res = await fetch(`${API_BASE}/videos/${VIDEO_ID}/status`);
            const data = await res.json();
            
            renderStatus(data);
            updateButtons(data.status);
            console.log("Polled status:", data.status);

            if (["processed", "failed"].includes(data.status)) {
                console.log("Processing finished with status:", data.status);
                clearInterval(poller);
            }
        }, 1000); // Poll every 1000 ms
    } catch (e) {
        alert("Failed to start processing.");
        updateButtons("failed");
    }
}
function renderStatus(data) {
    if (!data) return;

    const container = document.getElementById("statusList");
    const statusSection = document.getElementById("statusSection");
    statusSection.classList.remove("hidden");

    // 1. Try to find the existing card for this specific video
    let card = document.querySelector(`[data-video-id="${data.video_id}"]`);

    // 2. If it doesn't exist, create the initial shell
    if (!card) {
        card = document.createElement('div');
        card.setAttribute('data-video-id', data.video_id);
        card.className = `status-card-v2`;
        
        // Build the structure once
        card.innerHTML = `
            <div class="status-header">
                <span class="status-badge"></span>
                <span class="status-time"></span>
            </div>
            <div class="status-main">
                <div class="progress-circle-container">
                    <svg viewBox="0 0 36 36" class="circular-chart">
                        <path class="circle-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                        <path class="circle" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                        <text x="18" y="20.35" class="percentage">0%</text>
                    </svg>
                </div>
                <div class="status-info">
                    <h4 class="stage-text"></h4>
                    <p class="message-text"></p>
                </div>
            </div>
            <div class="status-error hidden"></div>
            <div class="status-footer">
                <div class="meta-item"><span>ID: ${data.video_id.slice(0, 8)}...</span></div>
            </div>
        `;
        container.appendChild(card);
    }

    // 3. Update only the parts that change (The "Patch")
    const percent = Math.round((data.progress || 0) * 100);
    const statusClass = (data.status || 'queued').toLowerCase();

    // Update classes and text without destroying elements
    card.className = `status-card-v2 ${statusClass}`;
    card.querySelector('.status-badge').innerText = data.status.replace('_', ' ');
    card.querySelector('.status-time').innerText = new Date(data.updated_at).toLocaleTimeString();
    card.querySelector('.stage-text').innerText = data.current_stage;
    card.querySelector('.message-text').innerText = data.message || 'Waiting to start...';
    
    // Update SVG Progress with CSS Transition support
    const circle = card.querySelector('.circle');
    circle.setAttribute('stroke-dasharray', `${percent}, 100`);
    card.querySelector('.percentage').textContent = `${percent}%`;

    // Handle Error visibility
    const errorDiv = card.querySelector('.status-error');
    if (data.error) {
        errorDiv.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${data.error}`;
        errorDiv.classList.remove('hidden');
    } else {
        errorDiv.classList.add('hidden');
    }
}

async function listVideos() {
    try {
        const res = await fetch(`${API_BASE}/videos/list`);
        const data = await res.json();
        ALL_VIDEOS = data.videos || [];
        renderLibrary();
    } catch (e) { console.error("Failed to list videos", e); }
}
/**
 * RESTORED: Deletes a video and its metadata from the server.
 * @param {string} id - The ID of the video to delete.
 * @param {Event} event - The click event (to stop propagation).
 */
async function deleteVideo(id, event) {
    if (event) event.stopPropagation();

    if (!confirm(`Are you sure you want to delete video ${id.slice(0,8)}...?`)) {
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/videos/${id}`, {
            method: "DELETE"
        });

        if (res.ok) {
            console.log(`Video ${id} deleted.`);
            
            // --- UI RESET LOGIC ---
            if (VIDEO_ID === id) {
                VIDEO_ID = null;
                
                // Hide the Action/Info cards
                document.getElementById("videoInfo").classList.add("hidden");
                document.getElementById("statusSection").classList.add("hidden");
                
                // 1. Hide the Result Sections
                document.getElementById("transcriptSection").classList.add("hidden");
                document.getElementById("summarySection").classList.add("hidden");

                // 2. Clear the actual text content
                document.getElementById("transcriptOutput").textContent = "";
                document.getElementById("summaryOutput").textContent = "";
                
                // Reset Chat Title
                const chatTitle = document.querySelector(".header-info h2");
                if (chatTitle) chatTitle.innerText = "Visi-Agent Chat";

                // Optional: Clear chat messages or show empty state
                const container = document.getElementById("chatContainer");
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="icon-circle"><i class="fas fa-robot"></i></div>
                        <p>Video deleted. Select another video to begin.</p>
                    </div>`;
            }

            await listVideos();
        }
    } catch (e) {
        console.error("Error deleting video:", e);
    }
}

/**
 * UPDATED: Renders the library with the delete button included.
 */
function renderLibrary() {
    const container = document.getElementById("videoListContainer");
    container.innerHTML = ALL_VIDEOS.length ? "" : '<p class="empty-msg">No videos found.</p>';
    
    ALL_VIDEOS.forEach(v => {
        const div = document.createElement("div");
        // Standardize status for CSS class naming
        const statusClass = (v.status || "unknown").toLowerCase();
        
        div.className = `video-item ${v.id === VIDEO_ID ? 'active' : ''}`;
        
        // Note: The onclick for the main div handles selection, 
        // while the button handles deletion with event.stopPropagation()
        div.innerHTML = `
            <div class="video-item-content" onclick="selectVideo('${v.id}')">
                <i class="fas fa-video"></i>
                <div class="video-text">
                    <span class="video-name">${v.filename || v.id.slice(0,8)}</span>
                    <small class="status-tag ${statusClass}">${v.status}</small>
                </div>
            </div>
            <button class="btn-delete" onclick="deleteVideo('${v.id}', event)" title="Delete Video">
                <i class="fas fa-trash"></i>
            </button>
        `;
        container.appendChild(div);
    });
}
async function uploadVideo() {
    const fileInput = document.getElementById("videoFile");
    if (!fileInput.files.length) return alert("Select a video");

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    try {
        const res = await fetch(`${API_BASE}/videos/upload`, { method: "POST", body: formData });
        const data = await res.json();
        selectVideo(data.video_id);
        listVideos();
    } catch (e) { alert("Upload failed"); }
}

// --- Chat Management ---

async function handleSendMessage() {
    const chatInput = document.getElementById("chatInput");
    const question = chatInput.value.trim();
    if (!question) return;

    appendMessage(question, false);
    chatInput.value = "";
    
    const aiMsgObj = appendMessage("Thinking...", true);
    const contentDiv = aiMsgObj.querySelector('.message-content');

    try {
        const payload = VIDEO_ID 
            ? { video_id: VIDEO_ID, question, include_timestamps: true }
            : { question, video_ids: ALL_VIDEOS.map(v => v.id) };
        console.log(VIDEO_ID ? "Querying single video with payload:" : "Querying multiple videos with payload:", payload,VIDEO_ID);
        const endpoint = VIDEO_ID ? `${API_BASE}/query/ask` : `${API_BASE}/query/multi-video`;

        const res = await fetch(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        
        const data = await res.json();
        contentDiv.innerText = data.answer || "No response received.";
    } catch (e) { contentDiv.innerText = "Error connecting to Visi-Agent."; }
}

function appendMessage(text, isAi) {
    const container = document.getElementById("chatContainer");
    const empty = container.querySelector(".empty-state");
    if (empty) empty.remove();

    const wrapper = document.createElement("div");
    wrapper.className = `message-wrapper ${isAi ? 'ai' : 'user'}`;
    // Clean the HTML after parsing it
    const formattedText = isAi ? DOMPurify.sanitize(marked.parse(text)) : text;
    wrapper.innerHTML = `
    <div class="avatar">${isAi ? 'VA' : 'U'}</div>
    <div class="message-content">${formattedText}</div>
    `;
    container.appendChild(wrapper);
    container.scrollTop = container.scrollHeight;
    return wrapper;
}

function resetChat() {
    VIDEO_ID = null;
    document.getElementById("videoInfo").classList.add("hidden");
    document.getElementById("chatContainer").innerHTML = '<div class="empty-state"><p>Global Mode Active. Search all videos.</p></div>';
    renderLibrary();
}

// --- Results Fetchers ---

async function fetchTranscript() {
    const res = await fetch(`${API_BASE}/videos/${VIDEO_ID}/transcript`);
    const data = await res.json();
    document.getElementById("transcriptSection").classList.remove("hidden");
    document.getElementById("transcriptOutput").textContent = data;
}

async function fetchSummary() {
    const res = await fetch(`${API_BASE}/videos/${VIDEO_ID}/summary`);
    const data = await res.json();
    document.getElementById("summarySection").classList.remove("hidden");
    document.getElementById("summaryOutput").textContent = data.summary;
}

// Initialize
window.onload = listVideos;