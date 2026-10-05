# Changelog

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
