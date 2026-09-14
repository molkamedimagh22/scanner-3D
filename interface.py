import tkinter as tk
from tkinter import ttk, messagebox
import random


# ============================================================
# COULEURS
# ============================================================

BG = "#0B0F14"
CARD = "#151B23"
CARD2 = "#1D2630"

WHITE = "#FFFFFF"
GRAY = "#9AA4B2"

BLUE = "#55B7C8"
BLUE_DARK = "#3D95A5"

GREEN = "#35C98A"
RED = "#F05A5A"
ORANGE = "#F0A43C"


# ============================================================
# FENETRE PRINCIPALE
# ============================================================

fenetre = tk.Tk()
fenetre.title("ESP32 3D Scanner")
fenetre.geometry("1200x780")
fenetre.minsize(1000, 700)
fenetre.configure(bg=BG)


# ============================================================
# CONFIGURATION GRID
# ============================================================

fenetre.grid_rowconfigure(1, weight=1)
fenetre.grid_columnconfigure(0, weight=1)


# ============================================================
# HEADER
# ============================================================

header = tk.Frame(fenetre, bg=BG)
header.grid(row=0, column=0, sticky="ew", padx=30, pady=(20, 10))

header.grid_columnconfigure(0, weight=1)

titre = tk.Label(
    header,
    text="ESP32 3D SCANNER",
    font=("Segoe UI", 24, "bold"),
    fg=WHITE,
    bg=BG
)
titre.grid(row=0, column=0, sticky="w")

sous_titre = tk.Label(
    header,
    text="Interface de contrôle et de visualisation",
    font=("Segoe UI", 10),
    fg=GRAY,
    bg=BG
)
sous_titre.grid(row=1, column=0, sticky="w", pady=(3, 0))


# ============================================================
# ZONE PRINCIPALE
# ============================================================

container = tk.Frame(fenetre, bg=BG)
container.grid(row=1, column=0, sticky="nsew", padx=30, pady=10)

container.grid_rowconfigure(0, weight=1)
container.grid_columnconfigure(0, weight=1)


# ============================================================
# CREATION DES PAGES
# ============================================================

pages = {}

page_connexion = tk.Frame(container, bg=CARD)
page_parametres = tk.Frame(container, bg=CARD)
page_controle = tk.Frame(container, bg=CARD)
page_statut = tk.Frame(container, bg=CARD)
page_3d = tk.Frame(container, bg=CARD)
page_export = tk.Frame(container, bg=CARD)

pages["CONNEXION"] = page_connexion
pages["PARAMÈTRES"] = page_parametres
pages["CONTRÔLE"] = page_controle
pages["STATUT"] = page_statut
pages["3D"] = page_3d
pages["EXPORT"] = page_export

for page in pages.values():
    page.grid(row=0, column=0, sticky="nsew")


# ============================================================
# FONCTION TITRE DES BLOCS
# ============================================================

def titre_page(parent, titre_text, description):
    tk.Label(
        parent,
        text=titre_text,
        font=("Segoe UI", 22, "bold"),
        fg=WHITE,
        bg=CARD
    ).pack(anchor="w", padx=35, pady=(30, 5))

    tk.Label(
        parent,
        text=description,
        font=("Segoe UI", 10),
        fg=GRAY,
        bg=CARD
    ).pack(anchor="w", padx=35, pady=(0, 25))


# ============================================================
# 1. CONNEXION
# ============================================================

titre_page(
    page_connexion,
    "CONNEXION",
    "Connexion à l'ESP32 du scanner"
)

connexion_zone = tk.Frame(page_connexion, bg=CARD)
connexion_zone.pack(padx=80, pady=20, fill="x")

# IP
tk.Label(
    connexion_zone,
    text="Adresse IP ESP32",
    font=("Segoe UI", 11, "bold"),
    fg=WHITE,
    bg=CARD
).grid(row=0, column=0, sticky="w", pady=10)

ip_entry = tk.Entry(
    connexion_zone,
    font=("Segoe UI", 12),
    bg=CARD2,
    fg=WHITE,
    insertbackground=WHITE,
    relief="flat",
    width=30
)
ip_entry.insert(0, "192.168.1.10")
ip_entry.grid(row=1, column=0, sticky="w", ipady=8)


# Port
tk.Label(
    connexion_zone,
    text="Port",
    font=("Segoe UI", 11, "bold"),
    fg=WHITE,
    bg=CARD
).grid(row=0, column=1, sticky="w", padx=50, pady=10)

