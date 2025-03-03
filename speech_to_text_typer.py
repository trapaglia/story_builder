import speech_recognition as sr
import pyautogui
import keyboard
import time

def escuchar_y_escribir():
    # Inicializar el reconocedor
    r = sr.Recognizer()
    
    print("Mantén presionado 'F2' mientras hablas")
    print("Presiona 'ESC' para salir")
    
    while True:
        if keyboard.is_pressed('esc'):
            print("Programa terminado")
            break
            
        # Esperar a que se presione F2
        if keyboard.is_pressed('F2'):
            print("Escuchando...")
            
            # Capturar audio del micrófono
            with sr.Microphone() as source:
                # Ajustar el reconocedor para el ruido ambiental
                r.adjust_for_ambient_noise(source, duration=0.5)
                
                # Grabar mientras F2 esté presionado
                audio_data = []
                while keyboard.is_pressed('F2'):
                    try:
                        audio_chunk = source.stream.read(source.CHUNK)
                        audio_data.append(audio_chunk)
                    except KeyboardInterrupt:
                        break
                
                # Crear un AudioData con los chunks recolectados
                audio = sr.AudioData(b''.join(audio_data), 
                                   source.SAMPLE_RATE, 
                                   source.SAMPLE_WIDTH)
            
            print("Procesando...")
            try:
                # Convertir audio a texto
                texto = r.recognize_google(audio, language="es-ES")
                print(f"Has dicho: {texto}")
                
                # Escribir el texto donde esté el cursor
                pyautogui.write(texto + " ")
                
            except sr.UnknownValueError:
                print("No se pudo entender el audio")
            except sr.RequestError as e:
                print(f"Error en el servicio de reconocimiento: {e}")
        
        time.sleep(0.1)  # Pequeña pausa para no saturar el CPU

if __name__ == "__main__":
    escuchar_y_escribir() 