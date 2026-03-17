const form = document.getElementById("uploadForm");
const result = document.getElementById("result");

form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const fileInput = document.getElementById("videoFile");
    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    result.innerHTML = "Uploading...";

    const res = await fetch("/api/v1/videos/upload", {
        method: "POST",
        body: formData
    });

    const data = await res.json();

    result.innerHTML = `
        <p>✅ Uploaded</p>
        <p>Video ID: <b>${data.video_id}</b></p>
        <a href="/video/${data.video_id}">Go to Video Dashboard</a>
    `;
});
