
import os, sys, time, json, random
import numpy as np

from .core import Cfg, Clock, Room, Space, Item, Robot
from .env_maps import topologyName_dict
from .adaptation_overhead import log_overhead_statistics

def _sort_events_csv_by_time(csv_path: str):
    if not os.path.exists(csv_path):
        return
    try:
        with open(csv_path, 'r') as f:
            lines = f.readlines()
        if not lines:
            return
        header, rows = lines[0], lines[1:]
        def keyfun(line):
            try:
                first = line.split(',', 1)[0]
                return float(first)
            except Exception:
                return 0.0
        rows.sort(key=keyfun)
        with open(csv_path, 'w') as f:
            f.write(header)
            f.writelines(rows)
    except Exception:
        pass


def _log_sim_time(cfg: Cfg, sim_secs: float):
    # write simTime.csv
    path = cfg.SIMTIME_LOGFILE
    os.makedirs(os.path.dirname(path), exist_ok=True)
    new = not os.path.exists(path)
    with open(path, 'a') as f:
        if new:
            f.write('arch,space,Nrooms,Nbot,Nmal,failProb,commFailProb,arrival,loadItem,moveItem,dropItem,comp,comm,recovery,simTime\n')
        f.write(f"{cfg.ARCHITECTURE},{cfg.TOPOLOGY_NAME},{cfg.N_ROOMS},{cfg.N_ROBOTS},{cfg.N_MALICIOUS},{int(cfg.FAIL_PROB*100)},{int(cfg.COMM_FAIL_PROB*1000)},{int(cfg.ITEM_SPAWNING_TIME)},{int(cfg.LOAD_TIME)},{int(cfg.MOVEMENT_TIME)},{int(cfg.DROP_TIME)},{int(cfg.COMP_TIME)},{int(cfg.COMM_TIME)},{int(cfg.RECOVERY_TIME)},{sim_secs}\n")

def _build_cfg(config_path: str) -> Cfg:
    with open(config_path, 'r') as f:
        d = json.load(f)
    # Fill derived / defaults
    d.setdefault('SIMTIME_LOGFILE', os.path.join(d.get('RESULTS_DIR', 'results'), 'simTime.csv'))
    d.setdefault('LOGFILE', '')
    d.setdefault('ITEM_SPAWNING_TRACE', '_')
    d.setdefault('LOAD_TRACE', '_')
    d.setdefault('MOVEMENT_TRACE', '_')
    d.setdefault('DROP_TRACE', '_')
    d.setdefault('COMP_TRACE', '_')
    d.setdefault('COMM_TRACE', '_')
    d.setdefault('RECOVERY_TRACE', '_')
    d.setdefault('TARGETS', -1)
    d.setdefault('MALICIOUS_FAKE_FAILURES', True)
    d.setdefault('FIND_ROUTE_STRATEGY', 'breadth')
    # Keep simulator resilient if frontend payload omits optional fields.
    d.setdefault('IMPORTANCE_PROBABILITIES', [0.5, 0.1, 0.4])
    d.setdefault('EXPIRATION_TIME', [-1, -1, -1])
    d.setdefault('EXPIRATION_DISTR', ['exponential', 'exponential', 'exponential'])
    d.setdefault('PRIVACY_COMM_TIME_BONUS', [0.0, 0.0, 0.0])
    d.setdefault('PRIVACY_COMP_TIME_BONUS', [0.0, 0.0, 0.0])
    # booleans default
    for k in ['LOG_ITEM','LOG_DELIVERY','LOG_LOAD','LOG_DROP','LOG_EXPIRE','LOG_MOVE','LOG_FAIL','LOG_RECOVERY','LOG_HELP','LOG_FAKE','LOG_RESCUE']:
        d.setdefault(k, True if k in ['LOG_ITEM','LOG_DELIVERY','LOG_EXPIRE'] else False)
    return Cfg(d)

