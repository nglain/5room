const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 3457;
const LOG_FILE = path.join(__dirname, 'room_log.json');

// Инициализация лога
if (!fs.existsSync(LOG_FILE)) {
    fs.writeFileSync(LOG_FILE, JSON.stringify({ sessions: [] }, null, 2));
}

const server = http.createServer((req, res) => {
    // CORS
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }

    // Отдаём статику
    if (req.method === 'GET' && (req.url === '/' || req.url === '/index.html')) {
        const html = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');
        res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
        res.end(html);
        return;
    }

    // API для логгирования
    if (req.method === 'POST' && req.url === '/log') {
        let body = '';
        req.on('data', chunk => body += chunk);
        req.on('end', () => {
            try {
                const entry = JSON.parse(body);
                entry.timestamp = new Date().toISOString();

                // Читаем текущий лог
                const log = JSON.parse(fs.readFileSync(LOG_FILE, 'utf8'));

                // Добавляем запись
                if (!log.currentSession) {
                    log.currentSession = {
                        started: new Date().toISOString(),
                        entries: []
                    };
                }
                log.currentSession.entries.push(entry);

                // Сохраняем
                fs.writeFileSync(LOG_FILE, JSON.stringify(log, null, 2));

                console.log(`📝 ${entry.type}: ${entry.being || 'System'} - ${entry.content?.substring(0, 50) || ''}`);

                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ ok: true }));
            } catch (e) {
                console.error('Log error:', e);
                res.writeHead(500);
                res.end(JSON.stringify({ error: e.message }));
            }
        });
        return;
    }

    // Получить весь лог
    if (req.method === 'GET' && req.url === '/log') {
        const log = fs.readFileSync(LOG_FILE, 'utf8');
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(log);
        return;
    }

    // Завершить сессию
    if (req.method === 'POST' && req.url === '/end-session') {
        try {
            const log = JSON.parse(fs.readFileSync(LOG_FILE, 'utf8'));
            if (log.currentSession) {
                log.currentSession.ended = new Date().toISOString();
                log.sessions.push(log.currentSession);
                log.currentSession = null;
                fs.writeFileSync(LOG_FILE, JSON.stringify(log, null, 2));
            }
            res.writeHead(200);
            res.end(JSON.stringify({ ok: true }));
        } catch (e) {
            res.writeHead(500);
            res.end(JSON.stringify({ error: e.message }));
        }
        return;
    }

    res.writeHead(404);
    res.end('Not found');
});

server.listen(PORT, () => {
    console.log(`\n🏠 AI Room Server запущен!`);
    console.log(`📍 http://localhost:${PORT}`);
    console.log(`📝 Логи сохраняются в: ${LOG_FILE}\n`);
});
