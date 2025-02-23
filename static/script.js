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
    
    try {
        const response = await fetch('/generate_story', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                initial_idea: initialIdea,
                character_count: characterCount,
                narration_style: narrationStyle
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            storyOutput.textContent = data.story;
        } else {
            storyOutput.innerHTML = `<p class="text-danger">Error: ${data.error}</p>`;
        }
    } catch (error) {
        storyOutput.innerHTML = `<p class="text-danger">Error al conectar con el servidor: ${error}</p>`;
    } finally {
        loadingElement.classList.add('d-none');
    }
}); 