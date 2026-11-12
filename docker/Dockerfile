# ROS 2 Jazzy on Ubuntu 24.04. ros-base already includes robot_state_publisher, TF and rosbag2.
FROM ros:jazzy-ros-base
ENV DEBIAN_FRONTEND=noninteractive

# T1: robot + world + simulator. turtlebot3_gazebo pulls in ros_gz (bridge, sim) and Gazebo Harmonic (gz_*_vendor).
# libgl1-mesa-dri: GPU driver (Intel/AMD) so Gazebo renders through /dev/dri.
RUN apt-get update && apt-get install -y --no-install-recommends \
      ros-jazzy-turtlebot3-gazebo \
      libgl1-mesa-dri \
    && rm -rf /var/lib/apt/lists/*

# Q1.2: drive the robot by keyboard (teleop_twist_keyboard) and see its sensors and frames (RViz2).
RUN apt-get update && apt-get install -y --no-install-recommends \
      ros-jazzy-teleop-twist-keyboard \
      ros-jazzy-rviz2 \
    && rm -rf /var/lib/apt/lists/*

# Q2.1: build the map (slam_toolbox) and save it to disk (map_saver_cli, from nav2_map_server).
RUN apt-get update && apt-get install -y --no-install-recommends \
      ros-jazzy-slam-toolbox \
      ros-jazzy-nav2-map-server \
    && rm -rf /var/lib/apt/lists/*

# Q3.1: navigate on the saved map. Only the Nav2 servers launch/navigation.launch.py starts (48 MB);
# the navigation2 + nav2_bringup metapackages would add 629 MB (OpenCV, VTK, docking, TurtleBot4 sim).
RUN apt-get update && apt-get install -y --no-install-recommends \
      ros-jazzy-nav2-amcl \
      ros-jazzy-nav2-planner \
      ros-jazzy-nav2-navfn-planner \
      ros-jazzy-nav2-controller \
      ros-jazzy-nav2-regulated-pure-pursuit-controller \
      ros-jazzy-nav2-bt-navigator \
      ros-jazzy-nav2-behaviors \
      ros-jazzy-nav2-velocity-smoother \
      ros-jazzy-nav2-lifecycle-manager \
    && rm -rf /var/lib/apt/lists/*

# Q3.2: send goals from Python (BasicNavigator in nav2_simple_commander, used by go_to.py). One small package.
RUN apt-get update && apt-get install -y --no-install-recommends \
      ros-jazzy-nav2-simple-commander \
    && rm -rf /var/lib/apt/lists/*

# Run as the host user, so files written into the repo (maps, results, build) aren't owned by root.
# The base image already has the user "ubuntu" (UID/GID 1000); make passes your real IDs.
ARG USER_UID=1000
ARG USER_GID=1000
RUN if [ "$USER_GID" != "1000" ]; then groupmod -g "$USER_GID" ubuntu; fi \
 && if [ "$USER_UID" != "1000" ]; then usermod -u "$USER_UID" ubuntu; fi

ENV TURTLEBOT3_MODEL=burger
RUN echo 'source /opt/ros/jazzy/setup.bash' >> /home/ubuntu/.bashrc \
 && echo '[ -f /ws/install/setup.bash ] && source /ws/install/setup.bash' >> /home/ubuntu/.bashrc
USER ubuntu
WORKDIR /ws
