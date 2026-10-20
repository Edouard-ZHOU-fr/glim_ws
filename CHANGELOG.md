# Changelog

## [1.4.0] - 2026-10-20

### Versions des dépôts (`glim.repos`)

| Dépôt | 1.3.0 | 1.4.0 |
|---|---|---|
| `src/glim` | `1.0.0` (`409eeec`) | `1.1.0` (`5e8c91c`) |
| `src/glim_ros2` | `1.0.0` (`19e2c56`) | `1.0.0` (inchangé) |
| `src/glim_ext` | `1.3.1` (`672c63e`) | `1.4.0` (`f24a401`) |
| `src/convert_gnss` | `1.0.1` (`b7f1992`) | `1.0.1` (inchangé) |
| `../gtsam` | `1.0.0` (`41c8e54`) | `1.0.0` (inchangé) |
| `../iridescence` | `1.0.0` (`de083e2`) | `1.0.0` (inchangé) |
| `../gtsam_points` | `1.0.0` (`17e948d`) | `1.0.0` (inchangé) |

Les librairies ne changent pas : inutile de les recompiler.

### Ajouté

- **glim : estimation du biais IMU quand le véhicule est à l'arrêt**
  - À l'initialisation (`initialization_mode: "LOOSE"`, `use_static_imu_bias: true`) : si le véhicule est immobile pendant la fenêtre d'initialisation (`initialization_window_size`, 3 s), le prior du biais IMU est centré sur le biais estimé avec une précision de `1e6` (sigma 1e-3), au lieu d'un prior nul et lâche (précision `10`). Sinon, le comportement précédent est conservé.
  - Pendant l'odométrie (`static_imu_bias_update`) : chaque fois que le véhicule reste immobile pendant `static_imu_bias_update_window` (3 s), un prior de biais est ajouté sur la frame courante, au plus une fois par fenêtre.
    - `"NONE"` : désactivé.
    - `"OBSERVABLE"` : contraint le biais gyro et la composante du biais acc selon la gravité (biais acc horizontal laissé libre).
    - `"FULL"` : contraint aussi le biais acc horizontal à zéro, pour que le roll/pitch soit corrigé par la gravité (suppose un biais horizontal négligeable).
  - Estimation : biais gyro = vitesse angulaire moyenne ; biais acc = accélération moyenne - g × sa direction. Seule la composante selon la gravité est observable à l'arrêt, la composante horizontale vaut zéro. Les échantillons à plus de 2 sigma de la moyenne sont rejetés.
  - Détection de l'arrêt (seuils communs à l'initialisation et à l'odométrie) : écart-type max par axe < `static_acc_std_thresh` (0,1 m/s²) et < `static_gyro_std_thresh` (0,01 rad/s), mouvement de l'odométrie LiDAR dans la fenêtre < `static_max_translation` (0,1 m) et < `static_max_rotation` (0,003 rad). Les données IMU doivent couvrir au moins 90 % de la fenêtre (10 échantillons minimum).
  - Logs :
    - à l'initialisation : `sensor is static (...)` puis `static IMU bias=...`, sinon `sensor is not static (...), use the default IMU bias prior` ou `IMU data do not cover the initialization window (...)` ;
    - pendant l'odométrie : `static IMU bias update at ... (mode=...)` puis `static IMU bias=... current=...`.
  - Documentation dans les commentaires de `config_odometry_gpu.json`.

### Modifié

- **glim**
  - `config_odometry_gpu.json` (config utilisée) : ajout de `use_static_imu_bias: true`, `static_imu_bias_update: "OBSERVABLE"`, `static_imu_bias_update_window: 3.0` et des seuils `static_acc_std_thresh: 0.1`, `static_gyro_std_thresh: 0.01`, `static_max_translation: 0.1`, `static_max_rotation: 0.003`.
  - `config_odometry_cpu.json` : mêmes paramètres, mais avec `static_imu_bias_update: "NONE"` (biais à l'arrêt seulement à l'initialisation).
