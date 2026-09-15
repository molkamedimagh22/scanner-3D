"""
╔══════════════════════════════════════════════╗
║   APP WEB SCANNER 3D — SERVEUR FLASK        ║
║   Lance : py -3.11 app.py                   ║
║   Ouvre : http://localhost:5000              ║
╚══════════════════════════════════════════════╝
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import threading
import socket
import numpy as np
import json
import os
import time


# ════════════════════════════════════════════
#   INITIALISATION
# ════════════════════════════════════════════

app     = Flask(__name__)
app.config['SECRET_KEY'] = 'scanner3d_secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# dossier pour sauvegarder les scans
os.makedirs('scans', exist_ok=True)

# état global du scanner
etat = {
    "connecte"    : False,
    "scan_actif"  : False,
    "ip_esp32"    : "192.168.1.10",
    "port_esp32"  : 8080,
    "points"      : [],       # liste de (x, y, z)
    "nb_points"   : 0,
    "progression" : 0,
    "theta"       : 0.0,
    "phi"         : 0.0,
    "distance"    : 0,
}

# connexion TCP vers l'ESP32
connexion_esp32 = None
thread_reception = None


# ════════════════════════════════════════════
#   ROUTES — PAGES WEB
# ════════════════════════════════════════════

@app.route('/')
def index():
    """Page principale."""
    return render_template('index.html')

@app.route('/api/etat')
def get_etat():
    """Retourne l'état actuel du scanner."""
    return jsonify({
        "connecte"    : etat["connecte"],
        "scan_actif"  : etat["scan_actif"],
        "nb_points"   : etat["nb_points"],
        "progression" : etat["progression"],
    })

@app.route('/api/scans')
def liste_scans():
    """Liste les fichiers .ply sauvegardés."""
    fichiers = [f for f in os.listdir('scans') if f.endswith('.ply')]
    return jsonify(fichiers)


# ════════════════════════════════════════════
#   WEBSOCKET — ÉVÉNEMENTS NAVIGATEUR → FLASK
# ════════════════════════════════════════════

@socketio.on('connecter_esp32')
def handle_connexion(data):
    """
    Le navigateur demande de se connecter à l'ESP32.
    data = { ip: "192.168.1.10", port: 8080 }
    """
    global connexion_esp32, thread_reception

    ip   = data.get('ip',   '192.168.1.10')
    port = data.get('port', 8080)

    etat['ip_esp32']   = ip
    etat['port_esp32'] = port

    emit('log', {'msg': f'Connexion à {ip}:{port}...'})

    try:
        connexion_esp32 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connexion_esp32.settimeout(5)
        connexion_esp32.connect((ip, port))
        etat['connecte'] = True

        # démarrer le thread de réception
        thread_reception = threading.Thread(
            target=_recevoir_donnees_esp32,
            daemon=True
        )
        thread_reception.start()

        emit('connexion_ok', {'ip': ip, 'port': port})
        emit('log', {'msg': f'✓ Connecté à ESP32 ({ip})'})

    except Exception as e:
        etat['connecte'] = False
        emit('connexion_erreur', {'erreur': str(e)})
        emit('log', {'msg': f'✗ Erreur connexion : {e}'})


@socketio.on('deconnecter_esp32')
def handle_deconnexion():
    """Déconnecte l'ESP32."""
    global connexion_esp32
    if connexion_esp32:
        connexion_esp32.close()
        connexion_esp32 = None
    etat['connecte']   = False
    etat['scan_actif'] = False
    emit('deconnexion_ok')
    emit('log', {'msg': 'Déconnecté de l\'ESP32'})


@socketio.on('lancer_scan')
def handle_lancer_scan(data):
    """
    Lance un scan avec les paramètres donnés.
    data = { res_theta, res_phi, phi_min, phi_max }
    """
    if not etat['connecte']:
        emit('log', {'msg': '✗ Non connecté à l\'ESP32'})
        return

    # réinitialiser les points
    etat['points']      = []
    etat['nb_points']   = 0
    etat['progression'] = 0
    etat['scan_actif']  = True

    # construire la commande
    res_theta = data.get('res_theta', 1.8)
    res_phi   = data.get('res_phi',   3.6)
    phi_min   = data.get('phi_min',   30)
    phi_max   = data.get('phi_max',   150)

    commande = f"SCAN,{res_theta},{res_phi},{phi_min},{phi_max}\n"
    _envoyer_esp32(commande)

    emit('scan_demarre')
    emit('log', {'msg': f'▶ Scan lancé (θ={res_theta}° φ={res_phi}°)'})


