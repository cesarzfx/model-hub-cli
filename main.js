const baseUrl = "https://9h4tsnso06.execute-api.us-east-2.amazonaws.com";

document.getElementById("testBtn").onclick = async function() {
    const modelId = document.getElementById("modelId").value;
    document.getElementById("result").textContent = "Testing endpoint...";
    
    try {
        const response = await fetch(`${baseUrl}/artifact/model/${modelId}/rate`);
        const data = await response.json();
        document.getElementById("result").textContent = JSON.stringify(data, null, 2);
    } catch (err) {
        document.getElementById("result").textContent = "Error: " + err;
    }
};
