"""
╔══════════════════════════════════════════════╗
║     NUAGE DE POINTS — SCANNER 3D             ║
║     Entrée  : données (θ, φ, d) du ESP32     ║
║     Sortie  : fichier .ply (nuage 3D)        ║
╚══════════════════════════════════════════════╝

Installation des dépendances :
    pip install numpy open3d

Comment utiliser :
    1. Mode fichier CSV  → python nuage_points.py --csv scan.csv
    2. Mode WiFi direct  → python nuage_points.py --wifi 192.168.1.10
    3. Mode simulation   → python nuage_points.py --demo
"""

import numpy as np
import open3d as o3d
import socket
import argparse
import csv
import time
import os


# ════════════════════════════════════════════
#   1. LA FORMULE PRINCIPALE
#   Conversion coordonnées sphériques → cartésiennes
# ════════════════════════════════════════════

def spherique_vers_cartesien(theta_deg, phi_deg, distance_mm):
    """
    Convertit une mesure du scanner en point 3D.

    Entrée :
        theta_deg    → angle horizontal du plateau  (0° à 360°)
        phi_deg      → angle vertical du bras       (0° à 180°)
        distance_mm  → distance mesurée par VL53L1X (en mm)

    Sortie :
        (x, y, z)   → coordonnées 3D en mètres

    La formule :
        x = d × sin(φ) × cos(θ)
        y = d × cos(φ)
        z = d × sin(φ) × sin(θ)
    """

    # étape 1 : convertir degrés → radians
    # (les fonctions sin/cos de numpy utilisent des radians)
    theta = np.radians(theta_deg)
    phi   = np.radians(phi_deg)

    # étape 2 : convertir mm → mètres
    d = distance_mm / 1000.0

    # étape 3 : appliquer la formule sphérique
    x = d * np.sin(phi) * np.cos(theta)
    y = d * np.cos(phi)
    z = d * np.sin(phi) * np.sin(theta)

    return x, y, z


# ════════════════════════════════════════════
#   2. FILTRAGE DES MESURES ABERRANTES
# ════════════════════════════════════════════

def est_mesure_valide(distance_mm, dist_min=50, dist_max=3500):
    """
    Vérifie si une mesure est utilisable.

    Pourquoi filtrer ?
        Le VL53L1X retourne parfois :
        - 0 mm        → capteur n'a rien vu
        - 8191 mm     → erreur interne (valeur max du capteur)
        - > 4000 mm   → hors portée

    dist_min : distance minimale à considérer (50mm = 5cm)
    dist_max : distance maximale à considérer (3500mm = 3.5m)
    """
    return dist_min <= distance_mm <= dist_max


# ════════════════════════════════════════════
#   3. LECTURE DEPUIS UN FICHIER CSV
# ════════════════════════════════════════════

def lire_depuis_csv(chemin_fichier):
    """
    Lit les données depuis un fichier CSV sauvegardé.

    Format du fichier :
        theta,phi,distance
        0.0,30.0,248
        1.8,30.0,251
        3.6,30.0,247
        ...
    """
    points = []
    lignes_lues    = 0
    lignes_filtrees = 0

    print(f"\n📂 Lecture du fichier : {chemin_fichier}")

    if not os.path.exists(chemin_fichier):
        print(f"❌ Fichier introuvable : {chemin_fichier}")
        return np.array([])

    with open(chemin_fichier, 'r') as f:
        reader = csv.reader(f)

        # ignorer l'en-tête si présent
        premiere_ligne = next(reader)
        if not premiere_ligne[0].replace('.','').replace('-','').isdigit():
            print(f"   En-tête ignorée : {premiere_ligne}")
        else:
            # c'est une donnée, pas un en-tête → la traiter
            try:
                theta, phi, dist = float(premiere_ligne[0]), \
                                   float(premiere_ligne[1]), \
                                   float(premiere_ligne[2])
                if est_mesure_valide(dist):
                    x, y, z = spherique_vers_cartesien(theta, phi, dist)
                    points.append([x, y, z])
            except:
                pass

        # lire le reste du fichier
        for ligne in reader:
            lignes_lues += 1
            try:
                theta = float(ligne[0])
                phi   = float(ligne[1])
                dist  = float(ligne[2])

                if est_mesure_valide(dist):
                    x, y, z = spherique_vers_cartesien(theta, phi, dist)
                    points.append([x, y, z])
                else:
                    lignes_filtrees += 1

            except (ValueError, IndexError):
                lignes_filtrees += 1
                continue

    print(f"   ✓ {lignes_lues} mesures lues")
    print(f"   ✗ {lignes_filtrees} mesures filtrées (hors portée ou erreur)")
    print(f"   → {len(points)} points valides")

    return np.array(points)


# ════════════════════════════════════════════
#   4. LECTURE DEPUIS WIFI (ESP32 en direct)
# ════════════════════════════════════════════

