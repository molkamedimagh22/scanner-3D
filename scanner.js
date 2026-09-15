/* ════════════════════════════════════════════
   SCANNER 3D — LOGIQUE JS
   Three.js + Socket.IO
   ════════════════════════════════════════════ */


// ════════════════════════════════════════════
//   1. CONNEXION WEBSOCKET
// ════════════════════════════════════════════

const socket = io();

// ── Événements reçus du serveur ──────────────

socket.on('connect', () => {
    log('Connecté au serveur Flask', 'ok');
});

socket.on('connexion_ok', (data) => {
    setConnecte(true);
    log(`✓ Connecté à l'ESP32 (${data.ip})`, 'ok');
});

socket.on('connexion_erreur', (data) => {
    setConnecte(false);
    log(`✗ Erreur : ${data.erreur}`, 'erreur');
});

socket.on('deconnexion_ok', () => {
    setConnecte(false);
    log('Déconnecté', 'info');
});

socket.on('scan_demarre', () => {
    setScanActif(true);
    cacherMessageCentre();
    afficherBarre(true);
    t_debut = Date.now();
    timerInterval = setInterval(majChrono, 1000);
    log('▶ Scan démarré', 'ok');
});

socket.on('scan_arrete', () => {
    setScanActif(false);
    afficherBarre(false);
    clearInterval(timerInterval);
    log('⏹ Scan arrêté', 'info');
});

socket.on('scan_termine', (data) => {
    setScanActif(false);
    afficherBarre(false);
    clearInterval(timerInterval);
    majBarre(100);
    log(`✓ Scan terminé — ${data.nb_points} points`, 'ok');
});

// ── Réception de nouveaux points ─────────────
socket.on('nouveaux_points', (data) => {
    // ajouter les points à la scène 3D
    ajouterPoints(data.points);

    // mettre à jour l'affichage
    const nb = data.nb_total;
    document.getElementById('info-points').textContent = `${nb} points`;
    document.getElementById('info-angles').textContent =
        `θ=${data.theta?.toFixed(1)}°  φ=${data.phi?.toFixed(1)}°`;
    document.getElementById('info-dist').textContent =
        `d=${data.distance?.toFixed(0)}mm`;

    document.getElementById('stat-points').textContent = nb;
    document.getElementById('stat-theta').textContent  = `${data.theta?.toFixed(1)}°`;
    document.getElementById('stat-phi').textContent    = `${data.phi?.toFixed(1)}°`;
    document.getElementById('stat-dist').textContent   = `${data.distance?.toFixed(0)}mm`;

    if (data.prog !== undefined) {
        majBarre(data.prog);
        document.getElementById('stat-prog').textContent = `${data.prog}%`;
    }
});

socket.on('log', (data) => {
    log(data.msg);
});

socket.on('scan_sauvegarde', (data) => {
    log(`💾 Fichier sauvegardé : ${data.fichier}`, 'ok');
});


// ════════════════════════════════════════════
//   2. SCÈNE THREE.JS
// ════════════════════════════════════════════

let scene, camera, renderer, controls;
let nuagePoints = null;          // objet Three.js nuage
let geometrie   = null;          // géométrie des points
let positions   = [];            // tableau plat [x,y,z, x,y,z, ...]
let modeAffichage = 'points';    // 'points' ou 'mesh'

function initScene() {
    const canvas = document.getElementById('canvas-3d');
    const container = document.getElementById('canvas-container');

    // ── Scène ──
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x080812);

    // ── Caméra ──
    camera = new THREE.PerspectiveCamera(
        60,                                          // champ de vision (degrés)
        container.clientWidth / container.clientHeight,
        0.001,                                       // plan proche
        100                                          // plan loin
    );
    camera.position.set(0.5, 0.3, 0.8);

    // ── Renderer ──
    renderer = new THREE.WebGLRenderer({
        canvas    : canvas,
        antialias : true
    });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);

    // ── Contrôles orbitaux (tourner / zoomer) ──
    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping  = true;   // inertie
    controls.dampingFactor  = 0.05;
    controls.minDistance    = 0.05;
    controls.maxDistance    = 10;

    // ── Grille de référence ──
    const grille = new THREE.GridHelper(1, 10, 0x2a2a4a, 0x1a1a30);
    grille.position.y = -0.3;
    scene.add(grille);

    // ── Axes XYZ ──
    const axes = new THREE.AxesHelper(0.2);
    scene.add(axes);

    // ── Lumières ──
    scene.add(new THREE.AmbientLight(0x404080, 2));
    const lumiere = new THREE.DirectionalLight(0xffffff, 1);
    lumiere.position.set(1, 2, 1);
    scene.add(lumiere);

    // ── Boucle de rendu ──
    function animer() {
        requestAnimationFrame(animer);
        controls.update();
        renderer.render(scene, camera);
    }
    animer();

    // ── Redimensionnement ──
    window.addEventListener('resize', () => {
        const w = container.clientWidth;
        const h = container.clientHeight;
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
        renderer.setSize(w, h);
    });
}