- **glim_ext** (avec `dynamic_scale: true`) : une variance d'angle nulle ou négative est traitée comme « non fournie », même après l'interpolation au timestamp de la submap. Le prior de rotation prend alors le sigma par défaut (`yaw_prior_sigma_deg`, `roll_pitch_prior_sigma_deg`). Avant, l'interpolation avec une variance positive donnait une petite variance, donc le sigma minimal (`*_min_sigma_deg`).
- **glim_ws** : `glim.repos` passe `glim` à `1.1.0` et `glim_ext` à `1.4.0`.

### Corrigé

- **glim_ext**
  - **Covariance de position nulle** (ex. EKF mal initialisé) : elle donnait l'information maximale (`1.3e6`), donc le prior de translation le plus fort, et la position pouvait servir à estimer `T_mgrs_world`. Une variance nulle, négative ou NaN fait maintenant rejeter la position : log `Gnss abodonne: Zero covariance: (var=...)`, croix rouge dans le viewer, et la position n'est pas utilisée pour `T_mgrs_world`. Cela corrige aussi l'information NaN d'une covariance NaN (limitation connue de la 1.3.0).
  - **Accès concurrent aux submaps** (limitation connue de la 1.3.0) : le thread GNSS lisait `submap->frames` et `submap->T_world_origin` pendant que le global mapping les modifiait (remplacement des frames par `drop_frame_points()`, mise à jour des poses après chaque optimisation). Cela pouvait faire planter le processus ou donner des poses incohérentes. Les timestamps et `T_origin_imu` sont maintenant copiés dans `on_insert_submap()`, et les poses sont mises à jour sous mutex dans `on_update_submaps()`. Ce callback est désormais enregistré même avec `isShow: false`.
  - **Repère du cap et du roll/pitch** : l'estimation du yaw de `T_mgrs_world`, le log de cohérence roll/pitch et les angles non contraints du prior de rotation utilisaient la pose odométrique de la frame origine. Or les positions et `X(id)` sont dans le repère du global mapping, et l'écart entre les deux (la dérive déjà corrigée par le global mapping) biaisait le yaw de `T_mgrs_world`. Ces calculs utilisent maintenant la dernière pose optimisée de la submap.
  - **Blocage de l'association GNSS** : si le premier timestamp d'une submap était exactement égal au plus ancien timestamp GNSS en attente, cette submap n'était ni supprimée ni associée et bloquait toutes les suivantes, sans plus aucun prior GNSS jusqu'à la fin. Elle est maintenant supprimée.

### Limitations connues

- **Priors GNSS (glim_ext)**
  - Inchangé depuis la 1.3.0 : une seule submap par boucle de traitement reçoit un prior, et les autres n'en reçoivent jamais (ex. quand le global mapping insère plusieurs submaps d'un coup) ; `GlobalMapping::load()` supprime les priors GNSS ; comportement de `weak_inf_scale` et seuils "faible"/"fiable" codés en dur ; log `invalid condition in GNSS global module!!`.
  - Le yaw de `T_mgrs_world` est estimé avec toutes les submaps associées, pas seulement celles dont la position est fiable. Comme une variance d'angle nulle prend le sigma par défaut, les messages d'un EKF mal initialisé (orientation identité, covariance nulle) peuvent entrer dans la moyenne du cap.
  - Les variances x/y du GNSS sont données dans les axes MGRS, mais appliquées sur les axes x/y du repère GLIM, tournés du yaw de `T_mgrs_world` ; le terme croisé `covariance[1]` est ignoré. Cela n'a d'effet que si la covariance xy est anisotrope.
  - La durée d'une coupure GNSS n'est pas contrôlée : une submap prise pendant une coupure reçoit une position interpolée linéairement entre les deux bords de la coupure.
