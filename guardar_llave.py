"""
Asistente rápido para guardar GEMINI_API_KEY desde el portapapeles de Windows
hacia E:\\mcp\\.env (sin exponerla en pantalla ni en GitHub).
"""

import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from src.google_integrations import save_gemini_api_key_to_env


def try_get_clipboard_aiza(root: tk.Tk) -> str:
    try:
        clip = root.clipboard_get().strip()
        if clip.startswith("AIza") and len(clip) >= 30:
            return clip
    except Exception:
        pass
    return ""


def main() -> None:
    root = tk.Tk()
    root.title("Guardar GEMINI_API_KEY Segura (NJ Fence & Railing)")
    root.geometry("540x250")
    root.configure(bg="#141C2B")
    root.attributes("-topmost", True)

    # Check if AIza key is already in clipboard right now
    auto_key = try_get_clipboard_aiza(root)
    if auto_key:
        env_path = save_gemini_api_key_to_env(auto_key)
        home_env = Path.home() / ".env"
        home_env.write_text(f"GEMINI_API_KEY={auto_key}\n", encoding="utf-8")
        print(f"EXITO: GEMINI_API_KEY detectada en el portapapeles y guardada en {env_path}")
        messagebox.showinfo(
            "¡Llave Guardada con Éxito!",
            f"Se detectó tu clave AIza... en el portapapeles y quedó guardada de forma segura en:\n{env_path}\n\n(Protegida fuera de GitHub).",
        )
        root.destroy()
        return

    lbl = tk.Label(
        root,
        text=(
            "1. Ve a la ventana de Chrome (Google AI Studio)\n"
            "2. Haz clic en el icono de COPIAR (dos cuadritos) junto a tu llave\n"
            "3. Luego haz clic en el botón verde de abajo:"
        ),
        bg="#141C2B",
        fg="#F7FAFC",
        font=("Segoe UI", 11, "bold"),
        justify="left",
    )
    lbl.pack(pady=20, padx=20)

    def on_paste_and_save() -> None:
        key = try_get_clipboard_aiza(root)
        if not key:
            messagebox.showwarning(
                "Aún no has copiado la llave AIza...",
                "En tu portapapeles todavía no hay una clave que empiece por 'AIza...'.\n\n"
                "Ve a Chrome (aistudio.google.com/api-keys) y haz clic en el icono de copiar (dos cuadritos a la derecha de la fila).",
            )
            return
        env_path = save_gemini_api_key_to_env(key)
        home_env = Path.home() / ".env"
        home_env.write_text(f"GEMINI_API_KEY={key}\n", encoding="utf-8")
        print(f"EXITO: GEMINI_API_KEY guardada en {env_path}")
        messagebox.showinfo(
            "¡Llave Guardada con Éxito!",
            f"Tu GEMINI_API_KEY quedó guardada de forma segura en:\n{env_path}\n\n¡Ya puedes cerrar esta ventana!",
        )
        root.destroy()

    btn = tk.Button(
        root,
        text="📋 Ya la copié en Chrome — Guardar desde mi Portapapeles",
        command=on_paste_and_save,
        bg="#38A169",
        fg="#FFFFFF",
        font=("Segoe UI", 11, "bold"),
        padx=16,
        pady=10,
        cursor="hand2",
    )
    btn.pack(pady=10)

    root.mainloop()


if __name__ == "__main__":
    main()