@socketio.on('stopper_scan')
def handle_stopper_scan():
    """Arrête le scan en cours."""
    _envoyer_esp32("STOP\n")
    etat['scan_actif'] = False
    emit('scan_arrete')
    emit('log', {'msg': '⏹ Scan arrêté'})


@socketio.on('reset_position')
def handle_reset():
    """Remet les moteurs à 0°."""
    _envoyer_esp32("RESET\n")
    emit('log', {'msg': '↺ Reset position'})


@socketio.on('bouger_moteur')
def handle_bouger_moteur(data):
    """
    Bouge un moteur manuellement.
    data = { moteur: 'theta', angle: 90 }
    """
    moteur = data.get('moteur', 'theta').upper()
    angle  = data.get('angle', 0)
    _envoyer_esp32(f"BOUGE_{moteur},{angle}\n")
    emit('log', {'msg': f'→ Moteur {moteur} → {angle}°'})


@socketio.on('sauvegarder_scan')
def handle_sauvegarder(data):
    """Sauvegarde le scan actuel en .ply."""
    nom = data.get('nom', f'scan_{int(time.time())}')
    chemin = f"scans/{nom}.ply"
    _exporter_ply(chemin)
    emit('scan_sauvegarde', {'fichier': f'{nom}.ply'})
    emit('log', {'msg': f'💾 Sauvegardé : {nom}.ply'})


@socketio.on('simuler')
def handle_simuler(data):
    """Lance une simulation sans ESP32."""
    etat['points']      = []
    etat['nb_points']   = 0
    etat['progression'] = 0
    etat['scan_actif']  = True

    res_theta = data.get('res_theta', 1.8)
    res_phi   = data.get('res_phi',   3.6)
    phi_min   = data.get('phi_min',   30)
    phi_max   = data.get('phi_max',   150)

    thread_sim = threading.Thread(
        target=_simulation,
        args=(res_theta, res_phi, phi_min, phi_max),
        daemon=True
    )
    thread_sim.start()
    emit('scan_demarre')
    emit('log', {'msg': '🔵 Simulation démarrée'})


# ════════════════════════════════════════════
#   FONCTIONS INTERNES
# ════════════════════════════════════════════

def _envoyer_esp32(commande):
    """Envoie une commande à l'ESP32 via TCP."""
    global connexion_esp32
    if connexion_esp32 and etat['connecte']:
        try:
            connexion_esp32.sendall(commande.encode())
        except Exception as e:
            print(f"Erreur envoi ESP32 : {e}")


def _recevoir_donnees_esp32():
    """
    Thread qui reçoit les données de l'ESP32 en continu.
    Format reçu : "theta,phi,distance\n"
    """
    global connexion_esp32
    buffer = ""

    while etat['connecte'] and connexion_esp32:
        try:
            data = connexion_esp32.recv(1024).decode('utf-8')
            if not data:
                break

            buffer += data
            while '\n' in buffer:
                ligne, buffer = buffer.split('\n', 1)
                ligne = ligne.strip()
                _traiter_ligne_esp32(ligne)

        except socket.timeout:
            continue
        except Exception as e:
            print(f"Erreur réception : {e}")
            break

    etat['connecte']   = False
    etat['scan_actif'] = False
    socketio.emit('deconnexion_ok')