// ════════════════════════════════════════════
//   3. GESTION DES POINTS 3D
// ════════════════════════════════════════════

function ajouterPoints(nouveaux) {
    /*
     Ajoute une liste de points [[x,y,z], ...] à la scène.

     On utilise THREE.Points : chaque point est un pixel dans la scène 3D.
     C'est le moyen le plus rapide d'afficher des milliers de points.
    */

    // ajouter les nouvelles positions au tableau
    for (const p of nouveaux) {
        positions.push(p[0], p[1], p[2]);
    }

    // supprimer l'ancien objet de la scène
    if (nuagePoints) {
        scene.remove(nuagePoints);
        geometrie.dispose();
    }

    // créer la nouvelle géométrie avec tous les points
    geometrie = new THREE.BufferGeometry();
    const posArray = new Float32Array(positions);
    geometrie.setAttribute('position', new THREE.BufferAttribute(posArray, 3));

    // colorer les points selon leur hauteur (axe Y)
    const couleurs = new Float32Array(positions.length);
    const nbPts    = positions.length / 3;
    let yMin =  Infinity;
    let yMax = -Infinity;

    for (let i = 1; i < positions.length; i += 3) {
        if (positions[i] < yMin) yMin = positions[i];
        if (positions[i] > yMax) yMax = positions[i];
    }

    for (let i = 0; i < nbPts; i++) {
        const y     = positions[i * 3 + 1];
        const t     = (y - yMin) / (yMax - yMin + 0.0001);
        // dégradé : bleu (bas) → violet → rouge (haut)
        couleurs[i * 3]     = t;         // rouge
        couleurs[i * 3 + 1] = 0.2;       // vert
        couleurs[i * 3 + 2] = 1.0 - t;  // bleu
    }

    geometrie.setAttribute('color', new THREE.BufferAttribute(couleurs, 3));

    // matériau points
    const materiau = new THREE.PointsMaterial({
        size          : 0.004,
        vertexColors  : true,
        sizeAttenuation : true,
    });

    nuagePoints = new THREE.Points(geometrie, materiau);
    scene.add(nuagePoints);
}

function viderScene() {
    if (nuagePoints) {
        scene.remove(nuagePoints);
        geometrie.dispose();
        nuagePoints = null;
        geometrie   = null;
    }
    positions = [];
    document.getElementById('info-points').textContent = '0 points';
    document.getElementById('stat-points').textContent = '0';
    afficherMessageCentre();
    log('🗑 Scène vidée', 'info');
}


// ════════════════════════════════════════════
//   4. CONTRÔLES CAMÉRA
// ════════════════════════════════════════════

function resetCamera() {
    camera.position.set(0.5, 0.3, 0.8);
    controls.target.set(0, 0, 0);
    controls.update();
}

function setVue(vue) {
    const dist = 0.8;
    if (vue === 'front')  camera.position.set(0, 0, dist);
    if (vue === 'top')    camera.position.set(0, dist, 0);
    if (vue === 'side')   camera.position.set(dist, 0, 0);
    controls.target.set(0, 0, 0);
    controls.update();
}

function toggleAffichage() {
    // pour l'instant on reste en mode points
    // (le mesh Poisson nécessite open3d côté serveur)
    log('Mode : nuage de points (mesh nécessite reconstruction.py)', 'info');
}


// ════════════════════════════════════════════
//   5. ACTIONS UTILISATEUR
// ════════════════════════════════════════════

function connecter() {
    const ip   = document.getElementById('inp-ip').value;
    const port = parseInt(document.getElementById('inp-port').value);
    socket.emit('connecter_esp32', { ip, port });
    log(`Connexion à ${ip}:${port}...`, 'info');
}

function deconnecter() {
    socket.emit('deconnecter_esp32');
}

function lancerScan() {
    const params = lireParams();
    socket.emit('lancer_scan', params);
}

function simuler() {
    const params = lireParams();
    socket.emit('simuler', params);
}

function stopperScan() {
    socket.emit('stopper_scan');
}

function resetPosition() {
    socket.emit('reset_position');
    log('↺ Reset position envoyé', 'info');
}

function sauvegarderScan() {
    const nom = `scan_${Date.now()}`;
    socket.emit('sauvegarder_scan', { nom });
}

