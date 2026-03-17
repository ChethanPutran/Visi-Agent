async function runQuery() {
    const q = document.getElementById("query").value;
    const res = await fetch("/api/v1/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q })
    });

    document.getElementById("result").textContent =
        JSON.stringify(await res.json(), null, 2);
}
