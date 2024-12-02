import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
from magic_pdf.pipe.UNIPipe import UNIPipe
from magic_pdf.pipe.OCRPipe import OCRPipe
from magic_pdf.pipe.TXTPipe import TXTPipe
from magic_pdf.data.data_reader_writer import FileBasedDataWriter
from magic_pdf.config.make_content_config import DropMode, MakeMode
import json
from loguru import logger


def pdf_parse_main(
    pdf_path,
    parse_method="auto",
    output_dir=None,
    is_json_md_dump=True,
    is_draw_visualization_bbox=True,
    lang=None,
    debug=False,
    start_page=None,
    end_page=None,
):
    """Main PDF processing function"""
    try:
        pdf_name = os.path.basename(pdf_path).split(".")[0]

        if output_dir:
            output_path = os.path.join(output_dir, pdf_name)
        else:
            output_path = os.path.join(os.path.dirname(pdf_path), pdf_name)

        output_image_path = os.path.join(output_path, "images")
        os.makedirs(output_image_path, exist_ok=True)

        image_path_parent = os.path.basename(output_image_path)
        pdf_bytes = open(pdf_path, "rb").read()

        image_writer = FileBasedDataWriter(output_image_path)
        md_writer = FileBasedDataWriter(output_path)

        # Initialize appropriate pipe based on method
        if parse_method == "auto":
            pipe = UNIPipe(pdf_bytes, {"_pdf_type": "", "model_list": []}, image_writer)
        elif parse_method == "txt":
            pipe = TXTPipe(pdf_bytes, [], image_writer)
        elif parse_method == "ocr":
            pipe = OCRPipe(pdf_bytes, [], image_writer)
        else:
            raise ValueError("Invalid parse method")

        # Process the PDF
        pipe.pipe_classify()
        pipe.pipe_analyze()
        pipe.pipe_parse()

        # Generate content
        content_list = pipe.pipe_mk_uni_format(image_path_parent, drop_mode="none")

        # Save results
        if is_json_md_dump:
            md_writer.write_string(
                f"{pdf_name}_content.json",
                json.dumps(content_list, ensure_ascii=False, indent=4),
            )

            # Generate and save markdown if requested
            md_content = pipe.pipe_mk_markdown(image_path_parent, drop_mode="none")
            if isinstance(md_content, list):
                md_content = "\n".join(md_content)
            md_writer.write_string(f"{pdf_name}.md", md_content)

        return True

    except Exception as e:
        logger.exception(f"Error processing PDF: {str(e)}")
        raise


class MinerUGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("MinerU PDF Processor")
        self.root.geometry("900x600")
        self.root.minsize(800, 500)

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.configure_styles()

        self.create_variables()
        self.create_gui()

        # Add window closing protocol directly here instead of in create_bindings
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def configure_styles(self):
        colors = {
            "bg": "#2E2E2E",
            "fg": "#FFFFFF",
            "button": "#404040",
            "button_pressed": "#505050",
            "accent": "#007ACC",
            "error": "#FF4444",
            "success": "#44FF44",
        }

        self.root.configure(bg=colors["bg"])
        self.style.configure("TFrame", background=colors["bg"])
        self.style.configure(
            "TLabelframe", background=colors["bg"], foreground=colors["fg"]
        )
        self.style.configure(
            "TLabelframe.Label", background=colors["bg"], foreground=colors["fg"]
        )
        self.style.configure("TLabel", background=colors["bg"], foreground=colors["fg"])
        self.style.configure(
            "TButton", background=colors["button"], foreground=colors["fg"], padding=5
        )
        self.style.configure(
            "Success.TButton", background=colors["success"], foreground="black"
        )
        self.style.configure(
            "TEntry", fieldbackground=colors["button"], foreground=colors["fg"]
        )
        self.style.configure(
            "TCheckbutton", background=colors["bg"], foreground=colors["fg"]
        )
        self.style.configure(
            "TCombobox", fieldbackground=colors["button"], background=colors["fg"]
        )
        self.style.configure(
            "Horizontal.TProgressbar",
            background=colors["accent"],
            troughcolor=colors["bg"],
        )

    def create_variables(self):
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.method = tk.StringVar(value="auto")
        self.lang = tk.StringVar()
        self.debug = tk.BooleanVar(value=False)
        self.start_page = tk.StringVar()
        self.end_page = tk.StringVar()
        self.status = tk.StringVar(value="Ready")
        self.processing = False
        self.convert_markdown = tk.BooleanVar(
            value=True
        )  # New variable for markdown conversion

    def create_gui(self):
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Input section
        input_frame = ttk.LabelFrame(main_frame, text="Input Settings", padding="10")
        input_frame.pack(fill=tk.X, pady=(0, 10))
        input_frame.columnconfigure(1, weight=1)

        # Input PDF
        ttk.Label(input_frame, text="Input PDF:").grid(
            row=0, column=0, sticky="w", pady=5
        )
        ttk.Entry(input_frame, textvariable=self.input_path).grid(
            row=0, column=1, sticky="ew", padx=5
        )
        ttk.Button(input_frame, text="Browse", command=self.browse_input).grid(
            row=0, column=2, padx=(5, 0)
        )

        # Output Directory
        ttk.Label(input_frame, text="Output Directory:").grid(
            row=1, column=0, sticky="w", pady=5
        )
        ttk.Entry(input_frame, textvariable=self.output_path).grid(
            row=1, column=1, sticky="ew", padx=5
        )
        ttk.Button(input_frame, text="Browse", command=self.browse_output).grid(
            row=1, column=2, padx=(5, 0)
        )

        # Processing options
        options_frame = ttk.LabelFrame(
            main_frame, text="Processing Options", padding="10"
        )
        options_frame.pack(fill=tk.X, pady=(0, 10))
        options_frame.columnconfigure(1, weight=1)

        # Method selection
        ttk.Label(options_frame, text="Method:").grid(
            row=0, column=0, sticky="w", pady=5
        )
        method_combo = ttk.Combobox(
            options_frame,
            textvariable=self.method,
            values=["auto", "ocr", "txt"],
            state="readonly",
        )
        method_combo.grid(row=0, column=1, sticky="w", padx=5)

        # Language input
        ttk.Label(options_frame, text="Language:").grid(
            row=1, column=0, sticky="w", pady=5
        )
        ttk.Entry(options_frame, textvariable=self.lang).grid(
            row=1, column=1, sticky="ew", padx=5
        )

        # Checkboxes
        checkbox_frame = ttk.Frame(options_frame)
        checkbox_frame.grid(row=2, column=0, columnspan=2, sticky="w", pady=5)

        ttk.Checkbutton(checkbox_frame, text="Debug Mode", variable=self.debug).pack(
            side=tk.LEFT, padx=(0, 10)
        )
        ttk.Checkbutton(
            checkbox_frame, text="Convert to Markdown", variable=self.convert_markdown
        ).pack(side=tk.LEFT)

        # Page range
        page_frame = ttk.Frame(options_frame)
        page_frame.grid(row=3, column=0, columnspan=2, sticky="w", pady=5)

        ttk.Label(page_frame, text="Page Range (optional):").pack(side=tk.LEFT)
        ttk.Entry(page_frame, textvariable=self.start_page, width=5).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Label(page_frame, text="to").pack(side=tk.LEFT)
        ttk.Entry(page_frame, textvariable=self.end_page, width=5).pack(
            side=tk.LEFT, padx=5
        )

        # Process button
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(
            button_frame,
            text="Process PDF",
            command=self.process_pdf,
            style="Success.TButton",
        ).pack(side=tk.LEFT, padx=5)

        # Status area
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.progress = ttk.Progressbar(status_frame, mode="indeterminate")
        self.progress.pack(fill=tk.X, pady=5)

        ttk.Label(status_frame, textvariable=self.status).pack(side=tk.LEFT)

    def process_pdf(self):
        if not self.validate_inputs():
            return

        def process():
            try:
                self.status.set("Processing PDF...")
                self.progress.start()

                # Convert page numbers if provided
                start_page = (
                    int(self.start_page.get()) if self.start_page.get() else None
                )
                end_page = int(self.end_page.get()) if self.end_page.get() else None

                pdf_parse_main(
                    pdf_path=self.input_path.get(),
                    parse_method=self.method.get(),
                    output_dir=self.output_path.get(),
                    is_json_md_dump=True,
                    is_draw_visualization_bbox=True,
                    lang=self.lang.get() if self.lang.get() else None,
                    debug=self.debug.get(),
                    start_page=start_page,
                    end_page=end_page,
                )

                self.status.set("Processing complete!")
                messagebox.showinfo("Success", "PDF processing completed successfully!")
            except Exception as e:
                self.status.set("Error occurred!")
                messagebox.showerror("Error", str(e))
                logger.exception("Error processing PDF")
            finally:
                self.progress.stop()
                self.processing = False

        if not self.processing:
            self.processing = True
            threading.Thread(target=process, daemon=True).start()

    def validate_inputs(self):
        if not self.input_path.get():
            messagebox.showerror("Error", "Please select an input PDF file.")
            return False
        if not self.output_path.get():
            messagebox.showerror("Error", "Please select an output directory.")
            return False

        # Validate page range if provided
        if self.start_page.get() or self.end_page.get():
            try:
                if self.start_page.get():
                    start = int(self.start_page.get())
                    if start < 0:
                        raise ValueError
                if self.end_page.get():
                    end = int(self.end_page.get())
                    if end < 0:
                        raise ValueError
                if self.start_page.get() and self.end_page.get():
                    if start > end:
                        messagebox.showerror(
                            "Error", "End page must be greater than start page."
                        )
                        return False
            except ValueError:
                messagebox.showerror("Error", "Page numbers must be positive integers.")
                return False

        return True

    def browse_input(self):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if path:
            self.input_path.set(path)
            if not self.output_path.get():
                self.output_path.set(os.path.dirname(path))

    def browse_output(self):
        path = filedialog.askdirectory()
        if path:
            self.output_path.set(path)

    def on_closing(self):
        if self.processing:
            if messagebox.askokcancel(
                "Quit", "Processing is in progress. Do you want to quit anyway?"
            ):
                self.root.destroy()
        else:
            self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = MinerUGUI()
    app.run()
