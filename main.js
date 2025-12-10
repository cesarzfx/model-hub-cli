// ============================================
// Configuration
// ============================================
const baseUrl = "https://9h4tsnso06.execute-api.us-east-2.amazonaws.com";

// ============================================
// Dark Mode Toggle
// ============================================
function initializeDarkMode() {
    const themeToggle = document.getElementById('theme-toggle');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const savedTheme = localStorage.getItem('theme');
    
    // Set initial theme
    if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
        document.body.classList.add('dark-mode');
    }
    
    themeToggle.addEventListener('click', () => {
        document.body.classList.toggle('dark-mode');
        const isDark = document.body.classList.contains('dark-mode');
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
        
        // Update ARIA label
        themeToggle.setAttribute('aria-label', isDark ? 'Switch to light mode' : 'Switch to dark mode');
        themeToggle.setAttribute('title', isDark ? 'Switch to light mode' : 'Switch to dark mode');
    });
    
    // Update initial ARIA label
    const isDark = document.body.classList.contains('dark-mode');
    themeToggle.setAttribute('aria-label', isDark ? 'Switch to light mode' : 'Switch to dark mode');
    themeToggle.setAttribute('title', isDark ? 'Switch to light mode' : 'Switch to dark mode');
}

// ============================================
// Tab Management
// ============================================
function initializeTabs() {
    const tabs = document.querySelectorAll('[role="tab"]');
    const panels = document.querySelectorAll('[role="tabpanel"]');

    tabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            const targetPanel = tab.getAttribute('aria-controls');
            
            // Deactivate all tabs and panels
            tabs.forEach(t => {
                t.setAttribute('aria-selected', 'false');
                t.setAttribute('tabindex', '-1');
            });
            panels.forEach(p => {
                p.hidden = true;
            });

            // Activate clicked tab and its panel
            tab.setAttribute('aria-selected', 'true');
            tab.setAttribute('tabindex', '0');
            document.getElementById(targetPanel).hidden = false;
        });

        // Keyboard navigation
        tab.addEventListener('keydown', (e) => {
            let nextTab = null;
            
            if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
                nextTab = tab.parentElement.nextElementSibling?.querySelector('[role="tab"]');
                if (!nextTab) {
                    nextTab = tab.parentElement.parentElement.firstElementChild?.querySelector('[role="tab"]');
                }
            } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
                nextTab = tab.parentElement.previousElementSibling?.querySelector('[role="tab"]');
                if (!nextTab) {
                    nextTab = tab.parentElement.parentElement.lastElementChild?.querySelector('[role="tab"]');
                }
            } else if (e.key === 'Home') {
                nextTab = tab.parentElement.parentElement.firstElementChild?.querySelector('[role="tab"]');
            } else if (e.key === 'End') {
                nextTab = tab.parentElement.parentElement.lastElementChild?.querySelector('[role="tab"]');
            }

            if (nextTab) {
                e.preventDefault();
                nextTab.click();
                nextTab.focus();
            }
        });
    });
}

// ============================================
// Query Method Toggle
// ============================================
function initializeQueryMethodToggle() {
    const radios = document.querySelectorAll('input[name="query-method"]');
    const nameGroup = document.getElementById('query-name-group');
    const regexGroup = document.getElementById('query-regex-group');
    const nameInput = document.getElementById('query-name');
    const regexInput = document.getElementById('query-regex');

    radios.forEach(radio => {
        radio.addEventListener('change', () => {
            radios.forEach(r => r.setAttribute('aria-checked', 'false'));
            radio.setAttribute('aria-checked', 'true');

            if (radio.value === 'name') {
                nameGroup.hidden = false;
                regexGroup.hidden = true;
                nameInput.required = true;
                regexInput.required = false;
            } else if (radio.value === 'regex') {
                nameGroup.hidden = true;
                regexGroup.hidden = false;
                nameInput.required = false;
                regexInput.required = true;
            } else { // wildcard
                nameGroup.hidden = true;
                regexGroup.hidden = true;
                nameInput.required = false;
                regexInput.required = false;
            }
        });
    });
}

// ============================================
// Utility Functions
// ============================================
function showLoading(element) {
    element.innerHTML = '<div class="info-message"><span class="loading"></span>Processing request...</div>';
    element.setAttribute('aria-busy', 'true');
}

