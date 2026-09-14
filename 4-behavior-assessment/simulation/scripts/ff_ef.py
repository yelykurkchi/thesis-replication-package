import carla
import logging
import random
import time


client = carla.Client('localhost', 2000)
client.set_timeout(4.0) # seconds

print(client.get_available_maps())
world = client.load_world('Town05')

traffic_manager = client.get_trafficmanager()

spawn_points = world.get_map().get_spawn_points()

# for i, vehicle_spawn_point in enumerate(spawn_points):
#     world.debug.draw_string(vehicle_spawn_point.location, str(i), life_time=100)

vehicle_spawn_point: carla.Transform = spawn_points[299]
vehicle_spawn_loc = vehicle_spawn_point.location
end_point = spawn_points[83]



world.debug.draw_string(vehicle_spawn_point.location, 'Spawn point', life_time=100, color=carla.Color(255,0,0))

vehicle_bp = world.get_blueprint_library().find('vehicle.tesla.model3')
vehicle_bp.set_attribute('role_name','vehicle')
vehicle = world.spawn_actor(vehicle_bp, vehicle_spawn_point)

walker_bp = world.get_blueprint_library().find('walker.pedestrian.0004')
walker_spawn_point = carla.Transform(carla.Location(x=vehicle_spawn_loc.x-31.8, y=vehicle_spawn_loc.y-6.8, z=1.300000), carla.Rotation(pitch=0.000000, yaw=90, roll=0.000000))
walker = world.spawn_actor(walker_bp, walker_spawn_point)

spectator_loc: carla.Location = carla.Location(x=walker_spawn_point.location.x, y=walker_spawn_point.location.y-5, z=walker_spawn_point.location.z+2)
spectator_transform = carla.Transform(spectator_loc, carla.Rotation(pitch=-10, yaw=90, roll=0))


spectator = world.get_spectator()
world_snapshot = world.wait_for_tick()
spectator.set_transform(spectator_transform)

# spectator.set_transform(walker.get_transform())

traffic_manager.set_path(vehicle, [end_point.location])
vehicle.set_autopilot(True)


# https://carla.readthedocs.io/en/0.9.14/core_actors/#walkers
# walker_controller_bp = world.get_blueprint_library().find('controller.ai.walker')
# walker_controller = world.spawn_actor(walker_controller_bp, carla.Transform(), walker)
# walker_controller.start()
spectator_goal_loc: carla.Location = carla.Location(x=walker_spawn_point.location.x, y=walker_spawn_point.location.y+15, z=walker_spawn_point.location.z+2)
# walker_controller.go_to_location(spectator_goal_loc)
#walker_controller.go_to_location(world.get_random_location_from_navigation())
# walker_controller.set_max_speed(1.4)  # Between 1 and 2 m/s (default is 1.4 m/s).

while True:
    world.tick()

ai_controller.stop()
