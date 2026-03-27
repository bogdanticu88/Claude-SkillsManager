// SkillPM Registry - Frontend Application
// Author: Bogdan Ticu
// License: MIT

const API_BASE = window.location.origin;

// --- State ---
let currentSection = 'browse';

// --- API calls ---

async function apiGet(path) {
    const resp = await fetch(`${API_BASE}${path}`);
    if (!resp.ok) {
        throw new Error(`API error: ${resp.status}`);
    }
    return resp.json();
}

// --- Navigation ---

function hideAllSections() {
    document.getElementById('search-section').style.display = 'none';
    document.getElementById('results-section').style.display = 'none';
    document.getElementById('detail-section').style.display = 'none';
    document.getElementById('author-section').style.display = 'none';
    document.getElementById('dashboard-section').style.display = 'none';
    document.getElementById('about-section').style.display = 'none';
}

function showBrowse() {
    hideAllSections();
    document.getElementById('search-section').style.display = 'block';
    document.getElementById('results-section').style.display = 'block';
    currentSection = 'browse';
    setActiveNav(0);
}

function showDashboard() {
    hideAllSections();
    document.getElementById('dashboard-section').style.display = 'block';
    currentSection = 'dashboard';
    setActiveNav(1);
    loadDashboard();
}

function showAbout() {
    hideAllSections();
    document.getElementById('about-section').style.display = 'block';
    currentSection = 'about';
    setActiveNav(2);
}

function setActiveNav(index) {
    const links = document.querySelectorAll('.nav-link');
    links.forEach((l, i) => {
        l.classList.toggle('active', i === index);
    });
}

// --- Search ---

function handleSearch(event) {
    if (event.key === 'Enter') {
        performSearch();
    }
}

async function performSearch() {
    const query = document.getElementById('search-input').value;
    const tag = document.getElementById('filter-tag').value;
    const language = document.getElementById('filter-language').value;
    const sort = document.getElementById('filter-sort').value;

    let params = new URLSearchParams();
    if (query) params.append('q', query);
    if (tag) params.append('tag', tag);
    if (language) params.append('language', language);
    if (sort) params.append('sort', sort);

    try {
        const skills = await apiGet(`/api/v1/search?${params.toString()}`);
        renderResults(skills);
    } catch (err) {
        console.error('Search failed:', err);
        document.getElementById('results-grid').innerHTML =
            '<p>Failed to load results. Is the registry running?</p>';
    }
}

function renderResults(skills) {
    const grid = document.getElementById('results-grid');
    const count = document.getElementById('results-count');

    if (!skills || skills.length === 0) {
        count.textContent = 'No skills found.';
        grid.innerHTML = '';
        return;
    }

    count.textContent = `${skills.length} skill${skills.length !== 1 ? 's' : ''} found`;

    grid.innerHTML = skills.map(s => `
        <div class="skill-card" onclick="showSkillDetail('${s.name}')">
            <div class="skill-card-header">
                <span class="skill-name">${escapeHtml(s.name)}</span>
                <span class="skill-version">v${escapeHtml(s.version)}</span>
            </div>
            <div class="skill-description">${escapeHtml(s.description || 'No description')}</div>
            ${renderTags(s.metadata?.tags || [])}
            <div class="skill-meta">
                <span class="skill-author" onclick="event.stopPropagation(); showAuthor('${s.author_username}')">
                    ${escapeHtml(s.author_username)}
                </span>
                <div class="skill-stats">
                    ${s.avg_rating > 0 ? `<span class="rating">${s.avg_rating.toFixed(1)}/5</span>` : ''}
                    <span>${s.download_count} downloads</span>
                </div>
            </div>
            ${s.deprecated ? '<span class="deprecated-badge">DEPRECATED</span>' : ''}
        </div>
    `).join('');
}

function renderTags(tags) {
    if (!tags || tags.length === 0) return '';
    return '<div style="margin-bottom:8px">' +
        tags.slice(0, 4).map(t => `<span class="tag">${escapeHtml(t)}</span>`).join('') +
        '</div>';
}

// --- Skill Detail ---