def lire_depuis_wifi(ip_esp32, port=8080):
    """
    Se connecte à l'ESP32 et reçoit les données en temps réel.
    Lance le scan automatiquement avec les paramètres par défaut.
    """
    points = []
    print(f"\n📡 Connexion à l'ESP32 : {ip_esp32}:{port}")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((ip_esp32, port))
        print("   ✓ Connecté !")

        # envoyer la commande de scan
        # format : SCAN,res_theta,res_phi,phi_min,phi_max
        commande = "SCAN,1.8,3.6,30,150\n"
        sock.sendall(commande.encode())
        print(f"   → Commande envoyée : {commande.strip()}")
        print("   Réception des données...\n")

        buffer  = ""
        t_debut = time.time()
        nb_pts  = 0

        while True:
            try:
                data = sock.recv(1024).decode('utf-8')
                if not data:
                    break

                buffer += data

                # traiter chaque ligne complète
                while '\n' in buffer:
                    ligne, buffer = buffer.split('\n', 1)
                    ligne = ligne.strip()

                    if ligne == "FIN":
                        print(f"\n   ✓ Scan terminé ! {nb_pts} points reçus")
                        sock.close()
                        return np.array(points)

                    if ligne in ("BIENVENUE", "SCAN_DEBUT", ""):
                        continue

                    # parser la ligne "theta,phi,distance"
                    try:
                        parts = ligne.split(',')
                        theta = float(parts[0])
                        phi   = float(parts[1])
                        dist  = float(parts[2])

                        if est_mesure_valide(dist):
                            x, y, z = spherique_vers_cartesien(theta, phi, dist)
                            points.append([x, y, z])
                            nb_pts += 1

                            # afficher progression
                            if nb_pts % 100 == 0:
                                elapsed = int(time.time() - t_debut)
                                print(f"   Points reçus : {nb_pts} "
                                      f"| θ={theta:.1f}° φ={phi:.1f}° "
                                      f"d={dist:.0f}mm "
                                      f"| {elapsed}s", end='\r')

                    except (ValueError, IndexError):
                        continue

            except socket.timeout:
                print("\n   ⚠ Timeout — ESP32 ne répond plus")
                break

    except ConnectionRefusedError:
        print(f"   ❌ Connexion refusée — ESP32 allumé et connecté au WiFi ?")
    except Exception as e:
        print(f"   ❌ Erreur : {e}")
    finally:
        sock.close()

    return np.array(points)


# ════════════════════════════════════════════
#   5. MODE DÉMONSTRATION (sans matériel)
# ════════════════════════════════════════════

def generer_demo():
    """
    Génère un nuage de points simulé (sphère + bruit)
    pour tester le pipeline sans ESP32.
    """
    print("\n🔵 Mode démonstration — génération d'un objet simulé")
    points = []

    # paramètres identiques à un vrai scan
    res_theta = 1.8
    res_phi   = 3.6
    phi_min   = 30.0
    phi_max   = 150.0

    for phi_d in np.arange(phi_min, phi_max, res_phi):
        for theta_d in np.arange(0, 360, res_theta):

            # simule un objet irrégulier
            # (sphère de base + déformations pour rendre réaliste)
            rayon_base = 200  # mm
            deformation = (
                20 * np.sin(np.radians(theta_d * 3)) +   # ondulation horizontale
                15 * np.sin(np.radians(phi_d * 2))   +   # ondulation verticale
                np.random.uniform(-5, 5)                   # bruit capteur
            )
            dist = rayon_base + deformation

            x, y, z = spherique_vers_cartesien(theta_d, phi_d, dist)
            points.append([x, y, z])

    print(f"   ✓ {len(points)} points générés")
    return np.array(points)


# ════════════════════════════════════════════
#   6. NETTOYAGE DU NUAGE DE POINTS
# ════════════════════════════════════════════

def nettoyer_nuage(pcd):
    """
    Supprime les points aberrants (bruit).

    Comment ça marche :
        Pour chaque point, on regarde ses 20 voisins les plus proches.
        Si ce point est trop loin de la moyenne de ses voisins
        (plus de 2 fois l'écart-type), on le supprime.

        C'est comme dire : "si t'es trop loin de tout le monde,
        tu es probablement une erreur de mesure"
    """
    print("\n🔧 Nettoyage du nuage de points...")
    nb_avant = len(pcd.points)

    # suppression statistique des outliers
    pcd_propre, indices = pcd.remove_statistical_outlier(
        nb_neighbors = 20,    # regarder les 20 voisins
        std_ratio    = 2.0    # seuil : 2 fois l'écart-type
    )

    nb_apres   = len(pcd_propre.points)
    nb_enleves = nb_avant - nb_apres
    print(f"   Avant   : {nb_avant} points")
    print(f"   Enlevés : {nb_enleves} points aberrants")
    print(f"   Après   : {nb_apres} points")

    return pcd_propre


# ════════════════════════════════════════════
#   7. CALCUL DES NORMALES
# ════════════════════════════════════════════

