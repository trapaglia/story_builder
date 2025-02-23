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
    chatContainer.innerHTML = '';
    
    chatHistory.forEach(message => {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'agent-message';
        messageDiv.innerHTML = `
            <div class="agent-name">${message.agent}</div>
            <div class="message-content">${message.content}</div>
            <div class="timestamp">${formatTimestamp(message.timestamp)}</div>
        `;
        chatContainer.appendChild(messageDiv);
    });
    
    // Scroll al final del chat
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Manejo del formulario
document.getElementById('storyForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    // Mostrar loading y ocultar contenido anterior
    const loadingElement = document.getElementById('loading');
    const storyOutput = document.getElementById('storyOutput');
    loadingElement.classList.remove('d-none');
    storyOutput.innerHTML = '';
    
    // Obtener los valores del formulario
    const initialIdea = document.getElementById('initial_idea').value;
    const characterCount = document.getElementById('character_count').value;
    const narrationStyle = document.getElementById('narration_style').value;
    const characterNames = Array.from(document.querySelectorAll('.character-name'))
        .map(input => input.value.trim())
        .filter(name => name !== '');
    
    try {
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
            storyOutput.textContent = data.final_story;
            renderAgentChat(data.chat_history);
        } else {
            storyOutput.innerHTML = `<p class="text-danger">Error: ${data.error}</p>`;
        }
    } catch (error) {
        storyOutput.innerHTML = `<p class="text-danger">Error al conectar con el servidor: ${error}</p>`;
    } finally {
        loadingElement.classList.add('d-none');
    }
}); 