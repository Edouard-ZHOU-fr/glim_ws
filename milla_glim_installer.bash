#!/usr/bin/sh

log_milla () {
  log_string=$1
  log_to_file=$2
  color_string="\033[38;2;54;227;167m$log_string\e[0m"
  echo "[Info]$color_string"

}

log_warn () {
  log_string=$1
  log_to_file=$2
  color_string="\e[1;33m$log_string\e[0m"
  echo "[Warning]$color_string"

}

log_error () {
  log_string=$1
  log_to_file=$2
  color_string="\e[1;31m$log_string\e[0m"
  echo "[Erro]$color_string"
}

log_milla "Try to Connect Milla-GitLab Server" 0
git clone https://gitlab.infra.isfm.vpn:4000/milla/ad_ros2/ad_ros2 
if [ $? != 0 ]; then
    log_error "/!\\ Falied to Connect milla-GitLab server maybe check the VPN ou le Réseau?" 0
    clean_exit 1
else
    rm -rf ./ad_ros2
fi

log_milla "____ _     ___ __  __
 / ___| |   |_ _|  \/  |
| |  _| |    | || |\/| |
| |_| | |___ | || |  | |
 \____|_____|___|_|  |_| milla\n" 1

# Installer dependencies obligatoire
sudo apt install -y libomp-dev libboost-all-dev libmetis-dev \
                 libfmt-dev libspdlog-dev \
                 libglm-dev libglfw3-dev libpng-dev libjpeg-dev  >/dev/null 2>&1
if [ $? != 0 ]; then
    log_error "Aborting apt dependencies obligatoire" 0
    exit 1
else
    log_milla "Apt Dependencie install succesfully" 0
fi

pip3 install  scipy numpy --default-timeout=1000 >/dev/null 2>&1
status1=$?
pip3 install  open3d --default-timeout=3600 >/dev/null 2>&1
status2=$?
if [ $status1 != 0 ] || [ $status2 != 0 ] ; then
    log_error "Aborting pip3 dependencies obligatoire" 0
    exit 1
else
    log_milla "pip3 Dependencie install succesfully" 0
fi



# Clone les workspace obligatoire
git clone https://gitlab.infra.isfm.vpn:4000/milla/mapping/gtsam.git ../gtsam  >/dev/null 2>&1
git clone https://gitlab.infra.isfm.vpn:4000/milla/mapping/iridescence.git --recursive ../iridescence  >/dev/null 2>&1
git clone https://gitlab.infra.isfm.vpn:4000/milla/mapping/gtsam_points.git ../gtsam_points  >/dev/null 2>&1
cd ../

# build les workspaces
mkdir gtsam/build && cd gtsam/build
cmake .. -DGTSAM_BUILD_EXAMPLES_ALWAYS=OFF \
         -DGTSAM_BUILD_TESTS=OFF \
         -DGTSAM_WITH_TBB=OFF \
         -DGTSAM_USE_SYSTEM_EIGEN=ON \
         -DGTSAM_BUILD_WITH_MARCH_NATIVE=OFF  >/dev/null 2>&1
make -j$(nproc)  >/dev/null 2>&1
sudo make install  >/dev/null 2>&1
if [ $? != 0 ]; then
    log_error "Aborting failed install gtsam" 0
    exit 1
else
    log_milla "gtsam install succesfully" 0
    cd ../../
fi


mkdir iridescence/build && cd iridescence/build
cmake .. -DCMAKE_BUILD_TYPE=Release  >/dev/null 2>&1
make -j$(nproc)  >/dev/null 2>&1
sudo make install  >/dev/null 2>&1
if [ $? != 0 ]; then
    log_error "Aborting failed install iridescence(viwer)" 0
    exit 1
else
    log_milla "iridescence(viwer) install succesfully" 0
    cd ../../
fi


mkdir gtsam_points/build && cd gtsam_points/build
log_warn "Version actuelle compatible que avec GPU achitecture Ada Lovelace " 0
log_warn "Ex: RTX 4090 / 4080 / 4070 / 4060 / 4050"
cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_WITH_CUDA=ON \
  -DCMAKE_CUDA_ARCHITECTURES=89  >/dev/null 2>&1
make -j$(nproc)  >/dev/null 2>&1
sudo make install  >/dev/null 2>&1
if [ $? != 0 ]; then
    log_error "Aborting failed install gtsam_points" 0
    exit 1
else
    log_milla "gtsam_points install succesfully" 0
    cd ../../
fi


# Make shared libraries visible to the system
sudo ldconfig  >/dev/null 2>&1


# build ros2 workspace
cd glim_ws
vcs import . < glim.repos >/dev/null 2>&1
source /opt/ros/humble/setup.bash
colcon build --cmake-args \
  -DBUILD_WITH_CUDA=ON \
  -DBUILD_WITH_VIEWER=ON \
  -DBUILD_WITH_MARCH_NATIVE=OFF >/dev/null 2>&1

if [ $? != 0 ]; then
    log_error "Aborting failed install Glim_ws" 0
    exit 1
else
    log_milla "Glim_ws install succesfully" 0
    cd ../../
fi
