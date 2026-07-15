import open3d as o3d
import open3d.core as o3c
import time
import numpy as np
from scipy.spatial.transform import Rotation as R

################################

inputPLYName = "Noisy_le_roi.ply"
# T_mgrs_world x, y, z, qx, qy, qz, qw
se3_mgrs_world = np.array([30670.345011, 11472.709748, 189.927335, 0.000000, 0.000000, 0.603371, 0.797461])
useFiltrage = True
isShow = False

################################


def print_c(clignotant):
    clignotant = str(clignotant)
    print("\033[5;34;42m" + clignotant + "\033[0m", end='\r')


def print_reussi(reussi):
    reussi = str(reussi)
    print("\033[1;32;47m" + reussi + "\033[0m")


def transform_mgrs_world(input_pcd, se3_mgrs_world, outputPCDName):
    """input_pcd est un o3d.t.geometry.PointCloud (tensor API) -> conserve les attributs custom (ex: intensity)."""

    T_mgrs_world = np.eye(4)
    T_mgrs_world[:3, :3] = R.from_quat(se3_mgrs_world[3:]).as_matrix()
    T_mgrs_world[:3, 3] = se3_mgrs_world[:3]

    print("Transformation Matrix (T_mgrs_world):")
    print(T_mgrs_world)

    if input_pcd.is_empty():
        print("Error: Point cloud is empty or path is wrong.")
        return

    # transform() applique uniquement aux points/normales; les autres attributs (intensity...) restent inchangés
    T_tensor = o3c.Tensor(T_mgrs_world, dtype=o3c.Dtype.Float64)
    input_pcd.transform(T_tensor)

    o3d.t.io.write_point_cloud(outputPCDName, input_pcd, write_ascii=False)

    print("Verification - First point in UTM:")
    print(input_pcd.point.positions[0].numpy())
    if "intensity" in input_pcd.point:
        print("Verification - First intensity:")
        print(input_pcd.point["intensity"][0].numpy())
    else:
        print("Attention: aucun champ 'intensity' trouve dans le nuage de points.")


start = time.time()

# --- lecture via l'API tensor pour conserver TOUS les champs custom du PLY (dont intensity) ---
pcd = o3d.t.io.read_point_cloud(inputPLYName)

# print("Champs disponibles dans le nuage de points:", list(pcd.point.keys()))

print_c("####### Transformation en cours  #############")

if useFiltrage:
    # nb_neighbors: 20
    # std_ratio: 1.0 - 2.0
    pcd_cleaned, mask = pcd.remove_statistical_outliers(nb_neighbors=20, std_ratio=3.0)
else:
    pcd_cleaned = pcd
    mask = None

if isShow:
    outlier_cloud = pcd.select_by_mask(mask.logical_not()) if mask is not None else None
    if outlier_cloud is not None:
        outlier_cloud.paint_uniform_color([1.0, 0.0, 0.0])
    pcd_cleaned.paint_uniform_color([0.8, 0.8, 0.8])
    o3d.visualization.draw_geometries(
        [pcd_cleaned.to_legacy(), outlier_cloud.to_legacy() if outlier_cloud is not None else pcd_cleaned.to_legacy()]
    )

outputPCDName = inputPLYName.replace('.ply', '.pcd')
transform_mgrs_world(pcd_cleaned, se3_mgrs_world, outputPCDName)

end = time.time()
print_reussi(" Temps d'éxecusion: " + str(end - start) + "   (s)\n")
