
# core.py
# Discrete-Event core used by simulator.py. No external deps except numpy.

import os, sys, random, queue, numpy as np
from typing import List, Dict, Optional

# A thin read-only config holder (dict-like access with attributes).
class Cfg:
    def __init__(self, d: Dict):
        self.__dict__.update(d)
        # For dynamic-adaptation: track current active architecture
        if self.ARCHITECTURE == 'dynamic-adaptation':
            # Start with a default architecture (can be overridden by INITIAL_ARCHITECTURE)
            self.current_architecture = getattr(self, 'INITIAL_ARCHITECTURE', 'centralized-impprox')
        else:
            self.current_architecture = self.ARCHITECTURE
        # RTLola monitor reference (set by simulator)
        self.rtlola_monitor = None
    
    def set_architecture(self, new_arch: str):
        """Update the current architecture at runtime (for dynamic-adaptation)."""
        if new_arch not in ['decentralized', 'semi-decentralized', 'centralized-impprox']:
            print(f'[WARNING] Invalid architecture for dynamic switching: {new_arch}')
            return
        self.current_architecture = new_arch
        # print(f'[ADAPTATION] Switched architecture to: {new_arch}')

class Clock:
    def __init__(self):
        self.time = 0.0
        # timestamp -> list of events (preserve simultaneous events)
        self.eventDict = {}

    def getTime(self):
        return self.time

    def scheduleEvent(self, event, avgTimes, traceFiles, distributions):
        inc = 0.0
        for avg, trace, distr in zip(avgTimes, traceFiles, distributions):
            if distr == 'exponential':
                inc += np.random.exponential(avg)
            elif distr == 'uniform':
                inc += np.random.uniform(0.0, float(avg) * 2.0)
            elif distr == 'deterministic':
                inc += float(avg)
            elif distr == 'trace':
                if avg >= 0:
                    print('[ERROR] Using trace but avg >= 0')
                    sys.exit(-1)
                with open(trace, 'r') as f:
                    lines = f.readlines()
                if len(lines) == 0:
                    print('No more timestamps in', trace)
                    os.remove(trace)
                    sys.exit(0)
                val = lines[0].strip()
                with open(trace, 'w') as f:
                    f.writelines(lines[1:])
                inc += float(val)
            else:
                print('[ERROR] Unsupported distribution:', distr)
                sys.exit(-1)
        ts = self.time + inc
        self.eventDict.setdefault(ts, []).append(event)

    def getNextEvent(self):
        if not self.eventDict:
            # No more events - simulation complete
            return None, None
        t = min(self.eventDict.keys())
        self.time = t
        ev = self.eventDict[t].pop(0)
        if len(self.eventDict[t]) == 0:
            del self.eventDict[t]
        return t, ev

    def removeEvent(self, eventToRemove):
        for k in list(self.eventDict.keys()):
            self.eventDict[k] = [ev for ev in self.eventDict[k] if ev != eventToRemove]
            if len(self.eventDict[k]) == 0:
                del self.eventDict[k]

    def checkClock(self):
        vals = [ev for evs in self.eventDict.values() for ev in evs]
        if len(vals) != len(set(vals)):
            # duplicate event label would break semantics
            dups = [x for x in set(vals) if vals.count(x) > 1]
            print('[ERROR] The same event has been scheduled more than once:', dups)
            sys.exit(-1)


class Room:
    def __init__(self, idx: int):
        self.idx = idx
        self.source = False
        self.adjacents: List['Room'] = []

    def setSource(self):
        self.source = True

    def setAdjacentRooms(self, rooms: List['Room']):
        self.adjacents = rooms

    def getAdjacentRooms(self) -> List['Room']:
        return self.adjacents

    def isAdjacent(self, room: 'Room') -> bool:
        return room in self.adjacents

    def getIdx(self) -> int:
        return self.idx

    def getProximity(self) -> Dict['Room', int]:
        # BFS distances from self
        prox = {}
        q = queue.Queue()
        q.put((self, 0))
        while not q.empty():
            r, d = q.get()
            if r not in prox:
                prox[r] = d
                for n in r.adjacents:
                    q.put((n, d + 1))
        return prox


