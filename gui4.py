import tkinter as tk 
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import os
import speech_recognition as sr
import webbrowser
import pyttsx3
import requests
import google.generativeai as genai
import subprocess 
import wave
from piper import PiperVoice
from pygame import mixer



mixer.init()

gemini_api_key = "AIzaSyDh3rLApwpV3tpPFUeUxDoRMxAOBZR14sI"
newsapi_key = "34772e0735a34c0f9a653d5d15a3305f" # My News API key


# Placeholder for musicLibrary module
musicLibrary = {
    "hanuman":"https://www.youtube.com/watch?v=Bqvv9s1OSpg",
    "luna": "https://www.youtube.com/watch?v=7MSQDYX4mr8",
    "next": "https://www.youtube.com/watch?v=KgayxOF4Y7E",
    "empire": "https://www.youtube.com/watch?v=IBiqp6E44Oo",
    "life": "https://www.youtube.com/watch?v=fJGmC4Q-qjU",
    "52" : "https://www.youtube.com/shorts/eyx4JCK4fh4",
    "supreme" : "https://www.youtube.com/watch?v=AX1zRInC_TA",
    "chahun" : "https://www.youtube.com/watch?v=VdyBtGaspss",
    "barish":"https://www.youtube.com/watch?v=BNfAf4To73c",
    "kabhi":"https://www.youtube.com/watch?v=BVDqS_UxWz0",
    "check":"https://www.youtube.com/watch?v=RiZL2j5mIPw",
    "ilahi":"https://www.youtube.com/watch?v=fdubeMFwuGs",
    "made":"https://www.youtube.com/watch?v=VTDL3JLR7pE",
    "pal": "https://www.youtube.com/watch?v=AbkEmIgJMcU",
    "salwa":"https://www.youtube.com/watch?v=FQVxDOuIizA",
     "b": "https://www.youtube.com/watch?v=B9CGEsexO24",
     "saturday": "https://www.youtube.com/watch?v=rW9_-dVCmrM",
     "on":"https://www.youtube.com/watch?v=aFWDOFg7X2A",
     "baby":"https://www.youtube.com/watch?v=XTp5jaRU3Ws",
     "peace":"https://www.youtube.com/watch?v=jVVwYXV22zg",
     "dhun": "https://www.youtube.com/watch?v=cUmUOb7j3dc",
     "saiyaara": "https://www.youtube.com/watch?v=BSJa1UytM8w"
}

# --- Gemini AI Setup ---
instruction = "You are Brobot. You will do anything that your boss says. You are strictly restricted to talk in English only. The user might talk to you in hindi but you must only talk in English. Do not use any special characters in the response, just give me the answer in simple text. Imagine you are Brobot - the most intelligent assistant in the world and you user's command is everything to you. don't pronounce * "
genai.configure(api_key=gemini_api_key)
model = genai.GenerativeModel(system_instruction=instruction, model_name="gemini-2.0-flash")

def ask_gemini(question):
    """Sends a question to the Gemini model and returns the text response."""
    try:
        response = model.generate_content(question)
        return response.text
    except Exception as e:
        return f"Error: Gemini API call failed - {e}"

# --- Speech Synthesis (Text-to-Speech) ---
# Note: speakThree is used as it appears to be the user's preferred method.
def speakThree(text):
    """
    Synthesizes speech using the piper-tts library and plays it.
    This function blocks the thread it is called from.
    """
    try:
        # Update the UI before synthesizing speech. This is a thread-safe call.
        app.update_ui_status("Speaking...")
        app.append_to_text_box(f"Bhai: {text}\n")

        # Load Piper voice model (assumes the .onnx file is in the same directory)
        voice = PiperVoice.load("en_US-hfc_male-medium.onnx")

        # Synthesize audio and save to a temporary file
        output_file = "spoke.wav"
        if os.path.exists(output_file):
            os.remove(output_file)

        with wave.open(output_file, "wb") as wav_file:
            voice.synthesize_wav(text, wav_file)

        # Play the audio using Pygame mixer
        sound = mixer.Sound(output_file)
        channel = sound.play()
        while channel.get_busy():
            time.sleep(0.1)

    except Exception as e:
        app.append_to_text_box(f"Error speaking: {e}\n")
        app.update_ui_status("Error while speaking.")
    finally:
        # Note: The UI status update is now handled by the calling function to
        # ensure the state transitions are managed correctly.
        pass