def calculer_normales(pcd):
    """
    Calcule la direction perpendiculaire à la surface en chaque point.
    Nécessaire pour la reconstruction de surface (étape suivante).

    Imagine chaque point avec une petite flèche qui pointe
    vers l'extérieur de l'objet → c'est la normale.
    """
    print("\n📐 Calcul des normales...")

    pcd.estimate_normals(
        search_param = o3d.geometry.KDTreeSearchParamHybrid(
            radius = 0.05,    # chercher dans un rayon de 5cm
            max_nn = 30       # maximum 30 voisins
        )
    )

    # orienter toutes les normales vers l'extérieur
    pcd.orient_normals_consistent_tangent_plane(100)

    print("   ✓ Normales calculées")
    return pcd


# ════════════════════════════════════════════
#   8. EXPORT DU NUAGE
# ════════════════════════════════════════════

def exporter(pcd, chemin, format="ply"):
    """
    Sauvegarde le nuage de points dans un fichier.

    Formats supportés :
        .ply → le plus universel (Blender, MeshLab, CloudCompare)
        .xyz → texte simple (x y z par ligne)
        .pcd → format Point Cloud Data
    """
    print(f"\n💾 Export en cours → {chemin}")
    o3d.io.write_point_cloud(chemin, pcd)
    taille = os.path.getsize(chemin) / 1024
    print(f"   ✓ Sauvegardé : {chemin} ({taille:.1f} KB)")


# ════════════════════════════════════════════
#   9. VISUALISATION 3D
# ════════════════════════════════════════════

def visualiser(pcd, titre="Nuage de points — Scanner 3D"):
    """
    Affiche le nuage de points dans une fenêtre 3D interactive.

    Contrôles :
        Clic gauche + drag  → rotation
        Clic droit + drag   → déplacement
        Molette             → zoom
        Q ou Echap          → fermer
    """
    print("\n👁 Ouverture de la visualisation 3D...")
    print("   Contrôles : clic gauche=rotation | molette=zoom | Q=quitter")

    # colorier les points selon leur hauteur (axe Y)
    points = np.asarray(pcd.points)
    if len(points) > 0:
        y_vals  = points[:, 1]
        y_min, y_max = y_vals.min(), y_vals.max()

        # normaliser entre 0 et 1
        y_norm = (y_vals - y_min) / (y_max - y_min + 1e-9)

        # palette de couleurs : bleu (bas) → rouge (haut)
        couleurs = np.zeros((len(points), 3))
        couleurs[:, 0] = y_norm          # rouge augmente avec hauteur
        couleurs[:, 2] = 1.0 - y_norm   # bleu diminue avec hauteur
        pcd.colors = o3d.utility.Vector3dVector(couleurs)

    o3d.visualization.draw_geometries(
        [pcd],
        window_name = titre,
        width       = 900,
        height      = 700,
        point_show_normal = False
    )


# ════════════════════════════════════════════
#   10. PIPELINE COMPLET
# ════════════════════════════════════════════

def pipeline_complet(points_array, nom_fichier="scan"):
    """
    Prend un tableau numpy de points (x,y,z)
    et fait tout : nettoyage → normales → export → visualisation
    """

    if len(points_array) == 0:
        print("❌ Aucun point à traiter !")
        return None

    print(f"\n{'='*50}")
    print(f"  PIPELINE NUAGE DE POINTS")
    print(f"  {len(points_array)} points en entrée")
    print(f"{'='*50}")

    # créer l'objet PointCloud Open3D
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points_array)

    # nettoyage
    pcd = nettoyer_nuage(pcd)

    # normales
    pcd = calculer_normales(pcd)

    # export
    chemin_ply = f"{nom_fichier}.ply"
    exporter(pcd, chemin_ply)

    print(f"\n{'='*50}")
    print(f"  ✅ TERMINÉ")
    print(f"  Fichier : {chemin_ply}")
    print(f"  Points  : {len(pcd.points)}")
    print(f"{'='*50}\n")

    # visualisation
    visualiser(pcd)

    return pcd


# ════════════════════════════════════════════
#   11. POINT D'ENTRÉE
# ════════════════════════════════════════════

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Scanner 3D ESP32 — Générateur de nuage de points"
    )
    parser.add_argument(
        '--csv',
        type=str,
        help="Chemin vers un fichier CSV (ex: --csv scan.csv)"
    )
    parser.add_argument(
        '--wifi',
        type=str,
        help="IP de l'ESP32 pour scan direct (ex: --wifi 192.168.1.10)"
    )
    parser.add_argument(
        '--demo',
        action='store_true',
        help="Mode démonstration sans matériel"
    )
    parser.add_argument(
        '--output',
        type=str,
        default="mon_scan",
        help="Nom du fichier de sortie sans extension (défaut: mon_scan)"
    )

    args = parser.parse_args()

    # ── choisir la source de données ──
    if args.demo:
        points = generer_demo()

    elif args.csv:
        points = lire_depuis_csv(args.csv)

    elif args.wifi:
        points = lire_depuis_wifi(args.wifi)

    else:
        # aucun argument → mode démo par défaut
        print("Aucune source spécifiée → mode démonstration")
        print("Usage :")
        print("  python nuage_points.py --demo")
        print("  python nuage_points.py --csv scan.csv")
        print("  python nuage_points.py --wifi 192.168.1.10")
        print()
        points = generer_demo()

    # ── lancer le pipeline complet ──
    pipeline_complet(points, args.output)