class Item:
    def __init__(self, cfg: Cfg, logfile: str, idx: int, space: 'Space', simTime: float, imp=-1, target: Optional[Room]=None):
        self.cfg = cfg
        self.idx = idx
        self.position = space.getSource()
        self.target = target if target is not None else random.choice([r for r in space.getRooms() if r != space.getSource()])
        self.importance = self._randImportance(cfg.IMPORTANCE_PROBABILITIES) if imp == -1 else imp
        self.uber = None
        self.logfile = logfile
        if cfg.LOG_ITEM:
            self._log(simTime, 'create')

    def _randImportance(self, probs):
        if abs(sum(probs) - 1.0) > 1e-9:
            print('[ERROR] IMPORTANCE_PROBABILITIES must sum to 1')
            sys.exit(-1)
        r = np.random.uniform()
        s = 0.0
        for k, p in enumerate(probs):
            s += p
            if r < s:
                return k
        return len(probs) - 1

    # getters / setters
    def getIdx(self): return self.idx
    def getImportance(self): return self.importance
    def getLocation(self): return self.position
    def setLocation(self, room): self.position = room
    def getTarget(self): return self.target
    def getUber(self): return self.uber
    def setUber(self, robot): self.uber = robot

    def _log(self, simTime, event):
        os.makedirs(os.path.dirname(self.logfile), exist_ok=True)
        new = not os.path.exists(self.logfile)
        with open(self.logfile, 'a') as f:
            if new:
                f.write('simTime,robotId,itemId,itemImportance,position,destination,event\n')
            f.write(f'{simTime},{-1},{self.idx},{self.importance},{self.position.getIdx()},{self.target.getIdx()},{event}\n')


