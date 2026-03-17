let VIDEO_IDS = [];
let statusIntervals = {};

const videoFileInput = document.getElementById("videoFile");
const videoList = document.getElementById("videoList");
const statusSection = document.getElementById("statusSection");
const statusList = document.getElementById("statusList");
const transcriptSection = document.getElementById("transcriptSection");
const summarySection = document.getElementById("summarySection");
const transcriptOutput = document.getElementById("transcriptOutput");
const summaryOutput = document.getElementById("summaryOutput");

// Upload batch (all selected videos)
async function uploadBatchVideos() {
    if (!videoFileInput.files.length) return alert("Select videos to upload");

    const formData = new FormData();
    for (const file of videoFileInput.files) {
        formData.append("files", file);  // note plural 'files' for batch endpoint
    }

    const res = await fetch("http://localhost:8000/api/v1/videos/upload/batch", {
        method: "POST",
        body: formData
    });

    const data = await res.json();
    const results = data.results;

    results.forEach(result => {
        VIDEO_IDS.push(result.video_id);
        addVideoToList(result.video_id, result.filename);
    });

    alert(`Batch upload complete: ${data.successful_uploads} successful, ${data.failed_uploads} failed`);
}

// Upload single or multiple videos
async function uploadVideo() {
    if (!videoFileInput.files.length) return alert("Select video(s) to upload");

    const files = Array.from(videoFileInput.files);

    for (const file of files) {
        const formData = new FormData();
        formData.append("file", file);

        const res = await fetch("http://localhost:8000/api/v1/videos/upload", {
            method: "POST",
            body: formData
        });
        const data = await res.json();

        VIDEO_IDS.push(data.video_id);
        addVideoToList(data.video_id, data.metadata.filename);
    }
}

// Add video to the list
function addVideoToList(video_id, filename) {
    const li = document.createElement("li");
    li.id = `video-${video_id}`;
    li.innerHTML = `
        <strong>${filename}</strong> (ID: ${video_id})
        <div class="actions">
            <button onclick="processVideo('${video_id}', this)">▶ Process</button>
            <button onclick="fetchTranscript('${video_id}')">📝 Transcript</button>
            <button onclick="fetchSummary('${video_id}')">📌 Summary</button>
            <button onclick="deleteVideo('${video_id}')">❌ Delete</button>
        </div>
        <div class="status" id="status-${video_id}"></div>
    `;
    videoList.appendChild(li);

    // Initially disable transcript and summary
    li.querySelectorAll("button")[1].disabled = true;
    li.querySelectorAll("button")[2].disabled = true;
}

// Process video
async function processVideo(video_id, btn) {
    btn.disabled = true; // disable process
    const res = await fetch(`http://localhost:8000/api/v1/videos/${video_id}/process`, { method: "POST" });
    const data = await res.json();

    const statusDiv = document.getElementById(`status-${video_id}`);
    statusSection.classList.remove("hidden");

    statusIntervals[video_id] = setInterval(async () => {
        const res = await fetch(`http://localhost:8000/api/v1/videos/${video_id}/status`);
        const statusData = await res.json();
        statusDiv.innerHTML = renderStatusHTML(statusData);

        if (statusData.status === "completed") {
            clearInterval(statusIntervals[video_id]);
            statusDiv.innerHTML += "<p>✅ Processing complete</p>";
            const buttons = document.querySelector(`#video-${video_id}`).querySelectorAll("button");
            buttons[1].disabled = false; // enable transcript
            buttons[2].disabled = false; // enable summary
        }
    }, 3000);
}

// Render status nicely
function renderStatusHTML(data) {
    let html = "<ul>";
    for (const [key, value] of Object.entries(data)) {
        html += `<li><strong>${key}:</strong> ${value}</li>`;
    }
    html += "</ul>";
    return html;
}

// Fetch transcript
async function fetchTranscript(video_id) {
    const res = await fetch(`http://localhost:8000/api/v1/videos/${video_id}/transcript`);
    const data = await res.json();
    transcriptSection.classList.remove("hidden");
    transcriptOutput.textContent = JSON.stringify(data, null, 2);
}

// Fetch summary
async function fetchSummary(video_id) {
    const res = await fetch(`http://localhost:8000/api/v1/videos/${video_id}/summary`);
    const data = await res.json();
    summarySection.classList.remove("hidden");
    summaryOutput.textContent = JSON.stringify(data, null, 2);
}

// Delete video
async function deleteVideo(video_id) {
    if (!confirm("Are you sure you want to delete this video?")) return;
    await fetch(`http://localhost:8000/api/v1/videos/${video_id}`, { method: "DELETE" });

    const li = document.getElementById(`video-${video_id}`);
    li.remove();
}