def _logfile_name(cfg: Cfg) -> str:
    base = cfg.RESULTS_DIR
    os.makedirs(base, exist_ok=True)
    if cfg.ARCHITECTURE == 'decentralized':
        prefix = 'fully_'
    elif cfg.ARCHITECTURE == 'semi-decentralized':
        prefix = 'semi_'
    elif cfg.ARCHITECTURE.startswith('centralized-'):
        prefix = f"centralized{cfg.ARCHITECTURE.split('-',1)[1].capitalize()}_"
    else:
        prefix = f"{cfg.ARCHITECTURE}_"

    name = prefix + cfg.TOPOLOGY_NAME + '_Nbot' + str(cfg.N_ROBOTS) + '_Nmal' + str(cfg.N_MALICIOUS)
    name += '_p' + str(int(cfg.FAIL_PROB*100)) + 'pc_cmF' + str(int(cfg.COMM_FAIL_PROB*1000))
    name += '_A' + str(int(cfg.ITEM_SPAWNING_TIME)) + '_L' + str(int(cfg.LOAD_TIME)) + '_M' + str(int(cfg.MOVEMENT_TIME)) + '_D' + str(int(cfg.DROP_TIME))
    name += '_cp' + str(int(cfg.COMP_TIME)) + '_cm' + str(int(cfg.COMM_TIME)) + '_R' + str(int(cfg.RECOVERY_TIME)) + '.csv'
    return os.path.join(base, name)

def getTargetRoom(cfg: Cfg, rooms):
    if cfg.TARGETS == -1:
        return None
    if max(cfg.TARGETS) >= len(rooms):
        print('[ERROR] TARGETS has an index outside room range'); sys.exit(-1)
    trg = [t for t in cfg.TARGETS if t != cfg.SOURCE]
    if len(trg) == 0:
        return None
    idx = random.choice(trg)
    return rooms[idx]

def _resolve_topology_name(cfg: Cfg) -> str:
    """Support both full topology names (mesh25) and shorthand (mesh/ring/tree)."""
    name = cfg.TOPOLOGY_NAME
    if name in topologyName_dict:
        return name
    if name in ['mesh', 'ring', 'tree']:
        candidate = f'{name}{cfg.N_ROOMS}'
        if candidate in topologyName_dict:
            return candidate
    print('Unsupported topology:', name)
    sys.exit(-1)

