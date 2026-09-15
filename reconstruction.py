"""
╔══════════════════════════════════════════════╗
║   RECONSTRUCTION DE SURFACE 3D              ║
║   Entrée  : fichier .ply (nuage de points)  ║
║   Sortie  : fichier .stl (mesh imprimable)  ║
╚══════════════════════════════════════════════╝

Comment utiliser :
    python reconstruction.py --input mon_scan.ply
    python reconstruction.py --input mon_scan.ply --output objet_final
    python reconstruction.py --demo
"""

import open3d as o3d
import numpy as np
import argparse
import os


# ════════════════════════════════════════════
#   COMPRENDRE LA RECONSTRUCTION
#
#   NUAGE DE POINTS        MESH 3D
#   · · · · ·              ╱╲╱╲╱╲
#   · · · · ·      →      ╱  ╲  ╲
#   · · · · ·              ╲╱╲╱╲╱
#
#   Des points épars       Des triangles connectés
#   Pas de surface         Surface continue
#   Pas imprimable         Imprimable en 3D !
#
# ════════════════════════════════════════════


# ════════════════════════════════════════════
#   1. CHARGER LE NUAGE DE POINTS
# ════════════════════════════════════════════

def charger_nuage(chemin_ply):
    """
    Charge un fichier .ply et retourne le nuage de points.

    Un fichier .ply contient :
        - les coordonnées (x, y, z) de chaque point
        - (optionnel) les couleurs RGB
        - (optionnel) les normales
    """
    print(f"\n📂 Chargement : {chemin_ply}")

    if not os.path.exists(chemin_ply):
        print(f"❌ Fichier introuvable : {chemin_ply}")
        return None

    pcd = o3d.io.read_point_cloud(chemin_ply)
    print(f"   ✓ {len(pcd.points)} points chargés")
    return pcd


# ════════════════════════════════════════════
#   2. NETTOYER LE NUAGE
# ════════════════════════════════════════════

def nettoyer(pcd):
    """
    Supprime les points aberrants avant la reconstruction.

    Pourquoi nettoyer ?
    Si on laisse des points aberrants (bruit du capteur),
    la reconstruction va créer des "bosses" ou des "trous"
    à ces endroits → objet déformé.

    Comment ça marche :
    Pour chaque point → regarde ses 20 voisins les plus proches
    Si ce point est trop loin de ses voisins → aberrant → supprimer
    """
    print("\n🔧 Nettoyage des points aberrants...")
    nb_avant = len(pcd.points)

    pcd_propre, _ = pcd.remove_statistical_outlier(
        nb_neighbors = 20,    # nombre de voisins à analyser
        std_ratio    = 2.0    # seuil de tolérance
    )

    nb_apres   = len(pcd_propre.points)
    nb_enleves = nb_avant - nb_apres
    print(f"   Avant   : {nb_avant} points")
    print(f"   Enlevés : {nb_enleves} points aberrants")
    print(f"   Après   : {nb_apres} points")

    return pcd_propre


# ════════════════════════════════════════════
#   3. CALCULER LES NORMALES
# ════════════════════════════════════════════

def calculer_normales(pcd):
    """
    Calcule la direction perpendiculaire à la surface en chaque point.

    C'est quoi une normale ?

        surface
           |
    ───────┼───────
           |  ← normale (flèche perpendiculaire)
           ↑

    Pourquoi c'est nécessaire ?
    L'algorithme de reconstruction a besoin de savoir
    dans quelle direction "regarde" chaque point
    pour savoir comment connecter les triangles.

    Sans normales → la reconstruction ne sait pas
    où est l'intérieur et où est l'extérieur de l'objet.
    """
    print("\n📐 Calcul des normales...")

    # calculer les normales
    pcd.estimate_normals(
        search_param = o3d.geometry.KDTreeSearchParamHybrid(
            radius = 0.05,   # chercher dans un rayon de 5cm
            max_nn = 30      # max 30 voisins
        )
    )

    # orienter toutes les normales vers l'EXTÉRIEUR de l'objet
    # (sinon certaines pointeraient vers l'intérieur → objet inversé)
    pcd.orient_normals_consistent_tangent_plane(100)

    print("   ✓ Normales calculées et orientées")
    return pcd


# ════════════════════════════════════════════
#   4. RECONSTRUCTION DE POISSON
#   C'est l'algorithme principal
# ════════════════════════════════════════════

