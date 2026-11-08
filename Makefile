# Each README step is a make target. `make help` lists them.
DC := docker compose

# Host IDs passed to Docker: files stay yours; the GPU is reachable without root.
export USER_UID   := $(shell id -u)
export USER_GID   := $(shell id -g)
export VIDEO_GID  := $(or $(shell getent group video  | cut -d: -f3),44)
# No "render" group (older systems): fall back to your own group, so the two entries never clash.
export RENDER_GID := $(or $(shell getent group render | cut -d: -f3),$(USER_GID))

# Gazebo window on (1) or off (0): make sim GUI=0
GUI ?= 1

# Simulation processes that can outlive a closed terminal. The [x] brackets stop pkill from
# matching its own command line.
SIM_PROCS := [r]os2 launch|[g]z sim|[p]arameter_bridge|[r]obot_state_publisher

# Run a command inside the container, with ROS 2 and our workspace (once built) sourced.
ROS = $(DC) exec dev bash -c 'source /opt/ros/jazzy/setup.bash; \
      [ -f install/setup.bash ] && source install/setup.bash; $(1)'

.PHONY: help build up down clean log stop shell versions sim
help:      ## list the targets
	@grep -E '^[a-z-]+:.*## ' Makefile | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'
build:     ## build the Docker image and print its size
	$(DC) build
	docker images x2nav:jazzy
up:        ## start the container and allow its windows on your screen
	xhost +local:docker
	$(DC) up -d
down:      ## stop the container
	$(DC) down
clean:     ## remove the container and the image built here (next start needs make build)
	$(DC) down --rmi local
log:       ## status of the container, its CPU and RAM use, and the simulations running in it
	$(DC) ps -a
	@ids=$$($(DC) ps -q); \
	  if [ -n "$$ids" ]; then docker stats --no-stream $$ids; \
	    echo "Simulation processes:"; \
	    procs=$$($(DC) exec -T dev pgrep -af "$(SIM_PROCS)"); \
	    if [ -n "$$procs" ]; then echo "$$procs" | cut -c1-100; else echo "  none"; fi; \
	  else echo "No container running: make up"; fi
stop:      ## stop any simulation still running in the container (e.g. after closing a terminal)
	@$(DC) exec -T dev bash -c 'pkill -INT -f "$(SIM_PROCS)" && sleep 3; \
	  pkill -KILL -f "$(SIM_PROCS)"; echo "Simulation processes stopped."'
shell:     ## open a shell inside the container
	$(DC) exec dev bash
versions:  ## print the exact versions for the README
	@echo "Host: $$(lsb_release -ds) · $$(docker --version)"
	@$(call ROS,. /etc/os-release; echo "Container: $$PRETTY_NAME · ROS 2 $$ROS_DISTRO"; \
	  gz sim --version | head -1; dpkg-query -W ros-jazzy-turtlebot3-gazebo ros-jazzy-ros-gz-sim)
sim: stop  ## Q1.1: Burger in the House world (4 ms physics step). GUI=0: no Gazebo window
	$(call ROS,ros2 launch /ws/launch/sim.launch.py gui:=$(GUI))
