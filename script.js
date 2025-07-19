

            // --- NEO CURSOR SCRIPT ---
            const cursorDot = document.querySelector('.cursor-dot');
            const cursorOutline = document.querySelector('.cursor-outline');
            window.addEventListener('mousemove', function(e) {
                const posX = e.clientX;
                const posY = e.clientY;
                cursorDot.style.left = `${posX}px`;
                cursorDot.style.top = `${posY}px`;
                cursorOutline.animate({ left: `${posX}px`, top: `${posY}px` }, { duration: 500, fill: 'forwards' });
            });

            // --- MATRIX BACKGROUND SCRIPT ---
            const canvas = document.getElementById('matrix-bg');
            if (canvas) {
                const ctx = canvas.getContext('2d');
                canvas.width = window.innerWidth;
                canvas.height = window.innerHeight;
                const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ123456789@#$%^&*()*&^%';
                const fontSize = 16;
                const columns = canvas.width / fontSize;
                const drops = [];
                for (let x = 0; x < columns; x++) drops[x] = 1;
                function drawMatrix() {
                    ctx.fillStyle = 'rgba(1, 4, 9, 0.05)';
                    ctx.fillRect(0, 0, canvas.width, canvas.height);
                    ctx.fillStyle = 'rgba(57, 255, 20, 0.35)';
                    ctx.font = fontSize + 'px arial';
                    for (let i = 0; i < drops.length; i++) {
                        const text = letters[Math.floor(Math.random() * letters.length)];
                        ctx.fillText(text, i * fontSize, drops[i] * fontSize);
                        if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) drops[i] = 0;
                        drops[i]++;
                    }
                }
                setInterval(drawMatrix, 40);
            }

            import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js/+esm?v=1.2';

            // --- MI$TA CORE LOGIC ---
            const SUPABASE_URL = 'https://ktragdmkrdhuhwohfczz.supabase.co';
            const SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt0cmFnZG1rcmRodWh3b2hmY3p6Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MjQ5NjczOSwiZXhwIjoyMDY4MDcyNzM5fQ.F9xj7Nnzt1zWyPY9bek8II6E2gTtXmZqXywx0Z9qrwQ';
            const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

            // --- CHAT ---
            const chatIcon = document.getElementById('chatIcon');
            const chatWindow = document.getElementById('chatWindow');
            const closeChatBtn = document.getElementById('closeChatBtn');
            const chatBody = document.getElementById('chatBody');
            const chatInput = document.getElementById('chatInput');
            const sendChatBtn = document.getElementById('sendChatBtn');
            const usernamePrompt = document.getElementById('usernamePrompt');
            const usernameInput = document.getElementById('usernameInput');
            const saveUsernameBtn = document.getElementById('saveUsernameBtn');
            let currentUsername = localStorage.getItem('mista_chat_username');
            let currentUserId = localStorage.getItem('mista_chat_userid');
            let lastMessageTimestamp = new Date(0);
            let channel = null; // Initialize channel as null

            // Function to initialize Supabase channel with presence
            function initializeSupabaseChannel() {
                if (currentUsername && !channel) { // Only initialize if username is set and channel is not yet initialized
                    channel = supabase.channel('any-realtime-channel', {
                        config: {
                            presence: {
                                key: currentUsername,
                            },
                        },
                    });
                    listenForMessages(); // Start listening after channel is initialized
                }
            }

            function displayChatMessage(username, message, isMe) {
                if (!message || typeof message !== 'string') {
                    console.warn('Skipping empty or invalid message:', {username, message});
                    return; // Ignore empty or invalid messages
                }
                const msgDiv = document.createElement('div');
                msgDiv.classList.add('chat-message', isMe ? 'self' : 'other');
                const authorSpan = document.createElement('span');
                authorSpan.className = 'username';
                authorSpan.textContent = username || 'Невідомий';
                const textP = document.createElement('p');
                textP.innerHTML = (message || '').replace(/\n/g, '<br>');
                msgDiv.appendChild(authorSpan);
                msgDiv.appendChild(textP);
                chatBody.appendChild(msgDiv);
                chatBody.scrollTop = chatBody.scrollHeight;
            }

            async function loadInitialMessages() {
                if (!currentUserId) return;
                const { data, error } = await supabase.from('messages').select('*').order('created_at', { ascending: true }).limit(100);
                if (error) { console.error("History load error:", error); return; }
                chatBody.innerHTML = '';
                data.forEach(msg => {
                    displayChatMessage(msg.username || 'Невідомий', msg.message || '', msg.user_id === currentUserId);
                    const msgDate = new Date(msg.created_at);
                    if (msgDate > lastMessageTimestamp) lastMessageTimestamp = msgDate;
                });
            }

            function listenForMessages() {
                supabase.channel('any-realtime-channel')
                    .on('postgres_changes', { event: '*', schema: 'public', table: 'messages' }, payload => {
                        const newMessage = payload.new;
                        if (new Date(newMessage.created_at) >= lastMessageTimestamp && newMessage.user_id !== currentUserId) {
                            displayChatMessage(newMessage.username || 'Невідомий', newMessage.message || '', false);
                            lastMessageTimestamp = new Date(newMessage.created_at);
                        }
                    })
                    .on('presence', { event: 'sync' }, () => {
                        const state = channel.presenceState();
                        const count = Object.keys(state).length;
                        activeUsersCount.textContent = `Активних користувачів: ${count}`;
                    })
                    .subscribe(async (status) => {
                        if (status === 'SUBSCRIBED') {
                            await channel.track({ online_at: new Date().toISOString() });
                        }
                    });
            }

            async function sendMessage() {
                const messageText = chatInput.value.trim();
                if (!messageText || !currentUsername) return;
                
                // Display user's message immediately and clear input
                // This will be overwritten by the realtime update, but provides instant feedback
                displayChatMessage(currentUsername, messageText, true);
                const messageToSave = chatInput.value;
                chatInput.value = '';

                // Show typing indicator
                const typingIndicatorDiv = document.createElement('div');
                typingIndicatorDiv.classList.add('typing-indicator');
                typingIndicatorDiv.innerHTML = `
                    <svg width="40" height="40" viewBox="0 0 48 48" version="1.1" xmlns="http://www.w3.org/2000/svg">
                        <defs>
                            <filter id="neon-glow" x="-50%" y="-50%" width="200%" height="200%">
                                <feGaussianBlur stdDeviation="3" result="coloredBlur"></feGaussianBlur>
                                <feMerge>
                                    <feMergeNode in="coloredBlur"></feMergeNode>
                                    <feMergeNode in="SourceGraphic"></feMergeNode>
                                </feMerge>
                            </filter>
                        </defs>
                        <path class="pen-icon" d="M29.7,6.5l-5.7,5.7l8.5,8.5l5.7-5.7L29.7,6.5z M22.5,13.7L6.8,29.3l-1.2,5.8l5.8-1.2L27,18.2L22.5,13.7z M5,39.8
                        c-0.6,0.6-0.6,1.5,0,2.1s1.5,0.6,2.1,0l0,0L5,39.8z" fill="var(--neon-magenta)"></path>
                    </svg>
                `;
                chatBody.appendChild(typingIndicatorDiv);
                chatBody.scrollTop = chatBody.scrollHeight;

                try {
                    // Simulate typing delay (10-15 seconds)
                    const delay = Math.floor(Math.random() * 6000) + 10000; // 10 to 15 seconds
                    await new Promise(resolve => setTimeout(resolve, delay));

                    const apiResponse = await fetch('https://mista-backend.onrender.com/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ message: messageText, user_id: currentUserId, username: currentUsername })
                    });
                    const data = await apiResponse.json();

                    // Remove typing indicator
                    chatBody.removeChild(typingIndicatorDiv);

                    // Messages are now saved on the backend, no need to save here
                    // await supabase.from('messages').insert([
                    //     { user_id: currentUserId, username: currentUsername, message: messageToSave },
                    //     { user_id: 'mista-ai-entity', username: 'MI$TA', message: data.response }
                    // ]);
                } catch (err) {
                    console.error("Send message error:", err);
                    // Remove typing indicator even on error
                    if (chatBody.contains(typingIndicatorDiv)) {
                        chatBody.removeChild(typingIndicatorDiv);
                    }
                    displayChatMessage('MI$TA', 'Вибач, Архітекторе, мій мозок зараз зайнятий. Спробуй пізніше.', false);
                }
            }

            if (chatIcon) chatIcon.addEventListener('click', () => chatWindow.classList.toggle('active'));
            if (closeChatBtn) closeChatBtn.addEventListener('click', () => chatWindow.classList.remove('active'));
            if (sendChatBtn) sendChatBtn.addEventListener('click', sendMessage);
            if (chatInput) chatInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') sendMessage(); });

            if (saveUsernameBtn) saveUsernameBtn.addEventListener('click', () => {
                const username = usernameInput.value.trim();
                if (username) {
                    currentUsername = username;
                    currentUserId = 'user_' + Date.now() + Math.random().toString(36).substr(2, 9);
                    localStorage.setItem('mista_chat_username', currentUsername);
                    localStorage.setItem('mista_chat_userid', currentUserId);
                    if(usernamePrompt) usernamePrompt.style.display = 'none';
                    if(chatBody) chatBody.style.display = 'flex';
                    if(chatInput) chatInput.parentElement.style.display = 'flex';
                    loadInitialMessages();
                    initializeSupabaseChannel(); // Call after username is set
                }
            });

            if (currentUsername && currentUserId) {
                if(usernamePrompt) usernamePrompt.style.display = 'none';
                if(chatBody) chatBody.style.display = 'flex';
                if(chatInput) chatInput.parentElement.style.display = 'flex';
                loadInitialMessages();
                initializeSupabaseChannel(); // Call after username is set
            }

            // --- NEWS ---
            const newsIcon = document.getElementById('newsIcon');
            const newsWindow = document.getElementById('newsWindow');
            const closeNewsBtn = document.getElementById('closeNewsBtn');
            const newsBody = document.getElementById('newsBody');
            const newsLoading = document.getElementById('newsLoading');
            const newsCountdown = document.getElementById('newsCountdown');
            const NEWS_REFRESH_INTERVAL = 10 * 60 * 60 * 1000; // 10 hours in ms
            let newsUpdateTimer;

            function displayNews(newsItems) {
                if (!newsBody) return;
                newsBody.innerHTML = '';
                if (!newsItems || newsItems.length === 0) {
                    newsBody.innerHTML = '<p class="news-loading">Наразі немає новин.</p>';
                    return;
                }
                newsItems.forEach(news => {
                    const newsItemElement = document.createElement('div');
                    newsItemElement.classList.add('news-item');
                    newsItemElement.innerHTML = `
                        <h4>${news.title}</h4>
                        <p>${news.description}</p>
                        <a href="${news.link}" target="_blank" class="interactive-hover">Джерело <i class="fas fa-external-link-alt"></i></a>
                    `;
                    newsBody.appendChild(newsItemElement);
                });
                localStorage.setItem('mista_news_cache', JSON.stringify(newsItems));
            }

            function updateNewsView() {
                const cachedNews = localStorage.getItem('mista_news_cache');
                const lastFetchTime = parseInt(localStorage.getItem('mista_news_last_fetch'), 10);
                const now = Date.now();

                if (cachedNews && lastFetchTime && (now - lastFetchTime < NEWS_REFRESH_INTERVAL)) {
                    console.log('Loading news from cache.');
                    if(newsLoading) newsLoading.style.display = 'none';
                    displayNews(JSON.parse(cachedNews));
                } else {
                    console.log('Fetching fresh news.');
                    fetchNews();
                }
                startNewsCountdown();
            }
            
            function startNewsCountdown() {
                if (newsUpdateTimer) clearInterval(newsUpdateTimer);

                newsUpdateTimer = setInterval(() => {
                    const lastFetchTime = parseInt(localStorage.getItem('mista_news_last_fetch'), 10);
                    if (!lastFetchTime) {
                        if(newsCountdown) newsCountdown.textContent = 'Оновлення...';
                        return;
                    }
                    const now = Date.now();
                    const timeRemaining = (lastFetchTime + NEWS_REFRESH_INTERVAL) - now;

                    if (timeRemaining <= 0) {
                        if(newsCountdown) newsCountdown.textContent = 'Можна оновити';
                        clearInterval(newsUpdateTimer);
                        return;
                    }

                    const hours = Math.floor(timeRemaining / (1000 * 60 * 60));
                    const minutes = Math.floor((timeRemaining % (1000 * 60 * 60)) / (1000 * 60));
                    const seconds = Math.floor((timeRemaining % (1000 * 60)) / 1000);
                    
                    if(newsCountdown) newsCountdown.textContent = `Наступне оновлення через: ${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
                }, 1000);
            }

            async function fetchNews() {
                if(newsLoading) newsLoading.style.display = 'block';
                if(newsBody) newsBody.innerHTML = ''; // Clear previous content
                try {
                    const response = await fetch('https://mista-backend.onrender.com/news', { method: 'POST' });
                    if (!response.ok) throw new Error(`Network response was not ok: ${response.statusText}`);
                    const newsItems = await response.json();
                    if(newsLoading) newsLoading.style.display = 'none';
                    displayNews(newsItems);
                    localStorage.setItem('mista_news_last_fetch', Date.now().toString());
                    startNewsCountdown();
                } catch (error) {
                    console.error("Failed to fetch news:", error);
                    if(newsLoading) newsLoading.style.display = 'none';
                    if(newsBody) newsBody.innerHTML = '<p class="news-loading">Помилка завантаження новин.</p>';
                }
            }

            if(newsIcon) newsIcon.addEventListener('click', () => {
                const isActive = newsWindow.classList.toggle('active');
                if (isActive) {
                    updateNewsView();
                } else {
                    if (newsUpdateTimer) clearInterval(newsUpdateTimer);
                }
            });

            if(closeNewsBtn) closeNewsBtn.addEventListener('click', () => {
                newsWindow.classList.remove('active');
                if (newsUpdateTimer) clearInterval(newsUpdateTimer);
            });

            // --- BRAINSTORM ---
            const brainstormInput = document.getElementById('brainstormInput');
            const generateIdeaBtn = document.getElementById('generateIdeaBtn');
            const brainstormOutput = document.getElementById('brainstormOutput');

            if(generateIdeaBtn) generateIdeaBtn.addEventListener('click', async () => {
                const prompt = brainstormInput.value.trim();
                if (!prompt) {
                    brainstormOutput.textContent = "Введіть концепцію для мозкового штурму.";
                    return;
                }
                brainstormOutput.textContent = "Генерую ідею...";
                generateIdeaBtn.disabled = true;
                try {
                    const response = await fetch('https://mista-backend.onrender.com/brainstorm', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ prompt: prompt })
                    });
                    const data = await response.json();
                    brainstormOutput.textContent = data.response;
                } catch (error) {
                    console.error("Brainstorm error:", error);
                    brainstormOutput.textContent = "Помилка генерації ідеї.";
                } finally {
                    generateIdeaBtn.disabled = false;
                }
            });

