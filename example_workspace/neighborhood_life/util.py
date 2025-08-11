# Utilities: config, logging, time helpers, participant selection.
import json
import os
import random
from dataclasses import dataclass
from typing import Dict, List, Optional
import services
from date_and_time import DateAndTime
from sims.sim_info import SimInfo
from sims4communitylib.utils.sims.common_sim_utils import CommonSimUtils
from sims4communitylib.utils.sims.common_sim_filter_utils import CommonSimFilterUtils
from sims4communitylib.utils.common_log_registry import CommonLogRegistry

MOD_FOLDER_NAME = "NeighborhoodLife"
RESOURCES_DIR = "neighborhood_life_resources"
CONFIG_FILENAME = "config.json"

def log(msg: str):
    if NLConfig._cached and NLConfig._cached.debug_logging:
        print(f"[NeighborhoodLife] {msg}")

def ensure_singleton(old, new):
    if old is not None:
        return old
    return new

@dataclass
class NLConfig:
    participant_count: int
    time_blocks: list
    trait_bias: Dict[str, Dict[str, float]]
    weather_bias: Dict[str, Dict[str, float]]
    weekend_bias: Dict[str, float]
    news_enabled: bool
    debug_logging: bool

    _cached: Optional['NLConfig'] = None

    @classmethod
    def load(cls) -> 'NLConfig':
        if cls._cached is not None:
            return cls._cached
        # Locate config in Mods/NeighborhoodLife/neighborhood_life_resources/config.json
        user_dir = os.path.expanduser("~/")
        # In-game, direct documents path isn't necessary; the game sets current directory.
        # We search relative to Mods path by walking up from script location if needed.
        base_dir = None
        try:
            base_dir = os.path.dirname(__file__)
        except Exception:
            base_dir = None

        # Try multiple candidate paths
        candidates = []
        if base_dir:
            candidates.append(os.path.join(os.path.dirname(base_dir), RESOURCES_DIR, CONFIG_FILENAME))
        candidates.append(os.path.join(RESOURCES_DIR, CONFIG_FILENAME))

        data = None
        for p in candidates:
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                break

        if data is None:
            # Fallback defaults if not found
            data = {
                "participant_count": 8,
                "time_blocks": [],
                "trait_bias": {},
                "weather_bias": {},
                "weekend_bias": {},
                "news_enabled": True,
                "debug_logging": True
            }

        cfg = NLConfig(
            participant_count=int(data.get("participant_count", 8)),
            time_blocks=list(data.get("time_blocks", [])),
            trait_bias=dict(data.get("trait_bias", {})),
            weather_bias=dict(data.get("weather_bias", {})),
            weekend_bias=dict(data.get("weekend_bias", {})),
            news_enabled=bool(data.get("news_enabled", True)),
            debug_logging=bool(data.get("debug_logging", True))
        )
        cls._cached = cfg
        return cfg

def is_weekend() -> bool:
    time_service = services.time_service()
    day = time_service.sim_now.day_of_week()
    return day in (6, 7)  # Saturday=6, Sunday=7 in many TS4 enums

def time_str_to_minutes(hhmm: str) -> int:
    hh, mm = hhmm.split(":")
    return int(hh) * 60 + int(mm)

def get_today_minutes() -> int:
    now: DateAndTime = services.time_service().sim_now
    return int(now.hour()) * 60 + int(now.minute())

def select_participant_sims(count: int) -> List[SimInfo]:
    all_candidates: List[SimInfo] = []
    for sim_info in services.sim_info_manager().get_all():
        if sim_info.is_human and not sim_info.is_baby and not sim_info.is_instanced(allow_hidden_flags=False):
            if sim_info.is_npc or not sim_info.is_played:
                all_candidates.append(sim_info)
    random.shuffle(all_candidates)
    picked = all_candidates[:max(1, count)]
    log(f"Picked {len(picked)} participants from {len(all_candidates)} candidates.")
    return picked

def weighted_choice(weights: Dict[str, float]) -> str:
    items = [(k, max(v, 0.0)) for k, v in weights.items() if v > 0.0]
    if not items:
        return random.choice(list(weights.keys()))
    total = sum(v for _, v in items)
    r = random.uniform(0, total)
    upto = 0.0
    for k, v in items:
        if upto + v >= r:
            return k
        upto += v
    return items[-1][0]