def run(config_path='config.json'):
    cfg = _build_cfg(config_path)
    # print("DEBUG: Loaded Config:", json.dumps(cfg.__dict__, indent=2))
    
    # Validate architecture
    valid_archs = ['decentralized', 'semi-decentralized', 'centralized-proximity', 
                   'centralized-importance', 'centralized-proximp', 'centralized-impprox', 
                   'dynamic-adaptation']
    if cfg.ARCHITECTURE not in valid_archs:
        print('Unsupported architecture:', cfg.ARCHITECTURE); sys.exit(-1)
    
    # Initialize RTLola monitor for dynamic-adaptation
    rtlola_monitor = None
    if cfg.ARCHITECTURE == 'dynamic-adaptation':
        # print("[Monitor] Initializing RTLola CLI for dynamic-adaptation")
        try:
            from .rtlola_monitor import RTLolaMonitor
            # Get spec file path - convert to absolute if relative
            spec_file = getattr(cfg, 'RTLOLA_SPEC_FILE', 'spec2.rtlola')
            if not os.path.isabs(spec_file):
                # Try project root first, then fallback to sim package directory
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                candidate_root = os.path.join(project_root, spec_file)
                script_dir = os.path.dirname(os.path.abspath(__file__))
                candidate_pkg = os.path.join(script_dir, spec_file)
                spec_file = candidate_root if os.path.exists(candidate_root) else candidate_pkg
            
            rtlola_binary = getattr(cfg, 'RTLOLA_BINARY_PATH', None)
            rtlola_monitor = RTLolaMonitor(spec_file=spec_file, rtlola_binary=rtlola_binary)
            # print(f"[RTLola] Using spec: {spec_file}")
        except Exception as e:
            print(f"[ERROR] Failed to initialize RTLola monitor: {e}")
            print(f"[ERROR] RTLola is required for dynamic-adaptation architecture.")
            print(f"[ERROR] Ensure 'rtlola-cli' is installed and in your PATH, or configured in config.json.")
            sys.exit(-1)
    
    resolved_topology_name = _resolve_topology_name(cfg)
    cfg.TOPOLOGY_NAME = resolved_topology_name
    topo = topologyName_dict[resolved_topology_name]
    if cfg.N_ROOMS != len(topo.keys()):
        print('N_ROOMS mismatch with selected TOPOLOGY_NAME'); sys.exit(-1)

    # resolve logfile
    logfile = cfg.LOGFILE if cfg.LOGFILE else _logfile_name(cfg)
    cfg.LOGFILE = logfile  # write back

    # Remove existing logfile to ensure fresh simulation data
    if os.path.exists(logfile):
        try:
            os.remove(logfile)
        except OSError:
            pass

    # init env
    start_wall = time.time()
    clock = Clock()
    rooms = [Room(i) for i in range(cfg.N_ROOMS)]
    space = Space(cfg, rooms, topo, clock, source=rooms[cfg.SOURCE])
    
    # Set RTLola monitor reference in cfg for Robot access
    cfg.rtlola_monitor = rtlola_monitor

    # robots
    bots = []
    for i in range(cfg.N_ROBOTS):
        bots.append(Robot(cfg, i, i < cfg.N_MALICIOUS, space, logfile))
    botsRandomOrder = list(bots)

    # schedule first item
    clock.scheduleEvent('item', [cfg.ITEM_SPAWNING_TIME], [cfg.ITEM_SPAWNING_TRACE], [cfg.ITEM_SPAWNING_DISTR])

    itemIdx = 0
    event_count = 0
    last_adaptation_check = 0.0
    adaptation_interval = getattr(cfg, 'ADAPTATION_CHECK_INTERVAL', 300.0)  # Check every 5 minutes by default
    
    # Overhead tracking for dynamic adaptation
    adaptation_overhead_total = 0.0  # Total wall-clock time spent on adaptation
    adaptation_check_count = 0       # Number of adaptation checks performed
    adaptation_switch_count = 0      # Number of architecture switches
    adaptation_overhead_samples = [] # Individual overhead measurements
    
    # Adaptation State
    smoothed_latency = None
    alpha = 0.2 # Smoothing factor for EMA
    last_switch_time = -300.0 # Allow immediate switch at start
    min_time_between_switches = 30.0 # Cool-down period (seconds)
    
    # Latency tracking for adaptation (Python-based)
    latency_window = []  # Store (timestamp, latency) tuples
    latency_window_duration = 3600.0  # 1 hour window
    item_create_times = {}  # Track when each item was created
    
    try:
        while clock.getTime() < cfg.SIM_TIME:
            clock.checkClock()
            ts, event = clock.getNextEvent()
            
            # Dynamic Parameter Updates (Scenario A)
            # Check if we have phases defined in config
            if hasattr(cfg, 'PHASES') and cfg.PHASES:
                for phase in cfg.PHASES:
                    if phase['start'] <= ts < phase['end']:
                        # Apply phase parameters
                        if 'FAIL_PROB' in phase and cfg.FAIL_PROB != phase['FAIL_PROB']:
                            cfg.FAIL_PROB = phase['FAIL_PROB']
                            # print(f"[Phase] Time {ts:.1f}: Changed FAIL_PROB to {cfg.FAIL_PROB}")
                        
                        if 'COMM_FAIL_PROB' in phase and cfg.COMM_FAIL_PROB != phase['COMM_FAIL_PROB']:
                            cfg.COMM_FAIL_PROB = phase['COMM_FAIL_PROB']
                            # print(f"[Phase] Time {ts:.1f}: Changed COMM_FAIL_PROB to {cfg.COMM_FAIL_PROB}")

                        if 'RECOVERY_TIME' in phase and cfg.RECOVERY_TIME != phase['RECOVERY_TIME']:
                            cfg.RECOVERY_TIME = phase['RECOVERY_TIME']
                            # print(f"[Phase] Time {ts:.1f}: Changed RECOVERY_TIME to {cfg.RECOVERY_TIME}")
                            
                        if 'ITEM_SPAWNING_TIME' in phase and cfg.ITEM_SPAWNING_TIME != phase['ITEM_SPAWNING_TIME']:
                            cfg.ITEM_SPAWNING_TIME = phase['ITEM_SPAWNING_TIME']
                            # print(f"[Phase] Time {ts:.1f}: Changed ITEM_SPAWNING_TIME to {cfg.ITEM_SPAWNING_TIME}")
                        break
            
            # Artificial delay removed
            # time.sleep(0.001)
            
            # Check if no more events (simulation complete)
            if event is None:
                # print(f"[INFO] No more events at time {clock.getTime()}. Simulation complete.")
                break
                
            event_count += 1
            
            # Send event to RTLola if monitoring is active
            if rtlola_monitor and rtlola_monitor.is_running():
                # Determine event details for RTLola (spec2.rtlola format: time,itemId,event,destination)
                item_id = -1
                destination = -1
                event_type = ""
                
                if event == 'item':
                    event_type = "create"
                    item_id = itemIdx
                    destination = -1  # Not yet assigned
                elif event.startswith('move-'):
                    idx = int(event.split('-')[1])
                    if bots[idx].getItem():
                        item_id = bots[idx].getItem().getIdx()
                        destination = bots[idx].destination.getIdx()
                        event_type = "move"
                elif event.startswith('recovery-'):
                    event_type = "recover"
                elif event.startswith('expire-'):
                    item_id = int(event.split('-')[1])
                    event_type = "expire"
                
                # Send to RTLola (only send events that RTLola cares about)
                if event_type in ["create", "deliver"]:
                    try:
                        rtlola_monitor.send_event(ts, -1, item_id, -1, -1, destination, event_type)
                    except Exception as e:
                        print(f"[RTLola] Error sending event: {e}")
            
            # Process simulation event
            if event == 'item':
                trg = getTargetRoom(cfg, rooms)
                space.newItem(Item(cfg, logfile, itemIdx, space, ts, imp=-1, target=trg))
                item_create_times[itemIdx] = ts  # Track creation time
                itemIdx += 1
                random.shuffle(botsRandomOrder)
                for bot in botsRandomOrder:
                    if bot.getLocation() == space.getSource() and bot.isFree() and bot.isHealthy() and not bot.hasOtherTasks():
                        it = space.getMoreImportantItem(room=space.getSource())
                        if it is not None:
                            bot.loadItem(it, clock.getTime())
                            break
            elif event.startswith('move-'):
                idx = int(event.split('-')[1])
                bot = bots[idx]
                
                # Check if delivery will occur (robot has item and is at destination)
                has_item = bot.getItem() is not None
                at_destination = bot.getLocation() == bot.destination
                
                if has_item and at_destination:
                    item_id_for_delivery = bot.getItem().getIdx()
                    dest_id = bot.destination.getIdx()
                    
                    # Calculate latency directly
                    if item_id_for_delivery in item_create_times:
                        delivery_latency = ts - item_create_times[item_id_for_delivery]
                        
                        if delivery_latency > 0:
                            # Add to latency window
                            latency_window.append((ts, delivery_latency))
                            
                            # Remove old entries outside the window
                            latency_window = [(t, lat) for t, lat in latency_window if ts - t <= latency_window_duration]
                    
                    # Send deliver event to RTLola BEFORE move processes it
                    if rtlola_monitor and rtlola_monitor.is_running():
                        try:
                            rtlola_monitor.send_event(ts, -1, item_id_for_delivery, -1, -1, dest_id, "deliver")
                        except Exception as e:
                            print(f"[RTLola] Error sending delivery event: {e}")
                
                # Now process the move
                bots[idx].move(ts)
            elif event.startswith('recovery-'):
                idx = int(event.split('-')[1]); bots[idx].recovery(ts)
            elif event.startswith('expire-'):
                idx = int(event.split('-')[1]); item = space.getItembyId(idx); space.expireItem(item, ts)
            
            # Check for architecture adaptation (score-based)
            if rtlola_monitor and rtlola_monitor.is_running() and (ts - last_adaptation_check) >= adaptation_interval:
                last_adaptation_check = ts
                
                # Start overhead measurement
                adaptation_start_time = time.time()
                adaptation_check_count += 1
                
                # Calculate mean latency from window
                rtlola_query_start = time.time()
                if latency_window:
                    raw_latency = sum(lat for _, lat in latency_window) / len(latency_window)
                else:
                    raw_latency = None
                rtlola_query_time = time.time() - rtlola_query_start
                
                if raw_latency is not None:
                    # Update Smoothed Latency (EMA)
                    if smoothed_latency is None:
                        smoothed_latency = raw_latency
                    else:
                        smoothed_latency = alpha * raw_latency + (1 - alpha) * smoothed_latency
                        
                    # Import scoring functions
                    from .architecture_scoring import select_best_architecture
                    
                    # Calculate scores for all architectures
                    scoring_start = time.time()
                    
                    # Only consider switching if cool-down period has passed
                    time_since_last_switch = ts - last_switch_time
                    
                    if time_since_last_switch >= min_time_between_switches:
                        best_arch, scores = select_best_architecture(cfg, smoothed_latency)
                        
                        current_arch = cfg.current_architecture
                        
                        # Apply architecture switch if needed
                        if best_arch != current_arch:
                            adaptation_switch_count += 1
                            last_switch_time = ts
                            cfg.set_architecture(best_arch)
                            # Log architecture switch
                            with open(logfile, 'a') as f:
                                f.write(f'{ts},-2,-1,-1,-1,-1,switch_architecture_{best_arch}\n')
                            
                            # Only print when switching architecture
                            # print(f"[ADAPTATION] @ {ts:.2f}s: Switched from {current_arch} to {best_arch} (latency={smoothed_latency:.2f})")
                    else:
                        # In cool-down, stick with current
                        scoring_time = 0 # No scoring done
                        best_arch = cfg.current_architecture
                        
                    scoring_time = time.time() - scoring_start
                    
                    # Record overhead for this check
                    check_overhead = time.time() - adaptation_start_time
                    adaptation_overhead_total += check_overhead
                    adaptation_overhead_samples.append({
                        'sim_time': ts,
                        'total_overhead_ms': check_overhead * 1000,
                        'rtlola_query_ms': rtlola_query_time * 1000,
                        'scoring_ms': scoring_time * 1000,
                        'switched': best_arch != current_arch,
                        'latency': smoothed_latency
                    })
                    
                    # # Log overhead info
                    # print(f"[OVERHEAD] Check #{adaptation_check_count}: {check_overhead*1000:.2f}ms "
                    #       f"(RTLola: {rtlola_query_time*1000:.2f}ms, Scoring: {scoring_time*1000:.2f}ms)")
                else:
                    # No valid latency, still record overhead
                    check_overhead = time.time() - adaptation_start_time
                    adaptation_overhead_total += check_overhead
                    adaptation_overhead_samples.append({
                        'sim_time': ts,
                        'total_overhead_ms': check_overhead * 1000,
                        'rtlola_query_ms': rtlola_query_time * 1000,
                        'scoring_ms': 0,
                        'switched': False,
                        'latency': None
                    })
    
    finally:
        # Clean up RTLola monitor
        if rtlola_monitor:
            rtlola_monitor.shutdown()

    wall_time = time.time() - start_wall
    _log_sim_time(cfg, wall_time)
    _sort_events_csv_by_time(logfile)
    
    # Log adaptation overhead statistics
    log_overhead_statistics(
        adaptation_check_count,
        adaptation_switch_count,
        adaptation_overhead_total,
        adaptation_overhead_samples,
        wall_time,
        logfile
    )
    
    print(os.path.basename(logfile), '--> Simulation time (wall):', wall_time, f'({event_count} events)')
    return logfile, wall_time, event_count

if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else 'config.json'
    run(path)