- **Biais IMU à l'arrêt (glim)**
  - La précision du prior (`1e6`) ne dépend ni de l'écart-type mesuré ni du nombre d'échantillons : avec des vibrations (moteur au ralenti), le prior peut être environ 4 à 5 fois trop confiant.
  - Une rotation lente et constante (< `static_max_rotation` / fenêtre, soit 0,001 rad/s avec les valeurs par défaut) passe la détection et est absorbée dans le biais gyro.
  - Si `static_imu_bias_update_window` est à moins d'une période de frame de `smoother_lag - 0.1`, la mise à jour n'est jamais déclenchée, et aucun avertissement n'est loggé.
- **Sauvegarde après crash (glim)** : si le thread d'odométrie s'arrête sur une exception, les frames encore dans la fenêtre du smoother (`smoother_lag`, environ 5 s) ne sont pas transmises au mapping et manquent dans la carte enregistrée.
- **Déchargement GPU** (désactivé par défaut) : limitations de la 1.2.0 inchangées. De plus, après un OOM, `values.bin` contient pour les submaps déchargées (avec `gpu_offload_freeze_relinearization: true`) leur pose au moment du déchargement, sans les corrections ultérieures (ex. fermeture de boucle).
- **Installeur** : `milla_glim_installer.bash` crée `build/` sans `mkdir -p`. Après un échec, supprimez `../gtsam/build`, `../iridescence/build` et `../gtsam_points/build` avant de le relancer.

### Mise à jour depuis 1.3.0

```bash
cd glim_ws
vcs import . < glim.repos     # glim 1.1.0, glim_ext 1.4.0 (librairies inchangées)
source /opt/ros/humble/setup.bash
colcon build --cmake-args \
  -DGTSAM_DIR=/usr/local/lib/cmake/GTSAM \
  -DCMAKE_PREFIX_PATH="/usr/local;/opt/ros/humble" \
  -DBUILD_WITH_CUDA=ON \
  -DBUILD_WITH_VIEWER=ON \
  -DBUILD_WITH_MARCH_NATIVE=OFF
```

Avec un `config_odometry_*.json` personnalisé, ajoutez `use_static_imu_bias`, `static_imu_bias_update`, `static_imu_bias_update_window` et les seuils `static_*` : sans eux, l'estimation du biais à l'arrêt est désactivée (`use_static_imu_bias: false`, `static_imu_bias_update: "NONE"`). `config_gnss_global.json` ne change pas.

## [1.3.0] - 2026-10-09

### Versions des dépôts (`glim.repos`)

Les librairies `gtsam`, `iridescence` et `gtsam_points` sont maintenant déclarées dans `glim.repos` et figées sur un tag, comme les packages ROS. Elles sont toujours clonées dans `../`, à côté de `glim_ws`.

| Dépôt | 1.2.0 | 1.3.0 |
|---|---|---|
| `src/glim` | `1.0.0` (`409eeec`) | `1.0.0` (inchangé) |
| `src/glim_ros2` | `1.0.0` (`19e2c56`) | `1.0.0` (inchangé) |
| `src/glim_ext` | `1.0.0` (`943b3c9`) | `1.3.1` (`672c63e`) |
| `src/convert_gnss` | `1.0.0` (`2b5cadf`) | `1.0.1` (`b7f1992`) |
| `../gtsam` | `main`, cloné par l'installeur | `1.0.0` (`41c8e54`) |
| `../iridescence` | `master`, cloné par l'installeur | `1.0.0` (`de083e2`) |
| `../gtsam_points` | `main`, cloné par l'installeur | `1.0.0` (`17e948d`) |

Les tags des trois librairies pointent sur les mêmes commits que les branches clonées jusqu'ici : inutile de les recompiler si elles sont déjà installées à ces commits. Le tag `1.0.0` d'iridescence est un tag Milla, à ne pas confondre avec le tag amont `v1.0.1` (sur une autre branche) ; la librairie installée reste `libiridescence.so.1.0.1`.

### Ajouté

