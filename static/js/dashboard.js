// static/js/dashboard.js

document.addEventListener("DOMContentLoaded", function () {
    const clientList = document.getElementById("client-list");
    const conversationList = document.getElementById("conversation-list");
    const faqList = document.getElementById("faq-list");
    const reportContainer = document.getElementById("report-container");

    const spinnerHTML = '<div class="loading-spinner">Loading...</div>';

    async function fetchData(url, container, renderFunction) {
        if (container) container.innerHTML = spinnerHTML;
        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error(`Error ${response.status}`);
            const data = await response.json();
            renderFunction(data, container);
        } catch (error) {
            console.error("Fetch error:", error);
            if (container) container.innerHTML = `<p class="error-message">Failed to load data.</p>`;
        }
    }

    function renderClients(data, container) {
        if (data.tenants?.length) {
            let html = "<ul>";
            data.tenants.forEach(t => {
                html += `<li><strong>${t.tenant_name}</strong> (ID: ${t.tenant_id})</li>`;
            });
            html += "</ul>";
            container.innerHTML = html;
        } else {
            container.innerHTML = "<p>No clients available.</p>";
        }
    }

    function renderFaqs(data, container) {
        if (data.faqs?.length) {
            let html = "<table><tr><th>ID</th><th>Question</th><th>Answer</th></tr>";
            data.faqs.forEach(f => {
                html += `<tr><td>${f.id}</td><td>${f.question}</td><td>${f.answer}</td></tr>`;
            });
            html += "</table>";
            container.innerHTML = html;
        } else {
            container.innerHTML = "<p>No FAQs found.</p>";
        }
    }

    function renderConversationHistory(data, container) {
        if (data.conversations?.length) {
            let html = "";
            data.conversations.forEach(msg => {
                html += `
                <div class="message-item ${msg.sender === 'user' ? 'user-message' : 'bot-message'}">
                    <div class="message-header">
                        <span>${msg.sender === 'user' ? 'You' : 'Bot'}</span>
                        <span>${new Date(msg.timestamp * 1000).toLocaleString()}</span>
                    </div>
                    <div>${msg.message_text}</div>
                </div>`;
            });
            container.innerHTML = html;
        } else {
            container.innerHTML = "<p>No conversation history available.</p>";
        }
    }

    function renderReports(data) {
        const ctx = document.getElementById("monthlyChart").getContext("2d");
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Conversations per Month',
                    data: data.values,
                    backgroundColor: '#007bff'
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: true } }
            }
        });
        reportContainer.querySelector(".loading-spinner").remove();
    }

    if (clientList) fetchData("/api/clients", clientList, renderClients);
    if (faqList) fetchData("/api/faqs", faqList, renderFaqs);
    if (conversationList) {
        const waId = conversationList.dataset.waId;
        if (waId) fetchData(`/api/chat_history/${waId}`, conversationList, renderConversationHistory);
    }
    if (reportContainer) fetchData("/api/reports/monthly", null, renderReports);
});
