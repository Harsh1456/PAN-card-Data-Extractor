import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk
from pan_json import PANProcessor
import threading
import os
from tkinterdnd2 import DND_FILES, TkinterDnD
import time

class PANApp(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        self.TkinterDnDVersion = TkinterDnD._require(self)
        self.processor = PANProcessor()
        self.title("PAN Card Information Extractor")
        self.geometry("800x600")
        self.configure_appearance()
        self.create_initial_ui()
        self.setup_drag_drop()
        self.progress_running = False

    def configure_appearance(self):
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

    def create_initial_ui(self):
        # Main container for initial state
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(pady=40, padx=40, fill='both', expand=True)

        # Header
        self.header = ctk.CTkLabel(self.main_frame, 
                                 text="Extract PAN Card Information",
                                 font=("Arial", 24, "bold"))
        self.header.pack(pady=(30, 30))

        # Drag and Drop Area
        self.drop_frame = ctk.CTkFrame(self.main_frame, 
                                     height=200,
                                     border_width=2,
                                     border_color="#3B8ED0",
                                     corner_radius=15)
        self.drop_frame.pack(fill='x', padx=20, pady=10)
        
        self.drop_content = ctk.CTkLabel(self.drop_frame,
                                       text="Drag & Drop PAN Card Image Here",
                                       text_color=("gray50", "gray40"),
                                       font=("Arial", 14, "bold"),
                                       compound='top',
                                       anchor='center')
        self.drop_content.pack(expand=True, fill='both', pady=40)
        
        # Browse Files Button
        self.browse_btn = ctk.CTkButton(self.main_frame,
                                      text="Browse Files",
                                      command=self.browse_files)
        self.browse_btn.pack(pady=10)

    def create_processing_ui(self):
        # Processing UI elements
        self.processing_frame = ctk.CTkFrame(self)
        
        # File info
        self.file_label = ctk.CTkLabel(self.processing_frame,
                                      font=("Arial", 14),
                                      text_color=("gray50", "gray40"))
        self.file_label.pack(padx=30,pady=10)
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(self.processing_frame,
                                             height=20,
                                             corner_radius=10)
        self.progress_bar.pack(fill='x', padx=40, pady=10)
        self.progress_bar.set(0)
        
        # Percentage label
        self.progress_label = ctk.CTkLabel(self.processing_frame,
                                         text="0%",
                                         font=("Arial", 12))
        self.progress_label.pack(pady=5)
        
        # Loading spinner
        self.spinner_label = ctk.CTkLabel(self.processing_frame, text="Loading...")
        self.spinner_label.pack(pady=10)  
        
        # Results Display
        self.result_frame = ctk.CTkFrame(self.processing_frame, 
                                         height=300,
                                         corner_radius=10)
        self.result_frame.pack(fill='both', expand=True, padx=20, pady=20)

    def setup_drag_drop(self):
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.handle_drop)
        self.dnd_bind('<<DragEnter>>', self.on_drag_enter)
        self.dnd_bind('<<DragLeave>>', self.on_drag_leave)

    def on_drag_enter(self, event):
        self.drop_frame.configure(border_color="#1F6AA5")

    def on_drag_leave(self, event):
        self.drop_frame.configure(border_color="#3B8ED0")

    def handle_drop(self, event):
        files = event.data
        if files:
            file_path = files.strip("{}")  # Remove curly braces from Windows paths
            if os.path.isfile(file_path):
                self.start_processing(file_path)

    def browse_files(self):
        filetypes = (("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff"),
                   ("PDF files", "*.pdf"),
                   ("All files", "*.*"))
        file_path = filedialog.askopenfilename(filetypes=filetypes)
        if file_path and os.path.isfile(file_path):
            self.start_processing(file_path)

    def start_processing(self, file_path):
        # Switch to processing UI
        self.main_frame.pack_forget()
        self.create_processing_ui()
        self.processing_frame.pack(pady=40, padx=40, fill='both', expand=True)
        
        # Show file info
        self.file_label.configure(text=f"Processing: {os.path.basename(file_path)}")
        
        # Start processing
        self.progress_running = True
        threading.Thread(target=self.animate_spinner).start()
        threading.Thread(target=self.run_processing, args=(file_path,)).start()

    def animate_spinner(self):
        spinner_frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        frame = 0
        while self.progress_running:
            self.spinner_label.configure(text=spinner_frames[frame])
            frame = (frame + 1) % len(spinner_frames)
            time.sleep(0.1)
            self.update_idletasks()

    def run_processing(self, file_path):
        try:
            # Simulated progress updates
            for i in range(101):
                if not self.progress_running:
                    break
                self.progress_bar.set(i / 100)
                self.progress_label.configure(text=f"{i}%")
                time.sleep(0.03)
            
            # Actual processing
            data, missing = self.processor.process_image(file_path)
            
            if missing:
                self.show_error(missing)
            else:
                filename = os.path.splitext(os.path.basename(file_path))[0]
                saved_path = self.processor.save_to_json(data, filename)
                self.show_results(saved_path, data)  # Pass both saved_path and data correctly
                
        except Exception as e:
            messagebox.showerror("Error", f"Processing failed: {str(e)}")
        finally:
            self.progress_running = False
            self.spinner_label.configure(text="")  # Stop spinner

    def show_results(self, saved_path, data):
        self.spinner_label.pack_forget()
        
        fields = [
            ("Card Holder Name", data.get("name", "")),
            ("Father's Name", data.get("father_name", "")),
            ("PAN Number", data.get("pan_number", "")),
            ("Date of Birth", data.get("dob", ""))
        ]
        
        for field, value in fields:
            frame = ctk.CTkFrame(self.result_frame)
            frame.pack(fill='x', pady=2, padx=5)
            
            label = ctk.CTkLabel(frame, 
                               text=f"{field}:",
                               width=140,
                               anchor='w',
                               font=("Arial", 12, "bold"))
            label.pack(side='left', padx=5)
            
            entry = ctk.CTkEntry(frame,
                               width=400,
                               font=("Arial", 12),
                               fg_color=("white", "gray20"))
            entry.insert(0, value)
            entry.configure(state='readonly')
            entry.pack(side='left', fill='x', expand=True)
        
        success_frame = ctk.CTkFrame(self.result_frame, fg_color="transparent")
        success_frame.pack(pady=10)
        ctk.CTkLabel(success_frame, 
                   text=f"✓ Data saved to:\n{saved_path}", 
                   text_color="green",
                   font=("Arial", 12)).pack()
        
        # Add "Try Another One" button
        try_again_btn = ctk.CTkButton(self.result_frame, 
                                      text="Try Another One", 
                                      command=self.reset_to_initial_ui)
        try_again_btn.pack(pady=20)

    def reset_to_initial_ui(self):
        """Reset the UI to allow processing another image."""
        self.processing_frame.pack_forget()
        self.create_initial_ui()

    def show_error(self, missing):
        self.spinner_label.pack_forget()
        
        error_text = f"Missing fields detected:\n{', '.join(missing)}"
        if len(missing) >= 2:
            error_text += "\n\n⚠️ Please try again with a clearer image!"
            
        error_label = ctk.CTkLabel(self.result_frame, 
                                 text=error_text, 
                                 text_color="#ff5555",
                                 font=("Arial", 12),
                                 justify='left')
        error_label.pack(pady=20)

        try_again_btn = ctk.CTkButton(self.result_frame, 
                                      text="Try Another One", 
                                      command=self.reset_to_initial_ui)
        try_again_btn.pack(pady=20)

if __name__ == "__main__":
    app = PANApp()
    app.mainloop()