class Robot:
    def __init__(self, cfg: Cfg, idx: int, malicious: bool, space: 'Space', logfile: str):
        self.cfg = cfg
        self.idx = idx
        self.malicious = malicious
        self.space = space
        self.position = space.getSource()
        self.destination = space.getSource()
        self.space.setRobotPosition(self, self.position)
        self.item: Optional[Item] = None
        self.healthy = True
        self.optRoute: List[Room] = []
        self.memoryItem = None
        self.logfile = logfile

    # helpers
    def getIdx(self): return self.idx
    def isFree(self): return self.item is None
    def isHealthy(self): return self.healthy
    def hasOtherTasks(self): return len(self.optRoute) > 0
    def getItem(self): return self.item
    def setItem(self, item: Item): self.item, item.uber = item, self
    def unsetItem(self):
        if self.item:
            self.item.uber = None
        self.item = None
    def getItemImportance(self): return -1 if self.item is None else self.item.getImportance()
    def getLocation(self): return self.position
    def setLocation(self, r): self.position = r; self.space.setRobotPosition(self, r)
    def setDestination(self, r): self.destination = r

    def _privacy_bonus_by_importance(self, item: Optional[Item], bonus_cfg_name: str) -> float:
        if item is None:
            return 0.0
        bonuses = getattr(self.cfg, bonus_cfg_name, [0.0] * len(self.cfg.IMPORTANCE_PROBABILITIES))
        imp = item.getImportance()
        if imp < 0 or imp >= len(bonuses):
            return 0.0
        try:
            return float(bonuses[imp])
        except (TypeError, ValueError):
            return 0.0

    def _effective_comm_time(self, item: Optional[Item]) -> float:
        return float(self.cfg.COMM_TIME) + self._privacy_bonus_by_importance(item, 'PRIVACY_COMM_TIME_BONUS')

    def _effective_comp_time(self, item: Optional[Item]) -> float:
        return float(self.cfg.COMP_TIME) + self._privacy_bonus_by_importance(item, 'PRIVACY_COMP_TIME_BONUS')

    def _log(self, simTime, event):
        os.makedirs(os.path.dirname(self.logfile), exist_ok=True)
        new = not os.path.exists(self.logfile)
        with open(self.logfile, 'a') as f:
            if new:
                f.write('simTime,robotId,itemId,itemImportance,position,destination,event\n')
            if self.item is None:
                f.write(f'{simTime},{self.idx},{-1},{-1},{self.position.getIdx()},{self.destination.getIdx()},{event}\n')
            else:
                f.write(f'{simTime},{self.idx},{self.item.getIdx()},{self.item.getImportance()},{self.position.getIdx()},{self.destination.getIdx()},{event}\n')

    def dropItem(self, simTime, itemExpired=False):
        if self.position == self.destination:
            if self.cfg.LOG_DELIVERY: self._log(simTime, 'deliver')
            self.space.deliverItem(self.item)
        else:
            if self.cfg.LOG_DROP: self._log(simTime, 'drop')
            if itemExpired:
                self.space.clock.removeEvent(f'move-{self.getIdx()}')
            else:
                self.item.setLocation(self.position)
                self.space.switchItem(self.item)
        self.unsetItem()
        self.destination = self.space.getSource()
        if len(self.space.getItemsByImportance(imp=-1, room=self.position)) == 0 and self.isHealthy():
            self.optRoute = self.space.findRoute(self.position, self.destination, strategy=self.cfg.FIND_ROUTE_STRATEGY)
            if itemExpired and self.position != self.space.getSource():
                self.space.clock.scheduleEvent(f'move-{self.getIdx()}', [self.cfg.MOVEMENT_TIME], [self.cfg.MOVEMENT_TRACE], [self.cfg.MOVEMENT_DISTR])

    def loadItem(self, item: Item, simTime):
        if self.item is not None:
            self.dropItem(simTime)
        eff_comp_time = self._effective_comp_time(item)
        eff_comm_time = self._effective_comm_time(item)
        # Pay computation/communication costs depending on mechanism
        if self.cfg.current_architecture == 'semi-decentralized':
            avg = [self.cfg.LOAD_TIME, eff_comp_time, self.cfg.MOVEMENT_TIME, eff_comm_time, self.cfg.DROP_TIME]
            trc = [self.cfg.LOAD_TRACE, self.cfg.COMP_TRACE, self.cfg.MOVEMENT_TRACE, self.cfg.COMM_TRACE, self.cfg.DROP_TRACE]
            dst = [self.cfg.LOAD_DISTR, self.cfg.COMP_DISTR, self.cfg.MOVEMENT_DISTR, self.cfg.COMM_DISTR, self.cfg.DROP_DISTR]
        elif 'centralized-' in self.cfg.current_architecture:
            avg = [self.cfg.LOAD_TIME, 0, self.cfg.MOVEMENT_TIME, eff_comm_time, self.cfg.DROP_TIME]
            trc = [self.cfg.LOAD_TRACE, '_', self.cfg.MOVEMENT_TRACE, self.cfg.COMM_TRACE, self.cfg.DROP_TRACE]
            dst = [self.cfg.LOAD_DISTR, self.cfg.COMP_DISTR, self.cfg.MOVEMENT_DISTR, self.cfg.COMM_DISTR, self.cfg.DROP_DISTR]
        else:
            avg = [self.cfg.LOAD_TIME, eff_comp_time, self.cfg.MOVEMENT_TIME, 0, self.cfg.DROP_TIME]
            trc = [self.cfg.LOAD_TRACE, self.cfg.COMP_TRACE, self.cfg.MOVEMENT_TRACE, '_', self.cfg.DROP_TRACE]
            dst = [self.cfg.LOAD_DISTR, self.cfg.COMP_DISTR, self.cfg.MOVEMENT_DISTR, self.cfg.COMM_DISTR, self.cfg.DROP_DISTR]
        self.space.clock.scheduleEvent(f'move-{self.getIdx()}', avg, trc, dst)
        self.memoryItem = None
        self.setItem(item)
        self.destination = item.getTarget()
        self.space.switchItem(item)
        self.optRoute = self.space.findRoute(self.position, self.destination, strategy=self.cfg.FIND_ROUTE_STRATEGY)
        if self.cfg.LOG_LOAD:
            self._log(simTime, 'startLoading')

    def canLoadItem(self):
        if not self.isHealthy(): return False
        if len(self.space.getItemsByImportance(imp=-1, room=self.position)) == 0: return False
        if self.isFree(): return True
        currImp = self.item.getImportance()
        impItems = self.space.getItemsWithMoreImportance(imp=currImp, room=self.position)
        return len(impItems) > 0

    def move(self, simTime):
        if len(self.optRoute) == 0:
            print(f'[ERROR] Robot {self.getIdx()} stuck in Room {self.position.getIdx()}'); sys.exit(-1)
        nextRoom = self.optRoute.pop(0)
        self.setLocation(nextRoom)
        if self.cfg.LOG_MOVE: self._log(simTime, 'move')
        if self.destination == nextRoom and not self.isFree():
            self.dropItem(simTime); self.memoryItem = None
        if self._fail(simTime):
            self.space.clock.scheduleEvent(f'recovery-{self.getIdx()}', [self.cfg.RECOVERY_TIME], [self.cfg.RECOVERY_TRACE], [self.cfg.RECOVERY_DISTR])
            self.memoryItem = None
        elif self.memoryItem is not None:
            if self.memoryItem[0].getImportance() > self.space.getMaxImportance(room=nextRoom):
                self.optRoute = self.space.findRoute(self.position, self.memoryItem[1], strategy=self.cfg.FIND_ROUTE_STRATEGY)
                self.space.clock.scheduleEvent(f'move-{self.getIdx()}', [self.cfg.MOVEMENT_TIME], [self.cfg.MOVEMENT_TRACE], [self.cfg.MOVEMENT_DISTR])
            else:
                self.loadItem(self.space.getMoreImportantItem(room=nextRoom), simTime)
            self.memoryItem = None
        elif self.canLoadItem():
            self.loadItem(self.space.getMoreImportantItem(room=nextRoom), simTime)
        elif len(self.optRoute) == 0 and self.isFree() and self.position != self.space.getSource():
            self.destination = self.space.getSource()
            self.optRoute = self.space.findRoute(self.position, self.destination, strategy=self.cfg.FIND_ROUTE_STRATEGY)
            self.space.clock.scheduleEvent(f'move-{self.getIdx()}', [self.cfg.MOVEMENT_TIME], [self.cfg.MOVEMENT_TRACE], [self.cfg.MOVEMENT_DISTR])
        elif not (self.isFree() and self.position == self.space.getSource()):
            self.space.clock.scheduleEvent(f'move-{self.getIdx()}', [self.cfg.MOVEMENT_TIME], [self.cfg.MOVEMENT_TRACE], [self.cfg.MOVEMENT_DISTR])
        # malicious fake messages
        if self.isHealthy() and self.malicious and self.cfg.MALICIOUS_FAKE_FAILURES and not (np.random.uniform() < self.cfg.COMM_FAIL_PROB):
            self._fakeFailure(nextRoom, simTime)

    def _fail(self, simTime):
        if np.random.uniform() < self.cfg.FAIL_PROB:
            self.healthy = False
            if self.cfg.LOG_FAIL: self._log(simTime, 'fail')
            if self.item is not None:
                itemToDrop = self.item
                self.dropItem(simTime)
                if not (np.random.uniform() < self.cfg.COMM_FAIL_PROB):
                    if self.cfg.current_architecture == 'semi-decentralized':
                        importance = itemToDrop.getImportance() if not self.malicious else len(self.cfg.IMPORTANCE_PROBABILITIES) + 1
                        self._sendPeers(importance, self.position, simTime)
                    elif 'centralized-' in self.cfg.current_architecture:
                        strat = self.cfg.current_architecture.split('-')[1]
                        importance = itemToDrop.getImportance() if not self.malicious else len(self.cfg.IMPORTANCE_PROBABILITIES) + 1
                        self._sendMaster(importance, self.position, simTime, strat)
            return True
        return False

    def recovery(self, simTime):
        self.healthy = True
        self.position = self.space.getSource()
        self.space.setRobotPosition(self, self.position)
        self.destination = self.space.getSource()
        self.optRoute = []
        if self.cfg.LOG_RECOVERY: self._log(simTime, 'recover')
        if self.canLoadItem():
            self.loadItem(self.space.getMoreImportantItem(room=self.position), simTime)

    # messaging
    def _sendPeers(self, itemImportance, position, simTime, fake=False):
        near = self.space.getNearRobots(self)
        if self.cfg.LOG_HELP and not fake: self._log(simTime, 'help')
        # choose a helper among close robots with min importance
        cand = self.space.getRobotsByImportance(self, near, itemImportance)
        if len(cand) == 0: return None
        helper = random.choice(cand)
        helper._abortMission(itemImportance, position, simTime)

    def _sendMaster(self, itemImportance, position, simTime, strategy, fake=False):
        if self.cfg.LOG_HELP and not fake: self._log(simTime, 'help')
        bots = self.space.getAllRobots()
        if strategy == 'proximity':
            s1 = self.space.getRobotsByProximity(self, bots, position)
            s2 = s1
        elif strategy == 'importance':
            s1 = self.space.getRobotsByImportance(self, bots, itemImportance)
            s2 = s1
        elif strategy == 'proximp':
            s1 = self.space.getRobotsByProximity(self, bots, position)
            s2 = self.space.getRobotsByImportance(self, s1, itemImportance) if len(s1) > 0 else []
        elif strategy == 'impprox':
            s1 = self.space.getRobotsByImportance(self, bots, itemImportance)
            s2 = self.space.getRobotsByProximity(self, s1, position) if len(s1) > 0 else []
        else:
            print('Unsupported centralized strategy'); sys.exit(-1)
        if len(s2) > 0:
            helper = random.choice(s2)
            helper._abortMission(itemImportance, position, simTime)

    def _fakeFailure(self, position, simTime):
        if self.cfg.LOG_FAKE: self._log(simTime, 'fakeFailure')
        maxImp = len(self.cfg.IMPORTANCE_PROBABILITIES) + 1
        if self.cfg.current_architecture == 'semi-decentralized':
            self._sendPeers(maxImp, self.position, simTime, fake=True)
        elif 'centralized-' in self.cfg.current_architecture:
            strat = self.cfg.current_architecture.split('-')[1]
            self._sendMaster(maxImp, self.position, simTime, strat, fake=True)

    def _abortMission(self, newItemImportance, helpRoom, simTime):
        if self.cfg.LOG_RESCUE: self._log(simTime, 'rescue')
        if helpRoom == self.position:
            if self.canLoadItem():
                self.space.clock.removeEvent(f'move-{self.getIdx()}')
                self.loadItem(self.space.getMoreImportantItem(room=self.position), simTime)
        elif self.getItemImportance() < newItemImportance and self.isHealthy():
            if len(self.optRoute) == 0 or helpRoom != self.optRoute[0]:
                if not self.isFree():
                    self.memoryItem = [self.item, self.position]
                    self.dropItem(simTime)
                self.space.clock.removeEvent(f'move-{self.getIdx()}')
                self.destination = helpRoom
                self.optRoute = self.space.findRoute(self.position, self.destination, strategy=self.cfg.FIND_ROUTE_STRATEGY)
                self.space.clock.scheduleEvent(f'move-{self.getIdx()}', [self.cfg.MOVEMENT_TIME], [self.cfg.MOVEMENT_TRACE], [self.cfg.MOVEMENT_DISTR])


