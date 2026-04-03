# Installation
Le Glim est nécessaire que ROS 2 soit préinstallé! Et il est conseille de créer un dossier vide et mettre le glim_ws dedans, donc, le strcture de la dossier sera comme si dessous!
```txt
glim/
├──gtsam/
├──iridescence/
├──gtsam_points/
└──glim_ws/
    ├──README.md
    ├──milla_glim_installer.bash
    ├──glim.repos
    ├──src/
    ├──scripts/
    └──launch/
```
## Repository contents
* _Les librairies nécessaires_:
    * gtsam/: (sera généré par le script automatique) Cette librairie est pour le backend de SLAM
    * iridescence/: (sera généré par le script automatique) La librairie ros2 pour le Slam viwer qui permet de modifier les nuages de points en mode offline si besoin. 
    * gtsam_points/: (sera généré par le script automatique) Cette librairie est un Wrapper de GTSAM optimisé pour une accélération matérielle via CUDA

* _Les packages nécessaires_:
    * glim/:Le nœud ROS principal englobe du SLAM, l'optimisation du back-end et le tracking du front-end(VGICP).
    * glim_ros2/:Le nœud ROS2 pour lancer le node glim.
    * glim_ext/:Tous les extention modules de glim(ex: gnss correction).
    * convert_gnss/:le module qui permet de convertir le gnss de format **xxx** à **PoseWithCovarianceStamped**

## Lancement installation
* source Ros Humble: Compilation de worspace de Glim besoin d'environement de Ros 
```bash
source /opt/ros/humble/setup.bash

```
* Installation avec le script: le script `milla_glim_installer.bash` permet de faire tous les installation de Glim
```bash
./milla_glim_installer.bash
```
Une fois que le message **Glim_ws installed successfully** s'affiche, cela signifie que GLIM est correctement installé. Dans le cas contraire, le message **Aborting: failed to install Glim_ws** apparaîtra.



# Utilisation
Le système GLIM requiert trois entrées principales : les topics /kinematic_state, /imu et /perception/concatenated/pointcloud.

### Configuration de la carte pour la localisation
#### 1. Préparation du dossier de la carte
Si la zone n'a jamais été cartographiée, créez un dossier de carte contenant un fichier
`map_projector_info.yaml` avec la structure suivante :
```yaml
projector_type: MGRS
vertical_datum: WGS84
mgrs_grid: 31UDQ
```
Si vous réutilisez un dossier existant, supprimez ou renommez impérativement les éléments suivants :
- `pointcloud_map_metadata.yaml`
- `pointcloud_map.pcd/` (Dossier)
> :warning:  Si vous conservez l'ancien fichier ou dossier, la localisation sera biaisée par l'ancienne acquisition de données !

### 2. Launch AD
* lancement AD
```bash
millaros2
ros2 run ad_launcher start_ad -f '/home/milla/.milla/config/calibration/config.yaml' --disable-logging 
```

* lancement robot
```bash
source ~/ros/millarobo_ws/install/setup.bash
ros2 launch robo_launch robo_launch_all.launch.xml
```

### 3. Initialisation de localisation

Puisque la noeud lidar matching n'est pas utilisé, donc la localisation ne peut pas initialiser tous seul.
Ouvriez un nouveau terminal puis saisir:
```bash
millaros2
ros2 service call /localization/force_initialization std_srvs/srv/Trigger
```
Une fois vous avez vue ```succesful=True```, c'est à dire le localisation est bien initialisée!

### 4. lancement le Glim
**S'il vous avez enregisté le Rosbag et vous voulez le rejouer avec le glim, Veuillez commencer à partir d'ici!**
* source le workspace
```bash
source install/setup.bash
```
* lancement avec le script ros2 launch:
```bash
ros2 launch launch/milla_glim.launch.py
```
Cela ouvrira également une fenêtre Iridescence dédiée, permettant de visualiser le processus de cartographie en temps réel. Pour économiser des ressources lors du SLAM, vous pouvez décocher l'option "submap" afin de réduire l'affichage et de limiter la charge sur le GPU.

### 5. Roulage en mauelle
Vous pouvez conduire en mode manuel dans les zones que vous souhaitez cartographier. Théoriquement, GLIM peut fonctionner en temps réel jusqu'à 80 km/h. Cependant, pour des vitesses supérieures à 40 km/h, il est fortement conseillé d'enregistrer un rosbag pour un traitement ultérieur (poste-taitement)

### 6. Enregistement et géneration de nuage de points(.pcd)

* _Enregistement sous la format de glim_
    * Vous pouvez faicilement faire ```ctrl+c``` dans la terminal de glim pour générer un dossier ```pointcloud``` dans la glim_ws
    * En meme temps il va aussi générer un fichier ```mgrs.txt```, ce fichier enregister le matrice qui nous permet de transformer le nuage de points de repère local à la repère Mgrs.

* _Création le nuage de points au format.ply_
    * Le ros2 noeud glim ne créer que le nuage de points au format .ply
    * Donc vous pouvez lancer la ligne commande suivant pour ouvrir le offline viwer et puis générer le nuage de point .ply
    ```bash
    source install/setup.bash
    ros2 run glim_ros offline_viewer
    ```
    * Ensuite, Cliquez le ```File```, ```OPen New Map```  pour ouvrir votre nuage de points enregisté, puis choisir dans ```File```,```Save```, puis ```Export Points``` pour générer la nuage de point au format de ply.
    > :warning: Attention cette étape peut générer que le format de .ply pensez de bien saisir de sousfix .ply pour le nom de nuage de point.
* _Transformation nuages de points de la format .ply à la format .pcd_
    * Copiez la matrice dans```mgrs.txt``` puis le mettre dans ```scripts/ply2pcd.py```pour convertir le nuage de point de la format .ply à la format .pcd. Pensez à changer le répertoire de votre nuage de point .ply aussi.
    * Ex: les deux lignes à changer dans le python script. 
    ```python
    inputPLYName = "longviller.ply"
    # T_mgrs_world x, y, z, qx, qy, qz, qw    
    se3_mgrs_world = np.array([27309.745095,81371.585083,125.842703,0.000000,0.000000,0.937159,-0.348903])
    ```

