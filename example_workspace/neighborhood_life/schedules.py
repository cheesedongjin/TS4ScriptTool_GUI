# Build daily schedules based on config, traits, weather, and day of week.
import random
from dataclasses import dataclass
from typing import List, Dict, Tuple
import services
from sims4communitylib.utils.location.common_region_utils import CommonRegionUtils
from sims4communitylib.utils.sims.common_trait_utils import CommonTraitUtils
from sims4communitylib.utils.sims.common_sim_utils import CommonSimUtils
from sims4communitylib.enums.weather_types import CommonWeatherType
from sims4communitylib.utils.resources.common_weather_service_utils import CommonWeatherServiceUtils
from .util import time_str_to_minutes, log, weighted_choice, is_weekend

@dataclass
class TimeBlock:
    start_min: int
    duration_min: int
    action: str
    venue_tag: str

@dataclass
class DailySchedule:
    sim_id: int
    blocks: List[TimeBlock]

class ScheduleBuilder:
    def __init__(self, cfg: 'NLConfig'):
        self.cfg = cfg

    def build_for_sims(self, sim_infos: List) -> Dict[int, DailySchedule]:
        schedules: Dict[int, DailySchedule] = {}
        wtype = self._get_weather_type()
        for sim_info in sim_infos:
            sid = sim_info.sim_id
            blocks: List[TimeBlock] = []
            for block in self.cfg.time_blocks:
                start = time_str_to_minutes(block['start'])
                dur = random.randint(block['duration_min'][0], block['duration_min'][1])
                action_weights = dict(block['actions'])

                self._apply_trait_bias(sim_info, action_weights)
                self._apply_weather_bias(wtype, action_weights)
                if is_weekend():
                    self._apply_weekend_bias(action_weights)

                action = weighted_choice(action_weights)
                venue_tag = self._derive_venue_tag(action)
                blocks.append(TimeBlock(start_min=start, duration_min=dur, action=action, venue_tag=venue_tag))
            schedules[sid] = DailySchedule(sim_id=sid, blocks=blocks)
            log(f"Built schedule for {sid}: {[ (b.action, b.start_min, b.duration_min) for b in blocks ]}")
        return schedules

    def _derive_venue_tag(self, action: str) -> str:
        mapping = {
            'CAFE_IDLE': 'cafe',
            'LIB_IDLE': 'library',
            'GYM_IDLE': 'gym',
            'DINING_IDLE': 'dining',
            'PARK_WALK': 'park',
            'NEIGHBOR_VISIT': 'residential',
            'HOME_IDLE': 'residential',
            'WALK': None,
            'JOG': None
        }
        return mapping.get(action, None)

    def _apply_trait_bias(self, sim_info, weights: Dict[str, float]):
        traits = CommonTraitUtils.get_traits(sim_info)
        names = set(getattr(t, 'trait_name', None) or getattr(t, 'name', None) for t in traits)
        for trait_name, adds in self.cfg.trait_bias.items():
            if trait_name in names:
                for act, delta in adds.items():
                    weights[act] = weights.get(act, 0.0) + delta

    def _apply_weather_bias(self, weather_type: CommonWeatherType, weights: Dict[str, float]):
        name = str(weather_type.name) if weather_type is not None else None
        if name is None:
            return
        adds = self.cfg.weather_bias.get('Rain' if 'RAIN' in name else 'Snow' if 'SNOW' in name else None, None)
        if not adds:
            return
        for act, delta in adds.items():
            weights[act] = weights.get(act, 0.0) + delta

    def _apply_weekend_bias(self, weights: Dict[str, float]):
        for act, delta in self.cfg.weekend_bias.items():
            weights[act] = weights.get(act, 0.0) + delta

    def _get_weather_type(self) -> CommonWeatherType:
        svc = CommonWeatherServiceUtils.get_weather_service()
        if svc is None:
            return None
        return CommonWeatherServiceUtils.get_current_weather_type()