- **glim_ext : prior de roulis/tangage (roll/pitch) GNSS**
  - Contraint le roll et le pitch des submaps avec l'orientation des messages GNSS, contre la dérive d'inclinaison de la carte (haute vitesse, trajets longs, pentes, peu de fermetures de boucle).
  - Le yaw et le roll/pitch forment un seul prior de rotation (`PriorFactor<Pose3>`, mesure `Rz(yaw) * Ry(pitch) * Rx(roll)`). Chaque angle est activé et filtré indépendamment : le roll/pitch peut être contraint même si le cap est rejeté. L'information est exprimée sur les angles d'Euler (`J^-T * diag(1/sigma^2) * J^-1`), pour qu'un écart de yaw ne crée pas d'erreur de roll en pente.
  - Nouveaux paramètres : `enable_roll_pitch_prior`, `roll_pitch_prior_sigma_deg`, `roll_pitch_min_sigma_deg`, `roll_pitch_max_sigma_deg` (variances `covariance[21]` et `covariance[28]`).
  - Log à l'initialisation : `GNSS - estimated roll=... deg (std=... deg), pitch=... deg (std=... deg) over N submaps`. Une moyenne de plus de quelques dixièmes de degré indique une rotation entre l'IMU et `base_link` (montage) : augmentez `roll_pitch_min_sigma_deg` ou désactivez ce prior.
  - Documentation et conseils de réglage dans `src/glim_ext/README.md`.
- **glim_ext : affichage des contraintes GNSS dans le viewer** (paramètre `isShow`)
  - Prior de position : ligne submap → position GNSS et croix (cyan : normal, orange : faible, rouge : abandonné).
  - Prior de cap : ligne magenta selon le cap GNSS. Prior roll/pitch : ligne jaune selon l'axe z du prior.
  - Rien n'est dessiné si le viewer n'est pas lancé.
- **glim_ext : paramètre `weak_inf_scale`** : information (1/sigma²) du prior de translation quand le GNSS est faible ("Gnss faible"). Elle était figée à `[1e3, 1e3, 3e3]`, qui reste la valeur par défaut.

### Modifié

- **glim_ext** (avec `dynamic_scale: true`)
  - Seuil "Gnss faible" abaissé : information <= `5e2` en x/y ou <= `1e3` en z (avant : `1e3` et `2e3`), soit un sigma GNSS >= 5,1 cm (xy) ou >= 5,7 cm (z) au lieu de 3,6 cm et 4 cm. Ce seuil est codé en dur : il change aussi avec un ancien fichier de config.
  - `T_mgrs_world` n'est estimé qu'avec les submaps dont la position GNSS est fiable (information > `1e3` en x/y et > `2e3` en z, soit un sigma < 3,6 cm et < 4 cm). Une position biaisée (ex. EKF pas encore convergé) décalait tous les priors suivants. Logs : `T_mgrs_world not initialized yet: only N / M submaps have a usable GNSS position` en attendant, puis `T_mgrs_world=... (estimated from N / M submaps)`.
  - `config_gnss_global.json` : `yaw_max_sigma_deg` passe de `5.0` à `3.0` ; ajout de `weak_inf_scale: [3e2, 3e2, 5e2]` (sigma 5,8 cm en xy et 4,5 cm en z, au lieu de 3,2 cm et 1,8 cm), du prior roll/pitch (`enable_roll_pitch_prior: true`, sigmas `1.0` / `0.5` / `5.0`) et de `isShow: true`.
  - Le module `gnss_global` dépend maintenant d'Iridescence (`find_package(Iridescence REQUIRED)`).
