# Executes simple, safe actions using S4CL utilities.
from typing import Optional
import random
import services
from sims4.math import Vector3
from sims4communitylib.utils.sims.common_sim_utils import CommonSimUtils
from sims4communitylib.utils.location.common_location_utils import CommonLocationUtils
from sims4communitylib.utils.sims.common_sim_movement_utils import CommonSimMovementUtils
from sims4communitylib.utils.common_type_utils import CommonTypeUtils
from .schedules import TimeBlock
from .util import log

class ActionExecutor:
    def __init__(self, cfg: 'NLConfig'):
        self.cfg = cfg

    def execute(self, sim_info, block: TimeBlock):
        sim = CommonSimUtils.get_sim_instance(sim_info)
        if sim is None:
            log(f"Sim {sim_info.sim_id} not instanced; skipping action {block.action}")
            return

        action = block.action
        if action in ('JOG', 'WALK', 'PARK_WALK'):
            self._do_walk_or_jog(sim, jog=(action == 'JOG'))
        elif action in ('CAFE_IDLE', 'LIB_IDLE', 'DINING_IDLE', 'GYM_IDLE', 'HOME_IDLE'):
            self._do_idle(sim)
        elif action == 'NEIGHBOR_VISIT':
            self._do_neighbor_visit(sim)
        else:
            log(f"Unknown action {action}")

    def cleanup(self, sim_info, block: TimeBlock):
        pass

    def _do_walk_or_jog(self, sim, jog: bool = False):
        zone_id = services.current_zone_id()
        start = sim.position
        target = self._random_point_nearby(start, radius=12.0, tries=6)
        if target is None:
            log("No valid target position for walk/jog; skipping")
            return
        CommonSimMovementUtils.route_sim_to_position(sim, target)
        if jog:
            # No true jog animation without specific interaction; simulate with longer path and short waits.
            for _ in range(2):
                next_pos = self._random_point_nearby(target, radius=10.0, tries=4)
                if next_pos is not None:
                    CommonSimMovementUtils.route_sim_to_position(sim, next_pos)

    def _do_idle(self, sim):
        start = sim.position
        target = self._random_point_nearby(start, radius=8.0, tries=6)
        if target is None:
            return
        CommonSimMovementUtils.route_sim_to_position(sim, target)

    def _do_neighbor_visit(self, sim):
        self._do_idle(sim)

    def _random_point_nearby(self, pos, radius: float = 10.0, tries: int = 5) -> Optional[Vector3]:
        for _ in range(tries):
            dx = random.uniform(-radius, radius)
            dz = random.uniform(-radius, radius)
            candidate = Vector3(pos.x + dx, pos.y, pos.z + dz)
            if CommonLocationUtils.is_position_on_active_lot(candidate):
                return candidate
        return None