async function showSkillDetail(name) {
    hideAllSections();
    document.getElementById('detail-section').style.display = 'block';

    try {
        const skill = await apiGet(`/api/v1/skills/${name}`);
        const reviews = await apiGet(`/api/v1/skills/${name}/reviews`);

        let versionsHtml = '';
        try {
            const versions = await apiGet(`/api/v1/skills/${name}/versions`);
            versionsHtml = versions.map(v =>
                `<li>${escapeHtml(v.version)} ${v.yanked ? '(yanked)' : ''}</li>`
            ).join('');
        } catch (e) {
            versionsHtml = '<li>-</li>';
        }

        const detail = document.getElementById('skill-detail');
        detail.innerHTML = `
            <div class="detail-header">
                <h1>${escapeHtml(skill.name)}
                    <span class="skill-version">v${escapeHtml(skill.version)}</span>
                    ${skill.deprecated ? '<span class="deprecated-badge">DEPRECATED</span>' : ''}
                </h1>
                <p style="color:var(--text-secondary)">${escapeHtml(skill.description || '')}</p>
            </div>
            <div class="detail-body">
                <div>
                    <div class="detail-main">
                        <h3>Description</h3>
                        <p>${escapeHtml(skill.long_description || skill.description || 'No detailed description provided.')}</p>

                        ${skill.metadata?.tags?.length ? `
                            <h3 style="margin-top:16px">Tags</h3>
                            <div>${skill.metadata.tags.map(t => `<span class="tag">${escapeHtml(t)}</span>`).join('')}</div>
                        ` : ''}

                        ${skill.metadata?.target_llms?.length ? `
                            <h3 style="margin-top:16px">Target LLMs</h3>
                            <p>${skill.metadata.target_llms.join(', ')}</p>
                        ` : ''}
                    </div>

                    <div class="reviews-section">
                        <h3>Reviews (${reviews.length})</h3>
                        ${reviews.length === 0 ? '<p style="color:var(--text-secondary)">No reviews yet.</p>' : ''}
                        ${reviews.map(r => `
                            <div class="review-card">
                                <div class="review-header">
                                    <span>
                                        <strong>${escapeHtml(r.title || 'Review')}</strong>
                                        by <span class="skill-author" onclick="showAuthor('${r.username}')">${escapeHtml(r.username)}</span>
                                    </span>
                                    <span class="review-rating">${'*'.repeat(r.rating)}${'*'.repeat(5 - r.rating)}</span>
                                </div>
                                ${r.body ? `<p>${escapeHtml(r.body)}</p>` : ''}
                            </div>
                        `).join('')}
                    </div>
                </div>
                <div class="detail-sidebar">
                    <div class="sidebar-card">
                        <h3>Install</h3>
                        <div class="install-cmd">skillpm install ${escapeHtml(skill.name)}</div>
                    </div>
                    <div class="sidebar-card">
                        <h3>Stats</h3>
                        <p>Downloads: ${skill.download_count}</p>
                        <p>Rating: ${skill.avg_rating > 0 ? skill.avg_rating.toFixed(1) + '/5' : 'No ratings'} (${skill.review_count} reviews)</p>
                        <p>License: ${escapeHtml(skill.license || 'Not specified')}</p>
                        <p>Language: ${escapeHtml(skill.language || skill.metadata?.language || 'Not specified')}</p>
                    </div>
                    <div class="sidebar-card">
                        <h3>Author</h3>
                        <p><span class="skill-author" onclick="showAuthor('${skill.author_username}')">${escapeHtml(skill.author_username)}</span></p>
                    </div>
                    ${skill.repository_url ? `
                        <div class="sidebar-card">
                            <h3>Links</h3>
                            <p><a href="${escapeHtml(skill.repository_url)}" target="_blank">Repository</a></p>
                            ${skill.homepage_url ? `<p><a href="${escapeHtml(skill.homepage_url)}" target="_blank">Homepage</a></p>` : ''}
                        </div>
                    ` : ''}
                    <div class="sidebar-card">
                        <h3>Versions</h3>
                        <ul class="panel-list">${versionsHtml}</ul>
                    </div>
                </div>
            </div>
        `;
    } catch (err) {
        document.getElementById('skill-detail').innerHTML =
            `<p>Failed to load skill: ${escapeHtml(err.message)}</p>`;
    }
}

