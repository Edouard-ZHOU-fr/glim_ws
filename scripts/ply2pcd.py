import open3d as o3d
import time
import numpy as np
from scipy.spatial.transform import Rotation as R

################################


inputPLYName = "mob0.ply"
# T_mgrs_world x, y, z, qx, qy, qz, qw    
se3_mgrs_world = np.array([30785.204685,83444.300612,169.133631,0.000000,0.000000,0.974724,-0.223410])
useFiltrage = True
isShow = False

################################


def print_c(clignotant):
    clignotant = str(clignotant)
    # os.system("clear")
    print("\033[5;34;42m"+clignotant+"\033[0m", end='\r')

def print_reussi(reussi):
    reussi = str(reussi)
    print("\033[1;32;47m"+reussi+"\033[0m")

def transform_mgrs_world(input_pcd,se3_mgrs_world,outputPCDName):

    T_mgrs_world = np.eye(4)
    T_mgrs_world[:3, :3] = R.from_quat(se3_mgrs_world[3:]).as_matrix()
    T_mgrs_world[:3, 3] = se3_mgrs_world[:3]

    
    print("Transformation Matrix (T_mgrs_world):")
    print(T_mgrs_world)

    # pcd = o3d.io.read_point_cloud(input_pcd_path)
    if input_pcd.is_empty():
        print("Error: Point cloud is empty or path is wrong.")
        return

    input_pcd.transform(T_mgrs_world)
    o3d.io.write_point_cloud(outputPCDName, input_pcd, write_ascii=False)
    
    print("Verification - First point in UTM:")
    print(np.asarray(input_pcd.points)[0])

start = time.time()
pcd = o3d.io.read_point_cloud(inputPLYName)

print_c("####### Transformation en cours  #############")

if useFiltrage: 
# nb_neighbors:  20）
# std_ratio:  1.0 - 2.0）
    cl, ind = pcd.remove_statistical_outlier(nb_neighbors=20, std_ratio=3)

    pcd_cleaned = pcd.select_by_index(ind)
else:
    pcd_cleaned = pcd

if isShow :
    outlier_cloud = pcd.select_by_index(ind, invert=True)
    outlier_cloud.paint_uniform_color([1, 0, 0])
    pcd_cleaned.paint_uniform_color([0.8, 0.8, 0.8]) 
    o3d.visualization.draw_geometries([pcd_cleaned, outlier_cloud])


outputPCDName = inputPLYName.replace('.ply', '.pcd')
# o3d.io.write_point_cloud(outputPCDName, pcd_cleaned)
transform_mgrs_world(pcd_cleaned,se3_mgrs_world,outputPCDName)

end = time.time()
print_reussi(" Temps d'éxecusion: "+str(end-start)+"   (s)\n")
