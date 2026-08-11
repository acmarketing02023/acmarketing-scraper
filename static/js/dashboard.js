let currentPage = 1;
let currentFilters = {};
let allLeads = []; // Store all leads for quick filtering

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadFilterOptions();
    loadLeads();
    setupEventListeners();
    updateLastUpdated();
    setupQuickFilters();
});

function setupEventListeners() {
    document.getElementById('city-filter').addEventListener('change', () => {
        currentPage = 1;
        loadLeads();
    });

    document.getElementById('qualification-filter').addEventListener('change', () => {
        currentPage = 1;
        loadLeads();
    });

    document.getElementById('sort-filter').addEventListener('change', () => {
        currentPage = 1;
        loadLeads();
    });

    document.getElementById('reset-filters').addEventListener('click', () => {
        document.getElementById('city-filter').value = 'all';
        document.getElementById('qualification-filter').value = 'all';
        document.getElementById('sort-filter').value = 'priority_score';

        // Reset quick filter buttons
        document.querySelectorAll('.quick-stat-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector('[data-filter="all"]').classList.add('active');

        currentPage = 1;
        loadLeads();
    });

    document.getElementById('prev-page').addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            loadLeads();
            window.scrollTo(0, 0);
        }
    });

    document.getElementById('next-page').addEventListener('click', () => {
        currentPage++;
        loadLeads();
        window.scrollTo(0, 0);
    });
}

function setupQuickFilters() {
    document.querySelectorAll('.quick-stat-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            // Remove active class from all buttons
            document.querySelectorAll('.quick-stat-btn').forEach(b => b.classList.remove('active'));

            // Add active class to clicked button
            btn.classList.add('active');

            const filter = btn.getAttribute('data-filter');

            if (filter === 'all') {
                currentFilters.call_status = null;
            } else {
                currentFilters.call_status = filter;
            }

            currentPage = 1;
            loadLeads();
        });
    });
}

function buildFilters() {
    const filters = new URLSearchParams();

    const city = document.getElementById('city-filter').value;
    if (city !== 'all') filters.append('city', city);

    const qualification = document.getElementById('qualification-filter').value;
    if (qualification !== 'all') filters.append('qualification', qualification);

    if (currentFilters.call_status) {
        filters.append('call_status', currentFilters.call_status);
    }

    const sortBy = document.getElementById('sort-filter').value;
    filters.append('sort_by', sortBy);
    filters.append('sort_order', 'desc');

    filters.append('page', currentPage);

    return filters.toString();
}

async function loadLeads() {
    const params = buildFilters();
    try {
        const response = await fetch(`/api/leads?${params}`);
        const data = await response.json();

        renderLeads(data.leads);
        updatePagination(data.page, data.total_pages, data.total);
        updateQuickFilterCounts(data.all_counts);
    } catch (error) {
        console.error('Error loading leads:', error);
        document.getElementById('leads-tbody').innerHTML =
            '<tr><td colspan="8" style="text-align: center; color: #e74c3c;">Error loading leads</td></tr>';
    }
}

function updateQuickFilterCounts(counts) {
    if (counts) {
        document.getElementById('count-all').textContent = counts.all || 0;
        document.getElementById('count-not-contacted').textContent = counts.not_contacted || 0;
        document.getElementById('count-attempted').textContent = counts.attempted || 0;
        document.getElementById('count-connected').textContent = counts.connected || 0;
        document.getElementById('count-scheduled').textContent = counts.scheduled || 0;
    }
}

