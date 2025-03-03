import sys
import time
import subprocess
import requests
from pynput import keyboard
import threading
import psutil
import os
from systray import SysTrayIcon
import webbrowser

class AssistantKeyListener:
    def __init__(self):
        self.server_process = None
        self.server_url = "http://localhost:3000"
        self.recording_f8 = False
        self.recording_f9 = False
        
    def start_server(self):
        """Inicia el servidor Node.js si no está corriendo"""
        # Verificar si el servidor ya está corriendo
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if 'node' in proc.info['name'].lower() and 'server.js' in ' '.join(proc.info['cmdline']):
                    print("Servidor ya está corriendo")
                    return
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        print("Iniciando servidor...")
        self.server_process = subprocess.Popen(
            ['node', 'server.js'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        # Esperar a que el servidor esté listo
        time.sleep(2)

    def simulate_key_press(self, key):
        """Simula una pulsación de tecla enviando una petición al servidor"""
        try:
            # Intentar abrir la página web si no está abierta
            webbrowser.open(self.server_url, new=0)
            
            # Aquí podrías implementar la lógica para simular la pulsación
            # Por ahora solo imprimimos un mensaje
            print(f"Tecla {key} presionada")
        except Exception as e:
            print(f"Error al simular tecla: {e}")

    def on_press(self, key):
        """Maneja los eventos de teclas presionadas"""
        try:
            if key == keyboard.Key.f8 and not self.recording_f8:
                self.recording_f8 = True
                self.simulate_key_press('F8')
            elif key == keyboard.Key.f9 and not self.recording_f9:
                self.recording_f9 = True
                self.simulate_key_press('F9')
        except Exception as e:
            print(f"Error en on_press: {e}")

    def on_release(self, key):
        """Maneja los eventos de teclas liberadas"""
        try:
            if key == keyboard.Key.f8:
                self.recording_f8 = False
            elif key == keyboard.Key.f9:
                self.recording_f9 = False
        except Exception as e:
            print(f"Error en on_release: {e}")

    def on_quit_callback(self, systray):
        """Callback para cuando se cierra la aplicación"""
        print("Cerrando aplicación...")
        if self.server_process:
            self.server_process.terminate()
        os._exit(0)

    def run(self):
        """Inicia el listener y el servidor"""
        try:
            # Iniciar el servidor
            self.start_server()

            # Configurar el icono en la bandeja del sistema
            menu_options = (("Salir", None, self.on_quit_callback),)
            systray = SysTrayIcon("icon.ico", "Asistente de Voz", menu_options)
            systray.start()

            # Iniciar el listener de teclado
            with keyboard.Listener(
                on_press=self.on_press,
                on_release=self.on_release) as listener:
                listener.join()

        except Exception as e:
            print(f"Error al iniciar la aplicación: {e}")
            if self.server_process:
                self.server_process.terminate()
            sys.exit(1)

if __name__ == "__main__":
    assistant = AssistantKeyListener()
    assistant.run() 