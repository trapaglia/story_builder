// Variables globales para el estado de la historia
let storyInProgress = false;
let currentChapter = 1;
let totalChapters = 1;
let eventSource = null;

// Manejo de personajes
document.getElementById('add-character').addEventListener('click', function() {
    const container = document.getElementById('characters-container');
    const newCharacter = document.createElement('div');
    newCharacter.className = 'input-group mb-2';
    newCharacter.innerHTML = `
        <input type="text" class="form-control character-name" placeholder="Nombre del personaje">
        <button type="button" class="btn btn-outline-secondary remove-character">
            <i class="bi bi-trash"></i>×</button>
    `;
    container.appendChild(newCharacter);
});

document.getElementById('characters-container').addEventListener('click', function(e) {
    if (e.target.classList.contains('remove-character') || 
        e.target.parentElement.classList.contains('remove-character')) {
        const characterDiv = e.target.closest('.input-group');
        if (document.querySelectorAll('.character-name').length > 1) {
            characterDiv.remove();
        }
    }
});

// Formatear timestamp
function formatTimestamp(isoString) {
    const date = new Date(isoString);
    return date.toLocaleTimeString();
}

// Renderizar chat de agentes
function renderAgentChat(chatHistory) {
    const chatContainer = document.getElementById('agentChat');
    
    // Limpiar el mensaje inicial si existe
    if (chatContainer.querySelector('.text-muted')) {
        chatContainer.innerHTML = '';
    }
    
    // Si es un nuevo mensaje, añadirlo al final
    if (Array.isArray(chatHistory) && chatHistory.length > 0) {
        chatHistory.forEach(message => {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'agent-message';
            
            const headerContent = message.speaking_to === "todos" ? 
                `${message.agent}` : 
                `${message.agent} ${message.speaking_to}`;
            
            messageDiv.innerHTML = `
                <div class="agent-header">
                    <span class="agent-name">${headerContent}</span>
                    <span class="timestamp">${formatTimestamp(message.timestamp)}</span>
                </div>
                <div class="message-content">${message.content}</div>
            `;
            
            // Agregar animación de entrada
            messageDiv.style.opacity = '0';
            chatContainer.appendChild(messageDiv);
            
            // Animar la entrada del mensaje
            requestAnimationFrame(() => {
                messageDiv.style.transition = 'opacity 0.3s ease-in';
                messageDiv.style.opacity = '1';
            });
        });
        
        // Scroll suave al último mensaje
        chatContainer.scrollTo({
            top: chatContainer.scrollHeight,
            behavior: 'smooth'
        });
    }
}

// Iniciar la conexión SSE
function startEventSource() {
    if (eventSource) {
        eventSource.close();
    }
    
    eventSource = new EventSource('/chat_updates');
    
    eventSource.onmessage = function(event) {
        const data = JSON.parse(event.data);
        if (data.type === 'heartbeat') {
            return;
        }
        
        if (data.chat_history) {
            renderAgentChat(data.chat_history);
        }
    };
    
    eventSource.onerror = function() {
        console.log('SSE Error, reconectando...');
        if (eventSource.readyState === EventSource.CLOSED) {
            setTimeout(startEventSource, 1000);
        }
    };
}

// Manejar la navegación de capítulos
async function handleNextChapter() {
    const feedbackText = document.getElementById('chapter-feedback-text').value;
    const loadingElement = document.getElementById('loading');
    const nextChapterButton = document.getElementById('next-chapter');
    
    try {
        loadingElement.classList.remove('d-none');
        nextChapterButton.disabled = true;
        
        const response = await fetch('/next_chapter', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                feedback: feedbackText
            })
        });
        
        const data = await response.json();
        
        if (data.is_complete) {
            document.getElementById('chapter-navigation').classList.add('d-none');
            document.getElementById('storyOutput').innerHTML += `
                <div class="mt-4 text-center">
                    <h4>¡Historia Completada!</h4>
                    <p>Has llegado al final de todos los capítulos.</p>
                    <p>Total de caracteres: ${data.total_chars}</p>
                </div>`;
            return;
        }
        
        currentChapter = data.chapter_number;
        document.getElementById('current-chapter').textContent = currentChapter;
        
        // Animar la transición del capítulo
        const storyOutput = document.getElementById('storyOutput');
        storyOutput.style.opacity = '0';
        
        setTimeout(() => {
            storyOutput.innerHTML = `
                <h3>Capítulo ${data.chapter_number}: ${data.chapter_title}</h3>
                ${data.content}
            `;
            storyOutput.style.transition = 'opacity 0.5s ease-in';
            storyOutput.style.opacity = '1';
        }, 300);
        
        document.getElementById('char-count').textContent = data.character_count;
        document.getElementById('chapter-feedback-text').value = '';
        
    } catch (error) {
        console.error('Error al cargar el siguiente capítulo:', error);
        document.getElementById('storyOutput').innerHTML += `
            <p class="text-danger">Error al cargar el siguiente capítulo: ${error}</p>`;
    } finally {
        loadingElement.classList.add('d-none');
        nextChapterButton.disabled = false;
    }
}

// Configurar eventos de navegación
document.getElementById('next-chapter').addEventListener('click', handleNextChapter);

// Manejo del formulario
document.getElementById('storyForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    if (storyInProgress) {
        alert('Ya hay una historia en proceso de generación');
        return;
    }
    
    storyInProgress = true;
    
    // Mostrar loading y ocultar contenido anterior
    const loadingElement = document.getElementById('loading');
    const storyOutput = document.getElementById('storyOutput');
    const submitButton = this.querySelector('button[type="submit"]');
    
    loadingElement.classList.remove('d-none');
    storyOutput.innerHTML = '';
    document.getElementById('agentChat').innerHTML = `
        <p class="text-muted">Iniciando generación de historia...</p>
    `;
    submitButton.disabled = true;
    
    // Obtener los valores del formulario
    const initialIdea = document.getElementById('initial_idea').value;
    const characterCount = document.getElementById('character_count').value;
    const narrationStyle = document.getElementById('narration_style').value;
    const characterNames = Array.from(document.querySelectorAll('.character-name'))
        .map(input => input.value.trim())
        .filter(name => name !== '');
    
    try {
        // Iniciar la conexión SSE para actualizaciones en vivo
        startEventSource();
        
        const response = await fetch('/generate_story', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                initial_idea: initialIdea,
                character_count: characterCount,
                narration_style: narrationStyle,
                character_names: characterNames
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Animar la aparición de la historia
            storyOutput.style.opacity = '0';
            storyOutput.textContent = data.final_story;
            
            requestAnimationFrame(() => {
                storyOutput.style.transition = 'opacity 0.5s ease-in';
                storyOutput.style.opacity = '1';
            });
            
            document.getElementById('char-count').textContent = data.total_chars;
            
            if (data.has_more_chapters) {
                currentChapter = 1;
                totalChapters = data.total_chapters;
                document.getElementById('current-chapter').textContent = currentChapter;
                document.getElementById('total-chapters').textContent = totalChapters;
                document.getElementById('chapter-navigation').classList.remove('d-none');
            }
        } else {
            storyOutput.innerHTML = `<p class="text-danger">Error: ${data.error}</p>`;
        }
    } catch (error) {
        storyOutput.innerHTML = `<p class="text-danger">Error al conectar con el servidor: ${error}</p>`;
    } finally {
        loadingElement.classList.add('d-none');
        submitButton.disabled = false;
        storyInProgress = false;
    }
}); 