def reconstruction_poisson(pcd, profondeur=9):
    """
    Transforme le nuage de points en mesh 3D.

    L'algorithme de Poisson :
    ─────────────────────────
    Il résout une équation mathématique (équation de Poisson)
    pour trouver la surface qui "colle" le mieux à tous les points
    et leurs normales.

    En gros :
    1. Il imagine une fonction qui vaut 1 à l'intérieur de l'objet
       et 0 à l'extérieur
    2. Il trouve cette fonction en résolvant l'équation de Poisson
    3. Il extrait la surface entre les valeurs 0 et 1
       → c'est le mesh final

    Le paramètre 'profondeur' :
    ───────────────────────────
    profondeur = 6  → mesh grossier, rapide, peu de détails
    profondeur = 9  → mesh équilibré  ← on utilise ça
    profondeur = 12 → mesh très détaillé, lent, lourd

    C'est comme le zoom d'une photo :
    plus c'est élevé, plus c'est détaillé mais plus ça prend de place
    """
    print(f"\n🔺 Reconstruction de Poisson (profondeur={profondeur})...")
    print("   Patience — c'est le calcul le plus long...")

    mesh, densites = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
        pcd,
        depth       = profondeur,
        width       = 0,
        scale       = 1.1,
        linear_fit  = False
    )

    print(f"   ✓ Mesh créé :")
    print(f"     Triangles : {len(mesh.triangles)}")
    print(f"     Sommets   : {len(mesh.vertices)}")

    return mesh, densites


# ════════════════════════════════════════════
#   5. NETTOYER LE MESH
# ════════════════════════════════════════════

def nettoyer_mesh(mesh, densites):
    """
    Supprime les triangles "flottants" en dehors de l'objet.

    Pourquoi ils apparaissent ?
    L'algorithme de Poisson crée parfois une surface
    autour de zones où il n'y a pas vraiment de points
    → des "fantômes" de surface à supprimer.

    Comment on les supprime ?
    Chaque sommet (vertex) a une "densité" = combien de points
    du nuage l'ont influencé. Si densité faible → sommet fantôme.
    On supprime tous les sommets sous un certain seuil.
    """
    print("\n✂️  Nettoyage du mesh...")

    densites_array = np.asarray(densites)

    # seuil : supprimer les 5% de sommets les moins denses
    seuil = np.quantile(densites_array, 0.05)

    # garder seulement les sommets au-dessus du seuil
    sommets_a_garder = densites_array > seuil
    mesh_propre = mesh.select_by_index(
        np.where(sommets_a_garder)[0]
    )

    # supprimer les triangles dégénérés (trop petits ou aplatis)
    mesh_propre.remove_degenerate_triangles()
    mesh_propre.remove_duplicated_triangles()
    mesh_propre.remove_duplicated_vertices()
    mesh_propre.remove_non_manifold_edges()

    print(f"   Triangles restants : {len(mesh_propre.triangles)}")
    print(f"   Sommets restants   : {len(mesh_propre.vertices)}")

    return mesh_propre


# ════════════════════════════════════════════
#   6. CALCULER LES NORMALES DU MESH
# ════════════════════════════════════════════

def finaliser_mesh(mesh):
    """
    Calcule les normales des triangles et lisse les couleurs.
    Nécessaire pour un rendu visuel correct.
    """
    print("\n✨ Finalisation du mesh...")
    mesh.compute_vertex_normals()
    mesh.compute_triangle_normals()
    print("   ✓ Normales des triangles calculées")
    return mesh


# ════════════════════════════════════════════
#   7. EXPORTER LES FICHIERS
# ════════════════════════════════════════════

def exporter(mesh, nom_fichier):
    """
    Sauvegarde le mesh dans plusieurs formats.

    .ply → format universel (Open3D, MeshLab, Blender)
    .stl → format impression 3D (Cura, PrusaSlicer)
    .obj → format 3D universel avec textures (Blender, Maya)
    """
    print(f"\n💾 Export des fichiers...")

    # export .ply
    chemin_ply = f"{nom_fichier}.ply"
    o3d.io.write_triangle_mesh(chemin_ply, mesh)
    taille = os.path.getsize(chemin_ply) / 1024
    print(f"   ✓ {chemin_ply} ({taille:.1f} KB)")

    # export .stl (pour impression 3D)
    chemin_stl = f"{nom_fichier}.stl"
    o3d.io.write_triangle_mesh(chemin_stl, mesh)
    taille = os.path.getsize(chemin_stl) / 1024
    print(f"   ✓ {chemin_stl} ({taille:.1f} KB)")

    # export .obj (pour Blender)
    chemin_obj = f"{nom_fichier}.obj"
    o3d.io.write_triangle_mesh(chemin_obj, mesh)
    taille = os.path.getsize(chemin_obj) / 1024
    print(f"   ✓ {chemin_obj} ({taille:.1f} KB)")

    print(f"\n   → Pour imprimer en 3D : utilise le fichier .stl")
    print(f"   → Pour Blender        : utilise le fichier .obj")