function renderLeads(leads) {
    const tbody = document.getElementById('leads-tbody');

    if (leads.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: #636e72;">No leads found</td></tr>';
        return;
    }

    tbody.innerHTML = leads.map(lead => `
        <tr>
            <td>
                <strong>${escapeHtml(lead.name)}</strong>
            </td>
            <td>${escapeHtml(lead.location || lead.city || '')}</td>
            <td>
                ${lead.phone ? `<a href="tel:${lead.phone}" style="color: var(--primary-red); text-decoration: none; font-weight: 600;">${escapeHtml(lead.phone)}</a>` : '—'}
            </td>
            <td>
                ${lead.email ? `<a href="mailto:${lead.email}" style="color: var(--primary-red); text-decoration: none;">${escapeHtml(lead.email)}</a>` : '—'}
            </td>
            <td>
                <span class="qual-badge qual-${lead.qualification}">${capitalizeFirst(lead.qualification)}</span>
            </td>
            <td>
                <span class="status-badge status-${lead.call_status}">${formatStatus(lead.call_status)}</span>
            </td>
            <td>
                <strong>${lead.attempts || 0}</strong>
            </td>
            <td class="actions-cell">
                <button class="action-btn no-answer" onclick="logCall('${lead.id}', 'attempted', ${(lead.attempts || 0) + 1})" title="Called, no answer">❌ No Answer</button>
                <button class="action-btn answered" onclick="logCall('${lead.id}', 'connected', ${(lead.attempts || 0) + 1})" title="Called, not interested">✅ Answered</button>
                <button class="action-btn scheduled" onclick="logCall('${lead.id}', 'scheduled', ${(lead.attempts || 0) + 1})" title="Scheduled for follow-up">📅 Scheduled</button>
                <button class="action-btn reset" onclick="resetLead('${lead.id}')" title="Undo/Reset this lead">↻ Reset</button>
            </td>
        </tr>
    `).join('');

    // Attach event listeners to action buttons
    document.querySelectorAll('.action-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
        });
    });
}

async function logCall(leadId, status, attempts) {
    try {
        const response = await fetch(`/api/leads/${leadId}/update`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                call_status: status,
                attempts: attempts,
                last_contact_attempt: new Date().toISOString(),
            }),
        });

        if (response.ok) {
            // Visual feedback
            let statusText = '';
            if (status === 'attempted') statusText = '❌ No Answer';
            else if (status === 'connected') statusText = '✅ Answered (Not Interested)';
            else if (status === 'scheduled') statusText = '📅 Scheduled';
            console.log(`Logged: ${statusText}`);

            // Reload leads to show updated status
            loadLeads();
        }
    } catch (error) {
        console.error('Error logging call:', error);
        alert('Error logging call. Try again.');
    }
}

async function resetLead(leadId) {
    if (!confirm('Reset this lead? (Clears call status & attempts)')) {
        return;
    }

    try {
        const response = await fetch(`/api/leads/${leadId}/update`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                call_status: 'not_contacted',
                attempts: 0,
            }),
        });

        if (response.ok) {
            console.log('Lead reset');
            loadLeads();
        }
    } catch (error) {
        console.error('Error resetting lead:', error);
        alert('Error resetting lead. Try again.');
    }
}

function capitalizeFirst(str) {
    return str ? str.charAt(0).toUpperCase() + str.slice(1) : '';
}

function formatStatus(status) {
    const statusMap = {
        'not_contacted': 'Not Contacted',
        'attempted': 'Attempted',
        'connected': 'Connected',
        'scheduled': 'Scheduled',
        'booked': 'Booked',
        'converted': 'Converted',
        'declined': 'Declined'
    };
    return statusMap[status] || status;
}

function updatePagination(page, totalPages, total) {
    document.getElementById('prev-page').disabled = page === 1;
    document.getElementById('next-page').disabled = page === totalPages;
    document.getElementById('page-info').textContent = `Page ${page} of ${totalPages}`;
}

async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();

        document.getElementById('stat-total').textContent = data.total_leads;
        document.getElementById('stat-priority').textContent = data.high_priority_leads;
        document.getElementById('stat-no-website').textContent = data.leads_without_website;
        document.getElementById('stat-has-website').textContent = data.leads_with_website;
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

async function loadFilterOptions() {
    try {
        const response = await fetch('/api/filters');
        const data = await response.json();

        const citySelect = document.getElementById('city-filter');
        data.cities.forEach(city => {
            const option = document.createElement('option');
            option.value = city;
            option.textContent = city;
            citySelect.appendChild(option);
        });

        const categorySelect = document.getElementById('category-filter');
        data.categories.forEach(cat => {
            const option = document.createElement('option');
            option.value = cat;
            option.textContent = cat.charAt(0).toUpperCase() + cat.slice(1);
            categorySelect.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading filter options:', error);
    }
}

function updateLastUpdated() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    document.getElementById('last-updated').textContent = `Last refreshed: ${timeStr}`;
}

function truncate(str, len) {
    return str.length > len ? str.substring(0, len) + '...' : str;
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}