port_entry = tk.Entry(
    connexion_zone,
    font=("Segoe UI", 12),
    bg=CARD2,
    fg=WHITE,
    insertbackground=WHITE,
    relief="flat",
    width=15
)
port_entry.insert(0, "8080")
port_entry.grid(row=1, column=1, sticky="w", padx=50, ipady=8)


# Statut connexion
connexion_status = tk.Label(
    connexion_zone,
    text="● Non connecté",
    font=("Segoe UI", 12, "bold"),
    fg=RED,
    bg=CARD
)
connexion_status.grid(row=3, column=0, sticky="w", pady=(35, 0))


def connecter():
    connexion_status.config(
        text="● Connecté",
        fg=GREEN
    )


bouton_connecter = tk.Button(
    connexion_zone,
    text="CONNECTER",
    command=connecter,
    font=("Segoe UI", 11, "bold"),
    fg=WHITE,
    bg=BLUE_DARK,
    activebackground=BLUE,
    activeforeground=WHITE,
    relief="flat",
    cursor="hand2",
    padx=30,
    pady=10
)
bouton_connecter.grid(row=3, column=1, padx=50, pady=(30, 0))


# ============================================================
# 2. PARAMETRES
# ============================================================

titre_page(
    page_parametres,
    "PARAMÈTRES",
    "Configuration de la précision et de la vitesse du scanner"
)

param_zone = tk.Frame(page_parametres, bg=CARD)
param_zone.pack(padx=80, pady=10, fill="x")


# Résolution theta
tk.Label(
    param_zone,
    text="Résolution θ",
    font=("Segoe UI", 11, "bold"),
    fg=WHITE,
    bg=CARD
).grid(row=0, column=0, sticky="w", pady=12)

theta_combo = ttk.Combobox(
    param_zone,
    values=["0.9°", "1.8°", "3.6°", "7.2°"],
    state="readonly",
    width=15
)
theta_combo.set("1.8°")
theta_combo.grid(row=1, column=0, sticky="w")


# Résolution phi
tk.Label(
    param_zone,
    text="Résolution φ",
    font=("Segoe UI", 11, "bold"),
    fg=WHITE,
    bg=CARD
).grid(row=0, column=1, sticky="w", padx=80, pady=12)

phi_combo = ttk.Combobox(
    param_zone,
    values=["1.8°", "3.6°", "7.2°", "14.4°"],
    state="readonly",
    width=15
)
phi_combo.set("3.6°")
phi_combo.grid(row=1, column=1, sticky="w", padx=80)


# Phi min
tk.Label(
    param_zone,
    text="φ minimum",
    font=("Segoe UI", 11, "bold"),
    fg=WHITE,
    bg=CARD
).grid(row=2, column=0, sticky="w", pady=(30, 12))

phi_min_entry = tk.Entry(
    param_zone,
    font=("Segoe UI", 11),
    bg=CARD2,
    fg=WHITE,
    insertbackground=WHITE,
    relief="flat",
    width=18
)
phi_min_entry.insert(0, "30°")
phi_min_entry.grid(row=3, column=0, sticky="w", ipady=7)


# Phi max
tk.Label(
    param_zone,
    text="φ maximum",
    font=("Segoe UI", 11, "bold"),
    fg=WHITE,
    bg=CARD
).grid(row=2, column=1, sticky="w", padx=80, pady=(30, 12))

phi_max_entry = tk.Entry(
    param_zone,
    font=("Segoe UI", 11),
    bg=CARD2,
    fg=WHITE,
    insertbackground=WHITE,
    relief="flat",
    width=18
)
phi_max_entry.insert(0, "150°")
phi_max_entry.grid(row=3, column=1, sticky="w", padx=80, ipady=7)


# Vitesse
tk.Label(
    param_zone,
    text="Vitesse moteur",
    font=("Segoe UI", 11, "bold"),
    fg=WHITE,
    bg=CARD
).grid(row=4, column=0, sticky="w", pady=(35, 10))

vitesse_label = tk.Label(
    param_zone,
    text="50 %",
    font=("Segoe UI", 11, "bold"),
    fg=BLUE,
    bg=CARD
)
vitesse_label.grid(row=4, column=1, sticky="w", padx=80)


def changer_vitesse(value):
    vitesse_label.config(text=f"{int(float(value))} %")