class Space:
    def __init__(self, cfg: Cfg, rooms: List[Room], connection_dict, clock: Clock, source: Optional[Room] = None):
        self.cfg = cfg
        self.rooms = rooms
        self.connections_dict = connection_dict
        self.clock = clock
        self.source = source or rooms[0]
        self.source.setSource()
        for i, adjs in connection_dict.items():
            rooms[i].setAdjacentRooms([rooms[j] for j in adjs])
        self.availItems: List[Item] = []
        self.movingItems: List[Item] = []
        self.robotPositionDict: Dict[Robot, Room] = {}

    def getSource(self): return self.source
    def getRooms(self): return self.rooms
    def getClock(self): return self.clock
    def getAllRobots(self): return list(self.robotPositionDict.keys())

    def setRobotPosition(self, robot: Robot, room: Room):
        self.robotPositionDict[robot] = room

    def getNearRobots(self, askingRobot: Robot) -> List[Robot]:
        targetRoom = askingRobot.getLocation()
        outs = []
        for bot, room in self.robotPositionDict.items():
            if bot != askingRobot and (room == targetRoom or room.isAdjacent(targetRoom)):
                outs.append(bot)
        return outs

    def getRobotsByImportance(self, askingRobot: Robot, bots: List[Robot], itemImportance: int) -> List[Robot]:
        bots = [b for b in bots if b != askingRobot]
        minImp = itemImportance
        for b in bots:
            if b.isHealthy():
                curr = b.getItemImportance()
                if curr == -1:
                    minImp = curr; break
                elif curr < minImp:
                    minImp = curr
        if minImp >= itemImportance: return []
        return [b for b in bots if b.isHealthy() and b.getItemImportance() == minImp]

    def getRobotsByProximity(self, askingRobot: Robot, bots: List[Robot], targetRoom: Room) -> List[Robot]:
        bots = [b for b in bots if b != askingRobot and b.isHealthy()]
        prox = targetRoom.getProximity()
        minH = min([prox[self.robotPositionDict[b]] for b in bots], default=10**9)
        return [b for b in bots if prox[self.robotPositionDict[b]] == minH]

    # items
    def newItem(self, item: Item):
        self.availItems.append(item)
        impIdx = item.getImportance()
        expireTime = self.cfg.EXPIRATION_TIME[impIdx]
        if expireTime != -1:
            expireDistr = self.cfg.EXPIRATION_DISTR[impIdx]
            self.clock.scheduleEvent(f'expire-{item.getIdx()}', [expireTime], ['_'], [expireDistr])
        self.clock.scheduleEvent('item', [self.cfg.ITEM_SPAWNING_TIME], [self.cfg.ITEM_SPAWNING_TRACE], [self.cfg.ITEM_SPAWNING_DISTR])

    def getItembyId(self, idx: int) -> Item:
        for item in self.availItems + self.movingItems:
            if item.getIdx() == idx:
                return item
        print('[ERROR] No item with id', idx); sys.exit(-1)

    def getItemsByImportance(self, imp=-1, room: Optional[Room]=None) -> List[Item]:
        pool = self.availItems if room is None else [it for it in self.availItems if it.getLocation() == room]
        if imp == -1: return pool
        return [it for it in pool if it.getImportance() == imp]

    def getItemsWithMoreImportance(self, imp=-1, room: Optional[Room]=None) -> List[Item]:
        pool = self.availItems if room is None else [it for it in self.availItems if it.getLocation() == room]
        if imp == -1: return pool
        return [it for it in pool if it.getImportance() > imp]

    def getMoreImportantItem(self, room: Optional[Room]=None) -> Optional[Item]:
        pool = self.availItems if room is None else [it for it in self.availItems if it.getLocation() == room]
        best = None; bestImp = -1
        for it in pool:
            ii = it.getImportance()
            if ii > bestImp:
                bestImp, best = ii, it
        return best

    def getMaxImportance(self, room: Optional[Room]=None) -> int:
        it = self.getMoreImportantItem(room)
        return -1 if it is None else it.getImportance()

    def deliverItem(self, item: Item):
        self.clock.removeEvent(f'expire-{item.getIdx()}')
        self.movingItems.remove(item)

    def expireItem(self, item: Item, simTime: float):
        if self.cfg.LOG_EXPIRE:
            item._log(simTime, 'expire')
        if item in self.availItems:
            self.availItems.remove(item)
        elif item in self.movingItems:
            self.movingItems.remove(item)
            bot = item.getUber()
            bot.dropItem(simTime, itemExpired=True)
        else:
            print('[ERROR] Expired item does not exist'); sys.exit(-1)

    def switchItem(self, item: Item):
        if item in self.availItems:
            self.availItems.remove(item); self.movingItems.append(item)
        elif item in self.movingItems:
            self.movingItems.remove(item); self.availItems.append(item)
        else:
            print('[ERROR] Switching unknown item'); sys.exit(-1)

    # routing
    def _routes_dfs(self, start: Room, target: Room, visited=None, routes=None):
        if visited is None: visited = []
        if routes is None: routes = {}
        visited = [*visited, start]
        if start == target:
            routes[str([r.getIdx() for r in visited])] = len(visited) - 1
        else:
            for r in start.getAdjacentRooms():
                if r not in visited:
                    routes = self._routes_dfs(r, target, visited, routes)
        return routes

    def _routes_bfs(self, start: Room, target: Room):
        q = queue.Queue()
        q.put([start])
        routes = {}
        while not q.empty():
            path = q.get()
            if target in path:
                cost = len(path) - 1
                if len(routes) == 0 or cost < min(routes.values()):
                    routes = {str([r.getIdx() for r in path]): cost}
                elif cost == min(routes.values()):
                    routes[str([r.getIdx() for r in path])] = cost
            elif len(routes) == 0:
                for adj in path[-1].getAdjacentRooms():
                    if adj not in path: q.put(path + [adj])
        return routes

    def findRoute(self, start: Room, target: Room, strategy='breadth') -> List[Room]:
        if strategy == 'breadth':
            routes = self._routes_bfs(start, target); poss = list(routes.keys())
        elif strategy == 'depth':
            routes = self._routes_dfs(start, target); 
            minc = min(routes.values()); poss = [k for k, v in routes.items() if v == minc]
        else:
            print('[ERROR] Unknown routing strategy'); sys.exit(-1)
        if len(poss) == 0:
            print(f'[ERROR] No route between {start.getIdx()} and {target.getIdx()}'); sys.exit(-1)
        chosen = random.choice(poss)[1:-1].split(', ')
        # Filter out empty strings and skip the first element (start room)
        chosen = [i for i in chosen if i]
        if len(chosen) > 0:
            chosen = chosen[1:]  # Skip start room
        return [self.rooms[int(i)] for i in chosen]