def _traiter_ligne_esp32(ligne):
    """
    Traite une ligne reçue de l'ESP32.
    Convertit (theta, phi, distance) en (x, y, z)
    et l'envoie au navigateur via WebSocket.
    """
    if not ligne or ligne in ("BIENVENUE", "SCAN_DEBUT", "RESET_OK"):
        return

    if ligne == "FIN":
        etat['scan_actif']  = False
        etat['progression'] = 100
        socketio.emit('scan_termine', {'nb_points': etat['nb_points']})
        socketio.emit('log', {'msg': f'✓ Scan terminé — {etat["nb_points"]} points'})
        return

    if ligne == "SCAN_ARRETE":
        etat['scan_actif'] = False
        socketio.emit('scan_arrete')
        return

    # parser "theta,phi,distance"
    try:
        parts    = ligne.split(',')
        theta_d  = float(parts[0])
        phi_d    = float(parts[1])
        dist_mm  = float(parts[2])

        # filtrer les mesures hors portée
        if not (50 <= dist_mm <= 3500):
            return

        # conversion sphérique → cartésien
        theta = np.radians(theta_d)
        phi   = np.radians(phi_d)
        d     = dist_mm / 1000.0

        x = d * np.sin(phi) * np.cos(theta)
        y = d * np.cos(phi)
        z = d * np.sin(phi) * np.sin(theta)

        # mettre à jour l'état
        etat['points'].append([x, y, z])
        etat['nb_points']  += 1
        etat['theta']       = theta_d
        etat['phi']         = phi_d
        etat['distance']    = dist_mm

        # envoyer le point au navigateur
        # (envoyer par lot de 10 pour ne pas surcharger)
        if etat['nb_points'] % 10 == 0:
            socketio.emit('nouveaux_points', {
                'points'     : etat['points'][-10:],
                'nb_total'   : etat['nb_points'],
                'theta'      : theta_d,
                'phi'        : phi_d,
                'distance'   : dist_mm,
            })

    except (ValueError, IndexError):
        pass


def _simulation(res_theta, res_phi, phi_min, phi_max):
    """Simule un scan sans ESP32 pour tester l'interface."""
    thetas = np.arange(0,       360,     res_theta)
    phis   = np.arange(phi_min, phi_max, res_phi)
    total  = len(thetas) * len(phis)
    compte = 0

    for phi_d in phis:
        if not etat['scan_actif']:
            break
        for theta_d in thetas:
            if not etat['scan_actif']:
                break

            # objet simulé
            dist = 200 + 30 * np.sin(np.radians(theta_d * 3)) + \
                   np.random.uniform(-5, 5)

            # conversion
            theta = np.radians(theta_d)
            phi   = np.radians(phi_d)
            d     = dist / 1000.0
            x = d * np.sin(phi) * np.cos(theta)
            y = d * np.cos(phi)
            z = d * np.sin(phi) * np.sin(theta)

            etat['points'].append([x, y, z])
            etat['nb_points'] += 1
            compte += 1
            etat['progression'] = int(compte / total * 100)

            # envoyer par lot de 20
            if etat['nb_points'] % 20 == 0:
                socketio.emit('nouveaux_points', {
                    'points'   : etat['points'][-20:],
                    'nb_total' : etat['nb_points'],
                    'theta'    : theta_d,
                    'phi'      : phi_d,
                    'distance' : dist,
                    'prog'     : etat['progression'],
                })

            time.sleep(0.003)

    etat['scan_actif']  = False
    etat['progression'] = 100
    socketio.emit('scan_termine', {'nb_points': etat['nb_points']})
    socketio.emit('log', {'msg': f'✓ Simulation terminée — {etat["nb_points"]} points'})


def _exporter_ply(chemin):
    """Exporte le nuage de points en fichier .ply."""
    points = etat['points']
    if not points:
        return
    with open(chemin, 'w') as f:
        f.write("ply\nformat ascii 1.0\n")
        f.write(f"element vertex {len(points)}\n")
        f.write("property float x\nproperty float y\nproperty float z\n")
        f.write("end_header\n")
        for p in points:
            f.write(f"{p[0]:.6f} {p[1]:.6f} {p[2]:.6f}\n")


# ════════════════════════════════════════════
#   LANCEMENT
# ════════════════════════════════════════════

if __name__ == '__main__':
    print("="*50)
    print("  SCANNER 3D — SERVEUR WEB")
    print("  Ouvre : http://localhost:5000")
    print("="*50)
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
    