vitesse_slider = tk.Scale(
    param_zone,
    from_=10,
    to=100,
    orient="horizontal",
    command=changer_vitesse,
    bg=CARD,
    fg=WHITE,
    troughcolor=CARD2,
    highlightthickness=0,
    showvalue=False,
    length=350
)
vitesse_slider.set(50)
vitesse_slider.grid(row=5, column=0, columnspan=2, sticky="w")


# ============================================================
# 3. CONTROLE
# ============================================================

titre_page(
    page_controle,
    "CONTRÔLE",
    "Commandes du scanner et positionnement manuel"
)

controle_zone = tk.Frame(page_controle, bg=CARD)
controle_zone.pack(padx=70, pady=10)


def bouton_controle(parent, texte, couleur):
    return tk.Button(
        parent,
        text=texte,
        font=("Segoe UI", 11, "bold"),
        fg=WHITE,
        bg=couleur,
        activebackground=BLUE,
        activeforeground=WHITE,
        relief="flat",
        cursor="hand2",
        padx=25,
        pady=12
    )


bouton_lancer = bouton_controle(
    controle_zone,
    "▶ LANCER SCAN",
    GREEN
)
bouton_lancer.grid(row=0, column=0, padx=10, pady=10)

bouton_pause = bouton_controle(
    controle_zone,
    "PAUSE",
    ORANGE
)
bouton_pause.grid(row=0, column=1, padx=10, pady=10)

bouton_stop = bouton_controle(
    controle_zone,
    "STOP",
    RED
)
bouton_stop.grid(row=0, column=2, padx=10, pady=10)

bouton_reset = bouton_controle(
    controle_zone,
    "RESET POSITION",
    BLUE_DARK
)
bouton_reset.grid(row=0, column=3, padx=10, pady=10)


# Séparation
tk.Frame(
    page_controle,
    height=1,
    bg=CARD2
).pack(fill="x", padx=70, pady=30)


# Test manuel
tk.Label(
    page_controle,
    text="TEST MANUEL",
    font=("Segoe UI", 14, "bold"),
    fg=WHITE,
    bg=CARD
).pack(anchor="w", padx=70, pady=(0, 15))


manuel = tk.Frame(page_controle, bg=CARD)
manuel.pack(anchor="w", padx=70)


# Theta manuel
tk.Label(
    manuel,
    text="θ",
    font=("Segoe UI", 12, "bold"),
    fg=WHITE,
    bg=CARD
).grid(row=0, column=0, padx=10)

theta_manuel = tk.Entry(
    manuel,
    font=("Segoe UI", 11),
    bg=CARD2,
    fg=WHITE,
    insertbackground=WHITE,
    relief="flat",
    width=12
)
theta_manuel.insert(0, "90°")
theta_manuel.grid(row=0, column=1, padx=10, ipady=7)

tk.Button(
    manuel,
    text="GO",
    font=("Segoe UI", 10, "bold"),
    fg=WHITE,
    bg=BLUE_DARK,
    relief="flat",
    cursor="hand2",
    padx=20
).grid(row=0, column=2, padx=10)


# Phi manuel
tk.Label(
    manuel,
    text="φ",
    font=("Segoe UI", 12, "bold"),
    fg=WHITE,
    bg=CARD
).grid(row=1, column=0, padx=10, pady=20)

phi_manuel = tk.Entry(
    manuel,
    font=("Segoe UI", 11),
    bg=CARD2,
    fg=WHITE,
    insertbackground=WHITE,
    relief="flat",
    width=12
)
phi_manuel.insert(0, "45°")
phi_manuel.grid(row=1, column=1, padx=10, ipady=7)

tk.Button(
    manuel,
    text="GO",
    font=("Segoe UI", 10, "bold"),
    fg=WHITE,
    bg=BLUE_DARK,
    relief="flat",
    cursor="hand2",
    padx=20
).grid(row=1, column=2, padx=10)


# ============================================================
# 4. STATUT
# ============================================================

titre_page(
    page_statut,
    "STATUT",
    "État actuel du processus de scan"
)

statut_zone = tk.Frame(page_statut, bg=CARD)
statut_zone.pack(padx=100, pady=10, fill="x")


# Progression
tk.Label(
    statut_zone,
    text="Progression",
    font=("Segoe UI", 12, "bold"),
    fg=WHITE,
    bg=CARD
).grid(row=0, column=0, sticky="w")