function showError(element, message) {
    element.innerHTML = `<div class="error-message" role="alert"><strong>Error:</strong> ${escapeHtml(message)}</div>`;
    element.setAttribute('aria-busy', 'false');
}

function showSuccess(element, message) {
    element.innerHTML = `<div class="success-message" role="status"><strong>Success:</strong> ${escapeHtml(message)}</div>`;
    element.setAttribute('aria-busy', 'false');
}

function showInfo(element, title, data) {
    const formattedData = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
    element.innerHTML = `
        <h3>${escapeHtml(title)}</h3>
        <pre>${escapeHtml(formattedData)}</pre>
    `;
    element.setAttribute('aria-busy', 'false');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================
// Progress Indicators
// ============================================
function createProgressSteps(element, steps) {
    const stepsHtml = steps.map((step, index) => `
        <div class="progress-step" data-step="${index}">
            <div class="progress-step-circle">${index + 1}</div>
            <div class="progress-step-label">${escapeHtml(step)}</div>
        </div>
    `).join('');
    
    element.innerHTML = `
        <div class="progress-container">
            <div class="progress-steps">
                ${stepsHtml}
            </div>
        </div>
    `;
}

function updateProgressStep(element, stepIndex, status = 'active') {
    const steps = element.querySelectorAll('.progress-step');
    steps.forEach((step, index) => {
        step.classList.remove('active', 'completed');
        if (index < stepIndex) {
            step.classList.add('completed');
        } else if (index === stepIndex && status === 'active') {
            step.classList.add('active');
        }
    });
}

function completeAllSteps(element) {
    const steps = element.querySelectorAll('.progress-step');
    steps.forEach(step => {
        step.classList.remove('active');
        step.classList.add('completed');
    });
}

function createProgressBar(element, percentage = 0) {
    element.innerHTML = `
        <div class="progress-bar-container">
            <div class="progress-bar" style="width: ${percentage}%"></div>
        </div>
        <div class="progress-text">${percentage}%</div>
    `;
}

function updateProgressBar(element, percentage) {
    const bar = element.querySelector('.progress-bar');
    const text = element.querySelector('.progress-text');
    if (bar && text) {
        bar.style.width = `${percentage}%`;
        text.textContent = `${percentage}%`;
    }
}

// ============================================
// Upload Artifact
// ============================================
function initializeUploadForm() {
    const form = document.getElementById('upload-form');
    const resultDiv = document.getElementById('upload-result');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const artifactType = document.getElementById('artifact-type').value;
        const url = document.getElementById('artifact-url').value;
        const name = document.getElementById('artifact-name').value;

        // Show progress steps
        createProgressSteps(resultDiv, ['Validating', 'Uploading', 'Processing']);
        updateProgressStep(resultDiv, 0);

        try {
            const payload = { url };
            if (name.trim()) {
                payload.name = name.trim();
            }

            // Simulate validation step
            await new Promise(resolve => setTimeout(resolve, 500));
            updateProgressStep(resultDiv, 1);

            const response = await fetch(`${baseUrl}/artifact/${artifactType}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            updateProgressStep(resultDiv, 2);
            await new Promise(resolve => setTimeout(resolve, 300));

            const data = await response.json();

            if (response.ok) {
                completeAllSteps(resultDiv);
                setTimeout(() => {
                    showSuccess(resultDiv, `Artifact uploaded successfully! ID: ${data.metadata.id}`);
                    showInfo(resultDiv, 'Artifact Details', data);
                }, 500);
                form.reset();
            } else {
                showError(resultDiv, data.detail || 'Upload failed');
            }
        } catch (err) {
            showError(resultDiv, `Network error: ${err.message}`);
        }
    });
}

// ============================================
// Query Artifacts
// ============================================
function initializeQueryForm() {
    const form = document.getElementById('query-form');
    const resultDiv = document.getElementById('query-result');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const method = document.querySelector('input[name="query-method"]:checked').value;
        const typeCheckboxes = document.querySelectorAll('input[name="query-types"]:checked');
        const types = Array.from(typeCheckboxes).map(cb => cb.value);

        showLoading(resultDiv);

        try {
            let response, data;

            if (method === 'name') {
                const name = document.getElementById('query-name').value;
                const query = [{ name, types: types.length > 0 ? types : null }];
                
                response = await fetch(`${baseUrl}/artifacts`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(query)
                });
                data = await response.json();
                
            } else if (method === 'regex') {
                const regex = document.getElementById('query-regex').value;
                
                response = await fetch(`${baseUrl}/artifact/byRegEx`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ regex })
                });
                data = await response.json();
                
            } else { // wildcard
                const query = [{ name: '*', types: types.length > 0 ? types : null }];
                
                response = await fetch(`${baseUrl}/artifacts`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(query)
                });
                data = await response.json();
            }

            if (response.ok) {
                if (Array.isArray(data) && data.length > 0) {
                    displayArtifactTable(resultDiv, data);
                } else {
                    showInfo(resultDiv, 'No Results', 'No artifacts found matching your query.');
                }
            } else {
                showError(resultDiv, data.detail || 'Query failed');
            }
        } catch (err) {
            showError(resultDiv, `Network error: ${err.message}`);
        }
    });
}

function displayArtifactTable(element, artifacts) {
    const table = `
        <h3>Query Results (${artifacts.length} artifact${artifacts.length !== 1 ? 's' : ''})</h3>
        <table role="table" aria-label="Artifacts query results">
            <thead>
                <tr>
                    <th scope="col">ID</th>
                    <th scope="col">Name</th>
                    <th scope="col">Type</th>
                </tr>
            </thead>
            <tbody>
                ${artifacts.map(art => `
                    <tr>
                        <td><code>${escapeHtml(art.id)}</code></td>
                        <td>${escapeHtml(art.name)}</td>
                        <td><span class="badge">${escapeHtml(art.type)}</span></td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    element.innerHTML = table;
    element.setAttribute('aria-busy', 'false');
}

// ============================================
// View & Download Artifact
// ============================================
function initializeViewForm() {
    const form = document.getElementById('view-form');
    const resultDiv = document.getElementById('view-result');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const artifactType = document.getElementById('view-type').value;
        const id = document.getElementById('view-id').value;

        showLoading(resultDiv);

        try {
            const response = await fetch(`${baseUrl}/artifacts/${artifactType}/${id}`);
            const data = await response.json();

            if (response.ok) {
                displayArtifactDetails(resultDiv, data);
            } else {
                showError(resultDiv, data.detail || 'Artifact not found');
            }
        } catch (err) {
            showError(resultDiv, `Network error: ${err.message}`);
        }
    });
}

function displayArtifactDetails(element, artifact) {
    const downloadUrl = artifact.data.download_url || artifact.data.url;
    
    element.innerHTML = `
        <div class="success-message">
            <h3>Artifact Details</h3>
            <table role="table" aria-label="Artifact details">
                <tbody>
                    <tr>
                        <th scope="row">ID</th>
                        <td><code>${escapeHtml(artifact.metadata.id)}</code></td>
                    </tr>
                    <tr>
                        <th scope="row">Name</th>
                        <td>${escapeHtml(artifact.metadata.name)}</td>
                    </tr>
                    <tr>
                        <th scope="row">Type</th>
                        <td>${escapeHtml(artifact.metadata.type)}</td>
                    </tr>
                    <tr>
                        <th scope="row">Source URL</th>
                        <td><a href="${escapeHtml(artifact.data.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(artifact.data.url)}</a></td>
                    </tr>
                    <tr>
                        <th scope="row">Download URL</th>
                        <td><a href="${escapeHtml(downloadUrl)}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="display: inline-block; padding: 8px 16px; text-decoration: none;">Download Artifact</a></td>
                    </tr>
                </tbody>
            </table>
        </div>
    `;
    element.setAttribute('aria-busy', 'false');
}

// ============================================
// Rate Model
// ============================================
function initializeRateForm() {
    const form = document.getElementById('rate-form');
    const resultDiv = document.getElementById('rate-result');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const id = document.getElementById('rate-id').value;

        showLoading(resultDiv);

        try {
            const response = await fetch(`${baseUrl}/artifact/model/${id}/rate`);
            const data = await response.json();

            if (response.ok) {
                displayRatings(resultDiv, data);
            } else {
                showError(resultDiv, data.detail || 'Rating failed');
            }
        } catch (err) {
            showError(resultDiv, `Network error: ${err.message}`);
        }
    });
}

function displayRatings(element, rating) {
    const metrics = [
        { label: 'Net Score', value: rating.net_score, latency: rating.net_score_latency },
        { label: 'Ramp Up Time', value: rating.ramp_up_time, latency: rating.ramp_up_time_latency },
        { label: 'Bus Factor', value: rating.bus_factor, latency: rating.bus_factor_latency },
        { label: 'Performance Claims', value: rating.performance_claims, latency: rating.performance_claims_latency },
        { label: 'License', value: rating.license, latency: rating.license_latency },
        { label: 'Dataset & Code Score', value: rating.dataset_and_code_score, latency: rating.dataset_and_code_score_latency },
        { label: 'Dataset Quality', value: rating.dataset_quality, latency: rating.dataset_quality_latency },
        { label: 'Code Quality', value: rating.code_quality, latency: rating.code_quality_latency },
        { label: 'Reproducibility', value: rating.reproducibility, latency: rating.reproducibility_latency },
        { label: 'Reviewedness', value: rating.reviewedness, latency: rating.reviewedness_latency },
        { label: 'Tree Score', value: rating.tree_score, latency: rating.tree_score_latency },
    ];

    // Create unique ID for this chart
    const radarChartId = 'radarChart-' + Date.now();
    const barChartId = 'barChart-' + Date.now();
    const pieChartId = 'pieChart-' + Date.now();

    element.innerHTML = `
        <div class="success-message">
            <h3>Model Ratings: ${escapeHtml(rating.name)}</h3>
            <p><strong>Category:</strong> ${escapeHtml(rating.category)}</p>
            
            <div class="charts-grid">
                <div class="chart-container">
                    <div class="chart-title">📊 Performance Radar</div>
                    <div class="chart-wrapper">
                        <canvas id="${radarChartId}"></canvas>
                    </div>
                </div>
                
                <div class="chart-container">
                    <div class="chart-title">📈 Metric Scores</div>
                    <div class="chart-wrapper">
                        <canvas id="${barChartId}"></canvas>
                    </div>
                </div>
            </div>
            
            <table role="table" aria-label="Model rating metrics">
                <thead>
                    <tr>
                        <th scope="col">Metric</th>
                        <th scope="col">Score</th>
                        <th scope="col">Latency (s)</th>
                    </tr>
                </thead>
                <tbody>
                    ${metrics.map(m => `
                        <tr>
                            <th scope="row">${m.label}</th>
                            <td><strong>${m.value.toFixed(2)}</strong></td>
                            <td>${m.latency.toFixed(2)}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>

            <div class="charts-grid">
                <div class="chart-container">
                    <h4>Size Scores by Platform</h4>
                    <div class="chart-wrapper">
                        <canvas id="${pieChartId}"></canvas>
                    </div>
                </div>
                
                <div class="chart-container">
                    <h4>Platform Compatibility</h4>
                    <table role="table" aria-label="Size scores by platform">
                        <thead>
                            <tr>
                                <th scope="col">Platform</th>
                                <th scope="col">Score</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <th scope="row">Raspberry Pi</th>
                                <td>${rating.size_score.raspberry_pi.toFixed(2)}</td>
                            </tr>
                            <tr>
                                <th scope="row">Jetson Nano</th>
                                <td>${rating.size_score.jetson_nano.toFixed(2)}</td>
                            </tr>
                            <tr>
                                <th scope="row">Desktop PC</th>
                                <td>${rating.size_score.desktop_pc.toFixed(2)}</td>
                            </tr>
                            <tr>
                                <th scope="row">AWS Server</th>
                                <td>${rating.size_score.aws_server.toFixed(2)}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
            <p><small><strong>Size Score Latency:</strong> ${rating.size_score_latency.toFixed(2)}s</small></p>
        </div>
    `;
    element.setAttribute('aria-busy', 'false');

    // Create charts after DOM is updated
    setTimeout(() => {
        createRadarChart(radarChartId, metrics);
        createBarChart(barChartId, metrics);
        createPieChart(pieChartId, rating.size_score);
    }, 100);
}

function createRadarChart(canvasId, metrics) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    // Select key metrics for radar chart
    const radarMetrics = metrics.filter(m => 
        ['Ramp Up Time', 'Bus Factor', 'Code Quality', 'Reproducibility', 'Reviewedness', 'Tree Score'].includes(m.label)
    );

    new Chart(ctx, {
        type: 'radar',
        data: {
            labels: radarMetrics.map(m => m.label),
            datasets: [{
                label: 'Score',
                data: radarMetrics.map(m => m.value),
                backgroundColor: 'rgba(0, 123, 255, 0.2)',
                borderColor: 'rgba(0, 123, 255, 1)',
                borderWidth: 2,
                pointBackgroundColor: 'rgba(0, 123, 255, 1)',
                pointBorderColor: '#fff',
                pointHoverBackgroundColor: '#fff',
                pointHoverBorderColor: 'rgba(0, 123, 255, 1)'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    beginAtZero: true,
                    max: 1,
                    ticks: {
                        stepSize: 0.2
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });
}

function createBarChart(canvasId, metrics) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: metrics.map(m => m.label),
            datasets: [{
                label: 'Score',
                data: metrics.map(m => m.value),
                backgroundColor: [
                    'rgba(0, 123, 255, 0.8)',
                    'rgba(40, 167, 69, 0.8)',
                    'rgba(255, 193, 7, 0.8)',
                    'rgba(220, 53, 69, 0.8)',
                    'rgba(23, 162, 184, 0.8)',
                    'rgba(108, 117, 125, 0.8)',
                    'rgba(102, 126, 234, 0.8)',
                    'rgba(118, 75, 162, 0.8)',
                    'rgba(255, 99, 132, 0.8)',
                    'rgba(54, 162, 235, 0.8)',
                    'rgba(255, 159, 64, 0.8)'
                ],
                borderColor: [
                    'rgba(0, 123, 255, 1)',
                    'rgba(40, 167, 69, 1)',
                    'rgba(255, 193, 7, 1)',
                    'rgba(220, 53, 69, 1)',
                    'rgba(23, 162, 184, 1)',
                    'rgba(108, 117, 125, 1)',
                    'rgba(102, 126, 234, 1)',
                    'rgba(118, 75, 162, 1)',
                    'rgba(255, 99, 132, 1)',
                    'rgba(54, 162, 235, 1)',
                    'rgba(255, 159, 64, 1)'
                ],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 1
                }
            },
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });
}

function createPieChart(canvasId, sizeScores) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Raspberry Pi', 'Jetson Nano', 'Desktop PC', 'AWS Server'],
            datasets: [{
                data: [
                    sizeScores.raspberry_pi,
                    sizeScores.jetson_nano,
                    sizeScores.desktop_pc,
                    sizeScores.aws_server
                ],
                backgroundColor: [
                    'rgba(220, 53, 69, 0.8)',
                    'rgba(255, 193, 7, 0.8)',
                    'rgba(40, 167, 69, 0.8)',
                    'rgba(0, 123, 255, 0.8)'
                ],
                borderColor: [
                    'rgba(220, 53, 69, 1)',
                    'rgba(255, 193, 7, 1)',
                    'rgba(40, 167, 69, 1)',
                    'rgba(0, 123, 255, 1)'
                ],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

// ============================================
// Advanced Features
// ============================================

// Lineage
function initializeLineageForm() {
    const form = document.getElementById('lineage-form');
    const resultDiv = document.getElementById('lineage-result');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const id = document.getElementById('lineage-id').value;

        showLoading(resultDiv);

        try {
            const response = await fetch(`${baseUrl}/artifact/model/${id}/lineage`);
            const data = await response.json();

            if (response.ok) {
                displayLineage(resultDiv, data);
            } else {
                showError(resultDiv, data.detail || 'Lineage retrieval failed');
            }
        } catch (err) {
            showError(resultDiv, `Network error: ${err.message}`);
        }
    });
}

function displayLineage(element, lineage) {
    const graphId = 'lineage-graph-' + Date.now();
    
    const nodesTable = lineage.nodes.length > 0 ? `
        <h4>Nodes</h4>
        <table role="table" aria-label="Lineage nodes">
            <thead>
                <tr>
                    <th scope="col">Artifact ID</th>
                    <th scope="col">Name</th>
                    <th scope="col">Source</th>
                </tr>
            </thead>
            <tbody>
                ${lineage.nodes.map(node => `
                    <tr>
                        <td><code>${escapeHtml(node.artifact_id)}</code></td>
                        <td>${escapeHtml(node.name)}</td>
                        <td>${escapeHtml(node.source)}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    ` : '<p>No nodes found.</p>';

    const edgesTable = lineage.edges.length > 0 ? `
        <h4>Edges (Relationships)</h4>
        <table role="table" aria-label="Lineage edges">
            <thead>
                <tr>
                    <th scope="col">From</th>
                    <th scope="col">To</th>
                    <th scope="col">Relationship</th>
                </tr>
            </thead>
            <tbody>
                ${lineage.edges.map(edge => `
                    <tr>
                        <td><code>${escapeHtml(edge.from_node_artifact_id)}</code></td>
                        <td><code>${escapeHtml(edge.to_node_artifact_id)}</code></td>
                        <td>${escapeHtml(edge.relationship)}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    ` : '<p>No edges found.</p>';

    element.innerHTML = `
        <div class="success-message">
            <h3>Lineage Graph</h3>
            
            ${lineage.nodes.length > 0 ? `
                <div class="lineage-graph-container">
                    <div class="chart-title">🔗 Interactive Dependency Graph</div>
                    <div id="${graphId}"></div>
                    <div class="graph-legend">
                        <div class="legend-item">
                            <div class="legend-color" style="background: #007bff;"></div>
                            <span>Model</span>
                        </div>
                        <div class="legend-item">
                            <div class="legend-color" style="background: #28a745;"></div>
                            <span>Dataset</span>
                        </div>
                        <div class="legend-item">
                            <div class="legend-color" style="background: #ffc107;"></div>
                            <span>Code</span>
                        </div>
                    </div>
                </div>
            ` : ''}
            
            ${nodesTable}
            ${edgesTable}
        </div>
    `;
    element.setAttribute('aria-busy', 'false');

    // Create interactive graph if we have nodes
    if (lineage.nodes.length > 0) {
        setTimeout(() => {
            createLineageGraph(graphId, lineage);
        }, 100);
    }
}

function createLineageGraph(containerId, lineage) {
    const container = document.getElementById(containerId);
    if (!container) return;

    // Determine node type based on source or artifact_id pattern
    const getNodeType = (node) => {
        const source = node.source.toLowerCase();
        if (source.includes('model')) return 'model';
        if (source.includes('dataset')) return 'dataset';
        if (source.includes('code')) return 'code';
        return 'model'; // default
    };

    const getNodeColor = (type) => {
        switch (type) {
            case 'model': return '#007bff';
            case 'dataset': return '#28a745';
            case 'code': return '#ffc107';
            default: return '#6c757d';
        }
    };

    // Create nodes for vis-network
    const nodes = lineage.nodes.map(node => {
        const type = getNodeType(node);
        return {
            id: node.artifact_id,
            label: node.name || node.artifact_id.substring(0, 8),
            title: `${node.name}\nID: ${node.artifact_id}\nSource: ${node.source}`,
            color: {
                background: getNodeColor(type),
                border: getNodeColor(type),
                highlight: {
                    background: getNodeColor(type),
                    border: '#000'
                }
            },
            font: {
                color: '#ffffff',
                size: 14,
                face: 'Arial'
            },
            shape: 'box',
            margin: 10,
            widthConstraint: {
                minimum: 80,
                maximum: 150
            }
        };
    });

    // Create edges for vis-network
    const edges = lineage.edges.map((edge, index) => ({
        id: index,
        from: edge.from_node_artifact_id,
        to: edge.to_node_artifact_id,
        label: edge.relationship,
        arrows: 'to',
        color: {
            color: '#848484',
            highlight: '#007bff'
        },
        font: {
            size: 12,
            align: 'middle'
        },
        smooth: {
            type: 'cubicBezier',
            roundness: 0.5
        }
    }));

    // Create the network
    const data = { nodes: new vis.DataSet(nodes), edges: new vis.DataSet(edges) };
    const options = {
        layout: {
            hierarchical: {
                enabled: true,
                direction: 'UD',
                sortMethod: 'directed',
                levelSeparation: 150,
                nodeSpacing: 150
            }
        },
        physics: {
            enabled: false
        },
        interaction: {
            dragNodes: true,
            dragView: true,
            zoomView: true,
            hover: true,
            tooltipDelay: 200
        },
        nodes: {
            borderWidth: 2,
            borderWidthSelected: 3,
            shadow: true
        },
        edges: {
            width: 2,
            shadow: true,
            selectionWidth: 3
        }
    };

    new vis.Network(container, data, options);
}

// Cost
function initializeCostForm() {
    const form = document.getElementById('cost-form');
    const resultDiv = document.getElementById('cost-result');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const artifactType = document.getElementById('cost-type').value;
        const id = document.getElementById('cost-id').value;
        const dependency = document.getElementById('cost-dependency').checked;

        showLoading(resultDiv);

        try {
            const url = `${baseUrl}/artifact/${artifactType}/${id}/cost?dependency=${dependency}`;
            const response = await fetch(url);
            const data = await response.json();

            if (response.ok) {
                displayCost(resultDiv, data, id);
            } else {
                showError(resultDiv, data.detail || 'Cost calculation failed');
            }
        } catch (err) {
            showError(resultDiv, `Network error: ${err.message}`);
        }
    });
}

function displayCost(element, costData, artifactId) {
    const cost = costData[artifactId];
    const chartId = 'costChart-' + Date.now();
    
    // Calculate breakdown if we have dependencies
    const hasStandalone = cost.standalone_cost !== undefined;
    const standaloneCost = hasStandalone ? cost.standalone_cost : cost.total_cost;
    const dependencyCost = hasStandalone ? (cost.total_cost - cost.standalone_cost) : 0;
    
    element.innerHTML = `
        <div class="success-message">
            <h3>Storage Cost Analysis</h3>
            
            ${hasStandalone && dependencyCost > 0 ? `
                <div class="chart-container">
                    <div class="chart-title">💾 Cost Breakdown</div>
                    <div class="chart-wrapper" style="height: 300px;">
                        <canvas id="${chartId}"></canvas>
                    </div>
                </div>
            ` : ''}
            
            <table role="table" aria-label="Storage cost breakdown">
                <tbody>
                    ${hasStandalone ? `
                        <tr>
                            <th scope="row">Standalone Cost</th>
                            <td><strong>${standaloneCost.toFixed(2)} MB</strong></td>
                        </tr>
                        <tr>
                            <th scope="row">Dependencies Cost</th>
                            <td><strong>${dependencyCost.toFixed(2)} MB</strong></td>
                        </tr>
                    ` : ''}
                    <tr style="border-top: 2px solid var(--border-color);">
                        <th scope="row">Total Cost</th>
                        <td><strong>${cost.total_cost.toFixed(2)} MB</strong></td>
                    </tr>
                </tbody>
            </table>
        </div>
    `;
    element.setAttribute('aria-busy', 'false');

    // Create pie chart if we have breakdown
    if (hasStandalone && dependencyCost > 0) {
        setTimeout(() => {
            createCostPieChart(chartId, standaloneCost, dependencyCost);
        }, 100);
    }
}

function createCostPieChart(canvasId, standaloneCost, dependencyCost) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Standalone', 'Dependencies'],
            datasets: [{
                data: [standaloneCost, dependencyCost],
                backgroundColor: [
                    'rgba(0, 123, 255, 0.8)',
                    'rgba(108, 117, 125, 0.8)'
                ],
                borderColor: [
                    'rgba(0, 123, 255, 1)',
                    'rgba(108, 117, 125, 1)'
                ],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: ${value.toFixed(2)} MB (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// License Check
function initializeLicenseForm() {
    const form = document.getElementById('license-form');
    const resultDiv = document.getElementById('license-result');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const id = document.getElementById('license-model-id').value;
        const githubUrl = document.getElementById('license-github-url').value;

        showLoading(resultDiv);

        try {
            const response = await fetch(`${baseUrl}/artifact/model/${id}/license-check`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ github_url: githubUrl })
            });

            const data = await response.json();

            if (response.ok) {
                const compatible = data === true;
                if (compatible) {
                    showSuccess(resultDiv, 'License is compatible for fine-tuning and inference.');
                } else {
                    element.innerHTML = `<div class="info-message">License compatibility: ${data}</div>`;
                    element.setAttribute('aria-busy', 'false');
                }
            } else {
                showError(resultDiv, data.detail || 'License check failed');
            }
        } catch (err) {
            showError(resultDiv, `Network error: ${err.message}`);
        }
    });
}

// ============================================
// Initialize Everything
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    initializeDarkMode();
    initializeTabs();
    initializeQueryMethodToggle();
    initializeUploadForm();
    initializeQueryForm();
    initializeViewForm();
    initializeRateForm();
    initializeLineageForm();
    initializeCostForm();
    initializeLicenseForm();
});
