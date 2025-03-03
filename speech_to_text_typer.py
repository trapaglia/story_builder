import speech_recognition as sr
import pyautogui
import keyboard
import time

def escuchar_y_escribir():
    # Inicializar el reconocedor
    r = sr.Recognizer()
    
    print("Presiona 'F2' para comenzar a escuchar")
    print("Presiona 'ESC' para salir")
    
    while True:
        # Esperar a que se presione F2
        keyboard.wait('F2')
        
        if keyboard.is_pressed('esc'):
            print("Programa terminado")
            break
            
        # Capturar audio del micrófono
        with sr.Microphone() as source:
            print("Escuchando...")
            audio = r.listen(source)
            
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

if __name__ == "__main__":
    escuchar_y_escribir() 