progression_label = tk.Label(
    statut_zone,
    text="45 %",
    font=("Segoe UI", 12, "bold"),
    fg=BLUE,
    bg=CARD
)
progression_label.grid(row=0, column=1, sticky="e")

progress_bar = ttk.Progressbar(
    statut_zone,
    orient="horizontal",
    length=700,
    mode="determinate"
)
progress_bar["value"] = 45
progress_bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=10)


# Informations
infos = [
    ("θ actuel", "162.0°"),
    ("φ actuel", "72.0°"),
    ("Distance", "248 mm"),
    ("Points collectés", "4500"),
    ("Temps écoulé", "02:34"),
    ("Temps restant", "03:08")
]

for i, (nom, valeur) in enumerate(infos):
    row = 2 + i // 2
    col = (i % 2) * 2

    tk.Label(
        statut_zone,
        text=nom,
        font=("Segoe UI", 11),
        fg=GRAY,
        bg=CARD
    ).grid(row=row, column=col, sticky="w", pady=18)

    tk.Label(
        statut_zone,
        text=valeur,
        font=("Segoe UI", 13, "bold"),
        fg=WHITE,
        bg=CARD
    ).grid(row=row, column=col + 1, sticky="e", padx=(30, 100))


# ============================================================
# 5. VISUALISATION 3D
# ============================================================

titre_page(
    page_3d,
    "VISUALISATION 3D",
    "Nuage de points généré par le scanner"
)

visualisation_zone = tk.Frame(page_3d, bg=CARD)
visualisation_zone.pack(fill="both", expand=True, padx=35, pady=(0, 20))

canvas = tk.Canvas(
    visualisation_zone,
    bg="#080C11",
    highlightthickness=0
)
canvas.pack(fill="both", expand=True, padx=15, pady=15)


def generer_points():
    canvas.delete("all")

    largeur = canvas.winfo_width()
    hauteur = canvas.winfo_height()

    if largeur < 100:
        largeur = 700

    if hauteur < 100:
        hauteur = 400

    centre_x = largeur // 2
    centre_y = hauteur // 2

    for _ in range(500):

        x = random.gauss(0, largeur * 0.18)
        y = random.gauss(0, hauteur * 0.28)

        px = centre_x + x
        py = centre_y + y

        taille = random.choice([2, 2, 3, 4])

        canvas.create_oval(
            px,
            py,
            px + taille,
            py + taille,
            fill=BLUE,
            outline=""
        )


canvas.bind("<Configure>", lambda event: generer_points())


# Boutons visualisation
vis_buttons = tk.Frame(page_3d, bg=CARD)
vis_buttons.pack(pady=(0, 15))


for texte in [
    "⟳ Rotation",
    "Zoom",
    "Vue X",
    "Vue Y",
    "Vue Z"
]:
    tk.Button(
        vis_buttons,
        text=texte,
        font=("Segoe UI", 9, "bold"),
        fg=WHITE,
        bg=CARD2,
        activebackground=BLUE_DARK,
        activeforeground=WHITE,
        relief="flat",
        cursor="hand2",
        padx=18,
        pady=7
    ).pack(side="left", padx=5)


# ============================================================
# 6. EXPORT
# ============================================================

titre_page(
    page_export,
    "EXPORT",
    "Exporter les données du scan"
)

export_zone = tk.Frame(page_export, bg=CARD)
export_zone.pack(padx=100, pady=20, anchor="w")


# Format
tk.Label(
    export_zone,
    text="Format",
    font=("Segoe UI", 11, "bold"),
    fg=WHITE,
    bg=CARD
).grid(row=0, column=0, sticky="w", pady=15)

format_combo = ttk.Combobox(
    export_zone,
    values=[".PLY", ".OBJ", ".STL", ".CSV"],
    state="readonly",
    width=20
)
format_combo.set(".PLY")
format_combo.grid(row=1, column=0, sticky="w")


# Options
tk.Label(
    export_zone,
    text="Options",
    font=("Segoe UI", 12, "bold"),
    fg=WHITE,
    bg=CARD
).grid(row=2, column=0, sticky="w", pady=(35, 10))

nettoyer_var = tk.BooleanVar(value=True)
normales_var = tk.BooleanVar(value=True)
mesh_var = tk.BooleanVar(value=False)

