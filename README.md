Programa de Dictado por Voz para Windows
======================================

Descripción
----------
Este programa permite convertir voz a texto y escribirlo automáticamente en cualquier aplicación de Windows donde se encuentre el cursor. Es ideal para personas que prefieren dictar en lugar de escribir o tienen dificultades para teclear.

Funcionalidades
-------------
- Reconocimiento de voz en español
- Escritura automática en cualquier aplicación
- Control mediante teclas de acceso rápido
- Interfaz simple por línea de comandos

Tecnologías Utilizadas
--------------------
- Python 3.x
- SpeechRecognition: Para el reconocimiento de voz
- PyAudio: Para capturar audio del micrófono
- PyAutoGUI: Para simular la escritura
- Keyboard: Para manejar los atajos de teclado
- API de Google Speech Recognition: Para convertir voz a texto

Requisitos
---------
1. Python 3.x instalado
2. Micrófono funcional
3. Conexión a Internet (para el reconocimiento de voz)
4. Las dependencias listadas en requirements.txt

Instalación
----------
1. Clonar o descargar el repositorio
2. Instalar las dependencias:
   pip install -r requirements.txt

Uso
---
1. Ejecutar el programa:
   python speech_to_text_typer.py
2. Mantén presionada la tecla F2 mientras hablas
3. Suelta F2 cuando termines de hablar
4. El programa procesará automáticamente tu voz y escribirá el texto
5. Presiona ESC para salir

Notas
-----
- El programa requiere una conexión a Internet para funcionar
- La calidad del reconocimiento depende de la claridad del audio
- Se agrega un espacio automáticamente después de cada frase
- El programa está configurado para español (es-ES)
- El programa ajusta automáticamente el nivel de ruido ambiental
- La grabación se realiza solo mientras mantengas presionada la tecla F2 