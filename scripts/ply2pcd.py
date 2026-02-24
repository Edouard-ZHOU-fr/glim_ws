import open3d as o3d
import time
import numpy as np
from scipy.spatial.transform import Rotation as R

################################


inputPLYName = "mgrs_final.ply"
# T_world_utm 的参数: x, y, z, qx, qy, qz, qw    
se3_mgrs_world = np.array([41598.625653,3577.682233,218.441666,
                           0.000000,0.000000,-0.853967,0.520328])
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

def transform_mgrs_world(input_pcd_path,se3_mgrs_world):
    output_pcd_path = "global_map_mgrs_absolute.pcd"

    T_mgrs_world = np.eye(4)
    T_mgrs_world[:3, :3] = R.from_quat(se3_mgrs_world[3:]).as_matrix()
    T_mgrs_world[:3, 3] = se3_mgrs_world[:3]

    
    print("Transformation Matrix (T_mgrs_world):")
    print(T_mgrs_world)

    pcd = o3d.io.read_point_cloud(input_pcd_path)
    if pcd.is_empty():
        print("Error: Point cloud is empty or path is wrong.")
        return

    pcd.transform(T_mgrs_world)
    o3d.io.write_point_cloud(output_pcd_path, pcd, write_ascii=False)
    
    # 验证第一个点
    print("Verification - First point in UTM:")
    print(np.asarray(pcd.points)[0])

start = time.time()
pcd = o3d.io.read_point_cloud(inputPLYName)

print_c("####### Transformation en cours  #############")

if useFiltrage: 
# 2. 统计学去噪
# nb_neighbors: 指定邻居点的数量（通常设为 20）
# std_ratio: 标准差乘数，数值越小，滤除的点越多（建议 1.0 - 2.0）
    cl, ind = pcd.remove_statistical_outlier(nb_neighbors=20, std_ratio=3)
    # 提取清洗后的点云
    pcd_cleaned = pcd.select_by_index(ind)
else:
    pcd_cleaned = pcd

if isShow :
    outlier_cloud = pcd.select_by_index(ind, invert=True)
    outlier_cloud.paint_uniform_color([1, 0, 0]) # 红色标记噪点
    pcd_cleaned.paint_uniform_color([0.8, 0.8, 0.8]) # 灰色标记有效点
    o3d.visualization.draw_geometries([pcd_cleaned, outlier_cloud])


outputPCDName = inputPLYName.replace('.ply', '.pcd')
o3d.io.write_point_cloud(outputPCDName, pcd_cleaned)
transform_mgrs_world(outputPCDName,se3_mgrs_world)

end = time.time()
print_reussi(" Temps d'éxecusion: "+str(end-start)+"   (s)\n")