tk.Checkbutton(
    export_zone,
    text="Nettoyer les points",
    variable=nettoyer_var,
    font=("Segoe UI", 10),
    fg=WHITE,
    bg=CARD,
    selectcolor=CARD2,
    activebackground=CARD,
    activeforeground=WHITE
).grid(row=3, column=0, sticky="w", pady=5)

tk.Checkbutton(
    export_zone,
    text="Calculer les normales",
    variable=normales_var,
    font=("Segoe UI", 10),
    fg=WHITE,
    bg=CARD,
    selectcolor=CARD2,
    activebackground=CARD,
    activeforeground=WHITE
).grid(row=4, column=0, sticky="w", pady=5)

tk.Checkbutton(
    export_zone,
    text="Reconstruire le mesh",
    variable=mesh_var,
    font=("Segoe UI", 10),
    fg=WHITE,
    bg=CARD,
    selectcolor=CARD2,
    activebackground=CARD,
    activeforeground=WHITE
).grid(row=5, column=0, sticky="w", pady=5)


def exporter():
    messagebox.showinfo(
        "Export",
        f"Export en {format_combo.get()}\n\n"
        f"Nettoyage : {'Oui' if nettoyer_var.get() else 'Non'}\n"
        f"Normales : {'Oui' if normales_var.get() else 'Non'}\n"
        f"Mesh : {'Oui' if mesh_var.get() else 'Non'}"
    )


tk.Button(
    export_zone,
    text="💾 EXPORTER",
    command=exporter,
    font=("Segoe UI", 11, "bold"),
    fg=WHITE,
    bg=BLUE_DARK,
    activebackground=BLUE,
    activeforeground=WHITE,
    relief="flat",
    cursor="hand2",
    padx=35,
    pady=12
).grid(row=7, column=0, sticky="w", pady=30)


# ============================================================
# NAVIGATION EN BAS
# ============================================================

navigation = tk.Frame(
    fenetre,
    bg=BG
)
navigation.grid(
    row=2,
    column=0,
    sticky="ew",
    padx=30,
    pady=(5, 5)
)

navigation.grid_columnconfigure(
    (0, 1, 2, 3, 4, 5),
    weight=1
)


boutons_navigation = {}


def afficher_page(nom):
    page = pages[nom]
    page.tkraise()

    for nom_bouton, bouton in boutons_navigation.items():

        if nom_bouton == nom:
            bouton.config(
                bg=BLUE,
                fg=WHITE
            )
        else:
            bouton.config(
                bg=CARD2,
                fg=GRAY
            )


noms_navigation = [
    ("CONNEXION", "CONNEXION"),
    ("PARAMÈTRES", "PARAMÈTRES"),
    ("CONTRÔLE", "CONTRÔLE"),
    ("STATUT", "STATUT"),
    ("3D", "VISUALISATION 3D"),
    ("EXPORT", "EXPORT")
]


for i, (nom, texte) in enumerate(noms_navigation):

    bouton = tk.Button(
        navigation,
        text=texte,
        command=lambda n=nom: afficher_page(n),
        font=("Segoe UI", 9, "bold"),
        bg=CARD2,
        fg=GRAY,
        activebackground=BLUE_DARK,
        activeforeground=WHITE,
        relief="flat",
        cursor="hand2",
        padx=8,
        pady=12
    )

    bouton.grid(
        row=0,
        column=i,
        sticky="ew",
        padx=3
    )

    boutons_navigation[nom] = bouton


# ============================================================
# FOOTER / LOGO
# ============================================================

footer = tk.Frame(
    fenetre,
    bg=BG
)
footer.grid(
    row=3,
    column=0,
    sticky="ew",
    pady=(3, 8)
)

footer.grid_columnconfigure(0, weight=1)

try:
    logo_original = tk.PhotoImage(file="2.png")

    # Réduction du logo
    logo = logo_original.subsample(6, 6)

    logo_label = tk.Label(
        footer,
        image=logo,
        bg=BG
    )
    logo_label.grid(row=0, column=0)

except Exception:
    tk.Label(
        footer,
        text="CPU ISIMM",
        font=("Segoe UI", 9, "bold"),
        fg=GRAY,
        bg=BG
    ).grid(row=0, column=0)


# ============================================================
# PAGE PAR DEFAUT
# ============================================================

afficher_page("CONNEXION")


# ============================================================
# LANCEMENT
# ============================================================

fenetre.mainloop()