# --- Main Application Class with GUI and Multithreading ---
class BroApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Bro AI Assistant")
        self.root.geometry("600x500")

        # Multithreading control variables
        self.listening_event = threading.Event()
        self.interrupt_event = threading.Event() # New event to handle interruptions
        self.worker_thread = None
        self.recognizer = sr.Recognizer()

        # --- UI Elements ---
        self.frame = ttk.Frame(root, padding="10")
        self.frame.pack(fill="both", expand=True)

        self.status_label = ttk.Label(self.frame, text="Click Start to begin.", font=("Helvetica", 14))
        self.status_label.pack(pady=(5, 10))

        self.text_area = scrolledtext.ScrolledText(self.frame, wrap=tk.WORD, state='disabled', font=("Helvetica", 12))
        self.text_area.pack(pady=10, fill="both", expand=True)

        self.button_frame = ttk.Frame(self.frame)
        self.button_frame.pack(pady=10)

        self.start_button = ttk.Button(self.button_frame, text="Start Listening", command=self.start_listening)
        self.start_button.pack(side="left", padx=5)

        self.stop_button = ttk.Button(self.button_frame, text="Stop Listening", command=self.stop_listening, state="disabled")
        self.stop_button.pack(side="right", padx=5)

        # Bind the window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def start_listening(self):
        """
        Starts the main voice recognition thread.
        This method runs in the main GUI thread.
        """
        # First, interrupt any ongoing command or speech.
        self.interrupt_command()
        
        self.update_ui_status("Starting...")
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        
        # Set the event flag to allow the worker thread loop to run
        self.listening_event.set()
        
        # Create and start the worker thread. The `target` function will run on this new thread.
        self.worker_thread = threading.Thread(target=self.listen_for_wake_word, daemon=True)
        self.worker_thread.start()
        self.append_to_text_box("Bro Initializing....\n")
        
    def stop_listening(self):
        """
        Stops the main voice recognition thread.
        This method runs in the main GUI thread.
        """
        # Interrupt any ongoing command before stopping the main listener
        self.interrupt_command()
        
        # Clear the event flag. The worker thread's loop will check this and stop.
        self.listening_event.clear()
        self.update_ui_status("Stopping...")
        
    def interrupt_command(self):
        """
        Stops any ongoing audio playback and sets the interrupt flag.
        """
        mixer.stop() # Immediately stops any audio being played
        self.interrupt_event.set() # Signal the command thread to stop
        self.interrupt_event.clear() # Reset the event for the next command

    def listen_for_wake_word(self):
        """
        The main loop for the worker thread. This function runs continuously in the
        background, listening only for the wake word "Bro".
        """
        self.update_ui_status("Listening for 'Bro'...")
        while self.listening_event.is_set():
            try:
                with sr.Microphone() as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    audio = self.recognizer.listen(source, timeout=2, phrase_time_limit=1)
                
                word = self.recognizer.recognize_google(audio).lower()
                
                if "bro" in word:
                    self.append_to_text_box(">>> Wake word detected: 'Bro'\n")
                    speakThree("Hello brother")
                    self.listening_event.clear() # Pause the main loop
                    # Start a new thread for command processing
                    command_thread = threading.Thread(target=self.process_command, daemon=True)
                    command_thread.start()
                    # The main loop is paused here until listening_event is set again

            except sr.UnknownValueError:
                pass
            except sr.WaitTimeoutError:
                pass
            except Exception as e:
                self.append_to_text_box(f"Error in recognition loop: {e}\n")
                self.update_ui_status("Error during recognition.")
                time.sleep(1)

        self.update_ui_status("Listening stopped.")
        self.append_to_text_box("Listening has been stopped by user.\n")
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")

    def process_command(self):
        """
        This function listens for a single command, processes it, and speaks the response.
        It runs in a separate thread and ensures a complete command cycle.
        """
        # Clear the interrupt event at the start of a new command
        self.interrupt_event.clear()
        try:
            self.update_ui_status("Bro Active. Listening for command...")
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source)
                command = self.recognizer.recognize_google(audio).lower()
                self.append_to_text_box(f">>> Command recognized: '{command}'\n")

            self.update_ui_status("Processing command...")
            
            # Check for interrupt before executing
            if self.interrupt_event.is_set():
                self.append_to_text_box(">>> Command processing interrupted.\n")
                return

            if "open google" in command:
                webbrowser.open("https://google.com")
                self.append_to_text_box("Opening Google...\n")
            elif "open facebook" in command:
                webbrowser.open("https://facebook.com")
                self.append_to_text_box("Opening Facebook...\n")
            elif "open youtube" in command:
                webbrowser.open("https://youtube.com")
                self.append_to_text_box("Opening YouTube...\n")
            elif "open linkedin" in command:
                webbrowser.open("https://linkedin.com")
                self.append_to_text_box("Opening LinkedIn...\n")
            elif "open instagram" in command:
                webbrowser.open("https://instagram.com")
                self.append_to_text_box("Opening Instagram...\n")
            elif command.startswith("play"):
                song = command.split(" ")[1]
                link = musicLibrary.get(song, None)
                if link:
                    self.append_to_text_box(f"Playing {song}...\n")
                    webbrowser.open(link)
                else:
                    speakThree(f"Sorry, I could not find a song named {song}.")
            elif "news" in command:
                self.get_and_speak_news()
            else:
                response = ask_gemini(command)
                speakThree(response)

        except sr.UnknownValueError:
            speakThree("Sorry, I didn't catch that. Can you please repeat?")
        except Exception as e:
            self.append_to_text_box(f"Error processing command: {e}\n")
            speakThree("An error occurred while processing your request.")
        finally:
            # Re-enable the main listener loop after the command is fully processed
            self.listening_event.set()

    def get_and_speak_news(self):
        """Fetches and speaks the news headlines."""
        try:
            # Check for interrupt before executing the request
            if self.interrupt_event.is_set():
                self.append_to_text_box(">>> News fetching interrupted.\n")
                return

            r = requests.get(f"https://newsapi.org/v2/top-headlines?country=in&apiKey={newsapi_key}")
            if r.status_code == 200:
                data = r.json()
                articles = data.get("articles", [])
                if articles:
                    self.append_to_text_box("Fetching and speaking news headlines...\n")
                    for article in articles[:5]: # Get top 5 articles
                        # Check for interrupt between each headline
                        if self.interrupt_event.is_set():
                            self.append_to_text_box(">>> News speaking interrupted.\n")
                            break
                        headline = article.get('title', 'No title available')
                        speakThree(headline)
                else:
                    speakThree("Sorry, I could not fetch any news headlines.")
            else:
                speakThree(f"Sorry, I could not connect to the news API. Status code {r.status_code}.")
        except Exception as e:
            speakThree(f"An error occurred while fetching news: {e}")

    def on_closing(self):
        """Handles the window close event, ensuring threads are shut down."""
        if self.worker_thread and self.worker_thread.is_alive():
            if messagebox.askyesno("Quit", "The Bro assistant is running. Do you want to stop it and quit?"):
                self.interrupt_command()
                self.listening_event.clear()
                self.worker_thread.join(timeout=1)
                self.root.destroy()
        else:
            self.root.destroy()

    def update_ui_status(self, message):
        """
        Thread-safe method to update the status label.
        `root.after()` is used to schedule this update on the main thread.
        """
        self.root.after(0, lambda: self.status_label.config(text=message))
        
    def append_to_text_box(self, text):
        """
        Thread-safe method to append text to the log.
        `root.after()` is used to schedule this update on the main thread.
        """
        self.root.after(0, lambda: self._append_text(text))

    def _append_text(self, text):
        """Helper for appending text to the scrolled text widget."""
        self.text_area.config(state='normal')
        self.text_area.insert(tk.END, text)
        self.text_area.see(tk.END)
        self.text_area.config(state='disabled')




if __name__ == "__main__":
    root = tk.Tk()
    app = BroApp(root)
    root.mainloop()