function bougerMoteur(moteur) {
    let angle;
    if (moteur === 'theta') {
        angle = parseFloat(document.getElementById('inp-theta-manuel').value);
    } else {
        angle = parseFloat(document.getElementById('inp-phi-manuel').value);
    }
    socket.emit('bouger_moteur', { moteur, angle });
    log(`→ Moteur ${moteur.toUpperCase()} → ${angle}°`, 'info');
}

function lireParams() {
    return {
        res_theta : parseFloat(document.getElementById('sel-theta').value),
        res_phi   : parseFloat(document.getElementById('sel-phi').value),
        phi_min   : parseFloat(document.getElementById('inp-phi-min').value),
        phi_max   : parseFloat(document.getElementById('inp-phi-max').value),
    };
}


// ════════════════════════════════════════════
//   6. MISE À JOUR DE L'INTERFACE
// ════════════════════════════════════════════

function setConnecte(ok) {
    const badge = document.getElementById('badge-connexion');
    const dot   = badge.querySelector('.dot');
    const texte = badge.querySelector('span:last-child');
    if (ok) {
        dot.className   = 'dot vert';
        texte.textContent = 'Connecté';
    } else {
        dot.className   = 'dot rouge';
        texte.textContent = 'Déconnecté';
    }
    document.getElementById('btn-connecter').disabled   = ok;
    document.getElementById('btn-deconnecter').disabled = !ok;
}

function setScanActif(ok) {
    const badge = document.getElementById('badge-scan');
    const dot   = badge.querySelector('.dot');
    const texte = badge.querySelector('span:last-child');
    if (ok) {
        dot.className   = 'dot orange';
        texte.textContent = 'Scan en cours';
    } else {
        dot.className   = 'dot gris';
        texte.textContent = 'En attente';
    }
    document.getElementById('btn-scan').disabled = ok;
    document.getElementById('btn-stop').disabled = !ok;
}

function afficherBarre(ok) {
    document.getElementById('barre-progression').style.display = ok ? 'block' : 'none';
    if (ok) majBarre(0);
}

function majBarre(pct) {
    document.getElementById('barre-fill').style.width = `${pct}%`;
    document.getElementById('barre-texte').textContent = `${pct}%`;
}

function cacherMessageCentre() {
    document.getElementById('message-centre').style.display = 'none';
}

function afficherMessageCentre() {
    document.getElementById('message-centre').style.display = 'block';
}


// ════════════════════════════════════════════
//   7. CONSOLE LOG
// ════════════════════════════════════════════

function log(message, type = '') {
    const console_el = document.getElementById('console-log');
    const ligne = document.createElement('div');
    ligne.className    = `console-ligne ${type}`;
    ligne.textContent  = `[${new Date().toLocaleTimeString()}] ${message}`;
    console_el.appendChild(ligne);
    console_el.scrollTop = console_el.scrollHeight;

    // garder max 100 lignes
    while (console_el.children.length > 100) {
        console_el.removeChild(console_el.firstChild);
    }
}


// ════════════════════════════════════════════
//   8. CHRONOMÈTRE
// ════════════════════════════════════════════

let t_debut = null;
let timerInterval = null;

function majChrono() {
    if (!t_debut) return;
    const elapsed = Math.floor((Date.now() - t_debut) / 1000);
    const m = Math.floor(elapsed / 60).toString().padStart(2, '0');
    const s = (elapsed % 60).toString().padStart(2, '0');
    document.getElementById('stat-temps').textContent = `${m}:${s}`;
}


// ════════════════════════════════════════════
//   9. ESTIMATION DES POINTS
// ════════════════════════════════════════════

function majEstimation() {
    const res_t   = parseFloat(document.getElementById('sel-theta').value);
    const res_p   = parseFloat(document.getElementById('sel-phi').value);
    const phi_min = parseFloat(document.getElementById('inp-phi-min').value);
    const phi_max = parseFloat(document.getElementById('inp-phi-max').value);
    const n = Math.floor(360 / res_t) * Math.floor((phi_max - phi_min) / res_p);
    document.getElementById('nb-estimation').textContent = n.toLocaleString();
}

document.getElementById('sel-theta').addEventListener('change', majEstimation);
document.getElementById('sel-phi').addEventListener('change', majEstimation);
document.getElementById('inp-phi-min').addEventListener('input', majEstimation);
document.getElementById('inp-phi-max').addEventListener('input', majEstimation);


// ════════════════════════════════════════════
//   DÉMARRAGE
// ════════════════════════════════════════════

initScene();
majEstimation();
log('Scanner 3D initialisé', 'ok');