- **convert_gnss** : `package.xml` déclare ses dépendances d'exécution (`rclpy`, `nav_msgs`, `geometry_msgs`, `tf2_msgs`).
- **glim_ws**
  - `glim.repos` : ajout de `../gtsam`, `../iridescence` et `../gtsam_points` (voir le tableau ci-dessus).
  - `milla_glim_installer.bash` : un seul `vcs import . < glim.repos` clone les librairies et les packages ROS avant la compilation. Il remplace les trois `git clone` et le second `vcs import`. Les submodules d'iridescence sont récupérés par `git submodule update --init --recursive`. Le script s'arrête si le clonage échoue (avant, l'échec était silencieux).
  - `.gitignore` : ignore aussi `pointcloud*/`, `*.pcd`, `*.txt`, `*.csv` et `*.ply`.

### Corrigé

- **glim_ext**
  - Les poids du prior de translation (`dynamic_scale`) utilisent la covariance GNSS interpolée au timestamp de la submap, et non plus celle du dernier message reçu (limitation connue de la 1.2.0).
  - Le prior de translation pouvait être ajouté plusieurs fois à la même submap, quand les nouvelles submaps ne pouvaient pas encore être associées au GNSS (ex. coupure GNSS). Il est maintenant ajouté une seule fois par submap.
- **glim_ws** : `milla_glim_installer.bash` passe `GTSAM_DIR` et `GTSAM_UNSTABLE_DIR` (`/usr/local/lib/cmake/...`) à la configuration de `gtsam_points`, pour qu'il trouve le GTSAM installé.

### Limitations connues

- Priors GNSS (glim_ext) :
  - Seule la dernière submap associée à chaque boucle de traitement reçoit un prior, et la fusion de cartes (`GlobalMapping::load()`) supprime tous les priors GNSS, y compris ceux de rotation (inchangé depuis la 1.2.0).
  - Un GNSS faible reçoit `weak_inf_scale` quelle que soit sa covariance : un GNSS dégradé obtient un prior bien plus serré que sa covariance et tire la carte vers ses positions. Sur les 300 premières secondes du bag Vélizy du 2026-10-07 (config Milla), les 70 priors faibles viennent de sigmas GNSS de 6 à 74 cm (médiane 34 cm) mais reçoivent tous 5,8 cm. Réduisez `weak_inf_scale` pour les relâcher (ex. `[25, 25, 25]` donne 20 cm), en restant sous les seuils faibles (x/y < `5e2`, z < `1e3`).
  - Les seuils "faible" (prior) et "fiable" (initialisation de `T_mgrs_world`) sont codés en dur séparément : un GNSS de sigma 3,6-5,1 cm (xy) ou 4-5,7 cm (z) reçoit un prior normal mais ne sert pas à l'initialisation, qui peut être retardée.
  - `invalid condition in GNSS global module!!` est aussi loggé dans un cas valide, quand l'échantillon GNSS juste après la submap est le plus récent (ex. après une coupure). L'association est reportée et la submap peut ne recevoir aucun prior.
  - Une covariance de position NaN donnerait une information NaN (non observé dans les données enregistrées), et `submap->T_world_origin` est lu par le thread GNSS sans synchronisation.
- Les limitations du déchargement GPU listées en 1.2.0 sont inchangées.

### Mise à jour depuis 1.2.0

```bash
cd glim_ws
vcs import . < glim.repos     # src/ et ../gtsam, ../iridescence, ../gtsam_points
# Librairies : à recompiler seulement si elles ne sont pas à ces commits
#   gtsam 41c8e54, iridescence de083e2, gtsam_points 17e948d
git -C ../gtsam_points rev-parse --short HEAD
source /opt/ros/humble/setup.bash
colcon build --cmake-args \
  -DGTSAM_DIR=/usr/local/lib/cmake/GTSAM \
  -DCMAKE_PREFIX_PATH="/usr/local;/opt/ros/humble" \
  -DBUILD_WITH_CUDA=ON \
  -DBUILD_WITH_VIEWER=ON \
  -DBUILD_WITH_MARCH_NATIVE=OFF
```

Avec un `config_gnss_global.json` personnalisé, ajoutez `weak_inf_scale` et les paramètres roll/pitch : sans eux, `weak_inf_scale` vaut `[1e3, 1e3, 3e3]` et le prior roll/pitch est désactivé.

## [1.2.0] - 2026-10-05

### Versions des dépôts (`glim.repos`)

Tous les dépôts sont désormais figés sur un tag (au lieu de `main`) pour rendre l'installation reproductible.

| Dépôt | 1.1.0 | 1.2.0 |
|---|---|---|
| `src/glim` | `main` (`cc36834`) | `1.0.0` (`409eeec`) |
| `src/glim_ros2` | `main` (`a54c7a2`) | `1.0.0` (`19e2c56`) |
| `src/glim_ext` | `main` (`c569194`) | `1.0.0` (`943b3c9`) |
| `src/convert_gnss` | `1.0.0` | `1.0.0` (inchangé) |

Dépendance clonée par `milla_glim_installer.bash` (non figée, branche `main`) : `gtsam_points` doit inclure le merge `17e948d` (`feature/dynamicLoardGP`) pour utiliser le déchargement GPU.

### Ajouté

- **glim : déchargement de la mémoire GPU des submaps (cartographie longue durée)**
  - Avec `VGICP_GPU`, chaque submap occupe environ 7 Mo sur le GPU (environ 6 Go pour 20 min de roulage). Le global mapping peut maintenant décharger vers la RAM les submaps éloignées, puis les recharger quand elles redeviennent candidates de fermeture de boucle.
  - Deux politiques : par distance (`gpu_offload_distance`, `gpu_offload_prefetch_margin`, hystérésis) et par budget mémoire (`gpu_offload_max_resident_mb`, LRU).
  - Les `gpu_offload_keep_recent_submaps` dernières submaps restent toujours sur le GPU.
  - Les submaps déchargées ne sont pas relinéarisées par iSAM2 (`gpu_offload_freeze_relinearization`).
  - Toutes les 100 submaps, un log indique le nombre de submaps sur le GPU et la mémoire utilisée : `GPU offload: 120/1500 submaps on GPU (850 MB) ...`.
  - **Désactivé par défaut** (`enable_gpu_offload: false` dans `config_global_mapping_gpu.json`).
  - Documentation : `src/glim/README.md` (section *Milla fork*) et `src/glim/src/glim/README_zh.md`.
- **glim : tolérance aux erreurs fatales (ex. GPU out of memory)**
  - Une exception dans les threads odometry, sub mapping et global mapping arrête uniquement le thread concerné, pas tout le processus. Elle est signalée par `has_fatal_error()`.
  - Global mapping : en cas d'OOM GPU, les submaps les moins récemment utilisées sont déchargées, puis l'opération est relancée (2 tentatives au maximum, seulement si le déchargement GPU est actif).
  - Si l'erreur persiste, le global mapping passe en mode *halted* : les nouvelles submaps sont ignorées et `save()` n'enregistre que l'état validé par la dernière mise à jour iSAM2 réussie (facteurs, valeurs et submaps cohérents).
- **glim_ros2 : sauvegarde de la carte en cas de crash**
  - `timer_callback()` détecte les erreurs fatales des modules et appelle `rclcpp::shutdown()`. La carte est alors enregistrée normalement dans `pointcloud/`.
- **glim_ext : prior de cap (yaw) GNSS, adapté au RTK double antenne**
  - Le cap de `base_link` et sa variance (`covariance[35]`) sont lus depuis `PoseWithCovarianceStamped`, puis interpolés au timestamp de chaque submap par le chemin le plus court.
  - Le yaw de `T_mgrs_world` est estimé par moyenne circulaire de l'écart (cap GNSS - cap estimé), au lieu de l'alignement SVD des positions qui est sensible au bruit sur une base courte. Log : `T_mgrs_world yaw from GNSS heading=... deg (spread=... deg)`.
  - Un `PriorFactor<Pose3>` contraint uniquement le yaw, une fois par submap. Roll et pitch restent donnés par l'IMU. Ce facteur est sérialisable, donc conservé dans les dumps.
  - Nouveaux paramètres : `enable_yaw_prior`, `yaw_prior_sigma_deg`, `yaw_min_sigma_deg`, `yaw_max_sigma_deg`. Documentation et conseils de réglage dans `src/glim_ext/README.md`.
- **gtsam_points** (`main`, `17e948d`)
  - `IntegratedVGICPDerivatives::touch_points()` attend la fin du rechargement des données partagées entre plusieurs streams CUDA. Cela corrige des Hessiennes fausses et des `cudaErrorIllegalAddress`.
  - `cudaErrorMemoryAllocation` est converti en `std::bad_alloc`, ce qui rend possibles la reprise après OOM et la sauvegarde.

### Modifié

- **glim**
  - `config_odometry_gpu.json` : `initialization_window_size` passe de `1.0` à `3.0` (initialisation plus longue, plus stable) et `num_threads` passe de `2` à `4`.
  - `config_sub_mapping_gpu.json` : `enable_optimization` passe de `false` à `true` (optimisation des submaps activée).
  - `config_sensors.json` : `imu_bias_noise` passe de `1e-5` à `5e-5` et `global_shutter_lidar` passe de `false` à `true`.
  - `config_global_mapping_gpu.json` : ajout des paramètres `enable_gpu_offload` et `gpu_offload_*`.
- **glim_ext**
  - `config_gnss_global.json` : prior de cap activé (`enable_yaw_prior: true`, `yaw_prior_sigma_deg: 1.0`, `yaw_min_sigma_deg: 0.5`, `yaw_max_sigma_deg: 5.0`).
- **glim_ws**
  - `glim.repos` : tous les dépôts sont figés sur le tag `1.0.0`.

### Corrigé

- **glim_ws** : `milla_glim_installer.bash` appelait `clean_exit`, une fonction non définie. Quand le serveur GitLab Milla était injoignable (VPN ou réseau), le script continuait au lieu de s'arrêter. Il utilise maintenant `exit 1`.

### Limitations connues

- Déchargement GPU :
  - Une relinéarisation complète d'iSAM2 recharge toutes les submaps d'un coup, et le pic mémoire est alors le même que sans déchargement. Cela arrive lors d'une grande fermeture de boucle (plus de 65 % des variables) ou d'une reconstruction après une exception *indeterminant system*.
  - `find_overlapping_submaps` (bouton du viewer) et `GlobalMapping::load()` (offline viewer) ne déchargent pas les submaps.
  - Ce mode est incompatible avec `global_mapping_pose_graph` et avec le loop detector ScanContext de glim_ext.
- Prior de cap :
  - Seule la dernière submap associée à chaque boucle de traitement reçoit un prior.
  - Les poids en translation de `dynamic_scale` utilisent la covariance du dernier message GNSS.
  - La fusion de cartes (`GlobalMapping::load()` sur une carte existante) supprime tous les priors GNSS, y compris ceux de cap.
- La covariance de l'EKF Autoware est trop optimiste (sigma du yaw d'environ 0,4°). Montez `yaw_min_sigma_deg` à 1-2° si la carte est déformée.

### Mise à jour depuis 1.1.0

```bash
cd glim_ws
vcs import . < glim.repos     # checkout des tags 1.0.0
# Seulement pour activer enable_gpu_offload : recompiler gtsam_points à partir de main (>= 17e948d)
cd ../gtsam_points && git pull && cd build && make -j$(nproc) && sudo make install && sudo ldconfig && cd ../../glim_ws
source /opt/ros/humble/setup.bash
colcon build --cmake-args \
  -DGTSAM_DIR=/usr/local/lib/cmake/GTSAM \
  -DCMAKE_PREFIX_PATH="/usr/local;/opt/ros/humble" \
  -DBUILD_WITH_CUDA=ON \
  -DBUILD_WITH_VIEWER=ON \
  -DBUILD_WITH_MARCH_NATIVE=OFF
```
