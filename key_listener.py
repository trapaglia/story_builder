import sys
import os
import time
from pynput import keyboard
import threading
import tkinter as tk
from tkinter import ttk
from infi.systray import SysTrayIcon
import sounddevice as sd
import soundfile as sf
import numpy as np
import wave
import io
from openai import OpenAI
from google.cloud import texttospeech
import tempfile
from dotenv import load_dotenv
import http.client
http.client._MAXHEADERS = 1000

class VoiceAssistant:
    def __init__(self):
        load_dotenv()
        self.recording = False
        self.frames = []
        self.sample_rate = 44100
        self.window = None
        self.recording_f8 = False
        self.recording_f9 = False
        
        # Configurar OpenAI
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("No se encontró OPENAI_API_KEY en las variables de entorno")
        self.openai_client = OpenAI(api_key=api_key)
        
        # Configurar Google Text-to-Speech
        self.tts_client = texttospeech.TextToSpeechClient()
        
        # Configuración de voz
        self.voice_config = texttospeech.VoiceSelectionParams(
            language_code='es-ES',
            name='es-ES-Standard-A',
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
        )
        
        # Configuración de audio
        self.audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            sample_rate_hertz=24000
        )

    def create_popup(self, text, with_audio=False, audio_data=None):
        """Crea una ventana popup con el texto y opcionalmente audio"""
        if self.window is not None:
            self.window.destroy()
        
        self.window = tk.Tk()
        self.window.title("Asistente de Voz")
        self.window.geometry("400x300")
        
        # Estilo y tema
        style = ttk.Style()
        style.configure("Custom.TLabel", padding=10, font=('Arial', 11))
        
        # Marco principal
        frame = ttk.Frame(self.window, padding="10")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Texto
        text_widget = tk.Text(frame, wrap=tk.WORD, height=8, font=('Arial', 11))
        text_widget.insert(tk.END, text)
        text_widget.grid(row=0, column=0, pady=10, sticky=(tk.W, tk.E))
        text_widget.config(state='disabled')
        
        # Si hay audio, agregar controles
        if with_audio and audio_data:
            # Guardar el audio temporalmente
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            temp_file.write(audio_data)
            temp_file.close()
            
            def play_audio():
                data, sr = sf.read(temp_file.name)
                sd.play(data, sr)
                sd.wait()
            
            ttk.Button(frame, text="Reproducir Audio", command=play_audio).grid(row=1, column=0, pady=5)
        
        # Botón cerrar
        ttk.Button(frame, text="Cerrar", command=self.window.destroy).grid(row=2, column=0, pady=10)
        
        # Centrar la ventana
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')
        
        self.window.lift()
        self.window.focus_force()

    def start_recording(self):
        """Inicia la grabación de audio"""
        self.recording = True
        self.frames = []
        
        def audio_callback(indata, frames, time, status):
            if self.recording:
                self.frames.append(indata.copy())
        
        self.stream = sd.InputStream(callback=audio_callback, channels=1, 
                                   samplerate=self.sample_rate)
        self.stream.start()

    def stop_recording(self, is_chat=False):
        """Detiene la grabación y procesa el audio"""
        if not self.recording:
            return
            
        self.recording = False
        self.stream.stop()
        self.stream.close()
        
        if not self.frames:
            return
            
        # Convertir frames a audio
        audio_data = np.concatenate(self.frames, axis=0)
        
        # Guardar temporalmente como WAV
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_wav:
            with wave.open(temp_wav.name, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self.sample_rate)
                wf.writeframes((audio_data * 32767).astype(np.int16).tobytes())
        
        try:
            # Transcribir audio
            with open(temp_wav.name, 'rb') as audio_file:
                transcript = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="es"
                )
            
            if is_chat:
                # Obtener respuesta del chat
                completion = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Eres un asistente amable y servicial. Responde de manera concisa y clara en español."},
                        {"role": "user", "content": transcript.text}
                    ]
                )
                response_text = completion.choices[0].message.content
                
                # Convertir respuesta a voz
                synthesis_input = texttospeech.SynthesisInput(text=response_text)
                response = self.tts_client.synthesize_speech(
                    input=synthesis_input,
                    voice=self.voice_config,
                    audio_config=self.audio_config
                )
                
                # Mostrar respuesta con audio
                self.create_popup(response_text, True, response.audio_content)
            else:
                # Solo mostrar transcripción
                self.create_popup(transcript.text)
                
        except Exception as e:
            self.create_popup(f"Error: {str(e)}")
        finally:
            os.unlink(temp_wav.name)

    def on_press(self, key):
        """Maneja los eventos de teclas presionadas"""
        try:
            if key == keyboard.Key.f8 and not self.recording_f8:
                print("F8 presionada - Iniciando dictado")
                self.recording_f8 = True
                self.start_recording()
            elif key == keyboard.Key.f9 and not self.recording_f9:
                print("F9 presionada - Iniciando chat")
                self.recording_f9 = True
                self.start_recording()
        except Exception as e:
            print(f"Error en on_press: {e}")

    def on_release(self, key):
        """Maneja los eventos de teclas liberadas"""
        try:
            if key == keyboard.Key.f8 and self.recording_f8:
                print("F8 liberada - Finalizando dictado")
                self.recording_f8 = False
                self.stop_recording(is_chat=False)
            elif key == keyboard.Key.f9 and self.recording_f9:
                print("F9 liberada - Finalizando chat")
                self.recording_f9 = False
                self.stop_recording(is_chat=True)
        except Exception as e:
            print(f"Error en on_release: {e}")

    def on_quit_callback(self, systray):
        """Callback para cuando se cierra la aplicación"""
        print("Cerrando aplicación...")
        if self.window:
            self.window.destroy()
        os._exit(0)

    def run(self):
        """Inicia la aplicación"""
        try:
            print("Iniciando Asistente de Voz...")
            
            # Configurar el icono en la bandeja del sistema
            menu_options = (("Salir", None, self.on_quit_callback),)
            systray = SysTrayIcon("icon.ico", "Asistente de Voz", menu_options)
            systray.start()
            print("✓ Icono en bandeja del sistema iniciado")

            print("Iniciando listener de teclado...")
            # Iniciar el listener de teclado
            with keyboard.Listener(
                on_press=self.on_press,
                on_release=self.on_release) as listener:
                print("✓ Listener de teclado iniciado - Esperando teclas F8/F9...")
                listener.join()

        except Exception as e:
            print(f"❌ Error al iniciar la aplicación: {e}")
            sys.exit(1)

if __name__ == "__main__":
    assistant = VoiceAssistant()
    assistant.run() 