// --- Author Profile ---

async function showAuthor(username) {
    hideAllSections();
    document.getElementById('author-section').style.display = 'block';

    try {
        const author = await apiGet(`/api/v1/authors/${username}`);
        const skills = await apiGet(`/api/v1/authors/${username}/skills`);

        const detail = document.getElementById('author-detail');
        detail.innerHTML = `
            <div class="author-header">
                <div class="author-avatar">${username[0].toUpperCase()}</div>
                <div>
                    <h2>${escapeHtml(author.display_name || author.username)}</h2>
                    <p style="color:var(--text-secondary)">@${escapeHtml(author.username)}
                        ${author.verified ? ' (verified)' : ''}</p>
                    ${author.bio ? `<p>${escapeHtml(author.bio)}</p>` : ''}
                    ${author.website ? `<p><a href="${escapeHtml(author.website)}" target="_blank">${escapeHtml(author.website)}</a></p>` : ''}
                </div>
            </div>

            <h3>Skills (${skills.length})</h3>
            <div class="skill-grid">
                ${skills.map(s => `
                    <div class="skill-card" onclick="showSkillDetail('${s.name}')">
                        <div class="skill-card-header">
                            <span class="skill-name">${escapeHtml(s.name)}</span>
                            <span class="skill-version">v${escapeHtml(s.version)}</span>
                        </div>
                        <div class="skill-description">${escapeHtml(s.description || '')}</div>
                        <div class="skill-meta">
                            <span>${s.download_count} downloads</span>
                            ${s.avg_rating > 0 ? `<span class="rating">${s.avg_rating.toFixed(1)}/5</span>` : ''}
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    } catch (err) {
        document.getElementById('author-detail').innerHTML =
            `<p>Failed to load author: ${escapeHtml(err.message)}</p>`;
    }
}

// --- Dashboard ---

async function loadDashboard() {
    try {
        const stats = await apiGet('/api/v1/analytics/global');

        document.getElementById('dashboard-stats').innerHTML = `
            <div class="stat-card">
                <div class="stat-value">${stats.total_skills}</div>
                <div class="stat-label">Skills</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${stats.total_authors}</div>
                <div class="stat-label">Authors</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${stats.total_downloads}</div>
                <div class="stat-label">Downloads</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${stats.total_executions}</div>
                <div class="stat-label">Executions</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${stats.total_reviews}</div>
                <div class="stat-label">Reviews</div>
            </div>
        `;

        document.getElementById('top-downloaded').innerHTML = `
            <h3>Top Downloaded</h3>
            <ul class="panel-list">
                ${(stats.top_downloaded || []).map(s =>
                    `<li><span>${escapeHtml(s.name)}</span><span>${s.downloads}</span></li>`
                ).join('')}
                ${(stats.top_downloaded || []).length === 0 ? '<li>No data yet</li>' : ''}
            </ul>
        `;

        document.getElementById('newest-skills').innerHTML = `
            <h3>Newest Skills</h3>
            <ul class="panel-list">
                ${(stats.newest_skills || []).map(s =>
                    `<li>
                        <span class="skill-author" onclick="showSkillDetail('${s.name}')">${escapeHtml(s.name)}</span>
                        <span>v${escapeHtml(s.version)}</span>
                    </li>`
                ).join('')}
                ${(stats.newest_skills || []).length === 0 ? '<li>No skills yet</li>' : ''}
            </ul>
        `;
    } catch (err) {
        document.getElementById('dashboard-stats').innerHTML =
            '<p>Failed to load dashboard data.</p>';
    }
}

// --- Utilities ---

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// --- Tags loader ---

async function loadTags() {
    try {
        const tags = await apiGet('/api/v1/search/tags');
        const select = document.getElementById('filter-tag');
        tags.forEach(t => {
            const option = document.createElement('option');
            option.value = t.tag;
            option.textContent = `${t.tag} (${t.count})`;
            select.appendChild(option);
        });
    } catch (e) {
        // Tags loading is optional
    }
}

// --- Init ---

document.addEventListener('DOMContentLoaded', () => {
    performSearch();
    loadTags();
});