# ════════════════════════════════════════════
#   8. VISUALISATION DU MESH
# ════════════════════════════════════════════

def visualiser_comparaison(pcd, mesh):
    """
    Affiche côte à côte :
    - à gauche  : le nuage de points original
    - à droite  : le mesh reconstruit

    Pour bien voir la différence entre les deux.
    """
    print("\n👁  Visualisation comparative...")
    print("   Gauche = nuage de points | Droite = mesh reconstruit")
    print("   Contrôles : clic gauche=rotation | molette=zoom | Q=quitter")

    # décaler le mesh vers la droite pour la comparaison
    mesh_decale = o3d.geometry.TriangleMesh(mesh)
    mesh_decale.translate([0.8, 0, 0])

    # colorer le nuage en bleu
    pcd_copie = o3d.geometry.PointCloud(pcd)
    pcd_copie.paint_uniform_color([0.2, 0.4, 1.0])

    # colorer le mesh en orange
    mesh_decale.paint_uniform_color([1.0, 0.5, 0.2])

    o3d.visualization.draw_geometries(
        [pcd_copie, mesh_decale],
        window_name = "Nuage de points VS Mesh reconstruit",
        width       = 1200,
        height      = 700,
    )

def visualiser_mesh_seul(mesh):
    """Affiche uniquement le mesh final."""
    print("\n👁  Visualisation du mesh final...")
    mesh.paint_uniform_color([0.8, 0.6, 0.4])
    o3d.visualization.draw_geometries(
        [mesh],
        window_name = "Mesh 3D final — Scanner ESP32",
        width       = 900,
        height      = 700,
    )


# ════════════════════════════════════════════
#   9. PIPELINE COMPLET
# ════════════════════════════════════════════

def pipeline_reconstruction(chemin_input, nom_output):
    """
    Pipeline complet :
    .ply (nuage) → nettoyage → normales → Poisson → .stl (mesh)
    """

    print(f"""
{'='*55}
  RECONSTRUCTION DE SURFACE 3D
  Entrée : {chemin_input}
  Sortie : {nom_output}.stl / .obj / .ply
{'='*55}""")

    # ── 1. charger ──
    pcd = charger_nuage(chemin_input)
    if pcd is None:
        return

    # ── 2. nettoyer le nuage ──
    pcd = nettoyer(pcd)

    # ── 3. normales ──
    pcd = calculer_normales(pcd)

    # ── 4. reconstruction Poisson ──
    mesh, densites = reconstruction_poisson(pcd, profondeur=9)

    # ── 5. nettoyer le mesh ──
    mesh = nettoyer_mesh(mesh, densites)

    # ── 6. finaliser ──
    mesh = finaliser_mesh(mesh)

    # ── 7. exporter ──
    exporter(mesh, nom_output)

    print(f"""
{'='*55}
  ✅ RECONSTRUCTION TERMINÉE !
  Triangles : {len(mesh.triangles)}
  Sommets   : {len(mesh.vertices)}
{'='*55}
""")

    # ── 8. visualiser ──
    visualiser_comparaison(pcd, mesh)
    visualiser_mesh_seul(mesh)

    return mesh


# ════════════════════════════════════════════
#   10. POINT D'ENTRÉE
# ════════════════════════════════════════════

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Reconstruction 3D depuis un nuage de points"
    )
    parser.add_argument(
        '--input',
        type    = str,
        default = "mon_scan.ply",
        help    = "Fichier .ply en entrée (défaut: mon_scan.ply)"
    )
    parser.add_argument(
        '--output',
        type    = str,
        default = "objet_final",
        help    = "Nom du fichier de sortie sans extension"
    )
    parser.add_argument(
        '--demo',
        action  = 'store_true',
        help    = "Utilise mon_scan.ply généré par nuage_points.py"
    )

    args = parser.parse_args()

    if args.demo:
        # utilise le fichier démo généré précédemment
        chemin = "mon_scan.ply"
        if not os.path.exists(chemin):
            print("❌ Lance d'abord : py -3.11 nuage_points.py --demo")
        else:
            pipeline_reconstruction(chemin, "objet_final")
    else:
        pipeline_reconstruction(args.input, args.output)