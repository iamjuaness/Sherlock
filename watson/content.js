// content.js - Script de contenido para SofaScore

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'getPageInfo') {
        sendResponse({
            url: window.location.href,
            title: document.title,
            eventId: extractEventIdFromUrl(window.location.href),
            initialState: getInitialState()
        });
    }

    if (request.action === 'extractFromPage') {
        extractFromPage().then(sendResponse);
        return true;
    }
});

function extractEventIdFromUrl(url) {
    let match = url.match(/#id:(\d+)/);
    if (match) return match[1];
    match = url.match(/\/event\/(\d+)/);
    if (match) return match[1];
    match = url.match(/[?#&]id[=:](\d+)/);
    if (match) return match[1];

    const eventMeta = document.querySelector('[data-event-id]');
    if (eventMeta) return eventMeta.getAttribute('data-event-id');

    return null;
}

function getInitialState() {
    try {
        for (const key of ['__INITIAL_STATE__', '__APP__', '__DATA__', 'sofaScoreData']) {
            if (window[key]) {
                return { source: key, data: window[key] };
            }
        }

        const scripts = document.querySelectorAll('script');
        for (const script of scripts) {
            const text = script.textContent;
            if (text.includes('window.__INITIAL_STATE__') || text.includes('eventId')) {
                const match = text.match(/"eventId"\s*:\s*(\d+)/);
                if (match) return { source: 'script', eventId: match[1] };
            }
        }

        return null;
    } catch (e) {
        return null;
    }
}

async function extractFromPage() {
    const eventId = extractEventIdFromUrl(window.location.href);

    if (!eventId) {
        return { error: 'No se pudo extraer el ID del evento de la URL' };
    }

    const pageData = {
        url: window.location.href,
        eventId: eventId,
        title: document.title,
        timestamp: new Date().toISOString()
    };

    const homeTeamEl = document.querySelector('[data-testid="home-team-name"], .home-team, [class*="home"] h2, [class*="Home"]');
    const awayTeamEl = document.querySelector('[data-testid="away-team-name"], .away-team, [class*="away"] h2, [class*="Away"]');

    if (homeTeamEl) pageData.homeTeam = homeTeamEl.textContent.trim();
    if (awayTeamEl) pageData.awayTeam = awayTeamEl.textContent.trim();

    const scoreEls = document.querySelectorAll('[class*="score"], [class*="Score"]');
    if (scoreEls.length >= 2) {
        pageData.score = {
            home: scoreEls[0].textContent.trim(),
            away: scoreEls[1].textContent.trim()
        };
    }

    return pageData;
}

(function init() {
    const eventId = extractEventIdFromUrl(window.location.href);
    if (eventId) {
        chrome.runtime.sendMessage({
            action: 'pageDetected',
            data: {
                url: window.location.href,
                eventId: eventId,
                title: document.title
            }
        });
    }
})();

let lastUrl = location.href;
new MutationObserver(() => {
    const url = location.href;
    if (url !== lastUrl) {
        lastUrl = url;
        const eventId = extractEventIdFromUrl(url);
        if (eventId) {
            chrome.runtime.sendMessage({
                action: 'pageChanged',
                data: { url, eventId, title: document.title }
            });
        }
    }
}).observe(document, { subtree: true, childList: true });