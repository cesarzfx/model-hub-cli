const apiUrl = "https://9h4tsnso06.execute-api.us-east-2.amazonaws.com/";
document.getElementById("checkBtn").onclick = async function() {
    document.getElementById("result").textContent = "Checking...";
    try {
        const response = await fetch(apiUrl);
        const text = await response.text();
        document.getElementById("result").textContent = text;
    } catch (err) {
        document.getElementById("result").textContent = "Error: " + err;
    }
};
